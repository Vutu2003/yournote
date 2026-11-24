# Phase 02 — Kết nối ChatGPT và chứng minh dùng được hạn mức gói

Hãy triển khai phase này trong workspace `/home/vutu/Desktop/rag_notebooklm`, mã ứng dụng ở `project/`. Đọc `plan/00_README.md`, Phase 01 và phần bàn giao của nó. Chỉ triển khai Phase 02.

## Mục tiêu

Người dùng chủ động kết nối tài khoản ChatGPT qua cơ chế chính thức, cấp quyền dùng gói, xem các model được phép và hoàn thành một yêu cầu inference ngắn. Đây là mốc xác minh kỹ thuật; chưa tích hợp toàn bộ Chat/Studio.

## Điều kiện đầu vào và xác minh bắt buộc

- Hợp đồng provider Phase 01 đã có và dùng được. Nếu chưa đạt, báo đúng phần thiếu thay vì tạo lớp tích hợp thứ hai song song.
- Đọc tài liệu chính thức hiện hành được liên kết trong `00_README.md`; ghi ngày kiểm tra, SDK/phiên bản và điểm khác với kế hoạch nếu có.
- Xác định ứng dụng đang chạy cục bộ có phù hợp điều kiện truy cập hay không. Không dùng cookie trình duyệt, endpoint nội bộ, proxy không chính thức hoặc credential của một ứng dụng khác.
- Quyền đăng nhập danh tính chưa đủ để inference: cần xác minh quyền sử dụng gói thực sự được cấp.

## Công việc bắt buộc

1. Chọn cách tích hợp phù hợp React + FastAPI hiện có. Có thể dùng SDK/runtime chính thức nếu phù hợp hoặc triển khai theo tài liệu; không thêm Electron/Node sidecar chỉ để bám theo ví dụ khi chưa cần.
2. Backend cục bộ điều khiển luồng đăng nhập qua trình duyệt hệ thống, callback loopback và PKCE/state/nonce theo đặc tả hiện hành. Xác minh danh tính theo hướng dẫn; callback giả, hết hạn, dùng lại hoặc sai state phải bị từ chối.
3. Giữ định danh bản cài đặt và registration do dịch vụ cấp theo tài liệu. Reconnect không được tạo đăng ký mới vô hạn.
4. Lưu credential bằng OS keyring hoặc cơ chế được bảo vệ tương đương; nếu môi trường không hỗ trợ thì dùng phiên chỉ trong RAM với thông báo rõ. Không tự fallback sang lưu token dạng rõ trong file. Làm mới token có kiểm soát, tránh nhiều refresh đồng thời.
5. Thêm khu vực **Kết nối AI** trong Cài đặt theo giao diện hiện tại. Hiển thị trạng thái chưa kết nối/đang chờ/đã kết nối/cần kết nối lại/chưa cấp quyền dùng gói. Thông tin frontend chỉ gồm dữ liệu hiển thị an toàn và ID tham chiếu.
6. Cung cấp catalog model theo tài khoản/phiên hiện tại; lọc đúng model được phép hiển thị theo tài liệu. Lưu `display_name` cho UI và định danh model thực tế để gửi yêu cầu. Làm mới catalog khi đổi kết nối.
7. Tạo provider ChatGPT plan usage qua hợp đồng Phase 01 và một hành động **Kiểm tra kết nối** do người dùng bấm. Thông báo trước đây là một yêu cầu AI ngắn có dùng hạn mức; không tự gọi lặp khi mở trang.
8. Gửi inference qua public endpoint được hỗ trợ. Theo tài liệu đã tham khảo: `POST https://api.openai.com/v1/responses`, OAuth bearer, `store: false`, `stream: true`; kiểm chứng lại trước khi code. Chỉ đánh dấu thành công khi nhận terminal event hoàn tất, không chỉ dựa vào HTTP 200 hoặc text đầu tiên.
9. Phân biệt đăng nhập thành công, catalog thành công và inference thành công. Xử lý tài khoản chưa đủ quyền, model không còn khả dụng, quota, timeout và lỗi giữa stream bằng thông báo an toàn.
10. Có logout/xóa credential cục bộ; mô tả rõ khác biệt với thu hồi quyền phía ChatGPT và cung cấp lối quản lý quyền/usage chính thức. Không tuyên bố local logout đã thu hồi quyền nếu chưa có bằng chứng.
11. Bảo vệ endpoint cục bộ theo cơ chế phiên và kiểm tra origin/host phù hợp; không dựa riêng vào CORS để bảo vệ hành động kết nối hay gọi AI. Không bind dịch vụ credential ra mạng công cộng.

## Ngoài phạm vi

- Model picker trong Chat, chat streaming đầy đủ, tích hợp mọi công cụ Studio.
- Đọc lịch sử/hội thoại/memory từ ChatGPT; quyền dùng gói không tự cấp dữ liệu này.
- Quảng bá hỗ trợ ứng dụng thương mại/cloud hoặc các gói của nhà cung cấp khác.
- Mua credit, tự chuyển sang API tính phí, tự tăng hạn mức.

## Kiểm tra và tiêu chí hoàn thành

- Unit/integration test với OAuth server và stream giả: callback hợp lệ/sai/hết hạn, refresh, thiếu quyền, lỗi quota và stream thiếu sự kiện hoàn tất.
- Kiểm tra token không xuất hiện trong browser storage, JSON trả về, notebook, log hay URL ngoài callback bắt buộc; callback code không bị ghi log thô.
- Test logout và refresh không để phiên đã xóa được tác vụ nền lưu trở lại.
- Kiểm tra hồi quy luồng provider cũ và giao diện Cài đặt/reset notebook.
- Kiểm tra thật tối thiểu: người dùng tự đăng nhập trong trình duyệt → cấp quyền → lấy catalog → chủ động chạy một yêu cầu ngắn → nhận hoàn tất. Không yêu cầu người dùng gửi password/token vào chat.
- Nếu thiếu tài khoản/quyền/mạng, hoàn thành phần độc lập và ghi **chưa xác minh inference thật**. Không lấy mock hoặc catalog làm bằng chứng luồng dùng gói đã chạy.

## Cách làm việc và báo cáo

Triển khai trong phạm vi phase, cập nhật bàn giao dưới đây. Ghi bằng chứng đã được lược bỏ thông tin nhạy cảm, điều kiện môi trường và giới hạn thực tế. Không tự tiếp tục Phase 03.

## Bàn giao sau triển khai

- Trạng thái: **Hoàn thành Phase 02**, ngày 18/11/2026. Người dùng đã tự đăng nhập, cấp quyền, chọn model và chủ động chạy kiểm tra inference thật thành công. Chưa triển khai Phase 03.

### Bằng chứng kiểm tra thật

- Thời điểm hoàn tất: **18:43:24 ngày 18/11/2026, Asia/Ho_Chi_Minh**.
- Model được người dùng chọn và model thực tế trong phản hồi: **`gpt-6.1-terra`**.
- Backend xác nhận quyền dùng gói, catalog đã tải và inference đã nhận `response.completed`; không lấy badge đăng nhập hoặc HTTP 200 làm bằng chứng duy nhất.
- Thời lượng adapter: khoảng **3,77 giây**. Usage provider trả về: **15 input, 9 output, 24 total token**. Không suy ra chi phí hoặc phần trăm quota từ các số này.
- Người dùng xác nhận giao diện báo thành công; agent chỉ đọc metadata trạng thái sau đó, không gửi thêm yêu cầu inference thật.
- Credential storage trên máy kiểm tra: **keyring**. Không đưa email, subject, ID đăng ký, mã OAuth hay token thật vào bàn giao.

### Tài liệu và lựa chọn tích hợp

Kiểm tra tài liệu chính thức ngày 18/11/2026 và gọi discovery công khai thật; issuer và revocation endpoint đã được xác minh qua mạng.

- [Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in): public client đăng ký động, PKCE/nonce/state, callback `127.0.0.1` và xác minh ID token.
- [Accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions): refresh tuần tự, tái sử dụng registration, revocation và lưu credential được bảo vệ.
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations): public Responses route, catalog theo tài khoản, `store: false`, `stream: true` và sự kiện hoàn tất.
- [OIDC discovery công khai](https://auth.openai.com/.well-known/openid-configuration): endpoint và thuật toán xác minh.

Giữ React + FastAPI, dùng HTTPX trực tiếp và PyJWT; không thêm Electron, Tauri, Node sidecar hoặc Codex app-server. Các phiên bản đã dùng: HTTPX 0.28.1, PyJWT 2.15.1, cryptography 50.0.1, keyring 25.7.0. Dependency trực tiếp được khai báo trong `project/backend/requirements-api.txt`.

### Tệp/module và luồng đăng nhập

- `project/backend/services/chatgpt_oauth.py`: discovery bị giới hạn vào origin chính thức, đổi code, xác minh JWT RS256/JWKS/issuer/audience/expiry/nonce/subject, refresh và revocation.
- `project/backend/services/chatgpt_auth.py`: quản lý đăng ký/tài khoản, callback loopback, snapshot/generation, catalog, kiểm tra inference, đăng xuất và vòng đời runtime.
- `project/backend/services/chatgpt_storage.py`: host ID và metadata đăng ký ghi nguyên tử, quyền owner-only; token ở OS keyring hoặc RAM. Từ chối keyring dạng file plaintext/alternate không được cho phép.
- `project/backend/services/ai_security.py`: phiên browser cục bộ, cookie HttpOnly/SameSite=Strict, CSRF và kiểm tra peer/Host/Origin.
- `project/backend/api/routes/ai.py`, `backend/schemas/ai.py`: route và public DTO có danh sách field an toàn.
- `project/src/providers/chatgpt.py`: adapter Phase 01 gọi Responses, thu SSE upstream thành kết quả hoàn tất; phân loại auth/quota/model/permission/transport và không fallback sang billing khác.
- `project/src/llm.py`: dispatch provider `chatgpt`; giữ nguyên lỗi có kiểu từ credential resolver để không biến lỗi quota/tạm thời thành lỗi đăng nhập.
- `project/src/config.py`, `src/errors.py`, `backend/main.py`: cấu hình runtime, nhóm lỗi mới, đăng ký router và cleanup khi shutdown.
- `project/frontend/src/features/ai/`: khu vực Kết nối AI, client không giữ OAuth token, CSS theo giao diện hiện có.
- `project/frontend/src/features/notebooks/SettingsDialog.tsx`: thêm phần kết nối ngoài form reset notebook, tránh submit lẫn nhau.
- `project/frontend/vite.config.ts`: proxy cục bộ `/api/ai` cho dev/preview, giữ cookie/CSRF cùng origin frontend.
- `project/frontend/README.md`: cách kết nối, lưu phiên, giới hạn và đăng xuất.

Backend mở listener riêng trên `127.0.0.1` với cổng trống và path `/auth/callback`, trước khi người dùng được chuyển tới OpenAI. Popup chỉ nhận launch ticket cục bộ dùng một lần; backend tạo URL authorize chính thức. Callback không ghi access log/query và không phản chiếu code vào trang kết quả.

Mỗi lần đăng nhập tạo state/nonce/verifier mới, hết hạn sau 5 phút. Callback sai, trùng hoặc quá hạn không được đổi code. Đăng ký mới giữ `client_id` được cấp ngay khi callback hợp lệ để lần thử lại không tạo client vô hạn; đăng nhập lại giữ host ID/client ID và kiểm tra cùng subject. Không gửi `id_token_hint`, nên URL authorize không chứa ID token.

### Lưu credential, refresh và đăng xuất

- Mặc định metadata ở `project/.run/chatgpt/registrations.json`; có thể đổi bằng `RAG_CHATGPT_RUNTIME_DIR`. File chỉ có host/registration/identity metadata, không có access/refresh/ID token. Thư mục 0700, file 0600 trên Unix.
- Token set nằm trong namespace keyring của YourNote, tách theo host và ID tham chiếu đăng ký. Nếu keyring không được hỗ trợ/không dùng được thì mode trở thành `memory` và UI thông báo rõ. Không có file plaintext fallback.
- Constructor runtime được tuần tự hóa; file lock chỉ cho một runtime dùng kho đăng ký này để tránh hai process cùng refresh token xoay vòng.
- Refresh gần hết hạn được khóa riêng theo kết nối. Grant không được tự nâng quyền, scope không có trong phản hồi refresh giữ đúng quyền trước đó theo OAuth; lỗi tạm thời không xóa credential.
- Đăng xuất chặn truy cập/reauthorize mới của kết nối đó, chờ rotation đang chạy nếu có, rồi thu hồi refresh token mới nhất. Sau đó xóa token cục bộ và giữ registration để reconnect.
- Trả riêng `remote_revocation_confirmed` và `keyring_cleanup_confirmed`; không báo thu hồi từ xa thành công chỉ vì local logout đã chạy. Có liên kết quản lý quyền trong ChatGPT nếu chưa xác nhận thu hồi.

### API cho Phase 03 tái sử dụng

Tất cả route dưới `/api/ai` được bảo vệ bằng loopback, Host/Origin và browser session; POST cần CSRF. Frontend dùng proxy cùng origin. OAuth token không được gửi xuống frontend.

| Method | Route | Chức năng |
| --- | --- | --- |
| GET | `/api/ai/session` | Tạo/lấy cookie HttpOnly và CSRF token cục bộ |
| GET | `/api/ai/chatgpt` | Trạng thái đăng ký/quyền/catalog/inference an toàn |
| POST | `/api/ai/chatgpt/sign-in` | Bắt đầu đăng ký mới hoặc reconnect theo connection ID |
| GET | `/api/ai/chatgpt/sign-in/launch` | Dùng ticket một lần để chuyển tới OpenAI |
| POST | `/api/ai/chatgpt/sign-in/cancel` | Hủy phiên đăng nhập đang chờ |
| POST | `/api/ai/chatgpt/profiles/{id}/select` | Chọn đăng ký hiện có |
| POST | `/api/ai/chatgpt/profiles/{id}/catalog` | Tải lại catalog theo tài khoản, không inference |
| POST | `/api/ai/chatgpt/profiles/{id}/check` | Một yêu cầu AI ngắn, model phải thuộc catalog mới |
| POST | `/api/ai/chatgpt/profiles/{id}/logout` | Thu hồi phiên và xóa token cục bộ |
| POST | `/api/ai/chatgpt/profiles/{id}/notice` | Ghi nhận đã đọc thông báo dùng gói lần đầu |

Các trạng thái identity và quyền dùng gói tách biệt. Catalog chỉ hiển thị `visibility == "list"`, giữ thứ tự server, dùng `display_name` để hiển thị và `slug` để gọi model. Chọn model ngoài catalog bị từ chối, không tự chọn model thay thế.

### Kiểm tra và kết quả

- Baseline trước phase: **68/68 backend test đạt**.
- Sau triển khai: **92/92 backend test đạt**, bằng OAuth giả, JWT ký RSA tạm, MockTransport/SSE, callback HTTP loopback thật và DB/index/path tạm. Không gọi AI trả phí từ test tự động.
- Bao gồm callback sai/hết hạn/dùng lại, JWT signature/issuer/audience/expiry/nonce, khác subject/client, identity-only không có plan, refresh đồng thời, rotation, logout/refresh race, cancel khi đang exchange và rollback khi ghi manifest lỗi.
- Có test chặn origin lạ, peer từ xa, Host rebinding, thiếu session/CSRF và keyring plaintext. Kết quả/check HTTP không lộ mã/token.
- Frontend build đạt; lint 0 lỗi, 12 cảnh báo cũ, không thêm cảnh báo mới.
- Chrome headless với API giả: **32 tổ hợp** = 360/768/1280/1920px × dark/light × chưa kết nối/đã kết nối/thiếu quyền/cần reconnect; không tràn bố cục, form reset notebook còn hoạt động độc lập.
- Kiểm tra UI không tự inference khi mở Cài đặt, chọn model, lỗi quota, completed, logout chưa xác nhận revocation, và không lưu OAuth credential/CSRF vào browser storage.
- Kiểm tra thật do người dùng chủ động thực hiện đã đạt, với metadata ghi ở đầu bàn giao này.

Lệnh chính từ `project/`:

```bash
.venv/bin/python -m unittest discover -s backend/tests -q
.venv/bin/python -m compileall -q backend src app.py
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run lint
git diff --check
```

Trong môi trường agent này, TestClient/cổng callback cần runner ngoài sandbox như đã ghi ở Phase 01. Script kiểm tra browser nằm ở `/tmp/chatgpt-ui-check.mjs` với fixture riêng; không dùng profile Chrome của người dùng.

### Giới hạn và điều Phase 03 cần biết

1. Kết nối này chỉ phục vụ xác minh; Chat/reading/Studio vẫn dùng cấu hình cũ. Không đổi provider mặc định hoặc gán model mới vào notebook trong Phase 02.
2. Phase 03 lấy `get_manager()` từ `backend.services.chatgpt_auth`, xác minh ID kết nối và model theo catalog. Trong `llm_task`, dùng `CredentialRef(connection_id)` và resolver gọi `manager.access(ref.id)`; không đưa access token vào payload HTTP hay state notebook.
3. Provider `chatgpt` chưa nhận temperature/max output tokens và chưa công bố streaming downstream. Dùng `GenerationParameters()` rỗng; không tái sử dụng nguyên tham số của provider cũ.
4. Adapter hiện chỉ hỗ trợ text. Upstream SSE là bắt buộc và được thu thành `LLMResult` sau `response.completed`; partial/incomplete/lỗi giữa stream không thành công. Có giới hạn dữ liệu phản hồi 4 MB và timeout mạng, không retry inference tự động.
5. Phase 03 bổ sung stream/cancel tới UI và tích hợp model đã chọn cho mọi chức năng. Hiện `CancellationToken` chỉ có hiệu lực ở các điểm kiểm tra quanh I/O; không đảm bảo ngắt ngay khi SDK/HTTP đang đợi dữ liệu.
6. Catalog và metadata kiểm tra cuối hiện ở RAM, không được coi là quyền truy cập/quota vĩnh viễn. Sau restart phải tải catalog lại; credential ở keyring vẫn có thể khôi phục. Chế độ RAM yêu cầu đăng nhập lại sau khi dừng backend.
7. Frontend hỗ trợ origin local mặc định 5173/4173 và API local; bảo vệ kết nối không được tháo bỏ để triển khai remote. Ứng dụng thương mại/cloud cần xác minh điều kiện riêng.
8. Không mua credit, đổi billing, đọc lịch sử/memory ChatGPT, dùng cookie của ứng dụng khác hay gọi endpoint nội bộ. Các tính năng thuộc Phase 03 trở đi chưa được triển khai.
