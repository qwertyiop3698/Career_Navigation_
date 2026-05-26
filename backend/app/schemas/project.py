from pydantic import BaseModel, Field

from app.schemas.roadmap import RoadmapResponse


class ProjectSubmissionCreate(BaseModel):
    cycle_index: int = Field(..., ge=1, le=2)
    github_url: str | None = None
    problem_statement: str = Field(..., min_length=10, max_length=4000)
    data_description: str = Field(..., min_length=5, max_length=3000)
    skills_used: list[str] = Field(default_factory=list, max_length=20)
    methods_used: list[str] = Field(default_factory=list, max_length=20)
    metrics_used: list[str] = Field(default_factory=list, max_length=20)
    result_summary: str = Field(..., min_length=5, max_length=5000)
    improvement_notes: str = Field(..., min_length=5, max_length=4000)
    readme_text: str | None = Field(None, max_length=12000)
    execution_url: str | None = None


class ProjectEvaluationResponse(BaseModel):
    id: int
    rule_score: int
    project_evidence_points: int
    status: str
    score_breakdown: dict = Field(default_factory=dict)
    passed_checks: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    ai_review: dict | None = None
    ai_model: str | None = None
    ai_estimated_cost_usd: float | None = None


class ProjectSubmissionResponse(BaseModel):
    id: int
    cycle_index: int
    project_title: str
    github_url: str | None = None
    submitted_at: str | None = None
    evaluation: ProjectEvaluationResponse


class ProjectSubmissionResult(BaseModel):
    submission: ProjectSubmissionResponse
    roadmap: RoadmapResponse
