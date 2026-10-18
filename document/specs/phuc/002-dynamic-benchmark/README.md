# Benchmark mạng động — Sampler và sáu kịch bản chuẩn

T01 có sampler graph stable; T02 có đáp án chuẩn cho đủ sáu tình huống. `membership` là bảng người thuộc nhóm nào; `events` là nhãn thay đổi của nhóm nguồn; `links` cho biết nhóm nguồn nối sang nhóm nào ở tháng sau. Đáp án này dùng để đối chiếu với kết quả tracker sau này.

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

## Ví dụ đọc/chạy trong Python

Từ project đã cài editable package, dùng ví dụ này trong Python:

```python
from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import build_memberships

reference = "truth-dev-stable-easy-g11"
memberships = build_memberships("stable", reference)

# Tập active users kỳ vọng độc lập từ thiết kế stable: A12 và K12.
users = [f"u{i:03d}" for i in range(1, 13)]
users += [f"u{i:03d}" for i in range(101, 113)]
snapshots = sample_snapshots(
    memberships,
    expected_reference=reference,
    expected_users_by_month={"2020-01": users, "2020-02": users},
    generator_seed=11,
)
for snapshot in snapshots:
    print(snapshot.month, len(snapshot.nodes), len(snapshot.edges))
# 2020-01 24 76
# 2020-02 24 53
```

Khi dùng fixture đã export, lấy expected user lists bằng `read_nodes` và membership bằng `read_memberships`; xem [hướng dẫn fixture PHUC-001](../001-truth-fixtures/README.md).

## Kiểm tra và phạm vi

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

T02 đã chạy 70 test liên quan, gồm sáu test mới cho bộ đáp án sáu case và kiểm tra lại exporter/consumer cũ. [Bằng chứng T01](../evidence/PHUC-002-T01-stable-graphs.md) vẫn ghi lần kiểm tra riêng trước đó: 55 test, số cạnh stable, within/between, isolate và hashes.

T01/T02 có sampler và truth trong bộ nhớ. CSV/JSON kiểm chứng do runner local ghi để đối chiếu; API export graph đầy đủ kèm metadata/hashes thuộc T04. Tiếp theo T03 tạo file cấu hình chung cho probabilities, các case, lịch seed development/evaluation và quy tắc ordering. Chưa chạy Leiden/AMI/tracker trên các case mới.
