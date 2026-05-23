import argparse
import json
import time
from pathlib import Path

import requests
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

sys.path.append(str(ROOT_DIR))

from app.db import SessionLocal
from app.models import Document
from app.services.rag_service import RagService


EMBEDDING_PRICE_PER_1M_TOKENS_USD = 0.02


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild document embeddings.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source", default=None)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=None)
    parser.add_argument("--include-openai", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        documents = _load_documents(
            db,
            limit=args.limit,
            source=args.source,
            include_openai=args.include_openai,
        )
        estimate = _estimate_cost(documents)
        result = {
            "seen": len(documents),
            "dry_run": args.dry_run,
            **estimate,
            "rebuilt": 0,
        }

        if not args.dry_run:
            rag_service = RagService()
            spent_estimate = 0.0
            for batch in _chunks(documents, args.batch_size):
                batch_estimate = _estimate_cost(batch)["estimated_cost_usd"]
                if args.max_estimated_cost_usd is not None and spent_estimate + batch_estimate > args.max_estimated_cost_usd:
                    result["stopped_reason"] = "estimated_cost_limit_reached"
                    result["estimated_cost_spent_usd"] = round(spent_estimate, 6)
                    break

                embeddings = _create_embeddings_with_retry(
                    rag_service,
                    [document.content or "" for document in batch],
                )
                for document, embedding in zip(batch, embeddings):
                    db.execute(
                        text(
                            """
                            UPDATE embeddings
                            SET embedding = CAST(:embedding AS vector)
                            WHERE document_id = :document_id
                            """
                        ),
                        {
                            "document_id": document.id,
                            "embedding": rag_service.to_vector_literal(embedding),
                        },
                    )
                    metadata = dict(document.metadata_ or {})
                    metadata["embedding_provider"] = "openai"
                    metadata["embedding_model"] = "text-embedding-3-small"
                    document.metadata_ = metadata
                    result["rebuilt"] += 1

                spent_estimate += batch_estimate
                db.commit()
            result["estimated_cost_spent_usd"] = round(spent_estimate, 6)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _load_documents(db, limit: int, source: str | None, include_openai: bool = False) -> list[Document]:
    query = db.query(Document).order_by(Document.id.asc())
    if source:
        query = query.filter(Document.source == source)
    if not include_openai:
        query = query.filter(~Document.metadata_.contains({"embedding_provider": "openai"}))
    return query.limit(limit).all()


def _chunks(items: list[Document], size: int) -> list[list[Document]]:
    safe_size = max(1, size)
    return [items[index : index + safe_size] for index in range(0, len(items), safe_size)]


def _create_embeddings_with_retry(rag_service: RagService, texts: list[str]) -> list[list[float]]:
    last_exc = None
    for attempt in range(3):
        try:
            return rag_service.create_embeddings(texts)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_exc


def _estimate_cost(documents: list[Document]) -> dict:
    total_chars = sum(len(document.content or "") for document in documents)
    estimated_tokens = max(1, int(total_chars / 4))
    estimated_cost = estimated_tokens / 1_000_000 * EMBEDDING_PRICE_PER_1M_TOKENS_USD
    return {
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
    }


if __name__ == "__main__":
    main()
