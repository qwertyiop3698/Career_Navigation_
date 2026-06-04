from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.security import require_admin_or_internal_api_key
from app.db import get_db
from app.models import User
from app.schemas import (
    DocumentCreate,
    DocumentCreateResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagQueryResult,
)
from app.services.rag_service import RagService

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
admin_router = APIRouter(prefix="/api/v1/admin/rag", tags=["admin-rag"])
rag_service = RagService()


@admin_router.post(
    "/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    _: User | None = Depends(require_admin_or_internal_api_key),
):
    try:
        document = rag_service.create_document(
            db=db,
            content=payload.content,
            source=payload.source,
            metadata=payload.metadata,
        )
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise

    return DocumentCreateResponse(
        document_id=document.id,
        source=document.source,
        status="created",
    )


@router.post("/query", response_model=RagQueryResponse)
def query_documents(
    payload: RagQueryRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    results = rag_service.search_documents(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
    )

    return RagQueryResponse(
        results=[
            RagQueryResult(
                content=result["content"],
                source=result["source"],
                similarity_score=result["similarity_score"],
            )
            for result in results
        ]
    )
