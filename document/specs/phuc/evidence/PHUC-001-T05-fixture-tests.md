# Bằng chứng PHUC-001-T05 — Kiểm tra fixture và tính tái lập

**Task:** [PHUC-001-T05](../tasks.md#phuc-001). **Kết quả:** DONE.
**Kiểm tra hoàn tất:** 17/10/2026 22:06:54, Asia/Bangkok (UTC+07:00).
**Môi trường:** project `.venv`, Python 3.12.6; source cơ sở commit `391187b` cộng thay đổi test T05 trong working tree. Nhánh `feat/phuc-001-ground-truth-events`.

## Kiểm tra bổ sung

Thêm ba test trong lớp `TruthFixtureTests` của [test_synthetic_truth.py](../../../../tests/unit/test_synthetic_truth.py). T05 bổ sung kiểm tra phối hợp giữa generator, CSV và truth; code sinh dữ liệu T02–T04 giữ nguyên.

| Test | Cách đối chiếu | Kết quả thực tế |
|---|---|---|
| `test_csv_read_independently_matches_exact_members_and_transition_truth` | Ghi CSV bằng API, đọc bằng `csv.DictReader` của Python; so với tập user kỳ vọng khai báo riêng, không suy coverage từ dữ liệu thực tế. Đối chiếu nhãn/link với các nhóm đã đọc | 4 trường hợp: stable/grow, tháng thường và chuyển năm; đúng 48/54 membership, node đầy đủ, A→C và K→K khớp truth |
| `test_corrupted_scenario_csv_is_rejected_without_changing_the_input` | Sửa từng CSV thành duplicate, một user ở hai nhóm, thiếu user, user lạ, trộn reference hoặc tháng ngoài fixture; đọc bằng adapter với tập user kỳ vọng độc lập | 12 trường hợp bị từ chối đúng lỗi; byte của file input giữ nguyên |
| `test_csv_bytes_and_transition_records_repeat_in_fresh_python_processes` | Mỗi case chạy hai Python process mới với `PYTHONHASHSEED=0` và `137`; input user/tháng đi qua set để thay thứ tự lặp; so byte node/membership CSV và records events/links | 4 tiến trình thành công; ba CSV của mỗi case giống từng byte; nhãn/link giữ đúng nội dung và thứ tự |

## Bao phủ yêu cầu của task

| Requirement | Bằng chứng kiểm tra |
|---|---|
| FR01 — thành viên chuẩn | Tập user kỳ vọng độc lập cho A12→C12/C18, K12; cả mốc thường và đổi năm; các test `PlantedMembershipTests` hiện có |
| FR02 — khóa/schema/coverage | CSV đọc bằng stdlib, header và khóa duy nhất; 12 tình huống dữ liệu bị sửa sai; suite `SyntheticCsvTests` hiện có kiểm tra chi tiết adapter |
| FR03 — nhãn/link/successor | Đối chiếu event với user nguồn/đích đọc từ CSV; `PlantedTransitionTests` hiện có kiểm tra K, mỗi nguồn một nhãn, tháng cuối và thiếu successor |
| FR04 — phần kiểm tra output/tái lập của T05 | So byte node/membership CSV và records events/links qua process mới; các test no-overwrite hiện có trong `SyntheticCsvTests` cũng được chạy |

T05 hoàn thành phần kiểm tra fixture đang có. Nghiệm thu **toàn FR04 và spec PHUC-001** còn cần T06 bổ sung export CSV events/links, metadata/config/version/seed và gói đọc độc lập; các đầu ra đó chưa được test ở T05 vì chưa được triển khai.

## Lệnh và kết quả

Chạy từ root repo:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts tests.unit.test_leiden -v
git diff --check
```

**Kết quả:** 48/48 test pass, 0 skip/failure/error. Unittest 4.150s; subprocess wall 5.033s. Kiểm tra whitespace đạt. Đây là suite liên quan, không phải toàn bộ test của repo.

Chạy riêng ba test mới khi muốn kiểm tra nhanh:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_truth.TruthFixtureTests -v
```

Ba test mới đã chạy trong suite 48 test ở trên; không ghi nhận thêm một lượt chạy riêng. Các CSV tạm được tạo trong thư mục tạm của test, không phải gói artifact bàn giao cho Đăng.

## Artifact và hashes

Artifact **local, bị Git ignore**, tại `artifacts/verification/phuc-001-t05-001/`:

- `unit-tests.log`: output suite thực tế, gồm ba test mới và các test liên quan hiện có.
- `verification-result.json`: Python, source base, command, thời điểm, test counts, số tình huống fixture, thời gian và SHA-256 source/log.

Thành viên khác dùng các lệnh trên để tái tạo; artifact local không tự có trên GitHub.

SHA-256 file tại thời điểm chạy:

| File | SHA-256 |
|---|---|
| `tests/unit/test_synthetic_truth.py` | `0cdb1f2cda28d1a0c05effbb220fb01f1e2fb91056e80230d70e91a476eb9214` |
| `tests/unit/test_synthetic_io.py` | `c8386211f761b45df2454fed455f82e4442359c06f8eb31d55f304db1ef6d6c4` |
| `src/reddit_sna/benchmarks/scenarios.py` | `c91fc5ef008ff082af33e095b79a95ddafd46f1574c5172aea27d22807859b7c` |
| `src/reddit_sna/benchmarks/io.py` | `63e534c39d04c4a09fdda23d4d0cfd9144fe817b0a0fc4ce9ee8a90ac3cab4c5` |
| `unit-tests.log` local | `d6ee01deada7c7a484fc1e6fc757efa5df85eb604c261d3396efecdb0b098cc3` |

T05 chưa sinh graph hay chạy AMI/tracker. Việc Đăng nhận/accepted dữ liệu vẫn là mốc riêng. Task tiếp theo là **PHUC-001-T06: export fixture stable/grow đầy đủ và ghi lệnh đọc độc lập**.
