# Phase 09 — Đánh giá trải nghiệm đọc tài liệu

Hãy làm việc trong `/home/vutu/Desktop/rag_notebooklm`, với mã ứng dụng ở `project/`. Đọc [Phase 07](phase_07_evaluation_design.md), [Phase 08](phase_08_rag_benchmark.md) và phiếu sẵn có tại `project/docs/STUDENT_TRIAL.md`. Chỉ triển khai Phase 09.

## Mục tiêu

Kiểm tra người đọc có thể tìm lại đoạn gốc, xác lập phạm vi khi hỏi và tiếp tục ghi chú trong sổ như thế nào. Phần này đánh giá thao tác đọc và đối chiếu bằng chứng trên giao diện, bổ sung cho chất lượng câu trả lời và thời gian phản hồi đo ở Phase 08.

## Công việc

1. Chuẩn bị hai bộ nhiệm vụ tương đương về số trang, độ khó, số câu hỏi và số lần cần mở nguồn. Dùng tình huống thật của việc đọc, như tìm điều kiện áp dụng của một phương pháp trong PDF, kiểm tra bằng chứng rồi ghi lại nhận định. Chọn một cách làm quen thuộc để đối chiếu, chẳng hạn ứng dụng AI với PDF mở riêng hoặc một notebook đọc tài liệu mà nhóm có thể sử dụng. Ghi cấu hình, phiên bản, mô hình nếu biết và điều kiện cung cấp tài liệu.
2. Chốt cách tính trước. Ghi thời gian từ khi nhận nhiệm vụ đến khi mở đúng vị trí và xác nhận bằng chứng, tỷ lệ hoàn thành, độ đúng của vị trí tìm được, số lần cần hỗ trợ hoặc đổi cửa sổ và mức độ tập trung tự đánh giá theo thang 1–5. Có tiêu chí cho thời điểm bắt đầu, kết thúc và giới hạn thời gian. Ghi trường hợp bỏ dở hoặc hết giờ riêng.
3. Chạy thử kịch bản trên YourNote bằng bộ tài liệu đánh giá. Kiểm tra chọn nguồn, PDF cạnh chat, mở trích dẫn từ câu trả lời, hiển thị mô hình và ghi chú còn mở lại được. Ghi thời gian và lỗi thao tác dưới nhãn **kiểm tra nội bộ**. Nếu dùng câu trả lời đã lưu để so luồng đọc, áp dụng điều kiện tương đương và báo riêng với ca chạy mô hình thật.
4. Khi nhóm có người tham gia đã đồng ý, tổ chức một đợt nhỏ khoảng 3–5 sinh viên. Cho mỗi người thử cả hai cách, đổi thứ tự giữa các phiên và phân bổ hai bộ nhiệm vụ để giảm hiệu ứng học lại. Dùng mã người tham gia, ghi dữ liệu cần thiết cho phép đo và mức trợ giúp. Việc mời hoặc nhắn người tham gia do nhóm thực hiện khi có chủ trương.
5. Tổng hợp số người, số nhiệm vụ, số ca hoàn thành và trung vị hoặc khoảng thời gian. Khi có dữ liệu ghép theo người, trình bày chênh lệch trong từng cặp trước khi tổng hợp. Ghi các khác biệt về mô hình, nền tảng hoặc loại tài liệu có thể ảnh hưởng kết quả. Mẫu nhỏ dùng để mô tả trải nghiệm quan sát được.

## Đầu ra và điều kiện bàn giao

- Lưu báo cáo, kịch bản và hai bộ nhiệm vụ trong [results/phase_09_reading_evaluation.md](../results/phase_09_reading_evaluation.md). Phiếu thu thập, ảnh và dữ liệu kiểm tra nội bộ lưu trong `project/evaluation/phase09/artifacts/`.
- Nếu có dữ liệu người tham gia, bàn giao bảng tổng hợp với mẫu số, điều kiện đo và các lỗi thực tế. Nếu tuần này chưa có người tham gia, hoàn tất kịch bản, phiếu và lần chạy nội bộ. Ghi **chưa dùng thử với sinh viên** để Phase 10 báo cáo đúng trạng thái.

## Bàn giao sau triển khai

- Đối chiếu YourNote với luồng câu trả lời và PDF ở hai tab. Hai thẻ dùng cùng PDF bốn trang và hai câu trả lời đã lưu từ Phase 08. Có 0 lượt gọi LLM mới.
- Kiểm tra nội bộ hoàn tất 4/4 lượt mỗi điều kiện. Cả hai mở đúng trang và mở lại được ghi chú. YourNote dùng 0 lần đổi tab mỗi lượt, điều kiện hai tab dùng 2 lần. Thời gian là số đo kỹ thuật của script. PDF ở điều kiện hai tab được nạp trước và cơ chế lưu ghi chú khác nhau.
- Kiểm tra ở khung 390 × 844 xác nhận PDF vừa trang mặc định, có thể zoom và trở lại vừa trang. Trạng thái đã đọc chỉ thay đổi sau khi tick và đã được xác nhận trong dữ liệu đã lưu.
- **Chưa dùng thử với sinh viên.** Có 0 người và 0 nhiệm vụ có người thực hiện. Các chỉ số trợ giúp, tập trung và thời gian theo người đang để trống. [Báo cáo](../results/phase_09_reading_evaluation.md) · [Kịch bản](../results/phase_09_reading_evaluation.md#kịch-bản-dùng-thử-luồng-đọc) · [Phiếu thu thập](../evaluation/phase09/artifacts/collection.csv)
