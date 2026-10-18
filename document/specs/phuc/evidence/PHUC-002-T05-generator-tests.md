# Bằng chứng PHUC-002-T05 — Kiểm tra generator và lưu diagnostic

**Task:** [PHUC-002-T05](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hiện 5/6 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 16:01:47, Asia/Bangkok (UTC+07:00).
**Môi trường:** `.venv`, Python 3.12.6; source cơ sở `9c18322` cộng thay đổi T05 trên `feat/phuc-002-stable-graphs`.

## Vừa làm gì và kết quả

Bổ sung bộ kiểm tra để xác minh generator vẫn đúng khi đổi seed, đảo thứ tự đầu vào, đặt xác suất ở 0/1 hoặc dùng nhóm rất nhỏ. Không sửa thuật toán sampler/exporter trong T05.

[test_dynamic_benchmark.py](../../../../tests/unit/test_dynamic_benchmark.py) tăng từ **10 lên 18 test**: thêm 8 method và mở rộng một test process/hash-seed từ stable sang đủ sáu case. Nhiều test chạy qua nhiều case/seed/probability bằng subtest; số method không phải số dataset đã nghiệm thu.

| Nhóm kiểm tra | Bằng chứng | Requirement |
|---|---|---|
| Sáu case × development seed 11/12/13 | Cùng seed tái lập; ba seed tạo ba graph khác nhau trên từng fixture cố định, giữ tập người và nhãn/link chuẩn gồm K | FR01, FR03, FR05 |
| Ordering | Shuffle membership, đổi tên nhóm, đảo thứ tự tháng/user, dùng iterator một lượt: graph không đổi | FR04 |
| Process độc lập | Đủ sáu case, đầu vào set/dict và `PYTHONHASHSEED=0/137`: output khớp nhau và khớp API gọi trực tiếp | FR04 |
| Xác suất biên | Cả sáu case × bốn cặp (0,0), (1,0), (0,1), (1,1): đúng tập cạnh, node và truth giữ nguyên | FR01, FR02, FR03 |
| RNG protocol | Đổi p_in giữa 0/1 không dịch draw của cặp khác nhóm; đổi p_out không dịch draw của cặp cùng nhóm | FR01, FR04 |
| Seed/input lỗi | Chấp nhận và tái lập seed 0/2³²−1; từ chối registry/reference sai trước khi tạo RNG; tests sẵn có chặn seed/probability sai | FR01, FR04 |
| Cạnh và output lỗi | Suite T04 được chạy lại: self-loop/trùng/cặp ngược, sai tháng/user, NaN/Infinity/weight không dương, malformed CSV, overwrite/partial failure | FR02, FR04 |
| Split | Suite config kiểm tra seed/ID development–evaluation tách biệt; test generator chỉ dùng development và seed biên API, không sinh dataset evaluation | FR05 |
| Nhóm nhỏ/isolate | Bốn fixture dưới đây, kiểm tra node/edge/community/isolate và CSV round-trip, kể cả tháng rỗng được quan sát | FR02, FR04, FR05 |

## Các mẫu diagnostic được lưu

[dynamic_diagnostics.json](../../../../tests/fixtures/dynamic_diagnostics.json) là input fixture có version riêng **`tiny-sampler-diagnostics-v1`**, seed 11. Nó khai báo trước thành viên từng nhóm, tháng quan sát, probabilities và counts mong đợi. Không thay đổi JSON easy chuẩn và không sử dụng dữ liệu evaluation để chọn fixture.

| Case | p_in / p_out | Nodes tháng 1→2 | Cạnh tháng 1→2 | Nhóm tháng 1→2 | Isolate tháng 1→2 |
|---|---|---|---|---|---|
| zero-edges | 0 / 0 | 4→4 | 0→0 | 3→3 | 4→4 |
| small-groups | 1 / 0 | 4→4 | 1→1 | 3→3 | 2→2 |
| empty-singleton | 1 / 1 | 0→1 | 0→0 | 0→1 | 0→1 |
| singleton-empty | 1 / 1 | 1→0 | 0→0 | 1→0 | 1→0 |

Hai tháng là 2020-01/2020-02. Mẫu small-groups có nhóm a/b, singleton k và singleton s; chỉ a–b nối cạnh. zero-edges có cùng tập người nhưng không có cạnh. Dù xác suất bằng 1, mẫu chỉ có một người vẫn không sinh self-loop. Tháng rỗng được giữ bằng nodes/R header-only và metadata observed months.

Đây là **diagnostic sampler**, không phải sáu kịch bản easy. K trong fixture nhỏ có một người có chủ ý, không áp dụng K12 của benchmark chuẩn. Gói diagnostic chỉ có node/edge/membership, không phát nhãn events/links hoặc suy ra dissolve. Không tự thêm cạnh để chữa isolate.

Đã xuất **hai bộ, mỗi bộ bốn diagnostic / tám snapshot / 24 file**. So sánh **24/24 file giống byte**, gồm metadata; đọc lại độc lập bằng stdlib CSV/JSON/SHA-256 cho đủ tám gói. Metadata có artifact type `synthetic-sampler-diagnostic`, `scope="generator-only"`, difficulty diagnostic, protocol/config/seed, identity/reference, observed months, counts, Python/package versions và hash năm CSV. Metadata ghi cuối, không giả là gói graph/truth sáu sự kiện đầy đủ.

## Kiểm thử đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_dynamic_benchmark tests.unit.test_graph_export tests.integration.test_graph_export tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

**100/100 pass, 0 skip/failure/error**; unittest 15.502s, subprocess wall 16.126s. Đây là suite liên quan; không phải toàn bộ test repo. Lượt riêng generator trước đó: **18/18 pass**, 1.818s. Các khoảng thời gian chỉ ghi phạm vi chạy test, không phải benchmark hiệu năng.

Đã hash **136 file output cũ** dưới `artifacts/detection-tracking/` trước/sau, tất cả giữ nguyên. Fixture nguồn cũng không đổi byte. Chưa chạy detector, tracker hoặc AMI; số dataset evaluation sinh trong lượt này là 0.

## Đầu ra đã lưu ở đâu

Artifact **local, bị Git ignore**, không tự đi theo commit/push:

```text
artifacts/verification/phuc-002-t05-001/
  unit-integration-tests.log          # toàn bộ output của suite 100 test
  test-results.csv                    # 100 dòng kết quả theo method
  diagnostic-summary.csv              # counts của 4 case × 2 tháng
  verification-result.json            # lệnh, thời gian, counts, source hashes, kiểm tra bảo toàn
  dynamic-diagnostics-config.json     # bản input fixture đúng byte khi chạy
  artifact-hashes.json                # hash các file bằng chứng trước khi đóng ZIP
  verify.py                          # runner local tạo bằng chứng
  diagnostics-one/diag-<case>-g11/
    snapshots/2020-01/{R,nodes}.csv
    snapshots/2020-02/{R,nodes}.csv
    truth/membership.csv
    metadata.json
  diagnostics-two/diag-<case>-g11/...  # bộ đối chiếu tái lập
artifacts/verification/phuc-002-t05-001.zip
artifacts/verification/phuc-002-t05-001.zip.sha256
```

ZIP có **55 file, 33,169 byte**. Đã mở lại kiểm tra CRC và so nội dung từng entry với file nguồn, tất cả khớp. SHA-256 ZIP: `11cc2cfefb9320653e4783c009728478725abd8a0e7da26427a1e62c33dcec9d`.

Muốn xem nhanh, mở `diagnostic-summary.csv`; muốn thấy dữ liệu thực, mở thư mục `diagnostics-one`. Ví dụ `diag-small-groups-g11/snapshots/2020-01/R.csv` có đúng một cạnh a–b; nodes.csv vẫn có đủ a/b/k/s. Có thể gửi nguyên ZIP để người khác nhận output local.

Code test và fixture đã version trong Git; thành viên nhóm chạy suite và [ví dụ xuất CSV trong README](../002-dynamic-benchmark/README.md#kiểm-tra-generator-và-lưu-mẫu-nhỏ--t05) để tái tạo. Ví dụ README đã được chạy thật vào folder mới `artifacts/verification/phuc-002-t05-guide-001/`: lưu 20 CSV + một fixture copy, đối chiếu cạnh/node và membership với bộ bằng chứng đều đúng; `guide-check.json` ghi kết quả. Folder guide này nằm ngoài ZIP chính.

## Phần tiếp theo

T05 hoàn tất phần kiểm tra generator. **PHUC-002-T06** còn chạy/đọc lại benchmark development theo cohort đã khai báo, ghép diagnostic và lập báo cáo nghiệm thu tái lập. Test ba seed trong bộ nhớ và các gói tiny của T05 chưa thay thế lượt đó. Không cần chờ Đăng để làm T06.
