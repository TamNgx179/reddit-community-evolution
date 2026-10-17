# Bằng chứng PHUC-001-T04 — Events/links chuẩn stable/grow

**Task:** [PHUC-001-T04](../tasks.md#phuc-001). **Kết quả:** DONE.
**Kiểm tra hoàn tất:** 17/10/2026 21:52:10, Asia/Bangkok (UTC+07:00).
**Môi trường:** project `.venv`, Python 3.12.6; source cơ sở commit `28f1ea6` cộng thay đổi T04 trong working tree, nhánh `feat/phuc-001-ground-truth-events`.

## Đã triển khai

- [scenarios.py](../../../../src/reddit_sna/benchmarks/scenarios.py): `TruthEvent`, `PlantedTransitions`, `build_transitions()` và kiểm tra input chung với `build_memberships()`.
- [test_synthetic_truth.py](../../../../tests/unit/test_synthetic_truth.py): thêm 11 test cho nhãn, links, nguồn/đích, quan sát thiếu successor, đổi năm, input lỗi và tính độc lập với membership.
- [Contract](../contracts.md#api-truth-eventslinks-hiện-có): mô tả API, ánh xạ trường sang schema CSV và phạm vi quan sát.

Truth được khai báo từ thiết kế case; không chạy Jaccard/Leiden, không lấy nhãn do tracker dự đoán và không tính overlap để suy ra nhãn chuẩn. API membership T02 giữ nguyên tập thành viên và thứ tự record.

## Kết quả gọi API thật

Với source `2020-01`, target `2020-02`, cùng reference của từng dataset:

| Case | Event nguồn A | Link nguồn A | Event nguồn K | Link nguồn K | Tổng events / links |
|---|---|---|---|---|---|
| stable | stable | A→C | stable | K→K | 2 / 2 |
| grow | grow | A→C | stable | K→K | 2 / 2 |

- Mỗi nguồn có đúng một nhãn; các đích thuộc membership tháng sau. Giữ cùng reference và nối đúng tháng liên tiếp.
- Tháng cuối `2020-02` không có event nguồn, không được tự gán dissolve.
- Khi `observed_months=["2020-01"]` hoặc `["2020-02"]`, cả hai case trả **0 events / 0 links**. Không có cặp tháng liên tiếp được quan sát đầy đủ thì không tạo chuyển tiếp.
- Đảo thứ tự hai tháng quan sát không đổi kết quả. Đổi start sang `2020-12` tạo chuyển tiếp sang `2021-01`.
- Từ chối case chưa hỗ trợ, reference/tháng sai, danh sách quan sát rỗng/trùng, chuỗi đơn thay iterable hoặc tháng nằm ngoài fixture.

## Cách kiểm tra lại

Chạy từ root repo bằng project interpreter:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts tests.unit.test_leiden -v
```

**Kết quả thực tế:** 45/45 pass, 0 skip/failure/error; unittest 1.511s, subprocess wall 2.583s. Đây là suite liên quan gồm CSV, truth, shared contracts và Leiden hiện có; không phải toàn bộ test của repo.

Ví dụ đọc trực tiếp từ Python, không cần notebook, graph hay tracker:

```python
from reddit_sna.benchmarks.scenarios import build_transitions

truth = build_transitions("grow", "truth-grow-example")
print([(e.source.community_id, e.event.value) for e in truth.events])
# [('A', 'grow'), ('K', 'stable')]
print([(link.source.community_id, link.target.community_id) for link in truth.links])
# [('A', 'C'), ('K', 'K')]

partial = build_transitions(
    "grow", "truth-grow-example", observed_months=["2020-01"],
)
assert partial.events == () and partial.links == ()
```

## Artifact kiểm chứng và source hashes

Artifact **local, bị Git ignore**, tại `artifacts/verification/phuc-001-t04-001/`:

- `unit-tests.log`: output suite thực tế.
- `transition-summary.json`: events/links hai case và số record khi quan sát từng tháng riêng; đây là JSON kiểm chứng, không phải gói CSV bàn giao.
- `verification-result.json`: interpreter, command, thời điểm, test counts, source base, thời gian và hashes.
- `verify.py`: script local chạy suite và sinh summary nêu trên. Thành viên khác dùng lệnh/snippet trong tài liệu này để kiểm tra lại; các file local không tự có trên GitHub.

SHA-256 file tại thời điểm chạy:

| File | SHA-256 |
|---|---|
| `src/reddit_sna/benchmarks/scenarios.py` | `c91fc5ef008ff082af33e095b79a95ddafd46f1574c5172aea27d22807859b7c` |
| `src/reddit_sna/benchmarks/__init__.py` | `6adfbe6b3a04ff92f4ab8b61ea1cf943ae7abeb8d55cbe5e6925d9c47222e217` |
| `tests/unit/test_synthetic_truth.py` | `d5193942ecc2c3313596470fcead7fa18fc83eb072bd4cd41b04a3cc8c9b6bf4` |
| `transition-summary.json` local | `2d573576287105c45860af2448f4b513b563d169cc6822bfb9d1d51e215e1a34` |

## Phạm vi hoàn thành

T04 đáp ứng FR03 về sinh events/links chuẩn trong bộ nhớ cho stable/grow, gồm nhóm nền và quy tắc successor. Nhãn/links không phụ thuộc phần tracker của Đăng, nên không cần chờ Đăng để tự kiểm tra task này.

T05 vẫn TODO: cần hoàn thiện kiểm tra fixture theo phạm vi task. T06 vẫn TODO: CSV events/links, metadata và gói export/bàn giao chưa triển khai. Chưa có graph benchmark, AMI hoặc xác nhận Đăng đã nhận/accepted dữ liệu. PR #5 chỉ chứa T01–T03; thay đổi T04 ở nhánh riêng, chưa commit/push tại thời điểm ghi bằng chứng.
