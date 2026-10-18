# Bằng chứng PHUC-002-T06 — Nghiệm thu generator development

**Task:** [PHUC-002-T06](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hoàn thành 6/6 task.
**Lượt kiểm chứng:** 18/10/2026 16:23:40–16:24:48, Asia/Bangkok (UTC+07:00).
**Môi trường:** Python 3.12.6, package 0.1.0; source cơ sở `c154564` cộng T06 trên `feat/phuc-002-stable-graphs`. JSON bằng chứng ghi source hashes và trạng thái working tree lúc chạy.

## Vừa làm gì, dùng để làm gì

Chạy thật toàn bộ **18 dataset development**, thay vì chỉ có lịch dự kiến hoặc pilot seed 11. Mỗi dataset có hai tháng, graph/nodes, đáp án membership/events/links, config copy và metadata/hashes. Đây là bộ đầu vào để phần Leiden tiếp theo phát hiện nhóm rồi đối chiếu với đáp án chuẩn.

- [graphs.py](../../../../src/reddit_sna/benchmarks/graphs.py) thêm cờ `--all-development-seeds`, chọn đủ sáu case × seed 11/12/13 từ JSON. Mặc định không có cờ vẫn là sáu case ở một seed TOML. Cả hai mode từ chối seed ngoài development/output cũ; manifest ghi mode và danh sách seed thực dùng.
- [read_graph_dataset.py](../../../../scripts/read_graph_dataset.py) đọc bằng stdlib với `python -I`, không import generator, thư viện graph hoặc tracker. Kiểm tra metadata/config/provenance tương ứng, hash, schema/order, node/edge/weight, tập thành viên và events/links theo thiết kế độc lập sáu case. Reader không sinh lại cạnh; tính tái lập RNG được kiểm tra riêng bằng hai lần export và suite sampler.
- Lưu CSV tổng hợp nhỏ trong Git: [36 snapshot development](PHUC-002-T06-development-snapshots.csv), [8 dòng diagnostic](PHUC-002-T06-diagnostics.csv). Thành viên khác đọc được số liệu mà không cần có artifact local.

## Lệnh và cohort thực tế

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.graphs --all-development-seeds --run-id phuc-002-t06-001
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.graphs --all-development-seeds --run-id phuc-002-t06-002
& .\.venv\Scripts\python.exe -I scripts/read_graph_dataset.py artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-split-easy-g12
```

Hai tiến trình export lần lượt dùng `PYTHONHASHSEED=0` và `137`. Mỗi run có:

- 6 case × 3 generator seed = **18 dataset easy**, 2 tháng/dataset = **36 snapshot**.
- 9 file/dataset = **162 file dataset**, cộng một manifest run thành 163 file.
- Đúng split development, difficulty easy, generator seeds 11/12/13; mỗi metadata có identity scope/reference/tháng và detector references rỗng.
- Manifest `selection.mode="all-development-seeds"`, `completed_stages=["generation","truth"]`, hash phủ đủ 162 file kể cả metadata. Không giả là full detection/tracking hoặc manifest/freeze hoàn chỉnh PHUC-005.

**162/162 file dataset giữa hai run giống byte**, gồm CSV/config/metadata. Manifest có run ID và timestamp riêng nên không yêu cầu giống byte. Reader isolated chạy thành công đủ **36 gói** của hai run, không sửa input. Chạy lại run ID 001 trả exit **2**, không thay đổi file trong run cũ.

## Số liệu đã đo

Tháng 1/2 tương ứng 2020-01/2020-02. Counts tính cả K12; nhãn/link đúng cho tất cả nguồn, split có một event nhưng hai link của A, merge có event cho cả A và B, dissolve không link A.

| Case | Nodes tháng 1→2 | Nhóm tháng 1→2 | Cạnh seed 11 | Cạnh seed 12 | Cạnh seed 13 |
|---|---|---|---|---|---|
| stable | 24→24 | 2→2 | 76→53 | 75→65 | 80→67 |
| grow | 24→30 | 2→2 | 76→104 | 75→108 | 80→111 |
| shrink | 30→24 | 2→2 | 116→62 | 122→69 | 112→68 |
| merge | 36→36 | 3→2 | 98→185 | 108→175 | 102→196 |
| split | 36→36 | 2→3 | 164→107 | 171→106 | 178→118 |
| dissolve | 24→12 | 2→1 | 76→25 | 75→29 | 80→33 |

Tổng **3,545 hàng cạnh trên 36 snapshot** của run chính; 0 isolate ở cohort easy này. Không thêm cạnh hoặc đổi seed để đạt kết quả đó. Các case có cùng khuôn người/seed có thể trùng graph tháng đầu, ví dụ stable/grow/dissolve; không coi 36 snapshot này mặc nhiên là 36 quan sát thống kê độc lập.

Diagnostic được sinh lại từ fixture `tiny-sampler-diagnostics-v1`, lưu/đọc bằng stdlib riêng, không gộp vào cohort easy:

| Case | Nodes tháng 1→2 | Cạnh tháng 1→2 | Nhóm tháng 1→2 | Isolate tháng 1→2 |
|---|---|---|---|---|
| zero-edges | 4→4 | 0→0 | 3→3 | 4→4 |
| small-groups | 4→4 | 1→1 | 3→3 | 2→2 |
| empty-singleton | 0→1 | 0→0 | 0→1 | 0→1 |
| singleton-empty | 1→0 | 0→0 | 1→0 | 1→0 |

Hai bộ diagnostic, mỗi bộ **4 case / 8 snapshot / 24 file**; **24/24 file giống byte**, đọc lại độc lập đủ 8 gói. Giữ node/membership khi R header-only và tháng quan sát rỗng. Diagnostic không có events/links, không tự suy ra dissolve. Những trường hợp singleton/tháng rỗng và dissolve easy tháng cuối chỉ có K là giới hạn cần xử lý khi đánh giá detector; chưa tính AMI nên không suy ra khả năng khôi phục cộng đồng từ bảng này.

## Kiểm thử và nghiệm thu

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_graph_reader tests.integration.test_graph_export tests.unit.test_dynamic_benchmark tests.unit.test_graph_export tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

**105/105 pass, 0 skip/failure/error**; unittest 41.666s, subprocess wall 42.947s. Suite liên quan, không phải toàn bộ test repo. T06 thêm 5 test integration: full development/failed seed trong [test_graph_export.py](../../../../tests/integration/test_graph_export.py), reader độc lập/chuyển năm/corruption trong [test_graph_reader.py](../../../../tests/integration/test_graph_reader.py).

Reader từ chối hash sai; đồng thời chặn nhãn/link/member/node/cạnh bị sửa kể cả sau khi tính lại hash, cạnh trùng/NaN/tháng hoặc endpoint sai, CSV header/row hỏng, identity/config/counts/trạng thái/schema sai và JSON key trùng. Các test mode cũ tiếp tục pass. Giả lập lỗi ở stable seed 12 giữ dataset seed 11 đã xong và ghi run failed.

| AC của PHUC-002 | Kết quả và căn cứ |
|---|---|
| AC01 | PASS: 162 file hai full run giống byte; test đảo input/process/hash seed |
| AC02 | PASS: reader kiểm tra đáp án/tập người đủ sáu case gồm K cho cả 36 gói |
| AC03 | PASS: zero-edges diagnostic giữ node/truth, R chỉ có header; có cả tháng rỗng quan sát |
| AC04 | PASS: suite input/CSV/output lỗi; lặp run thật exit 2 giữ nguyên output |
| AC05 | PASS: seed development/evaluation tách biệt, isolate báo đúng, không chữa cạnh/đổi seed |

Đối chiếu trước/sau: **136 file output cũ** thuộc PHUC-001-T06 và PHUC-002-T04 giữ nguyên hash. Source/config hashes khi kiểm tra cũng không đổi.

Wall time hai lệnh export: 2.636s và 2.338s; tổng subprocess reader 13.186s; diagnostic sinh/đọc lại 1.211s. Phạm vi gồm startup/I/O, chỉ ghi thời gian quan sát, không phải benchmark hiệu năng. Chưa đo peak memory.

## Đầu ra đã lưu và cách nhận

Các đường dẫn dưới đây **local, bị Git ignore**:

```text
artifacts/detection-tracking/phuc-002-t06-001/   # 18 dataset chính + manifest
artifacts/detection-tracking/phuc-002-t06-002/   # bộ đối chiếu
artifacts/verification/phuc-002-t06-001/
  verification-result.json    # cohort, tests, timing, source/output hashes, AC01–05
  artifact-hashes.json
  unit-integration-tests.log
  test-results.csv            # 105 method
  development-snapshots.csv   # 36 dòng
  development-datasets.csv    # 18 dòng truth counts
  diagnostic-summary.csv     # 8 dòng, báo riêng
  benchmark-config-source.json / graph-config-source.toml / diagnostics-config.json
  readback-1/ / readback-2/   # 36 JSON kết quả reader isolated
  diagnostics-one/ / diagnostics-two/  # hai bộ CSV/metadata tiny
  export-1.log / export-2.log / no-overwrite.log / verify.py
artifacts/verification/phuc-002-t06-001.zip
artifacts/verification/phuc-002-t06-001.zip.sha256
artifacts/verification/phuc-002-t06-001.archive.json
```

ZIP chứa **424 file, 232,202 byte**, layout `run-primary/`, `run-replay/`, `verification/`. Đã mở lại kiểm tra CRC và so nội dung từng entry với file gốc; tất cả khớp. SHA-256: `5d5e6a06edcabf8cf75873eda2ca2dd1f7287b3786fc78d1aa4f0c0873be634e`.

Để xem nhanh, mở bảng snapshot/diagnostic đã version trong Git. Để dùng graph thực, lấy thư mục run chính hoặc gửi ZIP; người khác cũng có thể chạy hai lệnh export với run ID mới và reader theo [README](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06). Runner local là bản ghi của lượt kiểm chứng, không phải CLI mới được hỗ trợ. Các bản config trong evidence là bản sao khi chạy, chưa freeze evaluation.

**PHUC-002 đã hoàn thành phần generator development**. Không sinh dataset evaluation, không chạy Leiden/tracker hoặc tính AMI. Chưa có xác nhận nhận gói từ Đăng; mốc ghép nhóm theo dõi riêng. Tiếp theo **PHUC-003-T01** tích hợp detector có sẵn với graph đã tạo.
