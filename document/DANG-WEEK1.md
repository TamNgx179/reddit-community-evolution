# Báo cáo tuần 1 — Đăng

**Cặp:** Phúc–Đăng  
**Phạm vi:** Jaccard tracking và đánh giá detection/tracking trên benchmark tổng hợp  
**Ngày cập nhật:** 19/10/2026  
**Split đã chạy:** development và evaluation  
**Trạng thái config:** đã khóa trước khi mở evaluation

## 1. Mục tiêu

Tuần 1, phần việc của Đăng là:

1. Đọc và kiểm tra membership.
2. Triển khai Jaccard tracker.
3. Kiểm tra sáu sự kiện `stable`, `grow`, `shrink`, `merge`, `split`, `dissolve`.
4. Đánh giá event prediction bằng F1, support và confusion matrix.
5. Mapping community detector với truth bằng greedy one-to-one Jaccard.
6. Tạo artifact có provenance để Phúc ghép vào demo chung.

Phạm vi này dùng dữ liệu tổng hợp của Phúc, không phải kết quả Reddit thật.

## 2. Gói dữ liệu đã nhận và kiểm tra

Gói nhận:

```text
phuc-dang-week1-20261019-001.zip
```

SHA-256 thực tế:

```text
E1A611092A8273B30570ABDB4F6810EF9E07A0264AB07F0CE69CE4BCE3880A14
```

Lệnh consumer đã chạy:

```powershell
python -I -S .\consumer.py .\runs\development `
  --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e `
  --output .\check-development-001
```

Kết quả:

```text
Exit code: 0
status: complete
datasets: 18
snapshots: 36
snapshot_detector_runs: 108
```

Consumer đọc gói thành công, không phát hiện lỗi integrity hoặc thiếu artifact. Python đọc gói là `Python 3.14.4`, đáp ứng yêu cầu Python 3.11+.

## 3. Thay đổi code

### 3.1. Đọc membership nhiều tháng

Module:

- [tracking/membership.py](../src/reddit_sna/tracking/membership.py)

Đã hỗ trợ:

- Đọc một `membership.csv` chứa nhiều tháng.
- Kiểm tra header chính xác:

  ```text
  reference_id,month,community_id,user_id
  ```

- Kiểm tra một file chỉ chứa một `reference_id`.
- Kiểm tra dòng CSV thiếu cột hoặc giá trị rỗng.
- Gom membership theo tháng bằng `groups_by_month(...)`.
- Lấy riêng một snapshot bằng `groups_from_rows(..., month=...)`.
- Kiểm tra user kỳ vọng theo tháng khi caller cung cấp.

### 3.2. Jaccard tracker

Module:

- [tracking/jaccard.py](../src/reddit_sna/tracking/jaccard.py)

Quy tắc đã khóa cho development:

```text
Jaccard threshold = 0.30
size tolerance = 0.10
detector seed chính = 0
```

Event assignment:

- Không có target khi successor được quan sát: `dissolve`.
- Một source có nhiều target: `split`.
- Một target nhận nhiều source: `merge`.
- Tăng trên 10%: `grow`.
- Giảm dưới -10%: `shrink`.
- Còn lại: `stable`.
- Successor chưa được quan sát không bị gán `dissolve`.

Tracker giữ mọi link đạt ngưỡng, sắp xếp deterministic và trả diagnostics.

### 3.3. Evaluator và mapping

Module:

- [evaluation/tracking.py](../src/reddit_sna/evaluation/tracking.py)

Đã triển khai:

- Precision, recall, F1 và support từng event.
- Macro-F1 trên sáu nhãn cố định.
- Confusion matrix.
- Ghi nhận `__unmatched__`.
- Báo source truth chưa match.
- Báo prediction/detector source dư.
- Greedy one-to-one mapping truth–detector tại tháng nguồn.
- Project event detector về source truth sau mapping.

Truth không được đưa vào tracker để thay đổi event assignment; truth chỉ được dùng ở evaluator.

### 3.4. Xuất artifact

Module:

- [reporting/tracking_outputs.py](../src/reddit_sna/reporting/tracking_outputs.py)

Module này tạo run mới cho development, không sửa source run của Phúc, và ghi manifest hash cho các file output.

## 4. Kiểm thử code trước khi chạy dữ liệu thật

Lệnh đã chạy:

```powershell
& .\.venv\Scripts\python.exe -m unittest `
  tests.unit.test_jaccard_tracking -v
```

Kết quả:

```text
Ran 11 tests
OK
```

Các test bao phủ:

- Sáu event.
- Membership CSV nhiều tháng.
- Header sai thứ tự.
- Snapshot month selection.
- Successor chưa quan sát.
- Ambiguous split/many-to-many.
- Duplicate source.
- Missing prediction.
- Extra prediction source.
- Greedy mapping.
- Project detector events.

Compile và `git diff --check` cũng đã chạy thành công.

## 5. Kiểm tra đường A — tracker trên truth

### 5.1. Dataset thử nghiệm

Đã kiểm tra trước:

- `dev-grow-easy-g11`
- `dev-stable-easy-g11`

Kết quả `dev-grow-easy-g11`:

```text
A -> C = grow
K -> K = stable
links = A -> C, K -> K
event_match = True
link_match = True
```

Kết quả `dev-stable-easy-g11`:

```text
A -> C = stable
K -> K = stable
links = A -> C, K -> K
event_match = True
link_match = True
```

### 5.2. Batch development

Đã chạy truth tracker trên toàn bộ 18 development datasets.

Kết quả:

```text
completed = 18
failures = 0
```

Tất cả các event và links do tracker sinh ra đều khớp với truth:

| Event | Số dataset kiểm tra | Kết quả |
|---|---:|---|
| `stable` | 3 | 3/3 PASS |
| `grow` | 3 | 3/3 PASS |
| `shrink` | 3 | 3/3 PASS |
| `merge` | 3 | 3/3 PASS |
| `split` | 3 | 3/3 PASS |
| `dissolve` | 3 | 3/3 PASS |

Nhóm nền `K` được giữ lại và chấm như các source khác.

Kết luận đường A:

```text
18/18 dataset PASS
18/18 event sets khớp
18/18 link sets khớp
```

## 6. Kiểm tra đường B — detector seed 0

Đường B sử dụng membership detector seed 0, không dùng seed 1/2 làm kết quả chính.

Luồng:

```text
detector membership seed 0
    -> Jaccard tracker
    -> mapping detector–truth
    -> project event về truth source
    -> event metrics
```

Kết quả:

```text
completed = 18
failures = 0
mean matched coverage = 1.0
total unmatched truth = 0
total extra detector = 3
mean detector macro-F1 = 0.2561728395061728
```

Ba detector community dư xuất hiện ở:

```text
dev-split-easy-g11
dev-split-easy-g12
dev-split-easy-g13
```

Các source truth đều được mapping:

```text
matched coverage = 1.0
unmatched truth = 0
```

`dev-merge-easy-g11` có trường hợp many-to-many/ambiguous:

```text
links = 5
ambiguous sources = 2
detector macro-F1 = 0.16666666666666666
```

Đây là kết quả cần giữ để phân tích lỗi, không được sửa truth hoặc chọn seed khác để làm điểm cao hơn.

Coverage bằng 1.0 chỉ cho biết source truth có thể được mapping; không có nghĩa detector partition hoặc event prediction hoàn toàn đúng.

## 7. Artifact development

Artifact được tạo tại:

- [dang-week1-development-001](../artifacts/detection-tracking/dang-week1-development-001/)

Metadata:

- [metadata.json](../artifacts/detection-tracking/dang-week1-development-001/metadata.json)
- [manifest.json](../artifacts/detection-tracking/dang-week1-development-001/manifest.json)
- [tracker-config.json](../artifacts/detection-tracking/dang-week1-development-001/tracker-config.json)

Provenance:

```text
run_id = dang-week1-development-001
split = development
source_run = phuc-005-t05-development-001
detector_seed = 0
jaccard_threshold = 0.30
size_tolerance = 0.10
datasets = 18
input_manifest_sha256 = 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e
```

Cấu hình tracker/evaluator đã được khóa trước khi mở evaluation split. File
`tracker-config.json` ghi rõ ngưỡng, precedence, mapping, nhãn và kích thước
confusion matrix đã sử dụng trên development.

Mỗi dataset có hai nhóm output:

```text
truth_tracking/
    events.csv
    links.csv
    event_predictions.csv
    metrics.csv
    confusion_matrix.csv
    diagnostics.json

detector_tracking/
    events.csv
    links.csv
    source_mapping.csv
    event_predictions.csv
    metrics.csv
    confusion_matrix.csv
    diagnostics.json
    mapping_diagnostics.json
```

Kiểm tra cấu trúc:

```text
dataset directories = 18
source_mapping.csv = 18
manifest.json = present
metadata.json = present
```

Ví dụ artifact:

- [Grow truth metrics](../artifacts/detection-tracking/dang-week1-development-001/datasets/dev-grow-easy-g11/truth_tracking/metrics.csv)
- [Grow detector mapping](../artifacts/detection-tracking/dang-week1-development-001/datasets/dev-grow-easy-g11/detector_tracking/source_mapping.csv)
- [Split mapping diagnostics](../artifacts/detection-tracking/dang-week1-development-001/datasets/dev-split-easy-g11/detector_tracking/mapping_diagnostics.json)

## 8. Evaluation split sau khi khóa config

Sau khi ghi [tracker-config.json](../artifacts/detection-tracking/dang-week1-development-001/tracker-config.json),
evaluation được mở chỉ để đánh giá, không dùng để chọn lại threshold, precedence hoặc detector seed.

Receipt evaluation:

```text
source run = phuc-005-t06-evaluation-001
input manifest SHA-256 = e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c
consumer output = check-evaluation-dang-002
consumer exit code = 0
status = complete
datasets = 18
snapshots = 36
snapshot_detector_runs = 108
```

Artifact evaluation:

- [dang-week1-evaluation-001](../artifacts/detection-tracking/dang-week1-evaluation-001/)
- [evaluation metadata](../artifacts/detection-tracking/dang-week1-evaluation-001/metadata.json)
- [evaluation manifest](../artifacts/detection-tracking/dang-week1-evaluation-001/manifest.json)

Kết quả tổng hợp:

| Chỉ số | Development | Evaluation |
|---|---:|---:|
| Dataset hoàn tất | 18/18 | 18/18 |
| Truth tracker khớp truth events/links | 18/18 | 18/18 |
| Truth macro-F1 trung bình | 0.3055555555555556 | 0.3055555555555556 |
| Detector macro-F1 trung bình | 0.2561728395061728 | 0.2175925925925926 |
| Matched coverage trung bình | 1.0 | 1.0 |
| Tổng unmatched truth | 0 | 0 |
| Tổng detector community dư | 3 | 6 |

Evaluation giữ được coverage mapping và không có truth source bị unmatched, nhưng detector
macro-F1 giảm so với development. Vì vậy kết quả cho thấy chất lượng event prediction của
detector thay đổi theo split; không có cơ sở để kết luận tracker truth bị lỗi. Detector
community dư được giữ trong diagnostics và không bị biến thành một event thứ bảy.

Các artifact đại diện:

- [Evaluation grow metrics](../artifacts/detection-tracking/dang-week1-evaluation-001/datasets/eval-grow-easy-g101/truth_tracking/metrics.csv)
- [Evaluation grow mapping](../artifacts/detection-tracking/dang-week1-evaluation-001/datasets/eval-grow-easy-g101/detector_tracking/source_mapping.csv)
- [Evaluation split diagnostics](../artifacts/detection-tracking/dang-week1-evaluation-001/datasets/eval-split-easy-g101/detector_tracking/mapping_diagnostics.json)

## 9. Đối chiếu yêu cầu Handoff

| Yêu cầu trong Handoff | Trạng thái | Bằng chứng hoặc ghi chú |
|---|---|---|
| Receipt ZIP, SHA, Python, lệnh và kết quả consumer | Đạt | Mục 2; development consumer `0`, `complete`, 18/36/108. |
| Đọc hai dataset mẫu stable/grow | Đạt | Mục 5.1; event và links đều khớp. |
| Tracker truth trước, đủ sáu event development | Đạt | Mục 5.2; 18/18 dataset và 3/3 generator seed mỗi event. |
| Threshold Jaccard `>= 0.30`, giữ links đạt ngưỡng | Đạt | Module tracker và tracker config. |
| Size tolerance ±10% và event precedence | Đạt | Mục 3.2 và tracker config. |
| Test missing successor, empty/edge cases, many-to-many | Đạt | Unit tests 11/11; diagnostics được xuất. |
| Detector seed 0, không chọn seed tốt nhất | Đạt | Mục 6 và artifact development/evaluation. |
| Greedy one-to-one mapping ở tháng nguồn | Đạt | Mục 3.3 và `source_mapping.csv`. |
| Đường A: metrics, support, confusion 6×6 | Đạt | Outputs `truth_tracking` của cả hai artifact. |
| Đường B: events/links, mapping, unmatched, extra, confusion 6×7 | Đạt | Outputs `detector_tracking` của cả hai artifact. |
| Giữ reference/config/hash input trong metadata | Đạt một phần | Metadata có source run, input manifest hash, reference và config chính; cần Phúc kiểm tra cách ghép metadata khi tích hợp demo. |
| Gửi code/config, predictions và bảng chỉ số | Đạt một phần | Code, config development, predictions và metrics đã có trong repo/artifact; chưa tạo commit/nhánh bàn giao. |
| Notebook demo chung, bảng/hình và một case khó/null | Chưa đạt | Notebook/case analysis thuộc phần ghép chung; chưa thực hiện trong báo cáo này. |
| Receipt phản hồi chính thức cho Phúc | Chưa đạt | Báo cáo này là bằng chứng nội bộ; chưa gửi receipt qua kênh nhóm. |

### Kết luận đáp ứng Handoff

Phần tracker và evaluator của Đăng đã đáp ứng các yêu cầu kỹ thuật cốt lõi của Handoff:
đường A, đường B, sáu event, mapping, metrics, confusion matrices và artifact cho cả
development/evaluation đều đã chạy và có thể kiểm tra lại. Evaluation được mở sau khi
config đã khóa.

Tuy nhiên, báo cáo **chưa thể coi là hoàn tất toàn bộ yêu cầu bàn giao cặp** vì còn thiếu
notebook/demo chung, case analysis tích hợp và việc gửi receipt/artifact chính thức cho
Phúc. Đây là các đầu ra phối hợp, không phải lỗi của thuật toán tracker.

## 10. Giới hạn hiện tại

1. Chưa ghép notebook demo chung với Phúc.
2. Chưa có phân tích đầy đủ từng lớp event trên toàn bộ 39 truth sources trong một bảng tổng hợp duy nhất.
3. Detector source dư được báo riêng; chưa đưa vào điểm F1 như một truth source bị bỏ sót.
4. Kết quả benchmark là dữ liệu tổng hợp, không phải kết quả trên Reddit thật.
5. Macro-F1 trung bình thấp không mâu thuẫn với việc đường A khớp truth, vì confusion matrix tính đủ sáu lớp trong khi mỗi dataset chỉ có 2–3 source event.

## 11. Trạng thái bàn giao

Đã hoàn thành:

- [x] Receipt và kiểm tra gói handoff.
- [x] Adapter membership nhiều tháng.
- [x] Jaccard tracker.
- [x] Test sáu event và các trường hợp biên chính.
- [x] Đường A trên 18 development datasets.
- [x] Đường B trên detector seed 0.
- [x] Greedy source mapping.
- [x] Metrics và diagnostics cơ bản.
- [x] Artifact development có metadata/manifest.
- [x] Consumer evaluation và artifact evaluation.
- [x] Khóa tracker/evaluator trước evaluation.

Chưa hoàn thành:
- [ ] Ghép notebook demo chung với Phúc.
- [ ] Viết phân tích lỗi chi tiết cho các case merge/split/dissolve trong demo chung.
- [ ] Gửi receipt và artifact chính thức cho Phúc để ghép demo.

## 12. Lệnh tái chạy chính

Kiểm thử code:

```powershell
& .\.venv\Scripts\python.exe -m unittest `
  tests.unit.test_jaccard_tracking -v
```

Run artifact development đã dùng:

```text
run_id = dang-week1-development-001
source split = development
source run = phuc-005-t05-development-001
```

Không chạy lại trên cùng run ID nếu output đã tồn tại; mỗi lần tái chạy phải dùng run ID mới.

Evaluation artifact đã dùng:

```text
run_id = dang-week1-evaluation-001
source split = evaluation
source run = phuc-005-t06-evaluation-001
```
