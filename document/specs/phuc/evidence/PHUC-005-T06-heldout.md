# Bằng chứng PHUC-005-T06 — evaluation giữ lại theo khóa T05

**Kết quả:** T06 và **PHUC-005 DONE 6/6**; tổng **30/36 task**. **Owner:** Phúc.
**Ngày:** 19/10/2026, Asia/Bangkok. Nhánh `feat/phuc-005-reproducible-runs`, PR #10.
**Driver production:** [`09623f1a0fa299614c9e7ba3cf1dad560e5c13ac`](https://github.com/TamNgx179/reddit-community-evolution/commit/09623f1a0fa299614c9e7ba3cf1dad560e5c13ac), đã commit trước production, working tree sạch.
**Frozen package source:** `d4fe76b02962009dddb1d042da3fb084dd79582c`; **42 file source/package/pyproject giữ nguyên hash T05**.
**Kiểm chứng hoàn tất:** 19/10/2026 **11:22:56 UTC+07:00**.

## Vừa làm gì và dùng để làm gì

Chạy **một lượt production evaluation đã lên kế hoạch trước khi xem điểm**, đủ sáu case × generator seeds 101/102/103; tiếp tục dùng detector 0/1/2, canonical 0, gamma 1 và policy đã khóa. Không chọn subset, ngưỡng điểm hoặc valid/null counts làm điều kiện giữ kết quả.

[Driver ngoài package](../../../../scripts/run_frozen_evaluation.py) gọi `load_benchmark_freeze` trước output/heldout access, chụp nguyên bundle vào run, gọi các module graph/Leiden/evaluator đã khóa, rồi kiểm tra counts/nguồn freeze/TOML/driver trước complete. Package source/config/policy không đổi; driver source được archive/hash riêng theo phạm vi T05 cho phép. Lỗi giữ partial outputs/failed record; run cũ bị từ chối.

[Tests mới](../../../../tests/integration/test_frozen_evaluation.py) dùng **identity-only stubs**, không sinh graph/truth hoặc tính metric values giữ lại. Chạy tests trước commit driver; nguồn đã test giữ nguyên hash đến hết production. Các fixture freeze thật trong tests chỉ dùng development. Điểm evaluation thật chỉ được đọc sau lượt chạy theo khóa.

## Lệnh đã chạy và chronology

```powershell
& .\.venv\Scripts\python.exe scripts/run_frozen_evaluation.py `
    --config configs/detection_development.toml `
    --freeze artifacts/detection-tracking/phuc-005-t05-freeze-001 `
    --run-id phuc-005-t06-evaluation-001
```

| Mốc Asia/Bangkok, 19/10/2026 | Thời điểm |
|---|---|
| Freeze T05 | **10:58:31.148600** |
| Tạo evaluation run | **11:21:56.088664** |
| Bắt đầu truy cập heldout | **11:21:58.670511** |
| Evaluation root complete | **11:22:26.238593** |
| Independent audits/packaging hoàn tất | **11:22:56** |

Run ở `artifacts/detection-tracking/phuc-005-t06-evaluation-001/`, scope **heldout-detection-evaluation**, split evaluation; `evaluation_executed=true`, `freeze_record_created=false`, tracking not_implemented. T06 dùng bản khóa cũ, không tạo lại khóa. TOML tên development giữ namespace/input/output/canonical; lịch thực thi lấy từ evaluation schedule trong freeze.

## Kết quả evaluation và đối chiếu toàn lịch

| Tập | Dataset | Snapshot | Snapshot×detector seed / metric rows | AMI valid / null | Dataset lỗi |
|---|---:|---:|---:|---:|---:|
| Development T05, dùng lại nguyên output | 18 | 36 | 108 | 99 / 9 | 0 |
| Evaluation T06, sinh/chạy mới | 18 | 36 | 108 | 99 / 9 | 0 |
| **Tổng lịch** | **36** | **72** | **216** | **198 / 18** | **0** |

Dataset IDs và generator seeds hai tập disjoint. Mỗi dataset có hai tháng, mỗi tháng chạy ba detector seeds; detector seed không thành dataset độc lập. Ledger 36 dòng và combined metrics 216 dòng trong proof khớp chính xác mọi khóa dataset/month/seed dự kiến, không có dòng trùng/thiếu. Development được đọc lại để audit, không sinh hoặc chạy detector lại tại T06.

| Tập | Detector seed / vai trò | AMI mean trên dòng hợp lệ | AMI min | Valid / null | Coverage mean |
|---|---|---:|---:|---:|---:|
| Development | **0 canonical** | **0.9558799269999274** | 0.7241648712463861 | 33 / 3 | 1.0 |
| Development | 1 diagnostic | 0.9487475264624783 | 0.7241648712463861 | 33 / 3 | 1.0 |
| Development | 2 diagnostic | 0.9546409700892936 | 0.7251609881533845 | 33 / 3 | 1.0 |
| Evaluation | **0 canonical** | **0.9331167511618917** | 0.7241648712463861 | 33 / 3 | 1.0 |
| Evaluation | 1 diagnostic | 0.9484196642529084 | 0.7241648712463861 | 33 / 3 | 1.0 |
| Evaluation | 2 diagnostic | 0.9404717903026866 | 0.7241648712463861 | 33 / 3 | 1.0 |

Canonical vẫn **0 theo quyết định trước evaluation**; ba seed giữ bảng riêng, không chọn lại theo điểm. Mean theo dataset-month, chỉ trên `ami_status=ok`, giữ missing/support; không gộp hai split hoặc detector seeds thành một điểm tổng.

Evaluation có 9 AMI null, đều `degenerate_partition/truth_constant` ở dissolve tháng cuối, đủ ba generator seeds × ba detector seeds. Theo policy khi truth chỉ còn background K, dòng vẫn giữ với reason/support; null không phải lỗi pipeline. Coverage đo độ phủ gán nhóm, AMI đo mức trùng với planted truth.

Hai snapshot canonical thấp nhất: **`eval-merge-easy-g102 / 2020-02`** và **`eval-split-easy-g101 / 2020-01`**, cùng **0.7241648712463861**; tiếp theo `eval-merge-easy-g103 / 2020-02` có **0.7281798157360084**. Tất cả giữ nguyên để phân tích ở PHUC-006, không sửa tham số sau khi xem giữ lại. Kết quả thuộc benchmark tổng hợp, chưa phải độ chính xác dự báo sự kiện hoặc kết quả Reddit.

## Kiểm chứng và điều kiện nghiệm thu

- **25/25 targeted tests pass**, 0 skip/failure/error, **106.216s**: 8 driver control-flow tests, 7 freeze integration, 10 protocol unit. Không chạy lại full repo suite T06; không coi 108 metric rows là test cases.
- **4 lượt audit từ 3 consumer độc lập**: root evaluation stdlib; report evaluation và report development bằng CSV/direct sklearn; freeze stdlib. Chạy `python -I` trên copies sau relocation, không import producer/igraph để tự xác nhận output.
- Root evaluation có **433 hashed files + manifest**, package closure **42 files** khớp T05; driver có hash riêng. Timing giữ stage/dataset scopes đã chốt; evaluator tháng không nhân ba, peak memory chưa đo.
- Retry evaluation ID exit **2**, stdout rỗng, mọi hash giữ nguyên. Development/freeze T05 không đổi byte; **5.512 artifact cũ** và **95 code/config/test files** giữ hash trong lúc kiểm chứng.
- Reproducibility AC03 dùng evidence fresh-process/partition rename-reorder T04; **41 historical package hashes** của lượt replay đó khớp T06. T06 có đúng một production heldout run theo kế hoạch, không chọn lượt đẹp nhất.

[AC matrix](PHUC-005-T06-acceptance-matrix.csv): **AC01–AC05 PASS**. AC01 scope detection, AC02 failure/progress/no-overwrite, AC03 replay và invariant nguồn, AC04 đủ 36/72/216, AC05 chronology/freeze/source/summary hashes và canonical cố định. PHUC-005 hoàn thành; phần notebook/gói giao cá nhân còn PHUC-006, tracker/demo cặp theo dõi riêng.

## Hash và đầu ra đã lưu

- Freeze manifest T05: **`8c3749cce905e5d416929bddd931cbb4a7104f047ad9273ab22561d5ccdf8ff9`**.
- Evaluation manifest: **`e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c`**.
- External driver: **`8c18038300258f1e25b63ee16492a4d25a0e836b2e7a76dc4e441dd7eae124d0`**; archived ở `provenance/driver/run_frozen_evaluation.py`.
- Protocol/recipe/policies, source bytes và versions giữ binding T05; không thay frozen package sau access. Driver mới là phần orchestration ngoài package đã được khai báo trước evaluation.

Theo Git: [evaluation metrics 108 dòng](PHUC-005-T06-detection-metrics.csv), [evaluation summary 21 dòng](PHUC-005-T06-detection-summary.csv), [ledger toàn lịch 36 dòng](PHUC-005-T06-dataset-ledger.csv), [so sánh split/seed 6 dòng](PHUC-005-T06-split-comparison.csv), [AC matrix](PHUC-005-T06-acceptance-matrix.csv), [evaluation reference](PHUC-005-T06-evaluation-reference.json). Reference là thông tin tham chiếu, không thay bundle đầy đủ.

Proof local `artifacts/verification/phuc-005-t06-001/`: plan trước điểm, tests/source snapshots, raw commands/stdout/stderr, full copies development/evaluation (kèm freeze snapshot), combined metrics 216 dòng, ledger/comparison/AC/result/hashes và consumers. ZIP **845 file, 1.097.850 byte**, CRC/từng entry đã đối chiếu byte; SHA-256 **`f1f2a791bc3a515d6973758697432e9279b85fed4936358bb5feb16d88275dec`**. Sibling `.archive.json`/`.zip.sha256` giữ checksum. Artifacts/ZIP local bị ignore, chưa tự có trên máy thành viên.

Khi nhận ZIP và giải nén:

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_evaluation.py <thu-muc-giai-nen>/runs/evaluation 8c3749cce905e5d416929bddd931cbb4a7104f047ad9273ab22561d5ccdf8ff9
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/runs/evaluation/evaluation <thu-muc-giai-nen>/runs/evaluation/inputs
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_freeze.py <thu-muc-giai-nen>/runs/evaluation/freeze <thu-muc-giai-nen>/runs/development
```

Nguồn tái lập benchmark là driver `09623f1` và package bytes đã đóng gói; các bước reporting/handoff sau đó theo dõi riêng, không cập nhật lại khóa T05. **Tiếp theo PHUC-006-T01:** inventory và consumer bàn giao độc lập. Chưa có tracker/receipt/review Đăng, chưa nghiệm thu demo cặp.
