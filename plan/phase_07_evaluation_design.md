# Phase 07 — Thiết kế và chuẩn bị dữ liệu đánh giá

Hãy làm việc trong workspace `/home/vutu/Desktop/rag_notebooklm`, với mã ứng dụng ở `project/`. Đọc [kế hoạch chung](00_README.md) và [bàn giao Phase 06](phase_06_evaluation_release.md#bàn-giao-sau-triển-khai). Chỉ triển khai Phase 07.

## Mục tiêu

Chuẩn bị một phép đo có thể lặp lại cho ba câu hỏi. YourNote trả lời đúng và đủ đến đâu? Trích dẫn có dẫn về đúng vị trí và hỗ trợ nhận định không? Mỗi câu hỏi mất bao lâu? Chốt dữ liệu, rubric và cấu hình trước khi thu kết quả trên bộ đánh giá mới.

## Công việc

1. Rà bộ dữ liệu, chính sách chấm và runner trong `project/evaluation/phase06/`. Ghi phần có thể dùng lại và phần cần chỉnh. Phase 06 đã có 30 câu tự tạo, một mô hình thực và một tập đối chiếu retrieval nhỏ. Nếu bản xuất kết quả chi tiết vắng trong cây làm việc, tra lịch sử Git ở chế độ đọc hoặc dẫn bản bàn giao. Đánh dấu rõ số liệu nào có thể kiểm tra từ từng câu.
2. Tạo bộ đánh giá mới khoảng **24 câu** từ 4–6 tài liệu học tập tự tạo hoặc được phép sử dụng, ưu tiên PDF có lớp văn bản, DOCX và Markdown hoặc TXT. Gợi ý chia đều thành 6 câu một nguồn, 6 câu nhiều nguồn, 6 câu thiếu hoặc chỉ có một phần bằng chứng và 6 câu hỏi nối tiếp. Dùng thêm 2–4 câu riêng để thử quy trình. Giữ bộ 24 câu tách khỏi câu thử và phần chỉnh prompt. Dùng câu hỏi tiếng Việt bám thao tác đọc tài liệu.
3. Với mỗi câu, ghi ID, nhóm, phạm vi nguồn hoặc trang, mệnh đề cần trả lời, cách xử lý khi thiếu bằng chứng, đoạn nguồn chuẩn và vị trí PDF hoặc đoạn văn. Với câu có mâu thuẫn, gắn bằng chứng của từng phía và mô tả câu trả lời kỳ vọng khi tài liệu chưa đủ để phân xử. Với câu nối tiếp, ghi lịch sử đã hoàn tất và đối tượng mà câu hỏi đang tham chiếu. Kiểm tra đoạn chuẩn trên chính tệp sẽ nạp.
4. Chốt phép đo và mẫu số theo bảng dưới đây trong `protocol.md`.

   | Chỉ số | Cách tính |
   | --- | --- |
   | Evidence hit@k, recall@k | Đo có ít nhất một bằng chứng chuẩn và tỷ lệ các đơn vị bằng chứng chuẩn tìm được trên mỗi câu có bằng chứng. Ghi cả số câu được tính. |
   | Tỷ lệ câu trả lời đạt | Số câu đúng, đủ ý chính, có căn cứ và xử lý phù hợp khi thiếu dữ liệu trên tổng số ca đã thực sự chạy. Báo riêng tỷ lệ hoàn tất. |
   | Trích dẫn đúng vị trí | Số trích dẫn khớp tài liệu, phiên bản nếu có và trang hoặc đoạn trên tổng số trích dẫn kiểm tra. |
   | Mức hỗ trợ của trích dẫn | Số nhận định cần bằng chứng được trích dẫn hỗ trợ trên tổng số nhận định cần bằng chứng trong câu trả lời được chấm. Ghi riêng nhận định thiếu trích dẫn. |
   | Thời gian phản hồi | Từ lúc runner bắt đầu xử lý câu hỏi đến khi nhận kết quả hoàn tất. Báo trung vị, p95 và số lượt hoàn tất. Đo truy xuất và thời gian khởi tạo riêng. |

5. Chốt rubric qua ba tình huống dễ nhầm gồm đúng vị trí nhưng trích đoạn không hỗ trợ nhận định, trả lời đúng một phần và trả lời thận trọng khi thiếu bằng chứng. Tách kiểm tra bằng mã khỏi chấm nội dung bằng người đọc. Chốt quy tắc xử lý lượt lỗi và lượt đo bổ sung trước khi xem kết quả. Có thể kế thừa ngưỡng kỹ thuật từ Phase 06 nếu định nghĩa và mẫu số tương đương.
6. Chốt ma trận khả thi trong tuần. Cấu hình chính dùng truy xuất hybrid và **một mô hình có quyền truy cập**. Chọn trước 8 câu đại diện cho các nhóm để đối chiếu với vector-only, dùng cùng mô hình, `k`, nguồn, prompt và lịch sử. Với 24 câu chính và 8 câu đối chứng, dự trù 32 lượt nếu mỗi ca gọi mô hình một lần. Lượt thử thật được tính thêm trong kế hoạch ngân sách. Lưu danh sách câu, cấu hình, phiên bản mã và mã băm của dữ liệu, prompt và rubric trước khi chạy.
7. Chuẩn bị lệnh xem trước và kiểm tra bộ dữ liệu trên kho tạm. Runner Phase 06 gắn trực tiếp với bộ dữ liệu cũ, nên nếu tái sử dụng, cho runner mới nhận bộ dữ liệu và chính sách đã chốt. Xác minh đối tượng được tìm, vị trí nguồn và số lượt trong kế hoạch bằng kiểm tra cục bộ. Phase này dừng ở bước chuẩn bị, xem trước và kiểm tra dữ liệu.

## Đầu ra và điều kiện bàn giao

- `project/evaluation/phase07/` chứa bộ dữ liệu, tài liệu hoặc cách tái tạo, thông tin quyền sử dụng, đáp án và bằng chứng chuẩn.
- `results/phase_07_evaluation_design.md` tổng hợp kết quả và protocol, gồm các chỉ số, rubric, thiết lập đối chứng và quy tắc xử lý lượt.
- Có một lệnh kiểm tra dữ liệu và một kế hoạch chạy xem trước. Mỗi câu đọc được từ bộ dữ liệu, có phạm vi hợp lệ và có bằng chứng chuẩn hoặc lý do thiếu bằng chứng rõ ràng. Ghi việc cần xác nhận về quyền mô hình hoặc ngân sách khi chuyển Phase 08.

## Bàn giao sau triển khai

Xem [báo cáo và protocol Phase 07](../results/phase_07_evaluation_design.md) để lấy kết quả kiểm tra, mã băm, lệnh tái lập và điều kiện bắt đầu Phase 08.
