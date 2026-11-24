# Phase 08 — Đo hỏi đáp RAG trên 7 PDF gốc

Đo ngày **24/11/2026**, mã ứng dụng `8adbbdf74581e8c0aa899bc1bc513d4e66fdf6e6`. Câu hỏi tiếng Việt, tài liệu gốc tiếng Anh, index Qdrant cục bộ dựng từ 7 PDF và 406 chunk. Cùng MiniLM đa ngôn ngữ, `k=5`, phạm vi tài liệu/trang, lịch sử và prompt trong mỗi cặp. ChatGPT báo `gpt-6.1-terra` ở cả 34 lượt sinh. [Protocol và danh mục nguồn](phase_07_evaluation_design.md).

Runner gọi trực tiếp **retriever → tạo câu trả lời từ các đoạn → xác minh trích dẫn** bằng mã YourNote. API tác vụ, giao diện, luồng chọn văn bản và nhánh ưu tiên trích xuất tóm tắt của ứng dụng nằm ngoài đường đo này. Lịch sử của sáu câu nối tiếp do người thiết kế soạn trước. Ba ca thử chạy hybrid. Trong tập chính, 24 ca chạy hybrid và tám ca đối chứng chạy thêm vector-only.

Mã băm kế hoạch `153008dc38bb90643bc86c94e585b739f8b3b44f2b4e35046cf53b697f02a494`. Hồ sơ cục bộ lưu bản kê từng SHA-256 của PDF, tập câu, quy tắc chấm, prompt, mã chạy và cấu hình. Kế hoạch khóa trước đo (tệp cục bộ `.run/real_pdf_validation/plan.json`) · Preflight 27 câu (tệp cục bộ `.run/real_pdf_validation/preflight.json`).

## Truy xuất bằng chứng

| Điều kiện | Hoàn tất | Hit@5 | Recall@5 theo câu | Tìm được theo tổng mốc | Trung vị / p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid, tập chính | 24/24 | 8/21 (38,10%) | 33,33% (21 câu) | 10/32 | 37,49 / 60,70 |
| Hybrid, tám cặp | 8/8 | 4/7 | 50,00% (7 câu) | 5/11 | 35,56 / 49,53 |
| Vector-only, tám cặp | 8/8 | 4/7 | 50,00% (7 câu) | 5/11 | 28,66 / 34,43 |
| Thử kỹ thuật hybrid | 3/3 | 3/3 | 100% (3 câu) | 3/3 | 28,82 / 28,85 |

Ba câu chính thiếu bằng chứng hoàn toàn có mẫu số bằng 0 và được loại khỏi hit/recall. 35/35 lượt truy xuất hoàn tất. Xác minh **165/165 đoạn** về nguồn được chọn, phiên bản PDF, trang và vị trí; phát hiện **0 ca vượt phạm vi**. Thời gian khởi tạo embedding **1,02 s**, làm nóng **0,01 s** và nhập index **13,33 s** được đo riêng. Sau khi dựng lại index cho lần sinh, thứ tự chunk ở **35/35 ca** trùng với phép đo truy xuất riêng. Nhật ký truy xuất và các mốc thiếu từng câu (tệp cục bộ `.run/real_pdf_validation/retrieval.json`).

| Nhóm ca hybrid chính | Số câu | Hit@5 | Mốc tìm được | Câu đạt sơ bộ |
| --- | ---: | ---: | ---: | ---: |
| Một nguồn | 6 | 3/6 | 3/9 | 4/6 |
| Nhiều nguồn | 6 | 1/6 | 1/12 | 0/6 |
| Thiếu hoặc không đủ bằng chứng | 6 | 2/3 | 2/3 | 6/6 |
| Nối tiếp | 6 | 2/6 | 4/8 | 2/6 |

| Chủ đề của tập nguồn đã chọn | Số câu | Hit@5 | Mốc tìm được | Câu đạt sơ bộ |
| --- | ---: | ---: | ---: | ---: |
| HRV, động lực phi tuyến và giấc ngủ | 18 | 6/16 | 7/23 | 9/18 |
| Tối ưu lồi | 2 | 0/1 | 0/2 | 1/2 |
| CPC lọc nhiễu PPG | 2 | 2/2 | 3/3 | 2/2 |
| Liên chủ đề | 2 | 0/2 | 0/4 | 0/2 |

Theo tài liệu, số ca chính có chọn P01–P07 lần lượt là **5, 4, 4, 5, 5, 3, 4**. Số mốc truy được của từng PDF lần lượt là **0/4, 1/4, 1/5, 4/6, 1/5, 0/3, 3/5**. Một ca có thể chọn hai tệp nên số lần chọn tài liệu có phần trùng.

## Hỏi đáp và trích dẫn

| Điều kiện | Hoàn tất | Câu đạt | Ý bắt buộc có mặt | Bám ngữ cảnh¹ | Trích dẫn đúng vị trí² | Nhận định được trích dẫn hỗ trợ¹ | Liên quan cặp trích dẫn–nhận định¹ | Trung vị / p95 (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid chính | 24/24 | 12/24 | 25/44 | 36/36 | 32/32 | 35/36 | 40/40 | 4,10 / 6,69 |
| Hybrid trên tám cặp | 8/8 | 4/8 | 11/15 | 11/11 | 9/9 | 10/11 | 11/11 | 3,76 / 6,18 |
| Vector-only trên tám cặp | 8/8 | 4/8 | 8/15 | 10/10 | 9/9 | 10/10 | 11/11 | 4,05 / 5,75 |
| Pilot hybrid | 3/3 | 3/3 | 3/3 | 4/4 | 4/4 | 4/4 | 5/5 | 3,70 / 4,21 |

¹ Một lượt chấm ngữ nghĩa sơ bộ bởi Codex trên phiếu ẩn cấu hình. Chấm các nhận định có trong đáp án, nên các câu từ chối hoặc đáp án thiếu ý có thể làm mẫu số nhỏ. Mẫu nhỏ và chưa có người chấm độc lập. Tỷ lệ đồng thuận và Cohen’s κ để trống. ² Cột vị trí là kiểm tra bằng mã với PDF gốc. Phiếu ẩn cấu hình (tệp cục bộ `.run/real_pdf_validation/blind_packet.json`) · Mẫu cho người chấm (tệp cục bộ `.run/real_pdf_validation/human_review_template.json`) · Nhãn sơ bộ (tệp cục bộ `.run/real_pdf_validation/codex_labels.json`) · Số liệu tổng hợp (tệp cục bộ `.run/real_pdf_validation/scores.json`).

**Ngân sách và mẫu số.** Hoàn tất 32/32 ca chính và 3/3 ca thử. Có 34 lượt ChatGPT trong ngân sách tối đa 35. N05 không có chunk trong trang 18 của P06 và trả về thông báo thiếu thông tin bằng nhánh cục bộ, không tính là lượt ChatGPT. Lần preflight đầu phát hiện tiến trình YourNote giữ khóa, phát sinh 0 lượt sinh. Sau khi chạy tiếp với backend tạm dừng, không có lỗi sinh hoặc ca chưa chạy. Dịch vụ báo 82.005 token vào và 3.507 token ra, tổng 85.512 trên 34 lượt sinh. Trung vị riêng 23 ca hybrid chính có gọi mô hình là 4,24 s. Độ trễ đo từ lúc bắt đầu xử lý câu hỏi trong runner, không gồm phần dựng index hoặc tương tác UI. Lượt sinh, usage và trích dẫn (tệp cục bộ `.run/real_pdf_validation/inference.json`).

## Ghép cặp và ca điển hình

| ID | Chủ đề | Mốc hybrid | Mốc vector | Đạt hybrid / vector |
| --- | --- | ---: | ---: | --- |
| S02 | Thứ tự BRS qua chu kỳ ngủ | 1/1 | 1/1 | Có / Có |
| S06 | Phạm vi nghiệm tối ưu cục bộ | 0/2 | 1/2 | Không / Không |
| M03 | Khung kiểm định surrogate và cấu hình năm 2015 | 1/2 | 0/2 | Không / Không |
| M06 | Định nghĩa nghiệm tối ưu và trọng số CPC | 0/2 | 0/2 | Không / Không |
| N01 | Hệ số Pearson không báo trong trang được chọn | — | — | Có / Có |
| N06 | Mẫu CPC và giới hạn báo AAE cho nữ | 1/1 | 1/1 | Có / Có |
| F03 | Giải thích NMSPE vượt 1 | 0/1 | 0/1 | Không / Không |
| F06 | Chồng lấn cửa sổ CPC, ECG chuẩn | 2/2 | 2/2 | Có / Có |

Tám cặp hoàn tất, bốn cặp cùng đạt và bốn cặp cùng không đạt theo chấm sơ bộ. Hybrid và vector-only ngang nhau về hit@5 và recall@5 trong tập ghép cặp. S06 và M03 cho thấy sự chênh lệch tìm đoạn theo từng câu, dù tổng bằng nhau.

- **M03, thiếu dữ kiện khi tổng hợp.** Hybrid lấy được P03 trang 4, nên đáp án mô tả đủ các bước kiểm định. Nó lấy P04 trang 2 về NV% và UPI nhưng bỏ P04 trang 3, nơi ghi 250 surrogate cho mỗi chuỗi. Trích dẫn tới hai đoạn đúng vị trí và hỗ trợ những điều đã nêu. Đáp án vẫn thiếu dữ kiện cần để tái lập.
- **S01, mốc chuẩn và bằng chứng hợp lệ khác nhau.** Mốc P01 trang 6 không vào top 5. Mô hình dùng P01 trang 11 để đưa ra cơ chế thay thế phù hợp với yêu cầu nêu một cơ chế. Ca này trượt hit theo mốc đã khóa và đạt theo rubric nội dung.
- **N05, giới hạn trang được thực thi.** Scope đúng P06 trang 18, nơi parser không có văn bản. Hệ thống trả đủ trạng thái không tìm thấy bằng chứng với 0 trích dẫn và 0 lượt mạng.

Phân tích giới hạn ở 24 câu do nhóm soạn từ kho đang dùng và tám cặp đối chứng. Câu hỏi tiếng Việt và các đoạn PDF tiếng Anh cùng xuất hiện trong bộ đo. Chưa có phép đối chứng riêng để lượng hóa ảnh hưởng của khác biệt ngôn ngữ, cấu trúc PDF hoặc giới hạn top 5. Một số câu có đoạn hỗ trợ ngoài mốc ngắn đã chọn, nên cần đọc ngữ cảnh cùng với hit/recall.

**Đối chiếu công khai đã có.** Trên mẫu QASPER khóa ở commit `661b380`, hit@5 là **13/24** cho cả hai phương thức, recall theo câu lần lượt **42,71%** và **45,14%**. Đây là lần đo truy xuất theo đoạn gốc trên dữ liệu và phiên bản benchmark riêng. [Kết quả QASPER lưu trong repo](../evaluation/phase07/artifacts/qasper-retrieval.json).

Tái lập trên PC giữ các PDF cùng SHA-256. Từ `project/`, chạy `.venv/bin/python .run/real_pdf_validation/run.py retrieve` trong thư mục đo riêng để lưu lần đo mới. Chạy `live --confirm-sha <mã_kế_hoạch>` khi đã có quyền kết nối, ngân sách và nơi lưu riêng.
