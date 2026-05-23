from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    company: str = Field(..., examples=["OpenAI"])
    title: str = Field(..., examples=["Backend Developer"])
    description: str = Field(..., examples=["Build scalable APIs with Python."])
    source: str = Field(..., examples=["company_careers"])
    skills: list[str] = Field(..., examples=[["Python", "FastAPI", "PostgreSQL"]])


class JobResponse(BaseModel):
    job_id: int
    company: str
    title: str
    source: str
    skills: list[str]
    status: str
