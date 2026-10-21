# PLAN RIÊNG — TRÂM (tuần 1): bảng tổng hợp + B1 + B4 + pipeline `prediction`

Đọc kèm `01_PLAN_TUAN1_TRAM_ANH.md` — **§3 là hợp đồng đã chốt, không thay đổi**. File này là spec để agent code từng module nhỏ; mỗi module = một commit (code + test cùng commit). Nhánh: **`feat/tram-week1-baselines`**.

**Phạm vi (đúng PHAN-CONG):** sinh bảng community–tháng tổng hợp (lịch sử, features, nhãn, seed tái lập) + mô tả cơ chế sinh nhãn · B1 Majority/Persistence + fallback · B4 Logistic Regression · dùng split của Anh, **chỉ fit trên tập học** · xuất predictions từng mẫu · cấu hình/model.
**Ngoài phạm vi:** B2/B5 (Phúc), HeTCo/GED/features thật (Thanh), tracker (Đăng), split/metrics (Anh), dữ liệu Reddit, detector.

Môi trường: `.\.venv\Scripts\python.exe` (sklearn 1.9.1, pandas 3.0.6, numpy 2.5.4). Test bằng **unittest**: `& .\.venv\Scripts\python.exe -m unittest discover -s tests -v`.

## Sự thật đã biết từ `contracts.py` (đừng đoán khác)

`SCHEMA_VERSION = 1`; `Event` (StrEnum, thứ tự: stable, grow, shrink, merge, split, dissolve); `next_month(month)`; `SampleKey(reference_id, feature_month, community_id: str)`; `CommunitySample(key, label_month, label: Event, features: Mapping[str, float | None])` (features **chỉ số**); `Prediction(key, label_month, model, y_true: Event, y_pred: Event)`. Community ID **local theo snapshot**. Chỉ **import** từ `contracts.py`, không sửa, không định nghĩa lại `Event`/`next_month`. `pyproject.toml` hiện `dependencies = []`, không có pandas/sklearn/numpy trong extra nào. **Không sửa `pyproject.toml`** (tránh conflict, tính sau); pandas/scikit-learn/numpy đã cài thẳng vào venv của Trâm.

---

## M0 — Recon (không code sản phẩm)

Đọc: `config.py`, `artifacts.py`, `cli.py`, `pipelines/prediction.py` (stub?), `pipelines/preparation.py` (mẫu manifest/provenance), `configs/prediction.toml`, vài test có sẵn (kiểu import/fixture), `.gitignore`, `git status` + nhánh hiện tại, `reports/contribution_log.csv` (chỉ xem header). Báo cáo ngắn: API reserve run/ghi manifest, hàm nào `cli.py` đang tham chiếu trong `prediction.py`, `prediction.toml` có gì, cli có import `pipelines.prediction` lúc import không (nếu có thì import pandas/sklearn **lazy** trong hàm). Mâu thuẫn plan–code → theo `contracts.py` > md gốc > plan; ghi vào `reports/tram/progress.md` và báo Trâm.

## M1 — Generator `benchmarks/community_table.py`

```python
@dataclass(frozen=True)
class TableParams:
    reference_id: str = "synthetic-v1"
    first_month: str = "2015-01"
    n_months: int = 36              # 2015-01 … 2017-12
    n_initial: int = 40
    birth_rate: float = 3.0         # Poisson / tháng
    growth_threshold: float = 0.15
    label_noise: float = 0.05
    min_size: int = 3

SAMPLE_COLUMNS: tuple[str, ...]     # đúng 14 cột §3.1 file 01, đúng thứ tự
def generate_community_table(seed: int, params: TableParams = TableParams()) -> pd.DataFrame
def feature_catalog() -> pd.DataFrame      # §3.1 file 01: feature,dtype,source,window,available_at,allowed_models,note
def write_table(table, catalog, out_dir) -> dict[str, Path]    # samples.csv, feature_catalog.csv (UTF-8, \n)
def read_table(path) -> pd.DataFrame        # dtype tường minh: community_id str; size_*/age_months Int64; còn lại float64
```

**Cơ chế sinh nhãn** (docstring đầu module + ghi vào `README_DEMO.md`): mỗi community có trạng thái ẩn (kích thước, `density`, `reciprocity`, xu hướng `mu` cố định khi sinh, tăng trưởng tháng trước). Mỗi tháng:
1. `g = mu + 0.5·g_prev + N(0, 0.12)` (có quán tính → Persistence và lịch sử kích thước có tín hiệu).
2. **Thứ tự ưu tiên cố định:** `dissolve` (xác suất tăng khi nhóm nhỏ và đang co) → `split` (tăng theo kích thước) → `merge` (tăng khi nhóm nhỏ, density thấp) → còn lại theo `g`: `> +θ` grow, `< −θ` shrink, ngược lại stable.
3. Với xác suất `label_noise`, thay nhãn bằng lớp khác (mô phỏng nhiễu tracker).
4. Cập nhật kích thước theo sự kiện; community mới sinh theo `birth_rate`; `dissolve` thì ngừng sinh dòng.
5. Feature tại t chỉ dùng thông tin ≤ t. **Không** đưa `g` của t→t+1, size t+1, retention t→t+1 vào bất kỳ cột nào.

**Yêu cầu:** deterministic theo `seed` (`np.random.default_rng(seed)`); `community_id` dạng `c0000` **hoán vị local mỗi tháng**, không lưu lineage; community mới có lịch sử rỗng (`size_tm1/tm2`, `growth_rate`, `prev_label`, `retention_prev`); **tháng feature cuối (2017-12) có `label` rỗng**; bảng ~1.000–3.000 dòng; lớp hiếm (merge/split/dissolve) khoảng 5–10% mỗi lớp; hàm tự kiểm tra support tối thiểu mỗi lớp (≥ 15) trong khoảng label-month train mặc định (2015-02…2016-12), thiếu thì `raise ValueError` rõ ràng. Mức nhiễu/tham số chốt một lần, **không chỉnh theo điểm test**.

**Test `tests/unit/test_community_table.py`:** cùng seed → bảng và hash CSV y hệt, khác seed → khác; đúng 14 cột đúng thứ tự; khóa duy nhất; `label_month == next_month(feature_month)`; `label` ∈ `Event` hoặc rỗng chỉ ở tháng cuối; `growth_rate` tính lại từ `size_t/size_tm1` khớp; không cột lạ ngoài catalog; đủ 6 lớp trong khoảng train; **round-trip contract:** mọi dòng có label dựng được `SampleKey` + `CommunitySample` (features = cột số, NaN→None) không lỗi; ghi rồi `read_table` ra đúng dtype.
**Fixture:** `tests/fixtures/prediction/samples_mini.csv` (~60 dòng, đủ 6 lớp, có dòng thiếu lịch sử, có dòng `label` rỗng, 14 cột đúng thứ tự). **Đẩy trước 12h trưa 17/10.**

## M2 — Feature catalog (trong M1, không đụng `features/`)

`prev_label`→`B1_persistence`; `size_t,size_tm1,size_tm2,age_months,growth_rate`→`B4_logreg`; `retention_prev,density,reciprocity`→`reserved`; `available_at` ∈ `t|t-1|t-2`, không bao giờ `t+1`. Test: cột feature của bảng ⊆ catalog.

## M3 — B1 `models/majority_persistence.py`

```python
def fit_majority(train: pd.DataFrame) -> MajorityModel       # lớp phổ biến nhất trong `label` của TRAIN; hòa → theo thứ tự list(Event)
def predict_majority(model, samples) -> pd.DataFrame         # khóa + y_pred + used_fallback=False
def predict_persistence(model, samples) -> pd.DataFrame      # y_pred = prev_label; thiếu → majority, used_fallback=True
```
Test: majority = lớp phổ biến nhất **của train** (đổi nhãn test không đổi kết quả); persistence lặp `prev_label`; thiếu → fallback + cờ; train rỗng → lỗi rõ; hòa phá theo thứ tự `Event`.

## M4 — B4 `models/logistic_regression.py`

- `B4_FEATURES = ("size_t","size_tm1","size_tm2","age_months","growth_rate")` (đúng Proposal).
- `StandardScaler` **fit trên train** + `LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=seed)`. Siêu tham số cố định trong `B4Config`, lưu `baseline_config.json`; không chỉnh theo test (nếu chọn C thì chỉ dùng validation và ghi lại).
- Thiếu bất kỳ feature nào → **fallback Majority**, `used_fallback=True` (không impute từ test).
- `fit_logreg` raise `ValueError` rõ ràng nếu train < 2 lớp; lưu `missing_train_classes` (lớp không có trong train thì B4 không bao giờ dự đoán).
- `predict_logreg` → `y_pred` + `proba_<event>` cho 6 lớp (lớp vắng trong train = 0).
- Lưu `model_B4.joblib` trong thư mục run.
**Test:** `scaler.mean_` khớp trung bình train; train 1 lớp → ValueError; fallback đúng dòng thiếu feature; cùng seed → cùng dự đoán; proba cộng = 1; predict **không đọc** cột `label` của test; đổi nhãn test không đổi hệ số.

## M5 — Pipeline `pipelines/prediction.py` + `configs/prediction.toml`

`prediction.toml` chỉ có key được phép; đường dẫn tương đối theo thư mục TOML; không cần input Reddit. **Giữ nguyên tên/chữ ký hàm mà `cli.py` tham chiếu** (nếu có). Thêm `main(argv)` + `if __name__ == "__main__"` để chạy:
```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config configs/prediction.toml --run-id prediction-demo-001
```
**Luồng một run** (run-id mới, dùng cơ chế reserve của `artifacts.py`; không đụng `cli.py`):
1. `generate_community_table` → `samples.csv`, `feature_catalog.csv`
2. Anh: `check_samples` → `assert_samples_ok`; `assign_temporal_split` → `split.csv`, `split_summary.csv`
3. Fit B1/B4 **chỉ trên train** → `predictions.csv` (§3.3 file 01, kiểm tra từng dòng dựng được `Prediction`), `baseline_config.json`, `model_B4.joblib`
4. Anh: stage đánh giá → `metrics.csv`, `per_class.csv`, `confusion_*.csv`, `evaluation_notes.md`
5. `manifest.json`: config/seed, hash input–output, phiên bản thư viện, git revision + dirty, trạng thái từng stage, thời gian (peak memory không đo → null), `data_kind: "synthetic"`, `table_schema: "prediction-table-v1"` — mirror cách `preparation.py`.

Cấu trúc code: `run(...)` gọi `_stage_table`, `_stage_baselines` (Trâm) và `_stage_evaluation` (Anh sở hữu). Trước khi nhánh Anh có mặt: stub **trong file test**; sau đó thay bằng hàm thật. Không import pipeline khác, không import CLI.
**Test `tests/integration/test_prediction_pipeline.py`:** chạy trọn một run trong thư mục tạm; đủ file; cùng seed → hash `samples.csv` và `predictions.csv` y hệt; chạy lại cùng run-id bị từ chối; khóa predictions khớp split; đổi nhãn test không đổi tham số fit.

## M6 — Tiến độ và log (theo PHAN-CONG §4)

- `reports/tram/progress.md`: việc đã làm, đường dẫn code/artifact, lỗi, kế hoạch tiếp, **ví dụ lỗi** (vài mẫu B1/B4 đoán sai và vì sao), phần chưa làm, đoạn nội dung cho notebook (câu hỏi → đầu vào → protocol → đối chứng → kết quả → phản biện) để Anh gộp.
- `reports/contribution_log.csv`: đọc header rồi **chỉ thêm dòng việc thật** của Trâm; không sửa dòng người khác.

---

## Câu cần trả lời khi trình bày 22/10

1. Vì sao dữ liệu tổng hợp, nhãn sinh thế nào, vì sao điểm không nói gì về Reddit.
2. Vì sao split theo tháng nhãn và fit chỉ trên train; test nào chứng minh không rò.
3. Majority / Persistence / LR khác gì; khi nào fallback.
4. Lớp nào thiếu ở train/test và xử lý ra sao (macro-F1 trên support > 0).
5. Phần nào chưa làm (B2/B5, HeTCo, features thật) và vì sao không phải lỗi.

## Definition of Done

- [ ] M0–M6 xong; `unittest discover` pass; không sửa file ngoài danh sách (kể cả `pyproject.toml`).
- [ ] `git status` không có artifact/.venv/joblib/CSV lớn được stage.
- [ ] Một lệnh chạy hết pipeline với run-id mới; cùng seed → bảng/predictions trùng hash.
- [ ] Mọi mô tả ghi rõ **synthetic**.
