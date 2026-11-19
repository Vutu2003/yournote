# Checklist nội bộ 0.6.0-local

Bảng bằng chứng cuối nằm trong `reports/phase06/evaluation.md`. Đây là quyết định cho thử nghiệm cục bộ, không phải phát hành công khai hoặc xác minh thị trường.

- [x] Bộ CC0 30 câu: 10 một nguồn, 8 nhiều nguồn, 6 thiếu bằng chứng, 6 nối tiếp; giáo trình/slide/ghi chú và bốn định dạng.
- [x] Dataset/rubric/hash/ngưỡng chốt trước đo; kết quả từng câu và annotation theo hash.
- [x] Runner preview mặc định, opt-in + xác nhận plan + budget, không fallback/retry lỗi và không chạy inference trong unit test.
- [x] Inference thật 30 hybrid +8 vector cùng model trong giới hạn người dùng chọn; tách phép chấm tự động/thủ công.
- [x] Không dùng nguồn ngoài scope, marker/locator được kiểm tra, không lấy câu trả lời cũ làm bằng chứng.
- [x] Test auth/quota/stream/cancel, dữ liệu cũ, Studio/graph, autosave lỗi, xóa/reset đúng notebook.
- [x] 48 tổ hợp giao diện 360/768/1280/1920px, hai theme, Studio/reading/model picker.
- [x] Cài mới source/venv CPU/npm, start/stop/restart và restore bản sao: `clean-runtime.json` success, state/nguồn/citation lịch sử đúng.
- [x] Archive allowlist được giải nén kiểm checksum, không có dữ liệu/credential runtime; xem `releases/manifest.json` và `reports/phase06/package-proof.json`.
- [x] Chuẩn bị hướng dẫn localhost, backup/restore và demo có quyền sử dụng.
- [x] Chuẩn bị biểu mẫu dùng thử 3–5 sinh viên, chưa liên hệ ai.
- [ ] Dùng thử sinh viên thật — chưa thực hiện.
- [ ] So sánh nhiều model trên cùng retrieval — chưa chạy trong ngân sách 38 calls.
- [ ] Kiểm chứng Windows/macOS — chưa thực hiện.
- [ ] Xác nhận lợi ích thị trường/tận dụng gói hiệu quả hơn — chưa có dữ liệu.

Không có commit/tag/public release/deploy trong Phase 06. Kết quả synthetic nhỏ và chấm của developer không thay thế đánh giá độc lập hoặc kiểm chứng trên môn học thật.
