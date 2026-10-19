import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Monitor(Base):
    __tablename__ = "monitors"
    __table_args__ = (
        CheckConstraint("interval_seconds BETWEEN 30 AND 3600"),
        CheckConstraint("timeout_seconds BETWEEN 0.1 AND 120"),
        CheckConstraint("expected_status BETWEEN 100 AND 599"),
        CheckConstraint("failure_threshold BETWEEN 1 AND 10"),
        CheckConstraint("state IN ('UNKNOWN','UP','DOWN','PAUSED')"),
        CheckConstraint("consecutive_failures >= 0"),
        CheckConstraint("config_version >= 1"),
        CheckConstraint("(lease_token IS NULL) = (lease_until IS NULL)"),
        Index("ix_monitors_next_due_at", "next_due_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(2048))
    interval_seconds: Mapped[int] = mapped_column(default=30)
    timeout_seconds: Mapped[float] = mapped_column(default=5.0)
    expected_status: Mapped[int] = mapped_column(default=200)
    expected_body: Mapped[str | None] = mapped_column(String(1000))
    failure_threshold: Mapped[int] = mapped_column(default=2)
    state: Mapped[str] = mapped_column(String(10), default="UNKNOWN")
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status_code: Mapped[int | None]
    last_response_ms: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config_version: Mapped[int] = mapped_column(default=1, server_default="1")
    run_requested: Mapped[bool] = mapped_column(default=False, server_default="false")

    @property
    def is_running(self):
        return bool(self.lease_until and self.lease_until > now())


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_results_monitor_time", "monitor_id", "checked_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    monitor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    success: Mapped[bool]
    status_code: Mapped[int | None]
    response_ms: Mapped[float]
    error: Mapped[str | None] = mapped_column(Text)
    config_version: Mapped[int] = mapped_column(default=1, server_default="1")


class MonitorGroup(Base):
    __tablename__ = "monitor_groups"
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    monitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (CheckConstraint("config_version >= 1"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    config_version: Mapped[int] = mapped_column(default=1, server_default="1")


class GroupRecipient(Base):
    __tablename__ = "group_recipients"
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(254), primary_key=True)
