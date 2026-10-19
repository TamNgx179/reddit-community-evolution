# PHUC-005 — Hướng dẫn cấu hình và lượt chạy tái lập

**T01 DONE, PHUC-005 1/6:** liên kết cấu hình, policy chấm và lịch dự kiến; **68/68 test pass**, Windows checkout giữ hash. Tiến độ/nghiệm thu tại [task board](../tasks.md#phuc-005); [spec](spec.md) ghi phạm vi toàn bộ sáu task.

## T01 dùng để làm gì

PHUC-004 đã chứng minh evaluator chấm được kết quả Leiden có sẵn. PHUC-005 chuẩn bị đường chạy từ cấu hình đến graph, detection và metrics, cùng bằng chứng bộ evaluation được giữ lại. T01 chốt bộ tham số và đơn vị của đường chạy đó; T02 mới ghép API, T05 mới ghi freeze, T06 mới chạy evaluation.

| Tập | Generator seeds | Dataset dự kiến | Snapshot dự kiến | Snapshot × detector seed dự kiến |
|---|---|---:|---:|---:|
| Development | 11, 12, 13 | 18 | 36 | 108 |
| Evaluation giữ lại | 101, 102, 103 | 18 | 36 | 108 |
| Tổng | Hai tập không trùng seed/dataset ID | 36 | 72 | 216 |

Mỗi tập có sáu case `stable/grow/shrink/merge/split/dissolve`, hai tháng `2020-01/2020-02`, difficulty easy. Generator dùng `p_in=0.50`, `p_out=0.02`, weight 1; detector dùng gamma 1 và seeds 0/1/2, canonical 0. Ba detector seeds là ba lần chạy trên cùng dataset. Ví dụ một dataset có hai tháng sẽ tạo sáu đơn vị chấm, vẫn chỉ là một dataset.

## Hai file cấu hình đi cùng nhau

- [benchmark_week1.json](../../../../configs/benchmark_week1.json) là graph recipe schema 1 đã dùng cho output cũ: lịch case/tháng/seed, probabilities, protocol RNG và ordering.
- [benchmark_week1_protocol.json](../../../../configs/benchmark_week1_protocol.json) là binding schema 1, ID `week1-detection-evaluation-v1`: tên/hash recipe, toàn bộ AMI/summary policy đang được evaluator hỗ trợ, quy tắc tách tập và expected counts.

Graph recipe giữ nguyên byte để input/metadata đã lưu tiếp tục kiểm chứng được. File protocol bổ sung policy cho đường chạy mới. Loader kiểm tra hash recipe, policy có khớp runtime hay không, seed/dataset identity không trùng và counts đúng đơn vị. Thay cấu hình cần cập nhật binding có chủ đích; thay policy cần version và review tác động trước evaluation. File `.gitattributes` giữ quy tắc data/LFS sẵn có và thêm LF cho đúng hai JSON này để checkout Windows giữ hash ổn định.

Policy `synthetic-ami-v1` chấm trên endpoint users đã xác minh, arithmetic AMI, giữ điểm âm; empty/insufficient/constant/all-singletons có null/status/reason, input sai báo lỗi. Summary tính theo dataset-month, giữ từng seed riêng và valid/missing support. Xem [PHUC-004](../004-detection-evaluation/README.md) để hiểu chi tiết điểm và coverage.

## Lệnh và API chỉ lập kế hoạch

Chạy từ repository root với môi trường Python của repo:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.protocol configs/benchmark_week1_protocol.json
```

Output thành công có `scope=benchmark-plan-only`, `status=planned`, hashes và `planned_counts`; `evaluation_executed=false`, `freeze_record_created=false`. Config/policy lỗi thì exit 2. Lệnh đọc file, không tạo run hoặc output graph/membership/metrics.

```python
from pathlib import Path
from reddit_sna.benchmarks.protocol import load_benchmark_protocol
from reddit_sna.benchmarks.config import dataset_schedule

plan = load_benchmark_protocol(Path("configs/benchmark_week1_protocol.json"))
development = dataset_schedule(plan.benchmark, "development")
print(plan.protocol_sha256, plan.benchmark_sha256)
print(plan.protocol["expected_counts"])
```

Object trả về giữ các dictionary riêng cho caller; sửa object trong RAM không sửa file hoặc policy runtime. Đây chưa phải freeze record. Snapshot/hash/lifecycle của run được ghép ở T02/T03 và freeze chính thức ở T05.

## Kiểm tra và bằng chứng

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_benchmark_protocol tests.unit.test_benchmark_config tests.unit.test_detection_evaluation tests.unit.test_detection_summary tests.integration.test_detection_alignment tests.integration.test_detection_evaluation_export -v
```

Test protocol không cần igraph/leidenalg/sklearn. Bộ lệnh có integration evaluator cần extras `[graph,evaluation]`; tests dùng fixture development trong thư mục tạm. [Bằng chứng T01](../evidence/PHUC-005-T01-protocol.md), [dataset schedule](../evidence/PHUC-005-T01-dataset-schedule.csv) và [counts](../evidence/PHUC-005-T01-planned-counts.csv) phân biệt kế hoạch với thực thi.

**Tiếp theo T02:** ghép API generator → detection → metrics bằng protocol đã xác minh; scope hoàn thành chỉ đến detection evaluation. Không cần chờ tracker của Đăng.
