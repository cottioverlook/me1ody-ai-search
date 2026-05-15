import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(sa.String, nullable=False, default="anonymous", index=True)
    share_id: Mapped[str] = mapped_column(sa.String, nullable=False, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, server_default=sa.func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(sa.String, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, server_default=sa.func.now())


def create_engine(database_url: str):
    return create_async_engine(database_url, echo=False)


def create_sessionmaker(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def ensure_schema_columns(engine):
    """Small SQLite-friendly migration for the prototype deployment."""

    async with engine.begin() as conn:
        def migrate(sync_conn):
            inspector = sa.inspect(sync_conn)
            if "conversations" not in inspector.get_table_names():
                return
            columns = {column["name"] for column in inspector.get_columns("conversations")}
            if "user_id" not in columns:
                sync_conn.exec_driver_sql(
                    "ALTER TABLE conversations ADD COLUMN user_id VARCHAR NOT NULL DEFAULT 'anonymous'"
                )
            if "share_id" not in columns:
                sync_conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN share_id VARCHAR")
                sync_conn.exec_driver_sql("UPDATE conversations SET share_id = id WHERE share_id IS NULL")
            if "is_favorite" not in columns:
                sync_conn.exec_driver_sql(
                    "ALTER TABLE conversations ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0"
                )

        await conn.run_sync(migrate)
