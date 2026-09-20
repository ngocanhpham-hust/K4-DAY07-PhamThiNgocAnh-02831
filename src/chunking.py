from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        # Split text into sentences using regex
        sentence_endings = re.compile(r'(?<=[.!?])\s+|\n')
        sentences = sentence_endings.split(text)

        chunks: list[str] = []
        current_chunk: list[str] = []

        for sentence in sentences:
            if sentence.strip():  # Ignore empty sentences
                current_chunk.append(sentence.strip())
                if len(current_chunk) >= self.max_sentences_per_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

        # Add any remaining sentences as the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks   

        


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not remaining_separators:
            # No more separators, return the text as a single chunk
            return [current_text]

        separator = remaining_separators[0]
        chunks: list[str] = []

        if separator == "":
            return [
                current_text[i:i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        # Split the current text using the current separator
        parts = current_text.split(separator)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= self.chunk_size:
                chunks.append(part)
            else:
                # Recursively split the part using the next separator
                sub_chunks = self._split(part, remaining_separators[1:])
                chunks.extend(sub_chunks)

        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_product = _dot(vec_a, vec_b)
    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        results = {
            "fixed_size": FixedSizeChunker(
                chunk_size=chunk_size
            ).chunk(text),

            "by_sentences": SentenceChunker(
                max_sentences_per_chunk=3
            ).chunk(text),

            "recursive": RecursiveChunker(
                chunk_size=chunk_size
            ).chunk(text),
        }

        comparison = {}

        for strategy_name, chunks in results.items():
            count = len(chunks)

            comparison[strategy_name] = {
                "count": count,
                "avg_length": (
                    sum(len(chunk) for chunk in chunks) / count
                    if count > 0
                    else 0.0
                ),
                "chunks": chunks,
            }

        return comparison
