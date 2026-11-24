# Đánh giá định lượng YourNote

- **Đề tài** Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập
- **Sinh viên** Vũ Trịnh Tú và Nguyễn Quang Dũng
- **Giảng viên hướng dẫn** TS. Võ Lê Cường
- **Ngày tổng hợp** 24/11/2026

## 1. Mục tiêu đánh giá

Khảo sát đối chiếu các ứng dụng AI đa mục đích, notebook chuyên đọc tài liệu và công cụ ôn tập theo những thao tác người học cần thực hiện. Một người đọc có thể đang ở giữa bài báo, cần hỏi về đoạn khó, mở lại đúng vị trí để kiểm tra rồi lưu nhận định cho buổi sau. Từ các chức năng đã khảo sát, nhóm chọn tích hợp sổ theo chủ đề, PDF cạnh hội thoại, trích dẫn mở về nguồn, lựa chọn mô hình được cấp quyền và công cụ tạo tóm tắt, thẻ ghi nhớ, câu hỏi ôn tập. Phần đóng góp của đồ án nằm ở việc kết hợp các chức năng thành một quy trình đọc, hỏi, kiểm tra và lưu kiến thức. [Bối cảnh, khảo sát và hướng đề xuất](../reports/slide/Research_Notebook_HUST.pdf#page=2)

Phép đo tập trung vào hỏi đáp theo nguồn và luồng mở đoạn gốc. Các câu hỏi đánh giá gồm khả năng lấy đủ bằng chứng, trả lời đúng và đủ theo phạm vi, trích dẫn có thể kiểm tra, và thời gian tới khi nhận được câu trả lời hoàn tất. Kiểm tra giao diện xem người đọc có thể chọn nguồn, mở vị trí và mở lại ghi chú bằng các thao tác đã triển khai hay không. Chất lượng nội dung ôn tập trong Studio chưa nằm trong phép đo này.

## 2. Dữ liệu và cấu hình

| Phép đo | Dữ liệu và cách chạy | Chứng cứ |
| --- | --- | --- |
| Hỏi đáp tiếng Việt trên mô hình thật | Tập chính gồm **24 câu tiếng Việt** trên **5 tài liệu tổng hợp**, chia thành bốn nhóm mỗi nhóm **6 câu**. Hybrid chạy toàn bộ và vector-only chạy trên tập con đã định trước, tạo **8 cặp** đối chứng. Có **3 câu thử** riêng. | [Bộ câu hỏi và đáp án chuẩn](../evaluation/phase07/fixture.json) · [Kế hoạch chạy và mã băm](../evaluation/phase08/artifacts/plan.json) |
| Đối chứng truy xuất công khai | **24 câu tiếng Anh từ 24 bài báo** thuộc mẫu test QASPER v0.3, giữ câu có đáp án và bằng chứng bằng văn bản. Mỗi phương thức truy xuất một lần trên mỗi câu, phạm vi giới hạn trong bài báo được chọn. | [Phương pháp chọn mẫu và ánh xạ đoạn](phase_07_evaluation_design.md#7-đối-chiếu-truy-xuất-trên-benchmark-công-khai) · [Dữ liệu từng lượt](../evaluation/phase07/artifacts/qasper-retrieval.json) |
| Kiểm tra giao diện nội bộ | Hai thẻ đọc trên cùng PDF bốn trang. Dùng câu trả lời đã lưu và so YourNote với cách mở PDF ở tab riêng. Mỗi điều kiện chạy **4 lượt** trong Chrome trên máy tính. Có kiểm tra bổ sung ở kích thước điện thoại. | [Kịch bản](phase_09_reading_evaluation.md#kịch-bản-dùng-thử-luồng-đọc) · [Dữ liệu trình duyệt](../evaluation/phase09/artifacts/internal-check.json) |

Phép hỏi đáp dùng kết nối ChatGPT đã cấp quyền với định danh thực tế `gpt-6.1-terra` được dịch vụ trả về ở mọi lượt. Cả hai phương thức truy xuất dùng top 5, cùng embedding đa ngôn ngữ cục bộ, phiên bản nguồn, phạm vi, prompt và lịch sử soạn sẵn cho các câu nối tiếp. Thứ tự chạy trước–sau trong tám cặp được đổi cân bằng. Độ trễ trả lời tính từ khi runner xử lý câu hỏi đến khi nhận xong kết quả và kiểm tra trích dẫn. Thời gian nạp chỉ mục và độ trễ truy xuất riêng dùng đồng hồ monotonic. [Protocol và rubric](phase_07_evaluation_design.md#4-protocol-và-rubric-dùng-cho-phase-08) · [Kế hoạch đã đóng băng](../evaluation/phase08/artifacts/plan.json)

Một câu đạt rubric khi đúng đối tượng, đủ các ý bắt buộc, có bằng chứng thích hợp và xử lý đúng phần thiếu hoặc mâu thuẫn. Vị trí trích dẫn do mã xác minh theo nguồn, phiên bản và trang hoặc đoạn. Mức hỗ trợ do người chấm đọc nhận định và đoạn trích. Hiện đã có **một lượt chấm sơ bộ do tác nhân thực hiện trên phiếu ẩn cấu hình**. Chưa có hai bộ nhãn của người chấm độc lập. [Nhãn sơ bộ theo lượt](../evaluation/phase08/artifacts/review/developer_labels.json) · [Phiếu chấm ẩn cấu hình](../evaluation/phase08/artifacts/review/blinded_packet.json)

## Kết quả

### Hỏi đáp, bằng chứng và thời gian phản hồi

| Cấu hình | Hoàn tất / kế hoạch | Đạt rubric sơ bộ | Trích dẫn đúng vị trí | Nhận định được trích dẫn hỗ trợ | Trung vị / p95 phản hồi | Dữ liệu |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Hybrid trên toàn bộ tập chính | 24/24 | **22/24 (91,67%)** | **30/30** | **42/42** | **3,33 / 4,34 giây** (n = 24) | [Lượt mô hình](../evaluation/phase08/artifacts/inference.json) · [Điểm](../evaluation/phase08/artifacts/summary/scores.json) |
| Hybrid trên tám câu ghép cặp | 8/8 | 8/8 | 9/9 | 13/13 | 3,42 / 4,17 giây (n = 8) | [Lượt mô hình](../evaluation/phase08/artifacts/inference.json) · [Điểm cặp](../evaluation/phase08/artifacts/summary/scores.json) |
| Vector-only trên cùng tám câu | 8/8 | 8/8 | 10/10 | 13/13 | 3,58 / 4,72 giây (n = 8) | [Lượt mô hình](../evaluation/phase08/artifacts/inference.json) · [Điểm cặp](../evaluation/phase08/artifacts/summary/scores.json) |
| Hybrid trên tập thử riêng | 3/3 | 2/3 | 6/6 | 6/6 | 3,59 / 5,18 giây (n = 3) | [Lượt thử và điểm](phase_08_rag_benchmark.md#hỏi-đáp-trên-mô-hình-thật) · [Lượt mô hình](../evaluation/phase08/artifacts/inference.json) |

Tổng **35/35 lượt gọi** hoàn tất, gồm **32/32 lượt chính** và **3/3 lượt thử**, với **0 lượt lỗi**, **0 lượt chưa chạy** và **31.302 token** do dịch vụ báo. Mẫu tám câu hybrid ghép cặp nằm trong 24 lượt hybrid chính. p95 lấy phần tử tại hạng `ceil(0,95 × n)` sau khi sắp thời gian tăng dần. [Nhật ký từng lượt, usage và thống kê thời gian](../evaluation/phase08/artifacts/inference.json)

Hybrid chính trả lời đúng **33/35 ý bắt buộc (94,29%)**. Trong bốn nhóm, một nguồn đạt **6/6**, nhiều nguồn **4/6**, thiếu bằng chứng **6/6** và hỏi nối tiếp **6/6**. **3/24** câu hybrid chính từ chối do thiếu dữ liệu và không có citation. Các câu đó vẫn được chấm xử lý thiếu bằng chứng nhưng không phát sinh mẫu số cho chỉ số vị trí hay hỗ trợ trích dẫn. Tỷ lệ hỗ trợ **42/42** tính trên các nhận định đã phát ra, nên hai ý bị bỏ sót vẫn làm giảm tỷ lệ câu đạt. [Mẫu số và nhãn từng nhóm](../evaluation/phase08/artifacts/summary/scores.json)

Độ liên quan của trích dẫn trên tám câu ghép cặp là **14/14** cặp nhận định–trích dẫn có đóng góp ở hybrid và **14/15** ở vector-only. Cả hai có **8/8 cặp** cùng đạt rubric và cùng định danh mô hình được báo. Chênh lệch thời gian và một trích dẫn dư chỉ mô tả các lượt đã đo. Mẫu ghép cặp chưa cho cơ sở xác định phương thức nào tốt hơn. [Danh sách cặp và độ liên quan](../evaluation/phase08/artifacts/summary/scores.json)

### Truy xuất đoạn chuẩn

| Cấu hình | Hit@5 | Recall@5 trung bình theo câu | Đoạn chuẩn tìm thấy | Trung vị / p95 truy xuất | Dữ liệu |
| --- | ---: | ---: | ---: | ---: | --- |
| Hybrid toàn tập tiếng Việt | **21/21** | **98,41% (n = 21)** | **30/31** | 23,21 / 26,04 ms (n = 24) | [Kết quả từng lượt](../evaluation/phase08/artifacts/retrieval.json) |
| Hybrid trên tám câu ghép cặp | 7/7 | 100% (n = 7) | 9/9 | 23,32 / 26,04 ms (n = 8) | [Kết quả từng lượt](../evaluation/phase08/artifacts/retrieval.json) |
| Vector-only trên cùng tám câu | 7/7 | 100% (n = 7) | 9/9 | 22,29 / 24,82 ms (n = 8) | [Kết quả từng lượt](../evaluation/phase08/artifacts/retrieval.json) |
| QASPER · Hybrid | 13/24 | 42,71% (n = 24) | tính theo các bộ bằng chứng gốc | — | [Kết quả từng bài](../evaluation/phase07/artifacts/qasper-retrieval.json) |
| QASPER · Vector-only | 13/24 | 45,14% (n = 24) | tính theo các bộ bằng chứng gốc | — | [Kết quả từng bài](../evaluation/phase07/artifacts/qasper-retrieval.json) |

Hit@5 là tỷ lệ câu có ít nhất một đoạn chuẩn trong top 5. Recall tính tỷ lệ đoạn chuẩn tìm được cho từng câu rồi lấy trung bình theo câu. Trong tập tiếng Việt, chỉ đưa vào mẫu số các câu có đoạn chuẩn trong phạm vi, nên tập chính tính trên 21 câu và tập ghép cặp tính trên 7 câu. Trên QASPER, recall lấy giá trị tốt nhất trong các bộ đoạn được gán nhãn cho mỗi câu. **48 lượt QASPER** chỉ đo truy xuất trên mẫu bài báo đã chọn. Các lượt QASPER và lượt giao diện đều dùng **0 lượt gọi LLM mới**. Kết quả trên hồ sơ học tập tiếng Việt và bài báo tiếng Anh có điều kiện khác nhau về tài liệu, ngôn ngữ và tập câu hỏi, nên diễn giải theo từng phép đo. [Protocol tính điểm](phase_07_evaluation_design.md) · [Đối chiếu QASPER](../evaluation/phase07/artifacts/qasper-retrieval.json)

### Giao diện đọc và tìm lại bằng chứng

| Điều kiện | Mở đúng nguồn và trang | Mở lại ghi chú | Hoàn tất | Đổi tab mỗi lượt | Dữ liệu |
| --- | ---: | ---: | ---: | ---: | --- |
| YourNote | 4/4 | 4/4 | 4/4 | **0** | [Kịch bản đã chạy](../evaluation/phase09/artifacts/internal-check.json) · [Ảnh PDF cạnh chat](../evaluation/phase09/artifacts/yournote.png) |
| Câu trả lời và PDF ở hai tab | 4/4 | 4/4 | 4/4 | **2** | [Kịch bản đã chạy](../evaluation/phase09/artifacts/internal-check.json) · [Ảnh tab PDF](../evaluation/phase09/artifacts/separate_tabs.png) |

**8/8 lượt kiểm tra giao diện nội bộ** xác nhận đúng hai dữ kiện trên trang và mở lại được ghi chú sau khi tải lại. YourNote hiển thị PDF vừa khung ở các lượt máy tính. Kiểm tra bổ sung ở kích thước điện thoại xác nhận zoom và trở về vừa trang, cùng thao tác chủ động tick đã đọc. Thời gian xác nhận bằng chứng của script có trung vị **0,55 giây ở YourNote** và **0,05 giây ở cách hai tab** (n = 4 mỗi điều kiện). PDF ở điều kiện hai tab đã nạp trước và cơ chế lưu ghi chú khác với YourNote. Thời gian kỹ thuật này dùng để mô tả kịch bản trình duyệt. Chưa có dữ liệu về tốc độ đọc hay mức độ tập trung của sinh viên. [Kết quả theo lượt](phase_09_reading_evaluation.md) · [Ảnh điện thoại](../evaluation/phase09/artifacts/mobile-pdf.png)

## 4. Hai ca giúp giải thích kết quả

| Câu hỏi | Đối chiếu với tài liệu và câu trả lời | Nhận định |
| --- | --- | --- |
| `p07-m04` · So sánh điều kiện giữa hai hộp | Ghi chú hiện trường có đoạn về loại đầu dò và khe thông gió. Đoạn 5 của quy trình yêu cầu hai hộp cách nhau **1,5 m** nhưng vắng khỏi top 5. Câu trả lời nêu đúng hai ý có bằng chứng và báo chưa có thông tin về khoảng cách. | Truy xuất có hit nhưng chỉ lấy **2/3** đơn vị chuẩn. Câu trả lời bám ngữ cảnh và vẫn thiếu một ý cần có. |
| `p07-m05` · Số đọc trước hay trong lúc mây che | Top 5 có cả đoạn đo **14:00** và đoạn ghi mây che **14:10–14:30**. Câu trả lời chỉ ra đúng thứ tự thời gian và dẫn đủ nguồn. | Top 5 có đủ **2/2** đơn vị chuẩn. Rubric đã chốt yêu cầu nêu rõ **sớm hơn 10 phút**. Câu trả lời đúng ý chính của câu hỏi nhưng thiếu chi tiết theo tiêu chí đã định. |

[Bằng chứng chuẩn theo câu](../evaluation/phase07/fixture.json) · [Ngữ cảnh và câu trả lời thật](../evaluation/phase08/artifacts/inference.json) · [Nhãn chấm](../evaluation/phase08/artifacts/review/developer_labels.json)

## 5. Giới hạn và việc tiếp theo

- **Kiểm tra kỹ hơn câu hỏi nhiều nguồn.** Dùng `p07-m04` để rà việc bao phủ bằng chứng theo từng ý và `p07-m05` để kiểm tra độ đủ của câu trả lời. Với bộ câu mới, viết rõ trong câu hỏi nếu bắt buộc nêu chênh lệch số liệu. Giữ riêng dữ liệu đã dùng để rà lỗi và một tập câu mới để đánh giá lại.
- **Đối chiếu điểm với hai người chấm độc lập.** Điểm ngữ nghĩa hiện tại dựa trên một tác nhân và bộ 24 câu có phạm vi chủ đề hẹp. Chấm hai phiếu ẩn cấu hình, báo mức đồng thuận và Cohen’s κ trước khi đối chiếu bất đồng. [Phiếu chấm trắng](../evaluation/phase08/artifacts/review/human_review_template.json)
- **Dùng thử luồng đọc với 3–5 sinh viên đồng ý tham gia.** Hiện có **0 sinh viên và 0 nhiệm vụ do sinh viên thực hiện**. Dùng kịch bản đã chạy thử, đổi thứ tự hai điều kiện và ghi thời gian tìm đúng nguồn, tỷ lệ hoàn thành, trợ giúp và mức tập trung theo người. [Kịch bản](phase_09_reading_evaluation.md#kịch-bản-dùng-thử-luồng-đọc) · [Phiếu thu thập](../evaluation/phase09/artifacts/collection.csv)

### Kiểm tra và tái lập

Đã đối chiếu mã băm kế hoạch, dữ liệu, prompt và protocol. Các **35 cặp nhật ký** truy xuất và hỏi đáp lưu cùng danh sách đoạn phục vụ đánh giá. Kiểm tra lại **46/46 trích dẫn xuất hiện trong câu trả lời** khớp tệp, phiên bản và vị trí gốc, gồm 40 ở tập chính và 6 ở tập thử. Bảng điểm, mẫu số, trung vị, p95 và kết quả QASPER được tính lại từ các lượt đã lưu. Dữ liệu trình duyệt khớp bản câu trả lời đã lưu và phiếu thu thập sinh viên đang trống. [Bản kế hoạch chạy](../evaluation/phase08/artifacts/plan.json) · [Đối chiếu nhập liệu và tái lập hỏi đáp](phase_08_rag_benchmark.md#tái-lập) · [Tái lập giao diện](phase_09_reading_evaluation.md#tái-lập) · [Lệnh và nguồn QASPER](phase_07_evaluation_design.md#tái-lập-mẫu-và-kết-quả)

Bản kết quả QASPER đi kèm là nhật ký của lần chạy xác nhận đã lưu, gồm ID bài, ID câu, vị trí đoạn và điểm từng lượt. Điều kiện tái lập và giấy phép nguồn nằm trong protocol. [Bản kết quả QASPER đã lưu](../evaluation/phase07/artifacts/qasper-retrieval.json)

## Tin nhắn Zalo

Dạ em chào thầy, em xin cập nhật đề tài “Ứng dụng RAG hỗ trợ đọc hiểu và ôn tập tài liệu học tập”. Từ khảo sát các ứng dụng AI đa mục đích, notebook đọc tài liệu và công cụ ôn tập, nhóm em đã triển khai YourNote với PDF cạnh chat, trích dẫn mở về nguồn, chọn mô hình và tạo học liệu. Trên bộ 24 câu tiếng Việt, chấm sơ bộ cho 22/24 câu hybrid đạt. Kết quả đo có 30/30 trích dẫn đúng vị trí và trung vị phản hồi 3,33 giây. Nhóm đã kiểm tra nội bộ luồng đọc và đang chờ chấm độc lập, dùng thử với sinh viên. Em cảm ơn thầy ạ.

## Dàn ý trình chiếu

Đặt sau phần giới thiệu các chức năng, trước phần tổng kết và tài liệu tham khảo. Có thể thay slide tiến độ cũ bằng các nội dung sau. [Bộ slide hiện tại](../reports/slide/Research_Notebook_HUST.pptx)

1. **Thiết kế đánh giá.** Bộ **24 câu tiếng Việt trên 5 tài liệu**, chia theo một nguồn, nhiều nguồn, thiếu bằng chứng và hỏi nối tiếp. Cùng một mô hình và top 5 cho **8 cặp hybrid–vector-only**. Dành một dòng ghi riêng phần kiểm tra giao diện bằng câu trả lời đã lưu.
2. **Kết quả hỏi đáp và truy xuất.** Đưa **22/24 câu đạt rubric sơ bộ**, **30/30 trích dẫn đúng vị trí** và **3,33 / 4,34 giây** cho trung vị và p95. Ghi hybrid và vector-only cùng đạt trên **8/8 cặp**. Trình bày QASPER ở một dòng riêng với **13/24 câu** tìm được đoạn chuẩn ở cả hai phương thức, kèm nhãn mẫu bài báo tiếng Anh. Minh họa ca thiếu đoạn quy định khoảng cách **1,5 m** trong top 5.
3. **Luồng đọc và kiểm tra bằng chứng.** Dùng ảnh chụp YourNote có PDF cạnh chat. Nêu **8/8 lượt nội bộ** mở đúng nguồn và mở lại được ghi chú. Kịch bản YourNote có **0 lần đổi tab**, cách mở PDF riêng có **2 lần**. Ghi rõ đây là kịch bản trình duyệt và chưa có dữ liệu sinh viên. [Ảnh giao diện](../evaluation/phase09/artifacts/yournote.png)
4. **Giới hạn và việc tiếp theo.** Rà câu hỏi nhiều nguồn. Đối chiếu nhãn của hai người chấm. Dùng thử với **3–5 sinh viên** để đo thời gian tìm bằng chứng, trợ giúp và mức tập trung.

[Mẫu số, dữ liệu gốc và các ca phân tích](#kết-quả)
