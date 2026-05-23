import csv
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from datetime import datetime
from urllib.parse import urlparse

import requests
import xmltodict

from app.core.config import get_env
from app.models import Document
from app.services.rag_service import RagService

STANDARD_FIELDS = [
    "job_id",
    "company_name",
    "job_title",
    "job_category",
    "location",
    "career_level",
    "education",
    "required_skills",
    "preferred_skills",
    "employment_type",
    "deadline",
    "source_url",
    "source_name",
]

SUPPORTED_SOURCES = {
    "mock",
    "worknet",
    "public_data",
    "hrd",
    "hrdk_qual_info",
    "hrdk_stats",
    "hrdk_exam_info",
    "hrdk_hrdnet",
    "remotive",
    "arbeitnow",
}

HRDK_SOURCE_CONFIGS = {
    "hrd": {
        "env_url": "HRDK_CERT_ITEMS_URL",
        "fallback_url": "http://openapi.q-net.or.kr/api/service/rest/InquiryQualInfo/getList",
        "defaults": {},
    },
    "hrdk_qual_info": {
        "env_url": "HRDK_CERT_ITEMS_URL",
        "fallback_url": "http://openapi.q-net.or.kr/api/service/rest/InquiryQualInfo/getList",
        "defaults": {},
    },
    "hrdk_stats": {
        "env_url": "HRDK_CERT_STATS_URL",
        "fallback_url": "http://openapi.q-net.or.kr/api/service/rest/InquiryStatSVC/getTotExamList",
        "defaults": {"baseYY": str(datetime.now().year - 1)},
    },
    "hrdk_exam_info": {
        "env_url": "HRDK_CERT_EXAM_INFO_URL",
        "fallback_url": "http://openapi.q-net.or.kr/api/service/rest/InquiryTestInformationNTQSVC/getPEList",
        "defaults": {},
    },
    "hrdk_hrdnet": {
        "env_url": "HRDK_HRDNET_LINK_URL",
        "fallback_url": "https://c.q-net.or.kr/openapi/HrdnetHistInfo/hrdnetlinkhist.do",
        "defaults": {"type": "json", "year": str(datetime.now().year)},
    },
}

SKILL_KEYWORDS = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Kotlin",
    "Swift",
    "Go",
    "Rust",
    "C++",
    "C#",
    "PHP",
    "Ruby",
    "SQL",
    "React",
    "React Native",
    "Vue",
    "Angular",
    "Node.js",
    "Express",
    "FastAPI",
    "Django",
    "Flask",
    "Spring",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Terraform",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "GraphQL",
    "REST",
    "API",
    "LLM",
    "RAG",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
    "Pandas",
    "NumPy",
    "Tableau",
    "Power BI",
]


class DataCollectionError(Exception):
    """Raised when an external data source cannot be collected safely."""


class MissingApiKeyError(DataCollectionError):
    pass


class PublicApiResponseError(DataCollectionError):
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        super().__init__(payload.get("error") or "External public API request failed.")


class JobPostingCollector:
    def __init__(self, data_dir: Path | None = None):
        backend_root = Path(__file__).resolve().parents[3]
        self.data_dir = data_dir or backend_root / "data"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.rag_service = RagService()

    def collect(self, source: str = "mock", save_format: str = "json") -> dict[str, Any]:
        return self.collect_with_params(source=source, save_format=save_format)

    def collect_with_params(
        self,
        source: str = "mock",
        save_format: str = "json",
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = source.lower().strip()
        save_format = save_format.lower().strip()
        extra_params = extra_params or {}

        if source not in SUPPORTED_SOURCES:
            raise DataCollectionError(
                f"Unsupported source '{source}'. Choose one of: {', '.join(sorted(SUPPORTED_SOURCES))}."
            )
        if save_format not in {"json", "csv"}:
            raise DataCollectionError("save_format must be 'json' or 'csv'.")

        raw_records = (
            self._mock_records()
            if source == "mock"
            else self._fetch_source(source, extra_params=extra_params)
        )
        cleaned_records = [self._normalize_record(record, source) for record in raw_records]

        file_prefix = self._file_prefix_for_source(source)
        raw_path = self._save_records(raw_records, self.raw_dir, file_prefix, save_format)
        processed_path = self._save_records(
            cleaned_records,
            self.processed_dir,
            f"{file_prefix}_cleaned",
            save_format,
        )

        return {
            "message": "Job data collection completed.",
            "source": source,
            "raw_count": len(raw_records),
            "processed_count": len(cleaned_records),
            "parsed_format": getattr(self, "_last_parsed_format", None),
            "api_debug": getattr(self, "_last_api_debug_context", None),
            "raw_path": str(raw_path),
            "processed_path": str(processed_path),
            "fields": STANDARD_FIELDS,
        }

    def list_cleaned_jobs(self, limit: int | None = None) -> dict[str, Any]:
        jobs = self._load_processed_jobs()
        if limit is not None:
            jobs = jobs[: max(limit, 0)]

        return {
            "count": len(jobs),
            "path": str(self.processed_dir / "jobs_cleaned.json"),
            "jobs": jobs,
        }

    def collect_hrdk_to_rag_documents(
        self,
        db,
        source: str = "hrd",
        save_format: str = "json",
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        collection_result = self.collect_with_params(
            source=source,
            save_format=save_format,
            extra_params=extra_params,
        )
        records = self._load_records_from_path(collection_result["raw_path"])
        inserted = 0
        skipped_duplicates = 0

        for record in records:
            if self._is_existing_hrdk_document(db, record, source):
                skipped_duplicates += 1
                continue

            self.rag_service.create_document(
                db=db,
                content=self._to_hrdk_rag_content(record),
                source="hrdk",
                metadata={
                    "provider": "HRDK",
                    "api_source": source,
                    "hrdk_job_id": self._hrdk_record_id(record),
                    "source_url": self._first_text(record, ["source_url", "url", "detailUrl", "homepage"]),
                    "stable_hash": self._hrdk_stable_hash(record, source),
                    "parsed_format": collection_result.get("parsed_format"),
                    "raw_record": record,
                },
            )
            inserted += 1

        return {
            **collection_result,
            "rag_source": "hrdk",
            "rag_inserted": inserted,
            "rag_skipped_duplicates": skipped_duplicates,
        }

    def _fetch_source(
        self,
        source: str,
        extra_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        extra_params = extra_params or {}
        if source == "remotive":
            return self._fetch_remotive()
        if source == "arbeitnow":
            return self._fetch_arbeitnow()
        if source == "worknet":
            return self._fetch_worknet()
        if source in HRDK_SOURCE_CONFIGS:
            return self._fetch_hrdk(source=source, extra_params=extra_params)
        return self._fetch_generic_public_api(
            source_name="public_data",
            api_key_name="PUBLIC_DATA_API_KEY",
            default_url="https://apis.data.go.kr/1051000/recruitment/list",
            key_param="serviceKey",
        )

    def _fetch_worknet(self) -> list[dict[str, Any]]:
        api_key = self._required_api_key("WORKNET_API_KEY", "worknet")
        url = "https://www.work.go.kr/empInfo/empInfoSrch/list/dtlEmpSrch.do"
        params = {
            "authKey": api_key,
            "returnType": "JSON",
            "startPage": "1",
            "display": "20",
        }
        return self._request_json_records(url, params)

    def _fetch_hrdk(
        self,
        source: str,
        extra_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        api_key = self._required_hrdk_api_key()
        extra_params = extra_params or {}
        config = HRDK_SOURCE_CONFIGS[source]
        url = get_env(config["env_url"]) or config["fallback_url"]
        key_param = self._hrdk_key_param_for_url(url)
        params = {
            key_param: api_key,
            "pageNo": "1",
            "numOfRows": "10",
        }
        params.update(config["defaults"])
        params.update({key: value for key, value in extra_params.items() if value is not None})
        return self._request_json_records(url, params)

    def _fetch_generic_public_api(
        self,
        source_name: str,
        api_key_name: str,
        default_url: str,
        key_param: str,
    ) -> list[dict[str, Any]]:
        api_key = self._required_api_key(api_key_name, source_name)
        params = {
            key_param: api_key,
            "pageNo": "1",
            "numOfRows": "20",
            "resultType": "json",
            "type": "json",
        }
        return self._request_json_records(default_url, params)

    def _fetch_remotive(self) -> list[dict[str, Any]]:
        return self._request_json_records(
            "https://remotive.com/api/remote-jobs",
            {"category": "software-dev", "limit": "30"},
        )

    def _fetch_arbeitnow(self) -> list[dict[str, Any]]:
        return self._request_json_records(
            "https://www.arbeitnow.com/api/job-board-api",
            {},
        )

    def _required_api_key(self, env_name: str, source_name: str) -> str:
        value = get_env(env_name)
        if not value:
            raise MissingApiKeyError(
                f"{env_name} is not configured. Add it to .env before collecting from {source_name}."
            )
        return value

    def _required_hrdk_api_key(self) -> str:
        get_env("PUBLIC_DATA_API_KEY")
        api_key = (
            os.getenv("PUBLIC_DATA_API_KEY")
            or os.getenv("HRDK_SERVICE_KEY")
            or os.getenv("HRD_API_KEY")
        )
        if not api_key:
            raise MissingApiKeyError(
                "PUBLIC_DATA_API_KEY or HRDK_SERVICE_KEY or HRD_API_KEY is not configured"
            )
        return api_key

    def _hrdk_key_param_for_url(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host in {"openapi.q-net.or.kr", "c.q-net.or.kr"}:
            return "serviceKey"
        if host.endswith("hrd.go.kr"):
            return "authKey"
        return "serviceKey"

    def _request_json_records(self, base_url: str, params: dict[str, str]) -> list[dict[str, Any]]:
        timeout = int(get_env("PUBLIC_DATA_JOB_API_TIMEOUT_SECONDS", "20") or "20")

        retry_count = 0
        fallback_key_param_used = None
        try:
            response = self._get_with_retry(base_url, params, timeout=(10, max(timeout, 60)))
            retry_count = getattr(response, "_career_retry_count", 0)
            if _should_retry_qnet_lowercase_service_key(response, base_url, params):
                fallback_params = dict(params)
                fallback_params["serviceKey"] = fallback_params.pop("ServiceKey")
                response = self._get_with_retry(
                    base_url,
                    fallback_params,
                    timeout=(10, max(timeout, 60)),
                )
                params = fallback_params
                retry_count += getattr(response, "_career_retry_count", 0) + 1
                fallback_key_param_used = "serviceKey"
        except requests.Timeout as exc:
            raise PublicApiResponseError(
                {
                    "status": "failed",
                    "error": "External API request timed out.",
                    "status_code": None,
                    "content_type": None,
                    **_api_debug_context(None, base_url, params),
                    "pageNo": str(params.get("pageNo", "")),
                    "numOfRows": str(params.get("numOfRows", "")),
                    "retry_count": 1,
                    "fallback_key_param_used": fallback_key_param_used,
                    "sanitized_preview": "",
                }
            ) from exc
        except requests.RequestException as exc:
            raise PublicApiResponseError(
                {
                    "status": "failed",
                    "error": "External API request failed.",
                    "status_code": None,
                    "content_type": None,
                    **_api_debug_context(None, base_url, params),
                    "pageNo": str(params.get("pageNo", "")),
                    "numOfRows": str(params.get("numOfRows", "")),
                    "retry_count": retry_count,
                    "fallback_key_param_used": fallback_key_param_used,
                    "sanitized_preview": "",
                }
            ) from exc

        debug_context = _api_debug_context(response, base_url, params)
        debug_context["pageNo"] = str(params.get("pageNo", ""))
        debug_context["numOfRows"] = str(params.get("numOfRows", ""))
        debug_context["retry_count"] = retry_count
        debug_context["fallback_key_param_used"] = fallback_key_param_used
        self._last_api_debug_context = debug_context
        parsed_response = parse_public_api_response(response, debug_context)
        parsed = parsed_response["parsed"]
        parsed_format = parsed_response["format"]
        self._last_parsed_format = parsed_format

        result_code = extract_result_code(parsed)
        result_msg = extract_result_msg(parsed)
        if result_code and result_code != "00":
            raise PublicApiResponseError(
                {
                    "status": "failed",
                    "error": result_msg or "Public data API returned an error.",
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "api_url_host": debug_context["api_url_host"],
                    "api_url_path": debug_context["api_url_path"],
                    "query_param_keys": debug_context["query_param_keys"],
                    "parsed_format": parsed_format,
                    "result_code": result_code,
                    "result_msg": result_msg,
                    "sanitized_preview": parsed_response["raw_preview"],
                }
            )

        records = extract_items_from_public_data(parsed)
        if not records:
            records = self._extract_records(parsed)
        if not records:
            raise PublicApiResponseError(
                {
                    "status": "failed",
                    "error": result_msg or "External API returned no job records.",
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "api_url_host": debug_context["api_url_host"],
                    "api_url_path": debug_context["api_url_path"],
                    "query_param_keys": debug_context["query_param_keys"],
                    "parsed_format": parsed_format,
                    "result_code": result_code,
                    "result_msg": result_msg,
                    "sanitized_preview": parsed_response["raw_preview"],
                }
            )
        return records

    def _get_with_retry(
        self,
        base_url: str,
        params: dict[str, str],
        timeout: tuple[int, int],
    ) -> requests.Response:
        retryable_errors = (requests.Timeout, requests.ConnectionError)
        last_exc = None

        for attempt in range(2):
            try:
                response = requests.get(
                    base_url,
                    params=params,
                    headers={"Accept": "application/json, application/xml, text/xml"},
                    timeout=timeout,
                )
                response._career_retry_count = attempt
                return response
            except retryable_errors as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise

        raise last_exc

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [record for record in payload if isinstance(record, dict)]

        if not isinstance(payload, dict):
            return []

        candidates = [
            payload.get("jobs"),
            payload.get("job"),
            payload.get("data"),
            payload.get("items"),
            payload.get("wantedRoot", {}).get("wanted"),
            payload.get("response", {}).get("body", {}).get("items", {}).get("item"),
            payload.get("response", {}).get("body", {}).get("items"),
            payload.get("body", {}).get("items", {}).get("item"),
            payload.get("body", {}).get("items"),
        ]

        for candidate in candidates:
            if isinstance(candidate, list):
                return [record for record in candidate if isinstance(record, dict)]
            if isinstance(candidate, dict):
                return [candidate]

        return [payload]

    def _normalize_record(self, record: dict[str, Any], source_name: str) -> dict[str, Any]:
        required_text = self._clean_text(
            self._first_text(
                record,
                [
                    "required_skills",
                    "requirements",
                    "qualification",
                    "description",
                    "jobDescription",
                    "wantedInfo",
                    "dtlCont",
                    "recrutSe",
                    "tags",
                ],
            )
        )
        preferred_text = self._clean_text(
            self._first_text(
                record,
                [
                    "preferred_skills",
                    "preferred",
                    "preference",
                    "preferred_qualifications",
                    "pfCond",
                    "tags",
                    "우대사항",
                ],
            )
        )
        required_skills = self._extract_skills(required_text, record)
        preferred_skills = self._extract_skills(preferred_text, record)

        return {
            "job_id": self._first_text(record, ["job_id", "id", "slug", "wantedAuthNo", "recrutPblntSn", "jmCd"]),
            "company_name": self._first_text(
                record,
                ["company_name", "company", "corpNm", "companyName", "busplaName", "empBusiNm", "implNm", "instiNm"],
            ),
            "job_title": self._first_text(
                record,
                [
                    "job_title",
                    "title",
                    "position",
                    "wantedTitle",
                    "recrutPbancTtl",
                    "jobNm",
                    "jmfldnm",
                    "jmNm",
                    "description",
                    "linkNm",
                ],
            ),
            "job_category": self._first_text(
                record,
                ["job_category", "category", "jobCategory", "jobsCd", "ncsCdNm", "occupation", "seriesNm", "seriesCd"],
            ),
            "location": self._first_text(
                record,
                [
                    "location",
                    "candidate_required_location",
                    "region",
                    "workRegion",
                    "workPlc",
                    "workAddr",
                    "regionNm",
                    "basicAddr",
                    "mdobligFldNm",
                ],
            ),
            "career_level": self._first_text(
                record,
                ["career_level", "career", "experience", "careerCondition", "careerRequirement", "enterType"],
            ),
            "education": self._first_text(
                record,
                ["education", "academic", "educationLevel", "acdmcr", "minEdubg"],
            ),
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "employment_type": self._first_text(
                record,
                ["employment_type", "job_type", "job_types", "employmentType", "hireType", "empTpNm", "workType"],
            ),
            "deadline": self._first_text(
                record,
                ["deadline", "closeDate", "receiptCloseDt", "pbancEndYmd", "regDt", "publication_date", "created_at"],
            ),
            "source_url": self._first_text(
                record,
                ["source_url", "url", "detailUrl", "applyUrl", "wantedInfoUrl", "homepage"],
            ),
            "source_name": source_name,
        }

    def _first_text(self, record: dict[str, Any], keys: list[str]) -> str:
        lowered = {str(key).lower(): value for key, value in record.items()}
        for key in keys:
            value = record.get(key)
            if value is None:
                value = lowered.get(key.lower())
            text = self._stringify_value(value)
            if text:
                return text
        return ""

    def _stringify_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            parts = [self._stringify_value(item) for item in value]
            return ", ".join(part for part in parts if part)
        if isinstance(value, dict):
            parts = [self._stringify_value(item) for item in value.values()]
            return ", ".join(part for part in parts if part)
        return str(value).strip()

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _split_skills(self, value: str) -> list[str]:
        if not value:
            return []

        parts = re.split(r"[,/|·ㆍ\n]+", value)
        return [part.strip() for part in parts if part.strip()]

    def _extract_skills(self, text: str, record: dict[str, Any]) -> list[str]:
        tags = self._split_skills(self._first_text(record, ["tags"]))
        searchable = f"{text} {' '.join(tags)}".lower()
        detected = []

        for keyword in SKILL_KEYWORDS:
            if keyword.lower() in searchable:
                detected.append(keyword)

        for tag in tags:
            if 1 <= len(tag) <= 30 and tag not in detected:
                detected.append(tag)

        return detected[:20]

    def _save_records(
        self,
        records: list[dict[str, Any]],
        directory: Path,
        filename: str,
        save_format: str,
    ) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        if save_format == "csv":
            path = directory / f"{filename}.csv"
            self._save_csv(records, path)
            return path

        path = directory / f"{filename}.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _save_csv(self, records: list[dict[str, Any]], path: Path) -> None:
        fieldnames = STANDARD_FIELDS if self._is_cleaned_records(records) else self._raw_fieldnames(records)
        with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(self._csv_safe_record(record, fieldnames))

    def _is_cleaned_records(self, records: list[dict[str, Any]]) -> bool:
        return bool(records) and set(records[0].keys()) == set(STANDARD_FIELDS)

    def _raw_fieldnames(self, records: list[dict[str, Any]]) -> list[str]:
        return sorted({key for record in records for key in record.keys()}) if records else []

    def _csv_safe_record(self, record: dict[str, Any], fieldnames: list[str]) -> dict[str, Any]:
        safe_record = {}
        for fieldname in fieldnames:
            value = record.get(fieldname, "")
            safe_record[fieldname] = (
                ", ".join(str(item) for item in value)
                if isinstance(value, list)
                else value
            )
        return safe_record

    def _load_processed_jobs(self) -> list[dict[str, Any]]:
        json_path = self.processed_dir / "jobs_cleaned.json"
        if json_path.exists():
            return json.loads(json_path.read_text(encoding="utf-8"))

        csv_path = self.processed_dir / "jobs_cleaned.csv"
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                return list(csv.DictReader(csv_file))

        return []

    def _load_records_from_path(self, path_value: str) -> list[dict[str, Any]]:
        path = Path(path_value)
        if not path.exists():
            return []
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                return list(csv.DictReader(csv_file))
        return []

    def _file_prefix_for_source(self, source: str) -> str:
        if source in {"mock", "worknet", "public_data", "hrd", "remotive", "arbeitnow"}:
            return "jobs"
        return source

    def _mock_records(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "mock-ai-backend-001",
                "title": "AI Backend Developer",
                "company": "Compass Lab",
                "jobCategory": "Software Development",
                "region": "Seoul",
                "career": "Entry-level",
                "educationLevel": "Bachelor preferred",
                "qualification": "Python, SQL, FastAPI, REST API",
                "preferred": "RAG pipeline, LLM evaluation, MLOps",
                "employmentType": "Full-time",
                "closeDate": "2026-06-30",
                "detailUrl": "https://example.com/jobs/ai-backend",
            },
            {
                "id": "mock-data-analyst-002",
                "wantedTitle": "Data Analyst Intern",
                "corpNm": "Career Data Korea",
                "jobCategory": "Data Analysis",
                "workRegion": "Gyeonggi",
                "careerCondition": "No experience required",
                "education": "Associate degree or higher",
                "jobDescription": "Python, public data API, dashboard reporting",
                "preference": "SQL, visualization, crawling",
                "employmentType": "Intern",
                "receiptCloseDt": "2026-07-15",
                "url": "https://example.com/jobs/data-analyst",
            },
        ]

    def _is_existing_hrdk_document(self, db, job: dict[str, Any], source: str) -> bool:
        job_id = self._hrdk_record_id(job)
        source_url = self._first_text(job, ["source_url", "url", "detailUrl", "homepage"])
        stable_hash = self._hrdk_stable_hash(job, source)

        query = db.query(Document.id).filter(Document.source == "hrdk")
        if job_id:
            return (
                query.filter(Document.metadata_.contains({"api_source": source, "hrdk_job_id": job_id}))
                .first()
                is not None
            )
        if source_url:
            return (
                query.filter(Document.metadata_.contains({"api_source": source, "source_url": source_url}))
                .first()
                is not None
            )
        if stable_hash:
            return (
                query.filter(Document.metadata_.contains({"stable_hash": stable_hash}))
                .first()
                is not None
            )
        return False

    def _to_hrdk_rag_content(self, job: dict[str, Any]) -> str:
        fields = [
            ("Company", self._first_text(job, ["company_name", "company", "corpNm", "implNm", "instiNm"])),
            ("Title", self._first_text(job, ["job_title", "title", "description", "jmNm", "jmfldnm", "linkNm"])),
            ("Category", self._first_text(job, ["job_category", "seriesNm", "seriesCd", "mdobligFldNm"])),
            ("Location", self._first_text(job, ["location", "region", "workRegion", "basicAddr"])),
            ("Exam Date", self._first_text(job, ["docexamdt", "pracexamstartdt", "examYmd"])),
            ("Registration Start", self._first_text(job, ["docregstartdt", "pracregstartdt", "receiptStartDt"])),
            ("Registration End", self._first_text(job, ["docregenddt", "pracregenddt", "receiptEndDt"])),
            ("Pass Date", self._first_text(job, ["docpassdt", "pracpassdt", "passYmd"])),
            ("Source URL", self._first_text(job, ["source_url", "url", "detailUrl", "homepage"])),
        ]
        content = "\n".join(
            f"{label}: {value}"
            for label, value in fields
            if value
        )
        if content:
            content = f"{content}\n\nRaw Data:\n{json.dumps(job, ensure_ascii=False, indent=2)}"
            return content
        return f"Raw Data:\n{json.dumps(job, ensure_ascii=False, indent=2)}"

    def _hrdk_stable_hash(self, job: dict[str, Any], source: str) -> str:
        canonical = json.dumps(job, ensure_ascii=False, sort_keys=True, default=str)
        value = f"{source}|{canonical}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _hrdk_record_id(self, record: dict[str, Any]) -> str:
        return self._first_text(
            record,
            [
                "job_id",
                "id",
                "jmCd",
                "jmfldcd",
                "jmfldCd",
                "seriesCd",
                "linkCd",
            ],
        )


def parse_public_api_response(
    response: requests.Response,
    debug_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content_type = response.headers.get("Content-Type", "").lower()
    body = response.text or ""
    stripped = body.lstrip()
    raw_preview = _sanitize_preview(body)
    debug_context = debug_context or _api_debug_context(response, response.url, {})

    if _is_html_response(content_type, stripped):
        raise PublicApiResponseError(
            {
                "status": "failed",
                "error": (
                    "Configured HRD/HRDK endpoint returned HTML, not API data. "
                    "Check that the URL is the actual OpenAPI endpoint, not a "
                    "data.go.kr detail page or web page."
                ),
                "content_type": response.headers.get("Content-Type", ""),
                "status_code": response.status_code,
                "api_url_host": debug_context["api_url_host"],
                "api_url_path": debug_context["api_url_path"],
                "query_param_keys": debug_context["query_param_keys"],
                "pageNo": debug_context.get("pageNo"),
                "numOfRows": debug_context.get("numOfRows"),
                "retry_count": debug_context.get("retry_count", 0),
                "fallback_key_param_used": debug_context.get("fallback_key_param_used"),
                "sanitized_preview": raw_preview,
            }
        )

    json_first = "application/json" in content_type or stripped.startswith(("{", "["))
    xml_first = (
        "xml" in content_type
        or stripped.startswith("<")
        or not json_first
    )

    if json_first:
        try:
            return {
                "parsed": response.json(),
                "format": "json",
                "raw_preview": raw_preview,
            }
        except ValueError:
            try:
                return {
                    "parsed": xmltodict.parse(body),
                    "format": "xml",
                    "raw_preview": raw_preview,
                }
            except Exception as exc:
                raise PublicApiResponseError(
                    _parse_error_payload(
                        response,
                        "unknown",
                        raw_preview,
                        debug_context,
                    )
                ) from exc

    if xml_first:
        try:
            return {
                "parsed": xmltodict.parse(body),
                "format": "xml",
                "raw_preview": raw_preview,
            }
        except Exception as xml_exc:
            try:
                return {
                    "parsed": response.json(),
                    "format": "json",
                    "raw_preview": raw_preview,
                }
            except ValueError:
                raise PublicApiResponseError(
                    _parse_error_payload(
                        response,
                        "unknown",
                        raw_preview,
                        debug_context,
                    )
                ) from xml_exc

    raise PublicApiResponseError(
        _parse_error_payload(response, "unknown", raw_preview, debug_context)
    )


def extract_items_from_public_data(parsed: dict) -> list[dict]:
    body = _public_data_body(parsed)
    candidates = [
        body.get("items", {}).get("item") if isinstance(body.get("items"), dict) else None,
        body.get("items"),
        parsed.get("items", {}).get("item") if isinstance(parsed.get("items"), dict) else None,
        parsed.get("items"),
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            return [candidate]
    return []


def extract_result_code(parsed: dict) -> str | None:
    header = _public_data_header(parsed)
    value = header.get("resultCode") or header.get("result_code")
    return str(value) if value is not None else None


def extract_result_msg(parsed: dict) -> str | None:
    header = _public_data_header(parsed)
    value = header.get("resultMsg") or header.get("result_msg")
    return str(value) if value is not None else None


def extract_total_count(parsed: dict) -> int | None:
    body = _public_data_body(parsed)
    value = body.get("totalCount") or body.get("total_count")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _public_data_root(parsed: dict) -> dict:
    if not isinstance(parsed, dict):
        return {}
    root = parsed.get("response") or parsed.get("Response") or parsed
    return root if isinstance(root, dict) else {}


def _public_data_header(parsed: dict) -> dict:
    root = _public_data_root(parsed)
    header = root.get("header") or root.get("Header") or {}
    return header if isinstance(header, dict) else {}


def _public_data_body(parsed: dict) -> dict:
    root = _public_data_root(parsed)
    body = root.get("body") or root.get("Body") or {}
    return body if isinstance(body, dict) else {}


def _parse_error_payload(
    response: requests.Response,
    parsed_format: str,
    raw_preview: str,
    debug_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "failed",
        "error": "External API response could not be parsed as JSON or XML.",
        "status_code": response.status_code,
        "content_type": response.headers.get("Content-Type", ""),
        "api_url_host": debug_context["api_url_host"],
        "api_url_path": debug_context["api_url_path"],
        "query_param_keys": debug_context["query_param_keys"],
        "pageNo": debug_context.get("pageNo"),
        "numOfRows": debug_context.get("numOfRows"),
        "retry_count": debug_context.get("retry_count", 0),
        "fallback_key_param_used": debug_context.get("fallback_key_param_used"),
        "parsed_format": parsed_format,
        "result_code": None,
        "result_msg": None,
        "sanitized_preview": raw_preview,
    }


def _api_debug_context(
    response: requests.Response | None,
    base_url: str,
    params: dict[str, str],
) -> dict[str, Any]:
    parsed_url = urlparse(base_url or (response.url if response is not None else ""))
    query_keys = sorted(str(key) for key in params.keys())
    return {
        "api_url_host": parsed_url.netloc,
        "api_url_path": parsed_url.path,
        "query_param_keys": query_keys,
    }


def _is_html_response(content_type: str, stripped_body: str) -> bool:
    lowered = stripped_body[:100].lower()
    return (
        "text/html" in content_type
        or lowered.startswith("<!doctype html")
        or lowered.startswith("<html")
    )


def _should_retry_qnet_lowercase_service_key(
    response: requests.Response,
    base_url: str,
    params: dict[str, str],
) -> bool:
    host = urlparse(base_url).netloc.lower()
    if host not in {"openapi.q-net.or.kr", "c.q-net.or.kr"}:
        return False
    if "ServiceKey" not in params:
        return False
    if response.status_code >= 500:
        return True

    preview = (response.text or "")[:1000]
    return any(
        marker in preview
        for marker in [
            "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
            "SERVICE_KEY_IS_NOT_VALID_ERROR",
            "SERVICE_KEY_IS_NOT_VALID",
            "SERVICE_KEY",
        ]
    )


def _sanitize_preview(value: str, limit: int = 300) -> str:
    patterns = [
        r"(?i)(serviceKey=)[^&\s<]+",
        r"(?i)(ServiceKey=)[^&\s<]+",
        r"(?i)(authKey=)[^&\s<]+",
        r"(?i)(serviceKey</[^>]+>\s*<[^>]+>)[^<]+",
        r"(?i)(<serviceKey>)[^<]+",
        r"(?i)(<ServiceKey>)[^<]+",
        r"(?i)(<authKey>)[^<]+",
    ]
    sanitized = value
    for pattern in patterns:
        sanitized = re.sub(pattern, r"\1***MASKED***", sanitized)
    return " ".join(sanitized[:limit].split())
