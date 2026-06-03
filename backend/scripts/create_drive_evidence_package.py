from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "career_navigation_ai_rag_evidence_package_20260529"
PACKAGE_ROOT = ROOT / "data" / "exports" / "drive_package" / PACKAGE_NAME
ZIP_PATH = ROOT / "data" / "exports" / "drive_package" / f"{PACKAGE_NAME}.zip"

KEY_COUNTS = {
    "global_rag_candidates": 437,
    "kr_rag_candidates": 12,
    "total_rag_candidates": 449,
    "expected_embedding_tokens": 122465,
    "expected_embedding_cost_usd": 0.002449,
}


FOLDERS = [
    "01_overseas_raw_data",
    "02_overseas_global_evidence",
    "03_korean_raw_data",
    "04_korean_domestic_adoption",
    "05_rag_dryrun_documents",
    "06_reports",
    "07_scripts_snapshot",
    "08_methodology",
]


def main() -> int:
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (PACKAGE_ROOT / folder).mkdir(parents=True, exist_ok=True)

    copied: list[dict] = []
    missing: list[str] = []

    copy_group(
        "01_overseas_raw_data",
        [
            "data/exports/external_job_postings_snapshot_20260527.csv",
            "data/exports/external_job_postings.csv",
            "data/exports/external_job_postings_role_analysis_ml_skills_v2.csv",
        ],
        copied,
        missing,
    )
    copy_group(
        "02_overseas_global_evidence",
        [
            "data/exports/external_job_postings_role_evidence_v3.csv",
            "data/exports/external_job_postings_role_evidence_review_v3.csv",
            "data/exports/role_job_evidence_v3_validation_report.md",
            "data/exports/external_job_postings_role_evidence_v4.csv",
            "data/exports/external_job_postings_role_evidence_v4_removed_or_unverified.csv",
            "data/exports/role_job_evidence_v4_validation_report.md",
            "data/exports/additional_batches/external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv",
            "data/exports/additional_batches/role_job_evidence_v4_validation_report_evidence_boost_20260529_01_parserfix_v2.md",
            "data/exports/additional_batches/parserfix_impact_report_evidence_boost_20260529_01.md",
        ],
        copied,
        missing,
    )
    alias_copy(
        "data/exports/additional_batches/external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv",
        "02_overseas_global_evidence/GLOBAL_FINAL_role_job_evidence_v4_parserfix_v2.csv",
        copied,
        missing,
    )
    copy_group(
        "03_korean_raw_data",
        [
            "data/imports/korean_job_postings_manual_20260529.csv",
            "data/한국 구인공고 일부- 시트1.csv",
        ],
        copied,
        missing,
    )
    copy_group(
        "04_korean_domestic_adoption",
        [
            "data/exports/korean_batches/korean_job_postings_normalized_kr_v1.csv",
            "data/exports/korean_batches/korean_job_postings_role_evidence_v3_kr_v1.csv",
            "data/exports/korean_batches/korean_job_postings_role_evidence_review_v3_kr_v1.csv",
            "data/exports/korean_batches/korean_job_postings_role_evidence_v4_kr_v1.csv",
            "data/exports/korean_batches/korean_domestic_adoption_report_kr_v1.md",
            "data/exports/korean_batches/korean_job_postings_domestic_adoption_v2.csv",
            "data/exports/korean_batches/korean_job_postings_domestic_adoption_review_v2.csv",
            "data/exports/korean_batches/global_to_korean_skill_adoption_matrix_kr_v2.csv",
            "data/exports/korean_batches/korean_domestic_adoption_report_kr_v2.md",
            "data/exports/korean_batches/korean_cross_role_adoption_cases_kr_v2.csv",
            "data/exports/korean_batches/korean_domestic_adoption_quality_gate_v21.csv",
            "data/exports/korean_batches/korean_domestic_adoption_rag_candidates_v21.csv",
            "data/exports/korean_batches/korean_domestic_adoption_excluded_or_downgraded_v21.csv",
            "data/exports/korean_batches/global_to_korean_skill_adoption_matrix_kr_v21.csv",
            "data/exports/korean_batches/korean_domestic_adoption_quality_gate_report_kr_v21.md",
        ],
        copied,
        missing,
    )
    alias_copy(
        "data/exports/korean_batches/korean_domestic_adoption_rag_candidates_v21.csv",
        "04_korean_domestic_adoption/KR_FINAL_domestic_adoption_rag_candidates_v21.csv",
        copied,
        missing,
    )
    copy_group(
        "05_rag_dryrun_documents",
        [
            "data/exports/rag_dryrun/global_rag_documents_dryrun_v1.jsonl",
            "data/exports/rag_dryrun/kr_rag_documents_dryrun_v1.jsonl",
            "data/exports/rag_dryrun/global_kr_rag_document_samples_v1.md",
            "data/exports/rag_dryrun/global_kr_agent_search_strategy_v1.md",
            "data/exports/rag_dryrun/global_kr_rag_dryrun_validation_report_v1.md",
            "data/exports/rag_dryrun/global_kr_rag_indexing_dryrun_report_v1.md",
            "data/exports/rag_dryrun/global_kr_rag_indexing_container_dryrun_report_v1.md",
            "data/exports/rag_dryrun/global_kr_rag_documents_save_report_v1.md",
        ],
        copied,
        missing,
    )
    copy_reports(copied, missing)
    copy_group(
        "07_scripts_snapshot",
        [
            "scripts/index_role_job_evidence_documents.py",
            "scripts/validate_role_job_evidence_documents.py",
            "scripts/build_role_job_evidence_v3.py",
            "scripts/validate_role_job_evidence_v3_quality_gate.py",
            "scripts/build_role_job_evidence_v4.py",
            "scripts/rescreen_existing_role_evidence_batch.py",
            "scripts/collect_role_evidence_batch.py",
            "scripts/validate_additional_public_boards.py",
            "scripts/audit_v4_role_only_failures.py",
            "scripts/rebuild_additional_batch_parserfix_v2.py",
            "scripts/compare_parserfix_impact.py",
            "scripts/build_korean_domestic_adoption_evidence.py",
            "scripts/build_korean_domestic_adoption_evidence_v2.py",
            "scripts/audit_korean_domestic_adoption_quality_gate_v21.py",
            "scripts/build_global_kr_rag_documents_dryrun.py",
            "scripts/index_global_kr_rag_documents.py",
        ],
        copied,
        missing,
    )

    write_methodology_docs()
    write_readme()
    manifest = build_manifest(copied, missing)
    (PACKAGE_ROOT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    create_zip()

    print(json.dumps({
        "package_folder": str(PACKAGE_ROOT),
        "zip_path": str(ZIP_PATH),
        "files_copied": len(copied),
        "missing_files": missing,
    }, ensure_ascii=False, indent=2))
    return 0


def copy_group(folder: str, relative_paths: list[str], copied: list[dict], missing: list[str]) -> None:
    for relative in relative_paths:
        source = ROOT / relative
        destination = PACKAGE_ROOT / folder / source.name
        copy_one(source, destination, copied, missing, relative)


def alias_copy(relative_source: str, relative_destination: str, copied: list[dict], missing: list[str]) -> None:
    source = ROOT / relative_source
    destination = PACKAGE_ROOT / relative_destination
    copy_one(source, destination, copied, missing, relative_source)


def copy_one(source: Path, destination: Path, copied: list[dict], missing: list[str], label: str) -> None:
    if not source.exists():
        missing.append(label)
        return
    if should_exclude(source):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied.append({
        "source": str(source.relative_to(ROOT)),
        "destination": str(destination.relative_to(PACKAGE_ROOT)),
        "size_bytes": destination.stat().st_size,
    })


def copy_reports(copied: list[dict], missing: list[str]) -> None:
    report_names = [
        "role_job_evidence_validation_report.md",
        "role_job_evidence_v3_validation_report.md",
        "role_job_evidence_v3_quality_gate_report.md",
        "role_job_evidence_v4_validation_report.md",
        "additional_collection_plan_report.md",
        "existing_rescreen_after_validation_report_evidence_rescreen_20260527_01.md",
        "additional_collection_result_report_evidence_boost_20260529_01.md",
        "v4_role_only_failure_audit_evidence_boost_20260529_01.md",
        "parserfix_impact_report_evidence_boost_20260529_01.md",
        "korean_domestic_adoption_quality_gate_report_kr_v21.md",
        "global_kr_rag_dryrun_validation_report_v1.md",
        "global_kr_agent_search_strategy_v1.md",
        "global_kr_rag_indexing_container_dryrun_report_v1.md",
    ]
    all_exports = list((ROOT / "data" / "exports").rglob("*"))
    by_name = {}
    for path in all_exports:
        if path.is_file() and path.name not in by_name:
            by_name[path.name] = path
    for name in report_names:
        source = by_name.get(name)
        if not source:
            missing.append(f"data/exports/**/{name}")
            continue
        destination = PACKAGE_ROOT / "06_reports" / name
        copy_one(source, destination, copied, missing, str(source.relative_to(ROOT)))


def should_exclude(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if ".env" in lower_parts or "node_modules" in lower_parts or "__pycache__" in lower_parts:
        return True
    if path.suffix in {".pyc", ".log"}:
        return True
    return False


def write_readme() -> None:
    text = f"""# Career Navigation AI RAG Evidence Package

## 패키지 목적

이 패키지는 취준 나침반 Career Navigation AI의 RAG/Agent 근거 데이터를 구글 드라이브에 백업하고 공유하기 위한 evidence package입니다.

해외 데이터는 `GLOBAL leading signal`, 국내 데이터는 `KR domestic adoption`으로 분리했습니다. 두 데이터를 단순 합산해 하나의 시장 점수로 만들지 않습니다.

## 어떤 모델/방법으로 진행했는가

- Rule-based evidence validator로 직무와 기술 근거를 검증했습니다.
- RandomForest mock predictor는 이번 데이터 정제에는 사용하지 않았습니다.
- OpenAI embedding model은 아직 실행하지 않았고 비용 추정만 수행했습니다.
- pgvector/RAG Agent는 다음 단계에서 연결 예정입니다.
- 실제 학습 모델로 데이터를 자동 확정한 것이 아니라, 엄격한 규칙 기반 검증과 품질 게이트로 evidence를 선별했습니다.

## 데이터 철학

- 해외 데이터는 선행 기술 신호입니다.
- 국내 데이터는 국내 적용 사례입니다.
- 국내/해외 count를 합산하지 않습니다.
- Agent는 `GLOBAL leading signal -> KR domestic adoption -> User action` 순서로 설명합니다.

## 주요 결과 요약

- GLOBAL RAG 후보: 437건
- KR RAG 후보: 12건
- GLOBAL collection: `role_job_evidence_global_v1`
- KR collection: `role_job_evidence_kr_v21`
- KR URL/published_at은 전부 missing이라 시간차 확산 분석은 아직 불가합니다.
- KR high_confidence 후보 12건은 국내 적용 사례 설명용으로 사용 가능합니다.
- 예상 임베딩 대상: 449건
- 예상 토큰: 122,465
- 예상 임베딩 비용: 약 $0.002449

## 국내 KR v2.1 핵심 기술

- RAG: 6건
- Vector Database: 5건
- LLM: 9건
- API: 8건
- Data Pipeline: 3건
- Airflow: 3건
- Embedding: 2건
- FastAPI: 1건
- LangChain: 1건
- Docker: 1건
- Model Serving: 1건

## 폴더별 설명

- `01_overseas_raw_data`: 해외 채용공고 원본 또는 원본에 가까운 스냅샷
- `02_overseas_global_evidence`: 해외 GLOBAL leading signal 검증 결과
- `03_korean_raw_data`: 사용자가 직접 수집한 한국 공고 원본
- `04_korean_domestic_adoption`: 국내 KR domestic adoption 검증 결과
- `05_rag_dryrun_documents`: RAG 문서 dry-run JSONL, 샘플, 검색 전략, 검증 보고서
- `06_reports`: 전체 검증/수집/품질 게이트 보고서 모음
- `07_scripts_snapshot`: 재현성을 위한 핵심 스크립트 복사본
- `08_methodology`: 모델, 규칙, 파이프라인, evidence 정책 설명

## 이 패키지 생성 과정에서 하지 않은 작업

- DB 저장
- OpenAI 임베딩 생성
- embeddings 테이블 저장
- JobRoleSkillEvidence 재산출
- 추천 API 연결
- 프론트엔드 연결
- 국내 공고 URL/게시일 수동 보완

참고: 프로젝트 작업 흐름상 documents 저장 검증 보고서가 존재하면 패키지에 포함될 수 있지만, 이 패키지 생성 스크립트는 DB/RAG 저장을 수행하지 않습니다.

## 다음 단계

- documents 저장 상태 최종 확인
- 임베딩 실행 전 비용/토큰 재확인
- GLOBAL/KR 검색 API 구현
- Agent 응답 연결
- KR TOP 10 공고 URL/게시일 보완
- 해외 추가 수집
"""
    (PACKAGE_ROOT / "00_README.md").write_text(text, encoding="utf-8")


def write_methodology_docs() -> None:
    methodology = PACKAGE_ROOT / "08_methodology"
    methodology.mkdir(exist_ok=True)
    (methodology / "MODEL_AND_PIPELINE_SUMMARY.md").write_text(model_and_pipeline_summary(), encoding="utf-8")
    (methodology / "DATA_PROCESSING_FLOW.md").write_text(data_processing_flow(), encoding="utf-8")
    (methodology / "EVIDENCE_POLICY.md").write_text(evidence_policy(), encoding="utf-8")
    (methodology / "MODEL_USAGE_MANIFEST.json").write_text(
        json.dumps(model_usage_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def model_and_pipeline_summary() -> str:
    return """# 모델 및 파이프라인 요약

## 사용한 모델/기술 개요

### RandomForest mock prediction endpoint

- 역할: 초기 `/api/v1/model/predict`에서 직무 수요, 확산 시간, 영향도 mock 예측 응답 생성
- 주의: 이번 RAG evidence 검증 데이터셋을 학습한 실제 운영 모델은 아닙니다.
- 현재 역할: 프로젝트 구조상 예측 모델 연결 지점 또는 mock predictor입니다.

### Rule-based evidence validator

- 역할: 직무 혼용, ML/Research 혼입, Solutions Engineer 제외, final_skills 오탐 제거, verified_skills 생성
- 사용 위치:
  - v3 accepted/review/excluded 분류
  - v4 verified_core_skills / verified_secondary_skills 생성
  - KR v2/v2.1 domestic adoption quality gate
- 주의: 정량 ML 모델이 아니라 명시 규칙 기반 검증기입니다.

### RAG document builder

- 역할: 검증된 evidence를 GLOBAL/KR RAG 문서 content/metadata로 변환
- collection:
  - `role_job_evidence_global_v1`
  - `role_job_evidence_kr_v21`

### Embedding model

- 예정 모델: `text-embedding-3-small`
- 역할: RAG 문서를 벡터화하여 pgvector 검색에 사용 예정
- 현재 상태: 비용 추정만 수행, 실제 OpenAI API 호출 및 임베딩 생성은 아직 하지 않음
- 예상 임베딩 대상: 449건
- 예상 토큰: 122,465
- 예상 비용: 약 $0.002449

### pgvector

- 역할: embeddings 테이블에서 vector similarity search 수행 예정
- 현재 상태: 이전 RAG 구조와 pgvector 기반 검색 API는 존재하나, 이 패키지 생성 과정에서는 사용하지 않았습니다.

### Agent / RAG reasoning layer

- 역할: GLOBAL leading signal과 KR domestic adoption을 별도 검색한 뒤 사용자 목표 직무와 연결
- 응답 구조:
  1. GLOBAL leading signal
  2. KR domestic adoption
  3. User action / 12주 로드맵 과제

## 실제 사용 여부

| 구분 | 실제 사용 여부 | 설명 |
|---|---|---|
| Rule-based validator | 사용 | v3/v4/KR v2.1 검증 |
| RandomForest mock predictor | 이번 데이터 정제에는 미사용 | 기존 API mock predictor |
| OpenAI embedding | 미사용 | 비용 추정만 수행 |
| LLM generation | 수동/Codex 보조 | 데이터 생성이 아니라 코드 작성과 분석 보조 |
| pgvector search | 이번 패키지 생성에는 미사용 | 향후 임베딩 후 사용 |
| RAG Agent | 아직 미연결 | 문서 설계와 검색 전략만 dry-run |

## 해외 GLOBAL 처리 파이프라인

1. raw overseas postings
2. role analysis v2
3. v3 role validation
4. v4 skill verification
5. quality gate
6. additional collection
7. parserfix v2
8. GLOBAL RAG dry-run
9. indexing dry-run

## 국내 KR 처리 파이프라인

1. manual Korean CSV
2. KR normalization v1
3. KR role evidence v1
4. KR domestic adoption v2
5. KR quality gate v2.1
6. high_confidence KR RAG candidates
7. KR RAG dry-run

## 왜 여러 번 검증했는가

- 오추천 방지
- 직무 혼용 방지
- final_skills 오탐 제거
- reference-only 기술 제외
- 해외/국내 데이터 목적 분리
- Agent가 근거 없는 기술 추천을 하지 않도록 하기 위함
"""


def data_processing_flow() -> str:
    return """# 데이터 처리 흐름

```mermaid
flowchart TD
    A[Overseas Raw Job Postings] --> B[Role Analysis v2]
    B --> C[v3 Role Validation]
    C --> D[v4 Verified Skills]
    D --> E[Parserfix v2]
    E --> F[GLOBAL RAG Dry-run Documents]

    K[Korean Manual Job CSV] --> L[KR Normalization v1]
    L --> M[KR Role Evidence v1]
    M --> N[KR Domestic Adoption v2]
    N --> O[KR Quality Gate v2.1]
    O --> P[KR RAG Dry-run Documents]

    F --> Q[GLOBAL Collection: leading_signal]
    P --> R[KR Collection: domestic_adoption]

    Q --> S[Future Agent Search]
    R --> S
    S --> T[GLOBAL Signal → KR Adoption → User Action]
```

## 단계별 산출 파일

| 단계 | 주요 산출 파일 |
|---|---|
| 해외 원본 | `01_overseas_raw_data/*` |
| 해외 v3/v4 검증 | `02_overseas_global_evidence/*` |
| 해외 parserfix v2 최종 | `02_overseas_global_evidence/GLOBAL_FINAL_role_job_evidence_v4_parserfix_v2.csv` |
| 국내 원본 | `03_korean_raw_data/*` |
| 국내 v1/v2/v2.1 | `04_korean_domestic_adoption/*` |
| 국내 최종 RAG 후보 | `04_korean_domestic_adoption/KR_FINAL_domestic_adoption_rag_candidates_v21.csv` |
| RAG dry-run | `05_rag_dryrun_documents/*` |
| 검증 보고서 | `06_reports/*` |
| 재현 스크립트 | `07_scripts_snapshot/*` |
"""


def evidence_policy() -> str:
    return """# Evidence Policy

## GLOBAL evidence policy

- 해외 공고는 선행 기술 신호입니다.
- `skill_evidence_ready`만 RAG 후보입니다.
- `role_evidence_only`는 제외합니다.
- `verified_core_skills` 중심으로 사용합니다.
- 국내와 count를 합산하지 않습니다.

## KR evidence policy

- 국내 공고는 국내 적용 사례입니다.
- `high_confidence`만 1차 RAG 후보입니다.
- `supporting_context_only`는 역할 설명 보조용입니다.
- `manual_review_needed`는 URL/게시일 보완 후 재검토합니다.
- `exclude_from_rag`는 제외합니다.
- 국내와 해외 count를 합산하지 않습니다.
- URL/게시일이 없으면 time-lag 확산 주장을 하지 않습니다.

## 기술 검증 정책

- 본문 직접 근거만 인정합니다.
- `reference_skills`에만 있는 기술은 제외합니다.
- title만으로 skill-ready 처리하지 않습니다.
- AI/FDE/Product Engineer 제목만으로 기술을 추론하지 않습니다.
- 검색엔진을 RAG/Vector DB/Embedding으로 자동 확장하지 않습니다.
- QA/test automation은 Builder 적용 증거에서 제외합니다.
- 학과명/전공명은 Statistics 기술 적용 근거로 사용하지 않습니다.

## Agent output policy

- “전체 시장 1위 기술”처럼 단정하지 않습니다.
- “검증된 공고 사례 기준”으로 표현합니다.
- “해외에서 선행 신호가 관찰되고, 국내에서 적용 사례가 확인된다”는 식으로 설명합니다.
- 시간차 확산은 URL/게시일 보완 전까지 금지합니다.
"""


def model_usage_manifest() -> dict:
    return {
        "project": "Career Navigation AI",
        "package": PACKAGE_NAME,
        "models_and_methods": {
            "random_forest_mock_predictor": {
                "used_in_this_package": False,
                "role": "Existing mock prediction endpoint for demand/diffusion response",
                "notes": "Not used to generate or validate this evidence package",
            },
            "rule_based_evidence_validator": {
                "used_in_this_package": True,
                "role": "Role validation, skill verification, domestic adoption quality gate",
                "outputs": ["v3", "v4", "KR v2.1"],
            },
            "openai_embedding_model": {
                "model": "text-embedding-3-small",
                "used_in_this_package": False,
                "planned_use": "Embedding GLOBAL/KR RAG documents for pgvector search",
                "estimated_documents": 449,
                "estimated_tokens": 122465,
                "estimated_cost_usd": 0.002449,
            },
            "pgvector": {
                "used_in_this_package": False,
                "planned_use": "Vector similarity search after embedding generation",
            },
            "rag_agent": {
                "used_in_this_package": False,
                "planned_use": "Search GLOBAL/KR collections and explain GLOBAL signal → KR adoption → user action",
            },
        },
        "collections": {
            "global": "role_job_evidence_global_v1",
            "korean": "role_job_evidence_kr_v21",
        },
        "safety_status": safety_status(),
    }


def build_manifest(copied: list[dict], missing: list[str]) -> dict:
    return {
        "package_name": PACKAGE_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files_copied": len(copied),
        "missing_files": missing,
        "folders": FOLDERS,
        "copied_files": copied,
        "key_counts": KEY_COUNTS,
        "collections": [
            "role_job_evidence_global_v1",
            "role_job_evidence_kr_v21",
        ],
        "models_and_methods_summary": {
            "rule_based_validator_used": True,
            "random_forest_mock_used_for_package": False,
            "openai_embedding_used": False,
            "pgvector_used_for_package": False,
            "rag_agent_connected": False,
        },
        "safety_status": safety_status(),
        "notes": [
            "This package creation copied files only; it did not call DB, OpenAI, embeddings, recommendation APIs, or frontend code.",
            "GLOBAL data is leading_signal and KR data is domestic_adoption; counts must not be merged into one market score.",
            "Requested Korean imports CSV was missing; actual manual Korean CSV was included from backend/data/한국 구인공고 일부- 시트1.csv.",
        ],
    }


def safety_status() -> dict:
    return {
        "db_saved": False,
        "embeddings_created": False,
        "openai_called": False,
        "job_role_skill_evidence_recalculated": False,
        "frontend_modified": False,
    }


def create_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in PACKAGE_ROOT.rglob("*"):
            if path.is_file() and not should_exclude(path):
                archive.write(path, path.relative_to(PACKAGE_ROOT.parent))


if __name__ == "__main__":
    raise SystemExit(main())
