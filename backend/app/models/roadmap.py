from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    job_target = Column(Text, nullable=False)
    experience_level = Column(Text)
    goal_period = Column(Integer, default=12)
    progress_percent = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    content = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="roadmaps")
    weeks = relationship(
        "RoadmapWeek",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapWeek.week_number",
    )


class RoadmapWeek(Base):
    __tablename__ = "roadmap_weeks"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(
        Integer,
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_number = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    goal = Column(Text)

    roadmap = relationship("Roadmap", back_populates="weeks")
    tasks = relationship(
        "RoadmapTask",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="RoadmapTask.id",
    )


class RoadmapTask(Base):
    __tablename__ = "roadmap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    week_id = Column(
        Integer,
        ForeignKey("roadmap_weeks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_title = Column(Text, nullable=False)
    task_type = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime)

    week = relationship("RoadmapWeek", back_populates="tasks")
