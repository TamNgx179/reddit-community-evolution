# PHUC-005 — Hướng dẫn cấu hình và lượt chạy tái lập

**T01–T05 DONE, PHUC-005 5/6:** full development **18 dataset/36 snapshot/108 metrics** (99 valid/9 null), canonical AMI mean **0.955879927**, coverage 1.0. Đã tạo freeze sau development từ clean source `d4fe76b`, giữ config/source/versions và gate trước evaluation. **T05 40/40 test liên quan pass**, không chạy lại full suite; 314/314 là lượt T03. CSV/log/run/ZIP và freeze reference đã lưu; [task board](../tasks.md#phuc-005), [bằng chứng T05](../evidence/PHUC-005-T05-development-freeze.md). T06 evaluation giữ lại chưa chạy.

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
manifest.json                            # schema 2: scope, counts, hashes, status, timing
config/run-config.toml                   # TOML nguồn; manifest giữ run_id đã override
config/resolved-run-config.json          # config thực dùng, gồm override run_id
config/protocol/                         # protocol và recipe nguyên byte
provenance/environment.json              # Python, packages, platform, hash seed
provenance/source.json                   # Git revision/working tree và source hashes
provenance/source/                       # bản sao package Python + pyproject nếu có
inputs/source/<dataset-id>/              # graph/nodes/truth/config/metadata
inputs/detected/<dataset-id>/            # memberships/diagnostics/config/metadata
evaluation/                              # metrics, summary, policy, timing, metadata
```

`evaluation/` ở đây là **bước chấm điểm development**; tập evaluation giữ lại chưa được chạy. Thành công có `scope=development-detection-evaluation`, `tracking_status=not_implemented`, `freeze_record_created=false`. Danh sách subset ghi rõ số lượng được chọn, không được coi là hoàn thành toàn lịch benchmark. Lệnh `reddit-sna run` cho full detection-tracking vẫn báo chưa triển khai; dùng entry riêng ở trên để chạy đến detection evaluation.

Protocol, recipe và TOML được chụp trước các stage. Config/policy/selection/dependencies lỗi thì chưa tạo run; stage lỗi giữ những file đã tạo và manifest `failed` cùng stage/dataset. Thử lại vào run cũ bị từ chối. T02 có manifest trạng thái cơ bản; T03 bổ sung hồ sơ bên dưới, không sửa manifest/output T02 đã lưu. [Bằng chứng T02](../evidence/PHUC-005-T02-api.md) ghi lệnh thực chạy, kết quả và vị trí log/ZIP của T02.

T02 đã chạy hai demo `artifacts/detection-tracking/phuc-005-t02-001/` và `-002/`: mỗi run 2 dataset stable/grow seed 11, 4 snapshot, 12 metrics/9 summary, AMI/coverage 1 trong phạm vi này. 29 CSV/policy files giống byte, hai reader độc lập đạt, 3.301 artifact cũ được bảo toàn. [Metrics](../evidence/PHUC-005-T02-detection-metrics.csv)/[summary](../evidence/PHUC-005-T02-detection-summary.csv) nhỏ theo Git; proof/ZIP local `artifacts/verification/phuc-005-t02-001/` và `.zip` giữ cả hai run/source/log/hash. Full suite 305/305 pass, gồm 9 test composition mới; không chạy held-out evaluation hoặc tạo freeze record.

## Hồ sơ của mỗi lượt chạy — T03

Manifest schema **2** trả lời: đã chạy code/cấu hình nào, bằng môi trường gì, bước nào xong, mất bao lâu và file có còn nguyên byte không. Helper [artifacts.py](../../../../src/reddit_sna/artifacts.py) được API gọi tự động; không cần thêm tham số CLI. Schema của graph/detection/report con giữ nguyên. Các manifest T02 schema 1 vẫn là hồ sơ lịch sử, không tự nâng cấp hay ghi đè.

| Trường | Dùng để đọc gì |
|---|---|
| `config_inputs` | Path nguồn, archive path tương đối và SHA-256 của protocol, recipe, TOML |
| `resolved_config` và `config` | JSON cấu hình thực dùng, gồm run ID truyền từ CLI/API; TOML gốc có thể còn ID mặc định |
| `source` | Package Python thực được import, hashes/bản sao các file `.py` và pyproject nếu có; Git revision/branch/working tree |
| `environment` | Python/executable/platform, versions package/igraph/leidenalg/sklearn/numpy/scipy, `PYTHONHASHSEED` nếu đặt |
| `files` | Tất cả file output khác root manifest/pending manifest, gồm metadata con, byte count và SHA-256 |
| `stages` | Configuration, generation, detection, evaluation: pending/running/complete/failed, mốc UTC và wall seconds |
| `dataset_records` | Context case/seed/split, trạng thái generation/detection/evaluation và metadata path cho từng dataset |
| `progress_counts` | Số dataset đã sinh/chạy detector/đánh giá xong; khi lỗi không tự làm đủ expected counts |
| `integrity` | Verified sau kiểm tra cuối; partial/unavailable khi lỗi, giữ expected/actual hashes nếu file đã niêm phong bị đổi |

SHA-256 là mã đối chiếu nội dung file: khác mã nghĩa là byte đã thay đổi. Bản sao source giúp đối chiếu cả khi chạy từ working tree có sửa chưa commit; chỉ Git revision sẽ không đủ để mô tả tình huống đó. Nếu không lấy được Git, ghi `unavailable` cùng các trường null, vẫn giữ source hashes. Không ghi toàn bộ biến môi trường.

Manifest được ghi qua file pending rồi thay thế. Trước mỗi stage/dataset có checkpoint; sau mỗi stage kiểm tra lại các output đã niêm phong. Chỉ ghi root `complete` sau khi mọi stage, expected/actual counts, source hashes và inventory đã qua kiểm tra. `evaluation/metadata.json` complete không đủ để kết luận cả run complete: lỗi kiểm tra cuối hoặc ghi manifest cuối vẫn làm root failed.

Khi lỗi, API ném lại lỗi gốc, giữ artifact đã có và ghi root `failed`, stage/dataset, lỗi, thời gian đã đo và inventory còn đọc được. Ctrl+C được ghi theo đường lỗi khi Python còn xử lý được exception. Nếu ghi failed manifest cũng lỗi, helper cố lưu đầy đủ hồ sơ vào **`failure.json`**; người đọc phải ưu tiên dấu hiệu failure này và không coi checkpoint `started` là thành công. Mất điện, kill process hoặc không thể ghi cả hai file có thể chỉ để lại `started`; đó là run chưa hoàn tất, phải dùng run ID mới.

### Đọc thời gian đúng phạm vi

| Số đo | Phạm vi |
|---|---|
| `preflight_wall_seconds` | Kiểm tra config/selection/backend và lấy provenance trước khi tạo run |
| `timing.run_wall_seconds` | Từ khởi tạo recorder đến kiểm tra cuối; không gồm preflight hoặc ghi complete manifest cuối. Lỗi dùng scope failure capture ghi kèm |
| `stages.*.wall_seconds` | Cả wrapper của bước: gồm checkpoints bên trong và kiểm tra hash cuối stage; không gồm ghi checkpoint ranh giới |
| `dataset_records.*.generation/detection.wall_seconds` | Lời gọi exporter từng dataset, gồm công việc đọc/ghi của exporter; không gồm ghi checkpoint wrapper |
| `dataset_records.*.evaluation.wall_seconds` | **Null**: evaluator đo chung cả batch, không phân bổ giả thành từng dataset |
| `evaluation/timing.json` | Phạm vi report cũ: detection tháng lấy từ diagnostics đã lưu, compute/export report đo riêng; generation tại report vẫn null |
| Peak memory | **Null / not measured**; không suy ra từ các số đo thời gian |

Các số đo lồng nhau nên không cộng tất cả để tính tổng. Timing, timestamp, absolute path và Git working tree có thể khác giữa replay; CSV/policy trong cùng lịch/seed mới là đối tượng đối chiếu tái lập. Hai demo T03, failed run, kiểm tra hashes và log/ZIP được ghi tại [bằng chứng T03](../evidence/PHUC-005-T03-provenance.md).

T03 đã lưu hai successful runs `phuc-005-t03-001/002`, mỗi run 88 output files được hash và 41 source files được lưu; controlled failure `phuc-005-t03-failure-001` giữ progress 2 generated/1 detected/0 evaluated và partial file. Proof/ZIP local tại `artifacts/verification/phuc-005-t03-001`; [run summary](../evidence/PHUC-005-T03-run-summary.csv) và [stage timing](../evidence/PHUC-005-T03-stage-timing.csv) nhỏ theo Git. Full suite 314/314 pass; 3.503 artifact cũ được bảo toàn.

## Nghiệm thu chạy lại và xử lý lỗi — T04

T04 thêm 5 integration tests: từ chối started run; configuration archive lỗi và retry failed run; CLI nhận counts sai dù child report complete; lỗi replace complete manifest thật; hai CLI process cùng run ID chỉ một process được tạo output. Không sửa runtime/config. Chạy bộ liên quan:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_run_provenance tests.integration.test_synthetic_benchmark_run -v
```

Kết quả **23/23 pass**, 0 skip/failure/error, 109.220s. T04 không chạy lại full repo suite; baseline runtime không đổi là 314/314 ở T03.

Demo T04 chọn **stable + dissolve, generator seed 11** trước khi chạy. Hai CLI process hash seed 0/137, đảo dataset selection, mỗi run 2 dataset/4 snapshot/12 metrics/9 summary. **9 dòng AMI hợp lệ, 3 dòng AMI null**: dissolve tháng cuối chỉ còn background K nên policy loại partition constant khỏi AMI; vẫn giữ dòng, status/reason và support. Đây không phải ba dòng bị mất hoặc được gán điểm 0. Coverage cả 12 dòng là 1.0.

29 CSV/policy files khớp byte; 12 membership partitions khớp theo tập user, giữ nguyên khi đổi tên nhóm/đảo dòng; phép so sánh phát hiện khi membership thật bị thay đổi. CLI không ghi đè cả complete/failed/started run. Consumer root chặn started, failed, failure/pending marker và modified byte. Child report trong controlled failure vẫn đọc được nhưng **không được dùng thay trạng thái root**.

[Bằng chứng T04](../evidence/PHUC-005-T04-acceptance.md) có [AC matrix](../evidence/PHUC-005-T04-acceptance-matrix.csv), [metrics](../evidence/PHUC-005-T04-detection-metrics.csv), [summary](../evidence/PHUC-005-T04-detection-summary.csv), [partition comparison](../evidence/PHUC-005-T04-partition-comparison.csv) và [run summary](../evidence/PHUC-005-T04-run-summary.csv). Full log/source/run copies/consumer/ZIP local ở `artifacts/verification/phuc-005-t04-001`; 4.043 artifact cũ giữ hash. AC01–03 pass; AC04/05 còn formal freeze/evaluation.

Các kiểm tra T04 là điều kiện trước lượt formal development/freeze T05 bên dưới. T06 mới chạy tập giữ lại. Không cần chờ tracker Đăng.

## Chạy đủ development và tạo bản khóa — T05

API `create_benchmark_freeze(config, development_run=..., protocol=...)` trong [benchmarks/freeze.py](../../../../src/reddit_sna/benchmarks/freeze.py) tạo **run riêng**, giữ nguyên development run đã complete. Bản khóa chứa protocol/recipe/TOML/config thực dùng, source và môi trường đã tạo development, report development, bản sao manifest cùng hash và lịch hai tập. `frozen_at` là thời điểm UTC sau khi development hoàn tất; `changes_from_development=[]` chỉ khi hashes vẫn khớp.

Chạy từ repository root, chọn ID mới cho mỗi output:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.detection_tracking `
    --config configs/detection_development.toml `
    --protocol configs/benchmark_week1_protocol.json `
    --run-id phuc-005-development-review-001

& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.freeze create `
    --config configs/detection_development.toml `
    --protocol configs/benchmark_week1_protocol.json `
    --development-run artifacts/detection-tracking/phuc-005-development-review-001 `
    --run-id phuc-005-freeze-review-001

& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.freeze verify `
    artifacts/detection-tracking/phuc-005-freeze-review-001
```

Lệnh đầu không có `--dataset-id`, chạy đủ **18 development datasets**, sáu case × generator seeds 11/12/13, 36 snapshots và 108 snapshot×detector-seed units. Hai lệnh sau **không sinh/chấm evaluation data**. `create` trả freeze directory; `verify` chỉ đọc, kiểm tra và trả manifest hash. Lỗi exit 2, output cũ không được ghi đè.

Điều kiện tạo: full-development complete đúng lịch/counts/stages, inventory verified; config và source/runtime versions khớp. Namespace có graph/detection metadata `split=evaluation` thì không được tạo claim pre-evaluation freeze. Audit chỉ đọc metadata nhận diện artifact trong `artifacts/detection-tracking`, không đọc graph/truth/prediction giữ lại. Nếu ghi freeze lỗi, giữ phần đã tạo và failed record.

`load_benchmark_freeze(Path(...))` trả `BenchmarkFreeze` gồm directory, manifest/hash và protocol đã đọc từ bản lưu. Loader kiểm tra archive inventory, development manifest/hash/counts, lịch, chronology, source bytes và Python/package versions hiện tại. Path tuyệt đối producer chỉ ghi provenance; bundle chuyển chỗ vẫn đọc được. Thay source hoặc phiên bản liên quan phải xử lý công khai trước evaluation, không sửa hashes để bỏ qua gate.

Phạm vi khóa: **mọi `.py` trong package `reddit_sna` và pyproject nếu có**, recipe, scoring/split/summary policy và lịch seed. T06 có thể thêm driver ngoài package tại `scripts/run_frozen_evaluation.py` để gọi các module đã khóa; driver phải lưu source/hash riêng và không đổi thuật toán/policy/canonical. Git HEAD có thể tiến vì docs hoặc driver, nhưng package source hashes và versions vẫn phải khớp bản khóa. Khóa được thực thi bằng kiểm tra nội dung, không phải chỉ đánh dấu file readonly.

Schema của bản khóa là **1**, artifact type `synthetic-benchmark-freeze`, scope `benchmark-protocol-freeze`; `freeze_record_created=true`, `evaluation_executed=false` nói về thao tác tạo khóa. Development run vẫn giữ manifest schema 2 và `freeze_record_created=false` vì bản thân run đó không tạo khóa. Frozen source Git context là của development; production T05 đã dùng source `d4fe76b` với working tree sạch. Bản khóa không tự tuyên bố evaluation/tracking hoàn thành.

### Kết quả T05 đã lưu

Development: `artifacts/detection-tracking/phuc-005-t05-development-001/`, đủ 18 dataset/36 snapshot/108 metrics/21 summary/36 stored month timings; **99 AMI hợp lệ, 9 null truth_constant**, không loại điểm thấp. Canonical seed 0 có 33 valid/3 null, AMI mean **0.9558799269999274**, min **0.7241648712463861**, coverage mean 1.0. Seeds 1/2 giữ bảng riêng, không dùng để chọn lại canonical.

Freeze: `artifacts/detection-tracking/phuc-005-t05-freeze-001/`, lúc **19/10/2026 10:58:31 UTC+07:00**, source revision `d4fe76b`, changes rỗng; **54 hashed output files/42 source files**. Manifest SHA-256 **`8c3749cce905e5d416929bddd931cbb4a7104f047ad9273ab22561d5ccdf8ff9`**. Development manifest giữ nguyên; retry cả hai run IDs bị từ chối và không đổi output.

[Bằng chứng T05](../evidence/PHUC-005-T05-development-freeze.md), [metrics](../evidence/PHUC-005-T05-detection-metrics.csv), [summary](../evidence/PHUC-005-T05-detection-summary.csv), [ledger](../evidence/PHUC-005-T05-dataset-ledger.csv), [freeze reference](../evidence/PHUC-005-T05-freeze-reference.json) theo Git; reference chỉ trỏ tới bản khóa đầy đủ. Full proof/log/source/run copies và ZIP local ở `artifacts/verification/phuc-005-t05-001`. Ba independent consumers đạt sau relocation; 4.610 artifact cũ giữ hash. 40/40 targeted tests pass, không chạy lại full repo suite T05.

**Tiếp theo T06:** thêm driver ngoài frozen package, verify bản khóa rồi chạy 18 evaluation datasets seeds 101/102/103, lưu đầy đủ 108 metric rows/failed records và đối chiếu tổng 36/72/216. AC04 và nghiệm thu evaluation của AC05 còn pending; tracker Đăng không chặn bước này.

## Driver evaluation theo bản khóa — T06

[scripts/run_frozen_evaluation.py](../../../../scripts/run_frozen_evaluation.py) nằm ngoài frozen package theo contract T05. Driver gọi `load_benchmark_freeze` trước khi tạo run, kiểm tra namespace/canonical/TOML/chronology/backend, rồi chạy **toàn bộ** evaluation schedule đã khóa. Không có tham số chọn subset, gamma hoặc seed theo điểm. Mọi module trong `src/reddit_sna` và pyproject giữ nguyên hash từ T05.

```powershell
& .\.venv\Scripts\python.exe scripts/run_frozen_evaluation.py `
    --config configs/detection_development.toml `
    --freeze artifacts/detection-tracking/phuc-005-t05-freeze-001 `
    --run-id phuc-005-evaluation-review-001
```

Chọn run ID mới. Dùng TOML development để giữ nguyên input kind/canonical/output contract; **split chạy được lấy từ lịch evaluation trong freeze**, không từ tên file TOML. Output có root manifest schema 2, type `synthetic-frozen-evaluation-run`, scope `heldout-detection-evaluation`, split evaluation; shared full detection-tracking vẫn chưa có tracker.

Run mới giữ `freeze/` nguyên bundle làm đầu vào, `config/` gồm configs đã khóa và config thực dùng, `provenance/source/` package source unchanged, **`provenance/driver/run_frozen_evaluation.py`** cùng hash driver riêng, `inputs/source|detected/<eval-id>/`, `evaluation/` report. Root `freeze_reference` ghi hash/thời điểm/source revision T05; source Git context hiện tại ghi revision của driver. Đây là sử dụng bản khóa, `freeze_record_created=false`; `evaluation_executed=true` từ khi bắt đầu truy cập heldout, không thay trạng thái complete/failed.

Checkpoint, stage/dataset state, timing và inventory dùng `RunRecorder` đã khóa. Cuối run đối chiếu counts, original freeze, TOML và driver bytes; drift/lỗi giữ output và failed record, retry không overwrite. Chỉ root complete sau verification mới là kết quả evaluation hoàn tất.

Tests mới ở [test_frozen_evaluation.py](../../../../tests/integration/test_frozen_evaluation.py) dùng **identity-only stubs**, không sinh graph/truth hoặc tính điểm giữ lại. Chúng kiểm tra preflight, full-schedule control flow, failure/progress/no-overwrite và late drift; các stubs không tạo CSV metric values. Production được chạy sau khi driver đã kiểm tra và commit, có kế hoạch trước khi xem điểm. [Bằng chứng T06](../evidence/PHUC-005-T06-heldout.md) sẽ ghi kết quả và source revision thực tế.
