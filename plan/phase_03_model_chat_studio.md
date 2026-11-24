# Phase 03 — Chọn model và sử dụng trong Chat/Studio

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md` và bàn giao Phase 01–02. Chỉ triển khai Phase 03.

## Mục tiêu

Người dùng chọn kết nối/model được cấp quyền rồi dùng cho các chức năng hiện có. Chat hiển thị phản hồi dần, có dừng tác vụ; Studio sử dụng đúng model được chọn và chỉ lưu kết quả hợp lệ. Giao diện giữ phong cách đã chốt.

## Điều kiện đầu vào

- Provider abstraction, kết nối an toàn và catalog model từ phase trước đã có.
- Nếu inference thật của Phase 02 chưa được kiểm chứng, vẫn có thể làm UI/test độc lập nhưng không đánh dấu hoàn thành tích hợp thật.
- Đọc luồng Chat, reading chat, map/reduce Studio, autosave và xóa artifact hiện có trước khi sửa.

## Công việc bắt buộc

1. Thêm lựa chọn provider/kết nối/model ở vị trí gọn, dùng được trên mobile và desktop. Chỉ hiển thị model được cấp quyền; có trạng thái tải catalog, không có model hoặc kết nối hết hiệu lực.
2. Lưu lựa chọn mặc định như preference không chứa secret. Model ID cũ không còn hợp lệ phải yêu cầu chọn lại; không tự dùng một model khác. Phân biệt lựa chọn hiện tại với model đã tạo kết quả cũ.
3. Khi gửi tác vụ, chụp lại provider, model, kết nối, notebook và phạm vi nguồn thành snapshot. Thay model/nguồn hoặc mở notebook khác trong lúc chờ không được đổi hay gán nhầm kết quả đang chạy.
4. Tích hợp tất cả đường gọi: Chat, reading chat, Summary, Quiz, Flashcards và Mind Map, kể cả nhánh chia lô/tổng hợp. Capability của provider quyết định tham số gửi đi.
5. Thêm API stream riêng hoặc mở rộng có tương thích cho Chat và reading chat. Định nghĩa rõ sự kiện bắt đầu, text delta, kết quả/citation cuối và lỗi/hủy. Parser frontend xử lý được sự kiện bị chia thành nhiều network chunk.
6. Với plan usage, dùng stream upstream đúng yêu cầu; không coi stream kết thúc kết nối là tác vụ hoàn tất. Lỗi quota hoặc lỗi khác sau khi đã có text phải hiện đúng trạng thái.
7. Nút **Dừng** hủy request phía trình duyệt và truyền hủy tới upstream khi được hỗ trợ. Không hứa hủy sẽ hoàn usage đã tiêu thụ. Ngăn tác vụ bị hủy tiếp tục ghi đè autosave hoặc tạo artifact hoàn tất.
8. Chat chưa hoàn tất được phân biệt rõ với câu trả lời đã xác nhận. Chọn chính sách lưu bản nháp/dở dang có schema trạng thái rõ, hoặc không lưu; không trộn text dở dang vào lịch sử ngữ cảnh đáng tin cậy.
9. Studio không cần stream raw JSON ra UI. Có trạng thái tạo/hủy/thất bại; chỉ lưu artifact sau khi parse và validate schema/citation thành công. Với map/reduce nhiều lời gọi, kiểm tra hủy giữa các bước và giới hạn công việc hợp lý.
10. Lưu metadata không nhạy cảm cho lần tạo mới: provider, model thực tế, thời gian, trạng thái và usage nếu có. Dữ liệu cũ thiếu metadata vẫn mở được. Không bịa phần trăm hạn mức còn lại hoặc chi phí.
11. Thêm thông tin đang dùng gói và liên kết quản lý usage chính thức. Không retry quota/auth lặp, không tự chuyển sang API tính phí, không tự hạ model khi lỗi. Việc người dùng chọn provider khác phải là hành động rõ ràng.
12. Kiểm tra khóa core: giữ an toàn cho embedded Qdrant một worker; tránh giữ khóa truy cập index trong toàn thời gian chờ stream mạng nếu có thể tách an toàn. Không tăng worker để né vấn đề khóa.

## Ngoài phạm vi

- Định dạng tài liệu mới, multi-turn retrieval nâng cao và Knowledge Graph.
- Tái thiết kế Sources/Chat/Studio hoặc thêm nhiều tùy chọn kỹ thuật vào composer.
- Tự động chọn model theo giá/chất lượng khi chưa có hành vi được người dùng chấp thuận.

## Kiểm tra và tiêu chí hoàn thành

- Test stream: delta bị chia, lỗi trước/sau text, incomplete, disconnect, hủy và yêu cầu không nhận completed.
- Test đổi notebook/model/nguồn trong lúc đang tạo không lẫn kết quả; kết nối bị xóa phải thất bại an toàn.
- Kiểm tra model được chọn thực sự tới provider trong cả Chat, reading và các nhánh Studio nhiều bước.
- Reload mở được metadata mới và notebook cũ; xóa từng artifact/cancel xóa vẫn đúng, kết quả đang tạo không bị thao tác xóa một artifact khác làm mất.
- Kiểm tra theme sáng/tối và màn hình 360/768/1280/1920px; không tràn ngang hoặc che nút thao tác. Font và bố cục hiện tại được giữ.
- Backend tests, frontend build/lint; smoke test thật một Chat và một tác vụ Studio nhỏ khi có kết nối được người dùng cho phép. Ghi riêng phạm vi test mock/thật.

## Cách làm việc và báo cáo

Triển khai trực tiếp và cập nhật bàn giao. Ghi contract stream, chính sách hủy/lưu dở dang và schema metadata để phase sau tái sử dụng. Dừng ở Phase 03.

## Bàn giao sau triển khai

- Trạng thái: **Hoàn thành Phase 03**, ngày 18/11/2026. Không triển khai định dạng nguồn mới, multi-turn RAG nâng cao hoặc Knowledge Graph.

### Kết quả thực tế

- Có lựa chọn **Dịch vụ / Kết nối / Model** ở đầu bảng Trò chuyện, dùng chung cho Chat, reading chat và mọi công cụ AI trong Studio.
- Giữ provider API máy chủ đang có, đồng thời cho chọn gói ChatGPT đã kết nối. Không tự thay model, tài khoản hoặc đường tính phí khi lựa chọn cũ mất quyền.
- Chat hiển thị text tăng dần, có **Dừng**. Studio có **Dừng tạo** theo từng công cụ; không hiển thị raw JSON đang sinh.
- Chỉ chấp nhận/lưu kết quả sau terminal event hoàn tất, kiểm tra schema và tham chiếu nguồn. Bản nháp/lỗi/hủy không được ghi vào chat hoặc artifact.
- Kết quả mới có metadata model/thời gian/usage; kết quả cũ vẫn mở, xuất và xóa được. Không sửa bố cục chính, palette hoặc font đã chốt.

### Contract lựa chọn model và snapshot

- `backend/schemas/tasks.py` định nghĩa `ModelChoice` và request union cho `chat`, `reading`, `summary`, `quiz`, `flashcards`, `mindmap`.
- Mỗi request có `id` UUID do frontend tạo, `notebook_id`, lựa chọn `{provider, model, connection_id}`, và `input` được kiểm tra bằng schema cũ tương ứng.
- Reading có thêm `sources` để giữ nguyên snapshot filename/page. Backend kiểm tra phạm vi trong notebook, PDF đang mở và truyền snapshot vào reading service; không lấy lại lựa chọn trực tiếp từ UI trong lúc model đang chạy.
- Frontend chụp model, nguồn và notebook trước `await`; chờ flush workspace trước khi gửi tác vụ. Thay control chỉ ảnh hưởng tác vụ sau.
- Preference ở browser key `yournote.model.preference.v1`, chỉ chứa provider/model/ID tham chiếu đăng ký. Không chứa API key, OAuth token hoặc ID token.
- Khi chưa có preference, hành vi API máy chủ cũ được giữ. Khi preference có nhưng sai/không còn khả dụng, UI yêu cầu chọn lại; không tự quay về API máy chủ hoặc một model khác.
- Backend tải catalog mới của đúng kết nối trước tác vụ ChatGPT; chỉ cho model được cấp quyền. Provider API máy chủ chỉ chấp nhận model được cấu hình trên server, không nhận model tùy ý từ client.
- `ChatGPTConnections.bind_task()` giữ riêng epoch của đăng ký và resolver credential; đổi tài khoản active trong Cài đặt không đổi tác vụ đã bắt đầu. Logout/reauthorize làm tác vụ cũ không thể hoàn tất bằng credential mới.

### Endpoint và event stream

Các route mới vẫn dưới `/api/ai`, dùng cookie/CSRF/loopback/Host/Origin của Phase 02:

| Method | Route | Chức năng |
| --- | --- | --- |
| GET | `/api/ai/options` | Cho biết model API máy chủ và trạng thái sẵn sàng, không trả khóa |
| POST | `/api/ai/tasks` | Bắt đầu tác vụ và nhận `text/event-stream` |
| POST | `/api/ai/tasks/{id}/cancel` | Hủy tác vụ thuộc browser session; có thể chặn request chưa kịp bắt đầu |

Stream dùng frame `data: <JSON>\n\n` với các event:

| `type` | Nội dung |
| --- | --- |
| `started` | `task_id`, `notebook_id`, `feature` |
| `progress` | `stage`, số lời gọi đã có kết quả; không phải phần trăm quota |
| `delta` | `text`, chỉ cho Chat/reading |
| `completed` | `result` đầy đủ gồm citation và `generation` |
| `error` | mã lỗi, status, thông báo an toàn; không có provider body |
| `cancelled` | trạng thái dừng, không có kết quả để lưu |

- Heartbeat là comment SSE, không phải sự kiện hoàn tất.
- EOF, HTTP 200, text đầu tiên và `[DONE]` đều không tự chứng minh thành công. Thiếu completed hoặc stream bị cắt thì không lưu.
- Frontend dùng TextDecoder streaming, ghép frame qua nhiều network chunk, xử lý CRLF/UTF-8 và kiểm tra task/notebook ID trước khi nhận kết quả.
- API Chat/Studio cũ vẫn giữ để tương thích, không bổ sung chọn model qua các route cũ. UI hiện dùng task API mới.

### Hủy, autosave và giới hạn

- Chọn chính sách **không lưu bản nháp**. Các trường pending chỉ nằm trong state tạm, không nằm trong `WorkspaceSnapshot`.
- AbortController đóng request browser; cancel endpoint gửi UUID đã biết từ trước, kể cả khi POST tạo tác vụ chưa được xử lý. Backend giữ dấu hủy ngắn hạn để ngăn request đến trễ khởi động model.
- Ngắt kết nối SSE cũng hủy tác vụ. Job chỉ có quyền đọc notebook và trả event, không tự ghi notebook hoặc artifact.
- Mỗi operation có handle riêng trong ref. Sau hủy/unmount/đổi notebook, callback cũ không được commit state hay xóa trạng thái của tác vụ mới.
- Nút về trang chủ/sổ mới dừng tác vụ AI rồi flush workspace. Upload chưa xong vẫn được bảo vệ như trước. Xóa artifact dùng cập nhật state theo hàm, nên không làm sống lại kết quả vừa xóa khi một generation khác hoàn tất.
- CancellationToken hỗ trợ callback đóng transport. ChatGPT đóng HTTP response/client; Gemini đóng SDK client. Hủy khi đang chờ I/O là best effort, không cam kết hoàn lại usage hay ngắt tức thì trong mọi transport.
- Registry có 4 worker thread, tối đa 8 future đang hoạt động/chờ; future chưa bắt đầu có thể bị hủy. Giới hạn vẫn tính công việc chưa giải phóng dù client đã ngắt kết nối.
- Mặc định `RAG_TASK_MAX_CALLS=64`, `RAG_TASK_TIMEOUT_SECONDS=600`. Summary/Mind Map ước lượng số bước trước map/reduce và từ chối nếu vượt ngân sách; không âm thầm cắt bớt nguồn.
- Giữ retry cũ có giới hạn cho Gemini generate thông thường. Chat streaming không retry để tránh nhân đôi text; ChatGPT không tự retry inference/quota/auth hoặc chuyển billing.
- Lỗi sau khi đã có delta chỉ kết thúc bằng error/cancelled; không có artifact hoàn tất hoặc chat turn từ phần text đó.

### Schema metadata và tương thích

`backend/schemas/generation.py` định nghĩa `GenerationMetadata`, gắn vào `ChatResponse` và `LearningResponse` bằng field `generation` tùy chọn:

- `provider`, `requested_model`, `model` thực tế nếu biết, `actual_models` được provider báo.
- `created_at` ISO UTC, `status="completed"`, `request_id`, `notebook_id`.
- `source_filenames`, `pages`, `calls`, `duration_seconds`.
- `usage` với input/output/total token nếu provider trả. Khi gộp nhiều lời gọi, một field chỉ được cộng nếu tất cả lời gọi có số liệu cho field đó; không suy ra phần thiếu.

`calls` là số invocation có kết quả qua abstraction, không khẳng định bằng mọi HTTP attempt hoặc toàn bộ billing. Không có số liệu chi phí/quota suy đoán.

Metadata nằm trong kết quả đã lưu của chat/artifact, không thêm cột SQLite hay yêu cầu migration phá hủy. Field vắng mặt được bỏ khỏi JSON bằng Pydantic `exclude_if`; backend yêu cầu Pydantic 2.12 trở lên (môi trường kiểm tra dùng 2.12.5). Dữ liệu cũ không bị tự gắn metadata giả.

Kiểm tra citation tại phase này là cấu trúc/marker/phạm vi nguồn và quy tắc grounding hiện có. Không coi việc marker tồn tại là bằng chứng mọi kết luận đã đúng ngữ nghĩa; đánh giá sâu chất lượng truy xuất/bằng chứng thuộc Phase 04.

### Thay đổi chính trong code

- `src/providers/contracts.py`, `src/llm.py`: callback hủy transport, result/delta observer, ngân sách theo tác vụ, kế thừa ContextVar và cleanup.
- `src/providers/chatgpt.py`: stream thật với terminal validation; `generate()` thu stream cho Studio. Không gửi các tham số không hỗ trợ của provider cũ.
- `src/providers/gemini.py`: native text streaming, kiểm tra finish reason, metadata và đóng client khi hủy.
- `src/locks.py` (mới), `src/rag.py`, `backend/services/core_adapter.py`, `backend/services/reading.py`: khóa dùng chung chỉ bao index/chuẩn bị dữ liệu; không giữ xuyên suốt lời gọi model.
- `src/learning.py`, `src/mindmap.py`: preflight số bước và kiểm tra hủy qua abstraction cho mọi nhánh map/reduce.
- `backend/services/generation.py`, `backend/api/routes/tasks.py`, `backend/schemas/tasks.py` (mới): task registry, snapshot, SSE, cancel và validate trước completion.
- `backend/schemas/generation.py`, `backend/schemas/api_base.py` (mới), `backend/schemas/api.py`: metadata có tương thích; tách base model để tránh import vòng.
- `backend/services/chatgpt_auth.py`: bind credential theo đăng ký/epoch và đăng ký cancellation token của tác vụ.
- `frontend/src/features/ai/useModelChoice.ts`, `ModelPicker.tsx`, `models.css`, `tasks.ts`, `sse.ts` (mới): preference, model picker, stream parser và task client.
- `frontend/src/useNotebook.ts`, `features/notebooks/NotebookWorkspace.tsx`: snapshot/flush, cô lập operation, dừng khi rời notebook và chỉ commit completed.
- `frontend/src/features/chat/`, `features/studio/StudioPanel.tsx`, `components/GenerationInfo.tsx`, `components/ResultCard.tsx`, `types/api.ts`: hiển thị streaming/stop, metadata mới và giữ result cũ.
- `backend/tests/test_generation_tasks.py`, `test_provider_streaming.py` (mới): kiểm tra workflow và native stream. Các test cũ tiếp tục đạt.

### Kiểm tra tự động và giao diện

- Baseline: **92/92 backend test đạt**.
- Cuối phase: **107/107 backend test đạt**, không gọi AI trả phí. Gồm thiếu completion, lỗi sau delta, cancel trước start, disconnect, source/model snapshot, hết quyền sau delta, đọc PDF, map/reduce, giới hạn lời gọi, khóa index được giải phóng và metadata reload.
- Frontend build đạt, lint 0 lỗi và 12 cảnh báo đã có từ trước phase. Python compile và `git diff --check` đạt.
- Parser SSE: tiếng Việt/UTF-8 và CRLF tại 5 kích thước network chunk, sự kiện bị cắt và abort đều được kiểm tra.
- Chrome headless dùng API/notebook/PDF giả: phản hồi tăng dần; đổi model/nguồn giữa chừng; quota/incomplete/cancel không lưu draft; cancel khi còn chờ autosave không khởi động inference; xóa Studio trong lúc tạo; dừng riêng Studio; rời notebook; reading chat; reload preference và model mất quyền không fallback.
- Giao diện: **16 tổ hợp** 360/768/1280/1920px × light/dark × API/ChatGPT, giữ bố cục/font và không tràn ngang.
- Script hỗ trợ ở `/tmp/phase03-ui.mjs` và `/tmp/test-phase03-parser.mjs`; không dùng profile trình duyệt hoặc dữ liệu notebook thật để chạy QA.

Lệnh kiểm tra từ `project/`:

```bash
.venv/bin/python -m unittest discover -s backend/tests -q
.venv/bin/python -m compileall -q backend src app.py
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run lint
git diff --check
```

### Smoke test thật và phạm vi đã xác minh

Dùng đúng kết nối và model `gpt-6.1-terra` người dùng đã cấp quyền; chỉ gửi **1 Chat + 1 Summary**, trên PDF giáo dục mới tạo và DB/index/notebook trong `/tmp`. Ingestion PDF, embedding cục bộ, retrieval, provider, SSE, lưu và đọc lại metadata đều chạy thật. Không đưa corpus hoặc notebook riêng của người dùng vào phép thử.

| Tác vụ | Thời gian hoàn tất (Asia/Ho_Chi_Minh) | Thời lượng | Usage provider báo | Kết quả |
| --- | --- | --- | --- | --- |
| Chat | 19:24:52, 18/11/2026 | ~4,30 giây | 250 input / 26 output / 276 total | 22 delta, completed, 2 citation, metadata reload đúng |
| Summary | 19:24:58, 18/11/2026 | ~6,44 giây | 230 input / 147 output / 377 total | JSON hợp lệ, không stream raw JSON, 2 citation, metadata reload đúng |

Model thực tế cả hai lần là `gpt-6.1-terra`; mỗi tác vụ có 1 invocation. Proof đã lược bỏ danh tính/credential ở `/tmp/phase03-real-proof.json`. Backend được khởi động lại với code Phase 03, health/options qua proxy trả 200 và phiên keyring đã khôi phục được. Không cần người dùng đăng nhập lại cho lần triển khai này.

Quiz/Flashcards/Mind Map và Gemini được kiểm tra bằng mock, bao gồm các nhánh nhiều bước; chưa gọi thật các đường đó để tránh dùng thêm quota ngoài hai smoke test đã yêu cầu.

### Điều Phase 04 cần biết

1. Giữ task transport, completion gate, ContextVar và metadata khi cải thiện RAG. Các hàm core tiếp tục dùng `invoke_llm`; không gọi SDK trực tiếp hoặc làm mất observer/cancellation.
2. Metadata/citation hiện còn theo filename/page của PDF. Khi thêm định dạng/identity/locator mới, cập nhật đồng thời task schemas, snapshot, validator, reader/export và tương thích workspace cũ.
3. `reading.chat(..., filenames_snapshot=...)` nhận scope đã chụp; không bỏ tham số này rồi đọc lại nguồn hiện hành giữa tác vụ.
4. `src.locks.core_lock` là khóa index dùng chung; không đưa network generation trở lại bên trong khóa. Giữ một worker cho embedded Qdrant.
5. Lịch sử chỉ có completed turn. Multi-turn retrieval chưa được thêm ở phase này; Phase 04 phải giữ nguyên quy tắc loại bản nháp/lỗi khỏi context đáng tin cậy.
6. Nguồn/model thay đổi giữa tác vụ vẫn phải giữ metadata lịch sử cũ. Không chuyển preference hiện tại thành model đã tạo kết quả cũ.
7. Streaming và worker task là runtime trong RAM. Không bổ sung resume tác vụ sau restart, background cloud hoặc đồng bộ nhiều người ở Phase 03.


### Tinh chỉnh bộ chọn model sau Phase 03 — 18/11/2026

Đã thực hiện theo yêu cầu giao diện bổ sung, chưa bắt đầu Phase 04:

- Đưa nút model vào thanh dưới ô nhập; menu nổi theo mẫu, tìm kiếm model khi danh sách dài, chọn model/mức suy luận, reset về mặc định. Menu đóng bằng Escape/click ra ngoài, trả focus khi cần và giữ được bố cục trên mobile. Giữ tông màu/font đã chốt, căn menu theo ô nhập và tránh để toast che thao tác.
- Chuyển lựa chọn dịch vụ/kết nối về Cài đặt. Trong sổ chỉ còn bộ chọn model và nút mở nhanh Cài đặt; thêm thẻ **Hạn mức sử dụng** trong Cài đặt, mở `https://chatgpt.com/settings/usage`. Chưa đồng bộ quota trực tiếp; không hiển thị số hay phần trăm suy đoán.
- `modelPreference.ts` dùng preference/event cùng nguồn để cập nhật lựa chọn giữa Settings và notebook; chỉ lưu provider/model/ID kết nối/mức suy luận, không lưu credential. Catalog được gắn theo kết nối để tránh hiển thị nhầm danh sách khi đổi tài khoản. Kết nối hết quyền không tiếp tục hiện catalog cũ.
- Catalog công khai bổ sung `supported_reasoning_levels` (danh sách giá trị được hỗ trợ) và `default_reasoning_level` (có thể null), chỉ lấy từ metadata provider. Không suy ra capability từ tên model.
- Request `model.reasoning_effort` và `generation.reasoning_effort` là optional/null, tương thích payload/notebook cũ. Backend xác minh lại mức hỗ trợ trước khi gọi AI; `GenerationParameters`/capability kiểm tra tham số này, adapter chuyển thành Responses `reasoning: {effort: ...}`. Nếu null, bỏ tham số để dùng mặc định provider. Task snapshot giữ mức đã chọn cho cả nhánh Studio map/reduce; không dùng lựa chọn UI mới thay tác vụ đang chạy.

Tệp chính: `frontend/src/features/ai/{ModelPicker.tsx,models.css,modelPreference.ts,useModelChoice.ts,AIConnections.tsx,connections.css,client.ts}`, ChatPanel/NotebookWorkspace, GenerationInfo/types, `frontend/README.md`; backend schemas AI/task/generation, services chatgpt_auth/generation, provider contracts/chatgpt và ba module test tương ứng.

Kiểm chứng thực tế:

- **110 backend tests đạt** (MockTransport, không inference trả phí), gồm kiểm tra capability catalog, truyền effort lên Responses, Chat và Summary map/reduce giữ effort, từ chối mức không được cấp quyền trước khi gọi provider.
- Frontend build đạt; lint exit 0 với **12 warning có sẵn**. Compileall và `git diff --check` đạt.
- Chrome QA bằng API/notebook giả ở `/tmp/model-picker-ui.mjs`: chọn/tìm model, thanh suy luận có/không capability, reset, snapshot, Studio, preference reload, model bị thu hồi, mở Cài đặt và đồng bộ provider; **8 tổ hợp 360/768/1280/1920px × dark/light**, kiểm tra cả menu model, menu effort và thẻ quota. Ảnh ở `/tmp/model-picker-ui/`. Đã xem ảnh để rà bố cục. Không có lỗi JS hoặc yêu cầu inference tự phát.
- Backend đang chạy đã cập nhật, health 200. Tải catalog thật của kết nối đã được cấp quyền: **10 model**, cả 10 có metadata mức suy luận. Không gửi thêm inference thật ở lần chỉnh UI này; forwarding của tham số mới được xác minh bằng mock, chưa smoke test trả phí cho từng mức.

Tham khảo capability: [OpenAI Codex ModelInfo](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/openai_models.rs), [Responses reasoning](https://developers.openai.com/api/docs/guides/reasoning). Phase 04 cần giữ các trường optional và quy tắc validate/snapshot này khi thay luồng RAG. Không tự commit.
