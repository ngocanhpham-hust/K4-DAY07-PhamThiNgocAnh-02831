from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from src.chunking import (
    FixedSizeChunker,
    HeadingChunker,
    RecursiveChunker,
    SentenceChunker,
)
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


DATA_DIR = Path("data/ecommerce-policies")
OUTPUT_PATH = Path("ket_qua_benchmark.txt")
TOP_K = 3

# To compare team strategies fairly, each member changes only this line.
CHUNKER = HeadingChunker(chunk_size=800)


@dataclass(frozen=True)
class BenchmarkQuery:
    question: str
    gold_answer: str
    gold_doc_id: str
    answer_markers: tuple[str, ...]
    metadata_filter: dict[str, str] | None = None


BENCHMARK_QUERIES = [
    BenchmarkQuery(
        question=(
            "Shopee hoàn tiền về thẻ tín dụng hoặc thẻ ghi nợ trong bao lâu?"
        ),
        gold_answer="Từ 7 đến 14 ngày làm việc, tùy theo ngân hàng.",
        gold_doc_id="shopee-buyer-refund-time",
        answer_markers=("7 - 14 ngày làm việc",),
    ),
    BenchmarkQuery(
        question=(
            "Người mua Shopee được gửi yêu cầu trả hàng/hoàn tiền trong bao "
            "lâu sau khi giao hàng thành công, và thực phẩm tươi sống có ngoại "
            "lệ gì?"
        ),
        gold_answer=(
            "Thông thường là 15 ngày kể từ khi giao hàng thành công; riêng thực "
            "phẩm tươi sống và đông lạnh là 24 giờ."
        ),
        gold_doc_id="shopee-return-refund-policy",
        answer_markers=("15 (mười lăm) ngày", "trong vòng 24 giờ"),
    ),
    BenchmarkQuery(
        question=(
            "Tôi có thể hủy đơn vào lúc nào và việc hủy đơn có hậu quả gì?"
        ),
        gold_answer=(
            "Người mua có thể hủy tùy trạng thái đơn; hầu hết đơn có thể hủy "
            "trước khi chuyển sang trạng thái đang vận chuyển. Việc hủy không "
            "gây hậu quả cho người bán, trừ khi chọn lý do Giao hàng trễ; một "
            "số trường hợp cần người bán phê duyệt hoặc có ngoại lệ."
        ),
        gold_doc_id="tiktok-buyer-order-cancellation",
        answer_markers=("trước khi đơn hàng ở trạng thái", "không gây ra hậu quả"),
        metadata_filter={"audience": "buyer"},
    ),
    BenchmarkQuery(
        question=(
            "Những trường hợp nào được tính và không được tính vào tỷ lệ trả "
            "hàng/hoàn tiền do lỗi người bán của TikTok Shop?"
        ),
        gold_answer=(
            "Chỉ số tính các đơn bị trả do lỗi liên quan đến người bán như vấn "
            "đề chất lượng đã xác minh, hàng lỗi/hư hỏng, kiện rỗng, sai hoặc "
            "thiếu hàng, thất lạc. Không tính yêu cầu do người mua hủy, người "
            "mua không gửi lại hàng đúng hạn, người bán thắng phân xử hoặc trả "
            "hàng vì đổi ý."
        ),
        gold_doc_id="tiktok-seller-fault-return-rate",
        answer_markers=("Không bao gồm", "Đổi ý"),
    ),
    BenchmarkQuery(
        question=(
            "Trong tranh chấp sau bán hàng TikTok Shop, người bán có bao lâu "
            "để gửi tài liệu, nền tảng có bao lâu để ra quyết định và hai bên "
            "có bao lâu để phản đối?"
        ),
        gold_answer=(
            "Khi được yêu cầu, người bán phải gửi tài liệu trong 24 giờ. Nền "
            "tảng ra quyết định trong 72 giờ sau khi nhận đủ tài liệu; yêu cầu "
            "phản đối phải gửi trong 48 giờ sau khi hai bên được thông báo."
        ),
        gold_doc_id="tiktok-after-sale-dispute",
        answer_markers=("trong vòng 24 giờ", "trong vòng 72 giờ", "trong vòng 48 giờ"),
    ),
]


class CachedEmbedder:
    """Cache API embeddings by provider, model and content hash."""

    def __init__(
        self,
        embedder: Callable[[str], list[float]],
        cache_path: Path,
    ) -> None:
        self.embedder = embedder
        self.cache_path = cache_path
        self.backend_name = getattr(embedder, "_backend_name", "embedding")
        self.cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self.cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.sha256(
            f"{self.backend_name}\0{text}".encode("utf-8")
        ).hexdigest()
        if digest not in self.cache:
            self.cache[digest] = self.embedder(text)
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self.cache, ensure_ascii=False),
                encoding="utf-8",
            )
        return self.cache[digest]


def parse_frontmatter(raw_text: str) -> tuple[dict[str, Any], str]:
    """Return YAML-like frontmatter and Markdown body without dependencies."""
    if not raw_text.startswith("---\n"):
        return {}, raw_text.strip()

    closing_index = raw_text.find("\n---", 4)
    if closing_index == -1:
        raise ValueError("Frontmatter is missing its closing '---'")

    frontmatter_text = raw_text[4:closing_index]
    body = raw_text[closing_index + 4:].lstrip("\r\n")
    metadata: dict[str, Any] = {}

    for line in frontmatter_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Invalid frontmatter line: {line!r}")
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    return metadata, body.strip()


def load_chunked_documents(data_dir: Path) -> tuple[list[Document], int]:
    documents: list[Document] = []
    source_count = 0

    for path in sorted(data_dir.glob("*.md")):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))
        source_count += 1

        for index, chunk in enumerate(CHUNKER.chunk(content)):
            chunk_metadata = {
                **metadata,
                "doc_id": path.stem,
                "source_path": str(path),
                "chunk_index": index,
            }
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata=chunk_metadata,
                )
            )

    return documents, source_count


def build_embedder() -> tuple[Callable[[str], list[float]], str]:
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()

    if provider == "local":
        embedder = LocalEmbedder()
    elif provider == "openai":
        embedder = CachedEmbedder(
            OpenAIEmbedder(),
            Path(".cache/bench-openai-embeddings.json"),
        )
    elif provider == "gemini":
        embedder = GeminiEmbedder()
    elif provider == "mock":
        embedder = _mock_embed
    else:
        raise ValueError(
            f"Unsupported {EMBEDDING_PROVIDER_ENV}={provider!r}; "
            "choose mock, local, openai or gemini"
        )

    backend_name = getattr(
        embedder,
        "backend_name",
        getattr(embedder, "_backend_name", embedder.__class__.__name__),
    )
    return embedder, str(backend_name)


def format_results(results: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        preview = " ".join(result["content"].split())[:180]
        lines.append(
            f"  {rank}. score={result['score']:.6f} "
            f"doc_id={metadata.get('doc_id')} chunk_id={result['id']}"
        )
        lines.append(f"     {preview}")
    return lines


def run_benchmark() -> str:
    load_dotenv(override=False)
    embedder, backend_name = build_embedder()
    documents, source_count = load_chunked_documents(DATA_DIR)
    store = EmbeddingStore(
        collection_name="ecommerce_policy_benchmark",
        embedding_fn=embedder,
    )
    store.add_documents(documents)

    chunker_parameters = ", ".join(
        f"{key}={value}"
        for key, value in vars(CHUNKER).items()
        if isinstance(value, (str, int, float, bool))
    )
    chunker_description = CHUNKER.__class__.__name__
    if chunker_parameters:
        chunker_description += f" ({chunker_parameters})"

    lines = [
        "=== E-commerce Policy Benchmark ===",
        f"Data directory: {DATA_DIR}",
        f"Chunker: {chunker_description}",
        f"Embedding backend: {backend_name}",
        f"Loaded: {source_count} source files -> {store.get_collection_size()} chunks",
    ]

    for index, benchmark in enumerate(BENCHMARK_QUERIES, start=1):
        results = store.search_with_filter(
            benchmark.question,
            top_k=TOP_K,
            metadata_filter=benchmark.metadata_filter,
        )
        context = "\n".join(result["content"] for result in results)
        gold_in_top_three = any(
            result["metadata"].get("doc_id") == benchmark.gold_doc_id
            for result in results
        )
        answer_in_context = all(
            marker.casefold() in context.casefold()
            for marker in benchmark.answer_markers
        )

        lines.extend(
            [
                "",
                f"Q{index}: {benchmark.question}",
                f"Filter: {benchmark.metadata_filter}",
                f"Gold doc: {benchmark.gold_doc_id}",
                f"Gold answer: {benchmark.gold_answer}",
                *format_results(results),
                f"Gold doc in top-3: {'YES' if gold_in_top_three else 'NO'}",
                f"All answer markers in top-3: {'YES' if answer_in_context else 'NO'}",
            ]
        )

    filtered_query = next(
        query for query in BENCHMARK_QUERIES if query.metadata_filter == {"audience": "buyer"}
    )
    unfiltered_results = store.search(filtered_query.question, top_k=TOP_K)
    filtered_results = store.search_with_filter(
        filtered_query.question,
        top_k=TOP_K,
        metadata_filter=filtered_query.metadata_filter,
    )
    unfiltered_context = "\n".join(
        result["content"] for result in unfiltered_results
    )
    filtered_context = "\n".join(
        result["content"] for result in filtered_results
    )
    unfiltered_has_answer = all(
        marker.casefold() in unfiltered_context.casefold()
        for marker in filtered_query.answer_markers
    )
    filtered_has_answer = all(
        marker.casefold() in filtered_context.casefold()
        for marker in filtered_query.answer_markers
    )
    lines.extend(
        [
            "",
            "=== A/B metadata filter for the audience-ambiguous query ===",
            f"Query: {filtered_query.question}",
            "A — no filter:",
            *format_results(unfiltered_results),
            f"Answer markers present: {'YES' if unfiltered_has_answer else 'NO'}",
            "B — metadata_filter={'audience': 'buyer'}:",
            *format_results(filtered_results),
            f"Answer markers present: {'YES' if filtered_has_answer else 'NO'}",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    output = run_benchmark()
    print(output)
    OUTPUT_PATH.write_text(f"{output}\n", encoding="utf-8")
    print(f"\nSaved benchmark output to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
