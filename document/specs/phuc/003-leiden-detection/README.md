# Adapter Leiden tổng hợp — xuất gói detection có nguồn rõ ràng

**T01** nối graph benchmark với `detect_snapshots` có sẵn; **T02** đọc và chạy đủ detector seeds 0/1/2 từ cấu hình, giữ canonical 0; **T03** xuất membership, diagnostics, config và metadata mapping thành một gói. Đầu vào là các cạnh quan hệ theo tháng; đầu ra là bảng mỗi người được detector gán vào nhóm nào. Thuật toán tự tìm nhóm từ graph, không đọc membership/events/links chuẩn để tạo kết quả.

## API và cách chạy

API nằm trong [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py):

```python
detect_synthetic_dataset(source: Path, output: Path, *, benchmark_config: Path | None = None) -> dict
export_synthetic_detection(source: Path, output: Path, *, benchmark_config: Path | None = None) -> dict
```

`source` là một dataset graph/truth schema 1 đã xuất, ví dụ `dev-stable-easy-g11`; không truyền cả run 18 dataset. Hàm kiểm tra metadata/config, dataset/identity, tháng, hash của config/R/nodes, cạnh/unit weight/thứ tự và node coverage. Metadata nguồn cũng được ghi hash và kiểm tra không đổi. Sau đó gọi detector với **seeds `(0,1,2)`, gamma `1.0`, canonical 0, protocol `synthetic-planted-undirected-v1`**, identity scope và observed months của dataset. Đây là seed detector, khác generator seed 11 đã dùng sinh graph.

- `detect_synthetic_dataset` giữ giao diện T01/T02: ghi trực tiếp `<output>/<month>/membership-seed*.csv`, trả dictionary diagnostics. Chỉ dùng khi caller cần tự quản lý lưu diagnostics.
- `export_synthetic_detection` là cách xuất gói từ T03: gọi API trên, ghi `<output>/memberships/...`, `detection.json`, bản config thực đọc và `metadata.json`; trả metadata. Không bọc thêm một thư mục `memberships` khi gọi exporter.

`benchmark_config` chọn file JSON runtime, ví dụ `Path("configs/benchmark_week1.json")`. Nếu không truyền, API đọc bản `benchmark-config.json` đã lưu trong dataset. Các trường công thức sinh graph phải khớp bản nguồn; riêng mục detector được đọc từ file runtime. API ghi path/hash của file thực đọc trong `result["detector_config"]` và kiểm tra file không đổi trước khi xuất membership.

Protocol tuần 1 yêu cầu đúng thứ tự `[0,1,2]`, gamma 1, canonical 0. Lịch rút gọn/đảo thứ tự/đổi canonical hoặc công thức graph lệch bị từ chối trước output; không bỏ qua config để chạy default khác. Generic JSON validator có thể nhận lịch khác, nhưng adapter tuần 1 chỉ nhận protocol này. T01 là lượt lịch sử chạy riêng seed 0, artifact/evidence cũ giữ nguyên; API hiện tại chạy ba seed. Lượt kiểm chứng T02 vẫn chỉ dùng stable development, không chạy evaluation.

Từ repo đã cài editable package cùng `[graph]`, chạy ví dụ sau và chọn tên folder mới:

```powershell
@'
from pathlib import Path
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection

source = Path("artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11")
run = Path("artifacts/detection-tracking/phuc-003-package-demo")
metadata = export_synthetic_detection(source, run,
                                     benchmark_config=Path("configs/benchmark_week1.json"))
print("dataset:", metadata["dataset_id"])
print("canonical_seed:", metadata["detector"]["canonical_seed"])
print([(m["month"], m["seed"], m["assigned_users"], m["path"])
       for m in metadata["memberships"]])
'@ | & .\.venv\Scripts\python.exe -
```

Nếu chưa có source local, tái tạo nó bằng [lệnh full development PHUC-002](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06), chọn run ID mới rồi đổi path `source` cho đúng. Artifact local không tự đi theo Git.

Ví dụ API lưu:

```text
artifacts/detection-tracking/<new-folder>/
  memberships/2020-01/membership-seed0.csv
  memberships/2020-01/membership-seed1.csv
  memberships/2020-01/membership-seed2.csv
  memberships/2020-02/membership-seed0.csv
  memberships/2020-02/membership-seed1.csv
  memberships/2020-02/membership-seed2.csv
  detection.json
  detector-config.json
  metadata.json
```

Parent của `output` phải tồn tại; `output` phải mới và không chồng source, kể cả thư mục rỗng có sẵn cũng bị từ chối. Exporter chuẩn bị gói trong thư mục tạm rồi tạo output mới và chuyển `metadata.json` cuối cùng. Lỗi chuẩn bị không tạo output cuối; lỗi I/O khi chuyển file có thể để lại gói dở dang, không được retry vào đó. Không sửa input, metadata/config nguồn hoặc output cũ. Gói T01/T02 cũ và manifest prototype của chúng giữ nguyên; gói T03 có metadata `scope="detection"`, chưa phải manifest toàn pipeline của PHUC-005.

## Đọc gói và chọn file cho Đăng

`metadata.json` schema 1, artifact type `synthetic-detection`, lưu:

- Dataset/identity, split/scenario/generator seed, truth reference và các tháng thực quan sát. Truth reference chỉ là định danh để nối với gói nguồn; chưa phải matching cộng đồng detector–truth.
- `detector`: gamma, lịch seed, canonical 0, versions igraph/leidenalg, file config và hash. `detector-config.json` là bản sao **đúng byte của runtime JSON**, có cả công thức sinh graph/difficulty; có thể khác bản config archived trong source ở phần detector.
- `memberships`: một entry mỗi tháng/seed, gồm dataset, identity, reference, cờ canonical, đường dẫn CSV, SHA-256, graph/nodes nguồn, graph fingerprint và counts active/assigned/isolate/status. Graph rỗng vẫn có entry; không phải đoán reference từ CSV rỗng.
- `files`: hash của tám file khác trong gói; không tự hash `metadata.json`. `source.files`: hash sáu file graph/config/metadata đã đọc, không gồm CSV truth. `source.directory` và đường dẫn runtime trong diagnostics là dấu vết máy tạo gói.

Đường dẫn `memberships[*].path`, `diagnostics_file`, `detector.config_file` và keys `files` tương đối với **gói detection**. `graph_file`, `nodes_file`, keys `source.files` tương đối với **dataset graph nguồn**. Có thể chuyển gói detection sang chỗ khác và vẫn đọc/hash được các file trong gói; để kiểm tra endpoint hoặc tính AMI, phải cung cấp thêm gói nguồn tương ứng, không phụ thuộc đường dẫn tuyệt đối cũ.

Ví dụ kiểm tra toàn bộ hash rồi chọn hai membership canonical:

```powershell
@'
from hashlib import sha256
import json
from pathlib import Path

root = Path("artifacts/detection-tracking/phuc-003-package-demo")
meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
for name, info in meta["files"].items():
    assert sha256((root / name).read_bytes()).hexdigest() == info["sha256"]
for entry in meta["memberships"]:
    if entry["canonical"]:
        print(entry["dataset_id"], entry["month"], entry["seed"], root / entry["path"])
'@ | & .\.venv\Scripts\python.exe -
```

## Cách đọc kết quả

- CSV đúng header `reference_id,month,community_id,user_id`, UTF-8/LF, sort tháng/nhóm/user. Chỉ gán đúng endpoint của R: mỗi người có cạnh một hàng. Isolate vẫn nằm trong source nodes.csv, không bị âm thầm coi là đã được detector gán.
- `c0`, `c1` là tên nhóm cục bộ theo tháng. Không tự suy ra `c0` tháng 1 là cùng cộng đồng với `c0` tháng 2; tracking cần liên kết riêng.
- Mỗi seed có reference detector riêng, khác truth; cùng seed giữ chung reference qua các tháng. Reference gắn identity scope + graph cohort fingerprint + gamma/seed. API chặn thiếu/thừa/trùng endpoint, đảo run hoặc lẫn reference giữa các seed.
- `detection.json` lưu toàn bộ dictionary diagnostics của adapter: phiên bản igraph/leidenalg, input hashes, active/isolate counts, context dataset, chất lượng và timing mỗi tháng. `schema_version=2` là version diagnostics của detector có sẵn, khác metadata/membership schema 1. Timing tháng bao gồm cả ba seed, không phải thời gian riêng từng seed; JSON không hứa giống byte giữa hai lần chạy vì timing thay đổi.
- `modularity`/`rb_objective` là diagnostics, không phải AMI/accuracy. `seed_pair_ARI` có thứ tự cặp **(0,1), (0,2), (1,2)** khi graph không rỗng, đo độ giống nhau giữa các seed. Canonical luôn là seed đầu đã cấu hình (0), không chọn điểm cao nhất.
- R rỗng cho ba membership header-only/tháng, assigned 0, `empty_graph_no_partition`, modularity/objective null và `seed_pair_ARI=[]`. API vẫn giữ active/isolate counts đúng, không điền ARI giả cho graph rỗng.

Thuật toán Leiden và quy tắc graph Reddit không bị sửa để phục vụ giả lập. Wrapper dùng source CSV canonical và protocol synthetic riêng; chỉ xuất membership đã kiểm tra. Full `run` detection–tracking vẫn báo chưa triển khai, vì tracker/evaluator chưa được nối.

## Kiểm tra và phần tiếp theo

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

Suite hiện **66/66 test liên quan pass**. T03 thêm năm test xuất gói: diagnostics/config/mapping và đọc sau khi copy, empty mapping, output cũ/overlap/parent lỗi, lỗi ghi metadata và source metadata đổi trước publish. [Bằng chứng T03](../evidence/PHUC-003-T03-detection-package.md) ghi hai gói stable 9 file, sáu membership tái lập, ba lượt đọc stdlib độc lập gồm gói relocated và ZIP đã lưu. [T02](../evidence/PHUC-003-T02-detector-schedule.md) giữ lượt lịch sử 61 test/ba seed; [T01](../evidence/PHUC-003-T01-leiden-adapter.md) giữ 57 test/một seed. Test hiện có chưa thay thế nghiệm thu đầy đủ của T04/T05.

Tiếp theo **PHUC-003-T04** rà soát đầy đủ endpoint/empty/dependency/input lỗi/output cũ ở adapter và exporter. T05/T06 còn nghiệm thu integration và lượt development đủ cohort. AMI/coverage evaluator thuộc PHUC-004; không cần chờ tracker của Đăng để tiếp tục.
