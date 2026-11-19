# Phase 06 — Đánh giá và bản bàn giao cục bộ

Ngày chạy: **18/11/2026**. Phiên bản **0.6.0-local** giữ React + FastAPI, chỉ localhost. Kết luận kỹ thuật: **sẵn sàng dùng thử có kiểm soát trên Linux đã kiểm chứng**. Chưa xác minh thị trường, chưa có dùng thử sinh viên thật và chưa phát hành công khai.

## 1. Đối chiếu các phase trước với code và kiểm tra

Không chỉ dựa vào nhãn “hoàn thành” trong bàn giao. Đã đọc code provider/context/capability, OAuth storage/refresh/catalog, task stream/completion/cancel, source/version/locator/history, Studio/graph/workspace/export và script vận hành.

| Phạm vi | Bằng chứng chạy lại trong Phase 06 | Phần chưa thể suy ra |
| --- | --- | --- |
| 01: provider/context | 26 test provider/LLM/context | Không bảo đảm mọi SDK/model tương lai |
| 02: OAuth/plan | 26 test auth/OIDC/provider; 38 inference thật với kết nối được cấp quyền | Không chứng minh mọi tài khoản/gói có cùng catalog/quota |
| 03: stream/task | 18 test task/stream; UI stop/quota/incomplete/snapshot | Hủy best effort không hoàn usage |
| 04: tài liệu/RAG | 32 test docs/history/migration; API thật 4 định dạng; UI reading 16 bố cục; restore bản sao | Chưa OCR, chưa benchmark corpus lớn |
| 05: Research Studio | 16 test; UI các công cụ mới và cũ; graph/citation/note/export/delete | Semantic Studio/graph thật chỉ có bằng chứng nhỏ từ Phase 05 |
| 06: runner/release | 8 test mới và clean source/venv/npm/runtime/restore | Chưa test Windows/macOS hoặc người dùng độc lập |

Tổng toàn suite **168/168**, 0 error/failure/skip; các nhóm trên là phần được ánh xạ tới phase, các test API/RAG/learning/notebook cũ khác vẫn chạy trong tổng. Chi tiết từng test: `checks.json`, `functional-matrix.json`.

Khoảng trống đã hoàn thiện: dataset 30 câu, rubric/ngưỡng/hash, runner opt-in và annotation, entrypoint local frontend đã build, env mẫu, constraints dependency, CLI backup/preview restore, hướng dẫn/demo/study template và archive allowlist. Không thêm nhóm tính năng sản phẩm mới hoặc sửa slide.

## 2. Dataset và ngưỡng chốt trước đo

Dataset CC0-1.0 tự tạo tại `evaluation/phase06/fixture.json`, hash:

`1e777991274e1382a78addb798e1d12eee3f38b6358f413336bc080e52069a89`

Có 6 file giả lập: giáo trình DOCX, slide PDF, ghi chú MD, đề cương TXT, hướng dẫn lab MD và nguồn bẫy ngoài scope. Toàn bộ câu hỏi tiếng Việt, một phần nội dung tiếng Anh. Không dùng corpus cá nhân. Mỗi case có scope/page, quote kỳ vọng, kết quả mong đợi, cách xử lý thiếu dữ liệu, rubric và lịch sử nếu cần.

| Nhóm | Số câu |
| --- | ---: |
| Một nguồn | 10 |
| Nhiều nguồn, gồm đồng thuận/khác điều kiện/mâu thuẫn | 8 |
| Thiếu bằng chứng | 6 |
| Nối tiếp | 6 |
| Tổng | 30 |

23 câu có bằng chứng kỳ vọng; 7 câu cần nêu thiếu dữ liệu, gồm một câu nối tiếp có thông tin sai trong câu trả lời cũ. History được seed như các lượt hoàn tất synthetic, không phải 6 cuộc trò chuyện live tính cả các lượt trước.

`policy.json` được khóa trước retrieval/inference: không vượt scope, không bịa marker/locator, không lộ credential, không mất dữ liệu, không completed sau hủy/lỗi; quan sát bắt buộc bằng 0 lỗi ở ca kiểm tra. Ngưỡng chất lượng ≥85% câu đáp ứng nội dung và hỗ trợ bằng chứng; retrieval hit ≥90%, macro recall ≥85%; từ chối hợp lý ≥85%; answer p95 ≤60s, retrieval warm p95 ≤1000ms. Đây là ngưỡng dùng thử nội bộ, không phải chuẩn chất lượng phổ quát.

## 3. Thiết kế phép so sánh

Cùng parser/fixture/embedding MiniLM 384 chiều, chunk_size 1500/overlap 200, k=5, cùng contextual query/history/prompt/scope. Baseline dùng `retrieve_vector`; pipeline dùng vector+BM25/RRF. Baseline là nhánh ranking có kiểm soát, **không phải binary toàn bộ phiên bản cũ**. Không rollback code hoặc dữ liệu thật.

Người dùng chủ động chọn ngân sách tối đa **38 calls**: 30 câu hybrid +8 câu vector cùng model **gpt-6.1-terra**. Catalog và quyền được kiểm tra trước chạy; effort bỏ trống để dùng mặc định provider. Không fallback/retry inference. Kế hoạch đã duyệt ở `benchmark-plan.json`, kết quả ở `answers.json`. Chỉ chạy một model trong ngân sách được chọn; **chưa có so sánh nhiều model trên cùng retrieval**.

Cấu hình/hash mã và môi trường: `configuration.json`, `environment.json`. Không tính cold embedding/index vào warm retrieval. Latency từng câu live tính retrieval/preparation/inference trong runner, không gồm nhập tài liệu, thao tác UI hoặc thời gian các lượt history seed. Thứ tự hybrid trước/vector sau; không random hóa, không kiểm định thống kê.

## 4. Kết quả retrieval tự động, embedding/index thật

Đo 30 câu, mỗi câu ba lần, lấy median; hit/recall tính trên **23 câu có evidence labels**. Gold theo đơn vị quote cần thiết, không chỉ tên file.

| Metric | Vector baseline | Hybrid |
| --- | ---: | ---: |
| Evidence hit@5 | 23/23 (100%) | 23/23 (100%) |
| Macro evidence recall@5 | 97,83% | 97,83% |
| Vượt scope / 30 câu | 0 | 0 |
| Locator/marker integrity lỗi | 0 | 0 |
| Warm retrieval median | 9,32 ms | 10,87 ms |
| Warm retrieval p95 | 10,04 ms | 12,61 ms |
| LLM calls | 0 | 0 |

Dữ liệu từng câu/cold load: `retrieval.json`. Hai nhánh đạt cùng chất lượng retrieval trên corpus nhỏ này; hybrid chậm hơn một ít. **Không có bằng chứng cải thiện recall của hybrid trong bộ thử này**.

Lần đo đầu có lỗi ở metric: so sánh cả field mặc định rỗng của Locator với gold tối thiểu khiến evidence PDF bị tính thiếu. Đã sửa phép chấm theo các field locator thực sự được gold chỉ định, thêm test hồi quy và đo lại; không đổi fixture, threshold hoặc pipeline để nâng điểm. Bản sai giữ riêng ở `retrieval-metric-bug.json`, không dùng kết luận.

## 5. Inference thật và chấm thủ công

Developer agent đã đọc **toàn bộ 38 output** với source facts và mapping marker/locator. Annotation ở `manual_review.json` gắn hash của answer/context/citations; output thay đổi sẽ bị từ chối dùng điểm cũ. Đây **không phải giám khảo sinh viên độc lập**, không dùng một LLM judge tự chấm làm sự thật.

| Metric | Hybrid toàn bộ | Vector subset đối chiếu |
| --- | ---: | ---: |
| Mẫu số | 30 | 8 |
| Completed | 30/30 | 8/8 |
| Đáp ứng nội dung kỳ vọng + có bằng chứng | **29/30 (96,67%)** | 8/8 (100%) |
| Nhận định đã đưa ra có nguồn hỗ trợ | 30/30 | 8/8 |
| Nêu thiếu dữ liệu hợp lý | 7/7 | 1/1 |
| Median | 2,90 s | 3,33 s |
| p95 | 4,51 s | 4,92 s |
| Calls | 30 | 8 |
| Input token provider báo | 23.214 | 5.930 |
| Output token provider báo | 1.299 | 346 |
| Total token provider báo | 24.513 | 6.276 |

Chỉ so trực tiếp trên **cùng 8 câu**: hybrid 8/8, vector 8/8; hybrid median 3,42s so với vector 3,33s, reported total token 6.542 so với 6.276. Không lấy điểm 29/30 so với 8/8 để kết luận nhánh nào tốt hơn. Tổng đúng **38 calls, 30.789 total token được báo**; không suy ra tiền hoặc phần trăm quota.

Theo nhóm hybrid: một nguồn 10/10, nhiều nguồn 7/8, thiếu bằng chứng 6/6, nối tiếp 6/6.

**Ca chưa đạt m08:** top-5 không chứa đoạn full-batch cần thiết. Model trả đúng mini-batch 32 mẫu và nói ngữ cảnh không có phần full-batch; không bịa phần thiếu, nhưng câu hỏi tổng thể chưa đủ. Lỗi cho thấy model mạnh vẫn bị giới hạn bởi retrieval. Không sửa pipeline rồi chạy bù ngoài ngân sách để che ca lỗi.

Audit tự động dựng lại tài liệu synthetic: **38 context /48 citation**, không dùng nguồn ngoài scope, quote/marker/locator/version khớp original và context. Chuỗi prompt injection nằm trong corpus nhưng **không vào 38 context đã chọn**, nên không tính lần này là kiểm chứng model chống injection thật. Các invariant credential/auth/stream/cancel được kiểm tra riêng bằng test giả lập; không đưa credential thật vào prompt để thử rò rỉ. Chi tiết: `quality.json`.

## 6. Hồi quy, giao diện, cài mới và dữ liệu

- Backend 168 tests; frontend build pass; lint exit 0, **12 cảnh báo có sẵn**, không thêm warning mới. Test dùng kho/runtime tạm và không chạy benchmark thật. Lệnh tái kiểm tra: `.venv/bin/python scripts/check_local.py`; thêm `--ui` khi có Chrome.
- Chrome headless: **48 tổ hợp** =24 Studio +16 PDF/text reader +8 model picker, tại 360/768/1280/1920px, sáng/tối. Tạo/xem/reload/export/note/xóa/cancel-delete; quiz/flashcards/Mind Map cũ; pan/zoom/search/filter/list; scope/model/notebook đổi giữa tác vụ; quota/incomplete/cancel; notes dài, lỗi autosave và phục hồi, reset riêng notebook; lịch sử nguồn/citation. Không tràn ngang/che footer/lỗi JS trong các ca đã kiểm tra. API/profile dùng mock; không gọi đây là toàn bộ UI đã chạy inference thật.
- Clean source không có `.env`, dữ liệu hoặc credential; **venv mới không system-site-packages**, PyTorch 2.14.0+cpu và dependency qua constraints; `pip check` pass; toàn bộ 168 backend tests cũng pass trên venv CPU mới (`clean-tests.json`). `npm ci` +build ở source copy mới pass. Lần cài thử CUDA mặc định được dừng để tránh dependency GPU nhiều GB; bản CPU cài thành công, không thay venv ứng dụng hiện có. Cache embedding đã có; chưa kiểm tra tải embedding từ mạng hoàn toàn mới trên một máy trắng.
- Runtime clean dùng frontend build qua Vite preview loopback và API một worker: health/OpenAPI/frontend, proxy AI session JSON đúng; 6 nguồn thật thuộc 4 định dạng, SQLite/index/embedding thật, không LLM.
- Backup/restore **trên bản sao**: snapshot nhất quán 11 file của fixture, preview restore không ghi dữ liệu, restore giữ nguyên JSON notebook, 6 nguồn, note cũ, summary thiếu metadata và graph. DOCX được cập nhật version trước backup; citation phiên bản cũ vẫn mở được sau restore. Dừng/chạy lại nhiều lần không kẹt Qdrant. Proof: `clean-runtime.json`, `clean-install.json`, `clean-frontend.json`.
- Kho người dùng được backup offline trước benchmark ở đường dẫn ghi trong `backup-proof.json` (15 file), không reindex/xóa dữ liệu thật. Credential/keyring/.env không nằm trong backup hay archive demo. Sau bàn giao dịch vụ dùng lại kho hiện có; xem `running-proof.json` và `preservation-proof.json`.

## 7. Bản bàn giao và cách dùng

- Hướng dẫn: `docs/LOCAL_GUIDE.md`; env mẫu `.env.example`; dependency `requirements-local.txt`/`requirements-local.lock`.
- Khởi động bản local đã build: `bash scripts/start_local.sh`; trạng thái `bash scripts/status.sh`; dừng `bash scripts/stop_all.sh`. Frontend 5173, backend 8000, một worker.
- Backup/verify/preview restore/restore có xác nhận: `scripts/backup_local.py`. Không copy SQLite/index đang ghi hoặc chia sẻ archive nguồn cá nhân.
- Đóng gói nội bộ: `.venv/bin/python scripts/package_local.py`; archive và inventory/SHA256 trong `releases/`. Allowlist loại data/storage/.run/.env/keyring/.venv/node_modules/.git và slide; không publish, commit hoặc tag.
- Demo: `docs/DEMO.md`, dùng tài liệu CC0 tự tạo. Inference cần tài khoản/mạng/hạn mức; mở lại/export/zoom/xóa không cần LLM.
- Dùng thử 3–5 sinh viên: chỉ chuẩn bị `docs/STUDENT_TRIAL.md`, **chưa thực hiện**, không bịa phản hồi hay tự liên hệ.

Benchmark xem preview trước; không tự chạy khi unittest:

```bash
# Preview, không auth/embedding/inference:
.venv/bin/python evaluation/phase06/benchmark.py --models MODEL_DUOC_CAP_QUYEN --baseline-subset --max-calls 38
# Sau khi chủ động chấp nhận plan, dùng đúng hash vừa in; chọn output mới:
.venv/bin/python evaluation/phase06/benchmark.py --models MODEL_DUOC_CAP_QUYEN --baseline-subset --max-calls 38 --live --confirm-plan-sha HASH_VUA_XEM --output reports/phase06/my-new-run.json
# Chỉ retrieval, không dùng hạn mức:
.venv/bin/python evaluation/phase06/benchmark.py --retrieval-only --output reports/phase06/my-retrieval.json
```

Thêm nhiều `--models` sẽ nhân số calls; plan báo budget không đủ và live từ chối. Có `--subset controlled8` hoặc danh sách case ID để giới hạn. Không tự chọn model khác khi model được yêu cầu không còn quyền. Chấm output mới cần annotation mới theo hash; không tái dùng điểm hiện tại.

## 8. Giới hạn và quyết định

Đạt ngưỡng 85% trên bộ 30 câu synthetic và các invariant không thấy vi phạm trong ca đã chạy; phù hợp **thử nghiệm cục bộ có kiểm soát**. Không suy ra chất lượng 96,67% trên tài liệu bất kỳ, bảo đảm an toàn tuyệt đối hoặc ưu thế thị trường.

Chưa có so sánh nhiều model, tài liệu dài/corpus lớn, seed/test set độc lập, chấm bởi nhiều người hoặc độ đồng thuận giám khảo; nhiều lượt baseline chưa random hóa. Chưa smoke inference thật riêng mọi công cụ Studio trong Phase 06; giữ bằng chứng nhỏ từ Phase 03/05 và hồi quy mock. Graph gộp thận trọng còn trùng, không biểu diễn phủ định riêng hoặc tự giải quyết mâu thuẫn. Chưa OCR/web ingestion/cloud/multiuser, chưa Windows/macOS.

Chưa có dữ liệu người dùng để xác nhận giả thuyết sinh viên tận dụng gói AI hiệu quả hơn. Thành công kỹ thuật của bản local là điều kiện để thử giả thuyết đó, không thay thế dùng thử/thị trường. Điều kiện plan/model/quota được đối chiếu lại trong `eligibility.md`, cần kiểm tra lại khi mở rộng phạm vi phát hành.
