from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base


class ProjectSubmission(Base):
    __tablename__ = "project_submissions"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "cycle_index", name="uq_project_submission_cycle"),
    )

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(
        Integer,
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    cycle_index = Column(Integer, nullable=False)
    project_title = Column(Text, nullable=False)
    job_target = Column(Text, nullable=False)
    github_url = Column(Text)
    problem_statement = Column(Text, nullable=False)
    data_description = Column(Text, nullable=False)
    skills_used = Column(JSONB, nullable=False, default=list)
    methods_used = Column(JSONB, nullable=False, default=list)
    metrics_used = Column(JSONB, nullable=False, default=list)
    result_summary = Column(Text, nullable=False)
    improvement_notes = Column(Text, nullable=False)
    readme_text = Column(Text)
    execution_url = Column(Text)
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    roadmap = relationship("Roadmap", back_populates="project_submissions")
    evaluation = relationship(
        "ProjectEvaluation",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ProjectEvaluation(Base):
    __tablename__ = "project_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer,
        ForeignKey("project_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rule_score = Column(Integer, nullable=False, default=0)
    project_evidence_points = Column(Integer, nullable=False, default=0)
    status = Column(Text, nullable=False)
    score_breakdown = Column(JSONB, nullable=False, default=dict)
    passed_checks = Column(JSONB, nullable=False, default=list)
    missing_checks = Column(JSONB, nullable=False, default=list)
    critical_issues = Column(JSONB, nullable=False, default=list)
    ai_review = Column(JSONB)
    ai_model = Column(Text)
    ai_input_tokens = Column(Integer)
    ai_output_tokens = Column(Integer)
    ai_estimated_cost_usd = Column(Float)
    ai_reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    submission = relationship("ProjectSubmission", back_populates="evaluation")
