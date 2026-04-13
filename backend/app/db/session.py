from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_runtime_schema()


def _ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    has_agents_table = inspector.has_table("agents")
    agent_columns = (
        {column["name"] for column in inspector.get_columns("agents")}
        if has_agents_table
        else set()
    )
    statements: list[str] = []

    if "account_api_key_hash" not in user_columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN account_api_key_hash VARCHAR(64)"
        )
    if "account_api_key_prefix" not in user_columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN account_api_key_prefix VARCHAR(16)"
        )
    if "alpaca_paper_api_key" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN alpaca_paper_api_key TEXT")
    if "alpaca_paper_secret_key" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN alpaca_paper_secret_key TEXT")
    if "alpaca_live_api_key" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN alpaca_live_api_key TEXT")
    if "alpaca_live_secret_key" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN alpaca_live_secret_key TEXT")
    if has_agents_table and "real_money" not in agent_columns:
        statements.append(
            "ALTER TABLE agents ADD COLUMN real_money BOOLEAN DEFAULT FALSE"
        )

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_account_api_key_hash "
                "ON users (account_api_key_hash)"
            )
        )
        connection.execute(
            text(
                "UPDATE users "
                "SET alpaca_paper_api_key = alpaca_api_key, "
                "alpaca_paper_secret_key = alpaca_secret_key "
                "WHERE alpaca_base_url LIKE '%paper%' "
                "AND alpaca_paper_api_key IS NULL "
                "AND alpaca_api_key IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE users "
                "SET alpaca_live_api_key = alpaca_api_key, "
                "alpaca_live_secret_key = alpaca_secret_key "
                "WHERE alpaca_base_url NOT LIKE '%paper%' "
                "AND alpaca_live_api_key IS NULL "
                "AND alpaca_api_key IS NOT NULL"
            )
        )
        if has_agents_table:
            connection.execute(
                text(
                    "UPDATE agents "
                    "SET real_money = CASE WHEN is_paper THEN FALSE ELSE TRUE END "
                    "WHERE real_money IS NULL"
                )
            )
