# Benchmark mạng động — Sinh và xuất gói graph/truth

T01 có sampler graph stable; T02 có đáp án chuẩn cho đủ sáu tình huống; T03 đưa tham số và lịch seed vào file cấu hình chung; T04 xuất chúng thành gói CSV/JSON đọc lại được. `membership` là bảng người thuộc nhóm nào; `events` là nhãn thay đổi của nhóm nguồn; `links` cho biết nhóm nguồn nối sang nhóm nào ở tháng sau. Đáp án này dùng để đối chiếu với kết quả tracker sau này.

Sampler lấy membership chuẩn từ PHUC-001 rồi xét từng cặp user trong mỗi tháng. Hai user cùng community có xác suất nối cạnh `p_in=0.50`; khác community dùng `p_out=0.02`. Cạnh vô hướng, chỉ ghi một chiều source < target, weight 1.0.

`stable` nghĩa là thành viên A→C giữ nguyên và K giữ nguyên; cạnh được lấy mẫu mới mỗi tháng. Node hoạt động được giữ riêng với cạnh, nên user không có cạnh vẫn xuất hiện trong `.nodes`.

## Sampler graph — T01

[benchmarks/dynamic.py](../../../../src/reddit_sna/benchmarks/dynamic.py):

```python
sample_snapshots(
    memberships,
    expected_reference=...,
    expected_users_by_month=...,
    generator_seed=11,
    p_in=0.50,
    p_out=0.02,
)
```

Kết quả là tuple `SampledSnapshot(month, nodes, edges)` theo tháng tăng dần. `nodes` là tuple user ID; `edges` là tuple `SnapshotEdge`. Cả hai có thứ tự cố định. Danh sách node mong đợi phải đến từ caller, ví dụ node CSV của fixture truth, để kiểm tra membership thiếu/thừa/trùng và reference/tháng sai trước khi lấy mẫu.

Seed phải là int trong `[0, 2**32)`, không nhận bool. Xác suất phải là int/float hữu hạn trong `[0,1]`, không nhận bool. Các tháng quan sát phải liên tiếp; tháng được quan sát nhưng rỗng cần khai báo tường minh bằng danh sách user rỗng.

Protocol sampler v1: một `random.Random(seed)` riêng, duyệt tháng tăng dần, từng cặp user đã sort; tiêu thụ một lần random cho mọi cặp, kể cả xác suất 0 hoặc 1. Không sửa global random state, không tự thêm cạnh để bỏ isolate, không dùng kết quả detection/evaluation. Tái lập đã được kiểm tra trên Python 3.12.6; khi đổi phiên bản Python cần xác minh lại.

## Bộ đáp án sáu tình huống — T02

`build_memberships` và `build_transitions` trong [scenarios.py](../../../../src/reddit_sna/benchmarks/scenarios.py) hiện nhận đủ sáu giá trị của `SCENARIOS`:

| Case | Nhóm chính trước → sau | Đáp án nguồn chính |
|---|---|---|
| stable | A12 → C12, cùng người | A stable, một link tới C |
| grow | A12 → C18, thêm 6 | A grow, một link tới C |
| shrink | A18 → C12, bớt 6 | A shrink, một link tới C |
| merge | A12 + B12 → C24 | A và B mỗi nguồn một merge, cùng nối tới C |
| split | A24 → B12 + C12 | A có một split, hai link tới B và C |
| dissolve | A12 → không còn hoạt động | A dissolve, không có link đích |

Mọi case có thêm K12 riêng, giữ nguyên và mang nhãn stable. Vì có K nên dissolve vẫn có tháng sau được quan sát với 12 node. Sáu người bị loại trong shrink và 12 người của A trong dissolve không xuất hiện ở bất kỳ nhóm nào của tháng sau.

Ví dụ nhóm tách đôi:

```python
from reddit_sna.benchmarks.scenarios import build_memberships, build_transitions

memberships = build_memberships("split", "truth-example")
truth = build_transitions("split", "truth-example")
print([(e.source.community_id, e.event.value) for e in truth.events])
# [('A', 'split'), ('K', 'stable')]
print([(link.source.community_id, link.target.community_id) for link in truth.links])
# [('A', 'B'), ('A', 'C'), ('K', 'K')]
```

Mỗi nguồn có một nhãn, nên split không nhân đôi event theo số link. `observed_months=["2020-01"]` trả events/links rỗng với cả sáu case: chưa thấy tháng sau thì không tự gán dissolve. Tháng cuối cũng không bị gán event nguồn.

Bộ sinh đáp án không chạy tracker để đoán nhãn. [Bằng chứng T02](../evidence/PHUC-002-T02-six-event-truth.md) ghi counts của sáu case, lệnh kiểm tra, hashes và đối chiếu stable/grow cũ. API/CLI/consumer của **PHUC-001-T06** vẫn chỉ nhận stable/grow; gói graph sáu case dùng API T04 riêng bên dưới.

## Cấu hình chung — T03

[configs/benchmark_week1.json](../../../../configs/benchmark_week1.json) là công thức chạy chung, để thành viên nhóm dùng cùng tham số. Seed là mã giúp tái tạo cùng một lần lấy mẫu; seed sinh graph và seed detector có vai trò riêng.

| Tham số | Giá trị hiện tại | Ý nghĩa |
|---|---|---|
| `months` | 2020-01, 2020-02 | Hai tháng quan sát liên tiếp |
| `scenarios`, `difficulty` | Đủ 6 case, easy | Lịch cơ bản của tuần 1 |
| `generator.p_in`, `p_out`, `weight` | 0.50, 0.02, 1.0 | Xác suất cạnh trong/khác nhóm và trọng số |
| Generator development seeds | 11, 12, 13 | Bộ phát triển để viết/thử và điều chỉnh code |
| Generator evaluation seeds | 101, 102, 103 | Bộ đánh giá giữ lại, tách khỏi development |
| Detector seeds, canonical | 0, 1, 2; canonical 0 | Seed 0 là kết quả chính, hai seed còn lại để đối chiếu độ ổn định |
| `detector.gamma` | 1.0 | Độ phân giải Leiden dự kiến |
| Protocol/ordering | Sampler v1, RNG v1; tháng/user/cạnh được sort | Quy tắc tái lập trùng với sampler T01 |

[benchmarks/config.py](../../../../src/reddit_sna/benchmarks/config.py) cung cấp `load_benchmark_config(Path(...))`, `validate_benchmark_config(config)` và `dataset_schedule(config, "development"/"evaluation")`. Bộ đọc chỉ đọc file; không tạo run, không tự sinh dữ liệu hoặc chạy detector.

Schema v1 hiện dùng đúng sáu case theo thứ tự protocol, hai tháng liên tiếp và difficulty easy. Bộ đọc từ chối khóa lạ/thiếu/trùng, số JSON không chuẩn, xác suất/seed sai, seed trùng trong hoặc giữa hai split, gamma không hợp lệ, canonical khác seed detector đầu tiên và ordering/protocol không được hỗ trợ. Các thay đổi protocol/diagnostic sau này cần được version và cập nhật consumer.

Lịch dự kiến: **18 dataset development + 18 dataset evaluation = 36 dataset**, hai tháng/dataset thành **72 snapshot**; ba detector seed/snapshot thành **216 đơn vị detection dự kiến**. Ba seed detector là các lần chạy trên cùng graph, không nhân số dataset. T03 mới xác minh lịch; khóa cấu hình và chạy evaluation thuộc PHUC-005.

Kiểm tra file và in lịch dự kiến:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.config configs/benchmark_week1.json
```

Thành công trả exit code 0, `scope="benchmark-config"`, `status="valid"` và các trường `planned_*`. Cấu hình lỗi trả exit code 2. [Bằng chứng T03](../evidence/PHUC-002-T03-benchmark-config.md) ghi config hash, lịch split và mẫu graph thực sự chạy từ cấu hình.

## Ví dụ chạy sampler từ cấu hình

Từ project đã cài editable package, dùng ví dụ này trong Python:

```python
from pathlib import Path
from reddit_sna.benchmarks.config import dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import build_memberships

config = load_benchmark_config(Path("configs/benchmark_week1.json"))
spec = dataset_schedule(config, "development")[0]  # stable seed 11 trong file hiện tại
reference = f"truth-{spec['dataset_id']}"
memberships = build_memberships(spec["scenario"], reference, start_month=config["months"][0])

# Tập active users kỳ vọng độc lập từ thiết kế stable: A12 và K12.
users = [f"u{i:03d}" for i in range(1, 13)]
users += [f"u{i:03d}" for i in range(101, 113)]
snapshots = sample_snapshots(
    memberships,
    expected_reference=reference,
    expected_users_by_month={month: users for month in config["months"]},
    generator_seed=spec["generator_seed"],
    p_in=config["generator"]["p_in"],
    p_out=config["generator"]["p_out"],
)
for snapshot in snapshots:
    print(snapshot.month, len(snapshot.nodes), len(snapshot.edges))
# 2020-01 24 76
# 2020-02 24 53
```

Khi dùng fixture đã export, lấy expected user lists bằng `read_nodes` và membership bằng `read_memberships`; xem [hướng dẫn fixture PHUC-001](../001-truth-fixtures/README.md).

Ví dụ trên dùng đúng tham số đọc từ JSON. Các API sampler cũ vẫn giữ default riêng khi caller không truyền tham số; lệnh kiểm tra cấu hình không tự xuất artifact.

## Xuất gói graph/truth — T04

Từ thư mục repo đã cài editable package:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.graphs --run-id phuc-002-my-first-export
```

Chọn **run ID mới** mỗi lần chạy. Lệnh dùng [graph_benchmark.toml](../../../../configs/graph_benchmark.toml) để chọn output/namespace và generator seed 11; [benchmark_week1.json](../../../../configs/benchmark_week1.json) cung cấp tham số graph, tháng và lịch sáu case. Có thể chỉ định hai file bằng `--config <TOML>` và `--benchmark-config <JSON>`. Path tương đối của hai tham số CLI tính từ working directory; các path bên trong TOML tính từ thư mục chứa TOML.

TOML seed phải thuộc danh sách generator **development** trong JSON. CLI sinh đúng sáu dataset ở seed đó, không chạy cả ba seed development hoặc dùng seed evaluation. Thành công exit 0, `scope="graph-truth"`; input/output lỗi exit 2.

Ví dụ output stable:

```text
artifacts/detection-tracking/<run-id>/
  manifest.json
  datasets/dev-stable-easy-g11/
    benchmark-config.json
    metadata.json
    snapshots/2020-01/R.csv
    snapshots/2020-01/nodes.csv
    snapshots/2020-02/R.csv
    snapshots/2020-02/nodes.csv
    truth/membership.csv
    truth/events.csv
    truth/links.csv
  datasets/dev-grow-easy-g11/...
  ... bốn case còn lại
```

Mỗi dataset có **7 CSV + 1 config + 1 metadata**. Config lưu đủ giá trị từ JSON, serialize UTF-8/LF với key được sort; giữ nội dung cấu hình, không cam kết cùng byte với file JSON đầu vào. Metadata ghi identity scope/reference/tháng quan sát, seed/sampler/RNG/order, probabilities, phiên bản Python/package, số node/cạnh/nhóm/isolate và SHA-256 của tám file còn lại. `seed_used_for_truth=false`: seed dùng cho cạnh, đáp án lấy từ thiết kế. `detector_references={}` vì chưa chạy detector.

Exporter kiểm tra input trước khi tạo output, ghi CSV theo thứ tự cố định, đọc lại so với snapshot/truth rồi mới ghi metadata `status="complete"`. Manifest run hash cả metadata và ghi `completed_stages=["generation","truth"]` khi cả sáu dataset thành công. Manifest này chưa thay thế provenance/freeze đầy đủ của PHUC-005.

Output đã tồn tại, kể cả thư mục rỗng hoặc gói dở dang, bị từ chối. Lỗi giữa chừng giữ nguyên phần đã ghi; dataset lỗi không có metadata hoàn thành, manifest run ghi `failed`. Chọn run ID mới để thử lại. Không sửa hay thêm cạnh để loại isolate.

API cho một dataset, dành cho code ghép luồng:

```python
from pathlib import Path
from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset, read_edges, read_memberships, read_nodes

config = load_benchmark_config(Path("configs/benchmark_week1.json"))
# Parent đã tồn tại và được caller chọn theo run policy; destination phải mới.
destination = Path("artifacts/detection-tracking/<new-run>/datasets/dev-stable-easy-g11")
metadata = export_graph_dataset(
    destination, benchmark=config, scenario="stable", generator_seed=11,
)
nodes = {m: read_nodes(destination / f"snapshots/{m}/nodes.csv", expected_month=m)
         for m in metadata["observed_months"]}
edges = read_edges(destination / "snapshots/2020-01/R.csv",
                   expected_month="2020-01", expected_users=nodes["2020-01"])
truth = read_memberships(destination / "truth/membership.csv",
                         expected_reference=metadata["truth_reference"], expected_users_by_month=nodes)
```

`export_graph_dataset` suy ra dataset ID từ lịch đã kiểm tra; không nhận tên tùy ý dễ lệch seed/split. API có tham số `split` mặc định `development`; chọn evaluation là thao tác tường minh, không phải freeze/đánh giá. T04 không chạy nhánh evaluation. Các hàm CSV nhận path và kỳ vọng tường minh, không tự chọn run folder; hãy dùng CLI/run helper để kiểm tra output nằm trong `project_root/artifacts`.

`validate_edges`/`write_edges`/`read_edges` trong [io.py](../../../../src/reddit_sna/benchmarks/io.py) yêu cầu user list độc lập; chặn sai tháng, endpoint ngoài danh sách, self-loop, cặp ngược, cạnh trùng, weight không hữu hạn hoặc không dương. Writer sort theo source/target, ghi weight dạng số thực và từ chối overwrite. R rỗng có header; node không xuất hiện trong R vẫn nằm trong nodes/truth.

Gói chỉ có ở máy chạy vì `artifacts/` bị Git ignore. Thành viên nhóm chạy lệnh trên để tái tạo hoặc nhận nguyên thư mục run. Consumer độc lập `scripts/read_truth_fixture.py` dành cho gói PHUC-001 cũ, không nhận artifact type graph/truth mới. [Bằng chứng T04](../evidence/PHUC-002-T04-graph-export.md) ghi cách kiểm tra bằng stdlib riêng cùng các gói đã đo.

## Kiểm tra và phạm vi

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_graph_export tests.integration.test_graph_export tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

T03 đã chạy 80 test liên quan. T04 bổ sung 12 test cho CSV cạnh, gói sáu case, hashes/tái lập, isolate, failure và CLI không ghi đè. Kết quả suite và lượt export thực tế được ghi trong [bằng chứng T04](../evidence/PHUC-002-T04-graph-export.md). [Bằng chứng T02](../evidence/PHUC-002-T02-six-event-truth.md) giữ lượt 70 test trước đó; [bằng chứng T01](../evidence/PHUC-002-T01-stable-graphs.md) giữ lượt 55 test và số cạnh stable đã đo.

T01–T04 có sampler, truth sáu case, cấu hình/lịch chung và exporter. T05 bổ sung suite generator toàn diện về seed/order/xác suất biên/nhóm nhỏ; T06 nghiệm thu benchmark development cùng diagnostic/báo cáo tái lập đầy đủ. Lượt smoke test exporter T04 chưa thay thế các việc đó. Chưa có kết quả Leiden/AMI/tracker trên benchmark đầy đủ.
