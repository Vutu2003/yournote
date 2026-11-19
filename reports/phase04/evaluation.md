# Phase 04 — tài liệu và RAG có kiểm chứng

Đánh giá ngày 18/11/2026. Giữ embedding `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều), Qdrant embedded một worker và giao diện đã chốt. Không thêm reranker, web import hoặc Knowledge Graph.

## Bộ kiểm tra và cách so sánh

`evaluation/fixture.json` được tạo trước khi chỉnh retrieval: 24 đoạn, 6 nguồn giả lập cho sinh viên, 16 câu hỏi. Nội dung gồm đề cương/bài tập, đại số tuyến tính, hướng dẫn phòng thí nghiệm, hai thông báo thi mâu thuẫn, ghi chú học tập và một câu lệnh độc hại được nhúng trong nguồn. Hai câu hỏi thiếu thông tin được chấm riêng; 14 câu còn lại có nhãn chunk bằng chứng. Một câu hỏi nối tiếp có lượt hội thoại tham chiếu đã xác định.

SHA-256 fixture: `a74035280dd957478e5d538a02e2118d10df4dc9a4c4ad8c49c8fa080cf177de`.

- Baseline: vector retrieval hiện có, k=3; không thêm lịch sử. Đã ghi kết quả trước khi đổi retrieval.
- Bản mới: BM25 + vector, hợp nhất RRF (hằng số 60), cùng k=3; câu nối tiếp bổ sung tối đa hai câu hỏi trước đủ điều kiện. Không gọi thêm LLM để rewrite.
- Mỗi truy vấn đo 3 lần, lấy trung vị; chạy CPU 2 thread, embedding thật từ cache và Qdrant trong `/tmp`. Báo riêng cold load/index. Nhãn chunk dùng để đo retrieval, không coi đó là điểm semantic correctness của câu trả lời.
- Cách hợp nhất theo [bài RRF gốc](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf). Lọc nguồn/trang/phiên bản áp dụng trước vector và lexical; không tìm toàn corpus rồi mới gán nguồn.

## Kết quả retrieval thật

| Chỉ số | Baseline | Hybrid + ngữ cảnh |
| --- | ---: | ---: |
| Hit@1, 14 câu có nhãn | 78,6% | 85,7% |
| Macro recall@3, 14 câu có nhãn | 85,7% | 100% |
| Kết quả vượt selection/trang, 16 câu | 0 | 0 |
| Trung vị truy xuất | 7,56 ms | 8,29 ms |
| Cold load embedding + index fixture | 1,41 s | 1,31 s |
| Lượt gọi LLM cho retrieval/rewrite | 0 | 0 |

Dữ liệu từng câu và hash code: [baseline.json](baseline.json), [hybrid.json](hybrid.json). Cold time được ghi để tách khỏi thời gian query, không dùng chênh lệch một lần khởi động làm bằng chứng tối ưu hiệu năng.

## Kết quả câu trả lời thật

Chọn 8 tình huống đại diện, chạy cả hai phương án với model đã được người dùng kiểm chứng (`gpt-6.1-terra`), cùng provider và cùng source selection; tổng cộng **16 yêu cầu hoàn tất**, không retry hoặc đổi model. Chỉ gửi văn bản fixture tự tạo. Không đưa corpus riêng vào phép thử.

| Chỉ số | Baseline | Bản mới |
| --- | ---: | ---: |
| Đúng câu hỏi và được bằng chứng hỗ trợ, chấm thủ công | 7/8 | 8/8 |
| Hoàn tất | 8/8 | 8/8 |
| Trung vị cả retrieval + generation | 3,02 s | 3,21 s |
| Lượt gọi có kết quả | 8 | 8 |
| Input token do provider báo | 2.541 | 5.686 |
| Output token do provider báo | 342 | 272 |
| Total token do provider báo | 2.883 | 5.958 |

Tổng 8.841 token do provider báo cho 16 lượt; không quy đổi thành giá tiền hoặc phần trăm hạn mức gói. Prompt có quy tắc bằng chứng/lịch sử dài hơn làm tăng input token, dù không tăng số lượt gọi.

Khác biệt quan sát được: với “Vậy nó cần nộp những gì?”, baseline lấy yêu cầu của bài tập khác trong cùng nguồn. Marker vẫn tồn tại và đoạn được trích là thật, nhưng không hỗ trợ đúng đối tượng của câu hỏi nối tiếp. Bản mới xác định lại QZ-417 từ câu hỏi trước và trả đúng báo cáo PDF + mã Python. Đây là ví dụ vì sao kiểm tra marker không chứng minh được semantic grounding.

Cả hai phương án đều từ chối đúng câu học phí không có dữ liệu và câu deadline ngoài nguồn được chọn; đều nêu hai quy định thi khác nhau; không thực hiện lệnh độc hại trong mẫu. Các kết quả này chỉ xác nhận những tình huống đã thử.

[answers.json](answers.json) chứa toàn bộ câu trả lời, mapping citation → context và đánh giá từng trường hợp. Agent đã đọc/đối chiếu cả 16 đầu ra; đây **không phải** chấm mù bởi giảng viên hoặc người đánh giá độc lập. `evaluation/manual_review.json` khóa đánh giá bằng hash của câu trả lời, context và citations; chạy lại sinh đầu ra khác phải chấm lại, không tự tái sử dụng điểm cũ.

## Parser, viewer và hồi quy

- **144 backend tests đạt**: giữ bộ có sẵn, bổ sung PDF/DOCX/MD/TXT, định danh trùng tên/trùng kích thước, sửa phiên bản, ingest lại, ghi index dở dang, scope, lịch sử, marker, migration idempotent và rollback.
- Smoke bằng embedding MiniLM **thật** + Qdrant thật trong `/tmp`: upload → index → retrieval → resolve citation → viewer đều 200 cho cả 4 định dạng; PDF có locator trang, ba định dạng còn lại có locator đoạn. Không gọi LLM trong smoke này. Xem [format_smoke.json](format_smoke.json).
- Chrome với notebook/API giả lập: mở citation đúng anchor, HTML/script hiển thị như văn bản, điều hướng đoạn, cập nhật nguồn rồi mở lại bản cũ, chặn hỏi trên bản cũ, tải hai nguồn cùng tên khác nội dung; **16 tổ hợp** 360/768/1280/1920px × light/dark × PDF/text. Không lỗi JavaScript hoặc tràn ngang. Script/ảnh ở `/tmp/phase04-ui.mjs` và `/tmp/phase04-ui/`.
- Frontend build đạt; lint exit 0 với 12 warning có sẵn. Compileall và `git diff --check` đạt.
- Kho hiện có: 4 nguồn, 175 chunk; sau migration ID/số chunk giữ nguyên, JSON của 3 notebook giữ nguyên. Kiểm chứng 175/175 đoạn khớp bản gốc, không log văn bản riêng. Sửa lỗi chuẩn hóa dấu nối ở ranh giới chunk bằng so sánh NFKC + whitespace, giữ nguyên dấu nối/số âm; không dùng ngưỡng fuzzy matching.

## Giới hạn của kết luận

Bộ 16 câu nhỏ và do người triển khai tự tạo; không có tập test độc lập hoặc khoảng tin cậy. Câu nối tiếp so sánh cả thay đổi retrieval và thêm lịch sử, nên không gán toàn bộ cải thiện cho BM25. Tốc độ chỉ phản ánh máy và corpus nhỏ này; lexical hiện scroll các chunk trong scope và có giới hạn 20.000 chunk, chưa phải benchmark corpus lớn.

Chất lượng sinh Studio được kiểm tra schema/citation/scope và các nhánh nhiều bước bằng mock; chưa chấm semantic độc lập cho toàn bộ Quiz/Flashcards/Mind Map. Thử lệnh độc hại thành công không phải bảo đảm chống prompt injection tuyệt đối. OCR, layout Word đầy đủ, biểu thức toán/bảng phức tạp, header/footer/footnote DOCX, import URL và PPTX/XLSX chưa nằm trong phạm vi hỗ trợ.
