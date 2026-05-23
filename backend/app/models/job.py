from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(Text)
    title = Column(Text)
    description = Column(Text)
    source = Column(Text)
    created_at = Column(DateTime)

    skills = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer,
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )

    job = relationship("JobPosting", back_populates="skills")
    skill = relationship("Skill", back_populates="jobs")
