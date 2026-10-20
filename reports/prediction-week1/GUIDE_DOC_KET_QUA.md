# Guide to Evaluation Results

## 1. Mục đích và phạm vi

Tài liệu này hướng dẫn chạy prediction prototype và đọc artifact đánh giá Week 1. Run tham chiếu sử dụng dữ liệu **synthetic**, không phải dữ liệu Reddit thật. Prototype minh họa luồng bảng community-month → temporal split → baseline prediction → evaluation; không nên mô tả nó là pipeline Reddit end-to-end.

Run được dùng làm tham chiếu trong tài liệu là `lan-demo-final-20261020`. Mọi số liệu bên dưới đều thuộc run này, trừ khi có ghi rõ khác. Không trộn metrics, manifest hoặc revision từ các run khác nhau.

## 2. Chạy pipeline

Chạy từ repository root bằng virtual environment của dự án. Mỗi lần chạy cần một run ID mới chưa tồn tại:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction `
  --config .\configs\prediction.toml `
  --run-id <unique-run-id>
```

Không tái sử dụng run ID đã có và không ghi đè artifact cũ. Kết quả dự kiến nằm tại `artifacts/prediction/<run_id>/`. Nếu lệnh lỗi, đọc traceback và manifest của đúng run; không dùng một thư mục artifact cũ làm bằng chứng rằng lần chạy mới thành công.

## 3. Hợp đồng dữ liệu

Theo kế hoạch Week 1, `samples.csv` có 14 cột:

`reference_id`, `feature_month`, `community_id`, `label_month`, `label`, `prev_label`, `size_t`, `size_tm1`, `size_tm2`, `age_months`, `growth_rate`, `retention_prev`, `density`, `reciprocity`.

- `label_month` phải bằng `next_month(feature_month)`.
- Nhãn sử dụng các giá trị `Event` được khai báo trong `contracts.py`.
- Dòng không có nhãn, chẳng hạn tháng cuối không có tháng kế tiếp, phải được thống kê riêng và loại khỏi supervised evaluation.
- `community_id` là định danh cục bộ trong tháng; không dùng làm feature và không mặc định là identity xuyên tháng.
- `prev_label` là lịch sử riêng cho B1 Persistence, không phải numeric feature.
- Các feature số được mô tả trong kế hoạch gồm `size_t`, `size_tm1`, `size_tm2`, `age_months`, `growth_rate`, `retention_prev`, `density`, `reciprocity`.
- Không dùng thông tin tương lai, chẳng hạn retention từ `t` sang `t+1`, làm feature tại thời điểm `t`.

Các module cần dùng `Event` và `next_month()` từ `contracts.py`, không sao chép định nghĩa hợp đồng sang module đánh giá hoặc notebook.

## 4. Artifact đầu ra

| File | Ý nghĩa |
|---|---|
| `samples.csv` | Bảng community-month synthetic |
| `feature_catalog.csv` | Nguồn, cửa sổ thời gian, thời điểm khả dụng và model được phép dùng cho từng feature |
| `split.csv` | Khóa mẫu, tháng và split cho các mẫu có nhãn |
| `split_summary.csv` | Số mẫu, số `label_month`, phân bố nhãn theo split và dòng `unlabeled_dropped` |
| `predictions.csv` | Dự đoán long format, một dòng cho mỗi sample/model |
| `metrics.csv` | Metrics tổng hợp theo model/split |
| `per_class.csv` | Precision, recall, F1 và support theo lớp |
| `confusion_<model>_<split>.csv` | Ma trận nhầm lẫn theo model/split, nếu được tạo |
| `evaluation_notes.md` | Quy ước đánh giá, lớp thiếu và mẫu không nhãn bị loại |
| `manifest.json` | Trạng thái run, seed, revision và metadata |
| `baseline_config.json`, `model_B4.joblib` | Chỉ tồn tại nếu implementation của run tạo các file này |

Hợp đồng `predictions.csv` gồm các cột:

`reference_id`, `feature_month`, `community_id`, `label_month`, `model`, `y_true`, `y_pred`, `used_fallback`, `proba_stable`, `proba_grow`, `proba_shrink`, `proba_merge`, `proba_split`, `proba_dissolve`.

Theo kế hoạch, `predictions.csv` không có cột `split`; nối với `split.csv` bằng các khóa phù hợp khi cần phân tích theo split. Các cột probability được sử dụng cho B4 theo hợp đồng hiện tại.

## 5. Temporal split và leakage

Split theo toàn bộ `label_month`, không chia ngẫu nhiên từng dòng:

- Train: `2015-02` đến `2016-12` — 23 tháng.
- Validation: `2017-01` đến `2017-06` — 6 tháng.
- Test: `2017-07` đến `2017-12` — 6 tháng.
- Mẫu không nhãn bị loại khỏi supervised evaluation và được đếm riêng.

Số liệu trong run `lan-demo-final-20261020`:

| Split | Số mẫu | Số tháng nhãn |
|---|---:|---:|
| Train | 1.000 | 23 |
| Validation | 263 | 6 |
| Test | 261 | 6 |
| `unlabeled_dropped` | 46 | 0 |

`tests/fixtures/prediction/samples_leaky.csv` là negative-control fixture có chủ đích để kiểm tra phát hiện leakage; không dùng fixture này để train hoặc đánh giá mô hình. Các kiểm tra làm giảm rủi ro đã biết nhưng không chứng minh mọi dạng leakage đều đã bị loại bỏ.

## 6. Cách đọc metrics

- `macro_f1`: trung bình F1 trên các lớp có support lớn hơn 0 trong `y_true` của model/split đang xét; quy ước `zero_division=0`.
- `macro_f1_six`: trung bình F1 trên đủ sáu event class; lớp không có F1 xác định được tính bằng 0 theo quy ước.
- `balanced_accuracy`: trung bình recall trên các lớp có support trong `y_true`.
- `n`: số mẫu được đánh giá.
- `n_classes_present`: số lớp xuất hiện trong nhãn thật của split.

Đọc `metrics.csv` cùng `per_class.csv` và confusion matrix. Metric tổng hợp cao hơn không có nghĩa mô hình nhận diện tốt mọi lớp; cần kiểm tra support, recall và các kiểu nhầm lẫn. Cách tính cuối cùng phải khớp implementation trong `evaluation/metrics.py`.

## 7. Kết quả tham chiếu

Manifest của run `lan-demo-final-20261020` ghi:

- `status`: `complete_through_baselines`
- `data_kind`: `synthetic`
- `seed`: `42`
- `git revision`: `696cbb61da2faebb75f06a701afee943fe0199c0`
- `git dirty`: `false`
- Các stage `table`, `split`, `baselines`, `evaluation`: `complete`

### Metrics validation và test

| Model | Split | n | Macro-F1 | Macro-F1 (6 lớp) | Balanced accuracy |
|---|---|---:|---:|---:|---:|
| B1 Majority | validation | 263 | 0.1169 | 0.1169 | 0.1667 |
| B1 Majority | test | 261 | 0.1125 | 0.1125 | 0.1667 |
| B1 Persistence | validation | 263 | 0.2575 | 0.2575 | 0.2643 |
| B1 Persistence | test | 261 | 0.2557 | 0.2557 | 0.2586 |
| B4 Logistic Regression | validation | 263 | 0.2291 | 0.2291 | 0.2324 |
| B4 Logistic Regression | test | 261 | 0.2160 | 0.2160 | 0.2155 |

Ở run này, cả sáu lớp có support nên `macro_f1` và `macro_f1_six` trùng nhau. Không mặc định điều đó đúng cho các run khác. B1 Persistence có macro-F1 cao nhất trong ba baseline trên test của run synthetic này; kết quả không phải bằng chứng về hiệu quả trên Reddit thật.

## 8. Kiểm thử và notebook

Lần chạy kiểm thử được cung cấp dùng lệnh:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả:

```text
Ran 253 tests in 94.716s

OK
```

Notebook `notebooks/prediction/00_research_plan.ipynb` được để xử lý sau và không thuộc phạm vi cập nhật tài liệu này. Theo kiến trúc, đây là template nghiên cứu, không phải entry point thay thế pipeline. Việc rà soát notebook và lựa chọn run trong notebook sẽ được thực hiện riêng.

## 9. Giới hạn và bước tiếp theo

- Dữ liệu synthetic; chưa đánh giá trên Reddit thật.
- Run tham chiếu chỉ gồm B1 Majority, B1 Persistence và B4 Logistic Regression.
- B2 Random Forest, B5 Gradient Boosting, HeTCo và feature Reddit thật nằm ngoài phạm vi run này.
- Review chéo schema, temporal split, feature availability, fallback và metrics trước khi dùng kết quả trong báo cáo nghiên cứu.
- Dùng run ID mới khi chạy lại và chỉ lấy metadata/metrics từ cùng một thư mục run.