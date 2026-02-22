"""
Postgres + pgvector retrieval store.
Gracefully degrades to no-op when PG_DSN is not configured.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable

from backend.config import EMBEDDING_DIM, PG_DSN, RAG_TOP_K

try:
    import psycopg
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False


EmbeddingFn = Callable[[str], Awaitable[list[float]]]


class VectorStore:
    """Thin pgvector wrapper for chunk indexing and semantic retrieval."""

    def __init__(self, dsn: str = ""):
        self.dsn = dsn or PG_DSN
        self.enabled = bool(self.dsn and HAS_PSYCOPG)

    def _connect(self):
        if not self.enabled:
            raise RuntimeError("VectorStore is disabled (missing PG_DSN or psycopg).")
        # Supabase pooler (pgbouncer) can fail with prepared statements;
        # disable auto-prepare for compatibility.
        return psycopg.connect(self.dsn, prepare_threshold=None)

    async def ensure_schema(self):
        """Create pgvector extension, table, and index."""
        if not self.enabled:
            return
        await asyncio.to_thread(self._ensure_schema_sync)

    def _ensure_schema_sync(self):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS profile_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        profile_id TEXT NOT NULL,
                        chunk_text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({EMBEDDING_DIM}) NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_profile_chunks_profile_id
                    ON profile_chunks(profile_id);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_profile_chunks_embedding_ivfflat
                    ON profile_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                    """
                )
                conn.commit()

    async def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embedding_fn: EmbeddingFn,
    ) -> int:
        """
        Upsert chunk rows.
        chunk schema: {chunk_id, profile_id, chunk_text, metadata}
        """
        if not self.enabled or not chunks:
            return 0

        rows: list[tuple[str, str, str, str, str]] = []
        for chunk in chunks:
            text = str(chunk.get("chunk_text", ""))
            if not text.strip():
                continue
            embedding = await embedding_fn(text)
            vector_literal = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
            rows.append(
                (
                    str(chunk.get("chunk_id", "")),
                    str(chunk.get("profile_id", "")),
                    text,
                    json.dumps(chunk.get("metadata", {})),
                    vector_literal,
                )
            )

        if not rows:
            return 0

        return await asyncio.to_thread(self._upsert_rows_sync, rows)

    def _upsert_rows_sync(self, rows: list[tuple[str, str, str, str, str]]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk_id, profile_id, chunk_text, metadata_json, vector_literal in rows:
                    cur.execute(
                        """
                        INSERT INTO profile_chunks(chunk_id, profile_id, chunk_text, metadata, embedding)
                        VALUES (%s, %s, %s, %s::jsonb, %s::vector)
                        ON CONFLICT (chunk_id)
                        DO UPDATE SET
                            profile_id = EXCLUDED.profile_id,
                            chunk_text = EXCLUDED.chunk_text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding;
                        """,
                        (chunk_id, profile_id, chunk_text, metadata_json, vector_literal),
                    )
                conn.commit()
        return len(rows)

    async def search_profiles(
        self,
        query_text: str,
        embedding_fn: EmbeddingFn,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic retrieval for profile chunks.
        Returns list of dict: {profile_id, chunk_id, chunk_text, metadata, similarity}
        """
        if not self.enabled or not query_text.strip():
            return []

        embedding = await embedding_fn(query_text)
        vector_literal = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
        k = top_k or RAG_TOP_K
        return await asyncio.to_thread(self._search_sync, vector_literal, k)

    def _search_sync(self, vector_literal: str, top_k: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        profile_id,
                        chunk_id,
                        chunk_text,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM profile_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (vector_literal, vector_literal, top_k),
                )
                rows = cur.fetchall()

        return [
            {
                "profile_id": r[0],
                "chunk_id": r[1],
                "chunk_text": r[2],
                "metadata": r[3] if isinstance(r[3], dict) else {},
                "similarity": float(r[4]) if r[4] is not None else 0.0,
            }
            for r in rows
        ]
