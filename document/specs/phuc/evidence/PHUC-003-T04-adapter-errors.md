# Bằng chứng PHUC-003-T04 — Endpoint, isolate và xử lý lỗi adapter

**Task:** [PHUC-003-T04](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 4/6, tổng 16/36 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 19:12:28, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `be4e73c` cộng T04, nhánh `feat/phuc-003-leiden-adapter`.
**Môi trường:** Python 3.12.6, igraph 1.0.0, leidenalg 0.12.0. Không đổi dependency đã cài.

## Vừa làm gì

Rà soát và bổ sung guard trong [pipeline](../../../../src/reddit_sna/pipelines/detection_tracking.py) cho cả API membership-only và exporter. Membership có thể đúng nhưng diagnostics vẫn mâu thuẫn; T04 chặn trường hợp đó trước khi xuất kết quả.

- Metadata nguồn phải là object đủ trường bắt buộc; files/counts phải đúng kiểu, hash entries hợp lệ, counts int không âm đúng các tháng, không nhận bool. Truth reference phải khớp dataset ID. File thiếu giữ lỗi `FileNotFoundError` có path, input sai giữ `ValueError` rõ nguyên nhân.
- Membership phải bằng đúng tập endpoint R; không lấy giao để bỏ user sai. Số nhóm/sizes phải khớp CSV, assigned/node/edge counts phải khớp nguồn.
- Graph có cạnh phải status complete và quality hữu hạn; graph không cạnh phải không có partition quality/connectivity, seed ARI rỗng. Graph không rỗng có ba seed ARI hữu hạn trong [-1,1] với tolerance 1e-12, giữ raw value.
- Thiếu igraph/leidenalg báo hướng dẫn cài `[graph]` trước detector output. Source graph/metadata/runtime đổi trong lúc chạy bị từ chối; backend lỗi sau khi ghi scratch không xuất final output. Output cũ, kể cả file/thư mục rỗng, được giữ nguyên.
- Không thay thuật toán Leiden, ordering/protocol Reddit, lịch seed/canonical hoặc schema CSV. Không tự cài/gỡ dependency để giả lập lỗi.

## Test và kiểm chứng lỗi

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

**73/73 test liên quan pass**, không skip/failure/error; unittest **25.611s**, toàn process **26.670s**. Suite liên quan adapter/Leiden/CSV/contracts/export/config/CLI, không phải toàn repo.

Bảy test mới kiểm tra: thiếu từng optional library; 11 loại metadata/graph lỗi; sáu lỗi membership backend; chín loại diagnostics mâu thuẫn; mixed isolates; backend ném lỗi sau scratch; graph/metadata/runtime bị thay đổi trong khi chạy. Những trường hợp lỗi được thử trên cả hai API, trừ mixed-isolate là export thành công. Lượt targeted trước đó 23/23 pass.

Runner riêng lưu **20/20 fault checks pass**, mỗi API có mười tình huống: thiếu igraph/leidenalg, output directory/file cũ, membership thiếu/thừa/trùng user, backend failure, fake empty quality, source hash mismatch. Mọi tình huống đều từ chối, source và output cũ giữ nguyên. [CSV lỗi](PHUC-003-T04-failure-checks.csv) ghi exception/message/kết quả cụ thể. Thiếu dependency được mô phỏng bằng import failure, không phải môi trường thật bị thiếu thư viện.

## Gói diagnostic thực đã xuất

Ba output riêng ở `artifacts/detection-tracking/phuc-003-t04-001/`: `stable-regression/`, `zero-edges/`, `some-isolates/`. Mỗi output 9 file, hai tháng × ba detector seeds, gamma 1/canonical 0. Consumer stdlib `python -I` đọc ba gói và kiểm tra 18 CSV cùng hashes/config/references/counts/endpoint.

| Case riêng | Tháng | Active | Assigned | Isolates | Số nhóm / mỗi seed |
|---|---|---:|---:|---:|---:|
| stable-regression | 2020-01 | 24 | 24 | 0 | 2 |
| stable-regression | 2020-02 | 24 | 24 | 0 | 2 |
| zero-edges | 2020-01 | 24 | 0 | 24 | 0 |
| zero-edges | 2020-02 | 24 | 0 | 24 | 0 |
| some-isolates | 2020-01 | 24 | 12 | 12 | 5 |
| some-isolates | 2020-02 | 24 | 5 | 19 | 2 |

Stable dùng source T06 `dev-stable-easy-g11`, sáu membership giữ nguyên byte so với T03. Zero-edges dùng config riêng p_in/p_out=0/0; some-isolates dùng 0.05/0, generator seed 11, tạo bằng exporter graph. Hai fixture đổi probabilities chỉ là diagnostic riêng theo folder/case, **không thêm vào cohort mặc định hoặc coi là dataset độc lập để tổng hợp kết quả nghiên cứu**. Chúng cùng dataset ID theo schema easy; phải giữ config/graph reference/case directory để phân biệt, không nối chung theo ID.

Zero-edge có sáu CSV header-only, status `empty_graph_no_partition`, modularity/objective/connectivity null và ARI rỗng. Mixed-isolate giữ đủ 24 active users trong metadata nhưng chỉ endpoint được gán. Đây không phải đánh giá AMI trên tập giao tùy ý. [CSV diagnostic 18 dòng](PHUC-003-T04-diagnostic-summary.csv) lưu đủ ba seed và references.

Source stable, runtime JSON và **513 file output có trước** dưới `artifacts/detection-tracking/` giữ nguyên hash. Chưa chạy evaluation hoặc tracker.

## File đã lưu và cách đọc

- Output: `artifacts/detection-tracking/phuc-003-t04-001/<diagnostic-case>/`.
- Proof: `artifacts/verification/phuc-003-t04-001/`, gồm runner/consumer stdlib, input diagnostic, fault fixture, test log/73-row CSV, `diagnostic-summary.csv`, `failure-checks.csv`, `verification-result.json`, source/output hashes và readback logs.
- ZIP: `artifacts/verification/phuc-003-t04-001.zip`, **73 file, 52,439 byte**; mở lại kiểm tra CRC và từng entry đúng byte. SHA-256 **`41989c4729e7014a541a42c84189a02e7f8587e052e8b2245acaeafb32b67097`**; sibling `.zip.sha256`/`.archive.json` lưu kiểm chứng.
- Hai CSV tổng hợp trong evidence được version đúng byte với bản proof. Code/docs/tests đi theo Git; full output/ZIP local bị ignore.

[README](../003-leiden-detection/README.md) có API xuất gói, đọc/hash/chọn canonical và bảng xử lý lỗi. Stable có thể tái tạo từ source T06 và output path mới. Để tái tạo hai diagnostic, dùng `load_benchmark_config`, đổi probabilities như bảng rồi `export_graph_dataset` vào hai thư mục riêng; gọi `export_synthetic_detection` mà không truyền config mặc định khác để dùng đúng archived diagnostic config. Helper proof là record lượt kiểm chứng; không chạy lại vào cùng output/log path cũ.

**Tiếp theo T05:** nghiệm thu integration theo toàn bộ requirements; **T06:** chạy cohort development đủ lịch. Chưa đánh dấu hai task này DONE chỉ vì đã có test T04. Chưa có receipt/review từ Đăng; không có AMI, community matching hoặc full-run manifest/freeze.
