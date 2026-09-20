# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Phạm Thị Ngọc Anh
**Nhóm:** G16
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

Độ tương tự cosine cao nghĩa là hai vector gần cùng hướng, nên hai đoạn văn thường có nội dung hoặc ý nghĩa gần nhau. Giá trị càng gần 1 thì mức tương đồng càng cao; gần 0 là ít liên quan và gần -1 là ngược hướng.

**Ví dụ có độ tương tự CAO:**

- Câu A: “Shopee hoàn tiền về thẻ tín dụng trong 7 đến 14 ngày làm việc.”
- Câu B: “Tiền hoàn vào thẻ tín dụng Shopee mất từ 7 đến 14 ngày làm việc.”
- Tại sao tương đồng: Hai câu dùng cách diễn đạt khác nhau nhưng cùng nói về một phương thức và thời gian hoàn tiền.

**Ví dụ có độ tương tự THẤP:**

- Câu A: “Khách hàng có thể gửi tranh chấp sau bán hàng.”
- Câu B: “Python là một ngôn ngữ lập trình.”
- Tại sao khác: Một câu thuộc chính sách thương mại điện tử, câu còn lại thuộc lĩnh vực lập trình và không có chung ý nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

Cosine tập trung vào hướng của vector thay vì độ lớn tuyệt đối, nên phù hợp hơn khi cần so sánh ý nghĩa của văn bản có độ dài khác nhau. Với embedding đã chuẩn hóa, điểm cosine dễ diễn giải và dùng để xếp hạng kết quả.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

Mỗi chunk mới tiến thêm `500 - 50 = 450` ký tự. Số chunk được tính bằng `ceil((10,000 - 500) / 450) + 1 = 23`.

**Đáp án: 23 chunks.**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

Khi overlap tăng lên 100, bước nhảy còn 400 ký tự và số chunk tăng thành `ceil((10,000 - 500) / 400) + 1 = 25`. Overlap lớn hơn giúp giữ thông tin nằm sát ranh giới giữa hai chunk, nhưng đổi lại sẽ tốn thêm dung lượng lưu trữ và chi phí embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`**:

Mình dùng regex `(?<=[.!?])\s+|\n` để tách sau dấu chấm, chấm than, chấm hỏi hoặc khi xuống dòng. Sau đó mình bỏ các phần rỗng, loại khoảng trắng thừa và gom tối đa `max_sentences_per_chunk` câu. Giá trị số câu tối đa được chặn dưới ở 1, còn văn bản rỗng trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split`**

Mình thử lần lượt các dấu phân cách theo mức ưu tiên: đoạn văn, xuống dòng, dấu chấm, khoảng trắng, rồi mới cắt theo ký tự. Nếu một phần vẫn dài hơn `chunk_size`, hàm gọi đệ quy với dấu phân cách tiếp theo. Base case là văn bản đã đủ ngắn, hết separator, hoặc separator rỗng; riêng trường hợp `""` được cắt trực tiếp theo `chunk_size` để tránh lỗi `split("")` của Python.

**`HeadingChunker.chunk`** — chiến lược benchmark của mình:

Mình tách tài liệu trước mỗi heading Markdown và giữ cả chuỗi heading cha–con trong chunk. Nếu một section vượt quá 800 ký tự, phần thân được chia tiếp bằng `RecursiveChunker`, sau đó tiêu đề được gắn lại vào từng mảnh con. Nhờ vậy, chunk thứ hai trở đi vẫn cho biết nó đang thuộc điều khoản nào.

### Lớp EmbeddingStore

**`add_documents` + `search`**:

Mỗi `Document` được chuyển thành record gồm id, nội dung, metadata và embedding. Store thử đồng bộ sang ChromaDB nếu thư viện có sẵn, đồng thời giữ bản trong bộ nhớ để vẫn chạy ổn định khi ChromaDB không khả dụng. Khi tìm kiếm, mình tạo embedding cho câu hỏi, tính dot product với từng record rồi sắp xếp điểm giảm dần; với vector đã chuẩn hóa thì dot product tương đương cosine similarity.

**`search_with_filter` + `delete_document`**:

`search_with_filter` lọc record theo tất cả cặp key-value trong metadata trước rồi mới tính điểm, nhờ vậy không xếp hạng các tài liệu ngoài phạm vi. `delete_document` xóa toàn bộ chunk có cùng `metadata["doc_id"]`, đồng bộ thao tác xóa sang ChromaDB nếu đang sử dụng và trả về `True` khi thực sự có dữ liệu bị xóa.

### Tác tử KnowledgeBaseAgent

**`answer`**:

Agent gọi `store.search(question, top_k)` rồi đánh số các chunk lấy được và ghép chúng vào phần `Context`. Prompt yêu cầu mô hình chỉ trả lời dựa trên ngữ cảnh, đồng thời nói rõ là không đủ thông tin nếu các chunk không chứa câu trả lời. Câu hỏi được đặt sau context và toàn bộ prompt được truyền qua `llm_fn`, nên có thể thay LLM thật hoặc hàm giả lập khi kiểm thử.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
=============================== test session starts ================================
platform darwin -- Python 3.11.14, pytest-9.0.2, pluggy-1.6.0 -- /opt/homebrew/opt/python@3.11/bin/python3.11
cachedir: .pytest_cache
rootdir: /Users/ngocanh/K4-DAY07-PhamThiNgocAnh-02831
plugins: anyio-4.15.1, cov-7.0.0
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED[  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED       [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED  [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED        [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possiblePASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separatorPASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED       [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED  [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

================================ 42 passed in 0.04s ================================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Shopee hoàn tiền về thẻ tín dụng trong 7 đến 14 ngày làm việc. | Tiền hoàn vào thẻ tín dụng Shopee mất từ 7 đến 14 ngày làm việc. | Cao | 0.037790 | Không |
| 2 | Người bán chịu phí trả hàng nếu lỗi thuộc về người bán. | Khi người bán giao sai sản phẩm, phí hoàn hàng do người bán thanh toán. | Cao | 0.162364 | Không |
| 3 | TikTok Shop khuyến nghị tỷ lệ trả hàng do lỗi người bán dưới 1,5%. | Mục tiêu của người bán là giữ tỷ lệ hoàn trả do lỗi của mình thấp hơn 1,5%. | Cao | 0.032124 | Không |
| 4 | Shopee xử lý yêu cầu trả hàng và hoàn tiền. | Hôm nay thời tiết ở Hà Nội có mưa. | Thấp | 0.068052 | Có |
| 5 | Khách hàng có thể gửi tranh chấp sau bán hàng. | Python là một ngôn ngữ lập trình bậc cao. | Thấp | 0.019137 | Có |

Các điểm trên được đo bằng `MockEmbedder` 64 chiều của dự án; mình quy ước điểm từ 0.5 trở lên là cao cho phần đối chiếu này.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

Ba cặp đầu có nghĩa gần như giống nhau nhưng điểm lại rất thấp. Lý do là `MockEmbedder` sinh vector từ mã băm của toàn bộ chuỗi nên chỉ bảo đảm tính lặp lại cho kiểm thử, chứ không học quan hệ ngữ nghĩa giữa các từ. Điều này cho thấy muốn đánh giá retrieval thật sự thì cần một mô hình embedding ngữ nghĩa; mock embedding chỉ phù hợp để kiểm tra luồng chương trình.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Mình dùng 8 file trong `data/ecommerce-policies/`, tách frontmatter khỏi nội dung rồi chia phần thân bằng `HeadingChunker(chunk_size=800)`. Section dài được hạ xuống `RecursiveChunker`, nhưng heading vẫn được gắn lại vào từng mảnh con. Tổng cộng có 85 chunk; backend là `_mock_embed` và mỗi câu lấy `top_k=3`. Đây cũng là đúng 5 câu benchmark chung đã ghi trong `REPORT_NHOM.md`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Shopee hoàn tiền về thẻ tín dụng hoặc thẻ ghi nợ trong bao lâu? | `shopee-return-refund-policy#15`: nói về xử lý yêu cầu, không có mốc hoàn tiền theo thẻ | 0.250171 | Không | Không đủ ngữ cảnh để trả lời; gold answer là 7–14 ngày làm việc. |
| 2 | Người mua Shopee được gửi yêu cầu trả hàng/hoàn tiền trong bao lâu sau khi giao hàng thành công, và thực phẩm tươi sống có ngoại lệ gì? | `shopee-return-refund-policy#19`: đúng tài liệu nhưng sai section | 0.321098 | Không ở mức nội dung | Top-3 không chứa đủ hai mốc 15 ngày và 24 giờ nên agent không nên suy đoán. |
| 3 | Tôi có thể hủy đơn vào lúc nào và việc hủy đơn có hậu quả gì? | `shopee-buyer-return-request#0`; chunk gold `tiktok-buyer-order-cancellation#0` ở hạng 2 | 0.099288 | Có trong top-3 sau khi lọc `audience=buyer` | Người mua thường có thể hủy trước trạng thái đang vận chuyển; việc hủy không gây hậu quả cho người bán, trừ lý do “Giao hàng trễ”. |
| 4 | Những trường hợp nào được tính và không được tính vào tỷ lệ trả hàng/hoàn tiền do lỗi người bán của TikTok Shop? | `tiktok-after-sale-dispute#10`: nói về phản đối tranh chấp, sai nội dung | 0.347998 | Không | Không đủ ngữ cảnh để liệt kê chính xác các trường hợp được tính và loại trừ. |
| 5 | Trong tranh chấp sau bán hàng TikTok Shop, người bán có bao lâu để gửi tài liệu, nền tảng có bao lâu để ra quyết định và hai bên có bao lâu để phản đối? | `shopee-return-refund-policy#9`: sai nền tảng; gold doc có ở hạng 2/3 nhưng sai section | 0.293027 | Không ở mức nội dung | Context không chứa đủ ba mốc; gold answer lần lượt là 24 giờ, 72 giờ và 48 giờ. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3? 1 / 5**

Theo cách chấm ở mức nội dung trong `docs/SCORING.md`, mình tự chấm phần này 1/10: câu 3 có chunk chứa đáp án ở hạng 2 nên đạt 1 điểm; bốn câu còn lại không có đủ thông tin trả lời trong top-3. Nếu chỉ nhìn `doc_id`, câu 2 và 5 dễ bị chấm nhầm là đúng dù section truy xuất không chứa số liệu cần thiết.

Ở câu 3, A/B cho kết quả khá rõ: không filter thì top-3 không chứa đủ dấu hiệu đáp án; dùng `metadata_filter={"audience": "buyer"}` thì chunk buyer chứa đáp án xuất hiện ở hạng 2. Kết quả tổng thể vẫn thấp vì `MockEmbedder` băm chuỗi chứ không hiểu ngữ nghĩa; do đó số liệu này chủ yếu giúp kiểm tra pipeline và phân tích lỗi, chưa phản ánh chất lượng của `HeadingChunker` khi dùng embedding thật.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

Điều mình thấy rõ nhất khi đối chiếu các cách làm là chunking và metadata phải được thiết kế cùng nhau. Chunk nhỏ giúp kết quả tập trung hơn, nhưng nếu cắt mất câu trước hoặc tiêu đề thì nội dung lại khó hiểu; ngược lại, metadata như `platform`, `category` và `audience` có thể loại bỏ tài liệu sai nền tảng trước khi xếp hạng. Nếu làm vòng tiếp theo, mình sẽ dùng semantic embedding đa ngôn ngữ và so sánh riêng kết quả có/không có metadata filter.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 1 / 10 |
| **Tổng phần cá nhân** | **51 / 60** |
