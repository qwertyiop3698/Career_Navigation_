from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    DocumentCreate,
    DocumentCreateResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagQueryResult,
)
from app.services.rag_service import RagService

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
rag_service = RagService()


@router.post(
    "/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
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
