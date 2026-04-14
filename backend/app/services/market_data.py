from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from typing import Any, cast

import httpx

from app.core.config import get_settings


settings = get_settings()
PRICE_QUANT = Decimal("0.000001")
STOOQ_URL = "https://stooq.com/q/l/"


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def is_crypto_symbol(symbol: str) -> bool:
    return "/" in symbol


class MarketDataError(Exception):
    pass


@dataclass
class MarketDataResult:
    prices: dict[str, Decimal]
    provider: str | None


class MarketDataClient:
    def _has_alpaca_credentials(self) -> bool:
        return bool(settings.alpaca_api_key and settings.alpaca_secret_key)

    def _headers(self) -> dict[str, str]:
        if not self._has_alpaca_credentials():
            raise MarketDataError("Alpaca market data credentials are not configured.")
        api_key = settings.alpaca_api_key
        secret_key = settings.alpaca_secret_key
        if api_key is None or secret_key is None:
            raise MarketDataError("Alpaca market data credentials are not configured.")
        return {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json",
        }

    async def _get_alpaca_equity_prices(
        self, client: httpx.AsyncClient, equities: list[str]
    ) -> dict[str, Decimal]:
        if not equities:
            return {}

        response = await client.get(
            f"{settings.alpaca_data_url}/v2/stocks/trades/latest",
            headers=self._headers(),
            params={
                "symbols": ",".join(equities),
                "feed": settings.alpaca_equity_feed,
            },
        )
        if response.status_code >= 400:
            raise MarketDataError(response.text)
        payload = response.json().get("trades", {})
        return {
            symbol: to_decimal(data["p"])
            for symbol, data in payload.items()
            if data.get("p") is not None
        }

    async def _get_alpaca_crypto_prices(
        self, client: httpx.AsyncClient, crypto: list[str]
    ) -> dict[str, Decimal]:
        if not crypto:
            return {}

        response = await client.get(
            f"{settings.alpaca_data_url}/v1beta3/crypto/us/latest/trades",
            headers=self._headers(),
            params={"symbols": ",".join(crypto)},
        )
        if response.status_code >= 400:
            raise MarketDataError(response.text)
        payload = response.json().get("trades", {})
        return {
            symbol: to_decimal(data["p"])
            for symbol, data in payload.items()
            if data.get("p") is not None
        }

    async def _get_stooq_equity_price(
        self, client: httpx.AsyncClient, symbol: str
    ) -> tuple[str, Decimal] | None:
        response = await client.get(
            STOOQ_URL,
            params={
                "s": f"{symbol.lower()}.us",
                "f": "sd2t2ohlcvn",
                "e": "csv",
            },
        )
        if response.status_code >= 400:
            raise MarketDataError(response.text)

        rows = list(csv.reader(StringIO(response.text.strip())))
        if not rows:
            return None

        first_row = rows[0]
        if len(first_row) < 7 or first_row[1] == "N/D" or first_row[6] == "N/D":
            return None

        return symbol, to_decimal(first_row[6])

    async def _get_stooq_equity_prices(
        self, client: httpx.AsyncClient, equities: list[str]
    ) -> dict[str, Decimal]:
        if not equities:
            return {}

        raw_results = await asyncio.gather(
            *(self._get_stooq_equity_price(client, symbol) for symbol in equities),
            return_exceptions=True,
        )
        results = cast(list[tuple[str, Decimal] | Exception | None], raw_results)
        prices: dict[str, Decimal] = {}
        errors: list[Exception] = []
        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                continue
            if result is None:
                continue
            symbol, price = result
            prices[symbol] = price

        if prices:
            return prices
        if errors:
            raise MarketDataError(str(errors[0]))
        return {}

    async def get_latest_prices(self, symbols: list[str]) -> MarketDataResult:
        normalized_symbols = sorted({normalize_symbol(symbol) for symbol in symbols})
        if not normalized_symbols:
            return MarketDataResult(prices={}, provider=None)

        equities = [
            symbol for symbol in normalized_symbols if not is_crypto_symbol(symbol)
        ]
        crypto = [symbol for symbol in normalized_symbols if is_crypto_symbol(symbol)]
        prices: dict[str, Decimal] = {}
        provider: str | None = None

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            if equities and self._has_alpaca_credentials():
                try:
                    alpaca_equities = await self._get_alpaca_equity_prices(
                        client, equities
                    )
                    if alpaca_equities:
                        prices.update(alpaca_equities)
                        provider = "alpaca"
                except MarketDataError:
                    fallback_equities = await self._get_stooq_equity_prices(
                        client, equities
                    )
                    if fallback_equities:
                        prices.update(fallback_equities)
                        provider = "stooq"
            elif equities:
                fallback_equities = await self._get_stooq_equity_prices(
                    client, equities
                )
                if fallback_equities:
                    prices.update(fallback_equities)
                    provider = "stooq"

            missing_equities = [symbol for symbol in equities if symbol not in prices]
            if missing_equities:
                fallback_equities = await self._get_stooq_equity_prices(
                    client, missing_equities
                )
                if fallback_equities:
                    prices.update(fallback_equities)
                    if provider is None:
                        provider = "stooq"

            if crypto:
                crypto_prices = await self._get_alpaca_crypto_prices(client, crypto)
                if crypto_prices:
                    prices.update(crypto_prices)
                    if provider is None:
                        provider = "alpaca"

        return MarketDataResult(prices=prices, provider=provider)
