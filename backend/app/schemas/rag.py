from typing import Any

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    content: str = Field(..., examples=["FastAPI is a Python web framework."])
    source: str = Field(..., examples=["internal_notes"])
    metadata: dict[str, Any] | None = Field(
        default=None,
        examples=[{"category": "backend", "language": "python"}],
    )


class DocumentCreateResponse(BaseModel):
    document_id: int
    source: str
    status: str


class RagQueryRequest(BaseModel):
    query: str = Field(..., examples=["What skills are useful for backend APIs?"])
    top_k: int = Field(default=5, ge=1, le=20, examples=[5])


class RagQueryResult(BaseModel):
    content: str
    source: str
    similarity_score: float


class RagQueryResponse(BaseModel):
    results: list[RagQueryResult]
