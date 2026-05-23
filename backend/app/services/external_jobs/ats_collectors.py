from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from app.services.external_jobs.companies import COMPANIES

REQUEST_TIMEOUT_SECONDS = 20
HEADERS = {
    "User-Agent": "CareerNavigationAI/1.0 (+public ATS job trend analysis)",
}


def clean_html(html_text: str | None) -> str:
    if not html_text:
        return ""

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def fetch_greenhouse(company: str, slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    response = requests.get(
        url,
        params={"content": "true"},
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    normalized = []
    for job in payload.get("jobs", []):
        location = _extract_name(job.get("location"))
        departments = job.get("departments") or []
        department = ", ".join(
            item.get("name", "") for item in departments if item.get("name")
        )

        normalized.append(
            {
                "company": company,
                "title": job.get("title") or "",
                "location": location,
                "department": department,
                "description": clean_html(job.get("content")),
                "job_url": job.get("absolute_url") or "",
                "source": "greenhouse",
                "external_id": str(job.get("id") or ""),
                "raw_json": job,
            }
        )
    return normalized


def fetch_lever(company: str, slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}"
    response = requests.get(
        url,
        params={"mode": "json"},
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    normalized = []
    for job in payload:
        categories = job.get("categories") or {}
        description_parts = [
            job.get("descriptionPlain"),
            job.get("additionalPlain"),
            _extract_lever_lists_text(job.get("lists")),
        ]

        normalized.append(
            {
                "company": company,
                "title": job.get("text") or "",
                "location": categories.get("location") or "",
                "department": (
                    categories.get("department")
                    or categories.get("team")
                    or categories.get("commitment")
                    or ""
                ),
                "description": "\n\n".join(
                    part.strip() for part in description_parts if part
                ),
                "job_url": job.get("hostedUrl") or job.get("applyUrl") or "",
                "source": "lever",
                "external_id": str(job.get("id") or ""),
                "raw_json": job,
            }
        )
    return normalized


def fetch_ashby(company: str, slug: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    response = requests.get(
        url,
        params={"includeCompensation": "true"},
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    normalized = []
    for job in payload.get("jobs", []):
        normalized.append(
            {
                "company": company,
                "title": job.get("title") or "",
                "location": (
                    job.get("locationName")
                    or _extract_name(job.get("location"))
                    or ""
                ),
                "department": (
                    job.get("departmentName")
                    or _extract_name(job.get("department"))
                    or ""
                ),
                "description": clean_html(job.get("descriptionHtml")),
                "job_url": (
                    job.get("jobUrl")
                    or job.get("applicationUrl")
                    or job.get("applyUrl")
                    or ""
                ),
                "source": "ashby",
                "external_id": str(job.get("id") or ""),
                "raw_json": job,
            }
        )
    return normalized


def fetch_company_jobs(company_info: dict) -> list[dict]:
    ats = company_info.get("ats")
    company = company_info.get("company", "")
    slug = company_info.get("slug", "")

    if ats == "greenhouse":
        return fetch_greenhouse(company, slug)
    if ats == "lever":
        return fetch_lever(company, slug)
    if ats == "ashby":
        return fetch_ashby(company, slug)

    raise ValueError(f"Unsupported ATS: {ats}")


def collect_all_external_jobs() -> dict:
    jobs = []
    company_results = []
    failed_companies = []

    for company_info in COMPANIES:
        company = company_info.get("company", "")
        try:
            company_jobs = fetch_company_jobs(company_info)
            jobs.extend(company_jobs)
            company_results.append(
                {
                    "company": company,
                    "source": company_info.get("ats"),
                    "fetched": len(company_jobs),
                    "status": "success",
                }
            )
        except Exception as exc:
            failed_companies.append({"company": company, "reason": str(exc)})
            company_results.append(
                {
                    "company": company,
                    "source": company_info.get("ats"),
                    "fetched": 0,
                    "status": "failed",
                    "reason": str(exc),
                }
            )

    return {
        "jobs": jobs,
        "total_fetched": len(jobs),
        "company_results": company_results,
        "failed_companies": failed_companies,
    }


def _extract_name(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("name") or ""
    if isinstance(value, str):
        return value
    return ""


def _extract_lever_lists_text(lists: Any) -> str:
    if not isinstance(lists, list):
        return ""

    parts = []
    for item in lists:
        if not isinstance(item, dict):
            continue
        heading = item.get("text")
        content = item.get("content")
        if heading:
            parts.append(str(heading))
        if content:
            parts.append(clean_html(str(content)))
    return "\n".join(parts)
