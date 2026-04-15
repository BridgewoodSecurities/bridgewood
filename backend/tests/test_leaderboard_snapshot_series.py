# ruff: noqa: E402

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import Base
from app.models.entities import Agent, PortfolioSnapshot, TradingMode, User
from app.services.leaderboard import build_snapshot_series
from app.services.security import hash_api_key


class LeaderboardSnapshotSeriesTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _create_user(self) -> User:
        user = User(
            username=f"user-{uuid4().hex[:8]}",
            account_api_key_hash=hash_api_key(f"account-{uuid4()}"),
            account_api_key_prefix=f"acct-{uuid4().hex[:4]}",
        )
        with self.session_factory() as db:
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def _create_agent(self, user_id: str, *, name: str, created_at: datetime) -> Agent:
        agent = Agent(
            user_id=user_id,
            name=name,
            api_key_hash=hash_api_key(f"agent-{uuid4()}"),
            api_key_prefix=f"agent-{uuid4().hex[:4]}",
            starting_cash=Decimal("10000"),
            trading_mode=TradingMode.PAPER,
            created_at=created_at,
        )
        with self.session_factory() as db:
            db.add(agent)
            db.commit()
            db.refresh(agent)
        return agent

    def test_new_agent_without_snapshots_gets_baseline_point_in_daily_range(
        self,
    ) -> None:
        now = datetime(2026, 4, 15, 12, 53, tzinfo=timezone.utc)
        user = self._create_user()
        created_at = now - timedelta(hours=4)
        agent = self._create_agent(user.id, name="TradingBot", created_at=created_at)

        with self.session_factory() as db:
            with patch("app.services.leaderboard.utc_now", return_value=now):
                points = build_snapshot_series(db, "1D")

        agent_points = [point for point in points if point.agent_id == agent.id]
        self.assertEqual(len(agent_points), 1)
        self.assertEqual(agent_points[0].snapshot_at, created_at)
        self.assertEqual(agent_points[0].return_pct, 0.0)
        self.assertEqual(agent_points[0].total_value, 10000.0)

    def test_new_agent_series_starts_at_creation_before_first_snapshot(self) -> None:
        now = datetime(2026, 4, 15, 12, 53, tzinfo=timezone.utc)
        user = self._create_user()
        created_at = now - timedelta(hours=5)
        first_snapshot_at = now - timedelta(hours=2)
        agent = self._create_agent(user.id, name="House Bot", created_at=created_at)

        with self.session_factory() as db:
            db.add(
                PortfolioSnapshot(
                    agent_id=agent.id,
                    total_value=Decimal("10000"),
                    cash=Decimal("10000"),
                    pnl=Decimal("0"),
                    return_pct=Decimal("0"),
                    snapshot_at=first_snapshot_at,
                )
            )
            db.commit()

        with self.session_factory() as db:
            with patch("app.services.leaderboard.utc_now", return_value=now):
                points = build_snapshot_series(db, "1D")

        agent_points = [point for point in points if point.agent_id == agent.id]
        self.assertEqual(len(agent_points), 2)
        self.assertEqual(agent_points[0].snapshot_at, created_at)
        self.assertEqual(agent_points[0].return_pct, 0.0)
        self.assertEqual(agent_points[1].snapshot_at, first_snapshot_at)


if __name__ == "__main__":
    unittest.main()
