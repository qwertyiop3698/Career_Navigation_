import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("AUTH_TOKEN_SECRET", "test-auth-token-secret")

from app.api import auth as auth_api
from app.api import rag as rag_api
from app.api.security import require_admin_or_internal_api_key
from app.core.logging import mask_sensitive_payload
from app.db import get_db
from app.main import app
from app.schemas.auth import SignupRequest
from app.schemas.rag import DocumentCreate, RagQueryRequest
from app.schemas.user import UserProfileCreate


class FakeDb:
    def __init__(self, user=None):
        self.user = user
        self.committed = False
        self.refreshed = None

    def query(self, model):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.user

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def refresh(self, item):
        self.refreshed = item


def make_user(role="user"):
    return SimpleNamespace(id=uuid4(), role=role, email=f"{role}@example.com")


def make_token(user):
    return auth_api.create_access_token(str(user.id))


@pytest.fixture(autouse=True)
def clean_overrides(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def override_db(user=None):
    fake_db = FakeDb(user=user)

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _get_db
    return fake_db


def auth_headers(user):
    return {"Authorization": f"Bearer {make_token(user)}"}


def test_internal_api_key_missing_or_blank_does_not_bypass_auth(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    with pytest.raises(Exception) as missing_exc:
        require_admin_or_internal_api_key(x_internal_api_key="anything", db=FakeDb())
    assert getattr(missing_exc.value, "status_code", None) == 401

    monkeypatch.setenv("INTERNAL_API_KEY", "")
    with pytest.raises(Exception) as empty_exc:
        require_admin_or_internal_api_key(x_internal_api_key="", db=FakeDb())
    assert getattr(empty_exc.value, "status_code", None) == 401

    monkeypatch.setenv("INTERNAL_API_KEY", "   ")
    with pytest.raises(Exception) as blank_exc:
        require_admin_or_internal_api_key(x_internal_api_key="   ", db=FakeDb())
    assert getattr(blank_exc.value, "status_code", None) == 401


def test_user_controlled_payloads_do_not_accept_or_expose_role_admin():
    payload = SignupRequest(
        name="User",
        email="user@example.com",
        password="password123",
        role="admin",
    )
    dumped = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    assert "role" not in dumped

    profile = UserProfileCreate(
        job_target="Backend Developer",
        interest_domain="finance",
        experience_level="Junior",
        skills=["Python"],
        goal_period=6,
        role="admin",
    )
    profile_dumped = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
    assert "role" not in profile_dumped


def test_admin_api_rejects_unauthenticated_requests(client):
    override_db()
    response = client.post(
        "/api/v1/admin/trends",
        json={
            "skill_name": "Python",
            "global_score": 1.0,
            "domestic_score": 1.0,
            "time_lag": 0,
            "growth_rate": 0.0,
        },
    )
    assert response.status_code == 401


def test_admin_api_rejects_regular_user_token_with_403(client):
    user = make_user(role="user")
    override_db(user=user)
    response = client.post(
        "/api/v1/admin/trends",
        headers=auth_headers(user),
        json={
            "skill_name": "Python",
            "global_score": 1.0,
            "domestic_score": 1.0,
            "time_lag": 0,
            "growth_rate": 0.0,
        },
    )
    assert response.status_code == 403


def test_rag_query_requires_login(client, monkeypatch):
    override_db()
    monkeypatch.setattr(rag_api.rag_service, "search_documents", lambda **kwargs: [])

    anonymous = client.post("/api/v1/rag/query", json={"query": "Python", "top_k": 1})
    assert anonymous.status_code == 401

    user = make_user(role="user")
    override_db(user=user)
    authenticated = client.post(
        "/api/v1/rag/query",
        headers=auth_headers(user),
        json={"query": "Python", "top_k": 1},
    )
    assert authenticated.status_code == 200


def test_rag_validation_limits_are_enforced_by_pydantic():
    with pytest.raises(ValidationError):
        RagQueryRequest(query="valid", top_k=21)
    with pytest.raises(ValidationError):
        RagQueryRequest(query="x" * 1001, top_k=1)
    with pytest.raises(ValidationError):
        DocumentCreate(content="x" * 20001, source="manual")
    with pytest.raises(ValidationError):
        DocumentCreate(content="valid", source="manual", metadata={"blob": "x" * 4001})


def test_existing_rag_documents_path_requires_admin_or_internal_key(client, monkeypatch):
    override_db()

    anonymous = client.post(
        "/api/v1/rag/documents",
        json={"content": "doc", "source": "manual"},
    )
    assert anonymous.status_code == 401

    user = make_user(role="user")
    override_db(user=user)
    regular_user = client.post(
        "/api/v1/rag/documents",
        headers=auth_headers(user),
        json={"content": "doc", "source": "manual"},
    )
    assert regular_user.status_code == 403

    monkeypatch.setenv("INTERNAL_API_KEY", "collector-secret")
    monkeypatch.setattr(
        rag_api.rag_service,
        "create_document",
        lambda **kwargs: SimpleNamespace(id=1, source=kwargs["source"]),
    )
    allowed = client.post(
        "/api/v1/rag/documents",
        headers={"X-Internal-Api-Key": "collector-secret"},
        json={"content": "doc", "source": "manual"},
    )
    assert allowed.status_code == 201


def test_log_masking_covers_email_tokens_passwords_readme_and_github_url():
    masked = mask_sensitive_payload(
        {
            "email": "user@example.com",
            "password": "password123",
            "access_token": "token",
            "github_url": "https://github.com/user/repo",
            "readme_text": "private readme",
            "nested": {"token": "nested-token"},
        }
    )
    assert masked["email"] == "***MASKED***"
    assert masked["password"] == "***MASKED***"
    assert masked["access_token"] == "***MASKED***"
    assert masked["github_url"] == "***MASKED***"
    assert masked["readme_text"] == "***MASKED***"
    assert masked["nested"]["token"] == "***MASKED***"


def test_missing_auth_token_secret_has_clear_startup_error(monkeypatch):
    monkeypatch.delenv("AUTH_TOKEN_SECRET", raising=False)
    original_secret = auth_api.TOKEN_SECRET
    try:
        with pytest.raises(RuntimeError, match="Set it in .env or the deployment environment"):
            importlib.reload(auth_api)
    finally:
        monkeypatch.setenv("AUTH_TOKEN_SECRET", original_secret)
        importlib.reload(auth_api)
