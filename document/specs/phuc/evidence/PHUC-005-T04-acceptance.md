# Bằng chứng PHUC-005-T04 — nghiệm thu lifecycle và replay

**Task:** [PHUC-005-T04](../tasks.md#phuc-005). **Kết quả:** DONE; PHUC-005 **4/6 DOING**, tổng **28/36 task**.
**Ngày:** 19/10/2026, Asia/Bangkok. **Source cơ sở:** `df224d6`, nhánh `feat/phuc-005-reproducible-runs`, PR #10.
**Kiểm chứng hoàn tất:** 19/10/2026 10:34:11 (UTC+07:00).

## Vừa làm gì

T03 đã bổ sung hồ sơ cho từng run; T04 kiểm tra hồ sơ và đường chạy đó có xử lý đúng cả lúc thành công, chạy lại hoặc lỗi hay không. Thêm **5 integration tests** trong [test_synthetic_benchmark_run.py](../../../../tests/integration/test_synthetic_benchmark_run.py). Không sửa code runtime, dependencies, recipe, detector, AMI policy hoặc seed canonical.

- **Run started:** một thư mục đã có checkpoint và file dở phải bị từ chối trước backend; không sửa nội dung cũ.
- **Lỗi lưu cấu hình:** giả lập JSON config chỉ ghi được một byte rồi lỗi. Run phải failed tại configuration, giữ file/hash đã tạo, chưa sinh graph; retry vào failed run không được ghi đè.
- **CLI nhận sai counts:** evaluator đã tạo child report hợp lệ, nhưng trả count sai. CLI phải exit 2, không in JSON thành công; root failed tại evaluation, giữ sáu metric rows thật và progress 1 generated/1 detected/0 evaluated.
- **Atomic publication lỗi:** tạo pending complete manifest thật rồi giả lập lỗi `Path.replace`. Checkpoint trước đó còn started; helper ghi lại failed, giữ report đã có, không để root complete giả.
- **Hai CLI process cùng run ID:** một process thành công, một process exit 2 vì run đã tồn tại; chỉ có một report đầy đủ và không có failure marker của process thua ghi vào run thắng.

Các file lỗi được tạo trong thư mục tạm hoặc output mới của bằng chứng; không sửa data gốc hay artifact trước đó. Đây là kiểm tra lỗi có chủ đích, không phải phát hiện benchmark thật bị lỗi.

## Test và phạm vi đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_run_provenance tests.integration.test_synthetic_benchmark_run -v
```

**23/23 pass**, 0 skip/failure/error; unittest **109.220s**, process wall **110.693s**. Gồm 22 integration tests và 1 provenance unit test, bao gồm 5 test T04 mới cùng các kiểm tra preflight/config/selection/null/default-development/failure/replay T02/T03.

**Không chạy lại full repo suite tại T04.** Code runtime/config không đổi so với T03 `df224d6`, nơi 314/314 test toàn repo đã đạt; không trình bày kết quả đó thành một lượt full suite mới hoặc claim 319/319. Log targeted và CSV 23 test được giữ trong proof.

## Demo được chọn trước khi xem kết quả

Stable + dissolve development, generator seed 11, hai tháng 2020-01/02, detector 0/1/2, canonical 0. Mỗi successful run dự kiến 2 dataset/4 snapshot/12 metrics/9 summary; 3 dòng dissolve tháng cuối giữ AMI null theo policy vì truth chỉ còn background group K. Không chọn ngưỡng điểm để loại output.

Hai CLI process chạy mới với hash seed 0/137 và đảo thứ tự dataset selection. Đối chiếu byte các CSV/policy, đối chiếu phân hoạch bằng tập user trong từng nhóm; đổi tên nhóm và đảo thứ tự dòng trong RAM phải giữ phân hoạch, cố chuyển một user thành nhóm riêng phải bị nhận ra là thay đổi.

Output mới đã lưu trong `artifacts/detection-tracking/phuc-005-t04-001/`, `phuc-005-t04-002/`. Controlled failure `phuc-005-t04-failure-001/` dùng stable, tạo child report rồi cố ý trả counts sai; root failed. `phuc-005-t04-started-001/` là guard fixture giả lập checkpoint, **không chạy thuật toán**, không được cộng vào benchmark datasets.

Consumer stdlib audit root manifest/source/config/output hashes sau relocation; consumer CSV/direct sklearn kiểm tra report độc lập, không import project/igraph. Child report của failed run cũng được kiểm tra riêng để chứng minh child complete chưa đủ kết luận cả run complete. Guard fixtures failure/pending marker phải bị chặn trước khi đọc các bảng; một temporary copy bị sửa byte phải bị inventory check chặn.

## Phạm vi điều kiện nghiệm thu PHUC-005

| AC | Trạng thái tại T04 | Căn cứ/việc còn lại |
|---|---|---|
| AC01 | PASS | API/CLI chạy detection evaluation không cần tracker, scope chỉ development detection |
| AC02 | PASS | Failure/config/publication/counts, giữ output/progress, started/failed/complete không overwrite |
| AC03 | PASS | Fresh-process replay, byte/partition comparison; tên nhóm/thứ tự dòng không đổi phân hoạch |
| AC04 | PENDING T06 | Test có full development fixture 18 dataset/108 metrics; demo T04 chỉ 2 dataset, chưa chạy toàn lịch 36 dataset/72 snapshot/216 đơn vị |
| AC05 | PENDING T05/T06 | Hash/source provenance đã kiểm tra; formal freeze và evaluation giữ lại chưa chạy |

T04 hoàn tất kiểm tra FR02/FR03/FR05 trong phạm vi task; không tự đánh toàn bộ spec PHUC-005 DONE. T05 mới formal development/freeze; T06 mới evaluation giữ lại. Artifact consumer ở proof là công cụ nghiệm thu T04, chưa thay consumer bàn giao tổng quát PHUC-006.

## Kết quả thực tế đã lưu

| Kiểm chứng | Kết quả |
|---|---|
| Tests | **23/23 pass**, gồm 5 test mới; runtime/config giữ nguyên, không chạy lại full repo suite |
| Mỗi successful run | **2 dataset/4 snapshot/12 metrics/9 summary**, 88 hashed output files + root manifest |
| Valid/missing | **9 AMI hợp lệ bằng 1.0, 3 null**, status `degenerate_partition`, reason `truth_constant`; coverage 1.0 cả 12 dòng |
| CSV/policy replay | **29 file giống byte**; không yêu cầu timing/timestamp/provenance giống |
| Partition replay | **12/12 membership files** khớp theo nhóm user; **12/12** đổi tên nhóm/đảo dòng giữ kết quả, negative control đổi membership được phát hiện |
| Root audits | **3/3 pass** ở mode tương ứng: hai complete, một failed; source/config/output hashes khớp trên copies sau relocation |
| Report audits | Hai success reports: mỗi report 12 metrics/9 summary/4 timing; failed child: 6 metrics/6 summary/2 timing cũng hợp lệ, **root vẫn không được chấp nhận** |
| Controlled failure CLI | Exit **2**, stdout rỗng, root failed tại evaluation; progress **1 generated/1 detected/0 evaluated**, 70 hashed outputs được giữ |
| Root rejection probes | **5/5 chặn đúng lý do**: started, failed, failure marker, pending marker, modified output byte |
| No overwrite | **3/3 trạng thái complete/failed/started** bị CLI từ chối, exit 2, hash mọi file giữ nguyên |
| Bảo toàn | **4.043 artifact cũ** và **91 source/config/test files** giữ hash trong lúc kiểm chứng |

[Acceptance matrix](PHUC-005-T04-acceptance-matrix.csv) giữ cả ba AC pass và hai AC pending, mỗi dòng dẫn tới test thực sự đã chạy. [Partition comparison](PHUC-005-T04-partition-comparison.csv) có 12 dòng; [run summary](PHUC-005-T04-run-summary.csv) ghi hai success runs cùng một controlled failure, không trộn vào kết quả thành công.

[Metrics 12 dòng](PHUC-005-T04-detection-metrics.csv) và [summary 9 dòng](PHUC-005-T04-detection-summary.csv) được version để nhóm xem cả null/support ngay trong Git. Hai replay dùng cùng hai dataset IDs nên không cộng thành bốn dataset độc lập; ba detector seeds cũng không thành ba dataset độc lập. Đây là dữ liệu tổng hợp, không phải phát hiện từ Reddit thật.

ZIP local `artifacts/verification/phuc-005-t04-001.zip`: **312 file, 549.729 byte**, đã kiểm tra CRC và từng entry khớp byte. SHA-256 **`896df0aa9aee309645eef035484529ad0f8941693b0cd34cbcb74f41577fe0f6`**. `proof-hashes.json`, sibling `.archive.json`/`.zip.sha256` giữ checksum; script/lệnh, tests, raw stdout/stderr, run copies, source snapshots và negative probes đều trong proof. Temporary tamper copy đã được dọn tự động; `tamper-proof.json` và script/log giữ cách tái tạo và hai hashes, output gốc không bị sửa.

## Đọc lại bằng chứng

Proof local `artifacts/verification/phuc-005-t04-001/` giữ tests/log/source/config, acceptance plan, bản sao success/replay/failed/started, consumers và scripts ghi bằng chứng một lượt. Khi đã nhận ZIP thực tế và giải nén:

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_run.py <thu-muc-giai-nen>/runs/first complete
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/runs/first/evaluation <thu-muc-giai-nen>/runs/first/inputs
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_run.py <thu-muc-giai-nen>/runs/failed complete
```

Hai lệnh đầu phải thành công; lệnh cuối phải bị từ chối. Đổi expected status thành `failed` chỉ dùng để audit hồ sơ lỗi, không cho phép xem như run hoàn tất. Thay `first` bằng `replay` để audit lần hai. Consumers dùng path tương đối của gói, không đòi absolute producer paths còn tồn tại.

Full artifacts/ZIP local bị Git ignore; code tests/docs và CSV nhỏ theo Git. Chưa có tracker, receipt hay review Đăng.
