from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TradeIntent(APIModel):
    symbol: str
    side: Literal["buy", "sell"]
    amount_dollars: float = Field(gt=0)
    client_order_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class TradeSubmissionRequest(APIModel):
    trades: list[TradeIntent] = Field(min_length=1)
    rationale: str | None = None
    cycle_cost: float | None = Field(default=None, ge=0)


class TradeResult(APIModel):
    client_order_id: str
    status: str
    symbol: str
    side: str
    quantity: float | None = None
    price_per_share: float | None = None
    total: float | None = None
    rejection_reason: str | None = None


class PositionView(APIModel):
    symbol: str
    quantity: float
    market_value: float
    avg_cost: float


class PortfolioView(APIModel):
    agent_id: str
    cash: float
    total_value: float
    pnl: float
    return_pct: float
    positions: list[PositionView]


class TradeSubmissionResponse(APIModel):
    results: list[TradeResult]
    portfolio_after: PortfolioView


class UserCreateRequest(APIModel):
    username: str
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str


class UserCreateResponse(APIModel):
    user_id: str
    username: str
    alpaca_base_url: str


class AgentCreateRequest(APIModel):
    user_id: str
    name: str
    starting_cash: float = Field(gt=0)
    icon_url: str | None = None


class AgentCreateResponse(APIModel):
    agent_id: str
    name: str
    api_key: str
    is_paper: bool


class PricesResponse(APIModel):
    prices: dict[str, float]
    as_of: datetime


class SnapshotPoint(APIModel):
    agent_id: str
    name: str
    total_value: float
    snapshot_at: datetime
    is_benchmark: bool = False
    icon_url: str | None = None


class ActivityItem(APIModel):
    id: int
    agent_id: str
    agent_name: str
    icon_url: str | None = None
    event_type: str
    summary: str
    metadata: dict
    cost_tokens: float | None = None
    created_at: datetime


class LeaderboardEntry(APIModel):
    id: str
    name: str
    icon_url: str | None = None
    cash: float
    total_value: float
    pnl: float
    return_pct: float
    sharpe: float
    max_win: float
    max_loss: float
    trade_count: int
    is_benchmark: bool = False
    daily_change_pct: float = 0.0


class LeaderboardPayload(APIModel):
    type: str = "leaderboard_update"
    agents: list[LeaderboardEntry]
    timestamp: datetime


class ActivityPayload(APIModel):
    type: str = "activity"
    agent_id: str
    agent_name: str
    icon_url: str | None = None
    summary: str
    cost_tokens: float | None = None
    timestamp: datetime


class DashboardBootstrap(APIModel):
    leaderboard: LeaderboardPayload
    activity: list[ActivityItem]
    snapshots: list[SnapshotPoint]
    range: str


SnapshotRange = Literal["1D", "1W", "1M", "ALL"]
