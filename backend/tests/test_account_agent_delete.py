from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes import router
from app.db.session import Base, get_db
from app.models.entities import (
    ActivityEventType,
    ActivityLog,
    Agent,
    PortfolioSnapshot,
    Position,
    Trade,
    TradeSide,
    TradeStatus,
    User,
)
from app.services.security import encrypt_secret, generate_account_api_key, hash_api_key


class DummyConnectionManager:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    async def broadcast_json(self, payload: dict) -> None:
        self.payloads.append(payload)


class DummyPriceFeedService:
    def __init__(self) -> None:
        self.prices: dict[str, Decimal] = {}

    def snapshot(self) -> dict[str, Decimal]:
        return dict(self.prices)


class AccountAgentDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.engine = create_engine(
            f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

        self.app = FastAPI()
        self.app.include_router(router, prefix="/v1")
        self.app.state.connection_manager = DummyConnectionManager()
        self.app.state.price_feed_service = DummyPriceFeedService()

        def override_get_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _account_headers(self, account_api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {account_api_key}"}

    def _create_user(self, username: str) -> tuple[User, str]:
        account_api_key = generate_account_api_key()
        user = User(
            username=f"{username}-{uuid4().hex[:8]}",
            account_api_key_hash=hash_api_key(account_api_key),
            account_api_key_prefix=account_api_key[:10],
            alpaca_paper_api_key=encrypt_secret("paper-key"),
            alpaca_paper_secret_key=encrypt_secret("paper-secret"),
            alpaca_live_api_key=None,
            alpaca_live_secret_key=None,
            alpaca_api_key=encrypt_secret("paper-key"),
            alpaca_secret_key=encrypt_secret("paper-secret"),
            alpaca_base_url="https://paper-api.alpaca.markets",
        )
        with self.session_factory() as db:
            db.add(user)
            db.commit()
            db.refresh(user)
        return user, account_api_key

    def _create_agent(self, user_id: str, name: str = "Delete Me") -> Agent:
        agent = Agent(
            user_id=user_id,
            name=name,
            api_key_hash=hash_api_key(f"agent-{uuid4()}"),
            api_key_prefix=f"agent-{uuid4().hex[:4]}",
            starting_cash=Decimal("10000"),
            real_money=False,
            is_paper=True,
        )
        with self.session_factory() as db:
            db.add(agent)
            db.commit()
            db.refresh(agent)
        return agent

    def _seed_agent_state(self, agent_id: str) -> None:
        with self.session_factory() as db:
            db.add(
                Position(
                    agent_id=agent_id,
                    symbol="AAPL",
                    quantity=Decimal("1.25"),
                    avg_cost_basis=Decimal("150.00"),
                )
            )
            db.add(
                Trade(
                    agent_id=agent_id,
                    symbol="AAPL",
                    side=TradeSide.BUY,
                    amount_dollars=Decimal("187.50"),
                    quantity=Decimal("1.25"),
                    price_per_share=Decimal("150.00"),
                    filled_total=Decimal("187.50"),
                    realized_pnl=None,
                    alpaca_order_id="alpaca-123",
                    client_order_id=f"client-{uuid4().hex}",
                    rationale="Initial buy",
                    status=TradeStatus.FILLED,
                    rejection_reason=None,
                    executed_at=datetime.utcnow(),
                )
            )
            db.add(
                PortfolioSnapshot(
                    agent_id=agent_id,
                    total_value=Decimal("10150.00"),
                    cash=Decimal("9812.50"),
                    pnl=Decimal("150.00"),
                    return_pct=Decimal("1.50"),
                    snapshot_at=datetime.utcnow(),
                )
            )
            db.add(
                ActivityLog(
                    agent_id=agent_id,
                    event_type=ActivityEventType.CYCLE_SUMMARY,
                    summary="Closed the opening trade.",
                    metadata_json={"symbol": "AAPL"},
                    cost_tokens=Decimal("12.5"),
                )
            )
            db.commit()

    def test_delete_agent_success(self) -> None:
        owner, account_api_key = self._create_user("owner")
        doomed_agent = self._create_agent(owner.id, name="Delete Me")
        surviving_agent = self._create_agent(owner.id, name="Keep Me")
        self._seed_agent_state(doomed_agent.id)

        response = self.client.delete(
            f"/v1/account/agents/{doomed_agent.id}",
            headers=self._account_headers(account_api_key),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_id"], doomed_agent.id)
        self.assertEqual(response.json()["name"], "Delete Me")

        with self.session_factory() as db:
            self.assertIsNone(db.get(Agent, doomed_agent.id))
            self.assertIsNotNone(db.get(Agent, surviving_agent.id))
            self.assertEqual(
                db.scalar(
                    select(Trade).where(Trade.agent_id == doomed_agent.id).limit(1)
                ),
                None,
            )
            self.assertEqual(
                db.scalar(
                    select(Position)
                    .where(Position.agent_id == doomed_agent.id)
                    .limit(1)
                ),
                None,
            )
            self.assertEqual(
                db.scalar(
                    select(PortfolioSnapshot)
                    .where(PortfolioSnapshot.agent_id == doomed_agent.id)
                    .limit(1)
                ),
                None,
            )
            self.assertEqual(
                db.scalar(
                    select(ActivityLog)
                    .where(ActivityLog.agent_id == doomed_agent.id)
                    .limit(1)
                ),
                None,
            )

        broadcasts = self.app.state.connection_manager.payloads
        self.assertEqual(len(broadcasts), 1)
        self.assertEqual(broadcasts[0]["type"], "leaderboard_update")
        self.assertIn("Keep Me *", [entry["name"] for entry in broadcasts[0]["agents"]])
        self.assertNotIn(
            "Delete Me *", [entry["name"] for entry in broadcasts[0]["agents"]]
        )

    def test_delete_agent_returns_404_for_missing_agent(self) -> None:
        _, account_api_key = self._create_user("owner")

        response = self.client.delete(
            f"/v1/account/agents/{uuid4()}",
            headers=self._account_headers(account_api_key),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Agent not found.")
        self.assertEqual(self.app.state.connection_manager.payloads, [])

    def test_delete_agent_returns_403_for_other_accounts_agent(self) -> None:
        owner, owner_api_key = self._create_user("owner")
        other_user, _ = self._create_user("other")
        other_agent = self._create_agent(other_user.id, name="Do Not Touch")
        self._seed_agent_state(other_agent.id)

        response = self.client.delete(
            f"/v1/account/agents/{other_agent.id}",
            headers=self._account_headers(owner_api_key),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have access to this agent."
        )

        with self.session_factory() as db:
            self.assertIsNotNone(db.get(Agent, other_agent.id))
            self.assertIsNotNone(
                db.scalar(select(Trade).where(Trade.agent_id == other_agent.id).limit(1))
            )

        self.assertEqual(self.app.state.connection_manager.payloads, [])


if __name__ == "__main__":
    unittest.main()
