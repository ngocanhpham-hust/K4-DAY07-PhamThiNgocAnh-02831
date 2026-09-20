from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._client = None
        self._collection = None
        self._next_index = 0

        try:
            import chromadb

            self._client = chromadb.EphemeralClient()
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._client = None
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        metadata = dict(doc.metadata)

        # "file#0" -> "file"
        metadata.setdefault(
            "doc_id",
            doc.id.split("#", 1)[0],
        )

        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(
        self,
        query: str,
        records: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rank in-memory records by their embedding dot product."""
        if top_k <= 0 or not records:
            return []

        query_embedding = self._embedding_fn(query)
        results = [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": dict(record["metadata"]),
                "score": _dot(query_embedding, record["embedding"]),
            }
            for record in records
        ]
        results.sort(key=lambda result: result["score"], reverse=True)
        return results[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        records = [self._make_record(doc) for doc in docs]
        self._store.extend(records)

        if not self._use_chroma or self._collection is None:
            return

        storage_ids: list[str] = []
        chroma_metadatas: list[dict[str, Any]] = []
        for record in records:
            storage_ids.append(f"{self._collection_name}:{self._next_index}")
            self._next_index += 1

            record_metadata = dict(record["metadata"])
            record_metadata["__document_id"] = record["id"]
            chroma_metadatas.append(record_metadata)

        try:
            self._collection.add(
                ids=storage_ids,
                documents=[record["content"] for record in records],
                embeddings=[record["embedding"] for record in records],
                metadatas=chroma_metadatas,
            )
        except Exception:
            # The in-memory mirror remains complete if Chroma rejects metadata
            # or is otherwise unavailable at runtime.
            self._use_chroma = False
            self._client = None
            self._collection = None

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k)

        filtered_records = [
            record
            for record in self._store
            if all(
                record["metadata"].get(key) == value
                for key, value in metadata_filter.items()
            )
        ]
        return self._search_records(query, filtered_records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        matching_records = [
            record
            for record in self._store
            if record["metadata"].get("doc_id") == doc_id
        ]
        if not matching_records:
            return False

        self._store = [
            record
            for record in self._store
            if record["metadata"].get("doc_id") != doc_id
        ]

        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(where={"doc_id": doc_id})
            except Exception:
                # The in-memory store is the source used by public operations,
                # so deletion has still completed successfully.
                self._use_chroma = False
                self._client = None
                self._collection = None

        return True
