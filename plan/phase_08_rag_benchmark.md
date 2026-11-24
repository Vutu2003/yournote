# Phase 08 — Đo chất lượng hỏi đáp RAG

Hãy làm việc trong `/home/vutu/Desktop/rag_notebooklm`, với mã ứng dụng ở `project/`. Dùng [báo cáo và protocol Phase 07](../results/phase_07_evaluation_design.md) làm nguồn cho bộ dữ liệu, rubric và cấu hình đã chốt. Chỉ triển khai Phase 08.

## Mục tiêu

Thu số liệu trên hệ thống hiện tại về truy xuất bằng chứng, chất lượng câu trả lời, độ chính xác của trích dẫn và thời gian phản hồi. Đối chiếu hybrid với vector-only trên cùng tập câu hỏi đã định trước để đánh giá riêng ảnh hưởng của cách truy xuất.

## Công việc

1. Chạy kiểm tra đầu vào, lưu mã băm dữ liệu, prompt, policy, báo cáo chứa rubric, cấu hình và phiên bản mã đã chốt trước khi sinh câu trả lời. Dùng kho tài liệu, notebook và index tạm trong tiến trình đánh giá, tách khỏi dữ liệu làm việc. Tách thời gian khởi tạo embedding và lập chỉ mục khỏi thời gian truy xuất ổn định. Kết quả đối chiếu truy xuất QASPER đã có ở Phase 07, báo riêng với phép đo hỏi đáp tiếng Việt. Nếu mã hoặc cấu hình truy xuất thay đổi, ghi rõ phiên bản tương ứng với từng kết quả.
2. Đo retrieval cho cả hai cách trên các câu thuộc kế hoạch. Kiểm tra scope nguồn, trang và phiên bản, rồi ghi evidence hit@k, recall@k, độ trễ và bằng chứng còn thiếu theo từng câu. Nếu đường chạy benchmark gọi trực tiếp hàm truy xuất hoặc sinh đáp án, ghi rõ ranh giới của phép đo so với giao diện và các nhánh đặc biệt trong ứng dụng thực tế.
3. Chạy thử đầu cuối trên tập thử riêng và xem lại tập câu chính trước khi bắt đầu thu số liệu. In trước mô hình, câu hỏi, cấu hình retrieval, số lượt dự kiến và đường dẫn lưu kết quả. Chạy inference thật theo quyền truy cập và ngân sách đã được người dùng cho phép. Nếu quyền hoặc ngân sách chưa đủ, tiếp tục phần retrieval và kiểm tra runner, rồi ghi phần inference chưa đo.
4. Với phần inference chính, dùng cùng prompt, `k`, lịch sử và mô hình ở mỗi cặp so sánh. Ghi mô hình thực tế khi dịch vụ có báo. Lưu từng lượt gồm ID câu, cấu hình, trạng thái, thời lượng, context phục vụ chấm, câu trả lời, trích dẫn và usage được báo. Đếm cả lượt gọi đã thử nhưng hỏng. Khi gặp lỗi quota, quyền hoặc mô hình, dừng phần chạy liên quan, giữ kết quả đã có và ghi số câu chưa chạy. Dùng thư mục riêng cho lần đo bổ sung và giữ quy tắc chọn lượt nào để tổng hợp đã chốt trong protocol.
5. Dùng rubric Phase 07 để chấm độ bao phủ ý bắt buộc, mức bám ngữ cảnh, tỷ lệ câu đạt và chất lượng trích dẫn. Mã kiểm tra nguồn, phiên bản, đoạn hoặc trang. Hai người dùng phiếu ẩn cấu hình và chấm độc lập trước khi đối chiếu. Lưu hai bộ nhãn gốc, tỷ lệ đồng thuận và Cohen’s κ cho nhãn đạt, rồi ghi lý do xử lý các bất đồng. Nếu chỉ có một người chấm, ghi rõ và để trống chỉ số đồng thuận. Báo rõ lịch sử hội thoại được chuẩn bị sẵn.
6. Phân tích ít nhất một ca tiêu biểu theo kết quả thực tế. Chỉ ra bằng chứng có vào ngữ cảnh không, câu trả lời sử dụng đúng đoạn không và trích dẫn có hỗ trợ hay không. Đối chiếu hybrid với vector-only chỉ trên các câu có cả hai kết quả tương đương. Báo mẫu số theo từng nhóm, số lượt hoàn tất và số lượt chưa chạy. Để trống số liệu usage mà dịch vụ không trả về.

## Đầu ra và điều kiện bàn giao

- Lưu báo cáo trong [results/phase_08_rag_benchmark.md](../results/phase_08_rag_benchmark.md). Ghi mô hình, phiên bản, điều kiện đo, lệnh tái lập và số lượt đã dùng. Kế hoạch chạy, kết quả từng câu và dữ liệu chấm lưu trong `project/evaluation/phase08/artifacts/`.
- Có bảng evidence hit/recall, tỷ lệ câu đạt, bao phủ ý bắt buộc, mức bám ngữ cảnh, độ đúng vị trí, độ bao phủ và liên quan của trích dẫn, cùng thời gian phản hồi. Báo rõ số liệu xác minh bằng mã, chấm tay và kết quả đối chiếu trên mẫu QASPER. Ghi rõ phần nào chưa có kết quả trên mô hình thực.
- Có bảng cặp hybrid/vector khi chạy đủ dữ liệu so sánh, kèm danh sách câu đủ cặp và giới hạn của điều kiện đo. Các lỗi nghiêm trọng liên quan phạm vi nguồn hoặc trích dẫn cần có ca tái lập và được nêu ở phần kết quả.

## Bàn giao sau triển khai

- Truy xuất hoàn tất 32/32 lượt chính và 3/3 lượt thử. Hybrid toàn tập có hit@5 21/21 và recall trung bình 98,41%. Tám cặp cùng đạt 7/7 câu có bằng chứng và lấy đủ 9/9 đoạn chuẩn.
- Hỏi đáp thật hoàn tất 32/32 lượt chính và 3/3 lượt thử, dùng 35/35 lượt ChatGPT. Dịch vụ báo `gpt-6.1-terra` ở cả 35 lượt. Hybrid chính có 30/30 trích dẫn đúng vị trí, trung vị phản hồi 3,33 giây và p95 4,34 giây.
- Chấm sơ bộ bằng một tác nhân trên phiếu ẩn cấu hình cho 22/24 câu hybrid đạt. Cả hai phương thức đạt ở 8/8 cặp. Hai ca chính thiếu ý là `p07-m04` vì truy xuất thiếu đoạn về khoảng cách, và `p07-m05` vì câu trả lời bỏ qua chênh lệch 10 phút. Hai phiếu chấm độc lập của người đọc và Cohen’s κ đang chờ hoàn thành.
- Backend YourNote đã được khởi động lại và xác minh hoạt động. [Báo cáo và dữ liệu bàn giao](../results/phase_08_rag_benchmark.md)
