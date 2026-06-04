import json
from typing import Any

from pydantic import BaseModel, Field, validator


MAX_RAG_CONTENT_LENGTH = 20_000
MAX_RAG_METADATA_JSON_LENGTH = 4_000
MAX_RAG_QUERY_LENGTH = 1_000
MAX_RAG_SOURCE_LENGTH = 200


class DocumentCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_RAG_CONTENT_LENGTH,
        examples=["FastAPI is a Python web framework."],
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=MAX_RAG_SOURCE_LENGTH,
        examples=["internal_notes"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        examples=[{"category": "backend", "language": "python"}],
    )

    @validator("metadata")
    def metadata_must_be_bounded(cls, value):
        if value is None:
            return value
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        if len(serialized) > MAX_RAG_METADATA_JSON_LENGTH:
            raise ValueError("metadata is too large.")
        return value


class DocumentCreateResponse(BaseModel):
    document_id: int
    source: str
    status: str


class RagQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_RAG_QUERY_LENGTH,
        examples=["What skills are useful for backend APIs?"],
    )
    top_k: int = Field(default=5, ge=1, le=20, examples=[5])


class RagQueryResult(BaseModel):
    content: str
    source: str
    similarity_score: float


class RagQueryResponse(BaseModel):
    results: list[RagQueryResult]
