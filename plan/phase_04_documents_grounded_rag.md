# Phase 04 — Mở rộng tài liệu và cải thiện RAG có kiểm chứng

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md` và bàn giao Phase 01–03. Chỉ triển khai Phase 04.

## Mục tiêu

Notebook phục vụ tài liệu học tập đa dạng, không phụ thuộc PDF hoặc một chuyên ngành mẫu. Hỏi đáp dùng đúng nguồn, hiểu câu hỏi nối tiếp và đưa người dùng về đúng vị trí bằng chứng.

## Điểm cần khảo sát

- `src/indexing.py`, `src/store.py`, `src/filters.py`, `src/rag.py`, `src/schemas.py`, các template prompt.
- API document/reading, `backend/schemas/api.py`, schema workspace, dịch vụ SQLite và export.
- Frontend Sources, citation, reader và autosave. Hiện filename/locator trong nhiều schema đang giả định `.pdf` và số trang; không chỉ nới phần mở rộng file rồi coi là hỗ trợ xong.
- Cách document ID/chunk ID hiện được tạo; xác định nguy cơ cùng tên/cùng kích thước nhưng khác nội dung.

## Công việc bắt buộc

1. Lập chiến lược migration trước khi ghi dữ liệu: schema có phiên bản, tương thích JSON cũ, liên kết nguồn cũ và bản sao lưu nhất quán. Không vừa chạy backend thật vừa sao chép tùy tiện SQLite/Qdrant đang ghi.
2. Bổ sung ingestion cho DOCX, Markdown và TXT; PDF tiếp tục được hỗ trợ. Kiểm tra loại file, dung lượng, lỗi parse và giới hạn tài nguyên. Hiển thị rõ PDF scan chưa có text cần OCR; chưa bắt buộc triển khai OCR.
3. Định danh tài liệu và phiên bản dựa vào nội dung hoặc cơ chế ổn định đủ tránh ghi đè nhầm. Phân biệt tên hiển thị, tên file và identity. Không làm hỏng citation/reading của PDF cũ khi đổi identity.
4. Dùng locator có loại rõ ràng: PDF theo trang, DOCX/Markdown/TXT theo heading/đoạn hoặc anchor ổn định trong phiên bản nội dung. Không bịa số trang cho định dạng không có layout trang ổn định.
5. Chunk giữ cấu trúc tiêu đề/đoạn và nguồn gốc. Có đường xem văn bản cho định dạng mới; Markdown/HTML khi render phải được xử lý an toàn, không thực thi nội dung từ tài liệu.
6. Xử lý ingest lại không nhân đôi và không giữ chunk cũ đã lỗi thời. Index có thể cập nhật theo từng tài liệu; không yêu cầu xóa toàn bộ corpus. Nếu embedding dimension/model thay đổi, cần collection/migration riêng, không trộn vector không tương thích.
7. Tạo bộ đánh giá nhỏ trước khi chỉnh retrieval. So sánh baseline hiện tại với phương án phù hợp như lexical + vector và hợp nhất kết quả; chỉ thêm reranker nếu có bằng chứng lợi ích và ngân sách tài nguyên cho phép.
8. Áp dụng scope notebook/nguồn/trang ở mọi nhánh truy xuất, kể cả lexical, rewrite, map/reduce và citation. Không lấy ngữ cảnh từ notebook khác hoặc nguồn không được chọn.
9. Hỗ trợ câu hỏi nối tiếp bằng lịch sử có giới hạn và/hoặc viết lại truy vấn. Lấy history từ notebook hiện tại có kiểm tra scope; không tin câu trả lời trước đó là bằng chứng. Chỉ đưa lượt đã hoàn tất vào context.
10. Citation sinh từ chunk/locator thực sự đã dùng, có kiểm tra marker và phiên bản nguồn. Phân biệt citation tồn tại đúng với bằng chứng thực sự hỗ trợ kết luận; việc hỗ trợ ngữ nghĩa cần bộ đánh giá/chấm tay, không tuyên bố chỉ validator ID đã chứng minh tính đúng.
11. Khi nguồn không đủ, trả lời rõ giới hạn; khi đối chiếu nhiều nguồn thì chỉ rõ nguồn nào nói gì. Không đưa kiến thức ngoài nguồn vào như thể tài liệu đã phát biểu.
12. Cập nhật schema, API, workspace, viewer và export nhất quán; dữ liệu PDF/notebook/artifact cũ tiếp tục đọc và trích dẫn được. Lưu trace truy xuất tối thiểu phục vụ đánh giá, không log thô tài liệu riêng tư mặc định.

## Ngoài phạm vi

- Import URL trực tiếp, crawler, tìm kiếm web, OCR tự động, PPTX/XLSX.
- Knowledge Graph hoặc agent tự chạy công cụ.
- Thay embedding model chỉ vì muốn thêm công nghệ mới.

## Kiểm tra và tiêu chí hoàn thành

- Fixture nhỏ do tự tạo: slide PDF có text, giáo trình DOCX, ghi chú Markdown/TXT, hai tài liệu cùng tên khác nội dung, nguồn sửa phiên bản, file rỗng/hỏng và PDF scan.
- Fixture migration riêng mô phỏng notebook/citation/artifact cũ; migration chạy lại an toàn, rollback theo hướng dẫn và không tác động dữ liệu thật khi test.
- Test citation mở đúng trang/anchor; phiên bản cũ không bị âm thầm trỏ sang văn bản mới. Nguồn mới không làm hỏng viewer/export PDF hiện tại.
- Test câu hỏi nối tiếp, không đủ thông tin, nguồn mâu thuẫn và chỉ dẫn độc hại nhúng trong tài liệu.
- Test lọc nguồn chặt ở tất cả retrieval branch; kiểm tra không rò ngữ cảnh ngoài selection.
- Báo cáo baseline/phương án mới trên cùng bộ câu hỏi: truy xuất đúng bằng chứng, câu trả lời có căn cứ, tốc độ và số lời gọi. Không chỉ minh họa bằng vài câu trả lời đẹp.
- Backend tests, frontend build/lint và kiểm tra giao diện nguồn mới trên mobile/desktop.

## Cách làm việc và báo cáo

Triển khai từng phần trong phase, bảo vệ dữ liệu hiện có. Ghi rõ định dạng hỗ trợ, giới hạn parser, schema locator và số liệu đánh giá thật. Không tự triển khai Phase 05.

## Bàn giao sau triển khai

- Trạng thái: **Hoàn thành Phase 04**, ngày 18/11/2026. Giữ giao diện/model picker đã chốt; chưa triển khai Phase 05. Không tự commit.

### Định dạng và giới hạn

PDF, DOCX, Markdown, UTF-8 TXT đã nối xuyên suốt upload → identity/version → chunk/index → Chat/reading/Studio → citation/viewer/export. PDF scan không có text được báo cần OCR, không tạo nguồn rỗng. DOCX hỗ trợ main-body paragraphs, heading style và table-cell text; Markdown hỗ trợ ATX heading/đoạn; các định dạng mới hiển thị bằng text viewer an toàn, không thực thi HTML/script.

Parser chạy subprocess: 30 s wall time, 20 s CPU, 768 MiB address space; upload ≤25 MiB; PDF ≤500 trang; text ≤2 triệu ký tự; ≤10.000 paragraph, ≤5.000 chunk/tài liệu. DOCX ZIP ≤50 MiB giải nén/2.048 entry, giới hạn 10 MiB mỗi entry và tỷ lệ nén; từ chối DTD/entity XML. Chưa OCR, URL, PPTX/XLSX, layout Word đầy đủ hoặc nội dung header/footer/footnote/ảnh/embedded objects.

### Identity/version/locator và migration

- Registry schema 2: `project/storage/documents.sqlite`, `catalog_meta`, `documents`, `document_versions`. Workspace thêm `schema_version: 2`, đọc được JSON thiếu field và schema 1.
- Tách filename khóa nội bộ, original filename và alias theo notebook. Logical document ID mới dựa trên format + hash nội dung ban đầu, giữ ổn định khi cập nhật; `document_version` là SHA-256 của file gốc. Hai file cùng tên/cùng dung lượng khác nội dung không ghi đè nhau. Cùng nội dung/format có dedup; có thể phục hồi index thiếu khi ingest lại.
- Bản gốc bất biến ở `data/.versions/<hash>/<original_filename>`. Cập nhật từng tài liệu phải có document ID + expected version; giữ alias/read state, archive cũ và liên kết notebook. Chunk của phiên bản cũ được dọn khỏi index active, original cũ giữ để xem citation lịch sử.
- Point v2 chưa commit registry không hiện trong library/retrieval. Lỗi ghi/index không biến source dở dang thành source hợp lệ. Retry upsert và dọn phần staging/cũ. Bulk rebuild bao gồm cả nguồn chỉ nằm trong archive; không lấy file PDF legacy ở root để hoàn nguyên một active version đã cập nhật.
- Locator PDF `{kind:"page",page:n}`; DOCX/MD/TXT `{kind:"paragraph",anchor:"b000001",paragraph:n,heading:[...]}`. Không bịa trang; ID anchor chỉ có nghĩa trong content version.
- Citation mới có document ID/version/locator; citation PDF cũ không version được đối chiếu source_text với bản `legacy_version` cố định tại migration, kể cả sau update. Khác số âm/ngày/giá trị không được coi là trùng; không fuzzy-match để che sai khác. Đã sửa và thêm hồi quy cho dấu nối tại ranh giới chunk.

Đã dừng backend trước backup/migration thật. Backup kiểm chứng checksum:

- `project/storage/backups/phase04-preflight-20261118T133309`
- `project/storage/backups/phase04-apply-20261118T134930`

Kết quả thật: đăng ký 4 nguồn, 0 bản gốc thiếu, giữ ID/filename/số chunk; JSON của 3 notebook giữ nguyên. Kiểm chứng 175/175 chunk cũ khớp bản gốc và không vượt scope. Kho hiện có chưa lưu citation trong chat/artifact; khả năng đọc/mở citation cũ, artifact cũ và rollback được xác minh bằng fixture riêng. Không đưa tên/nội dung tài liệu riêng hoặc credential vào báo cáo.

`scripts/migrate_phase04.py` có migration idempotent, checksum backup và rollback; process guard chống chạy cùng backend/Qdrant. Restore giữ bản hiện tại trong `pre-rollback-*`; marker incomplete chặn backend khi thao tác bị ngắt. Không đổi embedding/collection, không re-embed dữ liệu thật. Hướng dẫn chi tiết: `project/reports/phase04/migration.md`.

### Retrieval/history/citation contract

- BM25 + vector, RRF k=60; không reranker hoặc LLM rewrite. Áp dụng filename/selection/page/version trong cả vector/lexical/fetch-all/Studio map-reduce. Giới hạn 20.000 chunk trong scope (`RAG_RETRIEVAL_MAX_CHUNKS`); vượt giới hạn báo lỗi để chọn phạm vi nhỏ hơn.
- Task chụp `document_versions` từ source selection; backend xác minh trước khi gọi provider và trước khi completed. `generation.source_versions` ghi snapshot; update nguồn giữa stream không được lưu kết quả hoàn tất. Giữ provider/model/effort, cancellation, stream contract và completion gate của Phase 03.
- History lấy từ notebook SQLite hiện tại, tối đa 3 lượt đã hoàn tất phù hợp source/page/version (xét tối đa 8 lượt gần nhất). Câu nối tiếp có thể ghép tối đa 2 câu hỏi trước cho retrieval; câu trả lời cũ chỉ làm tham chiếu, không là bằng chứng. Không nhận history tự khai từ frontend và không đưa draft vào lịch sử.
- Citation lấy từ chunk đã truyền cho model; kiểm tra marker, identity, version, locator và excerpt với original. Summary map dùng marker toàn cục qua các batch/reduce, không reset S1 cho mỗi batch. Đây là integrity checks, không tuyên bố chứng minh hỗ trợ ngữ nghĩa.
- Prompt yêu cầu nêu thiếu thông tin, gán rõ nguồn khi mâu thuẫn, coi tài liệu/lịch sử/partial là untrusted data. Nguồn đủ một phần được trả lời phần có bằng chứng và nêu giới hạn.
- Chat thêm `retrieval_trace`: method, query SHA-256, context chunk IDs/count, retrieval duration và số lượt history; không log raw document/query mặc định. Citation/export thêm locator/version và nullable page; dữ liệu cũ vẫn đọc được.

Endpoint bổ sung:

| Method | Route | Vai trò |
| --- | --- | --- |
| POST | `/api/documents/{document_id}/versions?expected_version=...` | Cập nhật có chủ đích một source, cùng format |
| GET | `/api/notebooks/{id}/documents/{doc_id}?version=...` | Metadata đúng phiên bản, có historical flag |
| GET | `/api/notebooks/{id}/documents/{doc_id}/text?version=...` | Đoạn/heading/anchor cho DOCX/MD/TXT |
| GET | `/api/notebooks/{id}/documents/{doc_id}/original?version=...` | Tải original bất biến |
| POST | `/api/notebooks/{id}/citations/resolve` | Xác minh excerpt/version rồi trả locator và metadata |

PDF `/pdf?version=...` tiếp tục hoạt động, bao gồm archived version. Reader bản cũ có thông báo và nút mở bản hiện tại; chặn dùng bản cũ như nguồn active để tạo nội dung mới. HTML/Markdown tài liệu không được đưa vào `innerHTML`.

### Bộ câu hỏi và kết quả thật

Fixture 24 chunk/6 nguồn/16 câu cố định trước chỉnh retrieval; bao quát học tập, mã bài tập/thiết bị dễ nhầm, semantic translation, page/source scope, follow-up, thiếu thông tin, mâu thuẫn và prompt injection. Cùng embedding MiniLM 384 chiều và cùng fixture/hash.

| Chỉ số | Baseline | Bản mới |
| --- | ---: | ---: |
| Hit@1, 14 câu có nhãn | 78,6% | 85,7% |
| Macro recall@3, 14 câu có nhãn | 85,7% | 100% |
| Vượt phạm vi, 16 câu | 0 | 0 |
| Trung vị retrieval, 3 lần/câu | 7,56 ms | 8,29 ms |
| Đúng câu hỏi + bằng chứng, 8 tình huống inference thật | 7/8 | 8/8 |
| Trung vị câu trả lời thật | 3,02 s | 3,21 s |
| Lượt gọi LLM thật | 8 | 8 |
| Total token provider báo | 2.883 | 5.958 |

Inference thật dùng model `gpt-6.1-terra` đã được kiểm chứng trước đó, chỉ fixture tự tạo; tổng 16 calls hoàn tất, 8.841 reported token. Không đổi model/fallback và không suy ra phí hoặc % quota. Agent đối chiếu thủ công toàn bộ 16 output với source/mapping, chưa có giám khảo độc lập. Câu nối tiếp là trường hợp baseline dùng nhầm yêu cầu của bài khác dù marker vẫn tồn tại; bản mới trả đúng đối tượng từ history. Hai phương án cùng qua các câu từ chối/mâu thuẫn/injection trong fixture; không coi đây là bảo đảm cho mọi dữ liệu.

Báo cáo, dữ liệu từng câu và giới hạn: `project/reports/phase04/evaluation.md`, `baseline.json`, `hybrid.json`, `answers.json`. `evaluation/manual_review.json` khóa annotation bằng hash của answer/context/citations; đầu ra khác cần chấm lại. Fixture nhỏ, không có test set độc lập hoặc kiểm định thống kê; lexical chưa benchmark corpus lớn và Studio chưa được chấm semantic toàn bộ bằng inference thật.

### Kiểm tra và runtime

- **144 backend tests đạt**: parser, same-name/same-size, idempotent ingest, missing-index repair, staging failure/update retry, per-source cleanup, version changed mid-task, source/page filters, history scope/version, marker integrity/map-reduce, old citation/artifact, migration/rollback/checksum/incomplete guard.
- Smoke API + MiniLM thật/Qdrant thật trên fixture trong `/tmp`: cả 4 định dạng upload/retrieve/resolve/viewer 200, đúng locator; không gọi thêm LLM. Kết quả `project/reports/phase04/format_smoke.json`.
- Frontend build đạt, lint exit 0 với 12 warning có sẵn. Chrome kiểm tra text/PDF, script/HTML không thực thi, đúng anchor/paragraph navigation, historical version/update, same-name uploads; 16 tổ hợp 360/768/1280/1920px × light/dark × PDF/text, không tràn ngang/lỗi JS. Script/ảnh ở `/tmp/phase04-ui.mjs`, `/tmp/phase04-ui/`.
- Compileall và `git diff --check` đạt. Tests dùng data/storage tạm, không reindex/xóa nguồn thật. Embedding thật lấy từ cache cục bộ; unit AI dùng mock.
- Backend đã bật lại một worker, `.run/backend-phase04.pid` / `.run/backend-phase04.log`; frontend 5173, health/OpenAPI/proxy 200. Đọc được 4 source/3 notebook và phiên ChatGPT keyring đã khôi phục. Nên reload frontend sau thay đổi/backend restart.

Lệnh hồi quy từ `project/` (cấp data root tạm cho cả suite):

```bash
RAG_STORAGE_DIR=/tmp/phase04-test-root/qdrant RAG_DATA_DIR=/tmp/phase04-test-root/data .venv/bin/python -m unittest discover -s backend/tests -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python evaluation/run_retrieval.py --mode hybrid --output reports/phase04/hybrid.json
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run lint
.venv/bin/python -m compileall -q backend src evaluation
git diff --check
```

Tệp/module chính: `src/document_parser.py`, `documents.py`, `locations.py`, `indexing.py`, `store.py`, `filters.py`, `retrieval.py`, `conversation.py`, `grounding.py`, `grounding_markers.py`, `rag.py`, prompt Studio/Chat và `learning.py`; backend schemas/API/reading/generation/notebooks; frontend source upload/menu, CitationList, NotebookWorkspace, TextReader/PdfReader, types/client/useNotebook; `src/data_guard.py`, `src/migration.py`, migration CLI, test Phase 04 và `evaluation/`.

### Điều Phase 05 cần biết

1. Giữ identity `(document_id, document_version, locator/chunk_id)`; không suy ra version từ filename hoặc dùng số trang cho DOCX/MD/TXT. Tái sử dụng resolve-citation để graph/report mở đúng original.
2. Claim/edge có marker hợp lệ vẫn cần kiểm tra ý nghĩa/đối chiếu nguồn. Benchmark này chỉ chấm 8 tình huống Chat, không chứng minh mọi claim trong Research Studio hoặc graph.
3. Giữ task snapshot, history scope/version, completed-only autosave và cancellation. Kết nối/model/effort không được chuyển global; không dùng artifact/answer cũ làm bằng chứng độc lập.
4. Không giữ core/index lock khi chờ model; vẫn một worker. Lexical hiện scroll scope, không thêm reranker/index mới chỉ vì tên công nghệ nếu chưa có số liệu và ngân sách.
5. Không xoá archive vì active source đã cập nhật: citation lịch sử phụ thuộc archived version. Migration/rollback cần dừng backend và restore cùng snapshot, không copy SQLite/Qdrant đang ghi.
6. Dữ liệu cũ không có source version chỉ được xử lý theo liên kết legacy đã kiểm chứng. Thiếu original hoặc excerpt không khớp phải báo giới hạn; không tự trỏ sang active text.
7. Định dạng mới/locator mới trong tương lai phải cập nhật đồng bộ API/schema/workspace/viewer/export, tương thích JSON cũ và bộ fixture. Không thêm URL/OCR/Knowledge Graph trong Phase 04 này.
