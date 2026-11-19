# Demo học tập với dữ liệu tự tạo

Dữ liệu có giấy phép CC0-1.0 trong `evaluation/phase06/fixture.json`, không có thông tin sinh viên hoặc giáo trình của bên khác. Các file sẵn có ở `demo/materials/`; có thể tạo lại bằng lệnh:

```bash
.venv/bin/python -c "from evaluation.phase06.bundle import write_materials; write_materials('demo/materials')"
```

Dùng giáo trình DOCX, slide PDF, ghi chú MD và đề cương TXT; để file `nguon_khong_chon.txt` ngoài phạm vi được chọn. Những ngày hạn nộp là dữ liệu giả nhằm minh họa đối chiếu, không phải lịch thực tế.

| Bước | Thao tác và điều cần quan sát |
| --- | --- |
| 1 | Tạo sổ “Ôn tập ML minh họa”, nhập các file và chọn đúng nguồn. |
| 2 | Kết nối/chọn model được cấp quyền. Phần này cần mạng/tài khoản và đồng ý dùng hạn mức. |
| 3 | Hỏi “Học phần B chia dữ liệu thế nào?”, rồi “Vậy tập kiểm tra chiếm bao nhiêu?”. Kiểm tra câu sau trả đúng B và citation. |
| 4 | Hỏi hạn LAB-A nhóm A với giáo trình + đề cương; xem hai ngày khác nhau, không tự chọn nguồn đúng. Mở bằng chứng ở DOCX/TXT. |
| 5 | Tạo So sánh với tiêu chí MSE, điều kiện scaling, hạn LAB-A và học phí. Kiểm tra đủ từng nguồn, khác điều kiện và thiếu thông tin. |
| 6 | Lưu một nhận định vào ghi chú và xuất Markdown. |
| 7 | Tạo Mạng tri thức mục tiêu “MSE, hồi quy tuyến tính và gradient descent”; chọn node/cạnh, xem quote, mở nguồn; thử tìm/lọc/zoom/danh sách. |
| 8 | Hủy xóa một artifact rồi xóa thật. Reload để kiểm tra chỉ artifact đó bị xóa, nguồn và các kết quả khác còn. |
| 9 | Tạo thử một tác vụ rồi Dừng; kiểm tra không xuất hiện artifact hoàn tất từ tác vụ đã hủy. |

Mỗi thao tác tạo bằng AI dùng hạn mức và có thể gồm nhiều lời gọi. Demo mở lại/zoom/export/xóa kết quả đã lưu không cần gọi model. Có thể trình bày bằng kết quả synthetic đã lưu trong báo cáo mà không chạy lại inference; phải nói rõ đó là kết quả đã chạy trước, không giả làm luồng live.
