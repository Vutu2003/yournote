# Phase 04 — chiến lược trước khi ghi dữ liệu

Ngày lập: 18/11/2026. Chỉ triển khai Phase 04; giữ nguyên embedding và collection hiện tại.

## Tương thích và identity

- Schema nguồn/chunk/workspace bổ sung version 2 theo cách cộng thêm field. JSON cũ được đọc với default; không đổi tên nguồn, ID PDF cũ, ghi chú, alias, artifact hoặc highlight.
- Nguồn mới lưu bản gốc bất biến theo SHA-256 nội dung, tách filename khóa nội bộ khỏi original_filename/tên hiển thị. Hai tệp cùng tên khác nội dung không ghi đè nhau. Tải lại cùng nội dung upsert/deduplicate.
- Registry SQLite quản lý logical document ID, active version và các bản lưu. Cập nhật có chủ đích theo từng tài liệu, với expected version; không tự coi mọi tệp cùng tên là bản thay thế.
- Chunk và citation mới mang document_id, document_version, locator có loại. PDF: page; DOCX/MD/TXT: heading/paragraph anchor trong phiên bản. Không tạo page giả.
- Citation cũ thiếu version phải đối chiếu source_text với bản gốc trước khi mở; nếu không xác minh được, báo rõ thay vì âm thầm mở nội dung mới.

## Dữ liệu thật và bản sao lưu

1. Viết/test migration và rollback với thư mục tạm trước; chưa sửa dữ liệu thật khi viết code hoặc benchmark.
2. Khi triển khai lên dữ liệu thật, dừng đúng backend một worker và chờ Qdrant/SQLite đóng. Kiểm tra lock trước khi sao lưu. Chặn tiến trình app cùng dùng kho khi migration đang chạy.
3. Tạo bản sao nhất quán của notebooks.sqlite (SQLite backup API), Qdrant đã đóng, thư mục data và registry nếu có. Không sao chép keyring, phiên OAuth hoặc file cấu hình credential vào backup. Manifest chỉ có schema, đường dẫn tương đối, thời gian và checksum.
4. Migration idempotent đăng ký/archive PDF cũ theo filename/ID hiện tại. Giữ các payload vector cũ; không re-embed và không đổi collection. JSON workspace được nâng schema khi lưu bình thường; bản sao lưu giữ JSON nguyên bản.
5. Nguồn mới chỉ trở thành active sau khi parse/index thành công. Lọc phiên bản active trong retrieval; lỗi staging không làm phiên bản dở dang trở thành nguồn hợp lệ. Bản cũ lưu cho việc mở citation lịch sử.
6. Khi đổi embedding model/dimension trong tương lai phải dùng collection riêng. Phase này chỉ kiểm tra tính tương thích và từ chối trộn vector sai.

## Rollback

Dừng backend, giữ riêng thư mục sau migration để điều tra; phục hồi data, Qdrant, notebooks.sqlite và registry từ cùng một backup đã kiểm tra checksum. Chạy code trước Phase 04 với đúng embedding/collection cũ. Không ghép SQLite của một mốc với Qdrant của mốc khác. Công cụ rollback phải được thử trên fixture trước khi sử dụng với dữ liệu thật.

## Bằng chứng sẽ bổ sung sau triển khai

Kết quả migration/rollback fixture, vị trí backup thật, định dạng schema chính thức, giới hạn parser và kết quả đánh giá sẽ được ghi vào bàn giao Phase 04. Không ghi nội dung tài liệu cá nhân hay credential vào báo cáo.

## Kết quả triển khai

- Đã thử migration/rollback trong fixture riêng; chạy lại migration không đổi ID hoặc nhân đôi bản nguồn. Thử lỗi giữa chừng, checksum backup hỏng, backend còn chạy và Qdrant đang mở đều có kiểm tra.
- Backup thật trước thao tác: `storage/backups/phase04-preflight-20261118T133309`.
- Backup nhất quán ngay trước migration: `storage/backups/phase04-apply-20261118T134930`.
- Đăng ký 4 nguồn cũ, giữ nguyên document ID/filename/số chunk; không thiếu bản gốc. JSON của 3 notebook được đối chiếu trước/sau và giữ nguyên.
- Kho hiện tại chưa có citation lưu trong notebook/artifact để kiểm chứng trực tiếp. Đã kiểm tra 175/175 chunk của 4 PDF khớp bản gốc đã archive, không xuất tên/nội dung riêng vào báo cáo. Fixture riêng kiểm chứng cả citation/artifact cũ và citation không có version sau khi cập nhật PDF.
- `legacy_version` cố định bản tại thời điểm migration; citation PDF cũ không có version được kiểm chứng và gắn vào bản đó, kể cả khi active version đã thay đổi. Trích đoạn không khớp sẽ bị từ chối, không suy đoán bằng ngưỡng tương đồng.
- Embedding model/dimension không đổi, không re-embed corpus hoặc đổi collection. Các file nguồn cũ ở root data được giữ; bulk rebuild ưu tiên bản active trong registry để không hoàn nguyên nhầm một PDF đã cập nhật.
- Backend Phase 04 đã bật lại với một worker; health, OpenAPI, danh sách nguồn/notebook, frontend và proxy đều 200. Phiên ChatGPT trong keyring được khôi phục; không cần đăng nhập lại chỉ vì migration.

## Schema và atomic visibility

Registry ở `storage/documents.sqlite` có `catalog_meta.schema_version=2`, bảng `documents` và `document_versions`. Bản gốc ở `data/.versions/<SHA-256>/<original_filename>`. Logical ID của nguồn mới bắt đầu từ hash của format + hash nội dung và được giữ khi thay phiên bản; `document_version` là SHA-256 của byte gốc. Filename trong notebook là khóa ổn định, không dùng phần hash trong tên để suy ra phiên bản active.

Chunk v2 có document ID/version, locator, chunk ID xác định theo nội dung và thứ tự. Chỉ các point thuộc phiên bản active đã commit mới hiện trong library/retrieval. Nếu ghi Qdrant dở dang trước commit registry, point staging không hiện; khi retry/upsert thành công, chunk cũ của tài liệu đó được dọn. Original/version cũ vẫn tồn tại để mở citation. Reupload có thể sửa lại index bị thiếu; không đòi xóa corpus.

API và workspace thêm field optional/default. `WorkspaceState.schema_version` nhận 1/2, frontend lưu 2. Locator PDF là `{kind:"page",page:n}`; DOCX/MD/TXT là `{kind:"paragraph",anchor:"b000001",paragraph:n,heading:[...]}`. Anchor chỉ ổn định trong một content version. Citation/export ghi version/locator; không tạo trang cho tài liệu reflowable.

## Lệnh chạy lại và phục hồi

Chạy từ `project/`, **dừng backend trước**. Không xóa thư mục `data`/`storage` bằng tay.

```bash
.venv/bin/python scripts/migrate_phase04.py migrate --backup storage/backups/phase04-new-unique-name
.venv/bin/python scripts/migrate_phase04.py rollback --backup storage/backups/phase04-apply-20261118T134930
```

Đích backup mới phải chưa tồn tại. Công cụ dùng process guard và kiểm tra lock Qdrant; không lấy snapshot từ một index đang ghi. Restore xác minh checksum trước, chuyển dữ liệu hiện tại sang `storage/backups/pre-rollback-*` rồi phục hồi cùng bộ snapshot. File `.phase04-incomplete` chặn backend khởi động nếu migration/restore bị ngắt; hoàn tất retry hoặc rollback bằng công cụ, không chỉ xóa marker.

Code Phase 04 đọc được JSON/index kiểu cũ sau rollback. Dữ liệu registry được phục hồi đúng trạng thái lúc backup (có thể chưa tồn tại); chạy migration lại trước khi tiếp tục cập nhật các PDF legacy. Nếu dùng bản code cũ do bạn quản lý, phải giữ cùng embedding/collection tương ứng. Không cần `git reset`, không có commit tự động từ lần triển khai này.

Parser đọc DOCX main body/headings/table text, Markdown ATX headings, TXT UTF-8 và text PDF. Không dựng layout Word, không đọc header/footer/footnote/embedded objects như nội dung chính, không OCR. Giới hạn và số liệu đánh giá ở [evaluation.md](evaluation.md).
