# Phase 09 — Kiểm tra luồng đọc trên 7 PDF gốc

**24/11/2026** · YourNote tại commit `8adbbdf` · Chrome 158.0.8127.88 · PDF.js 6.5.438. Bộ này dùng cùng bảy bản PDF và mã băm với Phase 07–08, chạy bằng frontend build riêng, FastAPI thật và SQLite/Qdrant tạm. 28 lượt desktop ở 1.440 × 900 và 7 lượt mobile ở 390 × 844. [Danh mục PDF](phase_07_evaluation_design.md).

## Cách đo

Mỗi tài liệu có hai thẻ, mỗi thẻ chọn một trang và làm một việc cụ thể như đối chiếu điều kiện tối ưu cục bộ, xác nhận số surrogate hoặc kiểm tra chồng lấn cửa sổ. 14 thẻ được chạy ở cả hai điều kiện. Thứ tự hai điều kiện đảo theo thẻ. Hai điều kiện dùng cùng nội dung, phiên bản PDF và vị trí trích dẫn. Câu trả lời ngắn được soạn trước từ đoạn gốc đã xác minh. Giao diện hiển thị nhãn kỹ thuật `replay-pdf-reference`, với **0 lượt gọi mô hình**. Các điểm chất lượng câu trả lời thật nằm ở [Phase 08](phase_08_rag_benchmark.md).

- **YourNote:** chọn đúng nguồn và trang, bấm trích dẫn để tải đúng bản PDF và kiểm tra hai dấu hiệu trên lớp chữ, rồi lưu và mở lại ghi chú. API xác minh phạm vi đã lưu và phiên bản tệp được tải.
- **Hai tab:** nguồn và trang được chọn trên tab đáp án, người thực hiện chuyển sang tab PDF để nhập trang rồi trở lại lưu ghi chú. Tệp PDF ở tab riêng đã mở trang đầu trước khi tính giờ. Ghi chú ở tab riêng dùng localStorage, còn YourNote kiểm tra lưu vào sổ tay qua API rồi tải lại.

Mốc bắt đầu là sau khi sổ tay hoặc đáp án và PDF tab riêng sẵn sàng. Mốc kết thúc lần lượt là trang đúng hiển thị, tìm thấy hai chuỗi xác nhận trên trang, và ghi chú được mở lại. Biểu hiện tập trung, nhu cầu hỗ trợ và thời gian của sinh viên cần đo bằng phiên có người tham gia.

## Kết quả kiểm tra nội bộ

| Điểm kiểm tra desktop | YourNote | Hai tab |
| --- | ---: | ---: |
| Hoàn thành / dự kiến | **14/14** | **14/14** |
| Chọn đúng phạm vi | 14/14 | 14/14 |
| Đúng bản PDF, đúng trang và có hai dấu hiệu xác nhận | 14/14 | 14/14 |
| Ghi chú mở lại đúng nội dung sau tải lại | 14/14 | 14/14 |
| Số lần chuyển tab trên mỗi thẻ | 0 | 2 |
| Mở đúng trang, trung vị / p95 (s) | 0,764 / 6,739 | 0,059 / 0,132 |
| Xác nhận chữ gốc, trung vị / p95 (s) | 0,765 / 6,739 | 0,081 / 0,158 |
| Mở lại ghi chú, trung vị / p95 (s) | 1,633 / 7,579 | 0,160 / 0,233 |

Mỗi độ trễ có 14 mẫu mỗi điều kiện, p95 lấy theo thứ hạng trần. Thời gian của YourNote gồm API xác minh trích dẫn và tải PDF theo phiên bản, còn PDF ở điều kiện hai tab đã được nạp trước. Luồng hai tab có ít bước xử lý lưu nội bộ hơn và trình duyệt được điều khiển tự động, nên các độ trễ này mô tả kỹ thuật dưới hai điều kiện đo. Trung vị chênh lệch theo cặp ở bước xác nhận là YourNote thêm 0,675 s. Hai thẻ của P05 cần khoảng 4,9 và 6,7 s ở YourNote, nổi bật so với các thẻ còn lại. Mẫu hiện tại ghi nhận hiện tượng theo tệp, chưa cô lập nguyên nhân. Dữ liệu 28 lượt desktop và 7 lượt mobile (tệp cục bộ `.run/real_pdf_validation/reading/internal-check.json`).

**PDF vừa trang.** Desktop **14/14** lượt hiển thị trọn trang và vùng PDF không có dư cuộn dọc ở chế độ vừa trang. Trên mobile, **7/7** tài liệu vừa khung ở trạng thái mở, tăng lên 125% có thể cuộn và trở lại vừa trang được. **7/7** ca vẫn để ô “Đã đọc” ở trạng thái chưa tick sau khi mở đọc chuyên sâu. Sau khi tick, **7/7** ca có trạng thái đúng trong dữ liệu sổ tay. Ảnh desktop mẫu (tệp cục bộ `.run/real_pdf_validation/reading/yournote.png`) · Ảnh mobile P06 (tệp cục bộ `.run/real_pdf_validation/reading/P06-mobile.png`).

## Kịch bản dùng thử luồng đọc

| PDF | Bộ A | Bộ B |
| --- | --- | --- |
| P01 | Cơ chế chung ảnh hưởng EEG và HRV, trang 6 | Gợi K-complex hoặc arousal, trang 1 |
| P02 | BRS qua chu kỳ ngủ, trang 5 | Dải HF và phế vị, trang 3 |
| P03 | Các bước kiểm định surrogate, trang 4 | NMSPE và mốc trung bình hoặc trung vị, trang 3 |
| P04 | Số surrogate và thống kê, trang 3 | Thay đổi khi nghiêng bàn, trang 4 |
| P05 | Mất cân bằng lớp Wake, trang 8 | Số giờ và nhóm giai đoạn, trang 2 |
| P06 | Phạm vi nghiệm cục bộ, trang 9 | Nút thắt của tối ưu lồi, trang 10 |
| P07 | Cửa sổ chồng lấn và ECG chuẩn, trang 2 | Trọng số 0,5 của hai bộ lọc, trang 4 |

Mỗi thẻ có cùng ba mốc thao tác, trang mục tiêu, hai dấu hiệu bằng chứng và ghi chú để kiểm tra sau khi mở lại. Cho 3–5 người đã đồng ý làm một tập ở YourNote và tập kia ở hai tab, đảo thứ tự và cách gán A/B giữa các người. Cho tối đa năm phút mỗi thẻ. Phiếu ghi mã người tham gia, điều kiện, tập, thứ tự, thời gian mở đúng trang, thời gian xác nhận, kết quả, lỗi/hết giờ, số lần chuyển tab, số lần hỗ trợ và đánh giá tập trung từ 1 đến 5. Ghi chênh lệch theo cặp trong từng người trước khi tổng hợp.

**Chưa dùng thử với sinh viên.** 0 người và 0 nhiệm vụ do người tham gia thực hiện. Chỉ số thời gian, mức tập trung và mức trợ giúp theo người để trống. Phiếu thu thập (tệp cục bộ `.run/real_pdf_validation/reading/collection.csv`) · Thẻ đọc và phân bổ (tệp cục bộ `.run/real_pdf_validation/scenarios.json`) · Runner Chrome (tệp cục bộ `.run/real_pdf_validation/run.mjs`).

Để tái lập trên PC, chạy từ `project/` bằng Node 24 với Chrome và môi trường Python đã cài. Dùng `.tools/node/bin/node .run/real_pdf_validation/run.mjs <thư_mục_kết_quả_mới>`. Chạy trong không gian mạng riêng và dùng các PDF gốc khớp manifest.
