# Phase 01 — Tách lớp model, giữ nguyên hành vi hiện tại

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md` và áp dụng các quy tắc chung. Chỉ triển khai Phase 01, chưa bắt đầu phase khác.

## Mục tiêu

Tạo nền tảng để Chat, đọc tài liệu và Studio sử dụng các provider/model khác nhau mà không phụ thuộc SDK cụ thể. Kết thúc phase, ứng dụng hiện tại vẫn hoạt động với cấu hình cũ; chưa cần người dùng đăng nhập ChatGPT.

## Khảo sát trước khi sửa

- Kiểm tra `git status` và cách chạy ứng dụng thực tế.
- Đọc `src/llm.py`, `src/config.py`, `src/errors.py`, `src/rag.py`, `src/learning.py`, `src/mindmap.py` và các nơi gọi `invoke_llm`.
- Đọc `backend/services/core_adapter.py`, dịch vụ reading, các route/schemas, luồng frontend gọi API.
- Xác định cách khóa Qdrant, request vào threadpool, retry và parse đầu ra có cấu trúc đang hoạt động.
- Chạy kiểm tra nền tảng để biết lỗi có sẵn. Không ghi lại credential hoặc nội dung tài liệu cá nhân.

## Công việc bắt buộc

1. Định nghĩa hợp đồng provider nhỏ, dùng được cho model gọi từ API key hoặc phiên OAuth sau này. Có loại dữ liệu cho lựa chọn model, request, kết quả và lỗi; tránh tạo framework plugin lớn.
2. Chuyển logic provider hiện tại sang adapter riêng, giữ timeout/retry và hành vi lỗi hợp lý. Giữ `invoke_llm(prompt)` hoặc cầu nối tương thích để các chức năng hiện có không bị vỡ trong quá trình chuyển đổi.
3. Kết quả có thể mang thông tin `provider`, model thực tế, thời lượng và usage do provider trả về. Trường chưa biết phải để trống; không suy ra số usage hay tiền từ con số không có căn cứ.
4. Định nghĩa ngữ cảnh thực thi bất biến theo tác vụ: provider, model, tham chiếu credential, request ID. Không để credential nằm trong object public, state notebook hoặc artifact.
5. Truyền ngữ cảnh rõ ràng qua các lớp. Nếu dùng ContextVar làm cầu nối, phải có set/reset bằng token trong `finally`, kiểm tra lan truyền qua threadpool và không để tác vụ sau nhận ngữ cảnh cũ.
6. Đặt nền tảng capability: hỗ trợ streaming, structured output, loại đầu vào và tham số hợp lệ. Không mặc định provider nào cũng nhận temperature, max token hoặc JSON schema theo cùng cách.
7. Chuẩn hóa lỗi tối thiểu: chưa cấu hình, cần kết nối lại, model không được cấp quyền, hết hạn mức, giới hạn tần suất, timeout, lỗi tạm thời, phản hồi không hợp lệ. Giữ HTTP contract cũ tương thích khi chưa cần mở rộng.
8. Chuẩn bị một hợp đồng stream/cancel cho Phase 03 ở mức cần thiết; chưa bắt buộc triển khai SSE hay UI streaming tại phase này.
9. Cấu hình mặc định cũ tiếp tục chạy. Provider/model không hợp lệ phải bị từ chối rõ ràng; không âm thầm fallback.
10. Đảm bảo health/OpenAPI vẫn không phải tải model embedding hoặc khởi tạo toàn bộ RAG không cần thiết.

## Ngoài phạm vi

- OAuth, đăng nhập thật, gọi ChatGPT bằng gói thuê bao.
- Thêm model picker, thay đổi bố cục hoặc đổi theme.
- Đổi embedding model, vector database, schema tài liệu hoặc di chuyển dữ liệu hiện có.
- Triển khai tất cả provider dự kiến trong tương lai.

## Kiểm tra và tiêu chí hoàn thành

- Các đường gọi Chat, reading chat, Summary, Quiz, Flashcards và Mind Map đi qua cùng hợp đồng provider, không bỏ sót nhánh map/reduce.
- Test adapter hiện tại bằng mock, kiểm tra lỗi/retry phù hợp; không gọi dịch vụ trả phí trong unit test.
- Test hai ngữ cảnh model/credential xen kẽ không lẫn nhau; request lỗi phải được dọn ngữ cảnh.
- Kiểm tra không lộ secret qua HTTP error, log, model dump hoặc export.
- Chạy bộ backend test hiện có, frontend build và lint nếu có chạm frontend. Các chức năng đang có và dữ liệu cũ tiếp tục đọc được.
- Bàn giao chỉ rõ cách Phase 02 thêm provider mới và cách Phase 03 chọn model theo request.

## Cách làm việc và báo cáo

Triển khai trực tiếp, không dừng ở bản thiết kế. Giữ refactor có phạm vi, giải thích lựa chọn lớn và không tự commit. Cập nhật phần bàn giao bên dưới bằng kết quả thật, rồi dừng ở ranh giới Phase 01.

## Bàn giao sau triển khai

- Trạng thái: **Hoàn thành Phase 01**, ngày 18/11/2026. Chỉ kiểm tra bằng provider giả/SDK mock, không gọi AI trả phí, chưa triển khai OAuth hay giao diện chọn model.

### Tệp/module đã thay đổi

- `project/src/providers/contracts.py` (mới): kiểu dữ liệu bất biến, hợp đồng provider/capability/credential resolver, nền tảng stream và hủy.
- `project/src/providers/gemini.py` (mới): adapter chứa toàn bộ logic SDK hiện tại, timeout, retry và chuyển lỗi.
- `project/src/providers/__init__.py` (mới): package provider, không tự import SDK.
- `project/src/llm.py`: điều phối provider, scope tác vụ và cầu nối `invoke_llm(prompt) -> str`; thêm `generate_llm(LLMRequest) -> LLMResult` cho metadata nội bộ.
- `project/src/errors.py`: thêm mã lỗi độc lập nhà cung cấp; constructor `LLMServiceError(status_code, detail)` cũ tiếp tục dùng được.
- `project/src/config.py`: kiểm tra cú pháp model; khóa cấu hình không xuất hiện trong repr/model dump. Tên biến môi trường và cấu hình mặc định hiện tại được giữ.
- `project/src/rag.py`, `learning.py`, `mindmap.py`: đánh dấu điểm bắt đầu tác vụ bằng `@llm_operation`, bao gồm đường Chat/reading và mọi nhánh map/reduce.
- `project/app.py`: bốn callback Gradio dùng `with gemini_api_key_scope(...)`, thay setter không có cleanup. Không đổi giao diện Gradio.
- `project/backend/main.py`: lỗi ngoài dự kiến chỉ log loại lỗi và vị trí stack, không log message/exception chain chứa token hoặc nội dung nguồn.
- `project/backend/tests/test_llm.py`: cập nhật điểm mock sang adapter, kiểm tra metadata, retry, lỗi và hủy.
- `project/backend/tests/test_provider_context.py` (mới): kiểm tra cô lập ngữ cảnh, threadpool, capability, toàn bộ workflow và lazy startup.
- `project/backend/tests/test_api.py`: dùng Qdrant fixture tạm thay index người dùng; kiểm tra HTTP/log không lộ khóa runtime.

Không sửa frontend trong phase này; không thay schema notebook/artifact/citation, vector/embedding, dữ liệu hay cơ chế khóa Qdrant.

### Hợp đồng provider và điểm tích hợp

- `ModelSelection(provider, model)`: lựa chọn model; kiểm tra cú pháp, không chứa SDK.
- `CredentialRef(id)`: ID tham chiếu kết nối phía backend; tuyệt đối không đặt token/API key vào trường này. Mặc định hiện tại là `environment:gemini`.
- `ExecutionContext(selection, credential_ref, request_id, parameters)`: snapshot bất biến cho toàn tác vụ; không chứa secret.
- `LLMRequest(prompt, parameters)`: yêu cầu text. `GenerationParameters` hiện có temperature và max output tokens, đều có thể bỏ trống.
- `LLMResult(text, provider, model, duration_seconds, usage)`: model thực tế lấy từ phản hồi provider; không có thì `None`. Usage chỉ giữ các count được trả về, không tính bù trường thiếu hay suy ra chi phí/hạn mức còn lại.
- `LLMProvider.generate(...)`: nhận request/context và credential kiểu `SecretStr` qua tham số riêng phía backend. Provider không nhận credential từ payload HTTP public.
- `invoke_llm` tiếp tục trả chuỗi, nên Chat/Studio và export/schema hiện có giữ tương thích. Metadata mới chỉ có ở API nội bộ `generate_llm`, chưa lưu vào artifact.
- `get_provider(name)` là điểm dispatch nhỏ, hiện chỉ có Gemini và import adapter khi cần. Provider không hỗ trợ bị từ chối; không có fallback ngầm.

### Quy tắc ngữ cảnh, capability và lỗi

- `llm_task(context, credential_resolver=..., cancellation=...)` cài ngữ cảnh bằng ContextVar và reset token trong `finally`. Scope con không truyền override sẽ dùng nguyên scope đang có.
- Các hàm core dùng `@llm_operation` để tự tạo snapshot khi chạy độc lập; nếu backend đã mở `llm_task` thì kế thừa, không tạo request ID mới cho từng batch.
- Credential thật nằm trong resolver riêng. Credential môi trường được chụp khi mở scope; kết nối chỉ định mà không resolve được không được fallback sang khóa môi trường.
- Đã kiểm tra hai async task xen kẽ qua `starlette.concurrency.run_in_threadpool` nhận đúng context/model/credential riêng, và scope khôi phục cả sau lỗi.
- `ProviderCapabilities` phân biệt streaming, native structured output, input types và tham số hỗ trợ. Adapter hiện chỉ triển khai text + temperature/max output tokens; streaming/native schema chưa được bật. JSON trong prompt cũ không được gọi là native structured output.
- Các nhóm lỗi có mã riêng: chưa cấu hình, cần kết nối lại, model không khả dụng, quota, rate limit, timeout, tạm thời không khả dụng, phản hồi/yêu cầu không hợp lệ, capability/provider không hỗ trợ và hủy.
- HTTP hiện vẫn trả `{ "detail": "..." }`; các status/message lỗi đang được frontend ánh xạ tiếp tục giữ nguyên. Mã lỗi mới là thông tin nội bộ, chưa thêm field public.
- Bare HTTP 429 trong adapter hiện tại được ghi là `rate_limited`, không tự suy ra hết quota. Có mã `quota_exceeded` để adapter tương lai dùng khi có bằng chứng có cấu trúc.
- Timeout SDK giữ 60 giây mỗi lần; tối đa 3 lần gọi với backoff 1/2 giây. Không retry auth/model/quota/rate limit hoặc lỗi request vĩnh viễn. Backoff dùng Event.wait để hủy được giữa các lần.
- Có `CancellationToken`, `TextDelta`, `Completion`, `StreamingProvider` cho Phase 03. Hiện chỉ hủy trước/sau lời gọi đồng bộ và trong backoff; chưa ngắt được một lời gọi SDK đang chờ mạng, chưa có SSE/UI hủy.

### Lệnh kiểm tra và kết quả

Chạy từ `project/`:

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python -m compileall -q src backend app.py
git diff --check
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run lint
```

- Backend: **68/68 test đạt**, gồm hồi quy notebook/reading/Studio/export, snapshot map/reduce, context cleanup, threadpool, metadata và lỗi an toàn. Không gọi provider thật.
- Compile Python và kiểm tra whitespace: đạt.
- Frontend build: đạt. Lint: 0 lỗi, 12 cảnh báo có sẵn từ trước phase.
- Startup test trong Python process mới chặn import SDK/model/RAG nặng: health và OpenAPI vẫn chạy được, không tải embedding hoặc mở index.
- API test dùng Qdrant collection và DB/path tạm, không mở index hay notebook thật. Các test workflow dùng chunk giả, không dùng corpus riêng tư.

### Vấn đề có sẵn hoặc giới hạn còn lại

- Lần chạy baseline đầu tiên phát hiện 47 test nhưng kẹt ở `TestClient.__enter__` trong sandbox. Đã tái hiện với FastAPI tối thiểu không liên quan code project; cùng kiểm tra ngoài sandbox trả 200. Bộ 68 test cuối được chạy ngoài sandbox và đạt. Nếu môi trường tương tự bị kẹt, cần chạy bằng runner có quyền phù hợp; không sửa event loop của ứng dụng để né sandbox.
- Có cảnh báo deprecation từ `langchain-community` hiện có; chưa đổi dependency vì ngoài phạm vi phase.
- Model ID chỉ được kiểm tra cú pháp cục bộ; model hợp cú pháp nhưng không tồn tại sẽ bị provider từ chối và không fallback. Catalog theo tài khoản thuộc Phase 02.
- Chưa thử inference thật hoặc xác nhận model/API key của người dùng đang có hạn mức. Đây không phải tiêu chí bắt buộc của refactor Phase 01.
- Không migration dữ liệu, không thêm metadata vào HTTP/workspace, không thay Qdrant lock/một worker. Chưa tối ưu khóa cho streaming mạng; Phase 03 cần xử lý khi thêm stream.

### Điều Phase 02 và Phase 03 cần biết

1. Thêm adapter mới trong `src/providers/`, thực hiện `LLMProvider`, khai báo đúng capability và chuyển lỗi sang `LLMServiceError` có message an toàn.
2. Mở rộng `get_provider` và `Settings.llm_provider` khi provider mới thực sự được triển khai. Không đặt registry/config global biến đổi theo request, không thay provider mặc định chỉ vì kết nối mới đã được thêm.
3. Backend xác minh kết nối/model, tạo `ExecutionContext` với `CredentialRef(connection_id)` và resolver lấy/refresh credential trong runtime được bảo vệ. Frontend không nhận resolver hoặc token.
4. Model mới không nhận các tham số cũ thì tạo `GenerationParameters()` với trường không hỗ trợ để trống; đừng tái sử dụng nguyên cấu hình generation của Gemini.
5. Bọc lời gọi service hiện có bằng `llm_task` để tất cả nhánh con nhận đúng model. Ví dụ tích hợp phía backend, sau khi đã xác minh quyền:

```python
execution = ExecutionContext(
    selection=ModelSelection(provider=verified_provider, model=verified_model),
    credential_ref=CredentialRef(connection_id),
    parameters=GenerationParameters(),
)
with llm_task(execution, credential_resolver=resolve_server_credential, cancellation=cancel):
    result = core_adapter.chat(request)
```

6. Phase 02 có thể dùng `generate_llm(LLMRequest(...))` trong scope để lấy metadata cho kiểm tra kết nối. Với provider bắt buộc stream upstream, adapter có thể thu stream thành `LLMResult` hoàn tất; chỉ trả thành công sau sự kiện terminal hợp lệ.
7. Phase 03 triển khai `StreamingProvider.stream` và transport stream riêng, giữ quy tắc delta không phải completion. Khi tạo task/thread mới, phải kiểm tra cách truyền context và vòng đời credential/cancellation; `run_in_threadpool` hiện tại đã có test.
8. Không gọi lại setter `set_runtime_gemini_api_key` cũ: đã thay toàn bộ nơi dùng trong repo bằng `gemini_api_key_scope` có cleanup. Thiết lập theo request mới nên dùng `llm_task` chung.
