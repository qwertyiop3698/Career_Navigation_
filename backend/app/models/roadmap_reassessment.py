from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base


class RoadmapReassessment(Base):
    __tablename__ = "roadmap_reassessments"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "checkpoint_week", name="uq_roadmap_checkpoint_week"),
    )

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(
        Integer,
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    checkpoint_week = Column(Integer, nullable=False)
    previous_assessments = Column(JSONB, nullable=False)
    updated_assessments = Column(JSONB, nullable=False)
    previous_diagnostics = Column(JSONB, nullable=False)
    updated_diagnostics = Column(JSONB, nullable=False)
    capability_score_before = Column(Integer, nullable=False)
    capability_score_after = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    roadmap = relationship("Roadmap", back_populates="reassessments")
