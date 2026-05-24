"""RAG service — ChromaDB + local sentence-transformer embeddings.

Two collections:
  - healthcare_kb: loaded from data/kb/ on first run
  - user_uploads: per-session docs from the /documents endpoint
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_KB = "healthcare_kb"
_UPLOADS = "user_uploads"


class RAGService:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embeddings_obj: Optional[SentenceTransformerEmbeddings] = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._kb = self._client.get_or_create_collection(_KB)
        self._user_docs = self._client.get_or_create_collection(_UPLOADS)

    @property
    def _embeddings(self) -> SentenceTransformerEmbeddings:
        if self._embeddings_obj is None:
            # loaded on first use so startup stays fast
            self._embeddings_obj = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        return self._embeddings_obj

    @staticmethod
    def _hash_id(text: str, prefix: str) -> str:
        return f"{prefix}-{hashlib.md5(text.encode()).hexdigest()[:12]}"

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)

    def ingest_kb(self, kb_dir: Optional[str] = None) -> int:
        kb_path = Path(kb_dir or settings.KB_DIR)
        if not kb_path.exists():
            log.warning("KB dir not found: %s", kb_path)
            return 0

        existing: set[str] = set()
        try:
            got = self._kb.get(include=["metadatas"])
            for m in got.get("metadatas") or []:
                if m and "source" in m:
                    existing.add(m["source"])
        except Exception:  # noqa: BLE001
            pass

        added = 0
        for fp in sorted(kb_path.glob("*")):
            if fp.suffix.lower() not in {".md", ".txt"} or fp.name in existing:
                continue
            chunks = self._splitter.split_text(fp.read_text(encoding="utf-8"))
            if not chunks:
                continue
            ids = [self._hash_id(c, fp.stem) for c in chunks]
            metas = [{"source": fp.name, "chunk": i, "type": "kb"} for i in range(len(chunks))]
            self._kb.add(ids=ids, documents=chunks, metadatas=metas, embeddings=self._embed(chunks))
            added += len(chunks)
            log.info("Ingested %d chunks from %s", len(chunks), fp.name)
        return added

    def ingest_user_document(self, *, text: str, filename: str, session_id: str) -> int:
        chunks = self._splitter.split_text(text)
        if not chunks:
            return 0
        ids = [self._hash_id(f"{session_id}-{filename}-{c}", "u") for c in chunks]
        metas = [{"source": filename, "session_id": session_id, "chunk": i, "type": "user_upload"} for i in range(len(chunks))]
        self._user_docs.add(ids=ids, documents=chunks, metadatas=metas, embeddings=self._embed(chunks))
        log.info("Ingested %s (%d chunks)", filename, len(chunks))
        return len(chunks)

    def search(self, query: str, *, k: int = 4, session_id: Optional[str] = None) -> list[dict]:
        q_emb = self._embeddings.embed_query(query)
        results = self._flatten(self._kb.query(query_embeddings=[q_emb], n_results=k))
        if session_id:
            results += self._flatten(self._user_docs.query(
                query_embeddings=[q_emb], n_results=k, where={"session_id": session_id}
            ))
        results.sort(key=lambda r: r["distance"])
        return results[:k]

    @staticmethod
    def _flatten(res: dict) -> list[dict]:
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        return [{"text": d, "metadata": m or {}, "distance": dist} for d, m, dist in zip(docs, metas, dists)]

    def kb_stats(self) -> dict:
        return {"kb_chunks": self._kb.count(), "user_upload_chunks": self._user_docs.count()}


_rag: Optional[RAGService] = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
