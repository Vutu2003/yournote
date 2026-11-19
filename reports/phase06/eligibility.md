# Kiểm chứng điều kiện tích hợp — 18/11/2026

Phạm vi bàn giao là ứng dụng source chạy localhost, không public hosting hoặc phát hành thương mại. Kết nối thực tế đã được người dùng tự cấp quyền; benchmark lần này xác minh lại model trong catalog trước inference.

- Plan usage là quyền bổ sung ngoài đăng nhập danh tính; không cho ứng dụng đọc lịch sử ChatGPT. Host ID phải ổn định qua restart. Flow hiện có dùng registration theo người dùng/workspace và keyring/RAM. [OSS/local overview](https://developers.openai.com/siwc/token-sharing-open-source)
- Model lấy từ catalog của đúng access token, giữ model slug được cấp quyền. Gọi public Responses API, `store:false`, `stream:true`; chỉ `response.completed` xác nhận thành công. Lỗi hạn mức có thể đến sau text. [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- Luồng HTTP không gửi temperature/max_output_tokens/previous_response_id hoặc các field bị loại; gửi lại ngữ cảnh cần thiết. Adapter text hiện có phù hợp phạm vi này, không thêm hosted file search/OCR hay tools ngoài phạm vi. [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- Quyền/hạn mức phụ thuộc gói, workspace/admin, ứng dụng và cài đặt cấp quyền; không thể suy ra quota còn lại từ token. Các quyền dùng credit khác phải do người dùng bật trong tài khoản, YourNote không tự chuyển billing. Tình trạng một tài khoản benchmark không chứng minh mọi tài khoản đều có cùng quyền. [Using your ChatGPT plan in other apps and sites](https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites)
- Cài đặt giữ thông báo dùng gói và liên kết quản lý usage. Theo yêu cầu UI đã chốt, các mục tài khoản/gói/usage nằm trong Cài đặt, model picker trong composer; không thêm lại banner/link dư trên sổ tay. [UI/UX guidelines](https://developers.openai.com/siwc/ui-ux-guidelines), [usage settings](https://chatgpt.com/settings/usage)

Đã đọc lại tài liệu ngày trên. Điều kiện có thể thay đổi; không tuyên bố mọi model/gói đều hỗ trợ hoặc dùng vô hạn. Các giới hạn thương mại/cloud chưa được đánh giá vì ngoài phạm vi bản cục bộ.
