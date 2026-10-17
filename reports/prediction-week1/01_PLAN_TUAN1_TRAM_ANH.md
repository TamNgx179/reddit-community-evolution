# PLAN TUẦN 1 — Cặp Trâm – Lan Anh (prototype baseline dự báo + đánh giá)

**Hạn:** code freeze **20/10** (T3) → 21/10 chạy lại sạch + slide → **báo cáo 22/10** (T5).
**Pipeline:** `prediction` · **Config:** `configs/prediction.toml` · **Notebook:** `notebooks/prediction/00_research_plan.ipynb` · **Nhánh Trâm:** `feat/tram-week1-baselines` · **Nhánh Anh (gợi ý cùng kiểu):** `feat/anh-week1-evaluation`

## 0. Nguồn luật

Thứ bậc: `ARCHITECTURE.md` / `README.md` / `PHAN-CONG-SNA-8-TUAN.md` / `Proposal V2.md` (luật) > `src/reddit_sna/contracts.py` (tên field) > file này. Mọi thông số kỹ thuật trong §3 **đã chốt**; không còn mục chờ xác nhận. Muốn đổi thì hai người đổi cùng lúc theo §3.7.

**Tên cố định theo md (không tự đặt):**

| Thứ | Tên | Nguồn |
|---|---|---|
| Config | `configs/prediction.toml` | README, PHAN-CONG |
| Notebook | `notebooks/prediction/00_research_plan.ipynb` | README, PHAN-CONG |
| Pipeline | `src/reddit_sna/pipelines/prediction.py` (Trâm–Anh) | PHAN-CONG |
| Bảng mẫu / baseline / chỉ số | `benchmarks/` (Trâm), `models/` (Trâm: B1/B4), `evaluation/` (Anh) | PHAN-CONG |
| Test | `tests/unit`, `tests/integration`, `tests/fixtures` | PHAN-CONG |
| Output | `artifacts/prediction/<run_id>/` | ARCHITECTURE |
| Ghi tiến độ | thư mục mang tên mình (PHAN-CONG §4) → `reports/tram/`, `reports/anh/` | PHAN-CONG |

Tên **file module mới** (vd `community_table.py`) do hai bạn đặt theo chức năng — ARCHITECTURE cho phép ("filenames describe responsibilities").

**Có code chung một file không?** Không. Mỗi người module riêng (§4). Chỉ có **hai** chỗ dùng chung: `pipelines/prediction.py` (mỗi người sở hữu hàm stage của mình) và notebook (một người sửa tại một thời điểm).

## 1. Mục tiêu tuần 1

Một đường chạy **độc lập** (không dùng artifact của Tâm–Thanh hay Phúc–Đăng):

```
bảng community–tháng TỔNG HỢP → split theo tháng nhãn → B1/B4 → predictions → evaluation
```

- Dữ liệu **tổng hợp**; mọi bảng/slide ghi rõ "synthetic, không phải kết quả Reddit".
- Điểm chỉ chứng minh baseline + evaluation **chạy đúng**; không chứng minh khả năng dự báo, không so với hai nhóm kia.
- Train phải có ≥ 2 lớp để chạy Logistic Regression; ghi rõ lớp thiếu và quy ước macro-F1.

## 2. Phân vai

| | **Trâm** | **Lan Anh** |
|---|---|---|
| Nhiệm vụ | Sinh bảng mẫu tổng hợp, B1 Majority/Persistence, B4 Logistic Regression, chạy baseline, xuất predictions | Split theo tháng nhãn, kiểm tra khóa/số lớp/thời điểm biết feature, chỉ số + confusion matrix, hướng dẫn đọc kết quả, báo cáo giới hạn |
| Đầu ra cá nhân | Script sinh bảng, bảng dữ liệu, code baseline, cấu hình/model, predictions B1/B4 | Split, code đánh giá, bảng điểm baseline, confusion matrix, báo cáo giới hạn, lệnh demo |

## 3. ĐÃ CHỐT — Hợp đồng bàn giao

### 3.0 Luồng

```
Trâm: generate_community_table ─► samples.csv + feature_catalog.csv ──H1──► Anh
Anh : check_samples + assign_temporal_split ─► split.csv           ──H2──► Trâm
Trâm: fit B1/B4 CHỈ trên train ─► predictions.csv                  ──H3──► Anh
Anh : evaluate ─► metrics / per_class / confusion / notes          ──H4──► cả hai (slide)
```

Không ai phải chờ ai: Trâm đẩy **fixture ~60 dòng ngày 17/10**; Anh code trên đó. Anh gửi **hàm split ngày 18/10**; trước đó Trâm dùng split tạm viết trong file test của mình (không đưa vào `src`).

### 3.1 H1 — `samples.csv` (Trâm → Anh)

Một dòng = một community tại tháng feature `t`; nhãn = sự kiện `t → t+1`. Tên cột bám `contracts.py` (`SampleKey`, `CommunitySample`). **Đúng 14 cột, đúng thứ tự:**

| # | Cột | Kiểu / giá trị | Ghi chú |
|---|---|---|---|
| 1 | `reference_id` | str, `synthetic-v1` | khóa mẫu |
| 2 | `feature_month` | `YYYY-MM` | khóa mẫu; hợp lệ theo `next_month()` |
| 3 | `community_id` | **str** `c0000`, `c0001`… | khóa mẫu; **local trong tháng**, không mang danh tính qua tháng, không dùng làm feature |
| 4 | `label_month` | `YYYY-MM` | = `next_month(feature_month)`; split dựa **chỉ** vào cột này |
| 5 | `label` | 1 trong `Event`: `stable, grow, shrink, merge, split, dissolve`; **rỗng** chỉ ở tháng feature cuối (chưa quan sát successor) | khớp `CommunitySample.label` |
| 6 | `prev_label` | `Event` hoặc rỗng | sự kiện chuyển t−1→t, đã biết tại t; cột lịch sử dạng chữ **ngoài** `features` (vì `features` chỉ nhận số); chỉ Persistence dùng |
| 7 | `size_t` | Int64 | |
| 8 | `size_tm1` | Int64, rỗng nếu chưa đủ lịch sử | |
| 9 | `size_tm2` | Int64, rỗng nếu chưa đủ lịch sử | |
| 10 | `age_months` | Int64 | số tháng tồn tại tới t |
| 11 | `growth_rate` | float64 | (size_t − size_tm1)/size_tm1; rỗng nếu thiếu t−1 |
| 12 | `retention_prev` | float64 | giữ chân **t−1→t** (quá khứ); retention t→t+1 là target-derived, **cấm** có trong bảng |
| 13 | `density` | float64 | thuộc tính cấu trúc tại t (B4 tuần 1 không dùng) |
| 14 | `reciprocity` | float64 | như trên |

Quy tắc: khóa (1–3) duy nhất; sự kiện/tháng/khóa dùng `Event` và `next_month` từ `contracts.py`, **không định nghĩa lại**; features dùng làm `CommunitySample.features` = các cột số 7–14 (NaN → `None`); dòng `label` rỗng **không** thành `CommunitySample` nên bị loại và đếm. CSV UTF-8, `\n`, đọc lại với `dtype` tường minh (`community_id` đọc là str).

`feature_catalog.csv` (một dòng/feature, gồm cột 6–14): `feature, dtype, source, window, available_at, allowed_models, note`. `available_at` ∈ `t`, `t-1`, `t-2` (không bao giờ `t+1`). `allowed_models`: `prev_label`→`B1_persistence`; `size_t, size_tm1, size_tm2, age_months, growth_rate`→`B4_logreg`; ba cột còn lại→`reserved` (cho mô hình sau).

### 3.2 H2 — split (Anh → Trâm)

- Chia theo **toàn bộ label-month**; một label-month thuộc đúng một tập; **không** cắt theo số dòng.
- Quan sát 2015-01…2017-12 (36 tháng) → label-month 2015-02…2017-12 (35 tháng):

| Tập | Label-month | Số tháng |
|---|---|---|
| `train` | 2015-02 … 2016-12 | 23 |
| `validation` | 2017-01 … 2017-06 | 6 |
| `test` | 2017-07 … 2017-12 | 6 |

- Dòng `label` rỗng (tháng feature cuối 2017-12) bị loại và **đếm**.
- **Giao diện (Anh, `evaluation/splits.py`):**
  ```python
  def assign_temporal_split(
      samples: pd.DataFrame,
      train_end: str = "2016-12",        # label_month cuối của train (gồm)
      validation_end: str = "2017-06",   # label_month cuối của validation (gồm)
  ) -> pd.DataFrame
  # Trả về: reference_id, feature_month, community_id, label_month, split
  # split ∈ {"train","validation","test"}; loại dòng label rỗng
  # ValueError: tháng sai định dạng, train_end >= validation_end, tập nào rỗng

  def summarize_split(samples: pd.DataFrame, split: pd.DataFrame) -> pd.DataFrame
  # Cột: split, n_samples, n_label_months, n_stable … n_dissolve; thêm dòng split="unlabeled_dropped"
  ```
- Artifact: `split.csv` (5 cột trên), `split_summary.csv`.
- Trâm **chỉ fit trên `train`**; không dùng test để chỉnh bất cứ gì; validation chỉ để chọn nếu cần và phải ghi lại.

### 3.3 H3 — `predictions.csv` (Trâm → Anh)

Dạng dài, một dòng/(mẫu, model), **đúng thứ tự cột:**
`reference_id, feature_month, community_id, label_month, model, y_true, y_pred, used_fallback, proba_stable, proba_grow, proba_shrink, proba_merge, proba_split, proba_dissolve`

- Bảy cột đầu = đúng field của `Prediction` (key làm phẳng). `y_true`/`y_pred` là giá trị `Event`.
- `model` ∈ `B1_majority`, `B1_persistence`, `B4_logreg`.
- `used_fallback` = True khi Persistence thiếu `prev_label` hoặc B4 thiếu feature (dùng Majority). `proba_*` chỉ có ở B4 (B1 để rỗng).
- Dự đoán cho **tất cả mẫu có nhãn** (train/validation/test); **không** có cột `split` (Anh join từ `split.csv`).
- Nghiệm thu: tập khóa khớp `split.csv`; mỗi (khóa, model) đúng một dòng; `y_pred` không rỗng và thuộc `Event`.

### 3.4 Hàm kiểm tra và đánh giá (Anh, `evaluation/`)

```python
# evaluation/sample_checks.py
def check_samples(samples, catalog, split=None) -> pd.DataFrame      # cột: check, status(PASS|FAIL), detail
def assert_samples_ok(report) -> None                                # raise SampleCheckError nếu có FAIL

# evaluation/metrics.py
def evaluate_predictions(predictions, split) -> dict[str, pd.DataFrame]   # keys: "metrics", "per_class"
def confusion_matrices(predictions, split) -> dict[tuple[str, str], pd.DataFrame]  # (model, split) -> ma trận 6x6 theo thứ tự list(Event)
```

`check_samples` kiểm tra tối thiểu: khóa duy nhất; `label_month == next_month(feature_month)`; `label` ∈ `Event` hoặc rỗng chỉ ở tháng cuối; cột feature ⊆ catalog; không `available_at == "t+1"`; không cột nào ngoài catalog + khóa + `label_month` + `label`; số lớp trong train ≥ 2 (nếu có split); nhận diện **fixture rò rỉ** `samples_leaky.csv` (negative control, Anh tạo).

### 3.5 H4 — kết quả đánh giá và quy ước macro-F1 (đã chốt)

- `macro_f1` (**chỉ số chính**) = trung bình F1 trên các lớp có **support > 0** trong `y_true` của (model, tập) đang đánh giá; `zero_division=0`.
- `macro_f1_six` (phụ) = trung bình F1 trên đủ 6 `Event`, `zero_division=0`.
- Lớp support = 0 **luôn liệt kê** trong `per_class.csv` (support 0) và `evaluation_notes.md`; không ép thành điểm đẹp. Lớp có support > 0 nhưng không được dự đoán → F1 = 0.
- Files: `metrics.csv` (`model, split, n, n_classes_present, macro_f1, macro_f1_six, balanced_accuracy`), `per_class.csv` (`model, split, label, precision, recall, f1, support`), `confusion_<model>_<split>.csv`, `evaluation_notes.md` (lớp thiếu, quy ước, số dòng bị loại, `data_kind: synthetic`).

### 3.6 Từ vựng chung

Tháng `YYYY-MM` (chuỗi); sự kiện = giá trị `Event` (chữ thường); `snake_case` cho cột/hàm, `UPPER_SNAKE` cho hằng; `tm1` = t−1, `tm2` = t−2; seed lấy từ `prediction.toml`, truyền tường minh, không `np.random.seed`.

### 3.7 Đổi schema

Đổi tên/cột/ý nghĩa ở §3.1–3.5 → nhắn người kia **trước khi sửa**; cập nhật fixture, test và mục này cùng một commit; ghi `table_schema: "prediction-table-v1"` (tăng v2…) trong manifest và `evaluation_notes.md`. Không sửa `contracts.py`.

## 4. Quy ước chống xung đột

**Sở hữu file** (mỗi file một người sửa):

| Trâm | Lan Anh |
|---|---|
| `src/reddit_sna/benchmarks/community_table.py` | `src/reddit_sna/evaluation/splits.py` |
| `src/reddit_sna/models/majority_persistence.py` | `src/reddit_sna/evaluation/sample_checks.py` |
| `src/reddit_sna/models/logistic_regression.py` | `src/reddit_sna/evaluation/metrics.py` |
| `src/reddit_sna/pipelines/prediction.py`: khung, `main`, stage sinh bảng + baseline | `pipelines/prediction.py`: **chỉ** hàm stage đánh giá (`_stage_evaluation`) và dòng gọi nó |
| `configs/prediction.toml` (chỉ key hợp lệ) | `tests/unit/test_splits.py`, `test_sample_checks.py`, `test_metrics.py` |
| `tests/unit/test_community_table.py`, `test_majority_persistence.py`, `test_logistic_regression.py` | `tests/fixtures/prediction/samples_leaky.csv` |
| `tests/fixtures/prediction/samples_mini.csv`, `tests/integration/test_prediction_pipeline.py` | `reports/anh/progress.md`, `reports/prediction-week1/GUIDE_DOC_KET_QUA.md`, `LIMITATIONS.md` |
| `reports/tram/progress.md` | `reports/prediction-week1/README_DEMO.md` (bản cuối) |

**Dùng chung — một người sửa tại một thời điểm:**
- `00_research_plan.ipynb`: JSON khó merge. Trâm viết phần dữ liệu + baseline thành đoạn trong `reports/tram/progress.md`; **Anh gộp vào notebook 19–20/10**, commit bản **không output** (bản chạy lưu cục bộ vào thư mục artifact mới); ô đầu in interpreter thật; Restart & Run All trước khi bàn giao; không sửa `sys.path`.
- `pipelines/prediction.py`: Trâm merge khung trước (18/10); Anh sửa hàm stage đánh giá trên nhánh của mình, không chạm phần khác. Giữ nguyên tên/chữ ký hàm mà `cli.py` đang tham chiếu (nếu có).
- `reports/contribution_log.csv`: mỗi người chỉ **thêm dòng** việc thật của mình, không sửa dòng người khác.

**Không sửa:** `pyproject.toml`, `contracts.py`, `config.py`, `artifacts.py`, `cli.py`, `README.md`, `ARCHITECTURE.md`, `PHAN-CONG-*.md`, `Proposal V2.md`, `data/`, `graphs/`, `detection/`, `tracking/`, `features/`, file không thuộc mình trong `benchmarks/` `models/` `evaluation/`, `pipelines/core.py`, `pipelines/detection_tracking.py`, config/notebook nhóm khác.

**Thư viện (KHÔNG sửa `pyproject.toml`, tránh conflict):** `pyproject.toml` hiện chưa khai báo pandas/scikit-learn/numpy; việc khai báo để tính sau. Mỗi người **tự cài vào venv của mình** để chạy và test:
```powershell
& .\.venv\Scripts\python.exe -m pip install numpy pandas scikit-learn
& .\.venv\Scripts\python.exe -c "import numpy, pandas, sklearn; print('Environment OK', numpy.__version__, pandas.__version__, sklearn.__version__)"
```
Trâm đã cài (numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1). **Lan Anh cần cài trước khi code**; nên dùng cùng phiên bản (pandas 3.x) để kết quả giống nhau, ghi phiên bản đang dùng vào `reports/anh/progress.md`.

**Git:** nhánh riêng mỗi người; code + test cùng commit; `git add` từng đường dẫn (không `git add -A`); review chéo trong cặp trước khi merge; không push `main`; không `reset --hard`/`clean`/force push.

**Config strict:** `prediction.toml` chỉ có `schema_version, pipeline, project_root, seed, input, output`. Tham số khác (số tháng, split, siêu tham số) là hằng/dataclass trong code. Mỗi lần chạy dùng **run-id mới**, ghi vào `artifacts/prediction/<run_id>/`, không ghi đè, không commit artifact.

**Lệnh demo (một lệnh, tuần 1):**
```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config configs/prediction.toml --run-id prediction-demo-001
```
(`cli.py` không thuộc phần của hai bạn; demo dùng entrypoint của module + notebook.)

## 5. Lịch

| Ngày | Trâm | Lan Anh | Điểm gặp nhau |
|---|---|---|---|
| **T7 17/10** | M0, M1 + **đẩy `samples_mini.csv` trước 12h trưa**, M3 (B1) | `sample_checks` + khung `splits`/`metrics` trên fixture | Fixture lên nhánh `feat/tram-week1-baselines` |
| **CN 18/10** | Bảng đầy đủ + catalog, M4 (B4), merge khung pipeline | **Gửi hàm `assign_temporal_split` trong ngày**; `metrics` + test | **Ghép lần 1** tối CN: pipeline chạy mini rồi full |
| **T2 19/10** | Edge-case (thiếu lớp, fallback), manifest, ví dụ lỗi | Leakage negative control, confusion, guide + limitations, gộp notebook | Review chéo PR |
| **T3 20/10** | **Freeze code.** Dry-run run-id mới; soạn kết quả + slide phần Trâm | Dry-run đánh giá; slide phần Anh | Hoàn thiện + bàn giao nội bộ |
| **T4 21/10** | Chạy chính thức run-id mới, lưu log/seed/env; tập nói | README_DEMO + lệnh demo, ghép slide | Chỉ sửa lỗi nghiêm trọng |
| **T5 22/10** | Trình bày phần Trâm | Trình bày phần Anh | |

## 6. Nghiệm thu (checklist PHAN-CONG)

- [ ] Đầu vào xác định; nguồn **synthetic** ghi rõ; cơ chế sinh nhãn được mô tả.
- [ ] Code + config của cả hai, một lệnh chạy trong `README_DEMO.md`.
- [ ] Chạy từ đầu đến evaluation, không nhập tay dự đoán, không xin artifact nhóm khác.
- [ ] Bảng kết quả B1/B4 trên train/validation/test, kiểm tra và **ví dụ lỗi**.
- [ ] Lưu seed, phiên bản môi trường, config, log, output trong `artifacts/prediction/<run_id>/`.
- [ ] Ghi rõ phần chưa làm (B2/B5, HeTCo, features thật, Reddit).
- [ ] Split theo label-month; fit chỉ trên train; negative control bắt được feature rò rỉ.
- [ ] `unittest discover` pass; `reports/contribution_log.csv` có dòng việc thật; mỗi người giải thích được code của mình.

## 7. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Train thiếu lớp | Generator kiểm tra support tối thiểu trong khoảng train; B4 báo lỗi rõ khi < 2 lớp; ghi `missing_train_classes` |
| Test thiếu lớp | Quy ước §3.5; liệt kê support = 0 |
| Bảng quá dễ/khó | Đặt mức nhiễu **một lần** trước khi chạy test, ghi trong docstring; không tinh chỉnh theo điểm test |
| Xung đột notebook / `prediction.py` | Quy tắc §4 |
| pandas 3 (dtype chuỗi mới, copy-on-write) | Khai báo dtype khi đọc CSV; tránh chained assignment |
| Lệch tên cột | Test integration đọc đúng schema §3; đổi schema theo §3.7 |

## 8. Tin nhắn gửi Lan Anh

> Anh ơi, mình chốt xong hết kỹ thuật tuần 1 rồi, Anh làm theo mục 3 trong file `reports/prediction-week1/01_PLAN_TUAN1_TRAM_ANH.md` là được:
> • **17/10 (trước 12h trưa):** Trâm đẩy `tests/fixtures/prediction/samples_mini.csv` (~60 dòng, 14 cột) lên nhánh `feat/tram-week1-baselines` để Anh code trên đó.
> • **18/10:** Anh gửi hàm `assign_temporal_split(samples, train_end="2016-12", validation_end="2017-06")` trong `evaluation/splits.py`; tối CN mình ghép chạy thử.
> • Split theo **tháng nhãn**: train 23 tháng, validation 6, test 6; không cắt theo số dòng; dòng chưa có nhãn thì loại và đếm.
> • Macro-F1 chính tính trên các lớp có **support > 0**; chỉ số phụ tính đủ 6 lớp.
> • **Nhớ cài 3 thư viện vào venv của Anh trước khi code:** `.\.venv\Scripts\python.exe -m pip install numpy pandas scikit-learn` (tụi mình không sửa pyproject nên mỗi người tự cài nha).
> • Muốn đổi tên cột/hàm thì nhắn Trâm trước nhé. Có gì chưa rõ cứ nhắn mình liền!
