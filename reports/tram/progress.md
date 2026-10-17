# Tiến độ Trâm — Tuần 1 (15–21/10/2026)

Dữ liệu tuần 1: **synthetic (tổng hợp)**, bộ `synthetic-v1`, seed 42.
Evidence run: `artifacts/prediction/prediction-demo-002` (run-id `prediction-demo-002`).

---

## Việc đã làm

### M0 — Recon (17/10)

- Đọc `config.py`, `artifacts.py`, `cli.py`, `pipelines/prediction.py` (stub), `contracts.py`.
- Xác nhận:
  - `cli.py` import `pipelines.prediction` lazy bên trong hàm chạy pipeline, không import ở đầu file.
  - `artifacts.create_run_directory(config)` gọi `validate_destination` trước khi ghi bất kỳ file nào.
  - `contracts.py`: `Event` (StrEnum: stable, grow, shrink, merge, split, dissolve), `next_month`, `SampleKey`, `CommunitySample`, `Prediction`.
  - `pyproject.toml` gốc: `dependencies = []`; pandas/scikit-learn/numpy cài thủ công vào venv, không sửa `pyproject.toml`.

### M1+M2 — Generator + Feature catalog (17/10)

**File:** `src/reddit_sna/benchmarks/community_table.py`

Cơ chế sinh nhãn (ghi rõ để truy vết):

1. Mỗi community có trạng thái ẩn: `size`, `density`, `reciprocity`, `mu`, `g_prev`.
2. Mỗi tháng: `g = mu + 0.5 * g_prev + N(0, 0.12)`.
3. Thứ tự ưu tiên nhãn: dissolve → split → merge → (grow/shrink/stable theo g so với growth_threshold=0.15).
4. `label_noise=0.05`: 5% dòng được gán nhãn ngẫu nhiên.
5. Feature tại `t` chỉ dùng thông tin ≤ t: không có `growth_target`, `size_{t+1}`.
6. `size_tm1` được ghi **trước** khi `_update_size` thay đổi kích thước.
7. `community_id` là hoán vị local mỗi tháng — không có lineage.
8. Tháng feature cuối (2017-12) có `label` rỗng.

**Lỗi đã sửa (17/10):** `size_tm1` bị gán sau `_update_size` nên `size_tm1 == size_t` và `growth_rate` luôn bằng 0. Sửa bằng `old_size = st.size` trước khi gọi `_update_size`. Test hồi quy `test_size_tm1_follows_prev_label` kiểm tra: `prev_label=grow` thì `size_t > size_tm1`, `stable` thì bằng nhau, `shrink/merge/split` thì không lớn hơn.

**Bảng thống kê run `prediction-demo-002` (seed=42, n_months=36):**

| Thông tin | Giá trị |
|---|---|
| Tổng dòng bảng | 1570 |
| Labelled (label != rỗng) | 1524 |
| Train (label_month 2015-02..2016-12) | 1000 |
| Validation (label_month 2017-01..2017-06) | 263 |
| Test (label_month 2017-07..2017-12) | 261 |
| Empty label (feature_month 2017-12) | 46 |

Phân bố nhãn: stable=775, grow=253, shrink=232, merge=103, dissolve=89, split=72.

### M3 — B1 Majority + Persistence (17/10)

**File:** `src/reddit_sna/models/majority_persistence.py`

- `fit_majority(train)` — lớp phổ biến nhất; hòa thì theo thứ tự `list(Event)`.
- `predict_majority(model, samples)` — y_pred = majority_class, used_fallback=False.
- `predict_persistence(model, samples)` — y_pred = prev_label; thiếu thì fallback Majority, used_fallback=True.

**Kết quả từ `prediction-demo-002` (1524 dòng gộp train+validation+test, chỉ là số sơ bộ):**

| Model | Accuracy | Macro-F1 | used_fallback |
|---|---|---|---|
| B1 Majority | 775/1524 = 50.85% | 0.1124 | 0 |
| B1 Persistence | 751/1524 = 49.28% | 0.2724 | 131/1524 |
| B4 Logistic Reg. | 540/1524 = 35.43% | 0.2510 | 257/1524 |

B1 Majority accuracy 50.85% vì lớp `stable` chiếm 50.9% số dòng có nhãn. Macro-F1 = 0.1124 vì 5 lớp còn lại có recall bằng 0.

**Per-class B1 Majority:**

| Lớp | Đúng/Tổng | Recall |
|---|---|---|
| stable | 775/775 | 1.000 |
| grow | 0/253 | 0.000 |
| shrink | 0/232 | 0.000 |
| merge | 0/103 | 0.000 |
| split | 0/72 | 0.000 |
| dissolve | 0/89 | 0.000 |

**Per-class B1 Persistence:**

| Lớp | Đúng/Tổng | Recall | F1 |
|---|---|---|---|
| stable | 535/775 | 0.690 | 0.645 |
| grow | 109/253 | 0.431 | 0.439 |
| shrink | 95/232 | 0.409 | 0.416 |
| merge | 8/103 | 0.078 | 0.078 |
| split | 4/72 | 0.056 | 0.056 |
| dissolve | 0/89 | 0.000 | 0.000 |

Persistence macro-F1 = 0.2724 > Majority (0.1124): Persistence khai thác tính quán tính của nhãn.
`dissolve` recall = 0: community đã dissolve thì không xuất hiện ở tháng sau nên không có dòng nào có `prev_label=dissolve`.
Fallback (age=0, không có `prev_label`): 131/1524 = 8.6% số dòng.

### M4 — B4 Logistic Regression (17/10)

**File:** `src/reddit_sna/models/logistic_regression.py`

- Features: `size_t`, `size_tm1`, `size_tm2`, `age_months`, `growth_rate`.
- `StandardScaler` fit chỉ trên train. `LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, solver="lbfgs", random_state=seed)`.
- Thiếu bất kỳ feature nào thì fallback Majority, `used_fallback=True`.
- Lưu `model_B4.joblib` + `baseline_config.json`.

**Lỗi đã sửa:** scikit-learn 1.9.1 bỏ tham số `multi_class` nên đã xóa khỏi `B4Config`.

**Per-class B4 Logistic Regression:**

| Lớp | Đúng/Tổng | Recall | F1 |
|---|---|---|---|
| stable | 326/775 | 0.421 | 0.485 |
| grow | 82/253 | 0.324 | 0.357 |
| shrink | 98/232 | 0.422 | 0.346 |
| merge | 8/103 | 0.078 | 0.053 |
| split | 19/72 | 0.264 | 0.180 |
| dissolve | 7/89 | 0.079 | 0.084 |
| **Macro-F1** | | | **0.2510** |

B4 macro-F1 = 0.2510 < B1 Persistence (0.2724). Nguyên nhân có thể: 16.9% số dòng phải fallback (257/1524, chủ yếu age 0–1 vì thiếu `size_tm1`/`size_tm2`), B4 không dùng `prev_label`, và các lớp hiếm merge/dissolve ít mẫu. Đây là giả thuyết, chưa tách riêng từng nguyên nhân.
Cột proba: 1267/1267 dòng không fallback có tổng `proba_*` ≈ 1.0 (kiểm tra bởi `test_b4_proba_columns_populated`).

**Ví dụ sai ở tháng đầu (không có lịch sử nên fallback Majority), từ `predictions.csv` của `prediction-demo-002`:**

| Model | feature_month | community_id | y_true | y_pred | Lý do |
|---|---|---|---|---|---|
| B1_majority | 2015-01 | c0025 | shrink | stable | Majority luôn dự đoán stable (lớp đa số) |
| B1_majority | 2015-01 | c0030 | grow | stable | Tương tự |
| B1_persistence | 2015-01 | c0025 | shrink | stable | age=0, không có prev_label nên fallback Majority |
| B1_persistence | 2015-01 | c0004 | grow | stable | Tương tự |
| B4_logreg | 2015-01 | c0025 | shrink | stable | Thiếu size_tm1/growth_rate nên fallback Majority |

Các ví dụ này đều là trường hợp fallback ở tháng đầu. Chưa phân tích lỗi của các dòng không fallback.

### M5 — Pipeline prediction.py (17/10)

**File:** `src/reddit_sna/pipelines/prediction.py`

Luồng:
1. `_stage_table`: sinh `samples.csv` + `feature_catalog.csv`.
2. `_basic_temporal_split`: chia train/validation/test tạm thời (sẽ thay bằng `assign_temporal_split` của Anh).
3. `_stage_baselines`: fit B1/B4 chỉ trên train → `predictions.csv`, `baseline_config.json`, `model_B4.joblib`.
4. `_stage_evaluation`: stub → `evaluation_notes.md` (Lan Anh thay bằng bản thật).
5. `manifest.json`: status=`complete_through_baselines`, seed, git, thư viện, stage_status, artifact_hashes.

**Lỗi đã sửa:**
- Cột `proba_*` bị rơi khi ghép predictions → thêm `proba_*` vào `merge_cols`.
- `except ValueError` nuốt lỗi B4 → bỏ, để `ValueError` truyền lên.
- `status="complete"` khi evaluation còn là stub → đổi thành `"complete_through_baselines"`.

Output của `prediction-demo-002`:
```
  [table] Generated 1570 rows -> D:\reddit-community-evolution\artifacts\prediction\prediction-demo-002\samples.csv
  [baselines] Wrote 4572 prediction rows -> predictions.csv
  [evaluation] stub wrote evaluation_notes.md (Lan Anh's stage pending merge)

[prediction] Pipeline complete_through_baselines -> D:\reddit-community-evolution\artifacts\prediction\prediction-demo-002
```

### Tests (17/10)

Output của `python -m unittest discover -s tests -v`:
```
Ran 201 tests in 70.943s
FAILED (failures=2)
```

2 FAIL đều từ `integration.test_cli.CliTests.test_unimplemented_runs_fail_without_producing_artifacts` (pipeline='prediction'):
- Test mong đợi pipeline `prediction` chưa implement (exit code 3, không tạo `artifacts/`).
- Pipeline `prediction` đã chạy được nên trả về exit 0 và tạo `artifacts/`.
- `tests/integration/test_cli.py` không thuộc phần của Trâm nên không sửa; cần nhóm trưởng cập nhật test này.

Tests của Trâm (tất cả PASS):

| File | Số test | Kết quả |
|---|---|---|
| `test_community_table.py` | 20 | PASS |
| `test_majority_persistence.py` | 12 | PASS |
| `test_logistic_regression.py` | 9 | PASS |
| `test_samples_mini_fixture.py` | 6 | PASS |
| `test_prediction_pipeline.py` | 6 | PASS |

### M6 — Progress log (17/10)

File này.

---

## Fixture `tests/fixtures/prediction/samples_mini.csv`

Sinh từ `generate_community_table(42)`, không viết tay. Script: `tests/fixtures/prediction/make_samples_mini.py`.
55 dòng, đủ 6 lớp, trải đủ train / validation / test, có dòng không có lịch sử (age 0) và 8 dòng nhãn rỗng (feature_month 2017-12).
`test_samples_mini_fixture.py` kiểm tra schema, độ phủ ba split và `test_rows_are_real_generator_output` (từng dòng khớp generator).

---

## Phần chưa làm (đúng phạm vi)

- B2 (Random Forest): Phúc.
- B5 (Structural Gradient Boosting): Phúc.
- HeTCo: Thanh.
- Features thật từ Reddit: Thanh.
- `_stage_evaluation`: Lan Anh; hiện là stub.
- Macro-F1 trên test split riêng: chưa đo — cần `_stage_evaluation` của Anh.

---

## Câu hỏi nghiên cứu

> Baseline B1/B4 đạt macro-F1 bao nhiêu trên dữ liệu synthetic? Điểm này làm tham chiếu cho mô hình phức tạp hơn.

Kết quả sơ bộ (1524 dòng gộp, chưa tách test):

| Model | Macro-F1 | Accuracy |
|---|---|---|
| B1 Majority | 0.1124 | 50.85% |
| B1 Persistence | 0.2724 | 49.28% |
| B4 Logistic Regression | 0.2510 | 35.43% |

Dữ liệu synthetic — không phản ánh khả năng dự báo trên Reddit thật.

---

## Kế hoạch (18–21/10)

| Ngày | Việc |
|---|---|
| 18/10 | Nhận `assign_temporal_split` từ Anh; thay `_basic_temporal_split`; chạy lại |
| 19/10 | Edge-case, impute NaN so với fallback |
| 20/10 | Code freeze; soạn slide |
| 21/10 | Chạy chính thức, lưu log/seed/env |
| 22/10 | Trình bày |