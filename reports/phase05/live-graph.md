# Mạng tri thức

## Mục tiêu

Liên kết MSE, sai số dự đoán, hồi quy tuyến tính, gradient descent và chuẩn hóa đặc trưng; chỉ quan hệ được nêu rõ trong nguồn.

## Phạm vi nguồn

- textbook--6c1710b77487833c.docx: 4/4 đoạn; complete; version 6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd
- slides--9024c3202ad306dd.pdf: 1/1 đoạn; complete; version 9024c3202ad306dd07ea4a476c5af04777e59b241ccddc49eea45009f4fe40b7
- notes--ac5273b411989a76.md: 4/4 đoạn; complete; version ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c

## Khái niệm

### Hồi quy tuyến tính

Tên thay thế: Linear regression, Hồi quy tuyến tính

Một mô hình học có giám sát dự đoán mục tiêu dạng số.

> [S1] Linear regression is a supervised learning model that predicts a numerical target.

> [S5] Linear regression predicts a numerical target.

### Mục tiêu dạng số

Tên thay thế: numerical target

Đại lượng dạng số được hồi quy tuyến tính dự đoán.

> [S1] Linear regression is a supervised learning model that predicts a numerical target.

### Sai số bình phương trung bình

Tên thay thế: Mean squared error, MSE, Sai số bình phương trung bình, mean squared error

Thước đo trung bình của sai số dự đoán bình phương.

> [S2] Mean squared error (MSE) measures the average squared prediction error.

> [S5] MSE means mean squared error.

> [S7] MSE (mean squared error) là trung bình bình phương sai số dự đoán.

### Sai số dự đoán bình phương

Tên thay thế: squared prediction error

Đại lượng có giá trị trung bình được đo bằng MSE.

> [S2] Mean squared error (MSE) measures the average squared prediction error.

### Gradient descent

Tên thay thế: Gradient descent, gradient descent

Phương pháp yêu cầu chuẩn hóa đặc trưng trong các bài tập của khóa học này.

> [S3] Gradient descent requires feature scaling for this course's exercises.

> [S5] Gradient descent minimizes mean squared error.

> [S8] Cần chuẩn hóa đặc trưng khi dùng gradient descent trong bài thực hành.

### Chuẩn hóa đặc trưng

Tên thay thế: feature scaling, Chuẩn hóa đặc trưng

Điều được gradient descent yêu cầu trong các bài tập của khóa học này.

> [S3] Gradient descent requires feature scaling for this course's exercises.

> [S5] Decision trees do not require feature scaling in this course.

### Cây quyết định

Tên thay thế: Decision trees

Trong khóa học này, cây quyết định không yêu cầu chuẩn hóa đặc trưng.

> [S5] Decision trees do not require feature scaling in this course.

### sai số dự đoán

Tên thay thế: sai số dự đoán

Sai số dự đoán là đại lượng được bình phương và lấy trung bình trong MSE.

> [S7] MSE (mean squared error) là trung bình bình phương sai số dự đoán.

### chuẩn hóa đặc trưng

Tên thay thế: chuẩn hóa đặc trưng

Chuẩn hóa đặc trưng là việc cần làm khi dùng gradient descent trong bài thực hành.

> [S8] Cần chuẩn hóa đặc trưng khi dùng gradient descent trong bài thực hành.

### cây quyết định

Tên thay thế: cây quyết định

Cây quyết định là đối tượng được áp dụng quy tắc không cần chuẩn hóa trong slide.

> [S9] Quy tắc không cần chuẩn hóa trong slide áp dụng cho cây quyết định, không áp dụng cho gradient descent.


## Quan hệ

### Hồi quy tuyến tính → Mục tiêu dạng số (predicts)

Hồi quy tuyến tính dự đoán một mục tiêu dạng số.

> [S1] Linear regression is a supervised learning model that predicts a numerical target.

### Sai số bình phương trung bình → Sai số dự đoán bình phương (measures)

MSE đo trung bình của sai số dự đoán bình phương.

> [S2] Mean squared error (MSE) measures the average squared prediction error.

### Gradient descent → Chuẩn hóa đặc trưng (requires)

Gradient descent yêu cầu chuẩn hóa đặc trưng trong các bài tập của khóa học này.

> [S3] Gradient descent requires feature scaling for this course's exercises.

### Gradient descent → Sai số bình phương trung bình (optimizes)

Gradient descent tối thiểu hóa MSE.

> [S5] Gradient descent minimizes mean squared error.

### Sai số bình phương trung bình → sai số dự đoán (measures)

MSE biểu thị trung bình bình phương sai số dự đoán.

> [S7] MSE (mean squared error) là trung bình bình phương sai số dự đoán.

### Gradient descent → chuẩn hóa đặc trưng (requires)

Trong bài thực hành, dùng gradient descent cần chuẩn hóa đặc trưng.

> [S8] Cần chuẩn hóa đặc trưng khi dùng gradient descent trong bài thực hành.

### cây quyết định → Gradient descent (contrasts_with)

Quy tắc không cần chuẩn hóa trong slide áp dụng cho cây quyết định nhưng không áp dụng cho gradient descent.

> [S9] Quy tắc không cần chuẩn hóa trong slide áp dụng cho cây quyết định, không áp dụng cho gradient descent.


## Giới hạn

- Bằng chứng được giới hạn trong các nguồn/đoạn đã xét; trích dẫn đúng vị trí không tự chứng minh mọi diễn giải là đúng.
- Đã cung cấp tất cả chunk trong phạm vi chọn; vẫn cần đối chiếu nhận định quan trọng với trích đoạn gốc.
- Chỉ gộp khái niệm khi cùng khóa nghĩa và trùng tên/alias có trong nguồn; khái niệm có thể còn trùng nếu chưa chắc đồng nghĩa.

## Sources

- [S1] textbook--6c1710b77487833c.docx đoạn 1 | anchor: b000001 | version: 6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd | chunk: a73b32117e8681a7f2c6e28624f2d0a4251a8be80069be4e3b2f3e848cb39f14:6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd:b000001:00f821f85a4c:0
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Linear regression is a supervised learning model that predicts a numerical target.</div></details>
- [S2] textbook--6c1710b77487833c.docx đoạn 2 | anchor: b000002 | version: 6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd | chunk: a73b32117e8681a7f2c6e28624f2d0a4251a8be80069be4e3b2f3e848cb39f14:6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd:b000002:a5882501003f:1
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Mean squared error (MSE) measures the average squared prediction error.</div></details>
- [S3] textbook--6c1710b77487833c.docx đoạn 3 | anchor: b000003 | version: 6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd | chunk: a73b32117e8681a7f2c6e28624f2d0a4251a8be80069be4e3b2f3e848cb39f14:6c1710b77487833c55e44a7c93f0c629985963b3360508a3bc9f5e50a21600fd:b000003:3c9865c4d5cb:2
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Gradient descent requires feature scaling for this course's exercises.</div></details>
- [S5] slides--9024c3202ad306dd.pdf p.1 | version: 9024c3202ad306dd07ea4a476c5af04777e59b241ccddc49eea45009f4fe40b7 | chunk: 908304154ec2003c8967846c37d0a1c8a136bad2d4806f6ac9a3e39efe6e231c:9024c3202ad306dd07ea4a476c5af04777e59b241ccddc49eea45009f4fe40b7:1:5dd85e892f22:0
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Linear regression predicts a numerical target.
MSE means mean squared error.
Decision trees do not require feature scaling in this course.
Assignment LAB-A is due on 21 April 2026 for Group A.
Gradient descent minimizes mean squared error.</div></details>
- [S7] notes--ac5273b411989a76.md Ghi chú ôn tập · đoạn 2 | anchor: b000002 | version: ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c | section: Ghi chú ôn tập | chunk: 05f549037edba6ff621bd96a92cda8d6e2e6f122ac1db61fa37d9dc24af9869c:ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c:b000002:baa46ac0347b:1
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">MSE (mean squared error) là trung bình bình phương sai số dự đoán.</div></details>
- [S8] notes--ac5273b411989a76.md Ghi chú ôn tập · đoạn 3 | anchor: b000003 | version: ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c | section: Ghi chú ôn tập | chunk: 05f549037edba6ff621bd96a92cda8d6e2e6f122ac1db61fa37d9dc24af9869c:ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c:b000003:70d5f518c31b:2
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Cần chuẩn hóa đặc trưng khi dùng gradient descent trong bài thực hành.</div></details>
- [S9] notes--ac5273b411989a76.md Ghi chú ôn tập · đoạn 4 | anchor: b000004 | version: ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c | section: Ghi chú ôn tập | chunk: 05f549037edba6ff621bd96a92cda8d6e2e6f122ac1db61fa37d9dc24af9869c:ac5273b411989a769e2f278b56c3bf7c9e6fcf18656b68f37966787d0410f25c:b000004:ac9e65f1ba07:3
  <details><summary>Xem đoạn nguồn</summary><div style="margin:8px 0 0 0; white-space:pre-wrap;">Quy tắc không cần chuẩn hóa trong slide áp dụng cho cây quyết định, không áp dụng cho gradient descent.</div></details>

## Thông tin lần tạo

- Provider: chatgpt
- Model yêu cầu: gpt-6.1-terra
- Model thực tế: gpt-6.1-terra
- Thời điểm: 2026-11-18T14:55:10.108205+00:00
- Trạng thái: completed
- Số lời gọi: 3
