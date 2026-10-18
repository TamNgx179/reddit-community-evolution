# Benchmark mạng động — Sampler, sáu kịch bản và cấu hình chung

T01 có sampler graph stable; T02 có đáp án chuẩn cho đủ sáu tình huống; T03 đưa tham số và lịch seed vào file cấu hình chung. `membership` là bảng người thuộc nhóm nào; `events` là nhãn thay đổi của nhóm nguồn; `links` cho biết nhóm nguồn nối sang nhóm nào ở tháng sau. Đáp án này dùng để đối chiếu với kết quả tracker sau này.

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

Bộ sinh đáp án không chạy tracker để đoán nhãn. [Bằng chứng T02](../evidence/PHUC-002-T02-six-event-truth.md) ghi counts của sáu case, lệnh kiểm tra, hashes và đối chiếu stable/grow cũ. API export/CLI/consumer T06 vẫn chỉ nhận stable/grow; xuất gói sáu case đầy đủ là T04.

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

Ví dụ trên dùng đúng tham số đọc từ JSON. Các API sampler cũ vẫn giữ default riêng khi caller không truyền tham số; lệnh kiểm tra cấu hình không thay thế API export/orchestration ở các task sau.

## Kiểm tra và phạm vi

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

T03 đã chạy 80 test liên quan, gồm 10 test mới cho cấu hình, lịch split và công thức gọi sampler từ JSON. [Bằng chứng T02](../evidence/PHUC-002-T02-six-event-truth.md) giữ lượt 70 test trước đó; [bằng chứng T01](../evidence/PHUC-002-T01-stable-graphs.md) giữ lượt 55 test và số cạnh stable đã đo.

T01–T03 có sampler, truth sáu case và cấu hình/lịch chung. CSV/JSON kiểm chứng do runner local ghi để đối chiếu; bước tiếp theo T04 xuất gói graph/truth đầy đủ kèm metadata/hashes và bảo toàn output cũ. Chưa có kết quả Leiden/AMI/tracker trên benchmark đầy đủ.
