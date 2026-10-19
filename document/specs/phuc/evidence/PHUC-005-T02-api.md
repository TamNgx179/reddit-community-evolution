# Bằng chứng PHUC-005-T02 — API từ protocol đến bảng điểm

**Task:** [PHUC-005-T02](../tasks.md#phuc-005). **Kết quả:** DONE; PHUC-005 **2/6 DOING**, tổng **26/36 task**.
**Ngày:** 19/10/2026, Asia/Bangkok. **Source cơ sở:** `24c29a9`, nhánh `feat/phuc-005-reproducible-runs`, PR #10.
**Kiểm chứng hoàn tất:** 19/10/2026 09:42:37 (UTC+07:00).

## Vừa làm gì

Thêm `run_synthetic_benchmark` và command module riêng ở [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py). API nhận TOML `RunConfig`, protocol T01 và tùy chọn dataset IDs; tự sinh graph/truth, chạy Independent Leiden 0/1/2, rồi xuất metrics/summary qua evaluator hiện có. Hàm trả về đường dẫn run mới.

Trước đây các module đã chạy riêng được; T02 ghép chúng thành một đường chạy có đầu vào/cấu hình tường minh. Nó tạo graph/detection mới trong run, không chỉ chấm lại output cũ như PHUC-004-T06. Không thay công thức AMI, sampler, Leiden hoặc canonical seed. [README](../005-reproducible-runs/README.md) có lệnh/API và cấu trúc output.

## Phạm vi và điều kiện chạy

- Development-only; default chọn đủ 18 development IDs, subset chỉ nhận ID duy nhất trong lịch và giữ thứ tự protocol. ID evaluation giữ lại hoặc selection sai bị chặn trước output.
- TOML namespace detection-tracking, input synthetic không có input.path, seed 0 là canonical detector. Generator seed lấy theo dataset ID/lịch config.
- Kiểm tra config/protocol/policy và backend trước khi reserve run, tái dùng `create_run_directory` để giữ boundary trong artifacts và từ chối overwrite.
- Chụp nguyên byte protocol/recipe/TOML vào run rồi dùng recipe đã lưu cho các stage; nếu file cấu hình nguồn đổi trong lúc chạy, manifest ghi failed.
- Manifest cơ bản ghi selection/expected-actual counts, completed stages, current stage/dataset và trạng thái. Scope thành công chỉ `development-detection-evaluation`, tracking `not_implemented`, freeze false. `run(config)` của full detection-tracking vẫn chưa triển khai.

T03 còn full provenance/source/output inventory/environment/timing, T04 nghiệm thu sau khi lifecycle đầy đủ, T05 freeze và T06 evaluation giữ lại. Việc thêm manifest cơ bản ở T02 không đánh DONE các task đó.

## Test mới

[9 test](../../../../tests/integration/test_synthetic_benchmark_run.py) gồm ba preflight tests không cần graph backend và sáu integration tests:

- Namespace/seed/input/output sai, empty/duplicate/unknown/evaluation IDs, protocol hash sai và backend thiếu đều bị chặn trước run.
- API chạy một dataset qua cả bốn stage generation/truth/detection/evaluation; không ghi đè output và không sửa file nguồn.
- Default chạy đủ 18 development datasets trong thư mục tạm, giữ 108 metrics với 99 AMI hợp lệ/9 null truth_constant; không tạo held-out datasets.
- Hai CLI process từ ngoài repository, subset đảo thứ tự, CSV/policy khớp byte và retry output cũ exit 2.
- Lỗi detector/evaluator giữ output stage trước và manifest failed; cấu hình nguồn đổi bị phát hiện dù stage dùng snapshot đã lưu.

Test default 18 dataset là fixture kiểm tra trong thư mục tạm, không thay lượt development/freeze chính thức T05. Các integration tests dùng graph/Leiden thật và cần `[graph,evaluation]`; chúng không dùng Reddit hoặc evaluation giữ lại.

## Lượt demo để lưu đầu ra

Plan trước khi chạy: `dev-stable-easy-g11` và `dev-grow-easy-g11`, tháng 2020-01/02, detector 0/1/2, gamma 1, canonical 0. Mỗi run dự kiến 2 dataset/4 snapshot/12 metrics/9 summary/4 stored detection month timings. Không đặt ngưỡng điểm làm điều kiện đạt.

Run mới `artifacts/detection-tracking/phuc-005-t02-001/` và `phuc-005-t02-002/` được sinh từ đầu qua API/CLI mới, process hash seed 0/137 và subset đảo thứ tự. Proof local `artifacts/verification/phuc-005-t02-001/` giữ bản sao cả hai run, source snapshots, test/run/reader/no-overwrite logs, before/result/hash manifests, recorder và consumer CSV/sklearn độc lập.

| Kiểm chứng | Kết quả |
|---|---|
| Test mới chạy riêng | **9/9 pass**, 44.467s; preflight và integration composition |
| Full repo suite | **305/305 pass**, 0 skip/failure/error; unittest **244.395s**, process wall **245.972s**; log và 305-row tests CSV trong proof |
| Mỗi run demo | **2 dataset, 4 snapshot, 12 metrics, 9 summary, 4 stored month timings**, 45 file; manifest expected/actual khớp |
| Điểm demo | **12 AMI hợp lệ/0 thiếu**, AMI và coverage đều **1.0**, 306 lượt user qua ba seed |
| Replay | **29 file** gồm 28 CSV graph/nodes/truth/membership/metrics/summary và policy JSON **giống byte** giữa hai run; không yêu cầu timing/timestamp/provenance paths giống |
| Consumer độc lập | Cả hai report pass, mỗi report 12 metrics/9 summary/4 timing; đọc raw CSV và gọi thẳng sklearn, không import project/igraph |
| No-overwrite | Thử lại run chính exit 2 và giữ hash cả 45 file |
| Bảo toàn | **3.301 artifact cũ** giữ SHA-256; **90 source/config/test files** giữ hash trong lúc kiểm chứng |

CSV [metrics 12 dòng](PHUC-005-T02-detection-metrics.csv) và [summary 9 dòng](PHUC-005-T02-detection-summary.csv) theo Git để nhóm xem ngay. Cả 12 dòng metrics khớp các dòng tương ứng của PHUC-004-T06: cùng protocol/input seed cho cùng kết quả, dù T02 đã sinh graph và chạy detector mới. Hai replay dùng cùng hai dataset IDs nên không cộng thành bốn dataset độc lập. 306 là lượt user được chấm qua dòng/tháng/seed, không phải số người độc lập.

Run chính/replay process wall **10.088s / 7.210s** gồm startup, generation, detection và report. Timing trong report chỉ giữ phạm vi của evaluator/diagnostics; generation/peak memory vẫn null ở report. T03 sẽ bổ sung timing đầy đủ ở cấp run, không suy ra generation bằng phép trừ các số đo có phạm vi khác nhau.

ZIP `artifacts/verification/phuc-005-t02-001.zip`: **108 file, 211.369 byte**, đã kiểm tra CRC và từng entry khớp byte. SHA-256 **`b83e6159262b78ed50f45144a812b055393fd38e14e8329fc3caf25290a5fb97`**; sibling `.archive.json`/`.zip.sha256` và `proof-hashes.json` trong gói giữ thông tin kiểm chứng. Recorder ghi một lượt, không chạy lại vào log/output cũ.

## Đọc lại độc lập

Khi có ZIP thực tế, giải nén và dùng sklearn trong Python đang chạy:

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/runs/first/evaluation <thu-muc-giai-nen>/runs/first/inputs
```

Thay `first` bằng `replay` để đọc lượt thứ hai. Consumer tự kiểm tra raw CSV user sets/references/counts/AMI/summary/timing/hashes, không import project/igraph. Absolute producer paths trong metadata chỉ ghi xuất xứ; consumer nhận input root sau relocation. Full artifacts/ZIP local bị ignore; code/config/tests/docs và CSV kết quả nhỏ được version trong Git.

**Tiếp theo PHUC-005-T03:** hoàn thiện manifest lifecycle, hashes, environment và timing ở cấp run. Chưa chạy freeze, evaluation giữ lại hoặc tracker, chưa có receipt/review của Đăng.
