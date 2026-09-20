from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)

        context = "\n\n".join(
            f"[{index}] {result['content']}"
            for index, result in enumerate(results, start=1)
        )
        if not context:
            context = "No relevant context was found."

        prompt = (
            "You are a knowledge-based assistant. Answer the question using only the provided context. If the context does not contain enough information, say that you do not have enough information.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        return self.llm_fn(prompt)
