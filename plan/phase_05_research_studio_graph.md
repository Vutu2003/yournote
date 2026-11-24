# Phase 05 — Phân tích nhiều nguồn và mạng tri thức có bằng chứng

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md` và bàn giao Phase 01–04. Chỉ triển khai Phase 05.

## Mục tiêu

Sinh viên có thể đối chiếu nhiều tài liệu, tạo bản tổng hợp để học và khám phá quan hệ giữa các khái niệm. Mọi nhận định mới phải truy về bằng chứng. Bổ sung theo nghiệp vụ học tập; không biến sản phẩm thành công cụ chỉ phục vụ đọc bài báo.

## Thứ tự thực hiện trong phase

Hoàn thành luồng so sánh và báo cáo trước, sau đó mới thêm graph có phạm vi giới hạn. Dùng chung provider, scope, locator, quản lý tác vụ và cách lưu/xóa artifact từ các phase trước.

## Công việc bắt buộc

1. Bổ sung công cụ **So sánh tài liệu** và **Tổng hợp/Báo cáo** vào Studio theo hệ thiết kế hiện có. Form chỉ yêu cầu mục tiêu, nguồn và tiêu chí thực sự cần thiết; có gợi ý để sinh viên dễ bắt đầu.
2. So sánh cần ít nhất hai nguồn. Kết quả theo tiêu chí: nội dung từng nguồn, điểm giống/khác, điểm chưa đủ thông tin và citation tương ứng. Tránh việc một nguồn được truy xuất nhiều hơn khiến nguồn còn lại không được xét mà vẫn gọi là so sánh đầy đủ.
3. Phân biệt mâu thuẫn trực tiếp, khác phạm vi/điều kiện và khác cách diễn đạt. Không kết luận tài liệu mâu thuẫn chỉ vì dùng thuật ngữ khác. Nhận định về mâu thuẫn phải có bằng chứng từ các phía liên quan.
4. Tổng hợp/báo cáo gồm mục tiêu, phạm vi nguồn đã xét, các phần nội dung, kết luận có dẫn chứng và giới hạn. Hỗ trợ đề cương ôn tập hoặc giải thích chủ đề; không chỉ có mẫu báo cáo nghiên cứu học thuật.
5. Cho xem kết quả, lưu trong notebook, chuyển phần hữu ích thành ghi chú và xuất Markdown. Lưu metadata model/phạm vi nguồn/thời gian; xóa từng kết quả có xác nhận và autosave như Studio hiện tại.
6. Các tác vụ nhiều bước phải có giới hạn số nguồn/chunk/lời gọi phù hợp, kế hoạch xử lý hiển thị ngắn gọn, tiến trình và nút dừng. Không mở vòng lặp agent vô hạn; không tự gửi toàn corpus nếu người dùng chỉ chọn vài nguồn.
7. Nếu đầu ra sai schema hoặc thiếu bằng chứng, thực hiện tối đa bước sửa có giới hạn hoặc báo chưa hoàn thành. Không tự lặp gọi model không giới hạn, không lưu bản hỏng như artifact hợp lệ.
8. Bổ sung **Mạng tri thức** riêng với Mind Map. Graph có thực thể/khái niệm, cạnh có loại quan hệ và bằng chứng trích từ nguồn; dùng lại locator Phase 04.
9. Graph đầu tiên chỉ chạy theo nguồn được chọn với giới hạn rõ, đề xuất tối đa 50 node/100 cạnh. Có chính sách hợp nhất khái niệm trùng, giữ tên thay thế và tránh gộp nhầm các khái niệm khác nghĩa.
10. Cạnh mang nguồn hỗ trợ và locator; loại hoặc đánh dấu không xác nhận các quan hệ không có bằng chứng. Bấm node/cạnh xem giải thích và trích đoạn; từ đó mở đúng tài liệu/anchor.
11. Viewer graph hỗ trợ pan/zoom, tìm khái niệm và lọc theo nguồn ở mức đơn giản, dễ đọc. Có danh sách node/quan hệ để dùng trên mobile và với bàn phím. Không bắt buộc Neo4j hoặc một hệ graph database mới.
12. Graph lưu/mở/xóa/export được trong notebook, có metadata phiên bản nguồn để nhận biết dữ liệu lỗi thời. Không gọi model lại chỉ để mở một graph đã lưu.
13. Duy trì toàn bộ Summary, Quiz, Flashcards, Mind Map và Notes cũ. Cập nhật workspace schema/API/export/migration có tương thích; không dùng trường Mind Map hiện có để chứa graph mới.

## Ngoài phạm vi

- Tự tìm web, tải nguồn mới, tự chạy script, kiểm chứng thực nghiệm hoặc thực thi mã.
- Tự động hợp nhất graph của mọi notebook thành một kho tri thức chung.
- Hệ agent nghiên cứu tự hành hoặc mô phỏng toàn bộ NotebookLM/Obsidian.
- Trình soạn thảo phức tạp khi ghi chú và export hiện tại đã đáp ứng nghiệp vụ.

## Kiểm tra và tiêu chí hoàn thành

- Tạo bộ nguồn trung lập: giáo trình + slide + ghi chú, có trường hợp thống nhất, khác điều kiện và mâu thuẫn trực tiếp. Không dựa vào corpus mẫu hiện tại.
- Kiểm tra câu trả lời so sánh đề cập đủ các nguồn, citation tồn tại và hỗ trợ nhận định; thêm trường hợp hoàn toàn không tìm được bằng chứng cho một tiêu chí.
- Test graph với tên đồng nghĩa, từ đồng âm, cạnh thiếu nguồn, marker sai và graph vượt giới hạn.
- Kiểm tra mọi công cụ mới: tạo → xem → reload → mở nguồn → export → hủy xóa → xóa thật; xác nhận chỉ ảnh hưởng artifact/notebook đang thao tác.
- Test cancel/lỗi giữa nhiều bước/đổi notebook; không tạo artifact hoàn tất từ tác vụ lỗi hoặc ghi đè kết quả của notebook khác.
- Kiểm tra nguồn đổi phiên bản được thông báo đúng, không âm thầm gán citation sang nội dung khác.
- Chạy backend tests, frontend build/lint và kiểm tra theme sáng/tối, responsive, keyboard trên các viewer mới.
- Smoke test thật một so sánh nhỏ và một graph nhỏ khi có quyền inference; ghi rõ phần nào chỉ được mock.

## Cách làm việc và báo cáo

Triển khai trực tiếp, ưu tiên kết quả học tập có thể kiểm chứng. Ghi contract artifact/graph, giới hạn tác vụ và kết quả kiểm tra. Nếu phần graph chưa đạt, ghi phase chưa hoàn thành thay vì gọi Mind Map hiện có là Knowledge Graph. Dừng trước Phase 06.

## Bàn giao sau triển khai

- **Trạng thái: Hoàn thành Phase 05**, ngày 18/11/2026. Chưa bắt đầu Phase 06, không commit. Chi tiết contract/kết quả/lệnh tái kiểm tra: [báo cáo triển khai](https://github.com/Vutu2003/yournote/blob/9af3864e4beeeb1ef80e299934800a8ae5023109/reports/phase05/implementation.md).
- **Research Studio:** thêm So sánh tài liệu (2–6 nguồn, 1–6 tiêu chí), Tổng hợp/Báo cáo (đề cương ôn tập/giải thích/tổng hợp), Mạng tri thức riêng Mind Map. Cả ba có mục tiêu, nguồn, bằng chứng/locator, xem, autosave/mở lại không inference, note có quote/version, Markdown và xác nhận/hủy xóa từng artifact.
- **Schema/API:** workspace `schema_version=3`, thêm `comparison_artifacts/report_artifacts/graph_artifacts`; JSON 1/2 thiếu trường vẫn đọc được. Research result version 1 có nguồn/coverage/version, structured evidence và metadata provider/model/thời gian/usage. Task stream cũ nhận feature `comparison|report|graph`; progress thêm counts/steps/stages. Không đổi embedding/index/parser/document ID. Graph ≤50 node/100 cạnh, quan hệ có hướng và loại; chỉ gộp cùng meaning_key + label/alias trùng có căn cứ, giữ riêng từ đồng âm.
- **Giới hạn/cancel/validation:** 6 nguồn × 6 chunk, raw context 60.000 ký tự, prompt 120.000 ký tự; Compare/Report ≤N+1 calls, Graph ≤N. 0 repair tự động; sai JSON/schema/marker/quote => không completed. Cạnh graph thiếu căn cứ bị loại/đếm, hết cạnh => thất bại. Quote kiểm tra nguyên văn với chunk/version cả khi reload/export. Snapshot model/nguồn/notebook; dừng giữa bước/upstream, chỉ completed hợp lệ mới lưu; không retry quota/auth/fallback. Qdrant một worker, không giữ index lock trong network inference.
- **Bộ nguồn:** `evaluation/phase05_fixture.py`: giáo trình DOCX + slide PDF + ghi chú MD, không dùng corpus hiện tại. Có MSE thống nhất, scaling khác thuật toán, hạn LAB-A mâu thuẫn cùng nhóm, học phí hoàn toàn thiếu. Đọc thủ công smoke Compare: 12 hàng/3 nguồn, 8 supported/4 missing; 3 nhận định phân loại đúng và có hai phía. Graph thật 10 node/7 cạnh, 7/7 có quote hỗ trợ; vẫn còn một số khái niệm tương đương chưa gộp vì meaning_key khác.
- **Test mock:** baseline 144 → **160/160 backend tests**; 16 test mới bao phủ nghiên cứu/graph/model metadata, lỗi/cancel nhiều bước, scope/notebook isolation, bounds trước model, schema cũ, export và backup/rollback. Unit test không gọi dịch vụ AI. Frontend build pass; lint exit 0, 12 warning có sẵn, không thêm warning mới. Health/OpenAPI vẫn lazy, không tải embedding/RAG khi khởi động.
- **Giao diện:** Chrome headless/API giả lập, 24 bố cục (3 viewer × 4 kích thước 360/768/1280/1920 × sáng/tối), không tràn ngang/che footer, không JS error. Kiểm tra create/view/reload/citation/note/export/cancel-delete/delete, xóa cũ khi tạo mới, lỗi/quota/incomplete, đổi model/nguồn/notebook; graph pan/zoom/search/filter, keyboard/mobile lists, stale-version banner. Harness `evaluation/phase05_ui.mjs`, proof/ảnh trong `project/reports/phase05/`.
- **Inference thật:** kết nối plan đã được người dùng cấp quyền, model `gpt-6.1-terra` được kiểm tra catalog, cùng provider/TaskRegistry thật trên kho tạm. Compare 4 calls, Graph 3 calls, cả hai completed, lưu/mở lại và Markdown thành công: [public smoke proof](https://github.com/Vutu2003/yournote/blob/9af3864e4beeeb1ef80e299934800a8ae5023109/reports/phase05/live-smoke.json). Tổng 11 calls có kết quả trong quá trình: lượt đầu 4 calls Compare xong nhưng gặp lỗi export metadata; đã sửa và thêm regression trước khi chạy lại 7 calls. Report các mode chỉ kiểm tra mock, chưa smoke thật riêng. Không suy ra quota/chi phí; usage lượt đầu không còn đầy đủ.
- **Dữ liệu/vận hành:** backup nhất quán/verify 15 file ở `project/storage/backups/phase05-predeploy-20261118T143347`; trước restart đối chiếu hai DB logic không đổi và 13 tệp source/index cùng checksum. Rollback kiểm tra trên fixture. Dữ liệu thật 4 nguồn/3 notebook; frontend 5173/backend 8000 một worker, health/OpenAPI/proxy 200, 1 profile kết nối. Không reindex hoặc gọi AI trên tài liệu cá nhân.
- **Giới hạn/Phase 06:** exact quote/schema đúng chưa bảo đảm semantic entailment; cần đánh giá tài liệu dài, coverage và thử dùng thực tế. Graph chỉ trong nguồn được chọn, merge thận trọng có thể còn trùng, chưa biểu diễn phủ định riêng hay tự phân xử nguồn đúng; không phải agent/web research. Tái dùng artifact arrays/DTO/task progress và tách mock/thật; mở/export/note graph không được gọi lại model. Dừng ở Phase 05.
