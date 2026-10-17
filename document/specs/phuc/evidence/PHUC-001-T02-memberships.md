# Bằng chứng PHUC-001-T02 — membership chuẩn stable/grow

**Task:** [PHUC-001-T02](../tasks.md#phuc-001). **Kết quả:** DONE.
**Kiểm tra hoàn tất:** 16/10/2026 19:15:07, Asia/Bangkok (UTC+07:00).
**Môi trường:** project `.venv`, Python 3.12.6, package editable 0.1.0.

## Code đã triển khai

- [scenarios.py](../../../../src/reddit_sna/benchmarks/scenarios.py): hàm `build_memberships(scenario, reference_id, *, start_month="2020-01")` trả `tuple[Membership, ...]`, dùng contract đã có.
- [Test membership](../../../../tests/unit/test_synthetic_truth.py): tám test hành vi cho phạm vi T02.
- Cập nhật mô tả package `benchmarks/__init__.py` để phản ánh phần membership đã có và các bước khác còn chờ triển khai.

Đây là phân hoạch chuẩn đặt trước thuật toán, hoàn toàn trong bộ nhớ. Hàm không đọc/ghi file, không gọi detector/tracker hoặc nguồn ngẫu nhiên. Seed sinh graph thuộc bước sau; tên reference do caller truyền vào chỉ giới hạn phạm vi định danh.

## Kết quả thực tế

Mỗi tình huống gồm hai tháng 2020-01 và 2020-02:

| Tình huống | Nhóm chính tháng 1 | Nhóm chính tháng 2 | Giữ lại / thêm / mất | K | User hoạt động mỗi tháng | Số record membership |
|---|---|---|---|---|---|---|
| stable | A: 12 người | C: đúng 12 người cũ | 12 / 0 / 0 | 12 người không đổi | 24 -> 24 | 48 |
| grow | A: 12 người | C: 18 người | 12 / 6 / 0 | 12 người không đổi | 24 -> 30 | 54 |

- Nhóm chính A đổi tên thành C; tập thành viên được so bằng user ID, không bằng community ID.
- User chính dùng ID tổng hợp `u001` trở đi; K dùng `u101`–`u112`, không giao với nhóm chính.
- Mỗi user chỉ có một membership trong một tháng; mọi record dùng reference caller yêu cầu.
- Thứ tự record cố định theo tháng, community, user; gọi lặp lại hoặc xen kẽ các scenario không làm đổi kết quả.
- Có thể chọn tháng bắt đầu khác; kiểm tra 2020-12 chuyển sang 2021-01 đã pass.
- Scenario chưa hỗ trợ, reference rỗng và tháng không hợp lệ bị từ chối.

## Kiểm tra đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_truth tests.unit.test_contracts -v
```

Kết quả: **13/13 tests pass**, gồm **8 test mới** và **5 test contract hiện có**; **0 skip, 0 failure, 0 error**, exit code 0. Unittest báo **0.009 giây**, wall time subprocess **0.697 giây**.

Tám test mới kiểm tra giữ thành viên stable, grow giữ 12 cũ/thêm 6 mới, K ổn định và disjoint, membership duy nhất/reference đúng, tái lập/thứ tự, chuyển năm và từ chối input không hợp lệ. Đây là kiểm tra chức năng membership; T05 vẫn TODO vì kiểm tra đầy đủ CSV/nhãn/export/tái lập dataset cần các bước T03/T04/T06.

Lượt này chạy các test liên quan nêu trên, chưa chạy full suite, installed-wheel validation hoặc benchmark detection/tracking.

## Cách gọi lại

Chạy trong Python của project đã cài editable:

```python
from reddit_sna.benchmarks.scenarios import build_memberships

stable = build_memberships("stable", "truth-stable-example")
grow = build_memberships("grow", "truth-grow-example")
print(len(stable), len(grow))  # 48 54

# Một record có reference_id, month, community_id và user_id.
print(grow[0])
```

## Log và hashes của lượt xác minh

Thư mục cục bộ: `artifacts/verification/phuc-001-t02-001/`. Output JSON dưới đây là bằng chứng chạy API, không phải bộ CSV bàn giao của T06.

| File | Nội dung | SHA-256 |
|---|---|---|
| `scenario-summary.json` | Membership thực tế và số lượng từng tháng/nhóm | `3c4465c19a9ea79f5ac7f0c217abcf9eea011faf31292d2075346a8097f846d4` |
| `test-command.json` | Interpreter, lệnh test, thời điểm, exit code, wall time | `f6a855fcb724d1bf45ba20e2c6dc84f5f471d4d5a78d024f9d7618bf7fe4fef9` |
| `unit-tests.log` | Output đầy đủ của 13 test | `3c963fa376081a560886bebec4501d5df509e5ef9ff83ab9cd4b4ec917d95cc6` |

`verification-result.json` lưu kết quả tổng hợp và hash source/test đã chạy:

- `src/reddit_sna/benchmarks/scenarios.py`: `7cfa527801b672add1a2cd8248a2e366fcc5ad808fb7c3e04d2bec9927e15c96`.
- `tests/unit/test_synthetic_truth.py`: `9ee1e93cd776bb29e721b2d6cff14f81ef42b1fe969501a3e7a0ff3115430d81`.

Artifact được ignore và chỉ nằm trên máy hiện tại. Chưa có CSV adapter/validator dataset (T03), events/links (T04), gói bàn giao (T06), graph, điểm AMI hoặc xác nhận nhận dữ liệu từ Đăng trong phạm vi T02.
