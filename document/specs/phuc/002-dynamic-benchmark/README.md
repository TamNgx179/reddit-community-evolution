# Sampler stable hai tháng — PHUC-002-T01

Sampler lấy membership chuẩn từ PHUC-001 rồi xét từng cặp user trong mỗi tháng. Hai user cùng community có xác suất nối cạnh `p_in=0.50`; khác community dùng `p_out=0.02`. Cạnh vô hướng, chỉ ghi một chiều source < target, weight 1.0.

`stable` nghĩa là thành viên A→C giữ nguyên và K giữ nguyên; cạnh được lấy mẫu mới mỗi tháng. Node hoạt động được giữ riêng với cạnh, nên user không có cạnh vẫn xuất hiện trong `.nodes`.

## API đã có

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
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_truth tests.unit.test_synthetic_io tests.unit.test_contracts -v
```

Đã chạy 55 test liên quan, gồm 10 test sampler mới. [Bằng chứng T01](../evidence/PHUC-002-T01-stable-graphs.md) ghi số cạnh, within/between, isolate, hashes, seed/config và file CSV kiểm chứng local.

T01 cung cấp sampler trong bộ nhớ và lần chạy stable thực tế. CSV kiểm chứng được runner local ghi để đối chiếu; API export graph đầy đủ kèm metadata/hashes thuộc T04. T02 sẽ mở rộng truth đủ sáu sự kiện; config lịch seed và bộ kiểm tra đủ sáu case vẫn là các task riêng. Chưa chạy Leiden/AMI/tracker trên graph này.
