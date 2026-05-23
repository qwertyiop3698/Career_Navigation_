from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ExternalJobPosting
from app.services.external_jobs.ats_collectors import collect_all_external_jobs
from app.services.external_jobs.skill_extractor import extract_skills


def collect_external_jobs_to_db(db: Session) -> dict:
    collected = collect_all_external_jobs()
    inserted = 0
    skipped_duplicates = 0

    for item in collected["jobs"]:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        source = (item.get("source") or "").strip()
        external_id = (item.get("external_id") or "").strip() or None
        job_url = (item.get("job_url") or "").strip() or None

        if _is_duplicate(db, source, external_id, job_url):
            skipped_duplicates += 1
            continue

        description = item.get("description") or ""
        posting = ExternalJobPosting(
            company=_varchar(item.get("company"), 255) or "",
            title=_varchar(title, 255) or "",
            location=_varchar(item.get("location"), 255),
            department=_varchar(item.get("department"), 255),
            description=description,
            job_url=job_url,
            source=source,
            external_id=_varchar(external_id, 255),
            skills=extract_skills(description),
            raw_json=item.get("raw_json"),
            collected_at=_utcnow(),
            created_at=_utcnow(),
        )

        try:
            db.add(posting)
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped_duplicates += 1
        except Exception:
            db.rollback()
            raise

    return {
        "status": "success",
        "total_fetched": collected["total_fetched"],
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "failed_companies": collected["failed_companies"],
    }


def _is_duplicate(
    db: Session,
    source: str,
    external_id: str | None,
    job_url: str | None,
) -> bool:
    if external_id:
        exists = (
            db.query(ExternalJobPosting.id)
            .filter(
                ExternalJobPosting.source == source,
                ExternalJobPosting.external_id == external_id,
            )
            .first()
        )
        if exists:
            return True

    if job_url:
        exists = (
            db.query(ExternalJobPosting.id)
            .filter(ExternalJobPosting.job_url == job_url)
            .first()
        )
        if exists:
            return True

    return False


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _varchar(value: str | None, max_length: int) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."
