from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)

    users = relationship(
        "UserSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )
    jobs = relationship(
        "JobSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )
    trends = relationship("SkillTrend", back_populates="skill")


class SkillTrend(Base):
    __tablename__ = "skill_trends"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"))
    global_score = Column(Float)
    domestic_score = Column(Float)
    time_lag = Column(Integer)
    growth_rate = Column(Float)
    updated_at = Column(DateTime)

    skill = relationship("Skill", back_populates="trends")
