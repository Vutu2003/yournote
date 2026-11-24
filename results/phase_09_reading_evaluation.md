# Phase 09 — Đánh giá trải nghiệm đọc tài liệu

Ngày 24/11/2026. Đã hoàn thành kịch bản, phiếu thu thập và kiểm tra nội bộ trên trình duyệt. **Chưa dùng thử với sinh viên.**

## Thiết lập

Hai thẻ A và B yêu cầu chọn đúng nguồn và trang, mở một vị trí, kiểm tra hai dữ kiện và lưu ghi chú. Thẻ A dùng trang 2 về kết quả đo nhiệt độ. Thẻ B dùng trang 4 về kích thước đáy hộp và vị trí đầu dò. Hai thẻ dùng chung một PDF tổng hợp có bốn trang và một nhật ký TXT để kiểm tra việc loại nguồn ngoài phạm vi. Đổi thứ tự điều kiện và thẻ qua bốn chuỗi chạy.

YourNote hiển thị PDF cạnh chat trên máy tính. Điều kiện đối chiếu là một giao diện cục bộ trung tính với câu trả lời và ghi chú ở một tab, PDF ở tab khác. Cả hai trình đọc dùng PDF.js 6.5.438 với cùng tệp và cùng phiên bản nội dung. Hai câu trả lời đã lưu ở Phase 08 đến từ `gpt-6.1-terra` và được dùng như nhau cho mỗi thẻ ở hai điều kiện. Không gửi câu hỏi mới. [Hai thẻ, tiêu chí và thứ tự trình bày](#kịch-bản-dùng-thử-luồng-đọc) · [Dữ liệu nguồn của câu trả lời](../evaluation/phase08/artifacts/inference.json)

Chạy trên Linux x64, Chrome 158.0.8127.88, khung máy tính 1440 × 900. Frontend được biên dịch từ workspace tại commit nền `661b380daa604c2fc52a222f8ed892c26f8e5047`. YourNote sử dụng API FastAPI, tệp PDF gốc, Qdrant và SQLite thực trong thư mục tạm. Kịch bản tự động xác nhận lớp văn bản và trạng thái lưu qua giao diện. Mã băm bản build, hai tài liệu, câu trả lời Phase 08 và kịch bản có trong dữ liệu đo. [Dữ liệu kiểm tra nội bộ](../evaluation/phase09/artifacts/internal-check.json)

## Kết quả kiểm tra nội bộ

| Chỉ số | YourNote · 4 lượt | AI và PDF ở hai tab · 4 lượt |
| --- | ---: | ---: |
| Phạm vi nguồn và trang đúng | 4/4 | 4/4 |
| Mở đúng tệp, phiên bản và trang | 4/4 | 4/4 |
| Hai dữ kiện tìm thấy trong trang gốc | 4/4 | 4/4 |
| Hiển thị model của câu trả lời đã lưu | 4/4 | 4/4 |
| Mở lại ghi chú sau tải lại | 4/4 | 4/4 |
| Hoàn thành / đã bắt đầu | 4/4 | 4/4 |
| Lỗi kỹ thuật / hết giờ / bỏ dở trong lượt đo | 0 / 0 / 0 | 0 / 0 / 0 |
| Đổi tab trong mỗi lượt | 0 | 2 |
| Lượt gọi LLM ở Phase 09 | 0 | 0 |

| Thời gian tự động đo, tính bằng giây | YourNote · trung vị và khoảng | Hai tab · trung vị và khoảng |
| --- | ---: | ---: |
| Hiển thị vị trí đúng | 0,55 · 0,526–0,575 | 0,05 · 0,051–0,070 |
| Xác nhận hai dữ kiện trong lớp văn bản | 0,55 · 0,526–0,575 | 0,05 · 0,052–0,071 |
| Lưu và mở lại được ghi chú, tính từ đầu lượt | 1,40 · 1,374–1,463 | 0,15 · 0,137–0,150 |

Giờ đo bắt đầu sau khi sổ hoặc các tab đã sẵn sàng. PDF ở điều kiện hai tab đã được nạp ở trang 1. Trong YourNote, bấm citation gọi API xác minh rồi mới mở PDF. Mốc mở lại ghi chú của YourNote gồm tự lưu qua API, tải lại và mở lại sổ. Điều kiện hai tab lưu trong trình duyệt. Các khác biệt đó góp phần vào độ trễ kỹ thuật quan sát được. Số đo của script chưa ước lượng thời gian con người đọc, tìm thao tác, đổi tab hoặc diễn giải bằng chứng. [Dữ liệu theo lượt và cấu hình](../evaluation/phase09/artifacts/internal-check.json)

| Lượt | Điều kiện | Thẻ và trang thực tế | Xác nhận đoạn gốc, giây | Mở lại ghi chú, giây |
| --- | --- | --- | ---: | ---: |
| I01-1 | YourNote | A · 2 | 0,555 | 1,374 |
| I01-2 | Hai tab | B · 4 | 0,053 | 0,150 |
| I02-1 | Hai tab | A · 2 | 0,071 | 0,149 |
| I02-2 | YourNote | B · 4 | 0,526 | 1,381 |
| I03-1 | YourNote | B · 4 | 0,575 | 1,463 |
| I03-2 | Hai tab | A · 2 | 0,055 | 0,137 |
| I04-1 | Hai tab | B · 4 | 0,052 | 0,148 |
| I04-2 | YourNote | A · 2 | 0,538 | 1,425 |

### Kiểm tra bổ sung trên YourNote

- Máy tính có **4/4 lượt** PDF cạnh chat. Cả bốn trang mở ở chế độ **Vừa trang**, không có phần cuộn dọc trong khung PDF tại thời điểm mở. [Ảnh YourNote trên máy tính](../evaluation/phase09/artifacts/yournote.png) · [Ảnh đối chiếu tab PDF](../evaluation/phase09/artifacts/separate_tabs.png)
- Ở khung 390 × 844, citation mở đúng trang 2 trong lần kiểm tra. Trang vừa khung ở mức mặc định, vượt khung khi zoom **125%**, rồi vừa lại sau khi bấm **Vừa trang**. Trạng thái **Đã đọc** vẫn bỏ chọn khi mở PDF và được lưu sau khi chủ động tick. [Ảnh khung điện thoại sau khi trở về vừa trang](../evaluation/phase09/artifacts/mobile-pdf.png)
- Khi hiệu chỉnh script, có một lỗi đợi danh sách nguồn và một lần đọc DOM trong lúc giao diện còn tải PDF ở khung nhỏ. Script đã được sửa để đợi dữ liệu sẵn sàng rồi chạy lại cả tám lượt. Số liệu trong báo cáo lấy từ lần chạy xác nhận cuối. Chưa đo tần suất người dùng bấm citation trong lúc sổ đang tải.

## Trạng thái dùng thử với sinh viên

Có **0 người tham gia và 0 nhiệm vụ có người thực hiện**. Chưa có tỷ lệ hoàn thành của sinh viên, số lần cần trợ giúp, điểm tập trung hoặc chênh lệch thời gian ghép theo người. Phiếu CSV tách riêng dữ liệu người tham gia khỏi lượt tự động và đang để trống. Các trang trong PDF thử chứa ít nội dung và hai thẻ dùng chung một tài liệu. Việc phân bổ đổi thứ tự chỉ giảm một phần khả năng quen tài liệu. [Kịch bản tuyển mẫu 3–5 người và cách tính](#kịch-bản-dùng-thử-luồng-đọc) · [Phiếu thu thập trống](../evaluation/phase09/artifacts/collection.csv)

## Tái lập

Chạy từ `project/` với Python cục bộ, Node, Chrome và frontend đã cài dependency. Runner dựng frontend cho cổng loopback riêng và dọn kho tạm khi kết thúc. Dùng một thư mục đầu ra mới để giữ nguyên lần đo đã báo cáo.

```bash
.tools/node/bin/node evaluation/phase09/run.mjs /tmp/yournote-phase09-replay
```

Để phục vụ phiên có người tham gia, chạy `--serve-only`, mở sổ hoặc hai URL được in theo thứ tự của thẻ. Khởi động một phiên mới cho mỗi sinh viên để bắt đầu với ghi chú trống, kể cả khi lặp lại chuỗi phân bổ. Dừng bằng Ctrl+C sau phiên. [Runner trình duyệt](../evaluation/phase09/run.mjs) · [Cấu hình hai thẻ](../evaluation/phase09/scenarios.json)

```bash
.tools/node/bin/node evaluation/phase09/run.mjs /tmp/yournote-phase09-student --serve-only
```

Mã băm kịch bản của lượt gốc đã được kiểm tra trước khi chuyển báo cáo. Các lần chạy mới tính mã băm phần kịch bản bên dưới.

<!-- phase09-study:start -->
## Kịch bản dùng thử luồng đọc

### Hai điều kiện

- **Y · YourNote.** Nguồn, câu trả lời và ghi chú ở cùng một sổ. Bấm citation để mở PDF cạnh chat trên màn hình máy tính.
- **T · AI và PDF ở hai tab.** Bản đối chiếu cục bộ gồm một tab có câu trả lời, thông tin nguồn và ghi chú, cùng một tab PDF mở sẵn ở trang 1. Đọc vị trí trong citation, chuyển tab và nhập trang cần kiểm tra. PDF dùng cùng phiên bản PDF.js và cùng tệp như YourNote. Bản này đại diện cho thao tác mở PDF riêng với một giao diện trung tính.

Hai điều kiện dùng cùng PDF bốn trang về bài thực hành CR-04 và nhật ký làm nguồn ngoài phạm vi. Mỗi thẻ dùng đúng một câu trả lời đã lưu từ Phase 08, cùng nội dung, citation và model được báo là gpt-6.1-terra. Thẻ A và B dùng hai trang có nội dung độc lập trong cùng PDF. Việc đã thấy tài liệu ở lượt đầu có thể giúp thao tác nhanh hơn ở lượt sau. Phân bổ đổi thứ tự để giảm ảnh hưởng này. Không gọi model trong kịch bản đọc và ghi chú.

### Hai thẻ nhiệm vụ

**Hướng dẫn chung.** Chỉ dùng bài thực hành PDF, xác lập phạm vi theo trang mà câu trả lời viện dẫn. Mở trang thực tế, xác nhận hai dữ kiện trong tài liệu, rồi lưu một ghi chú có số trang và hai dữ kiện. Kết thúc khi mở lại được ghi chú. Người điều phối giữ đáp án.

| Thẻ | Tình huống đưa cho người đọc | Khối lượng và đáp án |
| --- | --- | --- |
| A | Bạn cần đối chiếu kết quả đo lúc 14:00 trước khi dùng trong báo cáo thực hành. Tìm số đọc của hai hộp, rồi ghi lại số liệu kèm trang nguồn. | 4 trang, 1 câu đã lưu, 1 lần tìm trang. Trang 2 · mái phản quang 31,2 °C và mái trơn 34,8 °C. |
| B | Bạn cần dựng lại bố trí đo từ bài thực hành. Kiểm tra kích thước đáy hộp và vị trí đặt đầu dò, rồi ghi lại kèm trang nguồn. | 4 trang, 1 câu đã lưu, 1 lần tìm trang. Trang 4 · đáy 40 × 40 cm, đầu dò cao 15 cm so với đáy. |

Hai thẻ cùng yêu cầu đọc hai dữ kiện định lượng rõ ràng tại một vị trí nguồn và tạo một ghi chú. Chuẩn bị điều kiện trước khi bấm giờ. Trên YourNote mở đúng sổ của lượt. Ở điều kiện tab riêng, mở sẵn hai tab và để tab câu trả lời ở trước. Mỗi lượt dùng sổ hoặc phiên ghi chú mới.

### Cách tính trước khi chạy

| Biến | Cách quan sát và cách tính |
| --- | --- |
| Thời gian mở vị trí đúng | Từ khi người điều phối đọc xong thẻ và nói bắt đầu đến khi PDF hiển thị đúng tệp và trang gốc. Trang hiển thị sai trước đó vẫn tính vào thời gian. |
| Thời gian xác nhận bằng chứng | Từ cùng mốc bắt đầu đến khi người đọc chỉ hoặc đọc đúng hai dữ kiện của trang gốc. Tính theo giây. Lần chạy tự động lấy mốc hai chuỗi trong lớp văn bản của trang sẵn sàng. |
| Hoàn thành | Đúng phạm vi, trang, hai dữ kiện và mở lại ghi chú có đủ nội dung. Báo số hoàn thành trên số đã bắt đầu, kèm số lượt theo kế hoạch. Kiểm tra lưu bằng cách tải lại và mở ghi chú hoặc sổ tương ứng. |
| Độ đúng vị trí | Số lượt xác nhận đúng tệp và trang trên số lượt người đọc đã xác nhận vị trí. Ghi riêng chưa xác nhận. |
| Trợ giúp, lỗi thao tác | Đếm một trợ giúp cho mỗi lần người điều phối chỉ bước tiếp theo. Ghi lỗi quan sát được và bước xảy ra. Thao tác tự động không có điểm trợ giúp của người tham gia. |
| Đổi tab/cửa sổ | Đếm lần chuyển giữa tab câu trả lời, tab PDF hoặc cửa sổ cần dùng trong tác vụ. Đổi bảng trong một trang YourNote ghi ở ghi chú quan sát nếu cần. |
| Tập trung tự đánh giá | Hỏi ngay sau mỗi lượt. 1 là thường xuyên mất mạch, 3 là mất mạch vài lần nhưng quay lại được, 5 là giữ được mạch từ đầu đến cuối. |
| Hết giờ, bỏ dở | Giới hạn 300 giây mỗi thẻ. Ghi riêng lượt hết giờ, bỏ dở hoặc lỗi kỹ thuật, mốc cuối và nguyên nhân. Báo thời gian trung vị hoặc khoảng của lượt hoàn tất có thời gian hợp lệ. |

Một lượt bấm giờ bắt đầu ở thao tác chọn nguồn sau khi sổ hoặc các tab đã sẵn sàng. Mốc ghi chú bao gồm thời gian xác nhận lưu và mở lại sau tải lại. Chạy nội bộ ghi thời gian trình duyệt và bước thất bại kỹ thuật. Mức tập trung chỉ ghi trong phiên có người thật.

### Phân bổ nếu có sinh viên đã đồng ý

Dùng mã S01–S05 theo thứ tự tham gia. Mỗi sinh viên dùng cả hai điều kiện và làm mỗi thẻ một lần. Phiên có giới thiệu ngắn và tối đa hai lượt 5 phút, khoảng 15–20 phút cho cả phiên. Điều phối viên nhắc người tham gia có thể dừng và để trống câu hỏi tự đánh giá. Ghi bằng mã và tránh dữ liệu tài khoản. Việc mời người tham gia thuộc về nhóm.

| Mã | Lượt 1 | Lượt 2 |
| --- | --- | --- |
| S01 | Y–A | T–B |
| S02 | T–A | Y–B |
| S03 | Y–B | T–A |
| S04 | T–B | Y–A |
| S05 nếu có | Y–A | T–B |

Ghi hệ điều hành, trình duyệt, cỡ màn hình và mức quen dùng công cụ. Giữ cùng máy và trình duyệt cho hai lượt của mỗi người. Với từng cặp đủ dữ liệu, tính thời gian Y trừ T và trình bày từng cặp trước khi lấy trung vị. Báo mẫu số của thời gian, hoàn thành, trợ giúp và tập trung riêng. Các trường trong phiếu CSV để trống cho đến khi có phiên thật. [Phiếu thu thập](../evaluation/phase09/artifacts/collection.csv) · [Phiếu gốc của dự án](../docs/STUDENT_TRIAL.md)

Câu hỏi cuối phiên dành cho cả hai điều kiện. Bước nào khiến bạn mất mạch đọc? Bạn ngập ngừng ở đâu khi kiểm tra nguồn? Có ghi chú nào bạn chưa chắc đã lưu? Ghi câu trả lời ngắn theo mã, bỏ qua khi người tham gia không muốn trả lời.
<!-- phase09-study:end -->
