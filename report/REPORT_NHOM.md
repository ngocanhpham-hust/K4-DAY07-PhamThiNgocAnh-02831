# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** G16
**Thành viên:** Phan Duy Thành · Võ Đức Tài · Phạm Thị Ngọc Anh · Đỗ Đình Long
**Ngày:** 2026-09-20

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, hoàn tiền và quy định nhà bán hàng trên sàn thương mại điện tử **Lazada** (chủ đề bắt buộc của lớp K4-L3B theo `K4_VARIANT.md`).

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề này vì ba lý do. Thứ nhất, đây là chủ đề bắt buộc của L3B và gắn trực tiếp với trải nghiệm mua sắm thật của người dùng. Thứ hai, văn bản chính sách của Lazada được biên soạn sẵn theo từng mục/điều khoản (`## Bước 1`, `## Khung thời gian hoàn tiền`…), là điều kiện lý tưởng để so sánh các chiến lược chunking khác nhau. Thứ ba, corpus chứa cả tài liệu dành cho **người mua** lẫn **người bán** nói về cùng chủ đề trả hàng nhưng có đáp án khác nhau — nhờ đó nhóm chứng minh được giá trị của metadata filter.

### Danh sách tài liệu (Data Inventory)

| #   | Tên tài liệu                         | Nguồn (Source URL)                                        | Ngày lấy / Phiên bản             | Số ký tự | Metadata đã gán                                       |
| --- | ------------------------------------ | --------------------------------------------------------- | -------------------------------- | -------- | ----------------------------------------------------- |
| 1   | `lazada-thong-tin-tra-hang`          | helpcenter.lazada.vn/s/faq (categoryId=101398409)         | 2026-09-20 / not-stated          | 4.852    | audience=buyer, category=returns-policy, language=vi  |
| 2   | `lazada-san-pham-khong-duoc-tra-lai` | helpcenter.lazada.vn/s/faq (categoryId=101398409)         | 2026-09-20 / not-stated          | 3.029    | audience=buyer, category=returns-policy, language=vi  |
| 3   | `lazada-cach-tra-hang`               | helpcenter.lazada.vn/s/faq (categoryId=101398409)         | 2026-09-20 / not-stated          | 4.466    | audience=buyer, category=returns-process, language=vi |
| 4   | `lazada-tra-hang-bi-tu-choi`         | helpcenter.lazada.vn/s/faq (categoryId=101398409)         | 2026-09-20 / not-stated          | 2.042    | audience=buyer, category=returns-appeal, language=vi  |
| 5   | `lazada-chinh-sach-hoan-tien`        | helpcenter.lazada.vn/s/faq (categoryId=101400309)         | 2026-09-20 / not-stated          | 4.695    | audience=buyer, category=refund-policy, language=vi   |
| 6   | `lazada-khi-nao-nhan-tien-hoan`      | helpcenter.lazada.vn/s/faq (categoryId=101400323)         | 2026-09-20 / not-stated          | 2.864    | audience=buyer, category=refund-process, language=vi  |
| 7   | `lazada-yeu-cau-hoan-tien`           | helpcenter.lazada.vn/s/faq (categoryId=101400309)         | 2026-09-20 / not-stated          | 4.374    | audience=buyer, category=refund-process, language=vi  |
| 8   | `lazada-cach-yeu-cau-hoan-tien`      | helpcenter.lazada.vn/s/faq (categoryId=101397361)         | 2026-09-20 / not-stated          | 1.144    | audience=buyer, category=refund-process, language=vi  |
| 9   | `lazada-dieu-khoan-nha-ban-hang`     | sellercenter.lazada.vn/helpcenter (categoryId=1000028750) | 2026-09-20 / hiệu lực 2026-09-29 | 6.611    | audience=seller, category=seller-policy, language=vi  |

**Tổng:** 9 tài liệu · ~34.077 ký tự (đạt yêu cầu 5–10 tài liệu). File `sources.csv` khớp 1-1 với 9 file `.md`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ. Cả 9 trang đều nằm trong Help Center / Seller Center công khai của Lazada và được crawler kiểm `robots.txt` trước khi tải.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata. Tám tài liệu ghi `not-stated` vì trang nguồn không nêu số hiệu; riêng điều khoản nhà bán hàng có ngày hiệu lực `2026-09-29` (nhóm **không bịa** số hiệu khi nguồn không nêu).

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata    | Kiểu                         | Ví dụ giá trị                                       | Tại sao hữu ích cho truy xuất (retrieval)?                                                                                        |
| ------------------ | ---------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `doc_id`           | string                       | `lazada-cach-tra-hang`                              | Khoá nối chunk về **file gốc** (id chunk có dạng `file#i`); `delete_document` dựa vào đây để xoá đủ mọi chunk của một tài liệu.   |
| `title`            | string                       | `Cách trả hàng trên Lazada`                         | Hiển thị nguồn trong prompt, giúp agent trích dẫn và người đọc truy vết câu trả lời.                                              |
| `audience`         | enum `buyer`/`seller`/`both` | `buyer`, `seller`                                   | ⭐ Trục lọc quan trọng nhất: tách chính sách người mua khỏi người bán khi hai tài liệu cùng chủ đề nhưng khác đáp án (xem câu Q5). |
| `category`         | string                       | `returns-process`, `refund-policy`, `seller-policy` | Lọc theo nhóm quy trình (trả hàng / hoàn tiền / khiếu nại) để thu hẹp tập ứng viên trước khi xếp hạng.                            |
| `language`         | string                       | `vi`                                                | Lọc theo ngôn ngữ — hữu ích khi corpus mở rộng sang bản dịch tiếng Anh.                                                           |
| `source_url`       | string                       | `https://helpcenter.lazada.vn/...`                  | Bắt buộc cho provenance — truy vết mọi câu trả lời về trang gốc.                                                                  |
| `retrieved_at`     | date                         | `2026-09-20`                                        | Kiểm tra độ mới của dữ liệu; cảnh báo khi chính sách đã thay đổi.                                                                 |
| `document_version` | string                       | `"2026-09-29"` / `"not-stated"`                     | Ngày hiệu lực của văn bản quy định; chỉ ghi khi nguồn thực sự nêu.                                                                |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Đã chạy `ChunkingStrategyComparator().compare(body, chunk_size=300)` trên 3 tài liệu đại diện (đã **bỏ frontmatter** trước khi đo để không tính cả khối YAML):

| Tài liệu                         | Chiến lược (Strategy)            | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không?                                    |
| -------------------------------- | -------------------------------- | -------------- | ----------------- | ----------------------------------------------------------- |
| `lazada-thong-tin-tra-hang`      | FixedSizeChunker (`fixed_size`)  | 16             | 282,4             | Chưa — cắt giữa câu, sinh mảnh vụn                          |
| `lazada-thong-tin-tra-hang`      | SentenceChunker (`by_sentences`) | 9              | 499,0             | Có — trọn câu, nhưng gộp nhiều mục vào một chunk dài        |
| `lazada-thong-tin-tra-hang`      | RecursiveChunker (`recursive`)   | 20             | 224,1             | Khá — bám ranh giới dòng/đoạn nhưng nhiều chunk nhỏ         |
| `lazada-cach-tra-hang`           | FixedSizeChunker (`fixed_size`)  | 14             | 294,9             | Chưa — cắt giữa các bước quy trình                          |
| `lazada-cach-tra-hang`           | SentenceChunker (`by_sentences`) | 16             | 254,9             | Có — mỗi chunk trọn câu                                     |
| `lazada-cach-tra-hang`           | RecursiveChunker (`recursive`)   | 16             | 256,4             | Khá                                                         |
| `lazada-dieu-khoan-nha-ban-hang` | FixedSizeChunker (`fixed_size`)  | 21             | 297,2             | Chưa                                                        |
| `lazada-dieu-khoan-nha-ban-hang` | SentenceChunker (`by_sentences`) | 10             | 621,6             | Có nhưng chunk **quá dài** (>600 ký tự) → dễ loãng tín hiệu |
| `lazada-dieu-khoan-nha-ban-hang` | RecursiveChunker (`recursive`)   | 29             | 213,4             | Khá — nhiều chunk nhỏ, có nguy cơ vụn                       |

**Nhận xét baseline:** `by_sentences` cho **ít chunk nhất** nhưng độ dài trung bình lớn và **biến động mạnh** (255 → 622 ký tự) vì không kiểm soát kích thước. `recursive` sinh **nhiều chunk nhỏ nhất và đều nhất** nhưng chưa tận dụng tiêu đề điều khoản. `fixed_size` nằm giữa nhưng **cắt qua ranh giới câu** — đúng điểm yếu dự kiến của baseline.

### Chiến lược của từng thành viên

> Nhóm G16 có **4 thành viên**, mỗi người thử một chiến lược khác nhau trên cùng bộ tài liệu.

**Thành viên 1 — Phan Duy Thành**
- **Loại chiến lược:** FixedSize — `FixedSizeChunker(chunk_size=300, overlap=50)` (baseline)
- **Mô tả & lý do chọn cho chủ đề này:** Tôi nhận vai baseline để cả nhóm có mốc so sánh “cách cắt ngây thơ”. Cửa sổ trượt 300 ký tự với overlap 50 giữ liên kết ở ranh giới cắt; chọn chunk nhỏ để mỗi chunk tập trung vào một ý, đổi lại phải chấp nhận việc cắt giữa câu.
- **Code snippet (nếu custom):** Không cần — dùng chunker viết sẵn trong `src/chunking.py`.

**Thành viên 2 — Võ Đức Tài**
- **Loại chiến lược:** Sentence — `SentenceChunker(max_sentences_per_chunk=3)`
- **Mô tả & lý do chọn:** Văn bản chính sách được viết thành câu hoàn chỉnh, mỗi câu thường chứa trọn một điều kiện hoặc một mốc thời gian. Tách theo câu nên không bị ngắt đôi mệnh đề như FixedSize, rất phù hợp với các câu hỏi tra số liệu và hỏi điều kiện.
- **Code snippet (nếu custom):** Không cần — dùng chunker viết sẵn.

**Thành viên 3 — Phạm Thị Ngọc Anh**
- **Loại chiến lược:** Custom — `HeadingChunker(chunk_size=400)`, chia theo tiêu đề/mục (`##`) của điều khoản gốc *(chiến lược bắt buộc của vai R3)*
- **Mô tả & lý do chọn:** Mỗi `##` trong văn bản Lazada đã là một đơn vị ngữ nghĩa trọn vẹn (một bước quy trình, một điều khoản). Cắt theo heading giữ nguyên cấu trúc do người soạn chính sách chia sẵn; mục nào dài quá ngưỡng thì hạ xuống `RecursiveChunker` **và gắn lại tiêu đề vào từng mảnh con** để mảnh thứ hai trở đi không mất ngữ cảnh “mục này nói về cái gì”.
- **Code snippet (nếu custom):**
```python
class HeadingChunker:
    def __init__(self, chunk_size: int = 400) -> None:
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        parts = re.split(r"(?m)(?=^#{1,6}\s)", text)
        sections = [part.strip() for part in parts if part.strip()]
        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue
            lines = section.split("\n", 1)
            heading = lines[0].strip() if lines and lines[0].lstrip().startswith("#") else ""
            body = lines[1] if len(lines) > 1 and heading else section
            for piece in RecursiveChunker(chunk_size=self.chunk_size).chunk(body):
                chunks.append(f"{heading}\n{piece}" if heading else piece)
        return chunks
```

**Thành viên 4 — Đỗ Đình Long**
- **Loại chiến lược:** Recursive — `RecursiveChunker(chunk_size=300)`
- **Mô tả & lý do chọn:** Thử separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]` để cắt bằng ranh giới “to” (đoạn → dòng → câu) trước, chỉ khi mảnh vẫn quá dài mới hạ xuống separator nhỏ hơn. Cách này giữ ngữ nghĩa mà vẫn kiểm soát được kích thước chunk.
- **Code snippet (nếu custom):** Không cần — dùng chunker viết sẵn.

### So Sánh Giữa Các Thành Viên

| Thành viên        | Chiến lược (Strategy)       | Điểm truy xuất (/10) | Điểm mạnh                                                                     | Điểm yếu                                                           |
| ----------------- | --------------------------- | -------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Phan Duy Thành    | FixedSize (300, overlap 50) | 4                    | Đơn giản, số chunk đều, dự đoán được; overlap chống đứt thông tin ở ranh giới | Cắt giữa câu / giữa bước quy trình → chunk mất nghĩa               |
| Võ Đức Tài        | Sentence (3 câu/chunk)      | 6                    | Giữ trọn câu, không ngắt mệnh đề điều kiện                                    | Độ dài chunk biến động lớn (255–622 ký tự), bỏ qua cấu trúc mục    |
| Phạm Thị Ngọc Anh | Heading (400) — custom      | 7                    | Khớp trực tiếp cấu trúc điều khoản; mỗi chunk là một mục trọn vẹn             | Mục quá dài phải hạ xuống recursive; phụ thuộc tài liệu có heading |
| Đỗ Đình Long      | Recursive (300)             | 5                    | Bám ranh giới đoạn/dòng, kiểm soát được kích thước                            | Sinh nhiều chunk nhỏ; chưa tận dụng tiêu đề điều khoản             |

> ⚠️ **Cách đọc bảng điểm:** đây là **tự đánh giá định hướng** của nhóm. Vì benchmark chạy bằng `MockEmbedder` (băm MD5, không mã hoá ngữ nghĩa), điểm similarity không dùng để xếp hạng được — nhóm chốt điểm chủ yếu theo **độ mạch lạc chunk** + kết quả A/B metadata filter + số liệu `count`/`avg_length` ở bảng baseline.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **`HeadingChunker`** tốt nhất cho chủ đề chính sách. Văn bản quy định của Lazada đã được biên soạn theo từng mục (`## Bước 1`, `## Khung thời gian hoàn tiền`…), nên mỗi heading vốn là một đơn vị ngữ nghĩa trọn vẹn do chính người soạn chia sẵn; cắt theo heading biến mỗi chunk thành một “điều khoản mini” thay vì một mảnh cắt cơ học. `SentenceChunker` đứng nhì vì giữ trọn câu nhưng không kiểm soát độ dài. `FixedSize` hữu ích đúng ở vai baseline: nó cho thấy cắt thuần theo ký tự sẽ phá cấu trúc điều khoản — bằng chứng âm để nhóm biện luận vì sao nên chunk theo cấu trúc.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| #   | Câu hỏi (Query)                                                                             | Câu trả lời chuẩn (Gold Answer)                                                                                                                                                                 | Chunk nào chứa thông tin?                                                                                         |
| --- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | Sản phẩm LazMall & CHOICE được hoàn trả trong bao lâu?                                      | **30 ngày** kể từ ngày giao hàng (sản phẩm Marketplace & LazGlobal: 15 ngày; Taobao: 15 ngày)                                                                                                   | `lazada-thong-tin-tra-hang` — mục “Thông tin về việc trả hàng trên Lazada” / bảng “Thời gian hoàn trả tiêu chuẩn” |
| 2   | Thanh toán bằng ví MoMo thì bao lâu nhận được tiền hoàn?                                    | **Trong vòng 48 giờ** (nhóm Ví điện tử: MoMo, ZaloPay, Viettel Money, VNPT Money)                                                                                                               | `lazada-khi-nao-nhan-tien-hoan` — bảng “Khung thời gian hoàn tiền”                                                |
| 3   | Những loại sản phẩm nào không được trả lại?                                                 | Hàng dễ hỏng, đồ tạp hóa, đồ bơi, đồ lót, quần áo bà bầu, đồ dùng giải trí/đồ chơi kích thích; (nhóm không đủ điều kiện **cả** trả hàng lẫn hoàn tiền: hàng kỹ thuật số/voucher, sản phẩm ô tô) | `lazada-san-pham-khong-duoc-tra-lai` — mục “Các loại thường không được chấp nhận trả lại”                         |
| 4   | Để trả hàng với lý do “Tôi đổi ý”, sản phẩm cần điều kiện gì?                               | Sản phẩm còn **nguyên trạng ban đầu** (hoàn hảo, không mùi, sạch sẽ), phải trả lại **đầy đủ phụ kiện/quà tặng**, còn đúng mô tả; sản phẩm phải có logo “Tôi đổi ý”                              | `lazada-thong-tin-tra-hang` — FAQ “Câu hỏi 2”; điều kiện chung ở `lazada-cach-tra-hang` — “Bước 1”                |
| 5   | Khi sản phẩm phải thu hồi, ai phải thông báo và trong bao lâu? *(filter `audience=seller`)* | **Nhà bán hàng** phải thông báo **bằng văn bản cho Lazada** trong vòng **24 giờ** kể từ khi biết vấn đề, kèm đầu mối tiếp nhận sản phẩm                                                         | `lazada-dieu-khoan-nha-ban-hang` — “Phụ Lục Quốc Gia — Việt Nam”                                                  |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

> **Lưu ý cách chấm của nhóm:** vì cả nhóm chạy trên `MockEmbedder`, thứ hạng trong top-3 là nhiễu nên không thể kết luận theo `score`. Nhóm vì thế chấm ở **mức nội dung**: khai báo chuỗi bằng chứng cho mỗi gold answer rồi kiểm chuỗi đó có nằm trong ngữ cảnh truy xuất được hay không, thay vì chỉ kiểm `doc_id` (cách chấm theo `doc_id` dễ thổi phồng kết quả).

| #   | Câu hỏi                                            | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3?  | Ghi chú                                                                                         |
| --- | -------------------------------------------------- | ------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1   | LazMall & CHOICE hoàn trả bao lâu?                 | Heading                         | Có (mức nội dung)                | Bảng “Thời gian hoàn trả tiêu chuẩn” nằm trọn trong một heading chunk; FixedSize cắt ngang bảng |
| 2   | MoMo hoàn tiền bao lâu?                            | Heading / Recursive             | Có (mức nội dung)                | Bảng “Khung thời gian hoàn tiền” bị FixedSize xẻ đôi                                            |
| 3   | Sản phẩm không được trả lại?                       | Heading                         | Có (mức nội dung)                | Danh sách nằm trong đúng một mục `##`                                                           |
| 4   | Điều kiện “Tôi đổi ý”?                             | Sentence / Heading              | Có (mức nội dung)                | Điều kiện nằm trong FAQ “Câu hỏi 2”; chunk trọn câu đọc ra ngay                                 |
| 5   | Thu hồi — ai thông báo, bao lâu? *(filter seller)* | Heading                         | Có (mức nội dung + mức tài liệu) | Filter `audience=seller` thu hẹp về đúng tài liệu nhà bán trước khi xếp hạng                    |

**Số câu có chunk liên quan trong top-3 (mức nội dung, best-of-3 chiến lược):** 5 / 5
**Số câu đạt mức 2 điểm nếu dùng embedder thật:** nhóm kỳ vọng 3–4 / 5 (câu 1, 3, 5 vững; câu 2 và 4 phụ thuộc chất lượng embedding).

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Có, rõ nhất ở câu Q5.** Q5 (“khi sản phẩm phải thu hồi, ai phải thông báo và trong bao lâu?”) cố tình **không nêu người hỏi là ai**, trong khi corpus có hai nhóm tài liệu cùng nói về trả hàng nhưng khác đối tượng và khác đáp án: nhóm `buyer` (8 tài liệu) và tài liệu `seller` (`lazada-dieu-khoan-nha-ban-hang`). Khi chạy A/B, **không lọc** thì tài liệu người mua tràn vào top-3 và agent dễ trả lời sai đối tượng; khi thêm `metadata_filter={"audience": "seller"}` thì tập ứng viên thu về đúng tài liệu nhà bán và chunk chứa đáp án (thông báo trong 24 giờ) lọt top-3. Điểm đáng chú ý: **filter vẫn hiệu quả kể cả khi embedding là mock**, tức metadata filter là cơ chế độc lập với chất lượng embedding. Đánh đổi: filter quá chặt sẽ giảm recall — nếu sau này gộp cả hai đối tượng vào một file `audience: both` thì filter mất tác dụng, nên nhóm **tách tài liệu theo audience ngay từ khâu thu thập**.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Chấm hai mức khác nhau cho ra hai kết luận khác nhau.** Một chiến lược có thể chiếm trọn cả 3 slot top-3 bằng tài liệu đúng mà **không chunk nào chứa câu trả lời** — chuyện này đặc biệt dễ xảy ra với chunker theo heading, vì các mục trong cùng một tài liệu có điểm gần bằng nhau nên việc mục nào lọt top-3 gần như ngẫu nhiên. Vì vậy nhóm bắt buộc kiểm thêm mức nội dung (chuỗi bằng chứng), không chỉ kiểm `doc_id`.
> 2. **Metadata filter hoạt động độc lập với chất lượng embedding.** Ở Q5, filter `audience=seller` vẫn lọc đúng tài liệu dù chạy bằng `MockEmbedder` — chứng minh filter là “lưới an toàn” đáng tin hơn similarity score khi embedding chưa tốt.
> 3. **Chiến lược thắng phụ thuộc cấu trúc văn bản, không phải tham số.** Với văn bản quy định chia theo mục, `HeadingChunker` thắng; nếu đổi sang dữ liệu dạng chat/FAQ không có heading thì `SentenceChunker` sẽ hợp hơn — đây là bài học về việc đọc cấu trúc tài liệu **trước khi** chọn chunker.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ 9 tài liệu nhưng bốn chiến lược cho ra bốn “hình dạng” dữ liệu rất khác nhau: baseline trên `lazada-thong-tin-tra-hang` cho `fixed_size` 16 chunk (282 ký tự/chunk), `by_sentences` 9 chunk (499 ký tự), `recursive` 20 chunk (224 ký tự). `by_sentences` ít chunk nhất nhưng độ dài biến động mạnh (255–622 ký tự), còn `recursive` đều nhất nhưng nhiều mảnh nhỏ. Điều nhóm nhận ra: **khác biệt không nằm ở việc “cắt to hay nhỏ” mà ở việc chunk có trùng với đơn vị ngữ nghĩa của văn bản hay không** — chunker theo heading tạo ra chunk = một mục trọn vẹn, nên câu trả lời nằm gọn trong một chunk thay vì rải qua nhiều chunk.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> 1. **Bật embedder thật ngay từ đầu buổi** (Local multilingual / OpenAI / Gemini) và cài đặt sẵn từ lúc code để tải nền, thay vì để `MockEmbedder` chi phối toàn bộ benchmark — đây là thay đổi quan trọng nhất.
> 2. **Chốt corpus và 5 câu hỏi chung trước khi mỗi người chạy**, để mọi kết quả so sánh được trên cùng một thước đo (hiện tại mỗi thành viên thử trên dữ liệu riêng nên chỉ so được ở mức chiến lược).
> 3. **Thử thêm hybrid search (BM25 + vector) và reranking**, đồng thời chuẩn hoá `chunk_size` theo số token thay vì ký tự để ổn định giữa các tài liệu dài ngắn khác nhau.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá |
| ---------------------------------------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10           |
| Thiết kế chiến lược (Strategy Design)    | 12 / 15          |
| Chất lượng truy xuất (Retrieval Quality) | 7 / 10           |
| Thuyết trình (Demo)                      | 4 / 5            |
| **Tổng phần nhóm**                       | **32 / 40**      |
