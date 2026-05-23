from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    source = Column(Text)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, server_default=func.now())

    embeddings = relationship(
        "Embedding",
        back_populates="document",
        cascade="all, delete-orphan",
    )
