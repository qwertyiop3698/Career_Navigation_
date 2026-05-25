from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobRoleSkillEvidence(Base):
    __tablename__ = "job_role_skill_evidence"
    __table_args__ = (
        UniqueConstraint(
            "job_role_category",
            "skill",
            name="uq_job_role_skill_evidence_role_skill",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_role_category = Column(String(100), nullable=False, index=True)
    skill = Column(String(100), nullable=False)
    role_posting_count = Column(Integer, nullable=False)
    role_company_count = Column(Integer, nullable=False)
    keyword_posting_count = Column(Integer, nullable=False, default=0)
    model_posting_count = Column(Integer, nullable=False, default=0)
    low_confidence_model_count = Column(Integer, nullable=False, default=0)
    evidence_company_count = Column(Integer, nullable=False, default=0)
    weighted_posting_score = Column(Float, nullable=False, default=0)
    demand_share = Column(Float, nullable=False, default=0)
    company_coverage = Column(Float, nullable=False, default=0)
    market_score = Column(Float, nullable=False, default=0)
    evidence_level = Column(String(20), nullable=False)
    evidence_basis = Column(Text, nullable=False)
    calculated_at = Column(DateTime, nullable=False, default=_utcnow)
