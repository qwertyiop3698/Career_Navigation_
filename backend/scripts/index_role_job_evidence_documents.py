import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.core.config import get_env
from app.db import SessionLocal
from app.models import Document, Embedding
from app.services.rag_service import DEFAULT_EMBEDDING_MODEL, RagService


COLLECTION = "role_job_evidence_v2"
DOCUMENT_TYPE = "job_posting_evidence"
DATASET_VERSION = "2026-05-27"
SOURCE = "role_job_evidence"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_PRICE_PER_1M_TOKENS_USD = 0.02
DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_analysis_ml_skills_v2.csv"
DESCRIPTION_MAX_CHARS = 900
REASON_SKILL_LIMIT = 8


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create RAG evidence documents from the cleaned seven-role job-posting CSV."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--save-documents",
        action="store_true",
        help="Store document rows only. No embedding request is made.",
    )
    mode.add_argument(
        "--embed",
        action="store_true",
        help="Store missing documents and create missing OpenAI embeddings.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=f"Delete and recreate documents in collection '{COLLECTION}'. Requires --save-documents or --embed.",
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=None)
    args = parser.parse_args()

    if args.rebuild and not (args.save_documents or args.embed):
        parser.error("--rebuild requires --save-documents or --embed; dry-run never deletes data.")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")

    input_path = args.input.resolve()
    rows, columns = read_csv(input_path)
    candidate_documents, duplicate_input_rows = build_candidate_documents(rows)

    db = SessionLocal()
    try:
        existing_documents = load_collection_documents(db)
        existing_by_source_id = {
            str(document.metadata_.get("source_posting_id")): document
            for document in existing_documents
            if document.metadata_ and document.metadata_.get("source_posting_id") is not None
        }
        existing_embedded_ids = load_embedded_document_ids(db, existing_documents)
        documents_to_insert = [
            candidate
            for candidate in candidate_documents
            if candidate["source_posting_id"] not in existing_by_source_id
        ]
        existing_candidates = [
            existing_by_source_id[candidate["source_posting_id"]]
            for candidate in candidate_documents
            if candidate["source_posting_id"] in existing_by_source_id
        ]
        documents_needing_embeddings = documents_to_insert + [
            document
            for document in existing_candidates
            if document.id not in existing_embedded_ids
        ]

        if args.rebuild:
            documents_to_insert = candidate_documents
            documents_needing_embeddings = candidate_documents

        report = build_report(
            mode=execution_mode(args),
            input_path=input_path,
            columns=columns,
            rows=rows,
            candidate_documents=candidate_documents,
            duplicate_input_rows=duplicate_input_rows,
            existing_documents=existing_documents,
            documents_to_insert=documents_to_insert,
            documents_needing_embeddings=documents_needing_embeddings,
            rebuild=args.rebuild,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))

        if not (args.save_documents or args.embed):
            return

        if args.embed:
            validate_embedding_configuration()
            estimated_cost = report["estimated_embedding"]["estimated_cost_usd"]
            if (
                args.max_estimated_cost_usd is not None
                and estimated_cost > args.max_estimated_cost_usd
            ):
                raise ValueError(
                    "Estimated embedding cost exceeds --max-estimated-cost-usd. "
                    "No document or embedding was saved."
                )

        if args.rebuild:
            delete_collection_documents(db)

        saved_documents = store_missing_documents(
            db=db,
            candidates=candidate_documents,
            rebuild=args.rebuild,
        )

        embedded_count = 0
        if args.embed:
            embedded_count = embed_missing_documents(
                db=db,
                documents=saved_documents,
                batch_size=args.batch_size,
            )

        db.commit()
        verification = collection_verification(db)
        print(
            json.dumps(
                {
                    "write_result": {
                        "documents_inserted": len(saved_documents)
                        if args.rebuild
                        else len(documents_to_insert),
                        "embeddings_created": embedded_count,
                    },
                    "collection_verification": verification,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames or []
        return list(reader), columns


def build_candidate_documents(rows: list[dict[str, str]]) -> tuple[list[dict], int]:
    documents: list[dict] = []
    seen_source_ids: set[str] = set()
    duplicate_input_rows = 0
    for row in rows:
        source_posting_id = source_identifier(row)
        if source_posting_id in seen_source_ids:
            duplicate_input_rows += 1
            continue
        seen_source_ids.add(source_posting_id)

        documents.append(
            {
                "content": evidence_content(row),
                "source": SOURCE,
                "source_posting_id": source_posting_id,
                "metadata": evidence_metadata(row, source_posting_id),
            }
        )
    return documents, duplicate_input_rows


def source_identifier(row: dict[str, str]) -> str:
    posting_id = value(row, "id")
    if posting_id:
        return posting_id
    return stable_hash(
        value(row, "company"),
        value(row, "title"),
        value(row, "job_url"),
        value(row, "job_role_category"),
    )


def evidence_content(row: dict[str, str]) -> str:
    role = value(row, "job_role_category") or "Unknown Role"
    company = value(row, "company") or "Unknown Company"
    title = value(row, "title") or "Untitled Posting"
    skills = parse_skills(value(row, "final_skills"))
    posting_url = value(row, "job_url")
    description = evidence_description(row)
    skill_text = ", ".join(skills) if skills else "명시된 기술 없음"
    evidence_skills = ", ".join(skills[:REASON_SKILL_LIMIT]) if skills else "직무 관련 기술"

    lines = [
        f"직무: {role}",
        f"회사명: {company}",
        f"공고 제목: {title}",
        f"요구 기술: {skill_text}",
        f"주요 업무 또는 설명 일부: {description or '제공된 설명 없음'}",
    ]
    lines.append(
        "기술 근거 이유: "
        f"이 공고는 {role} 직무로 분류되었으며, 정제된 요구 기술 목록에 "
        f"{evidence_skills} 등의 기술이 포함되어 있어 해당 직무에서 실제 요구되는 "
        "기술의 근거로 사용됩니다."
    )
    if posting_url:
        lines.append(f"공고 URL: {posting_url}")
    return "\n".join(lines)


def evidence_description(row: dict[str, str]) -> str:
    sections = []
    for label, column in [
        ("주요 업무", "responsibilities"),
        ("요구 사항", "requirements"),
        ("우대 사항", "preferred_qualifications"),
    ]:
        text_value = normalized_text(value(row, column))
        if text_value:
            sections.append(f"{label}: {text_value}")
    description = " | ".join(sections)
    if len(description) > DESCRIPTION_MAX_CHARS:
        return f"{description[:DESCRIPTION_MAX_CHARS].rstrip()}..."
    return description


def evidence_metadata(row: dict[str, str], source_posting_id: str) -> dict:
    return {
        "collection": COLLECTION,
        "document_type": DOCUMENT_TYPE,
        "job_role_category": value(row, "job_role_category"),
        "company": value(row, "company"),
        "title": value(row, "title"),
        "posting_url": value(row, "job_url"),
        "skills": parse_skills(value(row, "final_skills")),
        "source_posting_id": source_posting_id,
        "dataset_version": DATASET_VERSION,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_status": "pending",
        "source_dataset": "external_job_postings_role_analysis_ml_skills_v2.csv",
        "stable_hash": stable_hash(COLLECTION, source_posting_id),
    }


def load_collection_documents(db: Session) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.metadata_.contains({"collection": COLLECTION}))
        .order_by(Document.id.asc())
        .all()
    )


def load_embedded_document_ids(db: Session, documents: list[Document]) -> set[int]:
    document_ids = [document.id for document in documents]
    if not document_ids:
        return set()
    return {
        document_id
        for (document_id,) in db.query(Embedding.document_id)
        .filter(Embedding.document_id.in_(document_ids))
        .all()
    }


def store_missing_documents(
    db: Session,
    candidates: list[dict],
    rebuild: bool,
) -> list[Document]:
    existing_by_source_id = {}
    if not rebuild:
        existing_by_source_id = {
            str(document.metadata_.get("source_posting_id")): document
            for document in load_collection_documents(db)
            if document.metadata_ and document.metadata_.get("source_posting_id") is not None
        }

    documents = []
    for candidate in candidates:
        existing = existing_by_source_id.get(candidate["source_posting_id"])
        if existing:
            documents.append(existing)
            continue
        document = Document(
            content=candidate["content"],
            source=candidate["source"],
            metadata_=candidate["metadata"],
        )
        db.add(document)
        db.flush()
        documents.append(document)
    return documents


def embed_missing_documents(db: Session, documents: list[Document], batch_size: int) -> int:
    existing_embedded_ids = load_embedded_document_ids(db, documents)
    pending_documents = [
        document for document in documents if document.id not in existing_embedded_ids
    ]
    rag_service = RagService()
    embedded_count = 0
    for batch in chunks(pending_documents, batch_size):
        vectors = create_embeddings_with_retry(
            rag_service,
            [document.content or "" for document in batch],
        )
        for document, vector in zip(batch, vectors):
            db.execute(
                text(
                    """
                    INSERT INTO embeddings (document_id, embedding)
                    VALUES (:document_id, CAST(:embedding AS vector))
                    """
                ),
                {
                    "document_id": document.id,
                    "embedding": rag_service.to_vector_literal(vector),
                },
            )
            metadata = dict(document.metadata_ or {})
            metadata["embedding_provider"] = "openai"
            metadata["embedding_model"] = EMBEDDING_MODEL
            metadata["embedding_status"] = "completed"
            metadata["embedded_at"] = utcnow_iso()
            document.metadata_ = metadata
            embedded_count += 1
    return embedded_count


def delete_collection_documents(db: Session) -> None:
    (
        db.query(Document)
        .filter(Document.metadata_.contains({"collection": COLLECTION}))
        .delete(synchronize_session=False)
    )
    db.flush()


def validate_embedding_configuration() -> None:
    if not get_env("OPENAI_API_KEY"):
        raise ValueError(
            "--embed requires OPENAI_API_KEY. No mock embedding is allowed for this collection."
        )
    configured_model = get_env("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    if configured_model != EMBEDDING_MODEL:
        raise ValueError(
            f"--embed requires OPENAI_EMBEDDING_MODEL={EMBEDDING_MODEL}; "
            f"configured model is {configured_model}."
        )


def collection_verification(db: Session) -> dict[str, int]:
    documents = load_collection_documents(db)
    embedded_ids = load_embedded_document_ids(db, documents)
    return {
        "collection_documents": len(documents),
        "collection_embeddings": len(embedded_ids),
    }


def build_report(
    mode: str,
    input_path: Path,
    columns: list[str],
    rows: list[dict[str, str]],
    candidate_documents: list[dict],
    duplicate_input_rows: int,
    existing_documents: list[Document],
    documents_to_insert: list[dict],
    documents_needing_embeddings: list,
    rebuild: bool,
) -> dict:
    embedding_candidates = candidate_documents if rebuild else documents_needing_embeddings
    preview_candidate = next(
        (
            candidate
            for candidate in candidate_documents
            if "제공된 설명 없음" not in candidate["content"]
        ),
        candidate_documents[0] if candidate_documents else None,
    )
    return {
        "mode": mode,
        "database_changes": mode != "dry-run",
        "openai_embedding_requests": mode == "embed",
        "collection": COLLECTION,
        "input_file": str(input_path),
        "csv_columns": columns,
        "input_rows": len(rows),
        "unique_document_candidates": len(candidate_documents),
        "duplicate_input_rows_skipped": duplicate_input_rows,
        "role_counts": dict(
            sorted(
                Counter(
                    candidate["metadata"].get("job_role_category") or "Unknown Role"
                    for candidate in candidate_documents
                ).items()
            )
        ),
        "existing_collection_documents": len(existing_documents),
        "documents_to_insert": len(candidate_documents) if rebuild else len(documents_to_insert),
        "documents_to_embed": len(embedding_candidates),
        "estimated_embedding": estimate_embedding_cost(embedding_candidates),
        "rebuild_requested": rebuild,
        "content_preview": preview_candidate["content"] if preview_candidate else None,
        "metadata_preview": preview_candidate["metadata"] if preview_candidate else None,
    }


def estimate_embedding_cost(documents: list) -> dict:
    contents = [
        document["content"] if isinstance(document, dict) else document.content or ""
        for document in documents
    ]
    total_chars = sum(len(content) for content in contents)
    estimated_tokens = max(1, int(total_chars / 4)) if contents else 0
    cost = estimated_tokens / 1_000_000 * EMBEDDING_PRICE_PER_1M_TOKENS_USD
    return {
        "pricing_model": EMBEDDING_MODEL,
        "price_per_1m_input_tokens_usd": EMBEDDING_PRICE_PER_1M_TOKENS_USD,
        "token_estimation_method": "total content characters / 4",
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": round(cost, 6),
    }


def execution_mode(args: argparse.Namespace) -> str:
    if args.embed:
        return "embed"
    if args.save_documents:
        return "save-documents"
    return "dry-run"


def chunks(items: list[Document], size: int) -> list[list[Document]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def create_embeddings_with_retry(
    rag_service: RagService,
    text_values: list[str],
) -> list[list[float]]:
    last_exc = None
    for attempt in range(3):
        try:
            return rag_service.create_embeddings(text_values)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_exc


def value(row: dict[str, str], column: str) -> str:
    return (row.get(column) or "").strip()


def parse_skills(skills_value: str) -> list[str]:
    return [skill.strip() for skill in skills_value.split(";") if skill.strip()]


def normalized_text(text_value: str) -> str:
    return " ".join(text_value.split())


def stable_hash(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
