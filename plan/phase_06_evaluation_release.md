# Phase 06 — Đánh giá chất lượng và chuẩn bị bản phát hành cục bộ

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md` và bàn giao Phase 01–05. Chỉ triển khai Phase 06.

## Mục tiêu

Tạo bản ứng dụng chạy cục bộ có thể bàn giao, có bằng chứng về tính đúng, độ ổn định và giá trị học tập. Đánh giá trung thực hiệu quả của model lẫn RAG; không dùng vài ảnh chụp đẹp để thay cho kiểm tra.

## Kiểm tra điều kiện đầu vào

- Đối chiếu tiêu chí của từng phase trước với code và bàn giao. Liệt kê phần còn thiếu; không mặc định tài liệu ghi hoàn thành thì tính năng đã chạy.
- Sửa các lỗi tích hợp/hồi quy cần thiết để đạt phạm vi đã chốt. Không phát triển thêm một nhóm tính năng lớn trong phase này.
- Kiểm tra lại tài liệu chính thức về eligibility, model, quota và giới hạn plan usage tại thời điểm phát hành.

## Công việc bắt buộc

1. Đóng băng một bộ đánh giá dùng tài liệu tự tạo hoặc được phép sử dụng, không dùng tài liệu cá nhân thật. Có giáo trình/slide/ghi chú, nhiều định dạng và câu hỏi tiếng Việt; có thể thêm một phần tài liệu tiếng Anh.
2. Bộ hỏi đáp tối thiểu 30 trường hợp: 10 câu một nguồn, 8 câu nhiều nguồn gồm khác biệt/mâu thuẫn, 6 câu thiếu bằng chứng và 6 câu hỏi nối tiếp. Mỗi case có phạm vi nguồn, bằng chứng kỳ vọng, tiêu chí chấm và kết quả kỳ vọng khi không đủ dữ liệu.
3. Thêm bộ ca chức năng riêng cho Studio/graph, quota/auth/stream/cancel, migration và dữ liệu cũ. Ca chức năng không thay thế bộ đánh giá chất lượng câu trả lời.
4. Đặt metric và ngưỡng trước khi chạy so sánh: retrieval evidence hit/recall, mức hỗ trợ bằng chứng của câu trả lời, đúng locator/marker, từ chối hợp lý, độ trễ và số lời gọi/usage được provider báo. Phân biệt kiểm tra tự động với chấm tay; không gọi một điểm LLM tự chấm là sự thật tuyệt đối.
5. Ngưỡng bắt buộc: không dùng nguồn ngoài scope, citation không bịa locator, không lộ credential, không mất dữ liệu ở các ca kiểm tra, tác vụ bị hủy/lỗi không mang trạng thái hoàn tất. Ngưỡng chất lượng gợi ý là ít nhất 85% câu trả lời đạt rubric hỗ trợ bằng chứng; chốt trước khi chạy và báo cả lỗi còn lại.
6. So sánh có kiểm soát để tách hiệu quả: cùng retrieval với các model khả dụng; cùng model với baseline retrieval và pipeline mới. Nếu không thể chạy đủ ma trận, ghi đúng phạm vi và không quy mọi cải thiện cho model mạnh.
7. Baseline cũ chạy trong fixture/index tách biệt; không rollback code làm việc hoặc ghi đè dữ liệu thật. Nếu không tái tạo được baseline đáng tin cậy, ghi rõ thiếu baseline và chỉ báo chất lượng hiện tại.
8. Real-model benchmark có chi phí/hạn mức nên tạo runner opt-in, cho chọn model/subset/giới hạn lời gọi và xem số tác vụ trước khi chạy. Không tự chạy toàn benchmark khi chỉ chạy unit test. Mock đủ cho kiểm tra hồi quy, nhưng không dùng điểm mock để công bố chất lượng model.
9. Hoàn thiện script/hướng dẫn chạy localhost: dependency, env mẫu không chứa secret, khởi động/dừng sạch, health check, một worker Qdrant, cổng dùng, lỗi thường gặp và các loại hệ điều hành đã kiểm chứng. Không tuyên bố hỗ trợ nền tảng chưa test.
10. Hướng dẫn backup/restore nhất quán SQLite + tài liệu + index và dữ liệu phiên bản liên quan; có chạy thử restore trên bản sao. Credential không đi kèm gói demo/backup chia sẻ.
11. Chuẩn bị demo nhỏ có quyền sử dụng: tạo notebook → nhập nhiều nguồn → kết nối/chọn model → hỏi nối tiếp → so sánh → xem bằng chứng → tạo/mở graph → xóa kết quả → reload. Ghi rõ phần inference cần mạng/tài khoản.
12. Chuẩn bị kịch bản dùng thử với 3–5 sinh viên khi có người tham gia: tác vụ, thời gian, chỗ vướng và mức hữu ích. Chỉ chuẩn bị tài liệu và biểu mẫu; không tự nhắn người khác. Nếu chưa có người dùng thật, ghi chưa thực hiện, không bịa phản hồi.
13. Viết báo cáo đánh giá Markdown trong thư mục phù hợp ở `project/reports/`, hướng dẫn sử dụng và release checklist nội bộ. Không sửa bộ slide hiện có hoặc thêm Markdown vào `project/reports/slide/`, nơi người dùng chỉ muốn PPTX/PDF.
14. Phân biệt điều kiện chốt kỹ thuật với xác minh thị trường. Bản cục bộ có thể sẵn sàng thử nghiệm dù chưa đủ người dùng; phải ghi rõ chưa xác nhận giả thuyết người dùng tận dụng gói hiệu quả hơn.

## Ngoài phạm vi

- Deploy cloud, mở public service, phát hành thương mại, tạo tài khoản hoặc gửi thông báo cho người khác.
- Tự mua gói/credit, thay đổi hạn mức tài khoản, chạy benchmark không kiểm soát.
- Bắt buộc chuyển sang desktop native. Ghi quyết định giữ localhost hoặc đề xuất phase đóng gói riêng nếu có bằng chứng cần thiết.
- Tự commit/tag/release công khai hoặc đụng tới slide báo cáo đã chốt.

## Kiểm tra và tiêu chí hoàn thành

- Chạy toàn bộ backend test hiện có và test mới, frontend build/lint; ghi môi trường và lỗi có sẵn nếu còn.
- Kiểm tra thao tác thật trên giao diện ở 360/768/1280/1920px, theme sáng/tối; nội dung dài, modal, viewer và model picker không gây chồng chéo.
- Hồi quy notebook cũ, PDF reading/citation, notes, từng công cụ Studio, xóa/cancel xóa, reset notebook, đổi notebook và autosave khi gặp lỗi.
- Kiểm tra khởi động từ môi trường sạch được mô tả, dừng/chạy lại không kẹt Qdrant, restore từ backup không thiếu nguồn/kết quả.
- Công bố bảng kết quả có model/ngày chạy/cấu hình/mẫu số/cách chấm; chia rõ test mock, inference thật, chấm tự động và chấm tay. Không có số liệu thì ghi chưa đo.
- Nếu chưa có tài khoản/quyền/ngân sách để đánh giá thật, bàn giao runner và phần đã kiểm tra; ghi **chưa hoàn thành xác minh chất lượng với model thật**. Không đánh dấu bản phát hành đã đạt toàn bộ tiêu chí.
- Danh sách known limitations rõ ràng; không có lỗi nghiêm trọng chưa xử lý trong các invariant về dữ liệu, scope, credential và trạng thái tác vụ.

## Cách làm việc và báo cáo

Triển khai các phần còn thiếu trong phạm vi hoàn thiện/phát hành cục bộ, không chỉ viết checklist. Cuối cùng nêu: phần đã chạy được, bằng chứng kiểm tra, chất lượng đo được, hạn chế và lệnh để người dùng tự chạy. Cập nhật bàn giao bên dưới; không công bố phát hành ra ngoài khi chưa được yêu cầu.

## Bàn giao sau triển khai

- **Trạng thái: Hoàn thành Phase 06 trong phạm vi bản cục bộ**, ngày 18/11/2026. Bản `0.6.0-local` sẵn sàng dùng thử có kiểm soát trên Linux đã test; không phát hành công khai, không commit/tag, không sửa slide. Chưa xác minh thị trường.
- **Cách chạy/môi trường:** Python 3.12.10, Node 24.21.0/npm 11.19.0, Linux x86_64. `requirements-local.txt` +constraints snapshot, `.env.example`, `scripts/setup_local.sh`, `scripts/start_local.sh` (frontend build/preview 5173 +API 8000 một worker), `status.sh`, `stop_all.sh`. [Hướng dẫn](../docs/LOCAL_GUIDE.md). Cài mới bằng source copy/venv không system-site-packages, PyTorch 2.14.0+cpu, npm ci/build và pip check đều đạt; embedding dùng cache đã có. Windows/macOS và tải embedding từ máy hoàn toàn trắng chưa test.
- **Dataset/rubric:** CC0 tự tạo 6 nguồn/bốn định dạng, 30 câu tiếng Việt phân bố 10 một nguồn/8 nhiều nguồn/6 thiếu bằng chứng/6 nối tiếp. Scope/evidence/expected-result/history/rubric từng câu trong `evaluation/phase06/fixture.json`. Dataset/prompt/policy hash và ngưỡng ≥85% được chốt trước đo; có gate scope/locator/credential/data/cancel bằng 0 lỗi quan sát. Runner preview mặc định, --live +plan hash +model/subset/call limit; không chạy thật trong unittest.
- **Inference thật:** người dùng chọn tối đa **38 calls**: `gpt-6.1-terra`, 30 hybrid +8 vector-only, cùng prompt/history/embedding/k=5/scope. Toàn bộ 38 completed, 30.789 reported total tokens, không retry/fallback hoặc gọi thêm. Chấm thủ công developer agent và audit riêng, không LLM judge/không phải người dùng độc lập. Hybrid **29/30 (96,67%)** đáp ứng nội dung +có bằng chứng, nhận định đã đưa ra được hỗ trợ 30/30; từ chối hợp lý 7/7. Median 2,90s/p95 4,51s. Ca m08 thiếu full-batch trong top-5, trả một phần đúng và nêu thiếu context; đã ghi lỗi, không che bằng chạy lại.
- **So sánh có kiểm soát:** cùng 8 câu cả hybrid/vector đạt 8/8; không có bằng chứng ưu thế hybrid. Retrieval 30 câu, 23 có gold evidence: cả hai hit@5 100%, macro recall@5 97,83%; 0 vượt scope/locator sai, hybrid warm p95 ~12,61ms so với vector ~10,04ms. Chưa chạy nhiều model trong ngân sách được chọn. Metric PDF ban đầu tính nhầm field mặc định, đã sửa/test/đo lại và giữ bản sai riêng; không đổi gold/ngưỡng/pipeline.
- **Hồi quy:** baseline 160 → **168/168 backend tests**, 0 skip/error/failure; toàn bộ 168 cũng đạt trên venv CPU cài mới. Build pass, lint exit 0 với 12 warning có sẵn. `scripts/check_local.py` luôn dùng storage/runtime tạm, không inference; có --ui. Chrome/API mock **48 bố cục**: 24 Studio +16 reading +8 picker, bốn kích thước 360/768/1280/1920, hai theme; không overflow/che footer/JS error. Đã kiểm tra Studio cũ/mới, note dài, autosave lỗi/phục hồi, reset và xóa/cancel đúng notebook, source versions và citation. Không gọi điểm mock là chất lượng model.
- **Backup/restore:** backup người dùng offline 15 file trước benchmark; DB logic và 13 source/index files khớp sau triển khai. Fixture clean runtime upload 6 nguồn thật, có legacy Summary/note/graph và version update; backup 11 file, restore sang data root khác giữ nguyên state/citation archive, restart không kẹt Qdrant. Không có credential trong backup/demo/archive. Kho thật vẫn **4 nguồn/3 notebook**, một profile kết nối, catalog 10 model; frontend/API/OpenAPI/proxy session đạt sau bật lại.
- **Báo cáo/demo/bản bàn giao:** [báo cáo](https://github.com/Vutu2003/yournote/blob/9af3864e4beeeb1ef80e299934800a8ae5023109/reports/phase06/evaluation.md), JSON proof/answers/annotations/config trong `project/reports/phase06/` và `evaluation/phase06/`; [demo](../docs/DEMO.md), tài liệu sẵn ở `demo/materials/`; [checklist nội bộ](../docs/RELEASE_CHECKLIST.md). `scripts/package_local.py` tạo archive private `project/releases/yournote-local-0.6.0.tar.gz`, SHA256/inventory; allowlist bỏ `.env/.run/keyring/storage/data/.venv/node_modules/.git` và slide. Không public/publish.
- **Dùng thử sinh viên:** chưa thực hiện. Đã chuẩn bị [kịch bản và biểu mẫu trống 3–5 người](../docs/STUDENT_TRIAL.md); không liên hệ ai hoặc bịa phản hồi.
- **Tiêu chí/giới hạn còn lại:** đạt ngưỡng thử nghiệm kỹ thuật và xác minh chất lượng với model thật trên bộ synthetic đã nêu; chưa có đa model, corpus lớn, held-out data, chấm độc lập hoặc người dùng thật. History benchmark là seed hoàn tất, không latency live nhiều lượt. Injection trong corpus không vào 38 context, không tính là ca model chống injection thật. Studio semantic thật giữ bằng chứng nhỏ từ phase trước, không smoke lại mọi công cụ trong Phase 06. Không khẳng định lợi ích tận dụng gói/tiết kiệm usage hoặc thị trường đã được xác minh. Dừng tại Phase 06.
