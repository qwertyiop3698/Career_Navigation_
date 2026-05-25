from uuid import UUID

from pydantic import BaseModel, Field


class CareerPathRequest(BaseModel):
    user_id: UUID | None = Field(None, examples=["6f4f312e-6d74-4e03-aecd-29e8ee4d6832"])
    job_role: str = Field(..., examples=["AI Backend Developer"])
    target_skill: str = Field(..., examples=["RAG"])
    skill_assessments: list[dict] = Field(default_factory=list)


class RoadmapStep(BaseModel):
    step: int
    title: str
    items: list[str]


class EvidenceDocument(BaseModel):
    content: str
    source: str
    similarity_score: float


class CareerPathRoadmapTask(BaseModel):
    id: int
    task_title: str
    task_type: str
    is_completed: bool
    completed_at: str | None = None


class CareerPathRoadmapWeek(BaseModel):
    id: int
    week_number: int
    title: str
    goal: str | None = None
    tasks: list[CareerPathRoadmapTask]


class CareerPathResponse(BaseModel):
    future_job: str
    demand_probability: float
    impact: str
    recommended_skills: list[str]
    roadmap: list[RoadmapStep]
    evidence_documents: list[EvidenceDocument]
    roadmap_id: int | None = None
    progress_percent: int = 0
    roadmap_12_weeks: list[CareerPathRoadmapWeek] = []
    current_skills: list[str] = Field(default_factory=list)
    skill_assessments: list[dict] = Field(default_factory=list)
    covered_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommended_projects: list[str] = Field(default_factory=list)
    evidence_summary: list[dict] = Field(default_factory=list)
    cycles: list[dict] = Field(default_factory=list)
    summary: str | None = None
    readiness_score: int = 0
    capability_score: int = 0
    project_evidence_score: int = 0
    application_readiness_score: int = 0
