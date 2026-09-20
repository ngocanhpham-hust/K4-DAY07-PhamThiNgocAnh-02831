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
            return [
                current_text[i:i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]

        if separator == "":
            return [
                current_text[i:i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        parts = current_text.split(separator)
        split_parts: list[str] = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= self.chunk_size:
                split_parts.append(part)
            else:
                split_parts.extend(
                    self._split(part, remaining_separators[1:])
                )

        # Merge adjacent small pieces back together so short lines or
        # paragraphs do not become tiny standalone chunks.
        chunks: list[str] = []
        current_chunk = ""

        for part in split_parts:
            candidate = (
                f"{current_chunk}{separator}{part}"
                if current_chunk
                else part
            )
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


class HeadingChunker:
    """Split Markdown by headings, then recursively split long sections.

    A heading is repeated on every child chunk so an oversized section keeps
    its subject and hierarchy after it has been split.
    """

    HEADING_LINE_PATTERN = re.compile(
        r"(?m)^(#{1,6})[ \t]+([^\n]+?)[ \t]*$"
    )

    def __init__(self, chunk_size: int = 800) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        matches = list(self.HEADING_LINE_PATTERN.finditer(text))
        if not matches:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text.strip())

        chunks: list[str] = []
        preamble = text[:matches[0].start()].strip()
        if preamble:
            chunks.extend(
                RecursiveChunker(chunk_size=self.chunk_size).chunk(preamble)
            )

        heading_stack: dict[int, str] = {}
        for index, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(0).strip()
            body_end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )
            body = text[match.end():body_end].strip()

            heading_stack = {
                stored_level: stored_heading
                for stored_level, stored_heading in heading_stack.items()
                if stored_level < level
            }
            heading_stack[level] = heading
            heading_context = "\n".join(
                heading_stack[stored_level]
                for stored_level in sorted(heading_stack)
            )

            # A title-only parent heading provides context to its child
            # sections, but is not useful as a standalone retrieval chunk.
            if not body:
                next_level = (
                    len(matches[index + 1].group(1))
                    if index + 1 < len(matches)
                    else None
                )
                if next_level is None or next_level <= level:
                    chunks.append(heading_context)
                continue

            chunks.extend(self._chunk_section(heading_context, body))
        return chunks

    def _chunk_section(self, heading: str, body: str) -> list[str]:
        section = f"{heading}\n\n{body}"
        if len(section) <= self.chunk_size:
            return [section]

        available_size = self.chunk_size - len(heading) - 2
        if available_size <= 0:
            raise ValueError(
                "chunk_size must be larger than the section heading"
            )

        body_chunks = RecursiveChunker(chunk_size=available_size).chunk(body)
        return [f"{heading}\n\n{chunk}" for chunk in body_chunks]


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
