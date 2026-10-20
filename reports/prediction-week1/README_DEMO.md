# Prediction Evaluation — Demo Guide

## 1. Tổng quan

Demo Week 1 minh họa luồng prototype:

`synthetic community-month table → sample checks / temporal split → B1/B4 baselines → evaluation`

Dữ liệu là synthetic, không phải dữ liệu Reddit thật. Demo kiểm tra các stage hiện có; không chứng minh hiệu quả dự báo trên Reddit và không phải pipeline Reddit end-to-end.

## 2. Yêu cầu

- Windows và PowerShell.
- Chạy lệnh từ repository root.
- Python environment tại `.venv`.
- Dependencies đã cài trong virtual environment của dự án.

Có thể kiểm tra nhanh môi trường:

```powershell
& .\.venv\Scripts\python.exe -c "import numpy, pandas, sklearn; print('Environment OK', numpy.__version__, pandas.__version__, sklearn.__version__)"
```

## 3. Chạy demo

Dùng run ID mới chưa tồn tại cho mỗi lần chạy:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction `
  --config .\configs\prediction.toml `
  --run-id <unique-run-id>
```

Không dùng lại run ID đã tồn tại và không ghi đè artifact cũ. Artifact được ghi dưới `artifacts/prediction/<run_id>/`. Nếu lệnh lỗi, kiểm tra traceback và manifest; không coi thư mục artifact cũ là bằng chứng cho lần chạy mới.

## 4. Các stage

1. Sinh bảng mẫu synthetic và `feature_catalog.csv`.
2. Kiểm tra schema, khóa, nhãn và feature availability.
3. Gán temporal split theo toàn bộ `label_month`.
4. Chạy B1 Majority, B1 Persistence và B4 Logistic Regression.
5. Kiểm tra predictions và liên kết với split.
6. Tạo metrics, per-class metrics, confusion matrices và evaluation notes.
7. Ghi metadata run vào `manifest.json`.

`complete_through_baselines` mô tả việc hoàn tất các stage hiện có của run. Trạng thái này không có nghĩa mọi mô hình dự kiến, tracking/features đầy đủ hoặc xử lý Reddit thật đã hoàn tất.

## 5. Artifact đầu ra

Thư mục đầu ra:

```text
artifacts/prediction/<run_id>/
```

Các file chính:

- `samples.csv`: mẫu community-month synthetic theo schema 14 cột trong kế hoạch.
- `feature_catalog.csv`: metadata feature, nguồn và thời điểm khả dụng.
- `split.csv`: khóa mẫu, tháng và split cho các mẫu có nhãn.
- `split_summary.csv`: số mẫu theo split, số `label_month`, phân bố nhãn và số mẫu không nhãn bị loại.
- `predictions.csv`: dự đoán long format, một dòng mỗi sample/model; ghép split từ `split.csv` khi cần.
- `baseline_config.json`, `model_B4.joblib`: chỉ có nếu implementation tạo các file này.
- `metrics.csv`: metrics theo model/split.
- `per_class.csv`: metrics theo lớp.
- `confusion_<model>_<split>.csv`: confusion matrices, nếu được tạo.
- `evaluation_notes.md`: quy ước đánh giá và ghi chú lớp thiếu/dòng bị loại.
- `manifest.json`: trạng thái, revision, seed và metadata run.

Các module đánh giá phải dùng `Event` và `next_month()` từ `contracts.py`. Reusable logic thuộc package; notebook nghiên cứu không thay thế entry point của pipeline.

Có thể đọc nhanh artifact của một run đã tồn tại bằng PowerShell:

```powershell
$run = ".\artifacts\prediction\<run-id>"

Get-Content "$run\manifest.json" -Encoding UTF8
Import-Csv "$run\split_summary.csv" | Format-Table -AutoSize
Import-Csv "$run\metrics.csv" | Format-Table -AutoSize
Import-Csv "$run\per_class.csv" | Format-Table -AutoSize
```

Thay `<run-id>` bằng ID thực tế. Đảm bảo mọi file được đọc từ cùng một thư mục run.

## 6. Temporal split và feature availability

Split theo toàn bộ `label_month`, không chia ngẫu nhiên từng dòng:

- Train: `2015-02` đến `2016-12` — 23 tháng.
- Validation: `2017-01` đến `2017-06` — 6 tháng.
- Test: `2017-07` đến `2017-12` — 6 tháng.
- Mẫu không nhãn bị loại và đếm riêng.

Số lượng của run tham chiếu `lan-demo-final-20261020`:

| Split | Số mẫu | Số tháng nhãn |
|---|---:|---:|
| Train | 1.000 | 23 |
| Validation | 263 | 6 |
| Test | 261 | 6 |
| `unlabeled_dropped` | 46 | 0 |

Feature số trong hợp đồng gồm `size_t`, `size_tm1`, `size_tm2`, `age_months`, `growth_rate`, `retention_prev`, `density`, `reciprocity`. `prev_label` là lịch sử riêng cho B1 Persistence, không phải numeric feature. `community_id` không phải feature và không khẳng định identity xuyên tháng. Không dùng thông tin tương lai làm feature. Fixture `tests/fixtures/prediction/samples_leaky.csv` chỉ dùng làm negative control để kiểm tra phát hiện leakage.

## 7. Kết quả tham chiếu

Run tham chiếu `lan-demo-final-20261020` có seed 42, revision `696cbb61da2faebb75f06a701afee943fe0199c0`, trạng thái `complete_through_baselines`; manifest ghi các stage table, split, baselines và evaluation đều hoàn thành.

| Model | Split | n | Macro-F1 | Balanced accuracy |
|---|---|---:|---:|---:|
| B1 Majority | validation | 263 | 0.1169 | 0.1667 |
| B1 Majority | test | 261 | 0.1125 | 0.1667 |
| B1 Persistence | validation | 263 | 0.2575 | 0.2643 |
| B1 Persistence | test | 261 | 0.2557 | 0.2586 |
| B4 Logistic Regression | validation | 263 | 0.2291 | 0.2324 |
| B4 Logistic Regression | test | 261 | 0.2160 | 0.2155 |

B1 Persistence có macro-F1 cao nhất trong ba baseline trên test của run synthetic này. Không diễn giải kết quả thành bằng chứng về hiệu quả trên Reddit thật.

## 8. Chạy test

Lệnh kiểm thử đã chạy:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả được cung cấp:

```text
Ran 253 tests in 94.716s

OK
```

Đây là kết quả của lần chạy được báo cáo. Nếu thay đổi source hoặc test, hãy chạy lại test trên working tree hiện tại và ghi nhận đúng kết quả.

## 9. Notebook nghiên cứu

`notebooks/prediction/00_research_plan.ipynb` ghi lại thiết kế nghiên cứu, bằng chứng đánh giá và giới hạn của prototype. Notebook hiện chọn run tham chiếu lan-demo-final-20261020. Đây là công cụ nghiên cứu, không thay thế entry point của pipeline; reusable logic vẫn thuộc src/reddit_sna.

## 10. Giới hạn và bước tiếp theo

- Dữ liệu synthetic; chưa đánh giá trên Reddit thật.
- Run tham chiếu gồm B1 Majority, B1 Persistence và B4 Logistic Regression.
- B2 Random Forest, B5 Gradient Boosting, HeTCo và feature Reddit thật nằm ngoài phạm vi run Week 1 này.
- Review chéo schema, split, feature availability, fallback và metrics trước khi dùng kết quả trong báo cáo nghiên cứu.
- Dùng run ID mới khi chạy lại và không trộn kết quả từ các run khác nhau.