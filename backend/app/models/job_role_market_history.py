from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, UniqueConstraint

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobRoleMarketHistory(Base):
    __tablename__ = "job_role_market_history"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "country",
            "job_role_category",
            "query_term",
            "metric",
            "period_month",
            name="uq_job_role_market_history_series_month",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)
    country = Column(String(10), nullable=False)
    job_role_category = Column(String(100), nullable=False, index=True)
    query_term = Column(String(200), nullable=False)
    metric = Column(String(50), nullable=False)
    period_month = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)
    granularity = Column(String(20), nullable=False, default="month")
    limitation_note = Column(Text, nullable=True)
    collected_at = Column(DateTime, nullable=False, default=_utcnow)
