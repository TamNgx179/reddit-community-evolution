# PHUC-005 — Hướng dẫn cấu hình và lượt chạy tái lập

**T01–T02 DONE, PHUC-005 2/6:** protocol binding và API/CLI development từ generator đến bảng điểm; **305/305 test repo pass**. Hai demo mới có 12 metrics/9 summary mỗi run, CSV/policy tái lập. Tiến độ/nghiệm thu tại [task board](../tasks.md#phuc-005); [spec](spec.md) ghi phạm vi toàn bộ sáu task.

## T01 dùng để làm gì

PHUC-004 đã chứng minh evaluator chấm được kết quả Leiden có sẵn. PHUC-005 chuẩn bị đường chạy từ cấu hình đến graph, detection và metrics, cùng bằng chứng bộ evaluation được giữ lại. T01 chốt bộ tham số và đơn vị; T02 ghép API development bên dưới, T05 mới ghi freeze, T06 mới chạy evaluation giữ lại.

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

## API và lệnh chạy từ cấu hình đến bảng điểm — T02

`run_synthetic_benchmark(config, protocol=..., dataset_ids=...)` trong [detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py) ghép ba module đã kiểm tra: sinh graph/truth → Leiden → evaluator. Mỗi lần gọi tạo run mới và lưu cả đầu vào lẫn điểm. Không cần tracker của Đăng.

Chạy hai dataset development nhỏ từ repository root:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.detection_tracking `
    --config configs/detection_development.toml `
    --protocol configs/benchmark_week1_protocol.json `
    --run-id phuc-005-api-demo-001 `
    --dataset-id dev-stable-easy-g11 `
    --dataset-id dev-grow-easy-g11
```

Chọn run ID mới nếu đã tồn tại. Lệnh cần extras `[graph,evaluation]`. Bỏ toàn bộ `--dataset-id` để chọn đủ **18 dataset development** theo protocol. Danh sách chỉ nhận ID development duy nhất, không rỗng; thứ tự thực thi luôn theo protocol. ID evaluation giữ lại bị chặn trước khi tạo output. TOML `seed=0` chỉ canonical detector; generator seed nằm trong từng dataset ID và lịch JSON.

API tương đương, dùng trong notebook hoặc script:

```python
from pathlib import Path
from reddit_sna.config import load_config
from reddit_sna.pipelines.detection_tracking import run_synthetic_benchmark

config = load_config(Path("configs/detection_development.toml"), run_id="phuc-005-api-review-001")
output = run_synthetic_benchmark(
    config, protocol=Path("configs/benchmark_week1_protocol.json"),
    dataset_ids=("dev-stable-easy-g11", "dev-grow-easy-g11"),
)
print(output / "evaluation/detection_metrics.csv")
```

Đầu ra ở `artifacts/detection-tracking/<run-id>/`:

```text
manifest.json                            # scope, selection, counts, stage/status
config/run-config.toml                   # TOML nguồn; manifest giữ run_id đã override
config/protocol/                         # protocol và recipe nguyên byte
inputs/source/<dataset-id>/              # graph/nodes/truth/config/metadata
inputs/detected/<dataset-id>/            # memberships/diagnostics/config/metadata
evaluation/                              # metrics, summary, policy, timing, metadata
```

`evaluation/` ở đây là **bước chấm điểm development**; tập evaluation giữ lại chưa được chạy. Thành công có `scope=development-detection-evaluation`, `tracking_status=not_implemented`, `freeze_record_created=false`. Danh sách subset ghi rõ số lượng được chọn, không được coi là hoàn thành toàn lịch benchmark. Lệnh `reddit-sna run` cho full detection-tracking vẫn báo chưa triển khai; dùng entry riêng ở trên để chạy đến detection evaluation.

Protocol, recipe và TOML được chụp trước các stage. Config/policy/selection/dependencies lỗi thì chưa tạo run; stage lỗi giữ những file đã tạo và manifest `failed` cùng stage/dataset. Thử lại vào run cũ bị từ chối. T02 có manifest trạng thái cơ bản; T03 tiếp tục inventory hashes/source/environment/timing và kiểm tra lifecycle đầy đủ. [Bằng chứng T02](../evidence/PHUC-005-T02-api.md) ghi lệnh thực chạy, kết quả và vị trí log/ZIP.

T02 đã chạy hai demo `artifacts/detection-tracking/phuc-005-t02-001/` và `-002/`: mỗi run 2 dataset stable/grow seed 11, 4 snapshot, 12 metrics/9 summary, AMI/coverage 1 trong phạm vi này. 29 CSV/policy files giống byte, hai reader độc lập đạt, 3.301 artifact cũ được bảo toàn. [Metrics](../evidence/PHUC-005-T02-detection-metrics.csv)/[summary](../evidence/PHUC-005-T02-detection-summary.csv) nhỏ theo Git; proof/ZIP local `artifacts/verification/phuc-005-t02-001/` và `.zip` giữ cả hai run/source/log/hash. Full suite 305/305 pass, gồm 9 test composition mới; không chạy held-out evaluation hoặc tạo freeze record.

**Tiếp theo T03:** hoàn thiện provenance, environment, timing và lifecycle manifest ở cấp run. Tracker của Đăng không chặn phần này.
