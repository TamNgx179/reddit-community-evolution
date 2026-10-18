# Theo dõi công việc Phúc — tuần 1

**Nguồn trạng thái chính:** file này. **Owner mọi task PHUC:** Phúc. **Tạo bảng:** 16/10/2026. **Mốc chung nội bộ:** tối 20/10; 21/10 dự phòng, 22/10 báo cáo theo lịch repo.

**Tiến độ:** 15/36 task triển khai hoàn thành: PHUC-001/002 DONE toàn bộ, PHUC-003-T01/T02/T03 DONE. Exporter lưu membership/diagnostics/config/metadata mapping; hai gói stable có 9 file/6 mapping mỗi gói, đọc được sau khi copy; CSV/log/ZIP đã lưu. Tiếp theo PHUC-003-T04 audit endpoint/empty/dependency/input lỗi/output cũ; chưa tính AMI hoặc chạy evaluation.

## Bảng tổng quan cho thành viên nhóm

| Spec | Phạm vi | Mốc nội bộ năm 2026 | Trạng thái | Task DONE | Đang làm / vướng mắc / bằng chứng |
|---|---|---|---|---|---|
| [PHUC-001](001-truth-fixtures/spec.md) | Truth stable/grow và fixture | 16/10 | DONE | 6/6 | 75 test liên quan pass; 2 run export/đọc độc lập, 12 file dataset giống byte, giữ output cũ. [Bằng chứng T06](evidence/PHUC-001-T06-export.md) |
| [PHUC-002](002-dynamic-benchmark/spec.md) | Graph và sáu sự kiện | 18/10 | DONE | 6/6 | 105 test liên quan pass; full development 18 dataset/36 snapshot mỗi run, 162 file giống byte, 36 reader pass; 4 diagnostic × 2 bộ khớp 24 file; báo cáo CSV/ZIP đã lưu, AC01–05 pass. [Bằng chứng T06](evidence/PHUC-002-T06-development.md) |
| [PHUC-003](003-leiden-detection/spec.md) | Adapter Leiden | Bộ đầu 17/10; đủ lịch 18/10 | DOING | 3/6 | T01/T02/T03 DONE; 66 test liên quan pass, gói detection 9 file/6 mapping; hai run khớp 6 membership, 3 lượt stdlib đọc primary/replay/relocated pass; CSV/log/ZIP đã lưu. Tiếp theo T04. [Bằng chứng T03](evidence/PHUC-003-T03-detection-package.md) |
| [PHUC-004](004-detection-evaluation/spec.md) | AMI và coverage | Bộ đầu 17/10; hoàn thiện 19/10 | TODO | 0/6 | Có thể viết evaluator bằng fixture |
| [PHUC-005](005-reproducible-runs/spec.md) | Development/evaluation tái lập | 19/10 | TODO | 0/6 | Cần đầu ra 002–004 để nghiệm thu |
| [PHUC-006](006-handoff-demo/spec.md) | Gói giao và notebook detection | 20/10 | TODO | 0/6 | Phần cá nhân chưa chờ Đăng; ghép chung tách bên dưới |

Bảng được cập nhật cùng checklist và ledger bằng chứng. Khi task đổi trạng thái, cập nhật dòng spec tương ứng trong cùng lần sửa. Checklist bên dưới là căn cứ đối chiếu nếu bảng tóm tắt lệch.

## Trạng thái và cách cập nhật

| Trạng thái | Dùng khi | Checkbox |
|---|---|---|
| TODO | Chưa bắt đầu, gồm việc có phụ thuộc dự kiến | `[ ]` |
| DOING | Đang thực hiện, ghi việc tiếp theo | `[ ]` |
| REVIEW | Có đầu ra, đang chờ review được yêu cầu | `[ ]` |
| BLOCKED | Task đang làm không thể tiếp tục vì thiếu điều kiện cụ thể | `[ ]` |
| DONE | Hoàn thành yêu cầu task và có bằng chứng kiểm tra | `[x]` |

- Mỗi dòng có ID duy nhất; `[FRxx]` tham chiếu requirement cùng spec. Ví dụ `PHUC-004-T03 [FR03]` ứng với `PHUC-004-FR03`.
- Task có nhiều FR phải đáp ứng tất cả. Task DONE nhưng không có record bằng chứng là chưa đủ để nghiệm thu.
- Cập nhật tại task, bảng tổng quan và ledger trong file này; không sửa trạng thái ở kế hoạch cũ.
- Chờ tracker chỉ gắn mốc demo chung; không gắn 001–005 BLOCKED vì Đăng chưa làm.
- Reviewer đề xuất: Đăng cho phần giao diện/detection; chưa có xác nhận nhận review. Không tự ghi review/acceptance thay thành viên.
- Quy trình chốt với Phúc ngày 17/10: sau mỗi task đã kiểm tra xong, cập nhật trạng thái/bằng chứng, commit có task ID và push nhánh đang làm; xác minh remote trước khi chuyển task tiếp theo.
- Theo yêu cầu ngày 18/10: khi hoàn thành task, giải thích dễ hiểu vừa làm gì, phần đó dùng để làm gì và kết quả cụ thể; dùng ví dụ trước/sau khi hữu ích.
- Theo yêu cầu tiếp theo ngày 18/10: lưu kết quả đầu ra, log và bằng chứng thành file; ghi rõ đường dẫn artifact local và cách tái tạo/nhận gói, không chỉ in kết quả trong chat. `artifacts/` vẫn bị Git ignore; code/fixture/docs được commit/push.

## Luồng ưu tiên tối nay

```text
001-T01 -> 001-T02/T03/T04 -> 002-T01 -> 003-T01
    -> 004-T01/T02/T03 -> một kết quả stable có AMI/coverage
```

Giao truth stable/grow cho Đăng khi đã kiểm tra được, không chờ luồng đầy đủ. T05/T06 và các spec còn lại hoàn thiện theo lịch. Có task nhỏ chạy được chưa có nghĩa toàn spec DONE.

## PHUC-001

[Đặc tả](001-truth-fixtures/spec.md). Phụ thuộc ngoài: không. Requirement và schema theo [contracts](contracts.md).

- [x] PHUC-001-T01 [DONE] [FR05] Kiểm tra project interpreter, import và chạy `tests/unit/test_leiden.py`; ghi môi trường/lệnh/pass-skip-error vào ledger của `document/specs/phuc/tasks.md`.
- [x] PHUC-001-T02 [DONE] [FR01] Viết kịch bản stable/grow và K trong `src/reddit_sna/benchmarks/scenarios.py`, user nhất quán, đích đổi tên.
- [x] PHUC-001-T03 [DONE] [FR02] Viết adapter/validator membership và node trong `src/reddit_sna/benchmarks/io.py`, chặn keys/tháng/reference/user sai.
- [x] PHUC-001-T04 [DONE] [FR03] Sinh events/links chuẩn độc lập thuật toán trong `src/reddit_sna/benchmarks/scenarios.py`, gồm K và quy tắc successor.
- [x] PHUC-001-T05 [DONE] [FR01,FR02,FR03,FR04] Thêm kiểm tra tập thành viên, nhãn, duplicate và output/tái lập trong `tests/unit/test_synthetic_truth.py`.
- [x] PHUC-001-T06 [DONE] [FR04,FR05] Export fixture stable/grow có metadata vào `artifacts/detection-tracking/<run_id>/datasets/`; ghi lệnh đọc độc lập và gói bàn giao vào ledger.

**Nghiệm thu:** tất cả AC của spec có evidence. Đăng đọc/nhận gói được ghi riêng tại mốc chung, không tự suy ra từ export thành công.

## PHUC-002

[Đặc tả](002-dynamic-benchmark/spec.md). Cần schema/truth 001; graph đầu tiên không phải đợi đủ suite hay tracker.

- [x] PHUC-002-T01 [DONE] [FR01,FR02] Viết sampler graph hai tháng stable seed 11 trong `src/reddit_sna/benchmarks/dynamic.py`, giữ nodes và cạnh hợp lệ.
- [x] PHUC-002-T02 [DONE] [FR03] Mở rộng `src/reddit_sna/benchmarks/scenarios.py` đủ shrink/merge/split/dissolve; mọi nguồn gồm K có truth.
- [x] PHUC-002-T03 [DONE] [FR01,FR04,FR05] Tạo `configs/benchmark_week1.json` với probabilities, cases, tháng, seed development/evaluation và chính sách ordering/protocol.
- [x] PHUC-002-T04 [DONE] [FR02,FR04] Hoàn thiện export R/nodes/truth/metadata/hashes và từ chối overwrite trong `src/reddit_sna/benchmarks/io.py`.
- [x] PHUC-002-T05 [DONE] [FR01,FR02,FR03,FR04,FR05] Kiểm tra seed/order, cạnh sai, xác suất biên, six-case truth, nhóm nhỏ/isolate trong `tests/unit/test_dynamic_benchmark.py`.
- [x] PHUC-002-T06 [DONE] [FR03,FR04,FR05] Sinh/đọc lại sáu case development vào output mới ở `artifacts/detection-tracking/<run_id>/`; ghi số node/cạnh/nhóm, diagnostic và kết quả đối chiếu tái lập.

**Nghiệm thu:** generator đúng theo kịch bản và contract; không phụ thuộc điểm Leiden có cao hay không.

## PHUC-003

[Đặc tả](003-leiden-detection/spec.md). Cần graph nhỏ 002 để chạy; không cần tracker.

- [x] PHUC-003-T01 [DONE] [FR01] Tích hợp lời gọi `detect_snapshots` hiện có vào API detection trong `src/reddit_sna/pipelines/detection_tracking.py`, seed 0/gamma 1/protocol synthetic đúng.
- [x] PHUC-003-T02 [DONE] [FR02] Đọc lịch seed 0/1/2 cố định từ `configs/benchmark_week1.json`, giữ canonical 0, kiểm tra cấu hình trước output.
- [x] PHUC-003-T03 [DONE] [FR03] Lưu `detection.json` và mapping dataset/reference/tháng/seed trong metadata từ `src/reddit_sna/pipelines/detection_tracking.py`.
- [ ] PHUC-003-T04 [TODO] [FR04] Kiểm tra endpoint-only membership, empty graph, dependency/input lỗi và output đã tồn tại ở adapter trong `src/reddit_sna/pipelines/detection_tracking.py`.
- [ ] PHUC-003-T05 [TODO] [FR01,FR02,FR03,FR04] Thêm integration graph nhỏ/refs/endpoint/empty/no-overwrite ở `tests/integration/test_synthetic_detection.py`.
- [ ] PHUC-003-T06 [TODO] [FR05] Chạy development thật với ba seed, lưu paths/diagnostics trong `artifacts/detection-tracking/<run_id>/`; ghi evidence và phân biệt ARI seed với AMI truth.

**Nghiệm thu:** có membership/diagnostics thật trên benchmark, không đánh DONE chỉ vì `leiden.py` đã có từ trước.

## PHUC-004

[Đặc tả](004-detection-evaluation/spec.md). Viết bằng fixture từ 001; nghiệm thu đầu ra thật cần 003.

- [ ] PHUC-004-T01 [TODO] [FR01] Viết xác minh dataset/reference/tháng/duplicate/user và căn vector nhãn bằng user ID trong `src/reddit_sna/evaluation/detection.py`.
- [ ] PHUC-004-T02 [TODO] [FR02] Tính active/endpoint/assigned/isolate/coverage và số nhóm ở đúng tập so sánh trong `src/reddit_sna/evaluation/detection.py`.
- [ ] PHUC-004-T03 [TODO] [FR03] Tính AMI và policy missing/degenerate trong `src/reddit_sna/evaluation/detection.py`; khai báo dependency thực dùng tại `pyproject.toml`.
- [ ] PHUC-004-T04 [TODO] [FR04] Xuất metrics/summary có n hợp lệ/thiếu, canonical riêng và timing đúng phạm vi từ `src/reddit_sna/evaluation/detection.py`.
- [ ] PHUC-004-T05 [TODO] [FR01,FR02,FR03,FR04] Kiểm tra đổi tên nhóm/thứ tự hàng, duplicate, user thiếu/lạ, isolate và empty/constant trong `tests/unit/test_detection_evaluation.py`.
- [ ] PHUC-004-T06 [TODO] [FR05] Chạy evaluator trên stable/grow thật, lưu `detection_metrics.csv`/`detection_summary.csv` vào run và ghi tập user chấm, config, versions, kết quả vào ledger.

**Nghiệm thu:** điểm truy ngược được đến user/input và đi kèm coverage; không đặt ngưỡng điểm đẹp làm tiêu chí DONE.

## PHUC-005

[Đặc tả](005-reproducible-runs/spec.md). Nghiệm thu cần 002–004; có thể chuẩn bị config/orchestration trước.

- [ ] PHUC-005-T01 [TODO] [FR01] Hoàn thiện/version lịch case/seed và policy trong `configs/benchmark_week1.json`; kiểm tra development/evaluation không trùng dataset/seed.
- [ ] PHUC-005-T02 [TODO] [FR02] Hoàn thiện API chạy riêng từ generator đến metrics trong `src/reddit_sna/pipelines/detection_tracking.py`, không yêu cầu tracker và không báo full pipeline complete.
- [ ] PHUC-005-T03 [TODO] [FR03] Hoàn thiện manifest lifecycle, config/source/output hashes, environment, timing và failed state tại API pipeline, dùng helper `src/reddit_sna/artifacts.py` khi phù hợp.
- [ ] PHUC-005-T04 [TODO] [FR02,FR03,FR05] Kiểm tra một run nhỏ, failure/no-overwrite và đối chiếu tái lập ở `tests/integration/test_synthetic_benchmark_run.py`; ghi log thật.
- [ ] PHUC-005-T05 [TODO] [FR01,FR04] Chạy development, lưu config khóa trước evaluation trong `artifacts/detection-tracking/<run_id>/`; ghi thời điểm/nguồn và mọi thay đổi lịch.
- [ ] PHUC-005-T06 [TODO] [FR04,FR05] Chạy lịch evaluation giữ lại, đối chiếu expected/actual/failed counts và summary trong output mới; ghi 36 dataset/72 snapshot/216 đơn vị hoặc protocol rút gọn được version trước evaluation.

**Nghiệm thu:** evidence development/freeze/evaluation tách biệt; manifest started không phải xong. Không cần artifact Đăng.

## PHUC-006

[Đặc tả](006-handoff-demo/spec.md). Truth có thể giao sớm; phần detection cuối cần 005. Mốc ghép chung bên dưới phụ thuộc Đăng, không tính vào 36 task cá nhân.

- [ ] PHUC-006-T01 [TODO] [FR01] Tạo inventory và consumer độc lập ở `src/reddit_sna/reporting/synthetic_handoff.py`, kiểm tra contract/hash và hành vi ở `tests/unit/test_synthetic_handoff.py`; lưu log thật, không ghi người nhận accepted thay họ.
- [ ] PHUC-006-T02 [TODO] [FR01,FR03] Viết `document/PHUC-DANG-WEEK1-HANDOFF.md` với schema, dataset/reference, môi trường, cách tái tạo/nhận gói và lệnh/API đã chạy thật.
- [ ] PHUC-006-T03 [TODO] [FR02] Tạo `notebooks/detection_tracking/01_synthetic_demo.ipynb` import module, hiển thị config, graph/truth/prediction, bảng AMI/coverage/timing có nguồn.
- [ ] PHUC-006-T04 [TODO] [FR04] Bổ sung phân tích case khó/sai hoặc null finding vào notebook và tài liệu bàn giao, chỉ rõ input/run/giới hạn, không bịa lỗi.
- [ ] PHUC-006-T05 [TODO] [FR02,FR03] Chạy notebook kernel sạch/output mới, kiểm tra môi trường cài đặt sạch và các gate repo phù hợp; lưu lệnh, pass/skip/error và artifact thực thi.
- [ ] PHUC-006-T06 [TODO] [FR01,FR04,FR05] Chốt gói phần Phúc, record evidence và phần thiếu trong `document/PHUC-DANG-WEEK1-HANDOFF.md`; cập nhật riêng trạng thái tracker/receipt/demo chung ở file task này.

**Nghiệm thu cá nhân:** Phúc có detection demo và gói giao kiểm tra được. **Nghiệm thu cặp:** chỉ khi các mốc Đăng bên dưới có bằng chứng thật.

## Điều kiện ghép chung với Đăng

Đây là mốc phối hợp dự kiến, không phải xác nhận Đăng đã nhận việc hoặc đã hoàn thành. Không đưa các mốc này vào tỷ lệ task cá nhân Phúc.

| Mốc | Người cung cấp/xác nhận dự kiến | Trạng thái hiện tại | Bằng chứng cần có |
|---|---|---|---|
| EXT-D01: Đăng nhận và đọc được fixture truth | Đăng | Chưa có phản hồi ghi nhận | Dataset/reference/path, lệnh đọc và phản hồi người nhận |
| EXT-D02: Tracker trên truth đủ sáu sự kiện | Đăng | Chưa có artifact bàn giao | Code/config, events/links, tests và F1/support/confusion |
| EXT-D03: Tracker trên detector và mapping | Đăng, Phúc ghép | Chưa có artifact bàn giao | Mapping/unmatched, predictions và kết quả nguồn chuẩn theo v1 |
| PAIR-DEMO: chạy hai nhánh A/B từ kernel sạch | Cả hai | Chưa nghiệm thu | Run/notebook, nguồn kết quả, review và giới hạn |

Nếu Phúc đã xong 36 task mà EXT-D02/D03 chưa có, báo “phần detection Phúc hoàn thành, demo cặp chưa hoàn thành”, không đổi PAIR-DEMO thành DONE.

## Ledger bằng chứng

Thêm một dòng khi có tiến triển kiểm tra được; có thể nhiều dòng cho một task. T01 xác minh môi trường, T02 kiểm tra membership chuẩn, T03 xác minh CSV, T04 kiểm tra events/links, T05 kiểm tra fixture phối hợp và tái lập, T06 export/đọc độc lập gói truth; chưa có kết quả benchmark detection/tracking nghiên cứu.

| Ngày/giờ Asia/Bangkok | Task ID | Code / commit / PR | Lệnh / môi trường | Kết quả và kiểm tra | Run / artifact / hash | Reviewer hoặc người nhận |
|---|---|---|---|---|---|---|
| 2026-10-16 18:37:02 +07:00 | PHUC-001-T01 | `.gitignore`; source cơ sở `8d135c9`; [bằng chứng](evidence/PHUC-001-T01-environment.md) | Python 3.12.6 `.venv`; editable `[graph,notebook]` + scikit-learn; `pip check`; `python -m unittest tests.unit.test_leiden -v` | Imports/pip check PASS; 3 tests pass, 0 skip/failure/error; unittest 1.124s | `artifacts/environment/phuc-001-t01-001/`; versions, commands, logs/freeze/hashes trong bằng chứng | Tự kiểm tra; chưa có review/acceptance từ Đăng |
| 2026-10-16 19:15:07 +07:00 | PHUC-001-T02 | `benchmarks/scenarios.py`, `tests/unit/test_synthetic_truth.py`; [bằng chứng](evidence/PHUC-001-T02-memberships.md) | Python 3.12.6; `python -m unittest tests.unit.test_synthetic_truth tests.unit.test_contracts -v`; gọi API hai case | 13/13 pass, 0 skip/failure/error; stable 48 record, grow 54 record; membership chuẩn trong bộ nhớ | `artifacts/verification/phuc-001-t02-001/`; summary, test log, hashes source/test | Tự kiểm tra; chưa có review/acceptance từ Đăng |
| 2026-10-16 21:09:18 +07:00 | PHUC-001-T03 | `benchmarks/io.py`, `tests/unit/test_synthetic_io.py`; [bằng chứng](evidence/PHUC-001-T03-csv.md) | Python 3.12.6; `python -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts -v`; CSV round-trip hai case | 31/31 pass, 0 skip/failure/error; stable 48 và grow 54 membership đọc lại đúng; chặn dữ liệu sai/no-overwrite | `artifacts/verification/phuc-001-t03-001/`; CSV xác minh, summary, test log và hashes | Tự kiểm tra; chưa có review/acceptance từ Đăng |
| 2026-10-17 21:52:10 +07:00 | PHUC-001-T04 | `benchmarks/scenarios.py`, `tests/unit/test_synthetic_truth.py`; source cơ sở `28f1ea6` + T04; [bằng chứng](evidence/PHUC-001-T04-transitions.md) | Python 3.12.6; `python -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts tests.unit.test_leiden -v`; gọi API hai case và quan sát từng tháng riêng | 45/45 pass, 0 skip/failure/error; mỗi case 2 events/2 links đúng; thiếu successor trả 0/0, không tự gán dissolve; unittest 1.511s | `artifacts/verification/phuc-001-t04-001/`; transition summary, test log, source/summary hashes | Tự kiểm tra; chưa có review/acceptance từ Đăng |
| 2026-10-17 22:06:54 +07:00 | PHUC-001-T05 | `tests/unit/test_synthetic_truth.py`; source cơ sở `391187b` + T05; [bằng chứng](evidence/PHUC-001-T05-fixture-tests.md) | Python 3.12.6; cùng suite CSV/truth/contracts/Leiden như T04; đọc CSV bằng stdlib và chạy subprocess với `PYTHONHASHSEED=0/137` | 48/48 pass, 0 skip/failure/error; 4 trường hợp CSV/truth chính xác, 12 CSV sửa sai bị từ chối không đổi input, 4 tiến trình tạo output tái lập; unittest 4.150s | `artifacts/verification/phuc-001-t05-001/`; test log, command/time/counts/source hashes | Tự kiểm tra; chưa có review/acceptance từ Đăng |
| 2026-10-17 22:18:26 +07:00 | PHUC-001-T06 | Export trong `benchmarks/io.py`, CLI `benchmarks/fixtures.py`, config truth, consumer `scripts/read_truth_fixture.py`; source cơ sở `9aba275` + T06; [bằng chứng](evidence/PHUC-001-T06-export.md) | Python 3.12.6; suite 8 module CSV/truth/export/consumer/contracts/Leiden/config/artifacts; CLI export hai run; consumer `python -I` cho từng dataset | 75/75 pass, 0 skip/failure/error; 4 reader pass; 12 file dataset giữa hai run giống byte; repeat run exit 2 và giữ nguyên output; unittest 13.847s | Gói chính `artifacts/detection-tracking/phuc-001-t06-001/`, đối chiếu `phuc-001-t06-002/`; log/hashes ở `artifacts/verification/phuc-001-t06-001/` | Tự kiểm tra consumer; EXT-D01 vẫn chưa có phản hồi Đăng |
| 2026-10-18 09:23:35 +07:00 | PHUC-002-T01 | `benchmarks/dynamic.py`, `tests/unit/test_dynamic_benchmark.py`; source cơ sở `306175f` + T01; [bằng chứng](evidence/PHUC-002-T01-stable-graphs.md) | Python 3.12.6; suite dynamic/truth/CSV/contracts; đọc fixture T06 rồi sample stable seed 11, p_in=.50/p_out=.02 hai lần | 55/55 pass, 0 skip/failure/error; 24 nodes mỗi tháng; R có 76/53 cạnh, 0 isolate ở case mặc định; 4 CSV lặp bằng byte; diagnostic p=0 giữ đủ 24 isolate/tháng | `artifacts/verification/phuc-002-t01-001/`; test log, verification JSON, hai bộ CSV graph, input/source/output hashes; unittest 3.517s | Tự kiểm tra; chưa chạy detection/AMI/tracker |
| 2026-10-18 09:33:35 +07:00 | PHUC-002-T02 | `benchmarks/scenarios.py`; test truth sáu case; guard exporter cũ; source cơ sở `8b56ab0` + T02; [bằng chứng](evidence/PHUC-002-T02-six-event-truth.md) | Python 3.12.6; suite truth/dynamic/CSV/contracts/export/consumer; gọi API sáu case hai lần và so exporter stable/grow với gói T06 | 70/70 pass, 0 skip/failure/error; một event mỗi nguồn, split hai links, dissolve không link A, K stable; 6 JSON tái lập; 12 file legacy bằng byte, 2 reader isolated pass; unittest 6.389s | `artifacts/verification/phuc-002-t02-001/`; JSON sáu case, legacy regression, logs và source/output hashes | Tự kiểm tra; chưa chạy tracker hoặc export benchmark đủ sáu case |
| 2026-10-18 10:23:42 +07:00 | PHUC-002-T03 | `configs/benchmark_week1.json`, `benchmarks/config.py`, test config; source cơ sở `93437d7` + T03; [bằng chứng](evidence/PHUC-002-T03-benchmark-config.md) | Python 3.12.6; suite config/truth/dynamic/CSV/contracts/export/consumer; CLI kiểm tra lịch, sampler dùng config stable seed 11 | 80/80 pass, 0 skip/failure/error; 18 dev + 18 eval, ID/seed không trùng; 72 snapshot/216 detector-unit là kế hoạch; mẫu stable 24 node, 76/53 cạnh và hash R khớp T01; unittest 8.139s | `artifacts/verification/phuc-002-t03-001/`; config copy/hash, hai lịch split, CLI/test logs và JSON kiểm chứng | Tự kiểm tra; không sinh dataset evaluation hoặc chạy detector ở T03 |
| 2026-10-18 15:47:24 +07:00 | PHUC-002-T04 | CSV cạnh/export trong `benchmarks/io.py`, CLI `benchmarks/graphs.py`, TOML graph, test unit/integration; source cơ sở `5274b04` + T04; [bằng chứng](evidence/PHUC-002-T04-graph-export.md) | Python 3.12.6; suite graph export/config/truth/dynamic/CSV/contracts/legacy export; hai process hash seed 0/137, consumer stdlib riêng | 92/92 pass, 0 skip/failure/error; 6 dataset/12 snapshot mỗi run, 54 file dataset giống byte; 12 gói đọc lại; repeat exit 2 giữ output, legacy và config nguồn không đổi; unittest 26.859s | `artifacts/detection-tracking/phuc-002-t04-001/` và `-002/`; log/runner/config copy/counts/source/output hashes ở `artifacts/verification/phuc-002-t04-001/` | Tự kiểm tra exporter; chưa nghiệm thu diagnostic T05/T06, chưa chạy evaluation/Leiden/AMI/tracker |
| 2026-10-18 16:01:47 +07:00 | PHUC-002-T05 | `tests/unit/test_dynamic_benchmark.py`, fixture tiny version 1; source cơ sở `9c18322` + T05; [bằng chứng](evidence/PHUC-002-T05-generator-tests.md) | Python 3.12.6; suite dynamic/graph export/config/truth/CSV/contracts/legacy export; test đủ sáu case, ba dev seed, bốn probability corners và hai process hash seed | 100/100 pass, 0 skip/failure/error; generator 18 test; hai bộ 4 diagnostic/8 snapshot, 24 file giống byte, đọc stdlib 8 gói; giữ 136 output cũ; unittest 15.502s | `artifacts/verification/phuc-002-t05-001/` có CSV/log/config/metadata/hashes, ZIP cùng tên bên ngoài 55 file đã kiểm tra; guide smoke ở `phuc-002-t05-guide-001/` | Tự kiểm tra; chưa nghiệm thu lượt development T06, không sinh evaluation hoặc chạy Leiden/AMI/tracker |
| 2026-10-18 16:24:48 +07:00 | PHUC-002-T06 | Full-development CLI, reader stdlib độc lập, integration tests, CSV kết quả; source cơ sở `c154564` + T06; [bằng chứng](evidence/PHUC-002-T06-development.md) | Python 3.12.6; suite 10 module liên quan, hai export hash seed 0/137 và 36 reader isolated; 4 diagnostic sinh/đọc riêng | 105/105 pass, 0 skip/failure/error; mỗi run 18 dataset/36 snapshot, 162 file dataset giống byte; 4 diagnostic × 2 bộ khớp 24 file; repeat exit 2, giữ 136 output cũ; AC01–05 pass; unittest 41.666s | `artifacts/detection-tracking/phuc-002-t06-001/` và `-002/`; evidence ở `artifacts/verification/phuc-002-t06-001/`, ZIP 424 file đã mở lại; CSV tổng hợp version trong `document/specs/phuc/evidence/` | Tự nghiệm thu generator; chưa có xác nhận nhận gói từ Đăng, không sinh evaluation/Leiden/AMI/tracker |
| 2026-10-18 17:31:54 +07:00 | PHUC-003-T01 | `pipelines/detection_tracking.py`, 4 integration test, CSV kết quả; source cơ sở `38ea2d1` + T01; [bằng chứng](evidence/PHUC-003-T01-leiden-adapter.md) | Python 3.12.6, igraph 1.0.0/leidenalg 0.12.0; suite adapter/Leiden/CSV/contracts/export/config/CLI; stable T06 qua hai process seed detector 0/gamma 1 | 57/57 pass, 0 skip/failure/error; hai tháng 24 assigned/2 nhóm 12/12, đúng endpoint; 2 CSV giữa hai run giống byte, đọc stdlib 4 CSV; không dùng truth labels; giữ 462 file output cũ; unittest 25.912s | `artifacts/detection-tracking/phuc-003-t01-001/` và `-002/`; proof ở `artifacts/verification/phuc-003-t01-001/`, ZIP 25 file đã mở lại; CSV tổng hợp version trong evidence | Tự kiểm tra T01; lịch ba seed/mapping/evaluator chưa nghiệm thu, chưa dùng evaluation/AMI/tracker |
| 2026-10-18 17:53:00 +07:00 | PHUC-003-T02 | Runtime detector config/ba seed trong pipeline, integration tests; source cơ sở `4e2e07c` + T02; [bằng chứng](evidence/PHUC-003-T02-detector-schedule.md) | Python 3.12.6, igraph 1.0.0/leidenalg 0.12.0; suite adapter/Leiden/CSV/config/CLI; hai process stable đọc rõ `configs/benchmark_week1.json`, canonical 0 | 61/61 pass, 0 skip/failure/error; mỗi run 6 membership/3 refs, 6 file khớp hai run; đọc stdlib 12 CSV và đối chiếu độc lập 12 ARI; seed 0 khớp T01, giữ 470 output cũ; unittest 15.057s | `artifacts/detection-tracking/phuc-003-t02-001/` và `-002/`; proof ở `artifacts/verification/phuc-003-t02-001/`, ZIP 35 file đã mở lại; hai CSV detector/ARI version trong evidence | Tự kiểm tra lịch FR02; mapping T03 và cohort T06 chưa nghiệm thu; không dùng evaluation/AMI/tracker |
| 2026-10-18 18:23:34 +07:00 | PHUC-003-T03 | Exporter diagnostics/config/metadata mapping trong pipeline, 5 integration test mới; source cơ sở `e300398` + T03; [bằng chứng](evidence/PHUC-003-T03-detection-package.md) | Python 3.12.6, igraph 1.0.0/leidenalg 0.12.0; suite adapter/Leiden/CSV/contracts/export/config/CLI; hai process stable graph-only và 3 reader stdlib `python -I` | 66/66 pass, 0 skip/failure/error; mỗi gói 9 file/6 mapping; 6 CSV khớp hai run và T02; đọc độc lập 18 CSV gồm recipient-copy; source/runtime/486 output cũ không đổi; unittest 16.328s | `artifacts/detection-tracking/phuc-003-t03-001/` và `-002/`; proof ở `artifacts/verification/phuc-003-t03-001/`, ZIP 49 file đã mở lại; CSV mapping version trong evidence, guide smoke riêng | Tự kiểm tra persistence FR03; chưa có receipt Đăng hoặc nghiệm thu cohort T06; không dùng evaluation/AMI/tracker |

Không yêu cầu đã có commit/PR mới được ghi tiến độ; đường dẫn code thực và lệnh chạy vẫn được dùng. Nếu artifact chỉ có trên máy Phúc, ghi rõ và cung cấp cách tái tạo; không ghi link giả để thành viên tưởng đã truy cập được.

**Git/review ngày 17/10:** T03 được commit `28f1ea6` (`feat(benchmarks): validate synthetic node and membership CSVs`) và push lên `feat/phuc-001-membership-csv`. [PR #5 — triển khai T01–T03](https://github.com/TamNgx179/reddit-community-evolution/pull/5) đang mở, base là nhánh tài liệu của [PR #2](https://github.com/TamNgx179/reddit-community-evolution/pull/2); cần merge #2 trước rồi chuyển base #5 sang `main`. Trước PR, 34 test CSV/truth/contracts/Leiden pass. T04 đã commit/push [`391187b`](https://github.com/TamNgx179/reddit-community-evolution/commit/391187be78c1596ed3c85e56d9762d874cd5e942) trên `feat/phuc-001-ground-truth-events`, remote đã xác minh khớp; T04 không nằm trong PR #5. T05 tiếp tục trên cùng nhánh T04.

T05 đã commit/push `9aba275` trên cùng nhánh T04. Đọc bản T04/T05/T06 tại [nhánh triển khai truth](https://github.com/TamNgx179/reddit-community-evolution/tree/feat/phuc-001-ground-truth-events). Commit ghi task ID; task board và evidence đi cùng thay đổi kiểm tra. [Hướng dẫn T06](001-truth-fixtures/README.md) chỉ cách tái tạo/nhận gói vì artifact local không nằm trong Git.

**Git/review ngày 18/10:** T06 đã commit/push `223cf0c`. Đã mở [PR #6 — hoàn thiện truth/export T04–T06](https://github.com/TamNgx179/reddit-community-evolution/pull/6), base `feat/phuc-001-membership-csv` của PR #5 để review riêng phần T04–T06. Thứ tự phụ thuộc: #2 → #5 → #6; chuyển base sang `main` sau khi các PR trước được merge và đồng bộ nếu cần. PR #6 có lệnh tái tạo, kết quả 75 test đã chạy và giới hạn phạm vi truth; chưa merge.

PHUC-002 triển khai trên nhánh riêng `feat/phuc-002-stable-graphs`, tách khỏi phạm vi PR #6. T01 đã commit/push `2926c3b`, T02 `93437d7`, T03 `5274b04`, T04 `9c18322`, T05 `c154564`, T06 `38ea2d1`. [PR #7 — hoàn thiện generator development PHUC-002-T01–T06](https://github.com/TamNgx179/reddit-community-evolution/pull/7) dùng base là nhánh của PR #6; reader, task board/evidence và CSV tổng hợp đi cùng implementation. [Hướng dẫn](002-dynamic-benchmark/README.md) có lệnh full development và đọc độc lập; artifact/ZIP local không nằm trong Git. PR chưa merge.

PHUC-003 triển khai trên [nhánh adapter riêng](https://github.com/TamNgx179/reddit-community-evolution/tree/feat/phuc-003-leiden-adapter). T01 đã commit/push `92fa179`, T02 `e300398`; T03 tiếp tục trên cùng nhánh, đi cùng test/task board/evidence và CSV mapping. [PR #8 — adapter, lịch seed và gói detection PHUC-003-T01–T03](https://github.com/TamNgx179/reddit-community-evolution/pull/8) có base là nhánh PR #7 để review riêng phần mới, mô tả cập nhật theo phạm vi thực tế; đang mở, chưa merge. [Hướng dẫn API](003-leiden-detection/README.md) có runtime config/cách replay/xuất gói/đọc metadata; full `run` detection–tracking vẫn chưa hoàn tất.

## Blocker và thay đổi

| Task/mốc | Thiếu điều kiện gì | Việc còn làm độc lập được | Người cần phản hồi | Bước mở chặn |
|---|---|---|---|---|
| — | Không có blocker đang mở; PHUC-001/002 và PHUC-003-T01/T02/T03 đã DONE | PHUC-003-T04: audit endpoint/empty/dependency/input lỗi/output cũ; chưa bắt đầu, không cần chờ Đăng | — | — |

Khi đổi requirement/contract, ghi lý do và cập nhật spec/plan/tasks liên quan; giữ evidence run cũ. Nếu đổi sau khi xem evaluation, ghi rõ ảnh hưởng đến tính giữ lại của bộ đánh giá.
