# Bằng chứng PHUC-003-T05 — Integration adapter và các gate chấp nhận

**Task:** [PHUC-003-T05](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 5/6, tổng 17/36 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 19:44:51, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `6583a10` cộng T05, nhánh `feat/phuc-003-leiden-adapter`.
**Môi trường:** Python 3.12.6, igraph 1.0.0, leidenalg 0.12.0.

## Vừa làm gì và vì sao cần

T04 kiểm tra từng lỗi dữ liệu/dependency. T05 thêm bốn test đầu cuối trong [test_synthetic_detection.py](../../../../tests/integration/test_synthetic_detection.py), kiểm tra thuật toán thật từ graph qua adapter đến file kết quả với đáp án độc lập. Source runtime/Leiden/schema/config/dependencies không đổi.

1. Hai clique rời nhau gồm user `u001..u012` và `u101..u112`, config riêng p_in=1/p_out=0: kiểm tra chính xác 132 cạnh mỗi tháng và partition gồm hai tập đã khai báo, qua hai tháng × ba seed. So tập thành viên, không phụ thuộc tên nhóm detector và không lấy đáp án từ CSV truth hoặc partition trả về.
2. Hai tháng R rỗng vẫn là hai tháng được quan sát hợp lệ; thiếu cả thư mục tháng phải báo lỗi ở hai API, không biến thành empty graph hoặc sự kiện dissolve.
3. Stable/grow p_in=1/p_out=0 có graph tháng đầu giống byte, tháng sau khác: cohort reference phải khác, nhưng reference từng seed vẫn shared qua hai tháng trong dataset tương ứng.
4. Hai fresh process với `PYTHONHASHSEED=0/137`, input chuyển vị trí và thêm ba CSV truth giả không hợp lệ: sáu membership và references giữ nguyên. Chạy lại vào gói complete phải bị từ chối và giữ nguyên cả metadata/diagnostics/CSV.

Test không mock detector để tạo kết quả thành công. Fixture graph-only không có truth; decoy truth cố ý không đọc được để phát hiện nếu adapter bắt đầu phụ thuộc nhãn chuẩn. Config diagnostic không thay cohort development mặc định.

## Lệnh và kết quả test

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- Targeted adapter: **24/24 pass**, 0 skip/failure/error, **13.990s**.
- Toàn repo theo README: **234/234 pass**, 0 skip/failure/error, unittest **122.534s**; full log và CSV 234 test đã lưu. Tests dùng temporary synthetic data, không phải kết quả trên Reddit thật.
- Collector đầu tiên chỉ nhận các dòng `... ok` liền nhau nên đọc thiếu test có output audit xen giữa. Đã chỉnh collector, đọc lại log gốc kết thúc `OK`; không chạy lại suite. Thời gian wall của process chưa được lưu nên để null; chỉ báo thời gian unittest thực có trong log.
- Không build wheel hoặc chứng nhận cài sạch trong T05; phần môi trường sạch/gate demo còn ở PHUC-006-T05. Test-only task này không đổi package runtime.

## Đối chiếu điều kiện chấp nhận

[CSV gate](PHUC-003-T05-acceptance-gates.csv) lưu tên test đã thực sự pass, được đối chiếu với log full suite trước khi xuất. Đây là kiểm tra kỹ thuật của Phúc, chưa phải review/receipt của Đăng.

| Gate | Yêu cầu | Bằng chứng hành vi | Kết quả |
|---|---|---|---|
| AC01 | FR01/FR03/FR04 | Graph biết đáp án, hai tháng/ba seed, partition đúng user và lưu diagnostics | PASS |
| AC02 | FR02/FR03 | Đủ seed/canonical 0, không chọn theo quality, reference tách seed và cohort | PASS |
| AC03 | FR04 | Observed empty khác missing month; active/isolate không bị gán giả | PASS |
| AC04 | FR04 | Input lỗi bị từ chối; gói complete cũ không đổi qua fresh process | PASS |
| AC05 | FR01/FR03 | Metadata/hash/path đọc được khi chuyển input/gói; nguồn graph và reference đúng cohort | PASS |

Gate FR01–FR04 không tự hoàn tất **FR05/T06**: còn lượt chạy đủ cohort development với config mặc định.

## Output integration đã lưu

Bốn gói ở `artifacts/detection-tracking/phuc-003-t05-001/<case>/`, mỗi gói 9 file. Bốn process detector thật và bốn reader stdlib `python -I` đọc lại; **24 CSV/24 partition checks pass**, dùng các tập user khai báo độc lập.

| Case | Tháng | Active/assigned/isolate | Sizes ở mỗi detector seed |
|---|---|---|---|
| known-cliques | Cả hai tháng | 24 / 24 / 0 | 12;12 |
| observed-empty | Cả hai tháng | 24 / 0 / 24 | Rỗng; null quality/connectivity, ARI rỗng |
| changed-cohort (grow) | 2020-01 | 24 / 24 / 0 | 12;12 |
| changed-cohort (grow) | 2020-02 | 30 / 30 / 0 | 12;18 |
| relocated-decoy | Cả hai tháng | 24 / 24 / 0 | 12;12; sáu CSV khớp known-cliques |

Nguồn riêng có probabilities 1/0 hoặc 0/0, generator seed 11 và detector 0/1/2, gamma 1/canonical 0. Đây là fixture diagnostic theo case folder, không thêm vào cohort 0.50/0.02 hoặc tổng hợp thành kết quả nghiên cứu độc lập. Không tính AMI/accuracy từ bảng kiểm tra partition. [CSV integration 24 dòng](PHUC-003-T05-integration-summary.csv) lưu đủ month/seed/reference/status.

Input graph/config không đổi; config mặc định repo và **540 file output có trước** dưới `artifacts/detection-tracking/` giữ nguyên hash. Không chạy evaluation split hoặc tracker.

## Bằng chứng và tái tạo

- Proof: `artifacts/verification/phuc-003-t05-001/` có `full-tests.log`, CSV 234 test, gate/integration CSV, source fixtures, command helpers/reader độc lập, read/detect/no-overwrite logs, `verification-result.json`, source/output hashes.
- ZIP: `artifacts/verification/phuc-003-t05-001.zip`, **109 file, 84,016 byte**; mở lại kiểm tra CRC và từng entry đúng byte. SHA-256 **`34242b24fd73adaaac9ecf51b39f0e8f06bc8d8f0b0989befa791e5bffa2a482`**; sibling `.zip.sha256`/`.archive.json` lưu kiểm chứng.
- Hai CSV gate/integration version trong Git giống byte với bản proof. Artifact/ZIP đầy đủ chỉ ở local; clone repo có code/docs/CSV, không tự có những thư mục này.
- Chạy hai lệnh test trên để tái tạo gate bằng thư mục tạm, không cần gói artifact cũ. Cần cài `[graph]`; skip vì thiếu thư viện không được coi là gate pass. [README](../003-leiden-detection/README.md) có API xuất gói; với fixture riêng dùng config archived tương ứng và output path mới. Helper proof là record lượt kiểm chứng, không retry vào output/log path cũ.

**Tiếp theo PHUC-003-T06:** đủ lịch development/ba detector seed, lưu diagnostics/evidence và giữ ARI seed riêng với AMI truth. PHUC-003 chưa DONE toàn bộ; chưa có community matching, AMI evaluator, full-run freeze hoặc xác nhận nhận gói từ Đăng.
