# Phase 05 — Research Studio và mạng tri thức có bằng chứng

Hoàn thành trong phạm vi Phase 05 ngày 18/11/2026. Chưa triển khai Phase 06; không commit. Giữ Sources/Chat/Studio, model picker và theme đã chốt. So sánh/báo cáo được triển khai và kiểm tra trước graph.

## Luồng sử dụng

Chọn tài liệu trong bảng Nguồn tài liệu, mở một công cụ trong Studio, nhập mục tiêu rồi tạo bằng model hiện đang chọn:

- **So sánh tài liệu**: 2–6 nguồn, 1–6 tiêu chí. Mỗi tiêu chí luôn có một hàng cho từng nguồn; thiếu dữ liệu được ghi “Chưa tìm thấy trong các đoạn đã xét”. Phân biệt thống nhất, mâu thuẫn trực tiếp, khác điều kiện/phạm vi, khác cách diễn đạt và khác biệt khác. Nhận định đối chiếu cần bằng chứng từ ít nhất hai phía.
- **Tổng hợp / Báo cáo**: 1–6 nguồn, ba dạng đề cương ôn tập, giải thích chủ đề, báo cáo tổng hợp. Có mục tiêu, phạm vi, các mục, kết luận và giới hạn; không chỉ phục vụ bài báo.
- **Mạng tri thức**: 1–6 nguồn; khái niệm, định nghĩa, tên thay thế và quan hệ có loại. Viewer có kéo/zoom, tìm tên/alias, lọc nguồn, chi tiết node/cạnh, mở trích dẫn, danh sách khái niệm/quan hệ cho mobile và bàn phím. Mind Map cũ vẫn là công cụ riêng.

Cả ba có tiến trình và Dừng; lưu hoàn tất vào notebook, mở lại không gọi model, chuyển ý/mục/định nghĩa/quan hệ thành ghi chú có quote/locator/version, tải Markdown, xác nhận/hủy xóa từng artifact. Xóa bản cũ trong khi tạo bản mới không làm mất kết quả đang tạo. Đổi model/nguồn không đổi snapshot của tác vụ; rời notebook hủy tác vụ đang chạy.

## Hợp đồng dữ liệu và tích hợp

`src/research_schemas.py` là các DTO độc lập SDK. `src/research.py` xét nguồn và tổng hợp; `src/knowledge.py` dựng graph. `backend/services/core_adapter.py` import các service này khi thực thi, health/OpenAPI không tải RAG/embedding. `backend/services/generation.py` tái dùng task registry/provider context/epoch kết nối/cancel và kiểm tra version từ Phase 03–04.

Workspace schema **3** chỉ thêm `comparison_artifacts`, `report_artifacts`, `graph_artifacts` và giá trị `active_tool`. JSON schema 1/2 thiếu các mảng mới nhận default rỗng; không di chuyển vector, không thay embedding/parser/document ID. Artifact giữ `id/title/createdAt/sourceFilenames/pages/topic/result`; snapshot ngoài artifact phải khớp nguồn bên trong và metadata nếu có. API version 0.5.0.

Result mới có `schema_version:1`, `kind`, `goal`, `sources`, `citations`, `limits`, `source_notes`, `generation` nếu có. Mỗi source ghi `filename/document_id/document_version/total_chunks/examined_chunk_ids/coverage`. `complete` chỉ có nghĩa đã cung cấp đủ chunk **trong phạm vi chọn**; `selected_excerpt` có cảnh báo không được suy ra toàn tài liệu thiếu thông tin.

`GroundedStatement = {text, evidence:[{source_marker,quote}]}`. Quote 8–700 ký tự, phải có nguyên văn trong chunk đã xét (chuẩn hóa Unicode/khoảng trắng, giữ dấu nối và số). Marker toàn tác vụ, filename/id/version/chunk phải khớp coverage. Trích dẫn dùng `Citation`/locator page hoặc paragraph Phase 04, không tạo cơ chế anchor khác. Validator chạy cả khi tạo, reload notebook và export; không chỉ kiểm tra marker tồn tại. Tổng hợp chỉ được dùng lại marker+quote đã xác thực ở lượt đọc nguồn. Báo cáo phải giữ đóng góp từ mọi nguồn có facts.

Graph có `nodes[{id,label,meaning_key,aliases,definition}]`, `edges[{id,source,target,relation,statement}]`, `discarded_relations`, `merge_policy`. Loại quan hệ: `is_a`, `part_of`, `requires`, `causes`, `contrasts_with`, `related_to`, `example_of`, `equivalent_to`, `optimizes`, `measures`, `predicts`, `uses`; có hướng, không self-edge. Không dùng database graph mới.

Gộp chỉ khi cùng meaning_key đã chuẩn hóa **và** trùng label/alias có căn cứ trong nguồn; NFKC/casefold/khoảng trắng, không bỏ dấu để gộp. Từ đồng âm khác meaning_key giữ riêng. Alias không có trong quote bị bỏ. Cạnh sai schema/type/endpoint/marker/quote bị loại và đếm; không còn cạnh hợp lệ thì tác vụ thất bại. Node hỏng hoặc graph vượt giới hạn làm cả tác vụ thất bại. Định nghĩa đã gộp giữ đầy đủ bằng chứng kể cả khi lọc mạng theo một nguồn; bộ lọc không được giấu nguồn cần để hiểu nhận định.

Metadata dùng contract cũ: provider/model yêu cầu/model thực tế/effort, request/notebook ID, thời gian, trạng thái, source versions, calls và usage provider báo. Không lưu credential/connection ID trong artifact, không ước tính chi phí/hạn mức. Export bỏ metadata trước khi validate core DTO rồi thêm thông tin công khai vào Markdown.

## Giới hạn thực thi và stream

- Tối đa **6 nguồn × 6 chunk**, context gốc **60.000 ký tự**, mỗi prompt đã đóng gói tối đa **120.000 ký tự**.
- Xét riêng từng nguồn; nếu >6 chunk, truy xuất hybrid có filter riêng của nguồn đó. Không lấy top-k chung rồi bỏ qua nguồn ít được truy xuất.
- Compare/Report tối đa **N+1** lời gọi: N lượt đọc, 1 tổng hợp. Graph tối đa **N** lượt, dựng/gộp cục bộ. Giới hạn provider task Phase 03 vẫn áp dụng; vượt budget được từ chối trước model.
- Graph tối đa **50 node/100 cạnh**; mỗi lượt nguồn ≤20 node/30 cạnh đề xuất. Layout local tối đa 160 vòng, không gọi model lại khi tương tác.
- **0 bước repair tự động**. Lỗi JSON/schema/quote/marker hoặc đầu ra thiếu nguồn => chưa hoàn tất; không lặp vô hạn, không fallback model/provider.
- Dùng `POST /api/ai/tasks` với `feature=comparison|report|graph`, `input={filenames,document_versions,pages,goal,...}`; comparison thêm criteria, report thêm mode. Không đổi endpoint stream cũ.
- Stream giữ `started/progress/completed/error/cancelled`; progress thêm `stage/completed_steps/total_steps/source_count/chunk_count/planned_calls`, stage `plan/examining/synthesizing/building_graph/validating` cùng preparing/generating cũ. JSON model không gửi thành delta ra UI.
- Cancel hợp tác giữa các bước và đóng upstream khi provider hỗ trợ; chỉ `completed` hợp lệ mới commit/autosave. Hủy/error/incomplete không tạo artifact. Không hoàn lại usage đã tiêu thụ. Backend background job không tự ghi notebook.
- Qdrant vẫn embedded **một worker**; index lock chỉ quanh I/O, không bao cả thời gian chờ model.

## Kiểm tra mock và trình duyệt

Baseline **144/144** backend test trước sửa; sau triển khai **160/160**, gồm **16 test mới** trong `backend/tests/test_research_phase05.py`, `backend/tests/test_knowledge_phase05.py`. Dùng storage/data/index tạm, mock provider; không gọi AI trả phí trong unit test.

Các nhánh mới đã kiểm tra: đủ từng nguồn và missing criterion; khác điều kiện/mâu thuẫn; ba mode báo cáo; unselected source; partial coverage/truy xuất cân bằng; context/call bounds trước inference; schema/quote/marker sai; đồng nghĩa/đồng âm; thiếu cạnh/endpoint/type; graph vượt giới hạn; metadata/model đúng qua mọi bước; cancel/lỗi giữa bước không completed; reload/export; schema 1/2; backup/rollback trả nguyên notebook/ghi chú/index cũ.

Frontend build thành công. Lint exit 0, **12 warning có sẵn**, không warning mới. Health/OpenAPI xác nhận không import `torch/sentence_transformers/src.rag/src.research/src.knowledge` khi mới khởi động.

Chrome headless với API giả lập và profile riêng: **24 tổ hợp** 3 viewer × 360/768/1280/1920px × sáng/tối; không tràn ngang/che footer, không lỗi JS. Kiểm tra create → view → reload không inference → mở anchor/version → note/export → hủy xóa → xóa; progress chia network chunk, dừng, quota, incomplete, xóa cũ khi tạo mới, đổi model/nguồn, rời notebook, stale-version banner; graph search/filter, pointer pan/zoom, keyboard pan/selection, mobile list. Graph ở lượt QA cuối dùng kết quả inference đã lưu trên fixture, không gọi model mới. QA kéo/thả nhanh phát hiện một race khi React xử lý state sau pointer-up; đã sửa bằng cách chụp tọa độ trước updater và chạy lại đầy đủ harness thành công.

Lệnh tái kiểm tra từ `project/` (backend cần biến storage/data trỏ thư mục tạm khi chạy toàn suite):

```bash
.venv/bin/python -m unittest discover -s backend/tests -q
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run lint
.venv/bin/python evaluation/prepare_research_ui.py --live-graph reports/phase05/live-smoke.json
.tools/node/bin/node evaluation/phase05_ui.mjs
```

Browser harness ở `evaluation/phase05_ui.mjs`, proof ở `ui-proof.json`, vài ảnh tiêu biểu trong `ui/`. Các thông báo lỗi do QA cố tình gây ra không phải lỗi inference thật. Cảnh báo Qdrant local payload-index và dòng EOF của negative PDF test là hành vi có sẵn, suite vẫn pass.

## Inference thật và đánh giá bằng chứng

Nguồn tự tạo trung lập ở `evaluation/phase05_fixture.py`: giáo trình DOCX, slide PDF, ghi chú Markdown; MSE thống nhất; gradient descent cần scaling còn cây quyết định không cần (khác điều kiện); LAB-A nhóm A ghi hai ngày hạn nộp (mâu thuẫn trực tiếp); học phí không có trong cả ba nguồn. Không đưa corpus cá nhân vào benchmark.

Chạy `evaluation/run_research.py --model gpt-6.1-terra` với kết nối plan đã được người dùng cấp quyền, backend đã dừng và index/database tạm; cùng TaskRegistry/provider/stream upstream thật. Compare **4 calls**, Graph **3 calls**, cả hai completed và roundtrip lưu/mở lại chính xác; Markdown thực trong `live-comparison.md`, `live-graph.md`, public results/progress/usage trong `live-smoke.json`. Report ba mode và các lỗi giả lập chỉ kiểm tra mock, chưa smoke inference thật riêng.

Có **4 lời gọi Compare** ở lần đầu đã hoàn tất nhưng harness gặp lỗi export vì truyền `generation` vào strict core schema. Sửa lỗi, thêm test hồi quy export có metadata rồi chạy lại có giới hạn. Tổng **11 lời gọi có kết quả** trong Phase 05, không phải 7 cho cả quá trình; không lặp auth/quota, không repair tự động. Usage đầy đủ chỉ có cho lượt smoke hoàn chỉnh 7 calls; không suy ra token/chi phí của lượt đầu đã mất kết quả khỏi RAM.

Đọc thủ công kết quả smoke: 12 hàng tiêu chí-nguồn, 8 có bằng chứng và 4 missing đúng fixture; 3 nhận định đối chiếu đều có hai phía và phân loại đúng. Graph **10 node, 7 cạnh**, 7/7 cạnh có trích đoạn hỗ trợ và direction phù hợp; không cạnh bị loại ở lần thật này. Có gộp MSE/Mean squared error giữa các nguồn; vẫn còn các cặp scaling/normalization hoặc decision_tree/decision_trees khác meaning_key nên chưa gộp. Đây là hạn chế đã biết của chính sách thận trọng. Đánh giá nhỏ này kiểm tra nghiệp vụ và bằng chứng trên fixture, không phải benchmark chất lượng tổng quát.

## Bảo toàn dữ liệu và vận hành

Trước bật backend mới đã dừng một worker, backup nhất quán bằng công cụ Phase 04: `storage/backups/phase05-predeploy-20261118T143347`, verify **15 file**. Không sao lưu .env/keyring/runtime credential. Đối chiếu trước restart: notebook DB và document registry có dữ liệu logic không đổi; **13 tệp nguồn/index** khớp checksum backup. Đường rollback đã kiểm tra trên fixture cả trước/sau workspace schema 3.

Dữ liệu thật tiếp tục có **4 nguồn / 3 notebook**; frontend `http://127.0.0.1:5173`, backend một worker `127.0.0.1:8000`; health/OpenAPI/frontend/proxy 200 và 1 profile kết nối. Không gửi inference trên tài liệu thật để kiểm tra. Không reindex/migrate collection.

Nếu cần phục hồi dữ liệu: dừng backend và mọi tiến trình mở index; dùng công cụ rollback Phase 04 với snapshot trên sau khi cân nhắc các thay đổi dữ liệu mới phát sinh từ lúc backup. Không chạy rollback chỉ để lùi UI: schema 3 có các field mới mà code cũ chưa hiểu; dùng bản code tương thích hoặc phục hồi snapshot nhất quán. Không tự rollback dữ liệu thật trong QA.

## Ranh giới cho Phase 06

Tái sử dụng các DTO/task stream/artifact arrays trên; mở/view/export không được phát sinh inference. Giữ fixtures và chia rõ mock/thật. Mở rộng đánh giá trên môn học/tài liệu dài, đánh giá ngữ nghĩa nhận định/quan hệ và độ đầy đủ retrieval; exact quote đúng vị trí chưa chứng minh mọi diễn giải đúng. Cần đo dùng thử, chất lượng/latency/usage; chưa có tự động xác minh semantic entailment hay graph đa notebook. Graph không biểu diễn riêng quan hệ phủ định, không tự giải quyết mâu thuẫn hay chọn nguồn đúng. Không thêm web research/agent tự hành trong Phase 05.
