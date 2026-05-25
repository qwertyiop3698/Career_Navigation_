from pydantic import BaseModel, Field


class SkillTrendCreate(BaseModel):
    skill_name: str = Field(..., examples=["Python"])
    global_score: float = Field(..., examples=[92.5])
    domestic_score: float = Field(..., examples=[88.0])
    time_lag: int = Field(..., examples=[2])
    growth_rate: float = Field(..., examples=[13.4])


class SkillTrendResponse(BaseModel):
    skill_name: str
    global_score: float
    domestic_score: float
    time_lag: int
    growth_rate: float


class SkillTrendCreateResponse(SkillTrendResponse):
    status: str


class JobRoleSkillEvidenceResponse(BaseModel):
    job_role_category: str
    skill: str
    role_posting_count: int
    role_company_count: int
    keyword_posting_count: int
    model_posting_count: int
    low_confidence_model_count: int
    evidence_company_count: int
    weighted_posting_score: float
    demand_share: float
    company_coverage: float
    market_score: float
    evidence_level: str
    evidence_basis: str


class JobRoleMarketHistoryResponse(BaseModel):
    source: str
    country: str
    job_role_category: str
    query_term: str
    metric: str
    period_month: str
    value: float
    granularity: str
    limitation_note: str | None = None
