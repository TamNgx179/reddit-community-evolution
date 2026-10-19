# PHUC-004 — Căn nhãn, coverage và AMI

T01 bổ sung [evaluation/detection.py](../../../../src/reddit_sna/evaluation/detection.py). Đầu vào là truth của PHUC-002 và membership Leiden đã lưu của PHUC-003. Hàm đọc kiểm tra hai gói thuộc cùng dataset, cùng graph và đúng tháng/seed, rồi ghép nhãn chuẩn với nhãn dự đoán theo **cùng user ID**.

Ví dụ truth ghi `u002 → B, u001 → A`, detector ghi `u001 → c1, u002 → c0`: kết quả theo thứ tự `u001, u002` là truth `[A, B]`, prediction `[c1, c0]`. Không ghép theo vị trí dòng CSV, không ép tên nhóm `A` phải bằng `c1`; mỗi community ID vẫn cục bộ theo reference/tháng.

## Đọc một dataset đã lưu

Chạy tại thư mục gốc repo, sau khi cài package theo README chung:

```powershell
@'
from pathlib import Path
from reddit_sna.evaluation.detection import load_aligned_detection

result = load_aligned_detection(
    Path("artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11"),
    Path("artifacts/detection-tracking/phuc-003-t06-001/datasets/dev-stable-easy-g11"),
    detector_seed=0,
)
print(result.dataset_id, result.truth_reference, result.detector_reference)
for snapshot in result.snapshots:
    print(snapshot.month)
    for user, truth, predicted in zip(
        snapshot.user_ids, snapshot.truth_labels, snapshot.predicted_labels, strict=True
    ):
        print(user, truth, predicted)
'@ | & .\.venv\Scripts\python.exe -
```

Full artifact không nằm trong Git. Nếu chưa có source, tạo full development theo [PHUC-002](../002-dynamic-benchmark/README.md), sau đó chạy [PHUC-003](../003-leiden-detection/README.md). Thay hai đường dẫn trên bằng dataset tương ứng của run mới. Hàm nhận **thư mục dataset**, không nhận thư mục run chứa `datasets/`.

`load_aligned_detection(source, detection, detector_seed=0)` chỉ đọc file, không gọi Leiden, không ghi lại input hoặc tính metric. Đọc dữ liệu đã lưu dùng stdlib và package hiện có, chưa cần scikit-learn/igraph. Seed hỗ trợ đúng lịch tuần 1: 0/1/2, gamma 1, canonical 0.

## Hàm kiểm tra gì?

- Metadata phải complete đúng loại graph/truth và detection, identity scope/dataset/truth reference/tháng khớp config và lịch dataset. Detector package phải có scope detection, stage detection và diagnostics schema 2.
- Đối chiếu SHA-256 của config, source metadata/graph/nodes, truth membership và các file được detector kê khai. Tính lại graph cohort và kiểm tra mapping tháng/seed/reference/path/fingerprint, tránh chấm nhầm output của graph khác.
- Recipe source và runtime detector phải khớp. PHUC-003 hiện lưu difficulty trong runtime config; loader kiểm tra difficulty qua config/lịch và kiểm tra cả metadata nếu field đó có mặt.
- Truth phải phủ đúng mọi active user trong `nodes.csv`, gồm isolate. Prediction phải phủ đúng endpoint của `R.csv`. Thiếu, trùng, sai tháng/reference hoặc có user lạ sẽ báo lỗi; không lấy phần giao để bỏ qua lỗi.
- Resolve file tương đối từ hai thư mục được truyền vào; đường dẫn tuyệt đối cũ trong metadata chỉ có tính mô tả. Có thể copy gói sang thư mục khác. Path vượt ra ngoài dataset bị từ chối.

Loader kiểm tra hash của `detection.json`; kiểm tra ý nghĩa timing/diagnostics thuộc bước hoàn thiện metric sau.

## Kết quả và API dùng với fixture

`AlignedDetection` giữ dataset/split/scenario/difficulty, generator seed, detector seed/gamma và hai reference. Mỗi `AlignedSnapshot` có:

| Field | Ý nghĩa |
|---|---|
| `month` | Tháng được quan sát |
| `active_user_ids`, `truth_labels_all` | Cùng thứ tự user đã sort, giữ cả isolate để dùng cho bước đếm sau |
| `user_ids`, `truth_labels`, `predicted_labels` | Ba vector cùng thứ tự endpoint user đã sort, dùng cho bước chấm sau |

Các record là frozen dataclass với tuple. Một user có thể lặp ở hai tháng; khóa là `(month, user_id)`. Không suy ra tracking từ community ID qua tháng.

Nếu chỉ có record trong bộ nhớ, gọi `align_memberships(truth, predictions, truth_reference=..., detector_reference=..., active_users_by_month=..., endpoint_users_by_month=...)`. Truth/predictions là iterable `Membership`; caller phải cung cấp tập active và endpoint độc lập từ dữ liệu quan sát. Hàm trả tuple `AlignedSnapshot`, không xác minh metadata/dataset khi caller không truyền gói file. Xem [unit tests](../../../../tests/unit/test_detection_evaluation.py) để biết ví dụ fixture.

Tháng quan sát không có cạnh vẫn có snapshot với ba vector chấm rỗng; truth của isolate được giữ. Policy AMI được mô tả ở T03 bên dưới.

## Đếm người, coverage và số nhóm — T02

Sau khi có `result` từ ví dụ ở trên:

```python
from dataclasses import asdict
from reddit_sna.evaluation.detection import count_snapshot

for snapshot in result.snapshots:
    print(asdict(count_snapshot(snapshot)))
```

`count_snapshot(AlignedSnapshot)` trả frozen dataclass `DetectionCounts` cho **một tháng của một dataset/seed**. Hàm kiểm tra lại vector lengths, ID duy nhất/đã sort, tập endpoint thuộc active và truth của cùng người phải khớp giữa hai tập. Record tự dựng bị sai sẽ báo `ValueError` trước khi đếm. Metadata/reference được xác minh ở loader T01.

| Field | Cách tính / ý nghĩa |
|---|---|
| `month` | Giữ tháng của snapshot |
| `active_nodes` | Số user trong `nodes.csv`, gồm cả isolate |
| `endpoint_nodes` | Số user xuất hiện ở ít nhất một đầu cạnh R |
| `assigned_nodes` | Số nhãn dự đoán; sau xác minh phải bằng endpoint |
| `isolated_nodes` | `active_nodes - endpoint_nodes` |
| `coverage` | `assigned_nodes / active_nodes`; là tỉ lệ 0–1, nhân 100 để hiển thị phần trăm |
| `coverage_status` | `defined` nếu active > 0; `no_active_users` nếu active = 0 |
| `true_communities_all_nodes` | Số nhãn truth khác nhau trên toàn bộ active |
| `true_communities_scored_nodes` | Số nhãn truth khác nhau trên endpoint được chấm |
| `predicted_communities` | Số nhãn detector khác nhau trên endpoint |

Ví dụ 3 active, trong đó 2 người thuộc A có cạnh và 1 người thuộc K bị isolate: assigned = endpoint = 2, isolate = 1, coverage = **2/3**. Số nhóm truth toàn bộ = **2**, nhóm truth được chấm = **1**. Vì vậy phải giữ riêng hai số nhóm này.

Nếu active > 0 nhưng không có cạnh, coverage = **0.0**, status `defined`, số nhóm được chấm/predicted = 0. Nếu active = 0, coverage = **None** (JSON null / CSV trống), status `no_active_users`, các counts = 0. Singleton hoặc partition chỉ có một nhóm vẫn có counts xác định; policy đánh giá chất lượng partition ở T03.

T02 chỉ trả counts, chưa tạo exporter metric/summary production. Bảng kiểm chứng development/diagnostic được lưu riêng, có dataset/seed/reference và đường dẫn input; xem [evidence T02](../evidence/PHUC-004-T02-counts.md). Coverage 100% chỉ nói detector đã gán đủ người; AMI đánh giá mức tương đồng giữa partition dự đoán và truth.

## AMI và policy dữ liệu thiếu/degenerate — T03

Cài extra đã khai báo trong `pyproject.toml`:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[evaluation]'
& .\.venv\Scripts\python.exe -m pip check
```

Extra `evaluation` yêu cầu `scikit-learn>=1.5,<2`; lượt kiểm chứng dùng **1.9.1**. Nếu cần sinh lại graph/detection fixture, cài `.[graph,evaluation]`. Alignment và counts vẫn chỉ cần stdlib; backend sklearn chỉ được import khi một snapshot đủ điều kiện chấm AMI.

```python
from dataclasses import asdict
from reddit_sna.evaluation.detection import AMI_POLICY, score_snapshot

print(dict(AMI_POLICY))  # lưu JSON này cùng config của lượt chạy trước khi chấm
for snapshot in result.snapshots:
    print(asdict(score_snapshot(snapshot)))
```

`score_snapshot(AlignedSnapshot)` kiểm tra input bằng `count_snapshot`, gọi `sklearn.metrics.adjusted_mutual_info_score` với **`average_method="arithmetic"`**, trả `DetectionAMI` gồm `month`, `n_scored_users`, `ami`, `ami_status`, `ami_reason`, `ami_policy_id`, `ami_average_method`. Chỉ chấm endpoint users đã xác minh/căn nhãn; isolate vẫn được phản ánh qua coverage riêng. Caller giữ dataset/seed/reference từ `AlignedDetection` và ghi phiên bản thư viện trong metadata khi lưu kết quả.

AMI 1 biểu thị hai phân hoạch trùng cấu trúc khi đủ điều kiện chấm, dù tên nhóm khác nhau. Mốc quanh 0 tương ứng mức tương đồng kỳ vọng do ngẫu nhiên; giá trị âm hợp lệ được giữ nguyên. AMI được tính theo cấu trúc phân nhóm, không phải phần trăm user có tên nhóm giống truth. [Tài liệu scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_mutual_info_score.html) giải thích metric, tính đối xứng và normalizer; đã tra cứu tài liệu 1.9.1 ngày 18/10/2026.

Policy cố định **`synthetic-ami-v1`** trong immutable mapping `AMI_POLICY`; [JSON đã lưu](../evidence/PHUC-004-T03-ami-policy.json) là bản sao từ code. Quy tắc được áp dụng theo thứ tự:

| Điều kiện | `ami` | `ami_status` / lý do |
|---|---|---|
| Sai keys, user thiếu/lạ/trùng, lengths hoặc truth mapping sai | Báo lỗi dữ liệu | Không biến lỗi input thành một hàng có điểm |
| Không có user được chấm, n = 0 | None | `empty_scored` / `no_scored_users` |
| Chỉ một user, n < 2 | None | `insufficient_users` / `fewer_than_2_scored_users` |
| Truth hoặc prediction chỉ có một nhóm | None | `degenerate_partition`, reason `truth_constant` và/hoặc `prediction_constant` |
| Truth hoặc prediction gán mỗi user một nhóm riêng | None | `degenerate_partition`, reason `truth_all_singletons` và/hoặc `prediction_all_singletons` |
| Các trường hợp còn lại | Kết quả thư viện, giữ cả số âm | `ok`, reason None |
| Thiếu sklearn, lỗi backend hoặc kết quả không hữu hạn | Báo lỗi | Thiếu sklearn có lệnh cài `[evaluation]`; lỗi dependency khác được giữ nguyên |

Nếu cả hai phía có cờ, reason nối bằng dấu phẩy theo thứ tự truth rồi prediction. None khi xuất JSON là null, khi xuất CSV là ô trống. Ví dụ `AABB` và `xxyy` có AMI 1; `AABB` và `xyxy` có AMI ≈ -0.5; `AAAA` và `xxxx` được policy để null với hai cờ constant.

Việc loại constant/all-singletons khỏi hàng có điểm là **quy tắc đánh giá của đồ án**, không phải hạn chế của thư viện. Các trường hợp đó vẫn giữ counts/coverage và trạng thái trong output. Summary T04 chỉ tổng hợp hàng `ami_status=ok`, đồng thời báo số hàng thiếu và lý do. Policy được version trong Git và lưu hash/bản sao trước lượt chấm development; việc freeze cấu hình cho tập evaluation thuộc PHUC-005.

[Bằng chứng T03](../evidence/PHUC-004-T03-ami.md) lưu kết quả theo từng snapshot/seed, policy, versions và consumer đọc CSV gọi thẳng sklearn, không import project. Đây là chấm benchmark tổng hợp; chưa chạy tập evaluation hoặc tracker.

## Xuất metrics, summary và timing — T04

Tại thư mục gốc repo, dùng source graph/truth và detection đã có. Mỗi `--pair` là hai **dataset directory**, output là thư mục mới có parent tồn tại:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.evaluation.detection `
  --pair artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11 `
         artifacts/detection-tracking/phuc-003-t06-001/datasets/dev-stable-easy-g11 `
  --output artifacts/detection-tracking/phuc-004-demo-new
```

Thêm các `--pair SOURCE DETECTION` trước `--output` để gộp nhiều dataset. ID trong cùng report phải duy nhất; các fixture diagnostic có cùng ID nhưng graph khác cần report riêng. Source phải có đủ file đã kê khai trong metadata; nếu chưa có input local, tái tạo theo PHUC-002/003 hoặc nhận ZIP thực tế. Lệnh này dùng lại graph và membership, chỉ thực hiện evaluation; output có sẵn bị từ chối kể cả thư mục rỗng. CLI thành công exit 0/in tóm tắt JSON; lỗi input, dependency hoặc I/O exit 2.

API tương ứng:

```python
from pathlib import Path
from reddit_sna.evaluation.detection import export_detection_evaluation

meta = export_detection_evaluation(
    [(Path("<source-dataset-dir>"), Path("<detection-dataset-dir>"))],
    Path("artifacts/detection-tracking/<new-report-id>"),
)
print(meta["metric_rows"], meta["summary_rows"])
```

Report thành công có năm file:

| File | Dùng để làm gì |
|---|---|
| `detection_metrics.csv` | Một dòng mỗi dataset/tháng/seed, gồm context/reference, canonical, counts/coverage, AMI/status/reason/policy/support và sklearn version |
| `detection_summary.csv` | Trung bình/support theo từng seed, ở mức scenario và all_scenarios; giữ split/difficulty/gamma riêng |
| `ami-policy.json` | Bản sao policy đã áp dụng |
| `timing.json` | Timing nguồn detection và timing evaluation/export mới, kèm scope; generation/peak memory null khi chưa đo |
| `metadata.json` | Status/scope/versions, summary policy, input paths/hashes, evaluator source hash và hash bốn file trên |

Trong summary, `aggregation_unit=dataset-month`. Seed 0 có `seed_role=canonical`, seed 1/2 là `diagnostic`; không có hàng gộp ba seed. `ami_mean/min/max` dùng các dòng `ok`, mỗi dòng một trọng số, **không trọng số theo số người**. `all_scenarios` là trung bình trên các dòng dataset-tháng hợp lệ của mọi case, không phải trung bình các case mean. `n_rows`, `n_datasets`, `n_ami_valid/missing`, ba counts trạng thái thiếu và JSON `ami_missing_reasons` giúp đọc đúng support. Nếu không có dòng hợp lệ, mean/min/max để trống.

`coverage_mean` là trung bình các coverage đã xác định, kèm `n_coverage_valid/missing`; coverage 0.0 vẫn được tính, coverage None bị loại khỏi mean và được đếm thiếu. `n_scored_user_observations`/`n_active_user_observations` cộng số người qua các dòng; user lặp qua tháng nên đây là số quan sát, không phải số người duy nhất hoặc mẫu thống kê độc lập.

Timing có phạm vi cụ thể:

- `detection_wall_seconds`: tổng `wall_seconds` đã lưu trong diagnostics, **một lần mỗi dataset-tháng cho cả ba seed**; `detection_by_month` giữ source SHA-256. Không đo lại detector hoặc biến thời gian tháng thành thời gian riêng từng seed.
- `evaluation_wall_seconds`: đo mới từ preflight/input verification/loading đến counts/AMI/summary, trước khi ghi output. `evaluation_compute_wall_seconds` chỉ cộng các lời gọi counts/AMI, có thể gồm startup backend trong lần gọi đầu.
- `csv_export_wall_seconds`: ghi policy và hai CSV; không gồm ghi timing/metadata. `generation_wall_seconds` và `peak_memory_bytes` null vì evaluator không đo chúng. Đơn vị thời gian là giây.

Input được kiểm tra/recheck trước khi tạo output; output không được chồng lên input. Metadata complete được publish cuối qua file pending. Lỗi khi ghi report giữ các file dở dang và `failure.json` nếu ghi được, chưa có complete metadata; dùng output ID mới khi chạy lại. Metadata report chỉ có `scope=detection-evaluation-only`/stage evaluation, không báo toàn bộ pipeline đã hoàn tất. Manifest của luồng đầy đủ thuộc PHUC-005.

[Bằng chứng T04](../evidence/PHUC-004-T04-export.md) có hai lượt development, CSV nhỏ theo Git, vị trí gói local và ZIP/consumer để đọc lại sau relocation. [Bằng chứng T05](../evidence/PHUC-004-T05-invariants.md) và [CSV AC01–05](../evidence/PHUC-004-T05-acceptance-matrix.csv) nối tiêu chí với test đã chạy. [T06](../evidence/PHUC-004-T06-stable-grow.md) đã nghiệm thu stable/grow với truy vết input/config/version và tập user được chấm.

## Kiểm tra và phần tiếp theo

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.unit.test_detection_summary tests.integration.test_detection_alignment tests.integration.test_detection_evaluation_export -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Integration tests tạo input bằng Leiden thật, cần extra `[graph]` theo hướng dẫn cài đặt repo; test chấm AMI cần thêm `[evaluation]`. Các unit tests căn nhãn/counts/null policy không cần thư viện graph. [Evidence T01](../evidence/PHUC-004-T01-alignment.md) giữ bằng chứng alignment và giới hạn lượt discover lịch sử; từng task mới ghi rõ test đã chạy.

**T01–T06 DONE:** căn nhãn, counts/coverage, AMI/policy, exporter metrics/summary/timing, kiểm tra các điều kiện nghiệm thu và chấm stable/grow development có truy vết. T05 chạy full suite **286/286 pass**, gồm **48 test evaluator**, 0 skip; AC01–05 pass với 16 ánh xạ test trong CSV. T06 chạy lại 48 test evaluator và hai report stable/grow tái lập, có input/config/versions và danh sách user được chấm. Tập evaluation giữ lại và tracker còn ở các phần việc riêng.

## Nghiệm thu stable/grow và tái tạo report — T06

[Bằng chứng T06](../evidence/PHUC-004-T06-stable-grow.md), [metrics](../evidence/PHUC-004-T06-detection-metrics.csv), [summary](../evidence/PHUC-004-T06-detection-summary.csv), [dataset ledger](../evidence/PHUC-004-T06-dataset-ledger.csv) ghi kết quả trên **6 dataset development, 12 snapshot, 36 dòng metrics**, dùng generator 11/12/13 và detector 0/1/2. Cả 36 dòng AMI 1, coverage 1; canonical vẫn là seed 0. Đây là kết quả của hai case tổng hợp easy, không suy rộng sang Reddit hoặc tracker.

Report thực tế: `artifacts/detection-tracking/phuc-004-t06-001/` và `phuc-004-t06-002/`. Proof/ZIP local `artifacts/verification/phuc-004-t06-001/` và `.zip` giữ 108 input files, hai report, raw trace **918 lượt user qua ba seed**, config/versions/hashes, reader và log. 918 là số lượt quan sát khi chấm, không phải số người độc lập. Metrics/summary/policy giống byte giữa hai process đổi thứ tự input/hash seed; timing và timestamp có thể khác.

Khi đã có graph/truth run và detection run development trên máy, chạy từ repository root vào output mới:

```powershell
$evaluationBenchmark = Get-Content configs/benchmark_week1.json -Raw | ConvertFrom-Json
$evaluationSource = 'artifacts/detection-tracking/phuc-002-t06-001/datasets'
$evaluationDetector = 'artifacts/detection-tracking/phuc-003-t06-001/datasets'
$evaluationOutput = 'artifacts/detection-tracking/phuc-004-stable-grow-review-001'
$evaluationArgs = @('-m', 'reddit_sna.evaluation.detection', '--output', $evaluationOutput)
foreach ($evaluationScenario in @('stable', 'grow')) {
    foreach ($evaluationGeneratorSeed in $evaluationBenchmark.generator.seeds.development) {
        $evaluationDataset = "dev-$evaluationScenario-easy-g$evaluationGeneratorSeed"
        $evaluationArgs += @('--pair', (Join-Path $evaluationSource $evaluationDataset), (Join-Path $evaluationDetector $evaluationDataset))
    }
}
& .\.venv\Scripts\python.exe @evaluationArgs
if ($LASTEXITCODE -ne 0) { throw 'Evaluation export failed; inspect the output/log before retrying with a new run ID.' }
Import-Csv (Join-Path $evaluationOutput 'detection_summary.csv') |
    Where-Object { $_.aggregation_level -eq 'all_scenarios' -and $_.detector_seed -eq '0' } |
    Select-Object n_datasets, n_rows, n_ami_valid, n_ami_missing, ami_mean, coverage_mean
```

Thay source/detector paths nếu dùng run ID khác và chọn output chưa tồn tại. Nếu clone repo chưa có artifacts, tạo đầu vào theo [PHUC-002 full development](../002-dynamic-benchmark/README.md) rồi [PHUC-003 detection](../003-leiden-detection/README.md); Git không chứa full artifacts. Nếu đã nhận ZIP T06, giải nén rồi dùng `read_report.py` và lệnh trong evidence để đọc độc lập, không cần sinh lại dữ liệu.

T06 không đổi code/config và không chạy lại full repo suite; 48/48 test liên quan pass, full 286/286 ở T05 vẫn là bằng chứng hồi quy gần nhất. **PHUC-004 hoàn thành 6/6. Tiếp theo PHUC-005-T01:** rà soát lịch/config/policy development/evaluation trước orchestration và freeze.
