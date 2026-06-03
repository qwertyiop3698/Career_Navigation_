from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.core.config import get_env
from app.db import SessionLocal
from app.models import Document, Embedding
from app.services.rag_service import DEFAULT_EMBEDDING_MODEL


GLOBAL_COLLECTION = "role_job_evidence_global_v1"
KR_COLLECTION = "role_job_evidence_kr_v21"
DOCUMENT_TYPE = "job_posting_evidence"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_PRICE_PER_1M_TOKENS_USD = 0.02
DEFAULT_GLOBAL_INPUT = ROOT_DIR / "data" / "exports" / "rag_dryrun" / "global_rag_documents_dryrun_v1.jsonl"
DEFAULT_KR_INPUT = ROOT_DIR / "data" / "exports" / "rag_dryrun" / "kr_rag_documents_dryrun_v1.jsonl"
DEFAULT_REPORT = ROOT_DIR / "data" / "exports" / "rag_dryrun" / "global_kr_rag_indexing_dryrun_report_v1.md"

REQUIRED_METADATA_COMMON = {
    "collection",
    "document_type",
    "evidence_purpose",
    "source_market",
    "market_region",
    "language",
    "source_posting_id",
    "rag_document_version",
}
REQUIRED_METADATA_GLOBAL = REQUIRED_METADATA_COMMON | {"evidence_quality"}
REQUIRED_METADATA_KR = REQUIRED_METADATA_COMMON | {"adoption_evidence_status", "rag_candidate_status"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or store GLOBAL/KR RAG JSONL documents into the documents table."
    )
    parser.add_argument("--global-input", type=Path, default=DEFAULT_GLOBAL_INPUT)
    parser.add_argument("--kr-input", type=Path, default=DEFAULT_KR_INPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--scope",
        choices=["all", "global", "kr"],
        default="all",
        help="Limit processing to one collection. Defaults to both.",
    )
    parser.add_argument(
        "--save-documents",
        action="store_true",
        help="Actually insert missing documents. No embeddings are created.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete and recreate only the selected GLOBAL/KR collections. Requires --save-documents.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embedding phase placeholder. Validates configuration and reports cost only; this script does not call OpenAI.",
    )
    parser.add_argument("--max-estimated-cost-usd", type=float, default=None)
    args = parser.parse_args()
    if args.rebuild and not args.save_documents:
        parser.error("--rebuild requires --save-documents. Dry-run never deletes data.")
    return args


def main() -> int:
    args = parse_args()
    selected_collections = selected_scope(args.scope)
    global_docs = load_jsonl(args.global_input) if GLOBAL_COLLECTION in selected_collections else []
    kr_docs = load_jsonl(args.kr_input) if KR_COLLECTION in selected_collections else []
    candidates = normalize_candidates(global_docs + kr_docs)
    validation = validate_candidates(candidates)
    input_duplicates = duplicate_keys(candidates)

    db_info = load_db_state(selected_collections)
    existing_by_key = db_info.get("existing_by_key", {})
    existing_embedded_keys = db_info.get("existing_embedded_keys", set())
    if args.rebuild:
        documents_to_insert = candidates
        duplicate_skip_count = 0
        documents_to_embed = candidates
    else:
        documents_to_insert = [candidate for candidate in candidates if candidate["dedupe_key"] not in existing_by_key]
        duplicate_skip_count = len(candidates) - len(documents_to_insert)
        documents_to_embed = list(documents_to_insert)
        documents_to_embed.extend(
            candidate
            for candidate in candidates
            if candidate["dedupe_key"] in existing_by_key and candidate["dedupe_key"] not in existing_embedded_keys
        )

    embedding_estimate = estimate_embedding_cost(documents_to_embed)
    if args.max_estimated_cost_usd is not None and embedding_estimate["estimated_cost_usd"] > args.max_estimated_cost_usd:
        raise ValueError(
            "Estimated embedding cost exceeds --max-estimated-cost-usd. "
            "No document or embedding was saved."
        )
    if args.embed:
        validate_embedding_configuration()

    report = build_report(
        args=args,
        selected_collections=selected_collections,
        global_docs=global_docs,
        kr_docs=kr_docs,
        candidates=candidates,
        validation=validation,
        input_duplicates=input_duplicates,
        db_info=db_info,
        duplicate_skip_count=duplicate_skip_count,
        documents_to_insert=documents_to_insert,
        documents_to_embed=documents_to_embed,
        embedding_estimate=embedding_estimate,
    )
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(report, encoding="utf-8")

    summary = report_summary(
        args,
        selected_collections,
        global_docs,
        kr_docs,
        validation,
        input_duplicates,
        db_info,
        duplicate_skip_count,
        documents_to_insert,
        documents_to_embed,
        embedding_estimate,
        args.report_output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not args.save_documents:
        return 0

    if validation["missing_required_metadata"] or validation["too_short_content"]:
        raise ValueError("Cannot save documents with missing required metadata or too-short content.")

    save_documents(selected_collections, candidates, documents_to_insert, rebuild=args.rebuild)
    post_save_db_info = load_db_state(selected_collections)
    save_report = build_save_report(
        args=args,
        selected_collections=selected_collections,
        pre_save_db_info=db_info,
        post_save_db_info=post_save_db_info,
        duplicate_skip_count=duplicate_skip_count,
        documents_to_insert=documents_to_insert,
        embedding_estimate=embedding_estimate,
    )
    args.report_output.write_text(save_report, encoding="utf-8")
    print(
        json.dumps(
            save_summary(
                args,
                post_save_db_info,
                duplicate_skip_count,
                documents_to_insert,
                embedding_estimate,
                args.report_output,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def selected_scope(scope: str) -> set[str]:
    if scope == "global":
        return {GLOBAL_COLLECTION}
    if scope == "kr":
        return {KR_COLLECTION}
    return {GLOBAL_COLLECTION, KR_COLLECTION}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def normalize_candidates(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for doc in docs:
        metadata = dict(doc.get("metadata") or {})
        collection = metadata.get("collection", "")
        source_posting_id = str(metadata.get("source_posting_id", ""))
        rag_version = str(metadata.get("rag_document_version", ""))
        candidates.append(
            {
                "content": doc.get("content") or "",
                "source": collection,
                "metadata": metadata,
                "collection": collection,
                "source_posting_id": source_posting_id,
                "rag_document_version": rag_version,
                "dedupe_key": dedupe_key(collection, source_posting_id, rag_version),
            }
        )
    return candidates


def validate_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    missing_required = []
    too_short = []
    collection_mismatch = []
    for candidate in candidates:
        metadata = candidate["metadata"]
        collection = metadata.get("collection")
        required = REQUIRED_METADATA_GLOBAL if collection == GLOBAL_COLLECTION else REQUIRED_METADATA_KR
        missing = sorted(key for key in required if metadata.get(key) in (None, ""))
        if missing:
            missing_required.append({"dedupe_key": candidate["dedupe_key"], "missing": missing})
        if len(candidate["content"].strip()) < 120:
            too_short.append(candidate["dedupe_key"])
        if collection not in {GLOBAL_COLLECTION, KR_COLLECTION}:
            collection_mismatch.append(candidate["dedupe_key"])
    return {
        "missing_required_metadata": missing_required,
        "too_short_content": too_short,
        "collection_mismatch": collection_mismatch,
    }


def duplicate_keys(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(candidate["dedupe_key"] for candidate in candidates)
    return {key: count for key, count in counts.items() if count > 1}


def load_db_state(collections: set[str]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        existing_documents = load_collection_documents(db, collections)
        embedded_ids = load_embedded_document_ids(db, existing_documents)
        existing_by_key = {
            document_key(document): document
            for document in existing_documents
            if document.metadata_
            and document.metadata_.get("collection")
            and document.metadata_.get("source_posting_id") is not None
            and document.metadata_.get("rag_document_version")
        }
        existing_embedded_keys = {
            key
            for key, document in existing_by_key.items()
            if document.id in embedded_ids
        }
        existing_counts = Counter(document.metadata_.get("collection") for document in existing_documents if document.metadata_)
        existing_embedding_counts = Counter(
            document.metadata_.get("collection")
            for document in existing_documents
            if document.metadata_ and document.id in embedded_ids
        )
        return {
            "db_read_success": True,
            "db_read_error": "",
            "existing_documents": existing_documents,
            "existing_by_key": existing_by_key,
            "existing_embedded_keys": existing_embedded_keys,
            "existing_counts": dict(existing_counts),
            "existing_embedding_counts": dict(existing_embedding_counts),
        }
    except Exception as exc:  # DB may be unavailable during local dry-run.
        return {
            "db_read_success": False,
            "db_read_error": str(exc),
            "existing_documents": [],
            "existing_by_key": {},
            "existing_embedded_keys": set(),
            "existing_counts": {collection: 0 for collection in collections},
            "existing_embedding_counts": {collection: 0 for collection in collections},
        }
    finally:
        db.close()


def load_collection_documents(db: Session, collections: set[str]) -> list[Document]:
    documents: list[Document] = []
    for collection in collections:
        documents.extend(
            db.query(Document)
            .filter(Document.metadata_.contains({"collection": collection}))
            .order_by(Document.id.asc())
            .all()
        )
    return documents


def load_embedded_document_ids(db: Session, documents: list[Document]) -> set[int]:
    ids = [document.id for document in documents]
    if not ids:
        return set()
    return {
        document_id
        for (document_id,) in db.query(Embedding.document_id)
        .filter(Embedding.document_id.in_(ids))
        .all()
    }


def save_documents(
    selected_collections: set[str],
    candidates: list[dict[str, Any]],
    documents_to_insert: list[dict[str, Any]],
    rebuild: bool,
) -> None:
    db = SessionLocal()
    try:
        if rebuild:
            delete_selected_collections(db, selected_collections)
            db.flush()
        to_insert_keys = {candidate["dedupe_key"] for candidate in documents_to_insert}
        for candidate in candidates:
            if candidate["dedupe_key"] not in to_insert_keys:
                continue
            metadata = dict(candidate["metadata"])
            metadata.setdefault("embedding_model", EMBEDDING_MODEL)
            metadata.setdefault("embedding_status", "pending")
            metadata["indexed_at"] = utcnow_iso()
            document = Document(
                content=candidate["content"],
                source=candidate["source"],
                metadata_=metadata,
            )
            db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_selected_collections(db: Session, selected_collections: set[str]) -> None:
    for collection in selected_collections:
        (
            db.query(Document)
            .filter(Document.metadata_.contains({"collection": collection}))
            .delete(synchronize_session=False)
        )


def validate_embedding_configuration() -> None:
    if not get_env("OPENAI_API_KEY"):
        raise ValueError("--embed requires OPENAI_API_KEY. Mock embeddings are not allowed.")
    configured_model = get_env("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    if configured_model != EMBEDDING_MODEL:
        raise ValueError(
            f"--embed requires OPENAI_EMBEDDING_MODEL={EMBEDDING_MODEL}; configured model is {configured_model}."
        )


def estimate_embedding_cost(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    total_chars = sum(len(candidate["content"] or "") for candidate in candidates)
    estimated_tokens = max(1, int(total_chars / 4)) if candidates else 0
    estimated_cost = estimated_tokens / 1_000_000 * EMBEDDING_PRICE_PER_1M_TOKENS_USD
    return {
        "embedding_model": EMBEDDING_MODEL,
        "price_per_1m_input_tokens_usd": EMBEDDING_PRICE_PER_1M_TOKENS_USD,
        "token_estimation_method": "sum(content characters) / 4",
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
    }


def build_report(
    args: argparse.Namespace,
    selected_collections: set[str],
    global_docs: list[dict[str, Any]],
    kr_docs: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    validation: dict[str, Any],
    input_duplicates: dict[str, int],
    db_info: dict[str, Any],
    duplicate_skip_count: int,
    documents_to_insert: list[dict[str, Any]],
    documents_to_embed: list[dict[str, Any]],
    embedding_estimate: dict[str, Any],
) -> str:
    candidate_counts = Counter(candidate["collection"] for candidate in candidates)
    insert_counts = Counter(candidate["collection"] for candidate in documents_to_insert)
    embed_counts = Counter(candidate["collection"] for candidate in documents_to_embed)
    global_existing = display_existing_count(db_info, GLOBAL_COLLECTION)
    kr_existing = display_existing_count(db_info, KR_COLLECTION)
    global_existing_embeddings = display_existing_embedding_count(db_info, GLOBAL_COLLECTION)
    kr_existing_embeddings = display_existing_embedding_count(db_info, KR_COLLECTION)
    lines = [
        "# GLOBAL/KR RAG Documents Indexing Dry-Run Report",
        "",
        "## Inputs",
        "",
        f"- GLOBAL JSONL: `{args.global_input.as_posix()}`",
        f"- KR JSONL: `{args.kr_input.as_posix()}`",
        f"- Scope: {args.scope}",
        f"- Selected collections: {', '.join(sorted(selected_collections))}",
        "",
        "## Candidate Counts",
        "",
        f"- GLOBAL input documents: {len(global_docs)}",
        f"- KR input documents: {len(kr_docs)}",
        f"- GLOBAL save candidates: {candidate_counts.get(GLOBAL_COLLECTION, 0)}",
        f"- KR save candidates: {candidate_counts.get(KR_COLLECTION, 0)}",
        "",
        "## Existing Collection State",
        "",
        f"- DB read success: {str(db_info['db_read_success']).lower()}",
        f"- DB read error: {db_info['db_read_error']}",
        f"- GLOBAL existing collection documents: {global_existing}",
        f"- KR existing collection documents: {kr_existing}",
        f"- GLOBAL existing embeddings: {global_existing_embeddings}",
        f"- KR existing embeddings: {kr_existing_embeddings}",
        "",
        "## Duplicate/New Save Estimate",
        "",
        f"- Input duplicate key count: {len(input_duplicates)}",
        f"- Duplicate skip expected from existing DB: {duplicate_skip_count}",
        f"- GLOBAL new save expected: {insert_counts.get(GLOBAL_COLLECTION, 0)}",
        f"- KR new save expected: {insert_counts.get(KR_COLLECTION, 0)}",
        f"- Total new save expected: {len(documents_to_insert)}",
        "",
        "## Metadata/Content Validation",
        "",
        f"- Missing required metadata documents: {len(validation['missing_required_metadata'])}",
        f"- Too-short content documents: {len(validation['too_short_content'])}",
        f"- Collection mismatch documents: {len(validation['collection_mismatch'])}",
        "",
        "## Embedding Estimate",
        "",
        f"- Expected embedding target documents: {len(documents_to_embed)}",
        f"- GLOBAL expected embedding targets: {embed_counts.get(GLOBAL_COLLECTION, 0)}",
        f"- KR expected embedding targets: {embed_counts.get(KR_COLLECTION, 0)}",
        f"- Estimated input tokens: {embedding_estimate['estimated_tokens']}",
        f"- Estimated embedding cost USD: {embedding_estimate['estimated_cost_usd']}",
        f"- Embedding model: {embedding_estimate['embedding_model']}",
        f"- Cost method: {embedding_estimate['token_estimation_method']}; price ${EMBEDDING_PRICE_PER_1M_TOKENS_USD}/1M input tokens.",
        "",
        "## Safety Confirmation",
        "",
        f"- DB changed: {str(args.save_documents).lower()}",
        "- OpenAI API called: false",
        "- Embeddings generated: false",
        "- embeddings table changed: false",
        "- JobRoleSkillEvidence recalculated: false",
        "- Recommendation API changed: false",
        "- Frontend changed: false",
        "- Existing legacy collections deleted: false",
        "",
        "## Next Commands",
        "",
        "```powershell",
        "python backend/scripts/index_global_kr_rag_documents.py",
        "python backend/scripts/index_global_kr_rag_documents.py --scope global",
        "python backend/scripts/index_global_kr_rag_documents.py --scope kr",
        "python backend/scripts/index_global_kr_rag_documents.py --save-documents",
        "python backend/scripts/index_global_kr_rag_documents.py --save-documents --rebuild",
        "python backend/scripts/index_global_kr_rag_documents.py --embed --max-estimated-cost-usd 0.01",
        "```",
        "",
        "## Before Actual Embedding",
        "",
        "- Confirm documents were saved into only `role_job_evidence_global_v1` and `role_job_evidence_kr_v21`.",
        "- Confirm KR URL/published_at limitations are acceptable for domestic adoption explanation only.",
        "- Confirm OPENAI_API_KEY exists and mock embeddings are not used.",
        "- Confirm `text-embedding-3-small` and 1536-dimensional pgvector policy remains unchanged.",
    ]
    return "\n".join(lines) + "\n"


def build_save_report(
    args: argparse.Namespace,
    selected_collections: set[str],
    pre_save_db_info: dict[str, Any],
    post_save_db_info: dict[str, Any],
    duplicate_skip_count: int,
    documents_to_insert: list[dict[str, Any]],
    embedding_estimate: dict[str, Any],
) -> str:
    insert_counts = Counter(candidate["collection"] for candidate in documents_to_insert)
    sample_metadata = sample_saved_metadata(post_save_db_info)
    lines = [
        "# GLOBAL/KR RAG Documents Save Report",
        "",
        "## Executed Command",
        "",
        "```powershell",
        "docker compose exec -T backend python scripts/index_global_kr_rag_documents.py --save-documents --report-output data/exports/rag_dryrun/global_kr_rag_documents_save_report_v1.md",
        "```",
        "",
        "## Scope",
        "",
        f"- Selected collections: {', '.join(sorted(selected_collections))}",
        "- Embeddings requested: false",
        "- OpenAI API requested: false",
        "- Rebuild requested: false",
        "",
        "## Before Save",
        "",
        f"- GLOBAL existing collection documents: {display_existing_count(pre_save_db_info, GLOBAL_COLLECTION)}",
        f"- KR existing collection documents: {display_existing_count(pre_save_db_info, KR_COLLECTION)}",
        f"- GLOBAL existing embeddings: {display_existing_embedding_count(pre_save_db_info, GLOBAL_COLLECTION)}",
        f"- KR existing embeddings: {display_existing_embedding_count(pre_save_db_info, KR_COLLECTION)}",
        "",
        "## Save Result",
        "",
        f"- Duplicate skip count: {duplicate_skip_count}",
        f"- GLOBAL inserted documents: {insert_counts.get(GLOBAL_COLLECTION, 0)}",
        f"- KR inserted documents: {insert_counts.get(KR_COLLECTION, 0)}",
        f"- Total inserted documents: {len(documents_to_insert)}",
        "",
        "## After Save Verification",
        "",
        f"- DB read success: {str(post_save_db_info['db_read_success']).lower()}",
        f"- DB read error: {post_save_db_info['db_read_error']}",
        f"- GLOBAL collection documents: {display_existing_count(post_save_db_info, GLOBAL_COLLECTION)}",
        f"- KR collection documents: {display_existing_count(post_save_db_info, KR_COLLECTION)}",
        f"- GLOBAL collection embeddings: {display_existing_embedding_count(post_save_db_info, GLOBAL_COLLECTION)}",
        f"- KR collection embeddings: {display_existing_embedding_count(post_save_db_info, KR_COLLECTION)}",
        "",
        "## Embedding Estimate For Next Step",
        "",
        f"- Expected embedding target documents: {len(documents_to_insert)}",
        f"- Estimated input tokens: {embedding_estimate['estimated_tokens']}",
        f"- Estimated embedding cost USD: {embedding_estimate['estimated_cost_usd']}",
        f"- Embedding model: {embedding_estimate['embedding_model']}",
        "",
        "## Sample Metadata",
        "",
    ]
    for label, metadata in sample_metadata:
        lines.extend(
            [
                f"### {label}",
                "",
                "```json",
                json.dumps(metadata, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Confirmation",
            "",
            "- DB save was performed only for documents table.",
            "- embeddings table changed: false",
            "- OpenAI API called: false",
            "- Embeddings generated: false",
            "- JobRoleSkillEvidence recalculated: false",
            "- Recommendation API changed: false",
            "- Frontend changed: false",
            "- Existing legacy collections deleted: false",
            "- GLOBAL and KR collections remain separated.",
            "",
            "## Before Embedding",
            "",
            "- Run an embedding dry-run/cost check again after confirming saved document counts.",
            "- Confirm OPENAI_API_KEY exists.",
            "- Confirm mock embeddings are not used.",
            "- Confirm KR URL/published_at limitations are still shown in Agent responses.",
        ]
    )
    return "\n".join(lines) + "\n"


def sample_saved_metadata(db_info: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    samples = []
    seen = set()
    for document in db_info.get("existing_documents", []):
        metadata = document.metadata_ or {}
        collection = metadata.get("collection")
        if collection in {GLOBAL_COLLECTION, KR_COLLECTION} and collection not in seen:
            samples.append((collection, metadata))
            seen.add(collection)
    return samples


def save_summary(
    args: argparse.Namespace,
    post_save_db_info: dict[str, Any],
    duplicate_skip_count: int,
    documents_to_insert: list[dict[str, Any]],
    embedding_estimate: dict[str, Any],
    report_output: Path,
) -> dict[str, Any]:
    insert_counts = Counter(candidate["collection"] for candidate in documents_to_insert)
    return {
        "mode": "save-documents",
        "db_changed": True,
        "openai_api_called": False,
        "embeddings_generated": False,
        "duplicate_skip_count": duplicate_skip_count,
        "global_inserted_documents": insert_counts.get(GLOBAL_COLLECTION, 0),
        "kr_inserted_documents": insert_counts.get(KR_COLLECTION, 0),
        "total_inserted_documents": len(documents_to_insert),
        "global_collection_documents_after_save": existing_count_or_none(post_save_db_info, GLOBAL_COLLECTION),
        "kr_collection_documents_after_save": existing_count_or_none(post_save_db_info, KR_COLLECTION),
        "global_collection_embeddings_after_save": embedding_count_or_none(post_save_db_info, GLOBAL_COLLECTION),
        "kr_collection_embeddings_after_save": embedding_count_or_none(post_save_db_info, KR_COLLECTION),
        "estimated_embedding": embedding_estimate,
        "report_output": str(report_output),
    }


def report_summary(
    args: argparse.Namespace,
    selected_collections: set[str],
    global_docs: list[dict[str, Any]],
    kr_docs: list[dict[str, Any]],
    validation: dict[str, Any],
    input_duplicates: dict[str, int],
    db_info: dict[str, Any],
    duplicate_skip_count: int,
    documents_to_insert: list[dict[str, Any]],
    documents_to_embed: list[dict[str, Any]],
    embedding_estimate: dict[str, Any],
    report_output: Path,
) -> dict[str, Any]:
    insert_counts = Counter(candidate["collection"] for candidate in documents_to_insert)
    return {
        "mode": "save-documents" if args.save_documents else "dry-run",
        "scope": args.scope,
        "selected_collections": sorted(selected_collections),
        "db_changed": bool(args.save_documents),
        "openai_api_called": False,
        "embeddings_generated": False,
        "global_input_documents": len(global_docs),
        "kr_input_documents": len(kr_docs),
        "global_existing_collection_documents": existing_count_or_none(db_info, GLOBAL_COLLECTION),
        "kr_existing_collection_documents": existing_count_or_none(db_info, KR_COLLECTION),
        "input_duplicate_key_count": len(input_duplicates),
        "duplicate_skip_expected": duplicate_skip_count,
        "global_new_save_expected": insert_counts.get(GLOBAL_COLLECTION, 0),
        "kr_new_save_expected": insert_counts.get(KR_COLLECTION, 0),
        "total_new_save_expected": len(documents_to_insert),
        "missing_required_metadata_documents": len(validation["missing_required_metadata"]),
        "too_short_content_documents": len(validation["too_short_content"]),
        "expected_embedding_target_documents": len(documents_to_embed),
        "estimated_embedding": embedding_estimate,
        "db_read_success": db_info["db_read_success"],
        "db_read_error": db_info["db_read_error"],
        "report_output": str(report_output),
    }


def existing_count_or_none(db_info: dict[str, Any], collection: str) -> int | None:
    if not db_info["db_read_success"]:
        return None
    return db_info["existing_counts"].get(collection, 0)


def embedding_count_or_none(db_info: dict[str, Any], collection: str) -> int | None:
    if not db_info["db_read_success"]:
        return None
    return db_info["existing_embedding_counts"].get(collection, 0)


def display_existing_count(db_info: dict[str, Any], collection: str) -> str:
    if not db_info["db_read_success"]:
        return "unknown (DB read failed)"
    return str(db_info["existing_counts"].get(collection, 0))


def display_existing_embedding_count(db_info: dict[str, Any], collection: str) -> str:
    if not db_info["db_read_success"]:
        return "unknown (DB read failed)"
    return str(db_info["existing_embedding_counts"].get(collection, 0))


def document_key(document: Document) -> str:
    metadata = document.metadata_ or {}
    return dedupe_key(
        str(metadata.get("collection", "")),
        str(metadata.get("source_posting_id", "")),
        str(metadata.get("rag_document_version", "")),
    )


def dedupe_key(collection: str, source_posting_id: str, rag_document_version: str) -> str:
    return f"{collection}|{source_posting_id}|{rag_document_version}"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
