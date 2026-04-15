from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.time import normalize_utc


settings = get_settings()
PRICE_QUANT = Decimal("0.000001")


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


@dataclass
class EquityBar:
    timestamp: datetime
    close: Decimal


@dataclass
class EquityPriceCandidate:
    timestamp: datetime | None
    priority: int
    price: Decimal


class MarketDataClient:
    def _alpaca_snapshots_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        snapshots = payload.get("snapshots")
        if isinstance(snapshots, dict):
            return snapshots
        return {
            symbol: snapshot
            for symbol, snapshot in payload.items()
            if isinstance(symbol, str) and isinstance(snapshot, dict)
        }

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
            f"{settings.alpaca_data_url}/v2/stocks/snapshots",
            headers=self._headers(),
            params={
                "symbols": ",".join(equities),
                "feed": settings.alpaca_equity_feed,
            },
        )
        if response.status_code >= 400:
            raise MarketDataError(response.text)
        payload = self._alpaca_snapshots_payload(response.json())
        prices: dict[str, Decimal] = {}
        for symbol, snapshot in payload.items():
            price = self._extract_alpaca_equity_price(snapshot)
            if price is not None:
                prices[symbol] = price
        return prices

    def _extract_alpaca_equity_price(self, snapshot: Any) -> Decimal | None:
        if not isinstance(snapshot, dict):
            return None

        candidates: list[EquityPriceCandidate] = []

        latest_trade = snapshot.get("latestTrade") or {}
        trade_price = latest_trade.get("p")
        if trade_price is not None:
            candidates.append(
                EquityPriceCandidate(
                    timestamp=self._parse_alpaca_timestamp(latest_trade.get("t")),
                    priority=4,
                    price=to_decimal(trade_price),
                )
            )

        latest_quote = snapshot.get("latestQuote") or {}
        bid_price = latest_quote.get("bp")
        ask_price = latest_quote.get("ap")
        if bid_price is not None and ask_price is not None:
            bid = Decimal(str(bid_price))
            ask = Decimal(str(ask_price))
            if bid > 0 and ask > 0:
                candidates.append(
                    EquityPriceCandidate(
                        timestamp=self._parse_alpaca_timestamp(latest_quote.get("t")),
                        priority=3,
                        price=to_decimal((bid + ask) / Decimal("2")),
                    )
                )

        for bar_key in ("minuteBar", "dailyBar", "prevDailyBar"):
            bar = snapshot.get(bar_key) or {}
            close = bar.get("c")
            if close is not None:
                priority = {
                    "minuteBar": 2,
                    "dailyBar": 1,
                    "prevDailyBar": 0,
                }[bar_key]
                candidates.append(
                    EquityPriceCandidate(
                        timestamp=self._parse_alpaca_timestamp(bar.get("t")),
                        priority=priority,
                        price=to_decimal(close),
                    )
                )

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda candidate: (
                candidate.timestamp or datetime.min.replace(tzinfo=UTC),
                candidate.priority,
            ),
        ).price

    def _parse_alpaca_timestamp(self, value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            return normalize_utc(
                datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            )
        except ValueError:
            return None

    async def _get_alpaca_equity_bars(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[EquityBar]:
        response = await client.get(
            f"{settings.alpaca_data_url}/v2/stocks/bars",
            headers=self._headers(),
            params={
                "symbols": symbol,
                "timeframe": timeframe,
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
                "feed": settings.alpaca_equity_feed,
                "adjustment": "raw",
                "sort": "asc",
                "limit": 10000,
            },
        )
        if response.status_code >= 400:
            raise MarketDataError(response.text)

        payload = response.json().get("bars", {})
        rows = payload.get(symbol, [])
        bars: list[EquityBar] = []
        for row in rows:
            close = row.get("c")
            timestamp = row.get("t")
            if close is None or timestamp is None:
                continue
            parsed_timestamp = normalize_utc(
                datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            )
            bars.append(EquityBar(timestamp=parsed_timestamp, close=to_decimal(close)))
        return bars

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
                alpaca_equities = await self._get_alpaca_equity_prices(client, equities)
                if alpaca_equities:
                    prices.update(alpaca_equities)
                    provider = "alpaca"

            if crypto:
                crypto_prices = await self._get_alpaca_crypto_prices(client, crypto)
                if crypto_prices:
                    prices.update(crypto_prices)
                    if provider is None:
                        provider = "alpaca"

        return MarketDataResult(prices=prices, provider=provider)

    async def get_equity_bars(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[EquityBar]:
        normalized_symbol = normalize_symbol(symbol)
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            return await self._get_alpaca_equity_bars(
                client,
                normalized_symbol,
                start=normalize_utc(start),
                end=normalize_utc(end),
                timeframe=timeframe,
            )
