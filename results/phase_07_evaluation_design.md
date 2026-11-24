# Phase 07 — Thiết kế và chuẩn bị dữ liệu đánh giá YourNote

Ngày 24/11/2026 · Hoàn thành chuẩn bị dữ liệu, kiểm tra cục bộ và đối chiếu truy xuất trên QASPER.

Bộ đánh giá YourNote gồm **24 câu tiếng Việt**, **3 câu thử riêng** và **5 tài liệu học tập tự tạo**. YourNote phân tích được cả 5 tệp và xác minh **35/35 đoạn chuẩn** tại đúng vị trí trong chỉ mục. Đây là kiểm tra nội bộ về dữ liệu và vị trí nguồn. Để có phép đo trên dữ liệu do nhóm nghiên cứu khác xây dựng, đã chạy hybrid và vector-only trên **24 câu từ 24 bài báo trong tập test QASPER**. Cả hai tìm được bằng chứng cho **13/24 câu**. Phase 07 dùng **0 lượt gọi LLM**. [Kết quả QASPER](#7-đối-chiếu-truy-xuất-trên-benchmark-công-khai)

## 1. Phần kế thừa từ Phase 06

Đã đọc bộ câu hỏi, cấu hình, runner và nhãn chấm của Phase 06. Bản xuất chi tiết có trong commit `9af3864e4beeeb1ef80e299934800a8ae5023109` tại `reports/phase06/{answers,quality,retrieval}.json`. Đã đối chiếu được mã băm của **38/38 lượt** giữa bản xuất từng câu và nhãn chấm. Bản retrieval có 60 dòng theo cặp câu–phương thức. Mỗi dòng lưu trung vị của ba lần đo độ trễ. [Bàn giao Phase 06](../plan/phase_06_evaluation_release.md#bàn-giao-sau-triển-khai)

| Kết quả lịch sử trên bộ Phase 06 | Số liệu kiểm tra được |
| --- | --- |
| Câu trả lời hybrid, `gpt-6.1-terra` | 29/30 đạt khi chấm nghiêm, 30/30 hoàn tất, trung vị 2,90 s, p95 4,51 s |
| Tám ca đối chứng | Hybrid đạt 8/8, vector-only đạt 8/8 |
| Truy xuất ở `k=5` | Mỗi phương thức tìm được ít nhất một đoạn chuẩn ở 23/23 câu có bằng chứng. Recall trung bình theo câu 97,83% ở cả hai phương thức |
| Ca `m08` | Model giải thích đúng phần mini-batch có trong top 5 nhưng thiếu phần full-batch do đoạn cần thiết chưa được truy xuất |

Phase 07 dùng lại cách tạo tệp gốc, chỉ mục tạm, lọc nguồn và phiên bản, truy xuất, cùng kiểm tra vị trí trích dẫn. Bộ mới bổ sung đáp án từng phần, câu nối tiếp có đối tượng tham chiếu rõ và ma trận đối chứng cân bằng theo nhóm. Phase 08 cần bộ đếm lượt thử gửi riêng vì `calls` của runner cũ đếm các kết quả nhận được qua callback. Phép chấm cũ do tác nhân phát triển thực hiện. [Bộ công cụ Phase 06](../evaluation/phase06/)

## 2. Tài liệu và bộ câu hỏi đã chốt

Hồ sơ mô phỏng một buổi thực hành về hai hộp mô hình với hai loại mái trong cùng sân. Các lượt thử và số liệu đều hư cấu, do nhóm soạn cho phép đánh giá, cấp quyền **CC0-1.0**, không chứa dữ liệu người học hoặc tài liệu trích từ bên thứ ba. Bộ chính và bộ thử dùng chung kho tài liệu nhưng có ID, câu hỏi và đơn vị bằng chứng bắt buộc riêng. [Bộ câu hỏi, đáp án và nguồn chuẩn](../evaluation/phase07/fixture.json)

| ID nguồn | Tệp | Phạm vi trích dẫn |
| --- | --- | --- |
| `handout` | `cool-roof-handout.pdf` | PDF tiếng Anh có lớp văn bản, 4 trang |
| `procedures` | `quy-trinh-do.docx` | Quy trình tiếng Việt, 7 đoạn |
| `field_notes` | `ghi-chu-hien-truong.md` | Ghi chú, 7 khối gồm tiêu đề |
| `log` | `nhat-ky-cr04.txt` | Nhật ký lượt chính, 7 đoạn |
| `appendix` | `phu-luc-cr05.txt` | Phiếu lượt thử riêng, 5 đoạn |

| Nhóm | Số câu chính | Tình huống |
| --- | ---: | --- |
| Một nguồn | 6 | Đọc số liệu, điều kiện thao tác hoặc vị trí trong một tài liệu hay trang đã chọn |
| Nhiều nguồn | 6 | Ghép dữ kiện để trả lời. Hai ca yêu cầu giữ cả hai ghi nhận mâu thuẫn khi chưa thể phân xử |
| Thiếu bằng chứng | 6 | Ba ca thiếu toàn bộ thông tin được hỏi, ba ca có thể trả lời một phần |
| Hỏi nối tiếp | 6 | Giải tham chiếu từ lượt đã hoàn tất và tìm bằng chứng trong phạm vi của câu hiện tại |
| **Tổng** | **24** | **21 câu có ít nhất một đoạn chuẩn, gồm 3 câu trả lời được một phần** |

Mỗi mục lưu câu hỏi tiếng Việt, ID, nhóm, nguồn/trang được phép, mệnh đề bắt buộc, dữ kiện thiếu, cách xử lý và đoạn chuẩn gắn trang PDF hoặc số đoạn kèm anchor. Câu nối tiếp có thêm hỏi–đáp đã hoàn tất, nguồn sử dụng và đối tượng tham chiếu. Câu thử gồm một ca đọc trang PDF, một ca ghép hai nguồn và một ca theo tham chiếu hội thoại.

## 3. Kiểm tra cục bộ đã thực hiện

- Tái tạo năm tệp, đối chiếu SHA-256, rồi chạy parser thực tế. Cả **5/5 tệp** đọc được, đủ trang hoặc khối và có dữ liệu phiên bản kể cả sau khi nạp vào chỉ mục Qdrant tạm.
- Kiểm tra **27/27 câu** bằng cách đọc các chunk trong phạm vi được phép. Tìm thấy **35/35 đơn vị bằng chứng chuẩn** đúng đoạn trích và vị trí, tính theo từng câu. Có **0 chunk ngoài phạm vi**. Ba ca thiếu toàn bộ dữ kiện có lý do đã ghi trong bộ câu hỏi. Các lý do thiếu được rà theo nội dung tài liệu.
- Kiểm tra **7/7 ca nối tiếp** gồm 6 ca chính và 1 ca thử. Hàm truy xuất dùng câu hỏi trước để làm rõ tham chiếu. Đáp án cũ được đưa vào prompt dưới dạng lịch sử và bằng chứng vẫn phải đến từ nguồn hiện tại.
- Chạy xếp hạng trên **3 câu thử** với cả hai cách truy xuất. Cả hybrid và vector-only có bằng chứng cho 3/3 câu, với recall trung bình theo câu 83,33%. Mỗi phương thức xác minh được **11/11 vị trí** của chunk trả về. Ở `p07-t02`, đoạn 7 của ghi chú hiện trường có trong chỉ mục nhưng vắng ở top 5 của cả hai cách. Giữ kết quả này để kiểm tra cách ghi nhận ca chỉ lấy được một phần bằng chứng.
- Xem trước cho 32 ca chính và 3 ca thử đúng cấu hình. Khi yêu cầu cả hai tập với trần 34 lượt, CLI báo vượt ngân sách và trả mã thoát 2. Việc đọc toàn bộ chunk của 24 câu chính chỉ dùng để kiểm tra dữ liệu. Top 5 và chất lượng câu trả lời của tập chính sẽ được đo ở Phase 08.
- Chạy lại **13 kiểm thử** của bộ benchmark Phase 06 và parser tài liệu, tất cả đều đạt. Năm phiên bản tệp xuất hiện trong ngữ cảnh Phase 06 vẫn tái tạo được đúng SHA-256 lịch sử.

## 4. Protocol và rubric dùng cho Phase 08

Ba khía cạnh được đo riêng. **Tìm bằng chứng** dùng các đoạn được gán nhãn và kiểm tra top 5, cùng hướng đánh giá nguồn hỗ trợ của KILT và QASPER. **Câu trả lời bám ngữ cảnh** xét mỗi nhận định có suy ra được từ các đoạn đã truy xuất hay không, theo khái niệm *faithfulness* của RAGAS. **Trích dẫn hỗ trợ câu trả lời** xét riêng các đoạn được dẫn, dựa trên ALCE và hướng dẫn chấm bằng người đọc của AIS. YourNote vận dụng các định nghĩa này trên dữ liệu và luồng trích dẫn của mình. Điểm của YourNote dùng người đọc và đơn vị nhận định, còn cách chấm tự động trong các công trình có mô hình và cách gộp điểm riêng. [KILT, NAACL 2021](https://aclanthology.org/2021.naacl-main.200/) · [QASPER, NAACL 2021](https://aclanthology.org/2021.naacl-main.365/) · [RAGAS, EACL 2024](https://aclanthology.org/2024.eacl-demo.16/) · [ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/) · [AIS, Computational Linguistics 2023](https://aclanthology.org/2023.cl-4.2/)

| Chỉ số | Đơn vị và mẫu số |
| --- | --- |
| Evidence hit@5, recall@5 | Đo trên các câu có ít nhất một đơn vị chuẩn. Hit bằng 1 nếu top 5 có ít nhất một đoạn chuẩn. Recall của một câu là số đơn vị chuẩn tìm được chia cho tổng số đơn vị chuẩn của câu đó. Lấy trung bình theo câu, mỗi câu trọng số như nhau. Với ca trả lời được một phần, chỉ tính bằng chứng cho phần có dữ liệu. Nếu chạy đủ, mẫu số là 21 ở hybrid toàn tập và 7 cho mỗi phương thức trên cùng tám câu đối chứng. |
| Tỷ lệ câu trả lời đạt | Số lượt đạt toàn bộ rubric dưới đây chia cho số lượt đã bắt đầu xử lý, gồm lượt lỗi. Tỷ lệ hoàn tất dùng số hoàn tất trên số lượt đã lên kế hoạch. Báo riêng số chưa bắt đầu, số lỗi và mẫu số theo nhóm. |
| Bao phủ ý bắt buộc | Số mệnh đề chuẩn được trả lời đúng chia cho số mệnh đề chuẩn ở các lượt hoàn tất đã chấm. Đo thêm để phân biệt bỏ sót ý với đưa ra nhận định thiếu căn cứ. Ca thiếu toàn bộ dữ kiện được chấm riêng về xử lý thiếu bằng chứng. |
| Trích dẫn đúng vị trí | Số citation có nguồn trong phạm vi, định danh, phiên bản, trang hoặc đoạn và trích đoạn khớp bản gốc chia cho tổng số citation đã kiểm tra. Ghi riêng ca hoàn tất có 0 citation, gồm ca từ chối và ca không dẫn được bằng chứng cho một câu trả lời thực chất. |
| Câu trả lời bám ngữ cảnh (*faithfulness*) | Số nhận định trọng yếu được toàn bộ ngữ cảnh thực tế sau truy xuất hỗ trợ, chia cho số nhận định trọng yếu. Đo trên cùng tập nhận định như hai hàng tiếp theo, kể cả khi câu trả lời không gắn citation. |
| Độ bao phủ của trích dẫn (*citation recall*, theo nhận định) | Số nhận định trọng yếu được các đoạn trích dẫn hợp lệ hỗ trợ đầy đủ chia cho số nhận định trọng yếu. Mỗi nhận định có thể cần kết hợp nhiều đoạn. Nhận định không dẫn nguồn, dẫn sai hoặc dẫn không đủ đều tính 0. Câu từ chối thuần túy được chấm riêng. |
| Độ liên quan của trích dẫn (*citation precision*, theo cặp) | Mỗi cặp duy nhất giữa một nhận định và một marker được tính một lần trong câu trả lời. Cặp đạt khi đoạn dẫn hợp lệ và tự hỗ trợ nhận định hoặc góp phần hỗ trợ nhận định khi kết hợp với các đoạn cùng được dẫn. Nếu các đoạn kết hợp vẫn thiếu căn cứ, các cặp của nhận định đó đều tính 0. Citation không gắn được với nhận định nào tính một cặp không đạt. |
| Thời gian phản hồi | Đồng hồ monotonic từ trước lúc xử lý câu hỏi và tạo truy vấn theo hội thoại đến lúc có câu trả lời hoàn tất và kiểm tra citation. Báo trung vị, p95 theo hạng `ceil(0,95 × n)`, và số lượt hoàn tất `n`. Ghi riêng thời gian truy xuất, thời gian khởi tạo embedding và xây index. Tách lượt hoàn tất do nhánh không cần gọi model nếu có. |

Mọi tỷ lệ luôn kèm tử số và mẫu số. Mẫu số bằng 0 báo **không áp dụng**. Ở tầng truy xuất, bằng chứng được tính theo đoạn trích chuẩn, phiên bản và locator, dùng cách chuẩn hóa Unicode/khoảng trắng của YourNote. Hai trích đoạn chuẩn trên một trang được tính là hai đơn vị; một chunk có thể chứa cả hai.

Một lượt **đạt** khi hoàn tất, trả lời đúng và đủ mệnh đề bắt buộc, giữ đúng đối tượng hỏi và phạm vi, trích dẫn có vị trí hợp lệ và bằng chứng hỗ trợ mọi nhận định trọng yếu. Khi nguồn thiếu dữ kiện, câu trả lời phải chỉ ra giới hạn. Khi nguồn mâu thuẫn, câu trả lời phải dẫn từng ghi nhận và giữ bất định nếu phạm vi chưa cho phép phân xử.

| Tình huống chấm | Quyết định |
| --- | --- |
| **Đúng vị trí, thiếu hỗ trợ.** Trích đúng đoạn quy định ngưỡng lệch 0,2 °C để khẳng định rằng độ lệch thực đo cũng là 0,2 °C ở `p07-i04`. | Vị trí hợp lệ. Nhận định về số đo thực tế thiếu hỗ trợ và lượt không đạt. |
| **Đúng một phần.** Ở `p07-m01` chỉ nêu 13:30 và bỏ kết quả tính giờ kết thúc. Ở `p07-i05`, nêu 13:30 kèm trích dẫn và nói rõ chưa có thông tin điện năng. | Lượt thứ nhất không đạt vì còn mệnh đề có đủ bằng chứng. Lượt thứ hai đạt vì trả lời đủ phần được hỗ trợ và chỉ rõ phần thiếu. |
| **Từ chối thận trọng.** Ở `p07-i01` chỉ được đọc trang 2, trong khi chiều cao đầu dò nằm ở trang 4. | Đạt nếu báo chưa đủ dữ kiện trong phạm vi, không suy đoán chiều cao. |
| **Mâu thuẫn.** Ở `p07-m02`, hai nguồn lần lượt ghi 10 phút và 5 phút. | Đạt nếu quy đúng mỗi số cho nguồn tương ứng, trích dẫn cả hai và nêu chưa thể chốt một số. |

Ngưỡng kỹ thuật đã chốt là **0 ca lộ nguồn ngoài phạm vi** và **0 marker/locator sai**. Mục tiêu **85%** là mốc theo dõi nội bộ cho tỷ lệ câu đạt, do nhóm đặt. [Chính sách đã đóng băng](../evaluation/phase07/policy.json)

### Chấm độc lập và đối chiếu điểm

1. Hai người chấm hiệu chỉnh cách hiểu rubric trên ba ca thử trước. Khi chấm tập chính, người chuẩn bị phiếu xáo thứ tự theo mã lượt, ẩn tên model, phương thức truy xuất, thứ tự chạy và thời lượng. Phiếu chứa câu hỏi, đối tượng tham chiếu, các ý chuẩn, câu trả lời, đoạn truy xuất và marker tương ứng. Mỗi người chấm tất cả lượt hoàn tất độc lập.
2. Tách các nhận định có thể kiểm chứng thành từng dòng và thống nhất danh sách nhận định trước khi gán nhãn. Gộp các ý lặp. Với mỗi nhận định, hai người chấm riêng sự hỗ trợ của toàn bộ ngữ cảnh và của những đoạn được dẫn cho nhận định đó. Đánh dấu cả nhận định đúng trong tài liệu nhưng không được các đoạn đã truy xuất hỗ trợ. Kiểm tra vị trí bằng mã và dùng nhãn ngữ nghĩa để quyết định câu đạt.
3. Lưu hai bộ nhãn gốc. Trên các lượt cả hai đã chấm, báo số đồng thuận, mẫu số và Cohen’s κ cho nhãn đạt/không đạt trước đối chiếu. Nếu κ không xác định do phân bố nhãn có mẫu số bằng 0, vẫn báo tỷ lệ đồng thuận và bảng đếm nhãn. Sau đó đối chiếu bất đồng trên đoạn nguồn và lưu lý do cho quyết định cuối. Nếu chỉ có một người chấm, ghi rõ tình trạng và để trống số đo đồng thuận. [Cohen, 1960](https://doi.org/10.1177/001316446002000104)
4. Báo điểm theo từng nhóm và từng phương thức. Tám cặp đối chứng tiếng Việt được báo theo số cặp cả hai đạt, chỉ hybrid đạt, chỉ vector đạt và cả hai chưa đạt. Các tỷ lệ của bộ 24 câu và chênh lệch ở tám cặp được diễn giải như kết quả mô tả trên mẫu, do các câu dùng chung hồ sơ tài liệu. Tách kết quả đó khỏi độ bao phủ bài báo tiếng Anh và thử nghiệm người dùng.

Phiếu chấm dùng chung `blind_id` và `reviewer_id`. Bảng ý chuẩn ghi `required_claim_id` và `required_claim_covered` theo từng ý, kể cả ý bị bỏ sót. Bảng nhận định ghi `claim_id`, `claim_text`, `supported_by_context`, `supported_by_citations` và `marker_contributions`. Bảng theo lượt ghi `uncertainty_correct`, `strict_pass` và `notes`.

### Lượt lỗi, đo bổ sung và đếm lượt gọi

- Cố định lựa chọn chính là lần bắt đầu đầu tiên của từng cặp ID câu–phương thức trong đợt chính. Lưu cả lỗi và bước xảy ra lỗi. Nếu đã bắt đầu nhưng thiếu bản ghi hoàn tất, ghi `interrupted`. Giữ các ca chưa bắt đầu là `not_run`. Chỉ loại khỏi tổng hợp chính các ca pilot, các lượt bổ sung và các ca chưa bắt đầu. Chỉ số đòi hỏi đầu ra hoàn tất ghi riêng phạm vi và mẫu số.
- Tính lần thử gửi đến nhà cung cấp ngay ở ranh giới gửi, kể cả timeout hoặc lỗi phát sinh sau khi gửi. Lỗi xác thực hay dựng context trước khi gửi được lưu như lỗi ca với 0 lượt gọi. Ở ca trả lời cục bộ vì context rỗng, ghi 0 lượt. Giới hạn một lần gửi mỗi ca, tắt tự thử lại và giữ nguyên model. Khi có lỗi quyền, quota, kết nối, model hoặc phạm vi/locator, dừng đợt liên quan và lưu tiến độ. Mọi lượt bổ sung dùng kế hoạch và ngân sách riêng, không thay dòng chính.
- Log ID ca, nhánh, trạng thái, thời gian, lần gửi, ngữ cảnh và bằng chứng thiếu, câu trả lời, citation, model yêu cầu, model thực tế và usage nếu dịch vụ báo. Trường không được báo giữ `null`. Kiểm tra phiên bản thực tế có tương thích giữa hai lượt trước khi đưa cặp vào bảng đối chứng. Không đưa nội dung ngoài tập tổng hợp hoặc thông tin xác thực vào bản xuất.

## 5. Ma trận chạy và điều kiện bàn giao

Dùng một model được cấp quyền, `k=5`, embedding cục bộ `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` và cùng phiên bản nguồn, phạm vi, prompt, lịch sử, tham số sinh. Phép đối chứng thay bước xếp hạng bằng vector-only. Trong mỗi nhóm có một cặp chạy hybrid trước và một cặp chạy vector trước. Hai lượt trong mỗi cặp được xếp liền nhau và dùng cùng môi trường. Đo trực tiếp qua truy xuất và `answer_from_chunks` với câu hỏi theo nội dung nguồn. Mỗi lượt đo thời gian thực hiện lại bước truy xuất trong lượt đó. Phép đo hướng đến lõi hỏi đáp, mẫu hội thoại chuẩn bị sẵn và phản hồi hoàn tất. Độ trễ giao diện, streaming và nhánh đặc biệt như tóm tắt abstract thuộc phạm vi khác.

| Nhóm | Hybrid toàn tập | ID cho tám cặp hybrid và vector-only |
| --- | ---: | --- |
| Một nguồn | 6 | `p07-s01`, `p07-s03` |
| Nhiều nguồn | 6 | `p07-m01`, `p07-m02` |
| Thiếu bằng chứng | 6 | `p07-i01`, `p07-i04` |
| Hỏi nối tiếp | 6 | `p07-f03`, `p07-f04` |
| **Tổng** | **24** | **Thêm 8 lượt vector-only** |

Trần chính **32 lượt**, thử đầu cuối riêng **tối đa 3 lượt hybrid**, tổng dự trù **tối đa 35**. Bảng so sánh dùng các ID có cả hai kết quả tương đương và công bố số cặp còn đủ. Khi báo chất lượng chung, dùng 24 ca hybrid theo kế hoạch. Cả năm tài liệu đều ngắn và dùng chung một kịch bản tổng hợp, vì vậy kết quả dùng để mô tả tập đã chốt.

**Bước đầu Phase 08.** Xác nhận provider, model thực sự có quyền và ngân sách được phép trước khi gọi thật. Ghi tham số sinh, bản mã chạy, phiên bản embedding/thư viện và mã băm của kế hoạch sau khi xác nhận cấu hình. `gpt-6.1-terra` trong lệnh dưới đây là ID minh họa lấy từ Phase 06. Giữ dữ liệu, prompt và quy tắc chấm đã đóng băng. Nếu thay đổi chúng sau khi xem kết quả, ghi một phép đo khác và giữ bản ban đầu. [Kế hoạch Phase 08](../plan/phase_08_rag_benchmark.md)

## 6. Lệnh tái lập và dấu vết

Chạy từ thư mục `project/`. Lệnh `check` cần embedding đã có trong bộ nhớ đệm cục bộ và dùng kho tạm. `materials` tạo năm tệp cùng `LICENSE.txt` trong thư mục mới. `preview` chỉ xuất kế hoạch JSON để rà soát. [Mã kiểm tra và xem trước](../evaluation/phase07/__main__.py)

```bash
.venv/bin/python -m evaluation.phase07 check
.venv/bin/python -m evaluation.phase07 materials /tmp/yournote-phase07-materials
.venv/bin/python -m evaluation.phase07 preview --provider chatgpt --model gpt-6.1-terra --split main --max-calls 32
.venv/bin/python -m evaluation.phase07 preview --provider chatgpt --model gpt-6.1-terra --split pilot --max-calls 3
```

| Thành phần | Điểm tham chiếu |
| --- | --- |
| Commit ứng dụng khi bắt đầu Phase 07 | `661b380daa604c2fc52a222f8ed892c26f8e5047` |
| Dữ liệu | `0fb256530c406dcce5a9c9d8482bcc3ca591f85cf2ef190c4390bafec5401ceb` |
| Policy | `d376caf4e4db1880a8d52ab824e15a446398ca59071032e94ff4494a7b739241` |
| Rubric, JSON sắp xếp khóa | `3637698bca9ae9e2efab5e4dea560c28cc421ec9ed478e3e0065bb316acf2103` |
| Prompt | `37e079d6b2ed82202f1a10b60debd1b406a7659f89439d30b356b85dd4fa1700` |

SHA-256 của năm tệp gốc có trong `source_sha256` của policy. Lệnh xem trước kèm SHA-256 của mã đánh giá đang chạy và tự tính `plan_sha256` theo cấu hình được chọn. Kiểm tra cục bộ dùng Python 3.12.10, pypdf 5.9.0, qdrant-client 1.19.1 và sentence-transformers 6.1.0. [Mã băm tài liệu và cấu hình](../evaluation/phase07/policy.json)

## 7. Đối chiếu truy xuất trên benchmark công khai

**Câu hỏi đánh giá.** Khi hỏi tiếng Anh về một bài báo khoa học đã chọn, YourNote tìm được đoạn bằng chứng do QASPER gán nhãn đến mức nào? QASPER được công bố tại NAACL 2021. Người đặt câu hỏi đọc tiêu đề và tóm tắt. Người khác đọc bài để trả lời và gán bằng chứng hoặc đánh dấu thiếu thông tin. [Dasigi và cộng sự, 2021](https://aclanthology.org/2021.naacl-main.365/)

**Chọn mẫu trước khi xếp hạng.** Dùng tập test chính thức v0.3 gồm 1.451 câu trên 416 bài. Bộ lọc giữ các câu mà mọi nhãn gốc đều có đáp án và mọi đoạn dẫn ánh xạ duy nhất được về phần thân văn bản. Điều kiện này cho 872 câu trên 366 bài. Sắp ID bài và ID câu theo SHA-256 với seed cố định `YourNote-QASPER-test-v0.3-2026-11-24`. Chọn 24 bài đứng đầu và một câu đứng đầu trong mỗi bài để các câu trong mẫu dùng 24 tài liệu khác nhau. Danh sách câu, vị trí bằng chứng và seed xuất được bằng lệnh xem trước. [Thông tin bộ dữ liệu QASPER](https://huggingface.co/datasets/allenai/qasper) · [Thông tin phiên bản và SHA-256 của Ai2](https://huggingface.co/datasets/allenai/qasper/blob/main/dataset_infos.json)

**Điều kiện đo.** Giữ nguyên câu hỏi tiếng Anh và dùng các đoạn thân bài từ bản phát hành, theo thứ tự gốc. Chuẩn hóa Unicode và khoảng trắng, nạp thành TXT trong kho tạm. Mỗi lượt lọc về đúng bài và phiên bản, lấy tối đa 5 chunk, quy về ID đoạn gốc và gộp các chunk cùng đoạn. Hai phương thức dùng cùng chỉ mục và lần lượt đảo thứ tự chạy giữa các câu. Evidence-F1 tính trên tập đoạn dự đoán, lấy điểm tốt nhất trong các bộ bằng chứng của người gán nhãn, sau đó lấy trung bình theo câu. Recall@5 cũng lấy giá trị tốt nhất theo từng bộ bằng chứng. Phép đo đếm một đoạn khi có chunk thuộc đoạn đó trong top 5. [Cách tính Evidence-F1 của QASPER, mục 4.1](https://aclanthology.org/2021.naacl-main.365.pdf#page=5)

| Chỉ số trên cùng 24 câu | Hybrid | Vector-only |
| --- | ---: | ---: |
| Có ít nhất một đoạn chuẩn trong top 5 | 13/24 (54,17%) | 13/24 (54,17%) |
| Recall đoạn bằng chứng @5, trung bình theo câu | 42,71% | 45,14% |
| Evidence-F1 @5, trung bình theo câu | 23,71% | 23,24% |
| Chunk khớp nguồn, phiên bản và vị trí | 120/120 | 120/120 |

Trong 24 cặp, **10** câu cả hai cùng tìm thấy đoạn chuẩn, **3** câu chỉ hybrid tìm thấy, **3** câu chỉ vector-only tìm thấy và **8** câu cả hai cùng bỏ sót. Chênh lệch trung bình trên mẫu là **−2,43 điểm phần trăm** về recall và **+0,47 điểm phần trăm** về Evidence-F1 cho hybrid so với vector-only. Kết quả mẫu chưa cho cơ sở để kết luận một phương thức tốt hơn. 240/240 vị trí hợp lệ xác nhận khả năng xác định đúng đoạn gốc, kể cả khi đoạn được truy xuất thiếu liên quan. Chạy lại trên một chỉ mục tạm mới cho cùng danh sách đoạn và điểm ở cả 48 lượt.

Đây là **48 lượt truy xuất trên mẫu test QASPER**, dùng **0 lượt gọi LLM**. Mẫu chỉ gồm câu tiếng Anh, có bằng chứng dạng văn bản, trên một bài đã chọn. Kết quả đo khả năng định vị đoạn với top 5 trong phạm vi đó. Chất lượng câu trả lời, trích dẫn xuất hiện trong câu trả lời, thao tác mở trang PDF, câu hỏi nhiều nguồn và câu hỏi tiếng Việt được đánh giá ở các phép đo phù hợp khác. Các điểm ở bảng cần được trình bày cùng thiết lập mẫu và top 5 khi dẫn trước giảng viên.

### Tái lập mẫu và kết quả

Dùng gói test v0.3 từ Ai2 và chạy từ `project/`. Runner kiểm tra SHA-256 của gói trước khi mở, xuất ID và kết quả từng câu, rồi bỏ kho chỉ mục tạm. Bản nguồn QASPER và nội dung bài báo được giữ ở môi trường cục bộ. [Gói test v0.3 từ Ai2](https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-test-and-evaluator-v0.3.tgz) · [Runner QASPER](../evaluation/phase07/qasper.py)

```bash
.venv/bin/python -m evaluation.phase07.qasper /tmp/yournote-qasper-test-v0.3.tgz --preview
.venv/bin/python -m evaluation.phase07.qasper /tmp/yournote-qasper-test-v0.3.tgz
```

| Dấu vết | SHA-256 |
| --- | --- |
| Gói test QASPER v0.3 | `72a52a41193e2838b8074f80ac074b94f956b84886c36a61c58a7df4171bdd72` |
| Danh sách 24 câu, đoạn chuẩn và độ dài tài liệu | `4a99f6db86ba8783f8a19b0592fc81183946e48b98eb748ef9ae6f242ab910be` |

### Cách trình bày trước giảng viên

> Nhóm đối chiếu khả năng truy xuất bằng chứng của YourNote trên một mẫu cố định từ tập test QASPER. Hybrid và vector-only cùng tìm được ít nhất một đoạn chuẩn trong top 5 ở 13/24 câu. Bộ câu hỏi tiếng Việt do nhóm xây dựng sẽ được dùng để đánh giá thêm độ đúng và đủ của câu trả lời, khả năng xử lý nguồn mâu thuẫn, câu hỏi nối tiếp và độ hỗ trợ của trích dẫn. Phần chấm câu trả lời sẽ dùng quy trình hai người chấm độc lập với rubric tham khảo ALCE và AIS.
