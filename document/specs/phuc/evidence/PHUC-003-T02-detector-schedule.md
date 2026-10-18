# Bằng chứng PHUC-003-T02 — Lịch detector seed 0/1/2

**Task:** [PHUC-003-T02](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 hiện 2/6 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 17:53:00, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `4e2e07c` cộng T02, nhánh `feat/phuc-003-leiden-adapter`.
**Môi trường:** Python 3.12.6, igraph 1.0.0, leidenalg 0.12.0.

## Vừa làm gì

Mở rộng [detect_synthetic_dataset](../../../../src/reddit_sna/pipelines/detection_tracking.py) để đọc seed/gamma/canonical từ JSON và chạy đủ lịch tuần 1. API nhận keyword `benchmark_config=Path("configs/benchmark_week1.json")`; nếu không truyền thì đọc bản benchmark-config.json đã lưu trong dataset.

- Runtime JSON được đọc/validate trước khi tạo output. Những trường công thức sinh graph phải khớp config nguồn; mục detector có thể lấy từ file runtime riêng. Protocol tuần 1 yêu cầu đúng **seeds `[0,1,2]`, gamma 1.0, canonical 0**; lịch rút gọn/đảo thứ tự hoặc canonical/gamma khác bị từ chối, không bị âm thầm thay bằng default.
- Giá trị đọc từ config được truyền vào detector. Canonical luôn là seed đầu đã cấu hình, không chọn theo modularity/RB objective. Dict trả về có `detector_seeds`, path/hash config thực đọc và selection policy; config được đối chiếu lại trước khi xuất membership.
- Mỗi tháng phải có ba run đúng thứ tự; mỗi seed có reference riêng, cùng seed giữ reference qua các tháng. Kiểm tra exact endpoint coverage và reference cho từng CSV, chặn lẫn seed/reference trước khi xuất output cuối.
- Không sửa thuật toán Leiden dùng chung. API vẫn không đọc truth membership/events/links. Các gói/lượt T01 cũ giữ nguyên; API hiện tại chạy đủ ba seed.

## Runtime config thực đã dùng

Hai caller đều truyền rõ `configs/benchmark_week1.json`, không chỉ dựa vào bản archived của source. SHA-256: `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`.

Đã lưu bản đúng byte vào `detector-benchmark-config.json` trong evidence local và đối chiếu trước/sau: file chung không đổi. API cũng kiểm tra runtime graph recipe khớp bản source, tránh dùng cấu hình graph khác để giải thích dữ liệu đã sinh.

Test runtime riêng dùng source archived chỉ khai báo detector `[0]`, còn runtime khai báo `[0,1,2]`: API vẫn xuất đủ ba seed theo runtime, cả hai input giữ nguyên. Đây là bằng chứng lịch không bị lấy nhầm từ source hoặc hardcode thành một seed.

## Lượt stable thật và đầu ra

Source: `artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11/`. Generator seed là **11**, detector seeds là **0/1/2**. R vẫn có 76/53 cạnh ở tháng 2020-01/02.

Hai process `PYTHONHASHSEED=0/137` xuất vào `artifacts/detection-tracking/phuc-003-t02-001/` và `phuc-003-t02-002/`. Mỗi run chạy cùng **một dataset**, hai tháng × ba seed = **6 membership CSV**, không phải ba dataset độc lập.

| Tháng | Detector seed | Assigned | Nhóm | Kích thước | Kết quả chính |
|---|---|---|---|---|---|
| 2020-01 | 0 | 24 | 2 | 12, 12 | Có |
| 2020-01 | 1 | 24 | 2 | 12, 12 | Không |
| 2020-01 | 2 | 24 | 2 | 12, 12 | Không |
| 2020-02 | 0 | 24 | 2 | 12, 12 | Có |
| 2020-02 | 1 | 24 | 2 | 12, 12 | Không |
| 2020-02 | 2 | 24 | 2 | 12, 12 | Không |

[CSV detector sáu dòng](PHUC-003-T02-stable-detection.csv) đã version trong Git, có reference và cờ `is_canonical`; active 24/isolate 0 ở mọi hàng. Mỗi seed có một reference shared qua hai tháng, ba seed có ba reference khác nhau.

**6/6 file membership giữa hai run giống byte**. Đã đọc độc lập bằng stdlib đủ 12 CSV, kiểm tra header/month/reference/endpoint/uniqueness/order/LF. Hai CSV seed 0 khớp đúng byte với gói T01, tức mở rộng lịch không đổi kết quả canonical đã có.

### Độ ổn định giữa seed

Thứ tự `seed_pair_ARI` của detector là (0,1), (0,2), (1,2). Cả ba cặp ở cả hai tháng có ARI raw **0.9999999999999998**, tương đương **≈1** trong sai số số thực. [CSV seed repeatability](PHUC-003-T02-seed-repeatability.csv) lưu nguyên số nhận từ thư viện, không làm tròn trong dữ liệu.

Runner tính ARI độc lập từ contingency counts của các membership CSV, không import hàm ARI của detector: **12 đối chiếu** qua hai run đều khớp trong tolerance 1e-12. Kết quả cho thấy các seed chia giống nhau trên hai graph stable này. Đây không phải AMI/accuracy so với truth và không đại diện cho toàn bộ cohort development.

## Kiểm thử

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

**61/61 pass, 0 skip/failure/error**, unittest 15.057s, subprocess wall 15.993s. Suite adapter/Leiden/CSV/config/CLI liên quan, không phải toàn repo. [Test integration](../../../../tests/integration/test_synthetic_detection.py) hiện 8 method: bốn method cũ mở rộng sang ba seed và bốn method mới cho runtime config, lịch/recipe lỗi, canonical và reference/order.

Test canonical cố ý sửa diagnostics để seed 2 có score cao hơn, nhưng kết quả chính vẫn là seed 0. Đây là fault injection trong test để xác minh quy tắc; dữ liệu thật trong bảng trên dùng diagnostics nguyên từ Leiden. Test lẫn reference hoặc đảo run phải thất bại trước khi xuất output cuối. Test graph rỗng giữ ba membership header-only, quality null và ARI rỗng, không tạo điểm giả.

Đã giữ nguyên hash **470 file output cũ**, không sửa input graph hoặc runtime JSON. Lặp run ID bị helper từ chối trước khi ghi (exit 1 do exception chưa bắt, giống caller local T01); API từ chối `output` đã tồn tại. Wall hai process thật 2.096s/2.263s gồm startup/I/O, không coi là benchmark hiệu năng.

## File đã lưu

Artifact **local, bị Git ignore**:

```text
artifacts/detection-tracking/phuc-003-t02-001/
  memberships/2020-01/membership-seed{0,1,2}.csv
  memberships/2020-02/membership-seed{0,1,2}.csv
  prototype-detection.json
  manifest.json
artifacts/detection-tracking/phuc-003-t02-002/...   # bộ đối chiếu
artifacts/verification/phuc-003-t02-001/
  verification-result.json / artifact-hashes.json
  unit-integration-tests.log / test-results.csv
  detection-summary.csv / seed-repeatability.csv
  detector-benchmark-config.json / run-config.toml
  input-graph-only/ / detect_one.py / verify.py
  detect-1.log / detect-2.log / no-overwrite.log
artifacts/verification/phuc-003-t02-001.zip
artifacts/verification/phuc-003-t02-001.zip.sha256
artifacts/verification/phuc-003-t02-001.archive.json
```

ZIP có **35 file, 28,910 byte**, layout run-primary/run-replay/verification. Đã mở lại kiểm tra CRC và so từng entry với file gốc, tất cả khớp. SHA-256: `7b08096bbdde5f23621c15bd66e8c7706cd4a1486cdc8e52f392438c6ad0abff`.

`input-graph-only` là bản sao graph/config/metadata cho API detection, không phải gói truth đầy đủ. Caller/runner local lưu dict thành `prototype-detection.json` và manifest scope prototype, chưa thay thế API persistence/mapping T03. Runtime JSON có bản sao riêng để nhận gói/replay. [Ví dụ README](../003-leiden-detection/README.md#api-và-cách-chạy) đã chạy vào `artifacts/verification/phuc-003-t02-guide-001/`, sáu membership khớp gói chính; folder guide nằm ngoài ZIP chính.

T02 hoàn tất lịch detector FR02. **Tiếp theo T03** chuẩn hóa lưu `detection.json` cùng mapping dataset/reference/tháng/seed trong metadata. Chưa chạy cohort development đủ 18 dataset ở T06, chưa dùng evaluation/AMI/tracker; không tự ghi Đăng đã nhận gói.
