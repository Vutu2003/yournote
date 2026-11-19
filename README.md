---
title: AIO2025M12 Project RAG Learning System
emoji: 📉
colorFrom: yellow
colorTo: indigo
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
---

# YourNote — không gian học tập với tài liệu

Ứng dụng cục bộ React + FastAPI: hỏi đáp có citation, đọc PDF/DOCX/Markdown/TXT, ghi chú và Studio (tóm tắt, quiz, flashcards, Mind Map, so sánh, báo cáo, mạng tri thức có bằng chứng). Chọn model từ kết nối được cấp quyền; credential giữ ở backend.

Bản **0.6.0-local** dành cho thử nghiệm localhost trên Linux x86_64, Python 3.12 và Node 24. Phần metadata Spaces phía trên thuộc entrypoint Gradio cũ; bản bàn giao hiện tại dùng hướng dẫn React/FastAPI dưới đây.

- [Cài mới, sử dụng, dừng/chạy lại, backup/restore](docs/LOCAL_GUIDE.md).
- [Demo với tài liệu tự tạo CC0](docs/DEMO.md).
- [Báo cáo đánh giá và giới hạn](reports/phase06/evaluation.md).
- [Checklist nội bộ](docs/RELEASE_CHECKLIST.md), [kịch bản dùng thử sinh viên](docs/STUDENT_TRIAL.md).

```bash
# Sau khi cài dependency theo hướng dẫn:
bash scripts/start_local.sh
bash scripts/status.sh
# http://127.0.0.1:5173
bash scripts/stop_all.sh
```

Kiểm tra hồi quy cô lập dữ liệu, không gọi LLM: `.venv/bin/python scripts/check_local.py` (thêm `--ui` khi có Chrome). Benchmark thật là opt-in riêng; xem preview, chọn model/subset/budget trước `--live`. Không dùng điểm mock làm chất lượng model.

Notebook, originals và index lưu trên máy; inference gửi ngữ cảnh cần thiết tới provider và dùng hạn mức được cấp quyền. Chưa có đồng bộ cloud, OCR tự động, thị trường được xác minh hoặc phát hành công khai. Không chạy API nhiều worker với Qdrant embedded.
