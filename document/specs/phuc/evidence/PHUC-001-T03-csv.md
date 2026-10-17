# Bằng chứng PHUC-001-T03 — CSV node/membership và validator

**Task:** [PHUC-001-T03](../tasks.md#phuc-001). **Kết quả:** DONE.
**Kiểm tra hoàn tất:** 16/10/2026 21:09:18, Asia/Bangkok (UTC+07:00).
**Môi trường:** project `.venv`, Python 3.12.6; source cơ sở commit `93958cc` cộng thay đổi T03 trong working tree.

## Chức năng đã triển khai

- [benchmarks/io.py](../../../../src/reddit_sna/benchmarks/io.py): `write_nodes`, `read_nodes`, `validate_memberships`, `write_memberships`, `read_memberships`.
- [Test CSV](../../../../tests/unit/test_synthetic_io.py): 18 test mới với file tổng hợp trong thư mục tạm.
- [Contract API](../contracts.md): ghi rõ tham số kỳ vọng, tháng rỗng, header/UTF-8, ordering và no-overwrite.

Membership được xác minh với reference và tập user theo tháng do caller cung cấp độc lập. Duplicate, reference/tháng sai và user thiếu/lạ bị từ chối. Node file giữ toàn bộ active users, gồm cả isolate; adapter không tự đoán từ graph hay tự lấy giao user để bỏ các dòng sai.

CSV phải đúng header và số cột, UTF-8 không BOM. Writer sort dữ liệu, dùng LF và file mới; reader giữ ID hợp lệ, xử lý CSV quoting cho Unicode/dấu phẩy/dấu nháy. Tháng rỗng được quan sát có thể biểu diễn bằng file chỉ có header khi kỳ vọng user tháng đó cũng rỗng.

## Kiểm tra đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts -v
```

Kết quả: **31/31 test pass**, gồm **18 test CSV mới** và **13 test membership/contract hiện có**; **0 skip, 0 failure, 0 error**, exit code 0. Unittest báo **0.212 giây**, wall time subprocess **0.632 giây**.

Các nhóm hành vi được kiểm tra:

- Round-trip stable/grow qua node CSV từng tháng và membership CSV.
- Unicode, quoting và output canonical có cùng byte dù đảo thứ tự input.
- Tháng quan sát rỗng; tháng ngoài kỳ vọng/không liên tiếp và kỳ vọng thiếu tháng.
- Duplicate node; duplicate membership kể cả khác community; user thiếu hoặc ngoài dataset.
- Reference rỗng/sai/trộn; ID rỗng; sai header, BOM, thiếu/thừa cột, quoting hỏng hoặc dòng trống.
- Validation trước khi tạo file, không tự tạo parent, không sửa file đầu vào và không ghi đè output cũ.

Đây là kiểm tra liên quan đến T03. Chưa chạy full suite hoặc installed-wheel validation. T05 vẫn TODO vì kiểm tra đầy đủ nhãn sự kiện và export/gói bàn giao cần T04/T06.

## Lượt CSV thực tế ngoài unit test

Đã sinh membership trong bộ nhớ bằng T02, ghi node/membership CSV vào thư mục xác minh mới rồi đọc lại bằng API T03:

| Case | User 2020-01 | User 2020-02 | Record membership | Đọc lại bằng bản gốc |
|---|---:|---:|---:|---|
| stable | 24 | 24 | 48 | Có |
| grow | 24 | 30 | 54 | Có |

Nhóm nền K có 12 người trong mỗi tháng. Đường dẫn cục bộ: `artifacts/verification/phuc-001-t03-001/roundtrip/{stable,grow}/`. Mỗi case có hai file `<month>-nodes.csv` và `membership.csv`.

Đây là fixture xác minh API, chưa phải gói bàn giao T06 có events/links/manifest đầy đủ; chưa có xác nhận nhận dữ liệu của Đăng.

## Ví dụ sử dụng

Đoạn sau dùng thư mục tạm để không ghi đè dữ liệu có sẵn:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from reddit_sna.benchmarks.scenarios import build_memberships
from reddit_sna.benchmarks.io import (
    read_memberships, read_nodes, write_memberships, write_nodes,
)

rows = build_memberships("grow", "truth-grow-example")
with TemporaryDirectory() as directory:
    root = Path(directory)
    nodes = {}
    for month in ("2020-01", "2020-02"):
        path = root / f"{month}-nodes.csv"
        write_nodes(path, month, [r.user_id for r in rows if r.month == month])
        nodes[month] = read_nodes(path, expected_month=month)
    expected = dict(
        expected_reference="truth-grow-example",
        expected_users_by_month=nodes,
    )
    write_memberships(root / "membership.csv", rows, **expected)
    assert read_memberships(root / "membership.csv", **expected) == rows
```

## Log và hashes

Thư mục cục bộ: `artifacts/verification/phuc-001-t03-001/`.

| File | SHA-256 |
|---|---|
| `unit-tests.log` | `1875db34184346c527e9bd4b37c18a10f62c3a49e6f152ae93e7a96c57407981` |
| `test-command.json` | `ccdc16480186fb08045af7498115dd533321f072e38007ccab2917e2bbcf7086` |
| `roundtrip-summary.json` | `95b58bdcb3e8c26838beef0d6e2b81199813ecae2eddf3a48267e3996565b30c` |

`verification-result.json` lưu hashes của tất cả CSV xác minh và source/test đã chạy:

- `src/reddit_sna/benchmarks/io.py`: `63e534c39d04c4a09fdda23d4d0cfd9144fe817b0a0fc4ce9ee8a90ac3cab4c5`.
- `tests/unit/test_synthetic_io.py`: `c8386211f761b45df2454fed455f82e4442359c06f8eb31d55f304db1ef6d6c4`.

Artifact được ignore và chỉ ở máy hiện tại. Bản ghi này công khai kết quả và cách kiểm tra lại, không coi log cục bộ đã có trên GitHub. T04 sẽ bổ sung events/links; T03 chưa sinh graph, chạy detector hoặc tính AMI.
