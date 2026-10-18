# Bằng chứng PHUC-002-T02 — Đáp án chuẩn đủ sáu tình huống

**Task:** [PHUC-002-T02](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hiện 2/6 task.
**Kiểm tra hoàn tất:** 18/10/2026 09:33:35, Asia/Bangkok (UTC+07:00).
**Môi trường:** `.venv`, Python 3.12.6. Source cơ sở `8b56ab0` cộng thay đổi T02 khi chạy, nhánh `feat/phuc-002-stable-graphs`.

## Vừa làm gì, dùng để làm gì

Đã mở rộng bộ sinh đáp án trong [scenarios.py](../../../../src/reddit_sna/benchmarks/scenarios.py) từ stable/grow thành đủ sáu tình huống. Bộ sinh tạo sẵn danh sách người thuộc từng nhóm, nhãn biến đổi của nhóm nguồn và liên kết tới nhóm đích.

Đây là bộ đề kèm đáp án: Đăng có thể cho tracker đọc membership rồi đối chiếu dự đoán với events/links chuẩn. Bộ sinh tự khai báo kịch bản, không lấy kết quả Jaccard/Leiden làm đáp án.

| Case | Nhóm chính trước → sau | Nhãn và liên kết nguồn chính |
|---|---|---|
| stable | 12 → cùng 12 người | A stable, A→C |
| grow | 12 → 18 người, giữ 12 cũ | A grow, A→C |
| shrink | 18 → giữ 12 người cũ | A shrink, A→C; 6 người còn lại không còn hoạt động |
| merge | A12 + B12 → hợp thành C24 | A và B mỗi nguồn một merge, A→C và B→C |
| split | A24 → B12 + C12 không chồng nhau | A có một split, hai liên kết A→B và A→C |
| dissolve | A12 → không còn hoạt động | A dissolve, không link đích; K vẫn tiếp tục |

K có 12 user riêng và một nhãn stable/link K→K trong mọi case. Với dissolve, tháng sau đã được quan sát và bộ sinh chủ động loại A; thiếu tháng sau không tự gán dissolve.

## Kết quả gọi API thật

Mỗi case dùng reference `truth-dev-<scenario>-easy-g11`, hai tháng `2020-01`, `2020-02`. Seed trong tên reference giữ quy ước dataset; API truth không dùng random.

**Các counts dưới đây gồm cả K:**

| Case | Active users trước / sau | Membership rows hai tháng | Events | Links |
|---|---|---|---|---|
| stable | 24 / 24 | 48 | 2 | 2 |
| grow | 24 / 30 | 54 | 2 | 2 |
| shrink | 30 / 24 | 54 | 2 | 2 |
| merge | 36 / 36 | 72 | 3 | 3 |
| split | 36 / 36 | 72 | 2 | 3 |
| dissolve | 24 / 12 | 36 | 2 | 1 |

Hai lần gọi mỗi builder trả cùng records; JSON kiểm chứng của sáu case bằng byte giữa hai lần ghi. Khi chỉ quan sát một trong hai tháng, cả sáu case trả **0 event / 0 link**; tháng cuối không trở thành nguồn sự kiện.

## Kiểm tra và tương thích

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

**70/70 test pass, 0 skip/failure/error**; unittest 6.389s, subprocess wall 6.726s. Đây là suite liên quan, không phải toàn bộ test repo.

Sáu test mới trong `SixEventScenarioTests` của [test_synthetic_truth.py](../../../../tests/unit/test_synthetic_truth.py) kiểm tra:

- Đúng tập user độc lập cho cả sáu case; một membership/user/tháng, reference đúng và K không chồng nhóm chính.
- Một nhãn cho mỗi nguồn; merge có hai nguồn main, split một event/hai links, dissolve không có link rỗng.
- Merge/split bảo toàn đúng tập thành viên; shrink loại đúng 6 người, dissolve loại toàn bộ A khỏi tháng sau.
- Thiếu successor không gán nhãn, không tự gán dissolve cho tháng cuối.
- Thứ tự canonical, tái lập và mốc `2020-12→2021-01`.
- Membership cả sáu case đi qua sampler với tập active users kỳ vọng đúng; p=0 vẫn giữ đầy đủ node.

**Tương thích stable/grow:** export lại hai fixture bằng API hiện tại vào thư mục kiểm chứng mới; cả **12 file** gồm CSV và metadata giống bản PHUC-001-T06 từng byte. Consumer isolated đọc hai fixture export lại thành công.

Exporter/CLI/consumer PHUC-001 vẫn chỉ hỗ trợ stable/grow. Thêm guard trong [io.py](../../../../src/reddit_sna/benchmarks/io.py) và mở rộng test input lỗi để bốn case mới bị từ chối **trước khi tạo output**. Điều này ngăn ghi metadata stable/grow không đúng cho case mới trước khi T04 triển khai export sáu case đầy đủ.

## Artifact và hashes

Artifact **local, bị Git ignore**, tại `artifacts/verification/phuc-002-t02-001/`:

- `verification-result.json`: command/counts/timing/source hashes và summary events/links của sáu case.
- `unit-integration-tests.log`: output suite thực tế.
- `six-event-truth-1/<scenario>.json`, `six-event-truth-2/<scenario>.json`: records kiểm chứng, không phải gói CSV export benchmark.
- `stable-grow-regression/`: hai fixture export lại; `reader-stable.log`, `reader-grow.log` ghi consumer pass.
- `verify.py`: runner local tạo/đối chiếu các output trên. Thành viên khác dùng [API và ví dụ](../002-dynamic-benchmark/README.md) để tái tạo; các artifact local không tự đi theo Git.

SHA-256 source tại thời điểm chạy:

| File | SHA-256 |
|---|---|
| `src/reddit_sna/benchmarks/scenarios.py` | `8fb1a8eb65ef9c070e2d7c033503c89ddd97bf32962263354612a00ce2309203` |
| `src/reddit_sna/benchmarks/io.py` | `ee4c6a1245bb554f0613d1d34f31dec67ffd562f603b80a6f6db9be210d3b44d` |
| `src/reddit_sna/benchmarks/__init__.py` | `96d4fc907b780696fa0473990c9bb2667f5ad158cc9a8d6c9a804ed1d0f3b137` |
| `tests/unit/test_synthetic_truth.py` | `5c06e362667899c41f47dcdccafe35e2e9af43222d44d6667de0e0b24379e1cb` |
| `tests/unit/test_truth_fixture_export.py` | `92902121c02810ea2ddd34529e34d0018b21a9dea18a7719e33317c34aa70df9` |

`verification-result.json` lưu SHA-256 từng JSON case. Chưa có kết quả tracker/AMI hoặc gói graph benchmark đủ sáu case. T02 đáp ứng FR03 ở tầng membership/events/links; T04/T05/T06 còn phần export/kiểm tra/lượt chạy đầy đủ của spec.

Tiếp theo **PHUC-002-T03** đưa probabilities, case, lịch seed development/evaluation và quy tắc ordering vào file cấu hình chung.
