from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import (
    CareerPathRequest,
    CareerPathResponse,
    RoadmapStep,
)
from app.services.roadmap_service import create_active_roadmap, serialize_roadmap

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/career-path", response_model=CareerPathResponse)
def create_career_path(
    payload: CareerPathRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_user_id = current_user.id
    user = current_user

    try:
        stored_assessments = [
            {
                "name": user_skill.skill.name,
                "level": user_skill.proficiency_level or 0,
            }
            for user_skill in user.skills
        ]
        skill_assessments = (
            [
                {"name": assessment.name, "level": assessment.level}
                for assessment in payload.skill_assessments
            ]
            if payload.skill_assessments
            else stored_assessments
        )
        current_skills = [
            assessment["name"]
            for assessment in skill_assessments
            if assessment["level"] > 0
        ]
        active_roadmap = create_active_roadmap(
            db=db,
            user_id=effective_user_id,
            job_target=payload.job_role,
            interest_domain=payload.interest_domain,
            experience_level="Junior",
            skills=current_skills,
            skill_assessments=skill_assessments,
            goal_period=12,
        )
        serialized_roadmap = serialize_roadmap(active_roadmap)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CareerPathResponse(
        future_job=serialized_roadmap["job_target"],
        interest_domain=serialized_roadmap["interest_domain"],
        demand_probability=0.0,
        impact="취업 결과 예측이 아니라 현재 공고 근거를 활용한 지원 준비 로드맵입니다.",
        recommended_skills=serialized_roadmap["recommended_skills"],
        roadmap=[
            RoadmapStep(
                step=index,
                title=cycle["title"],
                items=cycle["skills"],
            )
            for index, cycle in enumerate(serialized_roadmap["cycles"], start=1)
        ],
        evidence_documents=[],
        roadmap_id=serialized_roadmap["id"],
        progress_percent=serialized_roadmap["progress_percent"],
        roadmap_12_weeks=serialized_roadmap["weeks"],
        current_skills=serialized_roadmap["current_skills"],
        skill_assessments=serialized_roadmap["skill_assessments"],
        covered_skills=serialized_roadmap["covered_skills"],
        missing_skills=serialized_roadmap["missing_skills"],
        recommended_projects=[
            cycle["project"] for cycle in serialized_roadmap["cycles"]
        ],
        project_blueprints=serialized_roadmap["project_blueprints"],
        evidence_summary=serialized_roadmap["evidence_summary"],
        skill_diagnostics=serialized_roadmap["skill_diagnostics"],
        cycles=serialized_roadmap["cycles"],
        readiness_score=serialized_roadmap["readiness_score"],
        capability_score=serialized_roadmap["capability_score"],
        project_evidence_score=serialized_roadmap["project_evidence_score"],
        application_readiness_score=serialized_roadmap["application_readiness_score"],
        summary=(
            "현재 여러 회사의 공고에서 반복되는 부족 역량을 우선 선정하고, "
            "두 개의 실무 프로젝트로 묶은 12주 준비 계획입니다."
        ),
    )
