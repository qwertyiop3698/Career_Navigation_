import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, index=True)
    nickname = Column(Text)
    password_hash = Column(Text)
    job_target = Column(Text)
    experience_level = Column(Text)
    goal_period = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    skills = relationship(
        "UserSkill",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    predictions = relationship("Prediction", back_populates="user")
    roadmaps = relationship("Roadmap", back_populates="user")


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    proficiency_level = Column(Integer, nullable=False, default=0)
    evidence_note = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="users")
