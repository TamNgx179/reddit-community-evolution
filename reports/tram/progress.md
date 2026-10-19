# Tiến độ & bàn giao Trâm — Tuần 1

> **Dữ liệu:** SYNTHETIC (tổng hợp), bộ `synthetic-v1`, seed 42.
> Mọi số trong tài liệu này đọc từ `artifacts/prediction/week1-merged-001/`.

---

## 0. Tóm tắt

- Trâm triển khai bảng mẫu tổng hợp, B1 Majority, B1 Persistence và B4 Logistic Regression; Anh triển khai split, đánh giá và integration.
- Macro-F1 trên **TEST** (n=261): **B1_majority = 0.1125**, **B1_persistence = 0.2557**, **B4_logreg = 0.2160**.
- Đáng chú ý: B4_logreg thấp hơn B1_persistence 0.0397 điểm trên test (giải thích ở §8 và §6).
- Giới hạn chính: dữ liệu synthetic; chỉ 3 baseline; lớp `split` và `dissolve` recall = 0 với B1_persistence trên test.
- Trạng thái review: `pending_review` (chưa có reviewer xác nhận).

---

## 1. Phạm vi & phân công

### Việc của Trâm (đã hoàn thành trong run `week1-merged-001`)

| Module | File |
|---|---|
| Generator bảng mẫu | `src/reddit_sna/benchmarks/community_table.py` |
| B1 Majority + Persistence | `src/reddit_sna/models/majority_persistence.py` |
| B4 Logistic Regression | `src/reddit_sna/models/logistic_regression.py` |
| Pipeline (table + baselines stages) | `src/reddit_sna/pipelines/prediction.py` |
| Unit tests Trâm | `tests/unit/test_community_table.py`, `test_majority_persistence.py`, `test_logistic_regression.py` |
| Fixtures | `tests/fixtures/prediction/samples_mini.csv`, `make_samples_mini.py` |
| Integration test | `tests/integration/test_prediction_pipeline.py` |
| Fixture test | `tests/unit/test_samples_mini_fixture.py` |

### Việc của Anh (đã merge vào `week1-merged-001`)

| Module | File |
|---|---|
| Temporal split | `src/reddit_sna/evaluation/splits.py` |
| Kiểm tra mẫu | `src/reddit_sna/evaluation/sample_checks.py` |
| Metrics + confusion | `src/reddit_sna/evaluation/metrics.py` |
| Leaky fixture (negative control) | `tests/fixtures/prediction/samples_leaky.csv` |
| Unit tests Anh | `tests/unit/test_splits.py`, `test_sample_checks.py`, `test_metrics.py` |
| Báo cáo + guide | `reports/anh/progress.md`, `reports/prediction-week1/GUIDE_DOC_KET_QUA.md` |

### Việc của người khác (chưa làm trong tuần 1 — đúng phạm vi)

- **Phúc:** B2 Random Forest, B5 Structural Gradient Boosting.
- **Thanh:** HeTCo, features thật từ Reddit.
- **Tâm:** snapshot Reddit pilot, detector multislice/consensus.
- **Đăng:** Jaccard tracker, leakage bootstrap.

---

## 2. Dữ liệu synthetic

### Cơ chế sinh nhãn (trích docstring `community_table.py`)

1. Mỗi community có trạng thái ẩn: `size`, `density`, `reciprocity`, `mu` (xu hướng tăng trưởng cố định), `g_prev`.
2. Mỗi tháng: `g = mu + 0.5 * g_prev + N(0, 0.12)` (momentum — Persistence và lịch sử size mang tín hiệu).
3. Thứ tự ưu tiên nhãn: dissolve (xác suất tăng khi nhỏ và co rút) → split (tăng khi lớn) → merge (nhỏ, density thấp) → theo g: > +theta → grow, < -theta → shrink, else stable.
4. `label_noise = 0.05`: 5% dòng được gán nhãn ngẫu nhiên.
5. Feature tại `t` **chỉ dùng thông tin ≤ t**: `growth_target`, `size_{t+1}`, `retention t→t+1` **không bao giờ được ghi**.
6. `community_id` là hoán vị local mỗi tháng — không có lineage qua các tháng; không dùng làm feature.
7. Tháng feature cuối (2017-12) có `label` rỗng (chưa quan sát successor).

**Tham số cố định** (trong `TableParams` — không chỉnh theo điểm test):
- seed = 42, n_months = 36 (2015-01 → 2017-12), birth_rate Poisson/tháng, growth_threshold θ = 0.15.

### Thống kê từ `samples.csv`

| Thông tin | Giá trị |
|---|---|
| Tổng dòng | 1570 |
| Dòng có nhãn (`label` ≠ rỗng) | 1524 |
| Dòng nhãn rỗng (feature_month = 2017-12) | 46 |

**Phân bố nhãn (1524 dòng có nhãn):**

| stable | grow | shrink | merge | dissolve | split |
|---|---|---|---|---|---|
| 775 | 253 | 232 | 103 | 89 | 72 |

---

## 3. Chia dữ liệu & kiểm tra mẫu

### Quy tắc chia theo `label_month`

- Chia **toàn bộ theo label_month**; một label-month thuộc đúng một tập; không cắt theo số dòng.
- Quan sát 2015-01 → 2017-12 (36 tháng) → label_month 2015-02 → 2017-12 (35 tháng).
- 46 dòng nhãn rỗng (feature_month 2017-12) bị loại và đếm.

### Bảng `split_summary.csv`

| split | n_samples | n_label_months | n_stable | n_grow | n_shrink | n_merge | n_split | n_dissolve |
|---|---|---|---|---|---|---|---|---|
| train | 1000 | 23 | 500 | 165 | 160 | 65 | 52 | 58 |
| validation | 263 | 6 | 142 | 42 | 35 | 16 | 11 | 17 |
| test | 261 | 6 | 133 | 46 | 37 | 22 | 9 | 14 |
| unlabeled_dropped | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Kết quả `check_samples` (16 kiểm tra — tất cả PASS)

| check | status |
|---|---|
| sample_keys_present | PASS |
| unique_sample_keys | PASS |
| label_month_follows_feature_month | PASS |
| labels_valid | PASS |
| previous_labels_valid | PASS |
| catalog_schema | PASS |
| catalog_available_at_valid | PASS |
| features_in_catalog | PASS |
| no_unexpected_columns | PASS |
| no_t_plus_1_features | PASS |
| numeric_values_finite | PASS |
| numeric_ranges_valid | PASS |
| train_class_support | PASS (6 lớp) |
| split_values_valid | PASS |
| split_keys_are_labelled_samples | PASS |
| temporal_order_no_overlap | PASS (train < validation < test) |

---

## 4. Ba mô hình baseline

### Cấu hình từ `baseline_config.json`

**B1_majority:**
- Lớp phổ biến nhất trong train; hòa thì theo thứ tự `list(Event)`.
- Fit trên train; predict = majority_class cho mọi mẫu; `used_fallback = False`.

**B1_persistence:**
- Dự đoán `prev_label` (sự kiện t-1→t, đã biết tại t).
- Fallback sang Majority khi `prev_label` rỗng (age=0 hoặc chưa đủ lịch sử); `used_fallback = True`.

**B4_logreg** (cấu hình từ file):

| Tham số | Giá trị |
|---|---|
| features | size_t, size_tm1, size_tm2, age_months, growth_rate |
| C | 1.0 |
| class_weight | balanced |
| max_iter | 1000 |
| solver | lbfgs |
| seed | 42 |
| missing_train_classes | [] (tất cả 6 lớp có trong train) |

`StandardScaler` fit **chỉ trên train**; transform áp lên validation và test.
Fallback sang Majority khi bất kỳ feature nào là NaN; `used_fallback = True`.

> **Quy tắc cứng:** không dùng validation/test để chỉnh bất kỳ siêu tham số nào.

---

## 5. Kết quả

### Chỉ số trên validation và test (kết quả chính)

| Model | Split | n | macro_f1 | macro_f1_six | balanced_acc | n_fallback | fallback_rate |
|---|---|---|---|---|---|---|---|
| B1_majority | validation | 263 | 0.1169 | 0.1169 | 0.1667 | 0 | 0.00% |
| B1_majority | test | 261 | 0.1125 | 0.1125 | 0.1667 | 0 | 0.00% |
| B1_persistence | validation | 263 | 0.2575 | 0.2575 | 0.2643 | 20 | 7.60% |
| B1_persistence | test | 261 | **0.2557** | 0.2557 | 0.2586 | 13 | 4.98% |
| B4_logreg | validation | 263 | 0.2291 | 0.2291 | 0.2324 | 39 | 14.83% |
| B4_logreg | test | 261 | **0.2160** | 0.2160 | 0.2155 | 30 | 11.49% |

> Trên split train (in-sample): B1_majority=0.1111, B1_persistence=0.2791, B4_logreg=0.2618. **Không dùng để kết luận** — chỉ ghi để theo dõi; mô hình được fit trên chính tập này.

> `macro_f1 = macro_f1_six` vì n_classes_present = 6 (tất cả 6 lớp có support > 0 trên mỗi split).

### Per-class trên TEST

**B1_majority:**

| label | precision | recall | f1 | support |
|---|---|---|---|---|
| stable | 0.5096 | 1.0000 | 0.6751 | 133 |
| grow | 0.0000 | 0.0000 | 0.0000 | 46 |
| shrink | 0.0000 | 0.0000 | 0.0000 | 37 |
| merge | 0.0000 | 0.0000 | 0.0000 | 22 |
| split | 0.0000 | 0.0000 | 0.0000 | 9 |
| dissolve | 0.0000 | 0.0000 | 0.0000 | 14 |

**B1_persistence:**

| label | precision | recall | f1 | support |
|---|---|---|---|---|
| stable | 0.5855 | 0.6692 | 0.6246 | 133 |
| grow | 0.4524 | 0.4130 | 0.4318 | 46 |
| shrink | 0.4000 | 0.3784 | 0.3889 | 37 |
| merge | 0.0870 | 0.0909 | 0.0889 | 22 |
| split | 0.0000 | 0.0000 | 0.0000 | 9 |
| dissolve | 0.0000 | 0.0000 | 0.0000 | 14 |

**B4_logreg:**

| label | precision | recall | f1 | support |
|---|---|---|---|---|
| stable | 0.5556 | 0.5263 | 0.5405 | 133 |
| grow | 0.3415 | 0.3043 | 0.3218 | 46 |
| shrink | 0.2321 | 0.3514 | 0.2796 | 37 |
| merge | 0.0000 | 0.0000 | 0.0000 | 22 |
| split | 0.2500 | 0.1111 | 0.1538 | 9 |
| dissolve | 0.0000 | 0.0000 | 0.0000 | 14 |

### Nhận xét ma trận nhầm lẫn trên test

**B1_persistence:** Hay nhầm sang `stable` (89/133 stable đúng; 21 grow và 21 shrink bị đoán thành stable). `split` và `dissolve` không có dòng nào dự đoán đúng (recall = 0) — community đã dissolve không còn xuất hiện tháng sau nên không có `prev_label = dissolve`; split/dissolve rất ít mẫu (9 và 14).

**B4_logreg:** Nhầm nhiều sang `stable` và `shrink`. `merge` và `dissolve` recall = 0 — lớp hiếm (22 và 14 mẫu) với feature numeric khó phân biệt. B4 có fallback 11.49% (30/261 dòng test thiếu feature) nên một phần dự đoán là Majority.

---

## 6. Phân tích lỗi

### B1_persistence — 3 ví dụ đầu (không fallback, y_true ≠ y_pred, test, sắp theo feature_month, community_id)

| feature_month | community_id | y_true | y_pred | prev_label | size_t | size_tm1 | growth_rate |
|---|---|---|---|---|---|---|---|
| 2017-06 | c0001 | merge | shrink | shrink | 5 | 7 | -0.2857 |
| 2017-06 | c0003 | shrink | stable | stable | 9 | 9 | 0.0000 |
| 2017-06 | c0009 | dissolve | stable | stable | 3 | 3 | 0.0000 |

**Giải thích:**
- Dòng 1 (merge dự đoán shrink): `prev_label=shrink` → model dự đoán shrink, nhưng thực tế là merge. **Giả thuyết:** community nhỏ (size=5, đang co rút) gặp sự kiện merge bất ngờ không được báo trước bởi `prev_label`.
- Dòng 2 (shrink dự đoán stable): `prev_label=stable`, growth_rate=0 → model dự đoán stable, thực tế shrink. **Giả thuyết:** sự kiện shrink xuất hiện đột ngột mà không có tín hiệu trong `prev_label`.
- Dòng 3 (dissolve dự đoán stable): `prev_label=stable`, size=3 (rất nhỏ) → model dự đoán stable, thực tế dissolve. **Giả thuyết:** community nhỏ với lịch sử stable có thể dissolve đột ngột — `prev_label` không đủ để nhận biết.

### B4_logreg — 3 ví dụ đầu (không fallback, y_true ≠ y_pred, test)

| feature_month | community_id | y_true | y_pred | prev_label | size_t | size_tm1 | growth_rate |
|---|---|---|---|---|---|---|---|
| 2017-06 | c0000 | stable | shrink | stable | 10 | 10 | 0.0000 |
| 2017-06 | c0003 | shrink | stable | stable | 9 | 9 | 0.0000 |
| 2017-06 | c0004 | shrink | stable | shrink | 3 | 3 | 0.0000 |

**Giải thích:**
- Dòng 1 (stable dự đoán shrink): growth_rate=0, size không đổi → B4 dự đoán shrink nhầm. **Giả thuyết:** `class_weight="balanced"` làm B4 quá nhạy với shrink/grow, dẫn đến dự đoán sai khi feature tương đương stable và shrink.
- Dòng 2 (shrink dự đoán stable): growth_rate=0, size=9→9 → B4 dự đoán stable thay vì shrink. **Giả thuyết:** B4 không dùng `prev_label`, nên không thấy tín hiệu xu hướng shrink từ lịch sử nhãn.
- Dòng 3 (shrink dự đoán stable): `prev_label=shrink` nhưng B4 không dùng, growth_rate=0 → đoán stable. **Giả thuyết:** nếu B4 dùng thêm `prev_label`, có thể nhận biết xu hướng shrink tốt hơn.

---

## 7. Kiểm chứng

### Unit tests

- **Tổng:** 253 tests | **Pass:** 251 | **Fail:** 2
- Dòng cuối: `Ran 253 tests in 142.689s` / `FAILED (failures=2)`

**2 FAIL từ `integration.test_cli`:**
```
FAIL: test_unimplemented_runs_fail_without_producing_artifacts
      (integration.test_cli.CliTests) (pipeline='prediction')
  AssertionError: 0 != 3    ← mong exit code 3, nhận được 0
  AssertionError: True is not false  ← mong artifacts không được tạo, nhưng đã có
```
Test mong đợi pipeline `prediction` chưa implement (exit code 3, không tạo artifact). Pipeline đã chạy được nên trả về exit 0 và tạo artifact. `tests/integration/test_cli.py` không thuộc phần của Trâm — không sửa; cần nhóm trưởng cập nhật test.

**Tests của Trâm (tất cả PASS):**

| File | Số test | Kết quả |
|---|---|---|
| `test_community_table.py` | 20 | PASS |
| `test_majority_persistence.py` | 12 | PASS |
| `test_logistic_regression.py` | 9 | PASS |
| `test_samples_mini_fixture.py` | 6 | PASS |
| `test_prediction_pipeline.py` | 6 | PASS |

### Manifest

| Trường | Giá trị |
|---|---|
| status | `complete_through_baselines` |
| git revision | `c23425c69260ec66a6d2f8cb36f6b6049accc8bc` |
| git dirty | `false` |
| seed | 42 |
| python_version | 3.12.10 |
| numpy | 2.5.4 |
| pandas | 3.0.6 |
| scikit-learn | 1.9.1 |
| stage_status | table: complete, split: complete, baselines: complete, evaluation: complete |

### Danh sách artifact (8 ký tự đầu sha256)

| Artifact | sha256[:8] |
|---|---|
| baseline_config.json | a5591fd2 |
| confusion_B1_majority_test.csv | bad26255 |
| confusion_B1_majority_train.csv | 25a01a83 |
| confusion_B1_majority_validation.csv | aa737101 |
| confusion_B1_persistence_test.csv | bb9ad002 |
| confusion_B1_persistence_train.csv | ab6f68f4 |
| confusion_B1_persistence_validation.csv | cda30537 |
| confusion_B4_logreg_test.csv | 2e9f4e33 |
| confusion_B4_logreg_train.csv | 6d368fe5 |
| confusion_B4_logreg_validation.csv | 6839276c |
| evaluation_notes.md | 154dbabc |
| feature_catalog.csv | 2598c464 |
| metrics.csv | f9484e8e |
| model_B4.joblib | ba70093c |
| per_class.csv | c2940cce |
| predictions.csv | fc34fe1a |
| samples.csv | 80cd4a95 |
| split.csv | e133b1fc |
| split_summary.csv | dc061ac1 |

---

## 8. Giới hạn (trung thực)

1. **Dữ liệu synthetic:** Kết quả trên bảng tổng hợp `synthetic-v1`. Không phản ánh khả năng dự báo trên Reddit thật.
2. **Chỉ 3 baseline:** B1_majority, B1_persistence, B4_logreg. B2 (Random Forest) và B5 (Gradient Boosting) chưa có — thuộc Phúc (tuần 2+).
3. **Tập test nhỏ:** n_test = 261 mẫu (6 label_month). Khoảng tin cậy không được tính.
4. **Lớp recall = 0 trên test:**
   - B1_majority: grow, shrink, merge, split, dissolve (chỉ dự đoán stable).
   - B1_persistence: split (9 mẫu), dissolve (14 mẫu) — không có `prev_label` tương ứng.
   - B4_logreg: merge (22 mẫu), dissolve (14 mẫu) — lớp hiếm, feature numeric không phân biệt được.
5. **B4 không dùng `prev_label`:** Feature catalog ghi `prev_label` chỉ dành cho B1_persistence. B4 dùng 5 cột số. Đây là thiết kế có chủ ý để B4 độc lập với lịch sử nhãn.
6. **Fallback cao ở train (B4):** 188/1000 = 18.8% dòng train thiếu `size_tm1`/`size_tm2` (age = 0–1). Các dòng này dùng Majority thay vì LogisticRegression khi predict.
7. **Chưa có:** B2/B5, HeTCo, features thật từ Reddit, bootstrap confidence interval, ablation.

---

## 9. Cách tái lập

```powershell
# Cài đặt (nếu chưa có)
& .\.venv\Scripts\python.exe -m pip install numpy pandas scikit-learn

# Chạy pipeline (sinh run mới)
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction `
    --config configs/prediction.toml `
    --run-id week1-merged-001
```

> **Lưu ý:** `artifacts/prediction/week1-merged-001/` đã tồn tại — pipeline sẽ từ chối ghi đè. Dùng run-id mới để chạy lại.

**Tham số cố định:**
- RUN_ID: `week1-merged-001`
- Seed: 42 (từ `configs/prediction.toml`)
- Python: 3.12.10 | numpy: 2.5.4 | pandas: 3.0.6 | scikit-learn: 1.9.1
- Git revision: `c23425c69260ec66a6d2f8cb36f6b6049accc8bc` (dirty=false)

**Vị trí artifact:** `artifacts/prediction/week1-merged-001/`

---

## 10. Bàn giao & việc tiếp theo

### Đã bàn giao

| Artifact | Người nhận |
|---|---|
| `predictions.csv` (B1/B4 trên train/val/test) | Anh (đã dùng để evaluate) |
| `samples.csv`, `feature_catalog.csv` | Anh (đã dùng để check_samples) |
| `model_B4.joblib`, `baseline_config.json` | Lưu artifact — Trâm tái lập |

### Việc tiếp theo (theo PHAN-CONG)

| Người | Việc tuần 2+ |
|---|---|
| Trâm | Hoàn thiện B1/B4; nhận B5 từ Phúc; chạy baseline trên features thật khi Thanh bàn giao |
| Anh | Hoàn thiện macro-F1/confusion, bảng kết quả, mẫu báo cáo kết quả |
| Phúc | Bàn giao B2/B5 và cấu hình cho Trâm |
| Thanh | Bàn giao features/nhãn pilot cho Trâm |

---

## 11. Phụ lục — Kịch bản trình bày 22/10 (≤ 5 phút)

### Thứ tự trình bày

1. **Đề tài và phạm vi tuần 1** (30 giây): B.6 How Online Communities Change Over Time. Tuần 1: bảng tổng hợp → split → baseline → evaluation. Dữ liệu **synthetic**, không phải Reddit.

2. **Dữ liệu synthetic và split** (1 phút): 1570 dòng, 36 tháng, 6 sự kiện. Chia theo label_month: train 23 tháng/1000 dòng, val 6 tháng/263 dòng, test 6 tháng/261 dòng. 46 dòng cuối không có nhãn bị loại. 16 kiểm tra PASS.

3. **Ba baseline** (1 phút): B1_majority (lớp đa số = stable), B1_persistence (lặp prev_label; fallback 4.98% test), B4_logreg (5 features số; StandardScaler fit chỉ trên train; class_weight=balanced; fallback 11.49% test).

4. **Kết quả trên TEST** (1 phút): macro-F1: B1_majority=**0.1125**, B1_persistence=**0.2557**, B4_logreg=**0.2160**. B4 thấp hơn Persistence 0.040 điểm. Lớp hiếm (split=9, dissolve=14) recall = 0 ở Persistence và B4.

5. **Kiểm chứng** (30 giây): 253 tests, 251 PASS, 2 FAIL từ `test_cli` (pipeline `prediction` đã chạy được, test mong chưa implement — cần nhóm trưởng cập nhật). Manifest git dirty=false, seed=42.

6. **Giới hạn và bước tiếp** (1 phút): Kết quả synthetic, không thay thế Reddit. Chưa có B2/B5/HeTCo. Test nhỏ (261 mẫu). Từ tuần 2: nhận B5 từ Phúc, features thật từ Thanh.

---

### 5 câu hỏi thầy có thể hỏi

**Q1: Vì sao dùng dữ liệu synthetic?**
> Tuần 1 mỗi cặp hoàn thành đường chạy độc lập không cần artifact nhóm khác (PHAN-CONG §2). Features và nhãn thật từ Thanh sẽ có từ tuần 2. Dữ liệu synthetic đảm bảo pipeline chạy đúng và reproducible; không claim là kết quả Reddit.

**Q2: Vì sao chọn macro-F1 làm chỉ số chính?**
> Bài toán có 6 lớp với phân bố mất cân bằng (stable chiếm 50.9%). Macro-F1 coi mỗi lớp ngang nhau, phù hợp khi quan tâm đến cả lớp hiếm (dissolve, split). Tính trên lớp có support > 0; zero_division=0; quy ước này được chốt trước khi chạy test (01_PLAN §3.5).

**Q3: Vì sao chia theo `label_month` thay vì số dòng?**
> Đảm bảo không rò rỉ thời gian: mọi mẫu trong train có label_month ≤ 2016-12, validation ≤ 2017-06, test ≤ 2017-12. Cắt theo số dòng có thể đưa mẫu cùng tháng vào cả train lẫn test. Kiểm tra `temporal_order_no_overlap` đã PASS.

**Q4: Vì sao B4 (Logistic Regression) chưa hơn B1_persistence?**
> Trên test B4 thấp hơn 0.040. Có thể do: (1) B4 không dùng `prev_label` trong khi `prev_label` mang tín hiệu quán tính mạnh từ cơ chế sinh dữ liệu; (2) B4 fallback 11.49% dòng test (thiếu feature); (3) lớp hiếm merge/dissolve khó học từ 5 features số. **Đây là giả thuyết** — chưa tách riêng từng nguyên nhân.

**Q5: Làm sao đảm bảo không rò rỉ dữ liệu tương lai?**
> Ba tầng bảo vệ: (1) Feature catalog ghi `available_at ∈ {t, t-1, t-2}` — kiểm tra `no_t_plus_1_features` PASS; (2) `StandardScaler` fit **chỉ trên train**; (3) `check_samples` bắt leaky fixture (negative control `samples_leaky.csv` — FAIL đúng chỗ). Split temporal không overlap được xác nhận bởi `temporal_order_no_overlap` PASS.