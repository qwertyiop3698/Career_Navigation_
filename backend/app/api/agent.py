from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_optional_current_user
from app.db import get_db
from app.models import User
from app.schemas import (
    CareerPathRequest,
    CareerPathResponse,
    EvidenceDocument,
    RoadmapStep,
)
from app.services.agent_service import AgentCareerService
from app.services.roadmap_service import create_active_roadmap, serialize_roadmap

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
agent_service = AgentCareerService()


@router.post("/career-path", response_model=CareerPathResponse)
def create_career_path(
    payload: CareerPathRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    effective_user_id = current_user.id if current_user is not None else payload.user_id

    if effective_user_id is not None:
        user = db.query(User).filter(User.id == effective_user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

    try:
        result = agent_service.create_career_path(
            db=db,
            user_id=effective_user_id,
            job_role=payload.job_role,
            target_skill=payload.target_skill,
        )
        active_roadmap = create_active_roadmap(
            db=db,
            user_id=effective_user_id,
            job_target=payload.job_role,
            experience_level="Junior",
            skills=[payload.target_skill],
            goal_period=12,
        )
        serialized_roadmap = serialize_roadmap(active_roadmap)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CareerPathResponse(
        future_job=result.future_job,
        demand_probability=result.demand_probability,
        impact=result.impact,
        recommended_skills=result.recommended_skills,
        roadmap=[
            RoadmapStep(
                step=step["step"],
                title=step["title"],
                items=step["items"],
            )
            for step in result.roadmap
        ],
        evidence_documents=[
            EvidenceDocument(
                content=document["content"],
                source=document["source"],
                similarity_score=document["similarity_score"],
            )
            for document in result.evidence_documents
        ],
        roadmap_id=serialized_roadmap["id"],
        progress_percent=serialized_roadmap["progress_percent"],
        roadmap_12_weeks=serialized_roadmap["weeks"],
    )
