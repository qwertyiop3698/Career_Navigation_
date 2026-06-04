import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.data_collection import legacy_router as legacy_data_collection_router
from app.api.data_collection import admin_router as admin_data_collection_router
from app.api.data_collection import router as data_collection_router
from app.api.job import router as jobs_router
from app.api.model import router as model_router
from app.api.project import router as project_router
from app.api.rag import admin_router as admin_rag_router
from app.api.rag import router as rag_router
from app.api.roadmap import router as roadmaps_router
from app.api.trend import admin_router as admin_trends_router
from app.api.trend import router as trends_router
from app.api.v1.external_jobs import admin_router as admin_external_jobs_router
from app.api.v1.external_jobs import router as external_jobs_router
from app.api.v1.users import router as users_router
from app.db import Base, engine
from app.services.external_jobs.scheduler import (
    start_external_jobs_scheduler,
    stop_external_jobs_scheduler,
)

_ = models
logger = logging.getLogger(__name__)

app = FastAPI(title="Career Navigation AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(admin_data_collection_router)
app.include_router(admin_external_jobs_router)
app.include_router(admin_rag_router)
app.include_router(admin_trends_router)
app.include_router(data_collection_router)
app.include_router(legacy_data_collection_router)
app.include_router(jobs_router)
app.include_router(model_router)
app.include_router(project_router)
app.include_router(rag_router)
app.include_router(roadmaps_router)
app.include_router(trends_router)
app.include_router(external_jobs_router)
app.include_router(users_router)


@app.on_event("startup")
def initialize_database():
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(bind=engine)
        _ensure_mvp_columns()
        start_external_jobs_scheduler()
    except Exception:
        logger.exception("Failed to initialize database tables")
        raise


@app.on_event("shutdown")
def shutdown_background_workers():
    stop_external_jobs_scheduler()


def _ensure_mvp_columns():
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS github_url TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS interest_domain TEXT",
        "ALTER TABLE user_skills ADD COLUMN IF NOT EXISTS proficiency_level INTEGER DEFAULT 0",
        "ALTER TABLE user_skills ADD COLUMN IF NOT EXISTS evidence_note TEXT",
        "ALTER TABLE user_skills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "UPDATE users SET role = COALESCE(role, 'user')",
        "ALTER TABLE users ALTER COLUMN role SET NOT NULL",
        "UPDATE user_skills SET proficiency_level = COALESCE(proficiency_level, 0)",
        "ALTER TABLE user_skills ALTER COLUMN proficiency_level SET NOT NULL",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS job_target TEXT",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS experience_level TEXT",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS goal_period INTEGER DEFAULT 12",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "UPDATE roadmaps SET job_target = COALESCE(job_target, 'AI Backend Developer')",
        "UPDATE roadmaps SET progress_percent = COALESCE(progress_percent, 0)",
        "UPDATE roadmaps SET is_active = COALESCE(is_active, TRUE)",
        "ALTER TABLE roadmaps ALTER COLUMN job_target SET NOT NULL",
        "ALTER TABLE roadmaps ALTER COLUMN progress_percent SET NOT NULL",
        "ALTER TABLE roadmaps ALTER COLUMN is_active SET NOT NULL",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


@app.get("/")
def read_root():
    return {"message": "FastAPI + SQLAlchemy server is running"}


@app.get("/health")
def health_check():
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return {"status": "ok", "database": "connected"}
