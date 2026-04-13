import json
from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bridgewood Agent Trading Leaderboard"
    api_v1_prefix: str = "/v1"
    database_url: str = "sqlite:///./bridgewood.db"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    admin_token: str = "bridgewood-admin-token"
    fernet_key: str = "p63UvtXx1b9s_9g9qxGzbXClSH6sF8RClbQfmykUKQ8="
    mock_broker_mode: bool = True
    price_refresh_seconds: int = 15
    snapshot_interval_minutes: int = 5
    order_fill_timeout_seconds: int = 20
    order_fill_poll_seconds: float = 1.0
    alpaca_data_url: str = "https://data.alpaca.markets"
    alpaca_sandbox_data_url: str = "https://data.sandbox.alpaca.markets"
    alpaca_equity_feed: str = "iex"
    benchmark_symbol: str = "SPY"
    benchmark_starting_cash: float = 10000.0
    activity_page_size: int = 30

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            raise TypeError("cors_origins must be a list or string.")

        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("cors_origins JSON must decode to a list.")
            return [str(item).strip() for item in parsed if str(item).strip()]

        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
