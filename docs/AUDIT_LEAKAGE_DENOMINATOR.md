# Audit leakage / key-label join / cùng mẫu / denominator / bootstrap theo khối tháng

Người thực hiện: Đăng. Ngày: 2026-11-11.
Đầu vào: `Week4_Frozen_Core_Acceptance_20261109.zip`, SHA-256 `3a36ca98...5e132` (khớp file `.sha256`).
Phạm vi: cohort full-study (final, 1.269 mẫu, label_month 2018-01..09) và cohort 2016 (main 494, rolling 1.107). H1 ngoài phạm vi.

## 1. Toàn vẹn và replay
- `package_week4_handoff.py --verify`: 45 file đã xác minh.
- `verify_week4_inputs.py` và `run_week4_acceptance.py` (output mới `dang-inputs-001`, `dang-replay-001`): qua 2 cohort.
- `replayed-metrics.csv` giống từng byte với `week4-replay-002` trong gói.
- H1: `pending_missing_inputs` (4 đường dẫn H1 không có trong gói frozen). Hành vi thiết kế, không phải lỗi.

## 2. Khóa ghép và nhãn
| Kiểm tra | Full-study | 2016 |
|---|---|---|
| Dòng dự báo trùng (5 khóa + model/seed/window) | 0 | 0 |
| Khóa nhãn trùng | 0 | 0 |
| Dự báo không ghép được nhãn | 0 | 0 |
| Số dòng thay đổi sau khi ghép | không | không |
| `y_true` khác nhãn gốc | 0 | 0 |
| Dự báo thuộc mẫu không eligible | 0 | 0 |

## 3. Cùng mẫu giữa model
- Full-study: 57 nhóm model/seed, đúng 1 tập mẫu (1.269). 72.333 = 57 x 1.269.
- 2016: main 1 tập (494), rolling 1 tập (1.107), 33 nhóm model/seed cho mỗi cửa sổ (66 nhóm tổng cộng).

## 4. Cutoff / leakage
- `label_month <= feature_month`: 0 dòng ở cả hai cohort.
- `available_through_month` khác `feature_month`: 0 dòng.
- Tests: 102 passed (leakage, causal order, split, acceptance) và 55 passed (diagnostics, research evaluation).
- Giới hạn: cutoff huấn luyện chỉ đối chiếu ở mức protocol, gói không có fit logs.

## 5. Denominator (full-study)
Bảng nhãn 11.745 dòng: 7.490 resolved, 4.072 unresolved (`weak_overlap_unresolved`), 183 censored (`final_snapshot_censored`).
Dự báo chỉ phủ 1.269 mẫu final, không phải 7.490. Unresolved/censored không bị quy thành dissolve.
Coverage: community-month 64,78%, member-month 79,31%.

## 6. Bootstrap theo khối tháng (paired_tables, 1.000 draws, block 2, 9 tháng, 3 seed gộp trong từng draw)
Kiểm chứng pipeline: tái tạo đúng bảng 6.3 của MIDTERM2_DIAGNOSTIC_REPORT
(+0,0474 [-0,0073; +0,0934], +0,0049 [-0,0195; +0,0191], +0,0796 [+0,0292; +0,1321]) và tỷ lệ outcome 55,40/35,07/1,34/8,20.
Chạy lại cùng seed cho kết quả y hệt.

| Proposed `hier_lr_dynamic` so với | Delta Macro-F1 | CI 95% | Chứa 0? |
|---|---:|---|---|
| hier_hgb_dynamic | +0,0237 | [-0,0694; +0,0945] | có |
| flat_hgb_dynamic | +0,0476 | [-0,0303; +0,1163] | có |
| flat_lr_dynamic | +0,0502 | [-0,0294; +0,1176] | có |
| B4_logreg | +0,0806 | [-0,0101; +0,1418] | có |
| B5_matched_boosting | +0,1788 | [+0,0843; +0,2524] | không |

Nhạy theo bootstrap seed (4 seed): kết luận không đổi (cặp với B5 luôn dương; các cặp còn lại luôn chứa 0).
Paired outcome so với hier_hgb_dynamic: cả hai đúng 88,18%, proposed-only 2,29%, reference-only 2,76%, cả hai sai 6,78%.

## 7. Phát hiện cần xử lý
1. Claim C04 (INTEGRATED report) "proposed có Macro-F1 cao nhất" đúng về số (0,4117 so với 0,3880) nhưng khoảng ghép cặp với `hier_hgb_dynamic`, `flat_*`, `B4_logreg` đều chứa 0. Chỉ nên diễn đạt là lợi thế điểm số, không phải khác biệt có ý nghĩa. Báo cáo hiện chưa công bố CI cho cặp proposed so với HGB.
2. Cặp proposed so với HGB có reference-only (2,76%) lớn hơn proposed-only (2,29%): proposed thắng Macro-F1 nhưng thắng ít ca hơn, đã được báo cáo nêu đúng (mục 6.1).

## 8. Chưa kiểm được
- Cutoff huấn luyện (không có fit logs).
- Kiểm version khi sửa nhãn: chưa có lần sửa nhãn nào để so; `test_mixed_reference` chỉ phủ một phần.
- H1 (ngoài phạm vi theo xác nhận).
- Bootstrap chỉ khám phá trên 9 tháng đã được xem, không phải xác nhận.
