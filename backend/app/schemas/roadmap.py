from pydantic import BaseModel, Field

from app.schemas.user import SkillAssessment


class RoadmapCreateRequest(BaseModel):
    job_target: str = Field(..., examples=["AI Backend Developer"])
    experience_level: str = Field("Junior", examples=["Junior"])
    skills: list[str] = Field(default_factory=list, examples=[["Python", "SQL", "FastAPI"]])
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    goal_period: int = Field(12, examples=[12])


class RoadmapTaskResponse(BaseModel):
    id: int
    task_title: str
    task_type: str
    is_completed: bool
    completed_at: str | None = None


class RoadmapWeekResponse(BaseModel):
    id: int
    week_number: int
    title: str
    goal: str | None = None
    tasks: list[RoadmapTaskResponse]


class RoadmapResponse(BaseModel):
    id: int
    user_id: str
    job_target: str
    experience_level: str | None = None
    goal_period: int | None = None
    progress_percent: int
    is_active: bool
    current_skills: list[str] = Field(default_factory=list)
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    covered_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    readiness_score: int = 0
    capability_score: int = 0
    project_evidence_score: int = 0
    application_readiness_score: int = 0
    cycles: list[dict] = Field(default_factory=list)
    evidence_summary: list[dict] = Field(default_factory=list)
    evidence_note: str | None = None
    weeks: list[RoadmapWeekResponse]


class ActiveRoadmapResponse(BaseModel):
    roadmap: RoadmapResponse | None = None
    message: str | None = None


class ToggleTaskResponse(BaseModel):
    roadmap_id: int
    task_id: int
    is_completed: bool
    progress_percent: int
    completed_count: int
    total_count: int
    readiness_score: int = 0
    capability_score: int = 0
    project_evidence_score: int = 0
    application_readiness_score: int = 0


class RoadmapProgressResponse(BaseModel):
    roadmap_id: int | None = None
    progress_percent: int
    completed_count: int
    total_count: int
    message: str | None = None
