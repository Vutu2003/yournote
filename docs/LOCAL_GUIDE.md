# Chạy YourNote cục bộ

Bản 0.6.0-local dành cho dùng thử có kiểm soát trên Linux x86_64. Giữ React + FastAPI trên localhost, chưa đóng gói Tauri/Electron. Windows/macOS chưa được kiểm chứng.

## Cài mới

Môi trường tham chiếu: Python 3.12.10, Node 24.21.0/npm 11.19.0. Cần trình duyệt hiện đại và chỗ trống cho dependency, embedding model, tài liệu và backup. Cài trên bản thư mục mới; không ghi đè `.env` hoặc dữ liệu của bản đang dùng.

Trong workspace vào `project/`; nếu giải nén archive thì vào thư mục `yournote/` thay cho `project/` trong lệnh dưới.

```bash
cd project
# Node 24 phải có trong PATH; nếu dùng Node của workspace:
export PATH="$PWD/.tools/node/bin:$PATH"
bash scripts/setup_local.sh
# Tùy chọn cho cài mới; chỉ chạy nếu chưa có .env:
cp -n .env.example .env
bash scripts/start_local.sh
bash scripts/status.sh
```

`requirements-local.txt` dùng snapshot `requirements-local.lock` làm constraints. Bộ cài local dùng PyTorch CPU cùng nhánh 2.14, tránh tải CUDA không cần cho embedding. Đây là snapshot Linux đã kiểm tra, không phải lockfile đa nền tảng có hash wheel. `requirements.txt` gốc phục vụ giao diện Gradio cũ, không phải entrypoint của bản React này.

Mở **http://127.0.0.1:5173**. API: **http://127.0.0.1:8000**; health: `/api/health`; tài liệu API: `/docs`. Bản local dùng frontend đã build qua Vite preview, chỉ bind loopback; không dùng làm public production server. Chế độ phát triển: `bash scripts/start_all.sh` hoặc các script `dev_backend.sh`, `dev_frontend.sh`.

Lần đầu dùng retrieval cần tải `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; lần sau dùng cache. Health/OpenAPI không tải embedding. Không đổi tên embedding model trên kho cũ: collection ràng buộc identity/dimension để tránh đọc nhầm vector.

## Kết nối và học với tài liệu

1. Tạo sổ tay ở trang chủ. Thêm PDF có text, DOCX, Markdown hoặc TXT UTF-8; đổi tên hiển thị nếu cần. Chọn đúng các nguồn sẽ dùng cho Chat/Studio.
2. Vào **Cài đặt → Kết nối AI**, chọn dịch vụ/kết nối. Với ChatGPT, bấm **Continue with ChatGPT**, tự hoàn tất đăng nhập/cấp quyền rồi trở lại. Đăng nhập danh tính khác với quyền dùng gói. Có thể dùng provider API máy chủ nếu đã cấu hình khóa ở backend.
3. Chọn model trong ô chat; chỉ model được cấp quyền mới khả dụng. Model/mức suy luận đã mất quyền phải được chọn lại; ứng dụng không tự đổi model hoặc đường tính phí.
4. Hỏi câu đầu rồi hỏi nối tiếp. Bấm citation để mở đúng trang/đoạn và phiên bản nguồn. Câu trả lời trước không phải bằng chứng độc lập.
5. Studio giữ Tóm tắt, Quiz, Flashcards, Mind Map và Ghi chú; thêm So sánh, Tổng hợp/Báo cáo, Mạng tri thức. Kết quả có thể xem lại, xuất Markdown, xóa có xác nhận. Các công cụ nghiên cứu chuyển ý/mục/node/cạnh thành ghi chú có dẫn chứng.
6. Bấm Dừng để hủy tác vụ. Nội dung dở dang không được lưu thành kết quả hoàn tất. Hủy không hoàn lại usage đã tiêu thụ. Đổi sổ tay sẽ dừng tác vụ đang chạy.

Local-first nghĩa là notebook/index/originals lưu trên máy; phần ngữ cảnh cần cho inference vẫn gửi tới provider bạn chọn. Inference cần mạng và tài khoản/quyền/hạn mức phù hợp; không có cam kết dùng vô hạn hoặc truy cập mọi model. Trong Cài đặt có liên kết quản lý usage chính thức; không có phần trăm quota suy đoán.

Token ở OS keyring nếu được hỗ trợ; nếu chỉ có chế độ RAM, ứng dụng thông báo và cần đăng nhập lại sau khi tắt backend. Không gửi mật khẩu/token cho người hỗ trợ, không đưa chúng vào `.env.example`, Vite env hoặc notebook.

## Dừng/chạy lại

```bash
bash scripts/stop_all.sh
bash scripts/start_local.sh
bash scripts/status.sh
```

Qdrant embedded chỉ dùng **một worker**. Các script quản lý PID/start-time/session và từ chối dừng tiến trình không xác minh được. Nếu ứng dụng cũ chạy thủ công ngoài manager, dừng đúng terminal của nó trước; không dùng `killall python/node` và không tăng worker để né khóa index. Log private ở `.run/backend.log`, `.run/frontend.log`; không chia sẻ nguyên `.run`.

## Backup và restore

Backup phải gồm SQLite notebook, registry tài liệu, Qdrant, originals và toàn bộ `data/.versions`; không copy từng phần đang ghi. Backup có tài liệu cá nhân nên vẫn phải giữ riêng, dù không chứa credential runtime.

```bash
bash scripts/stop_all.sh
.venv/bin/python scripts/backup_local.py backup --backup storage/backups/my-snapshot
.venv/bin/python scripts/backup_local.py verify --backup storage/backups/my-snapshot
# Xem trước; chưa thay dữ liệu:
.venv/bin/python scripts/backup_local.py restore --backup storage/backups/my-snapshot
# Chỉ thực hiện khi chấp nhận thay dữ liệu bằng snapshot đã chọn:
.venv/bin/python scripts/backup_local.py restore --backup storage/backups/my-snapshot --confirm-restore RESTORE
bash scripts/start_local.sh
```

Restore thay cả bộ dữ liệu; thay đổi sau snapshot sẽ bị thay thế. Công cụ tự giữ bản recovery trước restore. Thử restore vào data root riêng trước khi dùng với kho thật. Không chép keyring, `.run/chatgpt`, `.env` vào demo/backup chia sẻ. Khi chuyển máy, đăng nhập lại bằng tài khoản của người sử dụng. Citation cũ phụ thuộc archive nên không tự xóa `.versions` để tiết kiệm dung lượng.

## Lỗi thường gặp

| Triệu chứng | Cách xử lý |
| --- | --- |
| Cổng 5173/8000 đang bị chiếm | Kiểm tra terminal/status, dừng đúng dịch vụ cũ; manager không tự dừng tiến trình lạ. |
| Qdrant bị khóa | Dừng API/Gradio/CLI đang mở cùng kho; chạy lại một worker. Không xóa file lock để ép mở. |
| Chưa tải được embedding | Lần đầu cần mạng tải model; chỉ bật HF_HUB_OFFLINE khi cache đã sẵn sàng. |
| PDF scan không có text | Cần bản có text; chưa có OCR tự động. DOCX không đọc công thức/ảnh nhúng như OCR. |
| Cần kết nối lại/model mất quyền | Mở Cài đặt, kết nối lại/tải catalog và tự chọn model; không có fallback tính phí. |
| Hết quota/lỗi giữa stream | Xem quản lý usage; bản dở dang không lưu. Không bấm tạo lặp liên tục. |
| Lưu chưa thành công | Giữ tab, bấm Thử lại hoặc sửa tiếp để lưu lại. Chưa reload tab trước khi xác nhận đã lưu. |
| Citation báo nguồn cũ/không khớp | Mở bản archive đúng phiên bản hoặc khôi phục backup; không gán citation sang bản mới. |

Giới hạn nghiên cứu: 6 nguồn × 6 chunk, 60.000 ký tự context; graph tối đa 50 node/100 cạnh. Tác vụ vượt giới hạn báo lỗi rõ, không tự cắt rồi gọi đó là kết quả đầy đủ. Cần đọc trích đoạn gốc cho các kết luận quan trọng.
