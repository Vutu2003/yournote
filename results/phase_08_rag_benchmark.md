# Phase 08 — Đo chất lượng hỏi đáp RAG của YourNote

Ngày 24/11/2026. Đã hoàn tất truy xuất và hỏi đáp thật theo kế hoạch. Các điểm ngữ nghĩa bên dưới là chấm sơ bộ trên phiếu ẩn cấu hình, đang chờ hai người chấm.

## Cấu hình và phạm vi

Phép đo dùng 24 câu tiếng Việt trên 5 tài liệu tổng hợp của Phase 07. Hybrid chạy trên toàn bộ tập. Vector-only chạy trên 8 câu đối chứng đã chốt, mỗi nhóm hai câu. Ba câu thử hybrid được giữ riêng. Hai lượt trong một cặp dùng cùng nguồn, phiên bản, trang, lịch sử, prompt, model và k = 5. Thứ tự trong cặp đã được đảo cân bằng theo nhóm. [Protocol và rubric Phase 07](phase_07_evaluation_design.md)

Runner gọi trực tiếp truy xuất và `answer_from_chunks` trên bản nguồn và chỉ mục Qdrant tạm. Trường hợp nối tiếp dùng lịch sử đã hoàn tất được chuẩn bị sẵn. Phép đo thời gian bao gồm bước tạo truy vấn theo lịch sử, truy xuất, nhận câu trả lời hoàn tất và kiểm tra citation. Giao diện, thời gian nhận token đầu tiên và các nhánh đọc đặc biệt như tóm tắt abstract được để ngoài phạm vi phép đo này.

- Provider và model yêu cầu đã chốt là **ChatGPT plan usage · `gpt-6.1-terra`**. Model xuất hiện trong danh mục của tài khoản tại thời điểm xem trước. Các tham số sinh dùng mặc định phía dịch vụ. Embedding cục bộ dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, chunk 1.500 ký tự và phần chồng lấn 200 ký tự.
- Bản mã ứng dụng gốc `661b380daa604c2fc52a222f8ed892c26f8e5047`. Kế hoạch ghi mã băm phiên bản nội dung mã đang chạy, dữ liệu, từng tệp nguồn, prompt, policy và báo cáo chứa rubric trước lúc sinh câu trả lời. [Kế hoạch cố định](../evaluation/phase08/artifacts/plan.json)
- Kiểm tra đầu vào nạp đủ **5/5 tài liệu**, kiểm tra **27/27 câu** và **35/35 đơn vị bằng chứng chuẩn**. Nơi lưu dữ liệu làm việc của YourNote được tách khỏi chỉ mục benchmark. [Kết quả kiểm tra](../evaluation/phase08/artifacts/preflight.json)

## Truy xuất được xác minh bằng mã

Tập chính hoàn tất **32/32 lượt truy xuất**, thêm **3/3 lượt thử**. Khởi tạo embedding mất **0,97 giây**, tạo chỉ mục tạm mất **1,11 giây**. Các thời gian này được đo riêng khỏi độ trễ truy xuất.

| Cấu hình | Lượt hoàn tất | Evidence hit@5 | Recall@5 trung bình theo câu | Đơn vị chuẩn tìm thấy | Trung vị / p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid toàn tập chính | 24/24 | 21/21 (100%) | 20⅔ / 21 (98,41%) | 30/31 | 23,21 / 26,04 ms |
| Hybrid trên 8 câu đối chứng | 8/8 | 7/7 (100%) | 7/7 (100%) | 9/9 | 23,32 / 26,04 ms |
| Vector-only trên cùng 8 câu | 8/8 | 7/7 (100%) | 7/7 (100%) | 9/9 | 22,29 / 24,82 ms |
| Hybrid trên tập thử riêng | 3/3 | 3/3 (100%) | 2,5/3 (83,33%) | 3/4 | 24,99 / 25,08 ms |

Hit và recall dùng các lượt có ít nhất một đơn vị chuẩn. Trong tập chính, ba câu hybrid thiếu toàn bộ thông tin, trong đó một câu thuộc tám cặp đối chứng. Các câu này được kiểm tra phạm vi nguồn và xử lý thiếu thông tin riêng. Tổng cộng **131/131 vị trí đoạn truy xuất ở tập chính** và **11/11 ở tập thử** khớp nguồn, phiên bản và vị trí. Có **0/35 lượt lộ nguồn ngoài phạm vi** và **0/35 lượt có lỗi vị trí đoạn truy xuất**. Đây là kiểm tra vị trí của đoạn trong ngữ cảnh. Chỉ số vị trí citation trong câu trả lời được tính riêng.

| Nhóm | Hybrid toàn tập | Hit / mẫu số | Recall trung bình | Vector-only đối chứng | Hit / mẫu số | Recall trung bình |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Một nguồn | 6/6 | 6/6 | 100% | 2/2 | 2/2 | 100% |
| Nhiều nguồn | 6/6 | 6/6 | 94,44% | 2/2 | 2/2 | 100% |
| Thiếu bằng chứng | 6/6 | 3/3 | 100% | 2/2 | 1/1 | 100% |
| Hỏi nối tiếp | 6/6 | 6/6 | 100% | 2/2 | 2/2 | 100% |

| Câu đối chứng | Hybrid tìm thấy / đoạn chuẩn | Vector-only tìm thấy / đoạn chuẩn |
| --- | ---: | ---: |
| `p07-s01` | 1/1 | 1/1 |
| `p07-s03` | 1/1 | 1/1 |
| `p07-m01` | 2/2 | 2/2 |
| `p07-m02` | 2/2 | 2/2 |
| `p07-i01` | Không có đoạn chuẩn trong phạm vi | Không có đoạn chuẩn trong phạm vi |
| `p07-i04` | 1/1 | 1/1 |
| `p07-f03` | 1/1 | 1/1 |
| `p07-f04` | 1/1 | 1/1 |

[Chi tiết từng lượt truy xuất, danh sách đoạn và thời gian](../evaluation/phase08/artifacts/retrieval.json)

### Ca thiếu bằng chứng trong top 5

Ở `p07-m04`, câu hỏi yêu cầu đọc hai nguồn về điều kiện so sánh giữa các hộp. Ngữ cảnh có đoạn về **khe thông gió mở như nhau** và **dùng cùng loại đầu dò**. Đoạn 5 của quy trình, quy định hai hộp cách nhau **1,5 m**, có trong chỉ mục nhưng vắng ở top 5. Ca này có hit = 1 và recall = 2/3. Ở câu thử `p07-t02`, top 5 có đoạn nhật ký về việc thiếu ảnh lắp mái hoặc cấu hình bộ ghi, còn đoạn liệt kê loại dữ liệu trong phiếu hiện trường nằm ngoài top 5.

## Hỏi đáp trên mô hình thật

Ba lượt thử hoàn tất và qua kiểm tra kỹ thuật trước khi bắt đầu bộ chính. Bộ chính hoàn tất **32/32 lượt**, gồm **24 hybrid** và **8 vector-only**. Có **0 lượt lỗi** và **0 lượt chưa chạy**. Dịch vụ trả về `gpt-6.1-terra` ở cả 35 lượt, nên tám cặp chính có cùng định danh model được báo. Backend đã được khởi động lại và kiểm tra hoạt động sau phép đo. [Kết quả từng lượt, ngữ cảnh, câu trả lời và trích dẫn](../evaluation/phase08/artifacts/inference.json)

| Cấu hình | Lượt gọi / trần | Vị trí trích dẫn hợp lệ | Lượt hoàn tất không trích dẫn | Trung vị / p95 phản hồi |
| --- | ---: | ---: | ---: | ---: |
| Hybrid toàn tập chính | 24/24 | 30/30 | 3/24 | 3,33 / 4,34 giây |
| Hybrid trên 8 câu đối chứng | 8/8 | 9/9 | 1/8 | 3,42 / 4,17 giây |
| Vector-only trên cùng 8 câu | 8/8 | 10/10 | 1/8 | 3,58 / 4,72 giây |
| Hybrid trên tập thử riêng | 3/3 | 6/6 | 0/3 | 3,59 / 5,18 giây |

Các lượt hoàn tất thiếu trích dẫn đều là câu từ chối khi không có dữ kiện trong phạm vi. Không có lượt hoàn tất bằng nhánh trả lời cục bộ trước khi gọi model. Đợt hỏi đáp khởi tạo embedding trong **1,44 giây** và lập chỉ mục tạm trong **1,35 giây**, tách khỏi thời gian phản hồi. Chỉ số vị trí trích dẫn kiểm tra nguồn, phiên bản, phạm vi, locator và trích đoạn. Mức hỗ trợ nhận định được chấm ở phần dưới.

Tổng cộng dùng **35/35 lượt** qua kết nối ChatGPT. Dịch vụ báo **29.582 token đầu vào** và **1.720 token đầu ra**, tổng **31.302 token**. Tập chính chiếm **28.683 token**, tập thử chiếm **2.619 token**. [Thống kê lượt gọi và usage](../evaluation/phase08/artifacts/inference.json)

### Chấm sơ bộ trên phiếu ẩn cấu hình

Một tác nhân đọc đủ **32 câu trả lời chính và 3 câu thử**, đối chiếu ý bắt buộc, ngữ cảnh và từng trích dẫn. Pilot dùng để xem rubric và được báo riêng. Chưa có nhãn của hai người chấm nên tỷ lệ đồng thuận và Cohen’s κ để trống. Các số liệu ngữ nghĩa trong hai bảng sau mang tính sơ bộ. [Nhãn chấm từng lượt](../evaluation/phase08/artifacts/review/developer_labels.json) · [Điểm và mẫu số](../evaluation/phase08/artifacts/summary/scores.json)

| Chỉ số ngữ nghĩa | Hybrid toàn tập chính | Hybrid trên 8 câu đối chứng | Vector-only trên cùng 8 câu | Hybrid tập thử riêng |
| --- | ---: | ---: | ---: | ---: |
| Câu trả lời đạt đủ rubric | 22/24 (91,67%) | 8/8 | 8/8 | 2/3 |
| Bao phủ ý bắt buộc | 33/35 (94,29%) | 12/12 | 12/12 | 3/4 |
| Nhận định bám ngữ cảnh | 42/42 | 13/13 | 13/13 | 6/6 |
| Nhận định được các citation hỗ trợ đầy đủ | 42/42 | 13/13 | 13/13 | 6/6 |
| Cặp nhận định–citation có đóng góp | 45/45 | 14/14 | 14/15 (93,33%) | 6/6 |

| Nhóm | Hybrid hoàn tất / kế hoạch | Hybrid đạt / số đã chạy | Vector-only hoàn tất / kế hoạch | Vector-only đạt / số đã chạy |
| --- | ---: | ---: | ---: | ---: |
| Một nguồn | 6/6 | 6/6 | 2/2 | 2/2 |
| Nhiều nguồn | 6/6 | 4/6 | 2/2 | 2/2 |
| Thiếu bằng chứng | 6/6 | 6/6 | 2/2 | 2/2 |
| Hỏi nối tiếp | 6/6 | 6/6 | 2/2 | 2/2 |

**Đối chứng trả lời.** Tám ID trong bảng đối chứng truy xuất đều đủ cặp và cùng định danh model được báo. Chấm sơ bộ cho **8 cặp cả hai đạt**, **0 chỉ hybrid đạt**, **0 chỉ vector-only đạt**, **0 cả hai chưa đạt**. Ở `p07-f04`, vector-only trả lời đúng CR-05 lấy mẫu mỗi 2 phút. Đoạn S2 hỗ trợ trực tiếp tần suất. Đoạn S1 giới thiệu CR-05 nhưng không thêm bằng chứng cho tần suất, nên cặp nhận định–S1 bị trừ ở chỉ số độ liên quan trích dẫn. Trên tám câu này, cả hai cùng đạt hit, recall và tỷ lệ câu đạt như nhau. Mẫu tám cặp trên một hồ sơ hư cấu chỉ cho phép kết luận trong phạm vi các ca đã đo. [Chi tiết từng cặp cùng model](../evaluation/phase08/artifacts/summary/scores.json)

### Hai nguyên nhân làm câu trả lời chưa đạt đủ rubric

- **`p07-m04` — thiếu đoạn trong truy xuất.** Câu trả lời dùng S1 cho khe thông gió và S2 cho loại đầu dò, cả hai đều khớp nguồn. Đoạn quy định **1,5 m** vắng trong ngữ cảnh. Model nêu rõ giới hạn và thiếu ý bắt buộc về khoảng cách. Điểm câu là chưa đạt, với hai trong ba ý đạt.
- **`p07-m05` — có đủ đoạn nhưng bỏ sót ý.** Truy xuất có đủ **2/2 đơn vị chuẩn**. Model dẫn đúng **14:00** và **14:10–14:30**, rồi kết luận đúng mốc đọc sớm hơn khoảng mây che. Rubric đã chốt yêu cầu nêu rõ **sớm hơn 10 phút**, nên điểm câu vẫn là chưa đạt. Số liệu này giải thích vì sao tỷ lệ bám ngữ cảnh có thể đạt 100% trong khi tỷ lệ câu đạt và độ bao phủ ý thấp hơn.

Để đối chiếu bằng hai người, dùng hai bản sao của phiếu trắng cùng danh sách nhận định đề xuất. Chỉ dùng phiếu ẩn và phiếu trắng khi chấm độc lập. Bản nhãn sơ bộ và bảng ánh xạ được dùng sau khi đã lưu nhãn gốc của từng người. [Phiếu ẩn cấu hình](../evaluation/phase08/artifacts/review/blinded_packet.json) · [Phiếu trắng cho người chấm](../evaluation/phase08/artifacts/review/human_review_template.json)

## Đối chiếu công khai đã chạy ở Phase 07

Trên mẫu **24 câu tiếng Anh thuộc 24 bài báo QASPER**, hybrid và vector-only cùng có hit@5 **13/24**. Recall trung bình lần lượt là **42,71%** và **45,14%**. Kết quả này dùng đoạn văn từ bài báo khoa học với thiết lập riêng. Điểm ở các bảng tiếng Việt phía trên phản ánh bộ tài liệu học tập tổng hợp của YourNote. [Đối chiếu QASPER](phase_07_evaluation_design.md#7-đối-chiếu-truy-xuất-trên-benchmark-công-khai)

## Tái lập

Chạy từ `project/`. Các lệnh dưới đây kiểm tra dữ liệu rồi tạo một thư mục đo mới.

```bash
.venv/bin/python -m evaluation.phase07 check
.venv/bin/python -m evaluation.phase08.benchmark plan --directory /tmp/yournote-phase08-reproduction --model gpt-6.1-terra
.venv/bin/python -m evaluation.phase08.benchmark retrieval /tmp/yournote-phase08-reproduction/plan.json
```

Để chạy hỏi đáp, dùng lệnh `live <plan.json> --confirm-plan-sha <plan_sha256>` với kế hoạch đã xem trước, kết nối ChatGPT hợp lệ và ngân sách được phép. Runner tạo checkpoint trước mỗi lượt và ngay trước khi gửi HTTP, đếm cả lần thử gửi bị lỗi. Phép đo mới có thư mục riêng. Danh sách đoạn trong ngữ cảnh của **35/35 lượt hỏi đáp** khớp lượt truy xuất riêng. **24 kiểm thử** benchmark, parser và provider đã chạy đạt, gồm ca quota, timeout, marker sai và nhánh không gọi LLM. [Runner](../evaluation/phase08/benchmark.py) · [Công cụ chấm](../evaluation/phase08/review.py)

Khi có hai bản nhãn với `reviewer_id` riêng và `role` là `human`, có thể tổng hợp độc lập vào một thư mục mới bằng lệnh dưới đây. Dùng một bản nhãn riêng với `role` là `adjudicated` để lưu quyết định cuối sau khi đối chiếu.

```bash
.venv/bin/python -m evaluation.phase08.review evaluation/phase08/artifacts/inference.json /tmp/yournote-phase08-human-summary \
  --labels /path/to/reviewer-a.json --labels /path/to/reviewer-b.json
```

Nhật ký và phiếu chấm gốc được lưu cùng mã đánh giá trong `project/evaluation/phase08/artifacts/`. Đường dẫn và mã băm ghi bên trong kế hoạch là của lần chạy đã lưu. Lệnh tái lập tạo kế hoạch mới trong thư mục đầu ra mới.
