# Bằng chứng PHUC-005-T01 — Protocol, policy và lịch hai tập

**Task:** [PHUC-005-T01](../tasks.md#phuc-005). **Kết quả:** DONE; PHUC-005 **1/6 DOING**, tổng **25/36 task**.
**Ngày:** 19/10/2026, Asia/Bangkok. **Source cơ sở:** `289fdd2`, nhánh mới `feat/phuc-005-reproducible-runs`, base là nhánh PR #9.
**Kiểm chứng cuối hoàn tất:** 19/10/2026 09:19:03 (UTC+07:00), Python 3.12.6.

## Kết quả của T06 trước đó

PHUC-004-T06 đã chạy evaluator trên membership Leiden thật của sáu dataset tổng hợp stable/grow development. Cả 36 dòng chấm có AMI 1 và coverage 1; nhãn được căn cùng user trước khi so sánh, nên đổi tên community không làm sai điểm. AMI 1 nghĩa là cấu trúc phân nhóm khớp ground truth, coverage 1 nghĩa là gán đủ active users trong những snapshot đó. Hai report giống byte ở metrics/summary/policy, có trace 918 lượt user và 48/48 test pass. [Bằng chứng T06](PHUC-004-T06-stable-grow.md) giữ input/config/versions và ZIP, hoàn thành PHUC-004 6/6. Kết luận nằm trong phạm vi hai case easy development.

## T01 mới làm gì

Thêm [protocol JSON](../../../../configs/benchmark_week1_protocol.json) và [loader/CLI](../../../../src/reddit_sna/benchmarks/protocol.py) liên kết graph recipe với policy AMI/summary và lịch dự kiến. Graph recipe [benchmark_week1.json](../../../../configs/benchmark_week1.json) giữ nguyên byte/hash `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`; seed, probabilities, gamma/canonical không đổi sau khi xem development.

Binding là file cùng thư mục với recipe, schema 1, ID `week1-detection-evaluation-v1`. Loader đọc JSON strict, kiểm tra SHA-256 của đúng bytes dùng để parse, policy khớp runtime (kể cả phân biệt bool với int), canonical/seeds/gamma được hỗ trợ và expected counts. Tên file phải là sibling, không dùng absolute/parent/alternate-stream paths. Dictionary trả về là snapshot riêng của caller, không phải freeze record.

Policy được copy đầy đủ vào protocol và so với immutable runtime policies: arithmetic AMI, verified endpoints, null có cờ cho empty/insufficient/degenerate, giữ số âm; summary dataset-month, không gộp seed, giữ valid/missing support. Protocol quy định evaluation sau development/freeze. T01 mới kiểm chứng và khai báo quy tắc này; gate chạy/freeze sẽ ghép ở các task sau.

`.gitattributes` giữ nguyên toàn bộ quy tắc data/LFS cũ và thêm LF cho hai JSON có binding hash. Kiểm tra checkout dùng `core.autocrlf=true` sang đường dẫn mới có dấu cách để xác nhận hash recipe/protocol vẫn khớp trên Windows.

## Lịch đã kiểm tra

| Tập | Generator seeds | Dataset dự kiến | Snapshot dự kiến | Snapshot × detector seed dự kiến |
|---|---|---:|---:|---:|
| Development | 11, 12, 13 | 18 | 36 | 108 |
| Evaluation giữ lại | 101, 102, 103 | 18 | 36 | 108 |
| Tổng | Seed và dataset IDs không trùng giữa hai tập | 36 | 72 | 216 |

Sáu case, hai tháng, ba generator seeds mỗi tập, detector seeds 0/1/2 và canonical 0. [Dataset schedule](PHUC-005-T01-dataset-schedule.csv) có 36 dòng `planned`; [counts](PHUC-005-T01-planned-counts.csv) có ba dòng split/total. Proof local còn có 216 planned detector units. Đây là kế hoạch, không phải 36 dataset đã chạy hoặc 216 điểm evaluation đã đo.

## Lệnh và test

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.protocol configs/benchmark_week1_protocol.json
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_benchmark_protocol tests.unit.test_benchmark_config tests.unit.test_detection_evaluation tests.unit.test_detection_summary tests.integration.test_detection_alignment tests.integration.test_detection_evaluation_export -v
```

[10 test mới](../../../../tests/unit/test_benchmark_protocol.py) kiểm tra recipe/policy binding, JSON/schema, path, recipe bị sửa byte dù JSON tương đương, seed overlap sau rehash, detector schedule/gamma/canonical ngoài phạm vi, sai expected units, relocation/read-only và fresh-process CLI không import igraph/leidenalg/sklearn. 10 test config hiện có kiểm tra thêm seeds/IDs; 48 evaluator tests kiểm tra tương thích policy/loader/report.

## Bằng chứng cuối

| Kiểm tra | Kết quả |
|---|---|
| Test liên quan | **68/68 pass**, 0 skip/failure/error; 10 protocol + 10 config + 48 evaluator tests; unittest **42.535s**, process wall **44.604s** |
| CLI mới | Exit 0, `planned`, counts 18/18 dataset; 72 snapshot/216 đơn vị tổng; hashes và cờ evaluation/freeze false |
| CLI config cũ | Exit 0, lịch 36 dataset/72 snapshot/216 đơn vị giữ nguyên |
| Checkout Windows | `git -c core.autocrlf=true checkout-index` sang thư mục mới có dấu cách; hai JSON giữ byte/hash, loader đọc thành công |
| Bảo toàn | **3.280 artifact cũ** giữ SHA-256; **89 source/config/test files** giữ hash trong lúc kiểm chứng; graph recipe nguyên byte với revision cơ sở |

Proof `artifacts/verification/phuc-005-t01-002/` giữ `unittest.log`, 68-row `tests.csv`, hai CLI logs, `windows-checkout.json`, 36-row schedule, 216 planned units, counts, source snapshots, before/result và proof hashes. Protocol SHA-256 **`cc78f961de7e3c83a343362035ccf84756a39cdc89c5c9cc1e5fd5115fe3a347`**. Lượt kiểm tra ban đầu `phuc-005-t01-001` được giữ lại; kết quả cuối dùng `002` sau khi rà soát và khôi phục đầy đủ các quy tắc `.gitattributes` sẵn có.

CSV schedule/counts nhỏ theo Git. Full proof/ZIP local bị ignore; người nhận cần nhận ZIP thực tế hoặc checkout nhánh/commit, cài môi trường repo và chạy lại các lệnh trên. Recorder `verify.py` ghi bằng chứng một lượt, không chạy lại vào thư mục đã có log/output.

ZIP cuối `artifacts/verification/phuc-005-t01-002.zip`: **17 file, 125.212 byte**, CRC/từng entry khớp byte; SHA-256 **`bf4170c7581f2f0261245a1f4d25385e45c0a548afea0f601664dfff9aabd474`**. Sibling `.archive.json`/`.zip.sha256` và `proof-hashes.json` trong gói giữ thông tin kiểm chứng.

Lệnh protocol trả `status=planned`, `evaluation_executed=false`, `freeze_record_created=false`; không import backend metric/graph hay tạo artifact run. Integration tests dùng fixture development trong thư mục tạm; không đọc hay sinh bộ evaluation giữ lại. Full suite lịch sử 286/286 ở PHUC-004-T05, không được trình bày thành lượt full suite mới của T01.

**Tiếp theo PHUC-005-T02:** ghép API từ protocol/config đến graph, detection và metrics. T03/T05 còn manifest lifecycle/freeze; tracker và receipt/review Đăng là phần việc riêng.
