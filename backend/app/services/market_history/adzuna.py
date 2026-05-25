from __future__ import annotations

from datetime import date, datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.core.config import get_env
from app.models import JobRoleMarketHistory


ADZUNA_HISTORY_URL = "https://api.adzuna.com/v1/api/jobs/{country}/history"
REQUEST_TIMEOUT_SECONDS = 30
SOURCE = "adzuna"
METRIC = "average_salary"
LIMITATION_NOTE = (
    "Adzuna standard history endpoint returns historical average salary, "
    "not historical vacancy counts or posting skill demand."
)

ROLE_QUERY_TERMS = {
    "Backend Developer": "backend developer",
    "Frontend Developer": "front end developer",
    "AI Backend Developer": "machine learning engineer",
    "Data Analyst": "data analyst",
    "Data Engineer": "data engineer",
    "Data Scientist": "data scientist",
    "Builder": "full stack developer",
}


def collect_adzuna_salary_history(
    db: Session,
    country: str = "us",
    start_month: date | None = None,
) -> dict:
    app_id = get_env("ADZUNA_APP_ID")
    app_key = get_env("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError("ADZUNA_APP_ID and ADZUNA_APP_KEY are required.")

    inserted = 0
    updated = 0
    skipped_before_start = 0
    series_results = []

    for role, query_term in ROLE_QUERY_TERMS.items():
        payload = _fetch_history(
            country=country,
            query_term=query_term,
            app_id=app_id,
            app_key=app_key,
        )
        month_values = payload.get("month") or {}
        available_months = sorted(month_values)
        stored_for_role = 0

        for month_text, value in month_values.items():
            period_month = _parse_month(month_text)
            if start_month is not None and period_month < start_month:
                skipped_before_start += 1
                continue

            row = (
                db.query(JobRoleMarketHistory)
                .filter(
                    JobRoleMarketHistory.source == SOURCE,
                    JobRoleMarketHistory.country == country,
                    JobRoleMarketHistory.job_role_category == role,
                    JobRoleMarketHistory.query_term == query_term,
                    JobRoleMarketHistory.metric == METRIC,
                    JobRoleMarketHistory.period_month == period_month,
                )
                .first()
            )
            if row is None:
                row = JobRoleMarketHistory(
                    source=SOURCE,
                    country=country,
                    job_role_category=role,
                    query_term=query_term,
                    metric=METRIC,
                    period_month=period_month,
                    value=float(value),
                    granularity="month",
                    limitation_note=LIMITATION_NOTE,
                    collected_at=_utcnow(),
                )
                db.add(row)
                inserted += 1
            else:
                row.value = float(value)
                row.limitation_note = LIMITATION_NOTE
                row.collected_at = _utcnow()
                updated += 1
            stored_for_role += 1

        series_results.append(
            {
                "job_role_category": role,
                "query_term": query_term,
                "returned_months": len(month_values),
                "first_available_month": available_months[0] if available_months else None,
                "last_available_month": available_months[-1] if available_months else None,
                "stored_months": stored_for_role,
            }
        )

    db.commit()
    return {
        "source": SOURCE,
        "country": country,
        "metric": METRIC,
        "requested_start_month": start_month.isoformat() if start_month else None,
        "inserted": inserted,
        "updated": updated,
        "skipped_before_start": skipped_before_start,
        "series_results": series_results,
        "limitation_note": LIMITATION_NOTE,
    }


def _fetch_history(
    country: str,
    query_term: str,
    app_id: str,
    app_key: str,
) -> dict:
    response = requests.get(
        ADZUNA_HISTORY_URL.format(country=country),
        params={
            "app_id": app_id,
            "app_key": app_key,
            "what": query_term,
            "content-type": "application/json",
        },
        headers={"Accept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _parse_month(value: str) -> date:
    return datetime.strptime(value, "%Y-%m").date().replace(day=1)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
