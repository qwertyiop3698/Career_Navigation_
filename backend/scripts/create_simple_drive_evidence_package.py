from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "career_navigation_ai_simple_evidence_package_20260529"
PACKAGE_ROOT = ROOT / "data" / "exports" / "drive_package" / PACKAGE_NAME
ZIP_PATH = ROOT / "data" / "exports" / "drive_package" / f"{PACKAGE_NAME}.zip"


FILES = {
    "01_raw": [
        (
            "data/exports/external_job_postings_snapshot_20260527.csv",
            "GLOBAL_RAW_external_job_postings_snapshot_20260527.csv",
            "해외 채용공고 원본 스냅샷입니다.",
        ),
        (
            "data/한국 구인공고 일부- 시트1.csv",
            "KR_RAW_manual_job_postings.csv",
            "사용자가 직접 수집한 국내 채용공고 원본입니다.",
        ),
    ],
    "02_first_pass": [
        (
            "data/exports/external_job_postings_role_analysis_ml_skills_v2.csv",
            "GLOBAL_1ST_role_analysis_ml_skills_v2.csv",
            "해외 공고를 7개 직무 분석용으로 1차 정리한 파일입니다.",
        ),
        (
            "data/exports/korean_batches/korean_job_postings_normalized_kr_v1.csv",
            "KR_1ST_normalized_kr_v1.csv",
            "국내 원본을 표준 컬럼으로 정규화한 1차 파일입니다.",
        ),
        (
            "data/exports/korean_batches/korean_domestic_adoption_report_kr_v1.md",
            "KR_1ST_domestic_adoption_report_kr_v1.md",
            "국내 1차 정규화/직무 판정 보고서입니다.",
        ),
    ],
    "03_second_pass": [
        (
            "data/exports/additional_batches/external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv",
            "GLOBAL_2ND_evidence_v4_parserfix_v2.csv",
            "해외 GLOBAL evidence의 2차 검증/파싱 보정 결과입니다.",
        ),
        (
            "data/exports/additional_batches/parserfix_impact_report_evidence_boost_20260529_01.md",
            "GLOBAL_2ND_parserfix_impact_report.md",
            "해외 parserfix v2 영향 보고서입니다.",
        ),
        (
            "data/exports/korean_batches/korean_job_postings_domestic_adoption_v2.csv",
            "KR_2ND_domestic_adoption_v2.csv",
            "국내 review 공고까지 domestic adoption 관점으로 회수한 2차 파일입니다.",
        ),
        (
            "data/exports/korean_batches/korean_cross_role_adoption_cases_kr_v2.csv",
            "KR_2ND_cross_role_adoption_cases_v2.csv",
            "국내 복합 직무 적용 사례입니다.",
        ),
        (
            "data/exports/korean_batches/korean_domestic_adoption_report_kr_v2.md",
            "KR_2ND_domestic_adoption_report_kr_v2.md",
            "국내 2차 domestic adoption 보고서입니다.",
        ),
    ],
    "04_current_final": [
        (
            "data/exports/rag_dryrun/global_rag_documents_dryrun_v1.jsonl",
            "GLOBAL_FINAL_rag_documents_dryrun_v1.jsonl",
            "최종 GLOBAL RAG 후보 문서 437건입니다.",
        ),
        (
            "data/exports/korean_batches/korean_domestic_adoption_rag_candidates_v21.csv",
            "KR_FINAL_rag_candidates_v21.csv",
            "최종 KR high_confidence RAG 후보 12건입니다.",
        ),
        (
            "data/exports/rag_dryrun/kr_rag_documents_dryrun_v1.jsonl",
            "KR_FINAL_rag_documents_dryrun_v1.jsonl",
            "최종 KR RAG 후보 문서 dry-run JSONL입니다.",
        ),
        (
            "data/exports/korean_batches/korean_domestic_adoption_quality_gate_report_kr_v21.md",
            "KR_FINAL_quality_gate_report_v21.md",
            "국내 v2.1 최종 품질 게이트 보고서입니다.",
        ),
        (
            "data/exports/rag_dryrun/global_kr_rag_dryrun_validation_report_v1.md",
            "RAG_FINAL_dryrun_validation_report_v1.md",
            "GLOBAL/KR RAG dry-run 검증 보고서입니다.",
        ),
        (
            "data/exports/rag_dryrun/global_kr_rag_documents_save_report_v1.md",
            "RAG_FINAL_documents_save_report_v1.md",
            "documents 저장 결과 보고서입니다. 임베딩은 생성하지 않았습니다.",
        ),
    ],
}


def main() -> int:
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)

    copied = []
    missing = []
    for folder, entries in FILES.items():
        (PACKAGE_ROOT / folder).mkdir(parents=True, exist_ok=True)
        for relative_source, output_name, description in entries:
            source = ROOT / relative_source
            target = PACKAGE_ROOT / folder / output_name
            if not source.exists():
                missing.append(relative_source)
                continue
            shutil.copy2(source, target)
            copied.append(
                {
                    "folder": folder,
                    "file": output_name,
                    "source": relative_source,
                    "description": description,
                    "size_bytes": target.stat().st_size,
                }
            )

    write_readme(copied, missing)
    manifest = {
        "package_name": PACKAGE_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Simplified Google Drive package with raw, first-pass, second-pass, current-final evidence files only.",
        "folders": list(FILES.keys()),
        "files_copied": len(copied),
        "missing_files": missing,
        "copied_files": copied,
        "key_counts": {
            "global_rag_candidates": 437,
            "kr_rag_candidates": 12,
            "total_rag_candidates": 449,
            "expected_embedding_tokens": 122465,
            "expected_embedding_cost_usd": 0.002449,
        },
        "safety_status": {
            "db_saved_by_this_script": False,
            "openai_called": False,
            "embeddings_created": False,
            "job_role_skill_evidence_recalculated": False,
            "frontend_modified": False,
        },
    }
    (PACKAGE_ROOT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    create_zip()
    print(json.dumps({"package_folder": str(PACKAGE_ROOT), "zip_path": str(ZIP_PATH), "files_copied": len(copied), "missing_files": missing}, ensure_ascii=False, indent=2))
    return 0


def write_readme(copied: list[dict], missing: list[str]) -> None:
    by_folder = {}
    for item in copied:
        by_folder.setdefault(item["folder"], []).append(item)

    lines = [
        "# Career Navigation AI Evidence Package - Simple Version",
        "",
        "이 패키지는 구글 드라이브 업로드용 단순 정리본입니다.",
        "",
        "복잡한 검증 파일 전체가 아니라, 발표/공유할 때 보기 쉽도록 `raw`, `1차`, `2차`, `현재최종` 단계만 남겼습니다.",
        "",
        "## 핵심 요약",
        "",
        "- 해외 데이터: GLOBAL leading signal",
        "- 국내 데이터: KR domestic adoption",
        "- 국내/해외 공고 수는 하나의 시장 점수로 합산하지 않습니다.",
        "- 최종 GLOBAL RAG 후보: 437건",
        "- 최종 KR RAG 후보: 12건",
        "- 총 RAG 후보: 449건",
        "- 예상 임베딩 토큰: 122,465",
        "- 예상 임베딩 비용: 약 $0.002449",
        "- 이 단순 패키지 생성 과정에서는 DB 저장, OpenAI 호출, 임베딩 생성을 하지 않았습니다.",
        "",
        "## 폴더 구조",
        "",
        "### 01_raw",
        "",
        "정제 전 원본에 가장 가까운 데이터입니다.",
        "",
        "- `GLOBAL_RAW_external_job_postings_snapshot_20260527.csv`: 해외 채용공고 원본 스냅샷",
        "- `KR_RAW_manual_job_postings.csv`: 사용자가 직접 수집한 국내 채용공고 원본",
        "",
        "### 02_first_pass",
        "",
        "원본을 분석 가능한 형태로 1차 정리한 데이터입니다.",
        "",
        "- 해외: 7개 직무 분석용 role analysis v2",
        "- 국내: 표준 컬럼 정규화 및 v1 보고서",
        "",
        "### 03_second_pass",
        "",
        "직무 혼용, 기술 오탐, 파싱 문제를 더 검증한 2차 데이터입니다.",
        "",
        "- 해외: GLOBAL evidence v4 parserfix v2",
        "- 국내: domestic adoption v2 및 복합 직무 적용 사례",
        "",
        "### 04_current_final",
        "",
        "현재 기준 최종 후보입니다.",
        "",
        "- GLOBAL 최종 RAG 문서 dry-run: 437건",
        "- KR 최종 high_confidence RAG 후보: 12건",
        "- GLOBAL/KR RAG 검증 보고서",
        "- documents 저장 결과 보고서",
        "",
        "## 단계별 파일 목록",
        "",
    ]
    for folder in FILES:
        lines.extend([f"### {folder}", ""])
        for item in by_folder.get(folder, []):
            lines.append(f"- `{item['file']}`: {item['description']}")
        lines.append("")
    if missing:
        lines.extend(["## 누락 파일", ""])
        for item in missing:
            lines.append(f"- `{item}`")
        lines.append("")
    lines.extend(
        [
            "## 아직 하지 않은 작업",
            "",
            "- OpenAI 임베딩 생성",
            "- embeddings 테이블 저장",
            "- 추천 API 연결",
            "- 프론트엔드 연결",
            "- 국내 공고 URL/게시일 수동 보완",
            "",
            "참고: 현재 프로젝트에서는 documents 저장까지 진행된 보고서가 포함되어 있지만, 이 단순 패키지 생성 스크립트 자체는 DB 저장을 수행하지 않았습니다.",
            "",
        ]
    )
    (PACKAGE_ROOT / "00_README.md").write_text("\n".join(lines), encoding="utf-8")


def create_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in PACKAGE_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(PACKAGE_ROOT.parent))


if __name__ == "__main__":
    raise SystemExit(main())
