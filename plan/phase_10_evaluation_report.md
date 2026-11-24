# Phase 10 — Tổng hợp và bàn giao kết quả đánh giá

Hãy làm việc trong `/home/vutu/Desktop/rag_notebooklm`, với mã ứng dụng ở `project/`. Đọc bàn giao [Phase 07](phase_07_evaluation_design.md), [Phase 08](phase_08_rag_benchmark.md) và [Phase 09](phase_09_reading_evaluation.md). Chỉ triển khai Phase 10.

## Mục tiêu

Viết phần đánh giá định lượng cho đề tài **Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập**. Trình bày rõ nhóm đã triển khai gì, đã đo gì, kết quả cho thấy gì trong điều kiện thử nghiệm và câu hỏi nào cần đánh giá tiếp.

## Công việc

1. Đối chiếu bảng số liệu với dữ liệu từng lượt, rubric và nhật ký chạy. Kiểm tra mẫu số, số lượt lỗi hoặc chưa chạy, cấu hình đối chứng, đơn vị thời gian và cách tính trung vị, p95. Khi có kết quả mâu thuẫn, ghi sự khác biệt về cách đo hoặc phiên bản trước khi kết luận.
2. Viết báo cáo theo mạch **mục tiêu → dữ liệu và cấu hình → kết quả → phân tích lỗi → giới hạn**. Mở đầu ngắn gọn bằng bối cảnh khảo sát và hướng đề xuất đã trình bày với giảng viên. Gom chứng cứ quanh chất lượng câu trả lời, trích dẫn và thời gian phản hồi. Tách kết quả chạy mô hình thật, kiểm tra giao diện nội bộ và dữ liệu sinh viên nếu có.
3. Trình bày bảng câu trả lời đạt, trích dẫn đúng vị trí, mức hỗ trợ của trích dẫn và thời gian phản hồi theo cấu hình. Báo kết quả retrieval và cặp hybrid/vector-only nếu đủ dữ liệu. Mỗi dòng chính có mẫu số và đường dẫn đến tệp kết quả. Dùng một hoặc hai ca đối chiếu trực tiếp với tài liệu để minh họa điểm tốt hoặc lỗi còn lại.
4. Nếu có dùng thử, tóm tắt thời gian tìm lại nguồn, tỷ lệ hoàn thành và phản hồi về mức độ tập trung. Nếu chỉ có chạy thử nội bộ, mô tả đúng thao tác đã kiểm tra. Số liệu Phase 06 có thể nhắc lại dưới dạng mốc kỹ thuật có điều kiện đo riêng. So sánh trực tiếp chỉ khi dữ liệu và cấu hình tương đương.
5. Rút ra tối đa ba việc cần làm tiếp, mỗi việc gắn với một ca lỗi hoặc giới hạn quan sát được. Soạn một đoạn cập nhật Zalo ngắn cho giảng viên, có tên đề tài, phần đã triển khai, phần đã đo kèm kết quả có thể xác minh và phần còn chờ. Chuẩn bị dàn ý ngắn cho slide đánh giá để nhóm dùng khi cần cập nhật báo cáo trình chiếu.

## Đầu ra và điều kiện bàn giao

- Lưu báo cáo, bảng số liệu, tin nhắn Zalo và dàn ý trình chiếu trong [results/phase_10_evaluation_report.md](../results/phase_10_evaluation_report.md). Kèm liên kết tới protocol, dữ liệu từng lượt, bản chấm và điều kiện tái lập.
- Kiểm tra mọi số liệu được nêu trong tin nhắn và dàn ý đều hiện diện trong báo cáo. Ghi rõ mẫu số, phạm vi và phần chưa đo, nhất là khi chưa có inference thật hoặc sinh viên tham gia.

## Bàn giao sau triển khai

- Đã tính lại các bảng từ lượt gốc, đối chiếu mã băm và kiểm tra 46/46 trích dẫn trên tệp nguồn được tái tạo. Hỏi đáp hoàn tất 35/35 lượt, gồm 32 lượt chính và 3 lượt thử. Hybrid chính đạt 22/24 theo chấm sơ bộ, có 30/30 trích dẫn đúng vị trí, trung vị 3,33 giây và p95 4,34 giây.
- Trên tám cặp tiếng Việt, cả hai phương thức đạt 8/8 theo chấm sơ bộ. Trên mẫu QASPER, hit@5 là 13/24 ở mỗi phương thức. Kiểm tra giao diện nội bộ hoàn tất 8/8 lượt.
- Còn chờ chấm độc lập bằng người đọc và dùng thử với sinh viên. Bản tổng hợp nêu riêng các giới hạn và ba việc tiếp theo.
- [Báo cáo](../results/phase_10_evaluation_report.md) · [Dữ liệu hỏi đáp](../evaluation/phase08/artifacts/inference.json) · [Đối chứng QASPER](../evaluation/phase07/artifacts/qasper-retrieval.json) · [Tin nhắn và dàn ý slide](../results/phase_10_evaluation_report.md#tin-nhắn-zalo)
