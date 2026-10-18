# Bằng chứng PHUC-003-T01 — Gọi Leiden trên benchmark stable

**Task:** [PHUC-003-T01](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 hiện 1/6 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 17:31:54, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `38ea2d1` cộng thay đổi T01, nhánh `feat/phuc-003-leiden-adapter`.
**Môi trường:** Python 3.12.6; igraph 1.0.0; leidenalg 0.12.0.

## Vừa làm gì, dùng để làm gì

Thêm `detect_synthetic_dataset(source, output)` trong [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py). API nhận một dataset graph đã xuất ở PHUC-002, kiểm tra graph/config/identity/tháng/hash rồi gọi `detect_snapshots` có sẵn với **seed 0, gamma 1.0**, protocol `synthetic-planted-undirected-v1` và identity scope của dataset.

Detector tự tìm nhóm từ cạnh R. Không đọc truth membership/events/links để tạo partition. Test gọi API thành công trên bản input đã loại thư mục truth, xác minh nó không phụ thuộc file đáp án.

API kiểm tra membership đúng tập endpoint R, một hàng mỗi user, reference riêng và giữ chung qua các tháng cùng seed. Xuất CSV UTF-8/LF theo thứ tự canonical, giữ source/old output nguyên vẹn. Dict trả về có diagnostics, dependency versions, dataset context, input hashes và active/isolate counts. Để giữ nguyên detector dùng chung, wrapper chuyển raw output tạm thành CSV chuẩn sau khi xác minh.

Không sửa [detection/leiden.py](../../../../src/reddit_sna/detection/leiden.py) hoặc graph provenance/ordering Reddit. Hàm `run(config)` toàn pipeline vẫn báo chưa triển khai: T01 mới là API detection riêng, không giả có tracker/evaluator.

## Input và kết quả chạy thật

Source là `artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11/`: generator seed **11**, hai tháng 2020-01/02, R có **76/53 cạnh**. Đây là generator seed, khác detector seed **0** trong lượt này.

Hai tiến trình riêng gọi cùng API, lần lượt với `PYTHONHASHSEED=0/137`, lưu output mới:

- `artifacts/detection-tracking/phuc-003-t01-001/` — gói chính.
- `artifacts/detection-tracking/phuc-003-t01-002/` — gói đối chiếu.

| Tháng | Active | Endpoint | Assigned | Isolate | Nhóm detector | Kích thước |
|---|---|---|---|---|---|---|
| 2020-01 | 24 | 24 | 24 | 0 | 2 | 12, 12 |
| 2020-02 | 24 | 24 | 24 | 0 | 2 | 12, 12 |

[CSV kết quả](PHUC-003-T01-stable-detection.csv) đã version trong Git để nhóm theo dõi. Đây là số liệu đọc từ output thực, không suy ra từ số nhóm truth. Cùng số lượng/kích thước nhóm chưa chứng minh đúng từng thành viên; AMI chưa được tính ở T01.

Hai run có **2/2 file membership giống byte**, cùng reference detector qua cả hai tháng. Đã đọc độc lập bằng stdlib đủ **4 CSV**, kiểm tra header, exact endpoint set, reference/tháng, uniqueness và ordering/LF. Reference khác truth reference và gắn dataset/protocol/cohort/gamma/seed. Graph cohort fingerprint:

`62fcdd92206d1be05370c24d4816326671cb5568642432aa806cf503f42a5853`

Diagnostics có modularity/RB objective và versions; đó không phải AMI/accuracy. Chỉ chạy một seed nên `seed_pair_ARI=[]`. JSON detector giữ schema version 2 hiện có; CSV membership dùng schema version 1 của benchmark, không trộn hai loại version này.

Mỗi gói prototype có hai membership, `prototype-detection.json` và manifest scope `synthetic-detection-prototype`, chỉ hoàn thành stage `detection-prototype`. Diagnostics JSON do caller kiểm chứng lưu từ dict trả về. Persistence/mapping chính thức `detection.json` của adapter vẫn thuộc T03, không đánh task đó DONE sớm.

## Kiểm thử và bảo toàn dữ liệu

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

**57/57 pass, 0 skip/failure/error**; unittest 25.912s, subprocess wall 26.959s. Suite này tập trung adapter/Leiden/CSV/config/CLI, không phải toàn bộ test repo hoặc cùng danh sách 105 test generator của T06.

Bốn test mới trong [test_synthetic_detection.py](../../../../tests/integration/test_synthetic_detection.py):

- Gọi Leiden thật trên graph-only input không có thư mục truth; seed 0/gamma 1/protocol synthetic, CSV/reference/endpoint đúng và source không đổi.
- R rỗng nhưng có 24 active user/tháng: assigned 0, membership header-only, 24 isolate, `empty_graph_no_partition`, modularity/objective null; không tạo partition giả.
- Graph hash hoặc identity sai bị từ chối trước detector, không tạo output cuối.
- Output tồn tại/source overlap bị từ chối, giữ file cũ.

Test Leiden gốc và CLI scaffold tiếp tục pass. Các test nền này chưa nghiệm thu đủ lịch/config/dependency/error của T02–T05.

Đã đối chiếu **462 file output cũ** trước/sau, tất cả giữ nguyên hash. Lặp run ID của caller local thất bại trước khi ghi output, exit 1 do exception chưa bắt ở helper; API trực tiếp từ chối `output` đã tồn tại bằng `FileExistsError`. Không nhầm mã exit này với CLI benchmark của PHUC-002.

Hai tiến trình detection quan sát wall 1.964s/2.043s gồm startup/I/O; các month timing trong diagnostics là phạm vi detector có sẵn. Không coi các số này là benchmark hiệu năng; chưa đo peak memory.

## Đầu ra đã lưu

Các đường dẫn dưới đây **local, bị Git ignore**:

```text
artifacts/detection-tracking/phuc-003-t01-001/
  memberships/2020-01/membership-seed0.csv
  memberships/2020-02/membership-seed0.csv
  prototype-detection.json
  manifest.json
artifacts/detection-tracking/phuc-003-t01-002/...  # bộ đối chiếu
artifacts/verification/phuc-003-t01-001/
  verification-result.json / artifact-hashes.json
  unit-integration-tests.log / test-results.csv / detection-summary.csv
  input-graph-only/              # config/metadata/R/nodes, không copy truth
  run-config.toml / detect_one.py / verify.py
  detect-1.log / detect-2.log / no-overwrite.log
artifacts/verification/phuc-003-t01-001.zip
artifacts/verification/phuc-003-t01-001.zip.sha256
artifacts/verification/phuc-003-t01-001.archive.json
```

`input-graph-only` là bản sao phần graph cho API detection, không phải gói graph/truth đầy đủ cho consumer PHUC-002. Gói đầy đủ gốc vẫn nằm ở output T06 không bị sửa. TOML/caller/runner trong evidence chỉ phục vụ lượt prototype này, không phải CLI pipeline mới.

ZIP có **25 file, 22,317 byte**, layout run-primary/run-replay/verification. Đã mở lại kiểm tra CRC và so nội dung từng entry với file gốc, tất cả khớp. SHA-256: `3ac4a242a11f21699430c840345b1f1f170bbea06d8d50e40e627e943989aaba`.

[Ví dụ API trong README](../003-leiden-detection/README.md#api-và-cách-chạy) đã chạy thật vào `artifacts/verification/phuc-003-t01-guide-001/`; hai membership khớp gói chính và diagnostics được lưu, `guide-check.json` ghi xác nhận. Folder guide nằm ngoài ZIP chính. Người khác dùng source T06 đã tái tạo/nhận gói và ví dụ này để replay.

T01 hoàn thành phần gọi detector FR01. **Tiếp theo T02** đọc và chạy lịch detector seed 0/1/2, canonical vẫn 0; T03 làm mapping/persistence, các task sau nghiệm thu đầy đủ. Chưa dùng evaluation, chưa chạy tracker hoặc tính AMI, chưa ghi nhận Đăng đã nhận gói.
