from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db

from app.services.data_collection import (
    DataCollectionError,
    HRDK_SOURCE_CONFIGS,
    JobPostingCollector,
    MissingApiKeyError,
    PublicApiResponseError,
)

router = APIRouter(prefix="/api/v1/data", tags=["data-collection"])
legacy_router = APIRouter(prefix="/api/v1/data-collection", tags=["data-collection"])
collector = JobPostingCollector()


@router.post("/jobs/collect")
def collect_jobs(
    source: str = Query(
        default="mock",
        pattern="^(mock|worknet|public_data|hrd|hrdk_qual_info|hrdk_stats|hrdk_exam_info|hrdk_hrdnet|remotive|arbeitnow)$",
    ),
    # save_format controls only local raw/processed files; external APIs may return JSON or XML.
    save_format: str = Query(default="json", pattern="^(json|csv)$"),
    save_to_rag: bool = Query(default=False),
    seriesCd: str | None = Query(
        default=None,
        pattern="^(01|02|03|04)$",
        description="HRDK qualification series code: 01=기술사, 02=기능장, 03=기사, 04=기능사",
    ),
    baseYY: str | None = Query(
        default=None,
        pattern="^[0-9]{4}$",
        description="HRDK statistics base year, for example 2025.",
    ),
    year: str | None = Query(
        default=None,
        pattern="^[0-9]{4}$",
        description="HRDK HRDNET link history year, for example 2026.",
    ),
    type: str | None = Query(
        default=None,
        pattern="^(json|xml|JSON|XML)$",
        description="HRDK HRDNET response type.",
    ),
    pageNo: int | None = Query(default=None, ge=1),
    numOfRows: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    extra_params = {}
    if seriesCd:
        extra_params["seriesCd"] = seriesCd
    if baseYY:
        extra_params["baseYY"] = baseYY
    if year:
        extra_params["year"] = year
    if type:
        extra_params["type"] = type
    if pageNo is not None:
        extra_params["pageNo"] = str(pageNo)
    if numOfRows is not None:
        extra_params["numOfRows"] = str(numOfRows)

    return _collect_jobs(
        source=source,
        save_format=save_format,
        save_to_rag=save_to_rag,
        extra_params=extra_params,
        db=db,
    )


@router.get("/jobs")
def get_jobs(limit: int | None = Query(default=None, ge=1, le=500)):
    return collector.list_cleaned_jobs(limit=limit)


@legacy_router.post("/jobs")
def collect_job_postings_legacy(
    use_mock: bool = Query(default=True),
    save_format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    source = "mock" if use_mock else "public_data"
    return _collect_jobs(
        source=source,
        save_format=save_format,
        save_to_rag=False,
        extra_params={},
        db=db,
    )


def _collect_jobs(
    source: str,
    save_format: str,
    save_to_rag: bool,
    extra_params: dict,
    db: Session,
):
    try:
        if save_to_rag and source in HRDK_SOURCE_CONFIGS:
            result = collector.collect_hrdk_to_rag_documents(
                db=db,
                source=source,
                save_format=save_format,
                extra_params=extra_params,
            )
            db.commit()
            return result
        return collector.collect_with_params(
            source=source,
            save_format=save_format,
            extra_params=extra_params,
        )
    except MissingApiKeyError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PublicApiResponseError as exc:
        db.rollback()
        return JSONResponse(status_code=502, content=exc.payload)
    except DataCollectionError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
