# Phase 07 — Thiết kế đánh giá trên 7 PDF gốc

Đề tài **Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập** · 24/11/2026.

Bộ đánh giá dùng toàn bộ 7 PDF người dùng đang có trong `project/data/`. Các bản trong `.versions/` là lưu trữ phiên bản nội bộ. Slide, báo cáo, PDF đề bài và tài liệu demo thuộc kho sản phẩm. Tất cả số trang dưới đây tính từ trang đầu của **tệp PDF**, bắt đầu từ 1.

| Mã | PDF | Chủ đề | Số trang |
| --- | --- | --- | ---: |
| P01 | Dynamic coupling between the central and autonomic nervous systems during sleep | CNS–ANS khi ngủ | 20 |
| P02 | Heart rate variability in normal and pathological sleep | HRV và giấc ngủ | 11 |
| P03 | Complexity and Nonlinearity in Short-Term Heart Period Variability | HRV phi tuyến, surrogate | 13 |
| P04 | Complexity analyses show two distinct types of nonlinear dynamics | HRV phi tuyến, hai phép kiểm | 7 |
| P05 | Recurrence quantification analysis across sleep stages | RQA và phân giai đoạn ngủ | 10 |
| P06 | Convex Optimization-15-34 | Tối ưu lồi | 20 |
| P07 | Cascade and parallel combination of adaptive filters for estimating heart rate | Lọc PPG khi vận động | 7 |
| **Tổng** | **7 tài liệu** | **Ba nhóm chủ đề** | **88** |

Bộ phân tích PDF của YourNote trích được chữ ở 86/88 trang, với trang 18 và 20 của P06 nằm ngoài phần có văn bản trích xuất được. Ca N05 cố ý khoanh trang 18 để kiểm tra cách xử lý khi phạm vi truy xuất rỗng. Mã SHA-256 theo tệp và số trang có trong manifest nguồn (tệp cục bộ `.run/real_pdf_validation/corpus.json`). Dữ liệu làm việc và bản gốc chỉ được đọc để tạo index tạm cho benchmark.

## Bộ câu hỏi và đối chứng

| Nhóm | Số ca chính | Năng lực được kiểm tra | Ca đủ điều kiện đối chứng đã chọn |
| --- | ---: | --- | --- |
| Một nguồn | 6 | Xác định phương pháp, điều kiện áp dụng, diễn giải kết quả | S02, S06 |
| Nhiều nguồn | 6 | Đối chiếu giả thuyết, protocol, đích đo và ý nghĩa kết quả | M03, M06 |
| Thiếu bằng chứng | 6 | Ba câu thiếu hoàn toàn, ba câu có thể trả lời một phần | N01, N06 |
| Nối tiếp | 6 | Khôi phục tham chiếu từ lịch sử có sẵn; trả lời bằng tài liệu | F03, F06 |
| Thử kỹ thuật | 3 | Chạy riêng để kiểm tra cấu hình trước ca chính | — |

Tập chính có 24 câu phủ cả 7 PDF, 32 mốc bằng chứng và 44 ý bắt buộc. Có thêm 3 mốc bằng chứng ở 3 ca thử. Mỗi câu lưu ngữ cảnh nguồn hoặc trang, một hoặc nhiều ý phải có và mốc bằng chứng định vị bằng nguồn, trang và chuỗi ký tự. Ví dụ M03 nối khung kiểm định surrogate trong P03 với lựa chọn 250 chuỗi đối chứng và các thống kê trong P04. M06 phân biệt định nghĩa nghiệm tối ưu trong P06 với cách trộn hai bộ lọc theo trọng số trong P07. N06 kiểm tra khả năng nêu đặc điểm mẫu nam rồi dừng đúng chỗ khi được hỏi về sai số trên nữ.

Đề, đáp án, phạm vi và trích đoạn chuẩn cho 27 câu (tệp cục bộ `.run/real_pdf_validation/design.json`) · Kiểm tra đầu vào, index và chứng cứ từng câu (tệp cục bộ `.run/real_pdf_validation/preflight.json`).

## Protocol khóa trước khi chạy

- **Truy xuất:** hybrid của YourNote (vector + từ khóa + RRF) và vector-only cùng dùng MiniLM đa ngôn ngữ, cùng chunk 1.500 ký tự, overlap 200 và `k=5`. So sánh ghép cặp trên tám câu trên. Mô hình sinh giữ nguyên cấu hình giữa hai nhánh. Dự kiến 24 hybrid + 8 vector-only + 3 pilot, tối đa 35 lượt sinh.
- **Evidence hit@5:** số câu có ít nhất một mốc chuẩn trong top 5 chia cho số câu có mốc chuẩn. **Recall@5:** tính phần mốc chuẩn tìm được trên từng câu rồi lấy trung bình. Báo kèm tỷ lệ theo tổng mốc để đọc được mẫu số. So trùng theo nguồn, trang và chữ đã chuẩn hóa. Một cách diễn đạt tương đương ở vị trí khác có thể bị tính thiếu.
- **Câu đạt:** trả lời đủ các ý bắt buộc, có bằng chứng hỗ trợ, xử lý phù hợp phần thiếu và tránh nhận định quan trọng vượt nguồn. Chấm riêng từng ý, liên quan của từng trích dẫn, mức hỗ trợ của từng nhận định và các nhận định thiếu chứng cứ. Kiểm tra vị trí bằng mã dựa trên định danh, phiên bản, trang và nội dung. Một trích dẫn có thể đúng vị trí nhưng yếu về nội dung.
- **Thời gian:** truy xuất đo sau khi làm nóng embedding, ghi riêng khởi tạo và nhập tệp. Thời gian trả lời chạy từ đầu xử lý câu đến lúc nhận đáp án hoàn tất. Ghi trung vị và p95 lấy theo thứ hạng trần.
- **Lượt lỗi:** lưu cả lượt hỏng, phân biệt hoàn tất, lỗi và chưa chạy. Dừng phần sinh khi hết quyền, quota, lỗi mô hình hoặc pilot không đạt. Cặp so sánh chất lượng yêu cầu cả hai nhánh hoàn tất trên cùng cấu hình. Sáu câu nối tiếp dùng lịch sử soạn sẵn, không lấy câu trả lời trước làm bằng chứng.
- **Chấm:** tách kết quả kiểm tra bằng mã khỏi đọc ngữ nghĩa. Khi có hai người chấm độc lập trên phiếu ẩn cấu hình, báo tỷ lệ đồng thuận và Cohen’s κ cho nhãn câu đạt. Một lượt chấm của tác nhân chỉ là đánh giá sơ bộ.

Lớp quyết định chỉ số và cách tổng hợp (tệp cục bộ `.run/real_pdf_validation/policy.json`) · Kế hoạch, phiên bản và mã băm đã chốt (tệp cục bộ `.run/real_pdf_validation/plan.json`) · Runner (tệp cục bộ `.run/real_pdf_validation/run.py`).

Đây là benchmark nội bộ có bộ đáp án bám theo tài liệu thật, tập thử riêng và đối chứng ghép cặp. Nguyên tắc tách truy xuất, câu trả lời và bằng chứng phù hợp với cách phân lớp đánh giá trong QASPER và ALCE. Tập này do nhóm xây dựng từ kho PDF đang dùng, nên các số đo mô tả bộ tài liệu và điều kiện đã kiểm tra. [QASPER](https://aclanthology.org/2021.naacl-main.365/) · [ALCE](https://aclanthology.org/2023.emnlp-main.398/).

Từ `project/`, xem manifest và điều kiện đã chốt ở `.run/real_pdf_validation/`. Hai bước `run.py freeze` và `run.py retrieve` lưu tệp mới để giữ nguyên nhật ký của lượt đã đo. Khi tái lập, sao chép thư mục private và dùng một thư mục chạy mới để tránh ghi đè dữ liệu đã ghi nhận.
