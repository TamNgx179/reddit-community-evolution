# Bằng chứng PHUC-002-T04 — Gói graph/truth và kiểm tra file

**Task:** [PHUC-002-T04](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hiện 4/6 task.
**Kiểm tra hoàn tất:** 18/10/2026 15:47:24, Asia/Bangkok (UTC+07:00).
**Môi trường:** `.venv`, Python 3.12.6; source cơ sở `5274b04` cộng thay đổi T04, nhánh `feat/phuc-002-stable-graphs`.

## Vừa làm gì, dùng để làm gì

Trước T04, sampler trả graph trong bộ nhớ; chưa có gói graph/truth sáu case dùng chung. T04 ghi graph, danh sách người hoạt động và đáp án thành CSV, kèm config/metadata/hashes. Leiden có thể đọc R.csv, evaluator có thể đọc nodes/membership, Đăng có thể dùng events/links để đối chiếu tracker. Chưa có kết quả các thuật toán đó trong lượt này.

- [io.py](../../../../src/reddit_sna/benchmarks/io.py): thêm `validate_edges`, `write_edges`, `read_edges`, `export_graph_dataset`. Chặn sai tháng/endpoint, self-loop/cạnh trùng/cặp ngược, weight sai; giữ isolate bằng node list riêng. Các writer kiểm tra input rồi mở exclusive, UTF-8 không BOM, LF, thứ tự cố định.
- `export_graph_dataset` nhận config đã kiểm tra và chọn một case/seed/split từ lịch; tự suy ra ID/reference để tránh tên lệch cấu hình. Ghi và đọc lại R/nodes/membership/events/links cùng bản JSON trước khi ghi metadata hoàn thành. Gói dở dang giữ nguyên khi lỗi.
- [graphs.py](../../../../src/reddit_sna/benchmarks/graphs.py) và [graph_benchmark.toml](../../../../configs/graph_benchmark.toml): lệnh xuất đủ sáu case tại một development seed. Run boundary dùng helper có sẵn, chỉ cho output trong `project_root/artifacts`, từ chối thư mục tồn tại kể cả rỗng. Khi lỗi, manifest failed giữ danh sách dataset đã xong và phần dở dang.
- Exporter/CLI/consumer truth stable/grow của PHUC-001 giữ nguyên giao diện và artifact type. Gói graph mới có artifact type riêng `synthetic-graph-truth`; consumer truth cũ không nhận loại mới.

Mỗi dataset có 7 CSV, `benchmark-config.json` và `metadata.json`. Bản config giữ đầy đủ giá trị từ JSON chung, serialize canonical; không giữ whitespace của file gốc. Metadata có identity scope, observed months, truth reference, seed/protocol/ordering/probabilities, Python/package versions, số node/cạnh/nhóm/isolate và SHA-256 của tám file dữ liệu/config. Metadata không tự hash; manifest run hash cả metadata.

`seed_used_for_truth=false`, `detector_references={}`. Run thành công chỉ có `scope="graph-truth"`, `completed_stages=["generation","truth"]`; đây chưa phải provenance/freeze đầy đủ PHUC-005.

## Lượt export thật

Đã chạy hai lệnh sau, lần lượt với `PYTHONHASHSEED=0` và `137`:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.graphs --run-id phuc-002-t04-001
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.graphs --run-id phuc-002-t04-002
```

Cả hai exit 0. Mỗi run có 6 dataset development seed 11, 12 snapshot, **54 file dataset + manifest**. API đọc lại trong exporter và runner dùng **stdlib CSV/JSON/SHA-256 riêng**, không import code generator, kiểm tra cả 12 gói của hai run. Runner đối chiếu tập thành viên từng nhóm, nhãn/link thiết kế sáu case, exact header, thứ tự/cạnh/node/weight, counts và hash mọi file.

| Case | Nodes tháng 1→2 | Cạnh tháng 1→2 | Nhóm tháng 1→2 | Membership | Events | Links |
|---|---|---|---|---|---|---|
| stable | 24→24 | 76→53 | 2→2 | 48 | 2 | 2 |
| grow | 24→30 | 76→104 | 2→2 | 54 | 2 | 2 |
| shrink | 30→24 | 116→62 | 2→2 | 54 | 2 | 2 |
| merge | 36→36 | 98→185 | 3→2 | 72 | 3 | 3 |
| split | 36→36 | 164→107 | 2→3 | 72 | 2 | 3 |
| dissolve | 24→12 | 76→25 | 2→1 | 36 | 2 | 1 |

Hai tháng là 2020-01 và 2020-02; counts tính cả K12. Mọi snapshot mặc định ở seed này có 0 isolate. Không thêm cạnh hoặc đổi seed để đạt điều đó. Diagnostic p=0 trong test giữ đủ node, R header-only và báo isolate đúng; bộ diagnostic/nhóm nhỏ nghiệm thu đầy đủ vẫn thuộc T05/T06.

**54/54 file dataset giữa hai run giống byte**, gồm config và metadata. Manifest có run ID và timestamp riêng nên không yêu cầu giống byte. Hash R stable vẫn khớp T01/T03:

- 2020-01: `58c34c2a7ba1297a7f536b8b5a55556ee5a8666ab9d65839a6a0876ba1476592`.
- 2020-02: `4ddcba4db3dbedaf4c9b294f522e132d3b17dd690d097bad15e8ac99bd5786dd`.

Chạy lại lệnh với run ID `phuc-002-t04-001` trả exit **2**, toàn bộ run cũ gồm manifest giữ nguyên hash. Gói PHUC-001-T06-001 được đối chiếu trước/sau, không đổi file; hai consumer stable/grow chạy bằng `python -I` vẫn pass. Config JSON nguồn cũng không đổi byte.

## Kiểm thử

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_graph_export tests.integration.test_graph_export tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

**92/92 pass, 0 skip/failure/error**, unittest 26.859s, subprocess wall 28.311s. Suite liên quan, không phải toàn bộ test repo. Hai tiến trình export thực tế mất tổng 2.525s wall, bao gồm startup/I/O; không coi là benchmark hiệu năng.

12 test mới: 9 unit trong [test_graph_export.py](../../../../tests/unit/test_graph_export.py), 3 integration trong [test_graph_export.py](../../../../tests/integration/test_graph_export.py). Bao phủ:

- CSV cạnh round-trip/canonical/header-only, malformed/NaN/Infinity/self-loop/trùng/cặp ngược/tháng và user sai; input lỗi không tạo file, đọc không sửa input.
- Gói đủ sáu case, exact counts, hashes/config, node/membership coverage, byte tái lập, p=0 giữ isolate và input config không bị thay đổi.
- Output hoàn chỉnh/rỗng/dở dang không bị ghi đè; lỗi ghi hoặc đọc lại không có metadata hoàn thành.
- CLI từ working directory ngoài repo có dấu cách, hai process khác hash seed vẫn giống dữ liệu; manifest hash cả 54 file; namespace/output/seed hoặc JSON sai bị từ chối trước khi tạo artifact. Seed evaluation 101 bị CLI development từ chối.
- Giả lập lỗi sau stable: manifest failed, stable hoàn chỉnh và grow dở dang được giữ; retry vào run đó bị từ chối.

## Artifact, tái tạo và giới hạn

Các gói và log sau **chỉ ở máy Phúc, bị Git ignore**:

- `artifacts/detection-tracking/phuc-002-t04-001/`: gói chính.
- `artifacts/detection-tracking/phuc-002-t04-002/`: gói đối chiếu.
- `artifacts/verification/phuc-002-t04-001/`: `verification-result.json`, runner `verify.py`, test log, export/repeat logs, hai legacy reader logs, bản config nguồn khi chạy. JSON ghi source base, source/config hashes, thời gian/lệnh/test counts và counts/hashes từng dataset.

Thành viên khác dùng code/config đã push và lệnh ở [README](../002-dynamic-benchmark/README.md), thay bằng hai run ID mới. Ví dụ kiểm tra hash và so hai gói từ repo bằng stdlib (đổi hai tên run nếu cần):

```powershell
@'
from hashlib import sha256
import json
from pathlib import Path
base = Path("artifacts/detection-tracking")
runs = [base / name for name in ("phuc-002-t04-001", "phuc-002-t04-002")]
def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}
for run in runs:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete" and manifest["scope"] == "graph-truth"
    assert len(manifest["datasets"]) == 6
    for name, info in manifest["files"].items():
        assert sha256((run / name).read_bytes()).hexdigest() == info["sha256"]
first, second = [files(run / "datasets") for run in runs]
assert len(first) == 54 and first == second
print("54 files identical; both manifest hashes verified")
'@ | & .\.venv\Scripts\python.exe -
```

Không sinh dataset evaluation, không chạy Leiden/AMI/tracker. Hai run sáu case ở seed 11 là smoke test của exporter T04, chưa nghiệm thu toàn bộ PHUC-002. **Tiếp theo T05** bổ sung suite generator seed/order/xác suất biên/nhóm nhỏ; T06 hoàn thiện lượt development/diagnostic và báo cáo nghiệm thu. Không cần chờ Đăng để làm các bước này.
