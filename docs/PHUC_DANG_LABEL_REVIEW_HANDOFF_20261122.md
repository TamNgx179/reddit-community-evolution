# Bàn giao gói review nhãn Phúc–Đăng — 22/11/2026

## Phạm vi và trạng thái

Tài liệu này ghi lại việc chuẩn bị kỹ thuật cho một vòng review nhãn **mù**
(blinded structural-label review). Đây là kiểm tra mức độ hợp lý của nhãn
chuyển tiếp dựa trên membership trong mạng quan sát; nó không chứng minh ground
truth xã hội.

- Mã nguồn: `origin/main` tại commit `e2c29d5`.
- Cohort: 15 corpus, các tháng đặc trưng từ `2015-01` đến `2015-12`.
- Seed đã cố định: `20261120`.
- Lấy mẫu: `--per-stratum 5`.
- Kết quả: 31 ca; vì không vượt 60 ca và `cases.json` không vượt 500 MiB nên
  không chạy lại với số ca nhỏ hơn.
- Trạng thái: **đã chuẩn bị và kiểm tra kỹ thuật, chưa được phát hành để chấm**.
  Phiếu A và B vẫn trống; chưa có submission, agreement hay kết luận người–tracker.

## Lệnh tái lập

```powershell
$env:PYTHONPATH = 'src'
python -m reddit_sna week1 --config configs/core.toml --run-id label-review-input-20261120

python -m reddit_sna review-labels `
  --forecast-run artifacts/core/label-review-input-20261120/forecast `
  --graph-run artifacts/core/label-review-input-20261120-input `
  --detection-run artifacts/core/label-review-input-20261120-input `
  --output artifacts/review/label-review-20261122-001 `
  --per-stratum 5 --seed 20261120

python scripts/audit_label_review_packet.py `
  --packet artifacts/review/label-review-20261122-001 `
  --output artifacts/review/label-review-20261122-001-audit
```

`review-labels` kiểm tra lineage/hash của ba input run. Audit sau đó xác nhận 31
ca có evidence membership dạng mù, `case_id` duy nhất, hai form cùng thứ tự và
trống, và không có top-level tracker label/reason/prediction trong `cases.json`.
Năm ca không có target chia sẻ thành viên là evidence hợp lệ, không phải bằng
chứng một nhóm ngoài đời đã biến mất.

## Gói đã tạo

Các artifact dưới `artifacts/` bị Git bỏ qua để không đưa case evidence hay
answer key lên repository.

| Người nhận | ZIP | SHA-256 | Nội dung được phép |
|---|---|---|---|
| Phúc (reviewer A) | `reviewer_a_handoff.zip` | `f44c5d1c9a58881c6105b87de362fd20c4dd0c0bc8e4a1494c866f677cb15f18` | `cases.json`, `reviewer_a.csv` trống, biểu mẫu provenance |
| Đăng (reviewer B) | `reviewer_b_handoff.zip` | `f586c13f6ec64e76a28127d8c7dc220ad7f865ee8439429e264c0dc8a947f632` | `cases.json`, `reviewer_b.csv` trống, biểu mẫu provenance |
| Tâm (coordinator) | `coordinator_handoff.zip` | `c7816329899a67e7943fe18237ec702b9bc33a8fdebfccf1e2c1b9328939e879` | `answer_key.json`, packet manifest |

Hai ZIP reviewer đã được kiểm tra để chắc chắn không có `answer_key.json`,
packet manifest hoặc phiếu của reviewer còn lại. ZIP coordinator không có
evidence/phiếu reviewer.

## Cổng bắt buộc trước khi gửi reviewer B

1. Tâm xác nhận 12 ca đã chấm trước đây không trùng cohort 2015, hoặc cung cấp
   danh sách `case_id` để loại trừ và chạy lại **trước khi** ai mở case.
2. Tâm xác nhận mình là người giữ key và rubric chính thức là phiên bản nào.
   Tài liệu hiện tại có mâu thuẫn: kế hoạch đính kèm gọi `frozen_v1.1`, còn
   `docs/LABEL_REVIEW.md` trên main vẫn ghi v1.1 là proposed.
3. Chỉ gửi ZIP reviewer B cho Đăng. Không gửi coordinator ZIP, packet manifest,
   form A hoặc gợi ý AI.

Sau đó Phúc và Đăng làm độc lập: mỗi người điền nhãn, confidence và rationale
cho toàn bộ 31 case, khai báo hỗ trợ AI nếu có, rồi gửi CSV cùng SHA-256 cho
Tâm để khóa. Đăng chỉ chạy agreement sau khi Tâm xác nhận đã nhận và khóa đủ
hai phiếu; answer key chỉ được mở sau mốc đó.
