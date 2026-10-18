# Adapter Leiden tổng hợp — bản đầu seed 0

**PHUC-003-T01** nối graph benchmark của PHUC-002 với `detect_snapshots` có sẵn. Đầu vào là các cạnh quan hệ theo tháng; đầu ra là bảng mỗi người được detector gán vào nhóm nào. Thuật toán tự tìm nhóm từ graph, không đọc membership/events/links chuẩn để tạo kết quả.

## API và cách chạy

API nằm trong [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py):

```python
detect_synthetic_dataset(source: Path, output: Path) -> dict
```

`source` là một dataset graph/truth schema 1 đã xuất, ví dụ `dev-stable-easy-g11`; không truyền cả run 18 dataset. Hàm kiểm tra metadata/config, dataset/identity, tháng, hash của config/R/nodes, cạnh/unit weight/thứ tự và node coverage. Sau đó gọi detector với **seed `(0,)`, gamma `1.0`, protocol `synthetic-planted-undirected-v1`**, identity scope và observed months của dataset. Đây là seed detector, khác generator seed 11 đã dùng sinh graph.

T01 yêu cầu config có gamma 1/canonical 0; chỉ chạy seed 0 dù JSON đã khai báo lịch 0/1/2. Đọc và chạy đủ lịch là T02. API kiểm tra seed/split của dataset; lượt kiểm chứng T01 chỉ dùng stable development, không chạy evaluation.

Từ repo đã cài editable package cùng `[graph]`, chạy ví dụ sau và chọn tên folder mới:

```powershell
@'
import json
from pathlib import Path
from reddit_sna.pipelines.detection_tracking import detect_synthetic_dataset

source = Path("artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11")
run = Path("artifacts/detection-tracking/phuc-003-my-first-detection")
run.mkdir(parents=True, exist_ok=False)
result = detect_synthetic_dataset(source, run / "memberships")
with (run / "prototype-detection.json").open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
    handle.write("\n")
print([(m["month"], m["runs"][0]["assigned_users"], m["runs"][0]["sizes"]) for m in result["months"]])
'@ | & .\.venv\Scripts\python.exe -
```

Nếu chưa có source local, tái tạo nó bằng [lệnh full development PHUC-002](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06), chọn run ID mới rồi đổi path `source` cho đúng. Artifact local không tự đi theo Git.

Ví dụ API lưu:

```text
artifacts/detection-tracking/<new-folder>/
  memberships/2020-01/membership-seed0.csv
  memberships/2020-02/membership-seed0.csv
  prototype-detection.json
```

Parent của `output` phải tồn tại; `output` phải mới và không chồng source. API không sửa input hoặc file output cũ. Ví dụ này tạo folder rồi lưu diagnostics trả về, chưa phải runner nghiên cứu đầy đủ. Gói kiểm chứng của T01 có thêm manifest scope `synthetic-detection-prototype`; mapping/persistence chính thức của adapter thuộc T03.

## Cách đọc kết quả

- CSV đúng header `reference_id,month,community_id,user_id`, UTF-8/LF, sort tháng/nhóm/user. Chỉ gán đúng endpoint của R: mỗi người có cạnh một hàng. Isolate vẫn nằm trong source nodes.csv, không bị âm thầm coi là đã được detector gán.
- `c0`, `c1` là tên nhóm cục bộ theo tháng. Không tự suy ra `c0` tháng 1 là cùng cộng đồng với `c0` tháng 2; tracking cần liên kết riêng.
- Reference detector khác reference truth, gắn identity scope + graph cohort fingerprint + gamma/seed, được giữ chung qua các tháng của cùng dataset/seed. API kiểm tra membership không thiếu/thừa/trùng endpoint hoặc lẫn reference.
- Dict trả về có diagnostics của detector, phiên bản igraph/leidenalg, input hashes, active/isolate counts và context dataset. `schema_version=2` là version diagnostics của detector có sẵn; `membership_schema_version=1` là schema CSV chung của benchmark.
- `modularity`/`rb_objective` là diagnostics, không phải AMI/accuracy. Chỉ một seed nên `seed_pair_ARI=[]`; chưa đánh giá độ ổn định giữa ba seed.
- R rỗng cho membership header-only, assigned 0, trạng thái `empty_graph_no_partition`, modularity/objective null. API vẫn ghi active/isolate counts đúng.

Thuật toán Leiden và quy tắc graph Reddit không bị sửa để phục vụ giả lập. Wrapper dùng source CSV canonical và protocol synthetic riêng; chỉ xuất membership đã kiểm tra. Full `run` detection–tracking vẫn báo chưa triển khai, vì tracker/evaluator chưa được nối.

## Kiểm tra và phần tiếp theo

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

Suite T01 có **57/57 test liên quan pass**. Test mới gọi Leiden thật, kiểm tra không cần file truth, CSV/reference/endpoint, R rỗng và input/output được giữ nguyên khi lỗi. [Bằng chứng T01](../evidence/PHUC-003-T01-leiden-adapter.md) ghi lượt stable thật: mỗi tháng có 24 assigned, 2 nhóm 12/12; hai lần chạy khớp membership, bảng kết quả/paths/ZIP đã lưu. Test nền của task này chưa thay thế suite đủ lịch/dependency/error của T04/T05.

Tiếp theo **PHUC-003-T02** đọc lịch detector seeds 0/1/2 từ cấu hình chung, canonical vẫn là 0. T03 sẽ lưu `detection.json` và mapping metadata chính thức. AMI/coverage evaluator thuộc PHUC-004; không cần chờ tracker của Đăng để tiếp tục.
