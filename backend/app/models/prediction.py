from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    job_role = Column(Text)
    probability = Column(Float)
    diffusion_time = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="predictions")
