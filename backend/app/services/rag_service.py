import hashlib
import random
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_env
from app.models import Document

EMBEDDING_DIMENSIONS = 1536
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class RagService:
    def create_document(
        self,
        db: Session,
        content: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        document = Document(
            content=content,
            source=source,
            metadata_=metadata,
        )
        db.add(document)
        db.flush()

        embedding = self.create_embedding(content)
        db.execute(
            text(
                """
                INSERT INTO embeddings (document_id, embedding)
                VALUES (:document_id, CAST(:embedding AS vector))
                """
            ),
            {
                "document_id": document.id,
                "embedding": self.to_vector_literal(embedding),
            },
        )

        return document

    def search_documents(
        self,
        db: Session,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        query_embedding = self.create_embedding(query)
        rows = db.execute(
            text(
                """
                SELECT
                    d.content,
                    d.source,
                    1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS similarity_score
                FROM embeddings e
                JOIN documents d ON d.id = e.document_id
                ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            ),
            {
                "query_embedding": self.to_vector_literal(query_embedding),
                "top_k": top_k,
            },
        ).mappings()

        return [
            {
                "content": row["content"],
                "source": row["source"],
                "similarity_score": round(float(row["similarity_score"]), 4),
            }
            for row in rows
        ]

    def create_mock_embedding(self, text_value: str) -> list[float]:
        seed = int(hashlib.sha256(text_value.encode("utf-8")).hexdigest(), 16)
        generator = random.Random(seed)
        return [
            round(generator.uniform(-1.0, 1.0), 6)
            for _ in range(EMBEDDING_DIMENSIONS)
        ]

    def create_embedding(self, text_value: str) -> list[float]:
        return self.create_embeddings([text_value])[0]

    def create_embeddings(self, text_values: list[str]) -> list[list[float]]:
        api_key = get_env("OPENAI_API_KEY")
        if not api_key:
            return [self.create_mock_embedding(text_value) for text_value in text_values]

        model = get_env("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        dimensions = int(get_env("OPENAI_EMBEDDING_DIMENSIONS", str(EMBEDDING_DIMENSIONS)) or EMBEDDING_DIMENSIONS)
        payload = {
            "model": model,
            "input": text_values,
        }
        if model and model.startswith("text-embedding-3"):
            payload["dimensions"] = dimensions

        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(10, 60),
        )
        response.raise_for_status()

        embeddings = [item["embedding"] for item in response.json()["data"]]
        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}."
                )
        return embeddings

    def to_vector_literal(self, embedding: list[float]) -> str:
        return "[" + ",".join(str(value) for value in embedding) + "]"
