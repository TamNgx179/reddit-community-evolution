# Bằng chứng PHUC-002-T01 — Graph stable hai tháng, seed 11

**Task:** [PHUC-002-T01](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hiện 1/6 task.
**Kiểm tra hoàn tất:** 18/10/2026 09:23:35, Asia/Bangkok (UTC+07:00).
**Môi trường:** project `.venv`, Python 3.12.6. Source cơ sở `306175f` cộng thay đổi T01 khi chạy, nhánh `feat/phuc-002-stable-graphs`.

## Đã triển khai

- [dynamic.py](../../../../src/reddit_sna/benchmarks/dynamic.py): `SampledSnapshot`, `sample_snapshots()`, sampler version 1 và RNG protocol tường minh.
- [test_dynamic_benchmark.py](../../../../tests/unit/test_dynamic_benchmark.py): 10 test ban đầu cho mô hình cạnh, nodes/isolate, thứ tự, seed, input lỗi, tháng rỗng/đổi năm và process riêng.
- [Hướng dẫn API](../002-dynamic-benchmark/README.md) và [contract](../contracts.md#sampler-graph-hiện-có--phuc-002-t01).

Sampler kiểm tra membership với reference và user lists độc lập từ caller. Cạnh được sinh trực tiếp từ membership chuẩn; không chạy detector, tracker hay evaluation, không thêm cạnh để loại isolate.

## Dữ liệu và kết quả thực tế

Input là fixture đã kiểm tra ở PHUC-001-T06:

`artifacts/detection-tracking/phuc-001-t06-001/datasets/dev-stable-easy-g11/`

Đọc hai `nodes.csv` bằng `read_nodes`, rồi `truth/membership.csv` bằng `read_memberships` với expected reference `truth-dev-stable-easy-g11` và các node lists vừa đọc. Input metadata SHA-256: `79d62e6430953ad5fb796549dc45b034819dfcf569de62dfac37a3877e0b99f6`.

Cấu hình cố định trước khi sinh: seed **11**, `p_in=0.50`, `p_out=0.02`, weight **1.0**. RNG protocol `python-random-sequential-months-sorted-pairs-v1`: một local `random.Random`, tháng tăng dần và cặp user đã sort, một draw/cặp kể cả p=0/1.

| Tháng | Nhóm chuẩn | Active nodes | Cạnh trong nhóm | Cạnh khác nhóm | Tổng cạnh | Endpoint nodes | Isolate |
|---|---|---|---|---|---|---|---|
| 2020-01 | A12 + K12 | 24 | 72 | 4 | 76 | 24 | 0 |
| 2020-02 | C12 + K12 | 24 | 50 | 3 | 53 | 24 | 0 |

Stable giữ thành viên A→C và K→K; hai tháng lấy mẫu cạnh mới. Không chọn lại seed hoặc ép số cạnh để có điểm detection đẹp. Chưa tính AMI/F1.

Hai lần sinh, trong đó lần hai đảo thứ tự membership đầu vào, cho cùng graph records và **bốn file CSV bằng nhau từng byte**. Mỗi file `R.csv` có header `month,source_user_id,target_user_id,weight`; cạnh source < target, không trùng/self-loop và weight 1.0. Node files giữ toàn bộ active users.

Diagnostic `p_in=p_out=0`: cả hai tháng **24 nodes, 0 edges**, toàn bộ 24 user là isolate và vẫn giữ trong `.nodes`. Đây là diagnostic của sampler, không phải kết quả detection.

## Kiểm tra

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_truth tests.unit.test_synthetic_io tests.unit.test_contracts -v
```

**55/55 test pass, 0 skip/failure/error**, unittest 3.517s; subprocess wall 3.977s. Suite liên quan gồm 10 test sampler mới và 45 test truth/CSV/contracts hiện có; không phải toàn bộ test repo.

Các test sampler kiểm tra:

- Hai tháng giữ đúng 24 user và cạnh canonical hợp lệ; seed 11 lấy mẫu cạnh mới theo tháng.
- `p_in=1,p_out=0` tạo hai clique 12 user, 132 cạnh/tháng; `p_in=0,p_out=1` tạo đúng 144 cạnh giữa hai nhóm; cả hai p=1 tạo 276 cặp vô hướng duy nhất.
- p=0 giữ isolate, tháng quan sát rỗng vẫn có record; đổi năm được giữ đúng.
- Đảo membership/user/month và đổi tên community cục bộ không đổi graph; seed 12 cho graph khác trong fixture này.
- Hai Python process có `PYTHONHASHSEED=0/137` cho cùng graph records; global RNG không đổi.
- Từ chối seed/xác suất sai, duplicate membership, user thiếu/lạ, reference trộn hoặc tháng ngoài quan sát.

Generation wall cho riêng một lời gọi sampler ở lần kiểm tra: 0.004357s. Đây là thời gian toy fixture, chưa dùng làm kết luận benchmark hiệu năng.

## Artifact và hashes

Artifact **local, bị Git ignore**, ở `artifacts/verification/phuc-002-t01-001/`:

- `verification-result.json`: nguồn input, command, Python, sampler/RNG version, seed/probabilities, counts, timing và source/input/output hashes.
- `unit-tests.log`: output suite thực tế.
- `stable-seed11-1/snapshots/<month>/{R,nodes}.csv` và `stable-seed11-2/...`: hai bộ CSV kiểm chứng.
- `verify.py`: runner local đọc fixture T06, gọi sampler, ghi CSV mới và đối chiếu. Các file local không tự có khi pull Git; thành viên khác dùng [ví dụ API](../002-dynamic-benchmark/README.md) để tái tạo graph records.

SHA-256 source tại thời điểm chạy:

| File | SHA-256 |
|---|---|
| `src/reddit_sna/benchmarks/dynamic.py` | `2eb641c108f81a8d8ed39c88239a1f5233e32c06aaab34204eedf97fa2c578e1` |
| `src/reddit_sna/benchmarks/__init__.py` | `cc238cca907522b1a9fa555b07d947f55a5b7db627571b71ea1c3d53ee02774c` |
| `tests/unit/test_dynamic_benchmark.py` | `3d569cce791eb368b54237a36d286edd466a981681b78f33d25d9d0fd94b4521` |

SHA-256 CSV kiểm chứng của lần sinh đầu:

| File trong `stable-seed11-1/snapshots/` | SHA-256 |
|---|---|
| `2020-01/R.csv` | `58c34c2a7ba1297a7f536b8b5a55556ee5a8666ab9d65839a6a0876ba1476592` |
| `2020-01/nodes.csv` | `6b6f5effb438aa74fc24827011f8cddec6ebc84e4ccacff06b68ccbf1fb3c639` |
| `2020-02/R.csv` | `4ddcba4db3dbedaf4c9b294f522e132d3b17dd690d097bad15e8ac99bd5786dd` |
| `2020-02/nodes.csv` | `1cb9331c956188feb401e87ae815d621591b66b8cf97ed695be8c16fe39cc54d` |

## Phạm vi nghiệm thu

T01 đáp ứng phần FR01/FR02 của sampler stable: lấy mẫu có seed/probabilities, node đầy đủ và cạnh hợp lệ. T05 vẫn TODO vì suite đầy đủ cần sáu case, lịch seed và các diagnostics tiếp theo. T04 vẫn TODO: CSV graph ở đây do runner kiểm chứng local ghi, chưa phải API export dataset graph đầy đủ kèm metadata/hashes. Chưa chạy Leiden/AMI/tracker hoặc nghiệm thu PHUC-002 toàn bộ.

Tiếp theo **PHUC-002-T02** mở rộng truth shrink/merge/split/dissolve, giữ K và events/links đúng từng nguồn; không cần chờ Đăng.
