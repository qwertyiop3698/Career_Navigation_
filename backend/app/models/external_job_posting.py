from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExternalJobPosting(Base):
    __tablename__ = "external_job_postings"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_external_job_postings_source_external_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    job_url = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=True)
    skills = Column(JSONB, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    collected_at = Column(DateTime, nullable=False, default=_utcnow)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
