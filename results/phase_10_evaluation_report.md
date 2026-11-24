# Phase 10 — Tổng hợp đánh giá YourNote trên 7 PDF gốc

- **Đề tài** Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập
- **Sinh viên** Vũ Trịnh Tú và Nguyễn Quang Dũng
- **Giảng viên hướng dẫn** TS. Võ Lê Cường
- **Ngày đo** 24/11/2026 · commit `8adbbdf`

Bộ đánh giá sử dụng toàn bộ kho PDF đang làm việc gồm 5 bài HRV/giấc ngủ, 1 bài lọc tín hiệu PPG khi vận động và 1 trích đoạn Convex Optimization. Trong 88 trang, parser trích được văn bản từ 86 trang. Nhóm đo riêng ba việc: truy xuất đoạn bằng chứng, trả lời và dẫn nguồn, và mở lại vị trí gốc trong luồng đọc. Kết quả dành cho bộ 7 PDF và điều kiện đo mô tả trong [Phase 07](phase_07_evaluation_design.md).

## Kết quả chính

| Phần đo | Kết quả | Cơ sở |
| --- | --- | --- |
| Truy xuất hybrid | **8/21** câu có bằng chứng chuẩn có mốc trong top 5. Recall trung bình **33,33%**, lấy đúng **10/32** mốc. | Kiểm tra bằng mã và truy vết từng chunk. |
| Đối chứng ghép cặp | Hybrid và vector-only cùng hit **4/7** và recall **50%** trên bảy câu có mốc. Cả hai có **4/8** câu đạt trên toàn bộ tám cặp. | Tám cặp đồng nhất cấu hình sinh. Nhãn đạt là chấm sơ bộ. |
| Trả lời hybrid | **12/24** câu chính đạt, bao phủ **25/44** ý. Sáu câu nhiều nguồn **0/6** đạt với **1/12** mốc chuẩn vào top 5. Nhóm thiếu bằng chứng **6/6** đạt. | Một lượt chấm của Codex trên phiếu ẩn cấu hình. |
| Kiểm tra trích dẫn | Hybrid chính **32/32** trích dẫn đúng vị trí. **35/36** nhận định có trích dẫn hỗ trợ, **40/40** liên kết trích dẫn–nhận định được gán có liên quan. | Vị trí kiểm tra bằng mã, hỗ trợ nội dung chấm sơ bộ. |
| Thời gian hỏi đáp | Hybrid chính trung vị **4,10 s**, p95 **6,69 s**, 24 ca. Truy xuất riêng trung vị **37,49 ms**. | Không gồm dựng index và thao tác UI. |
| Đọc và ghi chú | **14/14** lượt mỗi điều kiện mở đúng vị trí, xác nhận chữ gốc và mở lại ghi chú. YourNote dùng 0 lần chuyển tab, luồng hai tab dùng 2 lần mỗi lượt. | Hai bộ nhiệm vụ trên cả 7 PDF. Trình duyệt tự động dùng cùng đáp án đã chuẩn bị. |
| Hiển thị PDF | **14/14** lượt desktop và **7/7** lượt mobile vừa trang mặc định. **7/7** lượt mobile giữ trạng thái chưa đọc khi chỉ mở và lưu trạng thái đã đọc sau khi tick. | Kiểm tra giao diện và API của sổ tay tạm. |

Hoàn tất **35/35** ca hỏi đáp tính cả ba ca thử. Dùng **34** lượt ChatGPT `gpt-6.1-terra` trên hạn mức 35, với **85.512** token dịch vụ báo. Một ca trang không có văn bản được xử lý cục bộ. Truy xuất kiểm tra **165/165** vị trí ngữ cảnh và ghi nhận **0** ca vượt phạm vi. [Chi tiết truy xuất, hỏi đáp và phân nhóm](phase_08_rag_benchmark.md) · [Luồng đọc và kiểm tra mobile](phase_09_reading_evaluation.md).

## Ý nghĩa và giới hạn

Ca M03 cho thấy đúng trích dẫn về các bước kiểm định vẫn chưa đủ để người đọc tái lập phương pháp. Trang chứa 250 surrogate của bài thứ hai không vào top 5, nên câu trả lời bỏ mất con số cần thiết. Ở S01, nguồn có cách giải thích khác được trích dẫn hợp lệ dù mốc đã chọn không vào top 5. Hai ca cho thấy cần đọc tỷ lệ tìm đoạn cùng với mức đủ ý và hỗ trợ của trích dẫn.

Đối chứng chưa cho thấy hybrid tăng hit/recall trên tám câu đã chọn. Trong thử nghiệm giao diện, YourNote hạn chế việc chuyển tab. Thời gian kỹ thuật của YourNote cao hơn trong điều kiện đã đo. Phép đo YourNote gồm xác minh trích dẫn và tải theo phiên bản, còn điều kiện hai tab có PDF nạp trước. Hai thẻ của PDF RQA có độ trễ mở cao hơn, cần đo tách các bước để xác định nút thắt.

Tập câu hỏi do nhóm soạn và mới qua một lượt chấm sơ bộ. Chưa có nhãn độc lập từ hai người chấm, hệ số đồng thuận hoặc phiên dùng thử với sinh viên. Đối chiếu QASPER trước đó là phép đo retrieval riêng trên commit và corpus khác, giữ ở bảng tham khảo trong Phase 08.

## Việc tiếp theo

1. Thử giữ tối thiểu một số ứng viên theo từng nguồn hoặc dùng reranking cho câu nhiều nguồn. Đo lại theo đúng các ID và trang chuẩn, trước hết là M03 và M06.
2. Chấm độc lập bằng hai người trên phiếu ẩn cấu hình, đồng thời bổ sung các đoạn chuẩn tương đương được xác minh như S01.
3. Tách thời gian xác minh citation, tải PDF và render trang đối với hai thẻ RQA, rồi dùng kịch bản ở Phase 09 để đo với sinh viên.

## Tin nhắn Zalo

> Em chào thầy Cường, nhóm em cập nhật đề tài “Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập”. Nhóm đã đánh giá YourNote trên 7 PDF thật với 24 câu chính. Hybrid đưa được mốc bằng chứng vào top 5 ở 8/21 câu có đáp án, đạt 12/24 câu theo chấm sơ bộ và xác minh 32/32 trích dẫn đúng vị trí. Kiểm tra nội bộ mở đúng trang và lưu ghi chú đạt 14/14 lượt trên YourNote, với 7/7 PDF vừa trang khi thử trên mobile. Nhóm đang tập trung cải thiện khả năng tổng hợp nhiều nguồn và sẽ chấm độc lập, dùng thử với sinh viên.

## Dàn ý trình chiếu

- **Dữ liệu và thiết kế.** 7 PDF, 88 trang, 24 câu chính, 8 cặp so sánh dùng cùng mô hình.
- **Chất lượng hỏi đáp.** Hit@5 8/21, câu trả lời đạt 12/24, trích dẫn đúng vị trí 32/32. Minh họa M03 bỏ thiếu dữ kiện 250 surrogate.
- **Trải nghiệm đọc.** 14/14 lượt YourNote mở đúng vị trí và lưu ghi chú, 7/7 lượt mobile vừa trang. Ghi rõ đây là kiểm tra nội bộ và còn chờ dữ liệu từ sinh viên.
