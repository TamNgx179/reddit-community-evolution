# Bằng chứng PHUC-003-T03 — Gói detection và mapping nguồn file

**Task:** [PHUC-003-T03](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 3/6, tổng 15/36 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 18:23:34, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `e300398` cộng T03, nhánh `feat/phuc-003-leiden-adapter`.
**Môi trường:** Python 3.12.6, igraph 1.0.0, leidenalg 0.12.0; package 0.1.0.

## Vừa làm gì và dùng để làm gì

Thêm `export_synthetic_detection(source, output, *, benchmark_config=None)` vào [pipeline](../../../../src/reddit_sna/pipelines/detection_tracking.py). Trước đây caller phải tự lưu dictionary diagnostics; nay một lời gọi xuất gói kết quả có metadata để Đăng/evaluator chọn đúng dataset, tháng, seed và reference của file.

Mỗi gói pilot có **9 file**: sáu membership CSV, `detection.json`, `detector-config.json`, `metadata.json`. Hàm trả metadata. API `detect_synthetic_dataset` cũ vẫn ghi trực tiếp membership và trả diagnostics, không đổi layout đầu ra cũ.

- `detection.json`: đầy đủ diagnostics trả về, dependency versions, month timing/quality/seed ARI, input hashes và context nguồn. Diagnostics schema 2; metadata/membership schema 1.
- `detector-config.json`: bản sao đúng byte của runtime JSON thực đọc, không tự lấy bản archived khác trong source. Config có công thức generator/difficulty và lịch detector.
- Metadata type `synthetic-detection`, scope/completed stage chỉ `detection`, có references theo seed và một entry mapping mỗi tháng/seed: dataset/identity, reference, canonical, path/hash, graph/nodes nguồn, graph fingerprint, active/assigned/isolate/status.
- Paths output tương đối với gói detection; graph/nodes và `source.files` tương đối với dataset graph. Source/runtime absolute paths chỉ là provenance của máy tạo gói. Gói vẫn đọc/hash được sau khi chép sang thư mục khác; cần cung cấp source tương ứng nếu muốn kiểm tra endpoint hoặc đánh giá truth.
- Hash metadata nguồn cùng config/R/nodes (sáu file); kiểm tra không đổi trước publish. Không đọc CSV truth membership/events/links, không sửa metadata graph để chèn detector refs; mapping nằm trong metadata detection mới.
- Chuẩn bị toàn bộ trong thư mục tạm, kiểm tra trước khi tạo output; chuyển metadata cuối. Từ chối output cũ kể cả rỗng/overlap/parent thiếu. Lỗi publish I/O có thể giữ output dở dang, không retry ghi đè. Không tuyên bố publish atomic hoặc resume.
- `metadata.files` hash tám file khác trong gói; metadata không tự hash chính nó. Hash toàn gói và metadata nằm trong proof/ZIP riêng.

## Kiểm tra tự động

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

**66/66 pass**, không skip/failure/error; unittest **16.328s**, toàn process **17.166s**. Đây là suite liên quan adapter/Leiden/CSV/contracts/export/config/CLI, không phải toàn repo.

T03 thêm năm test: xuất diagnostics/config/mapping trên graph-only source và đọc gói copy; empty graph vẫn đủ mapping/reference; chặn output cũ/overlap/parent sai trước detector; lỗi ghi metadata không publish gói complete; phát hiện metadata nguồn thay đổi trước publish. Test explicit runtime dùng archived detector `[0]` và runtime `[0,1,2]`, kiểm tra bản config gói là file runtime. Test liên quan trước đó vẫn pass.

## Lượt chạy thật và đọc lại độc lập

Input gốc: `artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11/`. Runner copy đúng sáu file metadata/config/R/nodes sang `artifacts/verification/phuc-003-t03-001/input-graph-only/`; không copy thư mục truth. Hai lượt detection dùng cùng bản graph-only này, runtime rõ `configs/benchmark_week1.json`, generator seed 11, detector seeds 0/1/2, gamma 1, canonical 0.

Runtime config SHA-256: `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`.
Graph cohort SHA-256: `62fcdd92206d1be05370c24d4816326671cb5568642432aa806cf503f42a5853`.

| Kiểm tra | Kết quả thực tế |
|---|---|
| Hai process `PYTHONHASHSEED=0/137` | `phuc-003-t03-001/` và `phuc-003-t03-002/`, mỗi gói 9 file/6 mapping |
| Membership tháng 2020-01 và 2020-02, mỗi seed | 24 assigned, 2 nhóm 12/12, không isolate; reference đúng seed và shared qua tháng |
| Đối chiếu giữa hai run | 6/6 membership giống byte; bản config giống byte; diagnostics bằng nhau sau khi bỏ `months[*].wall_seconds` |
| Regression so với T02 | Cả 6 membership giống byte với `phuc-003-t02-001/` |
| Consumer stdlib `python -I` | 3 process đọc primary/replay/recipient-copy; xác minh 18 CSV, hash file, source hash, versions/config/identity và endpoint/counts |
| Gói chuyển vị trí | `recipient-copy/` vẫn đọc đủ 9 file theo metadata; không tìm membership qua absolute path cũ |
| Chạy lại vào output cũ | API `FileExistsError`, helper không bắt lỗi nên exit 1, toàn bộ output giữ nguyên hash |
| Giữ dữ liệu cũ | 486 file có trước dưới `artifacts/detection-tracking/` giữ nguyên hash; source/config không đổi |
| Wall time process detection | 2.229s / 1.763s, gồm startup/I/O, không phải benchmark hiệu năng |

Diagnostics giữ seed ARI ≈1 ở stable; đây chỉ là độ giống partition giữa seeds, không phải AMI truth hoặc dự báo. Không suy ra thành viên nhóm giữa hai tháng từ tên `c0`/`c1`.

## File đã lưu và tái tạo

- Hai gói: `artifacts/detection-tracking/phuc-003-t03-001/` và `phuc-003-t03-002/`.
- Proof: `artifacts/verification/phuc-003-t03-001/`, gồm `verification-result.json`, `artifact-hashes.json`, test log/CSV, `membership-mapping.csv`, input graph-only, bản copy recipient, log run/read/no-overwrite và các helper đã dùng.
- [CSV mapping sáu file](PHUC-003-T03-membership-mapping.csv) được version trong Git, đúng byte với CSV ở proof. Có hash/reference/path từng membership; dùng path tương đối với gói detection.
- ZIP: `artifacts/verification/phuc-003-t03-001.zip`, **49 file, 42,256 byte**; đã mở lại kiểm tra CRC và từng entry đúng byte. SHA-256 **`084f42e0d3813c9e60228a59d98fc9cdc5c4ea1759bde348ce950ed44feae8ed`**; sibling `.zip.sha256`/`.archive.json` ghi kiểm chứng.
- Hai đoạn code trong [README](../003-leiden-detection/README.md) đã chạy nguyên phần Python, chỉ đổi tên output: gói `artifacts/detection-tracking/phuc-003-t03-guide-001/`; proof `artifacts/verification/phuc-003-t03-guide-001/`. Cả hai snippet pass, sáu CSV khớp primary, reader stdlib pass. Guide smoke nằm ngoài ZIP chính.

Artifact/ZIP local được Git ignore. Thành viên clone repo có code/docs/CSV tổng hợp, cần dùng README và output ID mới để tái tạo hoặc nhận ZIP thực tế được chia sẻ. Helper trong proof là record của lượt kiểm chứng, không phải CLI pipeline được công bố; không chạy lại helper vào cùng output/log path cũ.

## Giới hạn và bước tiếp theo

Chỉ nghiệm thu persistence/mapping **FR03** trên stable development; chưa phải cohort 18 dataset của T06, không chạy evaluation, AMI/coverage evaluator hoặc tracker. Gói detection không thay gói graph/truth và chưa có full-run manifest/freeze PHUC-005. Mapping file không phải matching community detector–truth. Chưa có phản hồi Đăng nhận/đọc gói.

**T04** tiếp tục audit endpoint, empty graph, dependency/input lỗi và output cũ; **T05/T06** còn nghiệm thu integration/full development. Không cần chờ Đăng để làm các bước này.
