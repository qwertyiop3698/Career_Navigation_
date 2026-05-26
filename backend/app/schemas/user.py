from pydantic import BaseModel, Field


class SkillAssessment(BaseModel):
    name: str = Field(..., examples=["Python"])
    level: int = Field(0, ge=0, le=5, examples=[3])


class UserProfileCreate(BaseModel):
    job_target: str = Field(..., examples=["Backend Developer"])
    interest_domain: str = Field("커머스", examples=["금융"])
    experience_level: str = Field(..., examples=["Junior"])
    skills: list[str] = Field(default_factory=list, examples=[["Python", "FastAPI", "SQLAlchemy"]])
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    goal_period: int = Field(..., examples=[6])


class UserProfileResponse(BaseModel):
    user_id: str
    job_target: str
    interest_domain: str
    experience_level: str
    skills: list[str]
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    goal_period: int
    status: str


class GithubProfileUpdate(BaseModel):
    github_url: str | None = Field(None, max_length=300, examples=["https://github.com/username"])


class GithubProfileResponse(BaseModel):
    github_url: str | None = None
    status: str
