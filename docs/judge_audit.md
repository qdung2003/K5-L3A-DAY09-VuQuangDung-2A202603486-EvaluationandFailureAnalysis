# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | có | dùng |
| helpful | 100 | 0.375 | 1.0 | 0.3 | không | loại |

Ma trận tone: tp 24, fp 4, fn 6, tn 66. Tỉ lệ FAIL quan sát 0.28, Rogan–Gladen 0.3.
Ma trận helpful: tp 9, fp 0, fn 21, tn 70. Precision cao vì hầu như không bao giờ nói FAIL, recall 0.3 nên bỏ sót 21 case người chấm FAIL.

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | người | "Em đã hoàn tiền" — xưng hô không phải tone hỗ trợ |
| 2 | H-017 | PASS | FAIL | người | "bạn ơi" + "nha", tone lệch |
| 3 | H-029 | PASS | FAIL | người | Câu chờ xử lý, không xác nhận kết quả |
| 4 | H-042 | FAIL | PASS | người | Có số tiền, hạn 3–5 ngày, tone đạt; judge phạt oan |
| 5 | H-051 | FAIL | PASS | người | "LogiX đã refund 90.000đ" là câu đạt; judge quá khắt |

## Kết luận
- `helpful` bị loại: κ 0.375 và recall 0.3, dưới sàn. Judge gần như luôn PASS nên không bắt được câu vô ích. Không được dùng làm gate.
- `tone_ok` đạt cả ba sàn, được dùng cho theo dõi, không thay grader tiền và approval.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
