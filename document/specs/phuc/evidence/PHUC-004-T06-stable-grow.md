# Bằng chứng PHUC-004-T06 — Nghiệm thu stable/grow development

**Task:** [PHUC-004-T06](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 **6/6 DONE**, tổng **24/36 task**.
**Ngày thực hiện theo lịch người dùng:** 19/10/2026, Asia/Bangkok.
**Hoàn tất kiểm chứng chính:** 19/10/2026 09:00:16 (UTC+07:00).
**Source:** cơ sở `523f4d0` trên nhánh `feat/phuc-004-detection-evaluation`, PR #9. T06 dùng evaluator và cấu hình đã kiểm tra ở T05; không đổi code, dependency hoặc policy.

## Phạm vi đã chốt trước khi chấm

Chọn **cả stable và grow**, mỗi kịch bản dùng toàn bộ generator seeds development **11, 12, 13** trong `configs/benchmark_week1.json`. Mỗi dataset có hai tháng `2020-01/2020-02` và ba detector seeds **0, 1, 2**, gamma **1**, canonical **0**. Lịch ghi vào `acceptance-plan.json` trước hai lệnh evaluator; không đặt ngưỡng điểm hoặc chọn seed theo kết quả.

Input là graph/truth đã sinh ở `artifacts/detection-tracking/phuc-002-t06-001/datasets/` và membership Leiden thật đã lưu ở `artifacts/detection-tracking/phuc-003-t06-001/datasets/`. Hai manifest nguồn complete; gói input được copy và so byte/hash trước khi chấm. Chỉ chạy evaluator mới, không sinh lại graph hoặc chạy lại Leiden. Các trường hợp này là benchmark tổng hợp development, không phải kết quả Reddit hoặc tập evaluation giữ lại.

## Cách hiểu dữ liệu và điểm

- **Stable:** nhóm chính có 12 user qua hai tháng, nhóm nền K có 12; tổng active giữ 24. Tên nhóm chính chuẩn đổi A → C để kiểm tra cấu trúc thành viên thay vì dựa vào tên nhóm.
- **Grow:** nhóm chính tăng 12 → 18 user, nhóm nền K giữ 12; tổng active tăng 24 → 30. Nhãn community chuẩn là ground truth được tạo từ kịch bản, không được suy ra từ detector.
- Mỗi dòng metrics ứng với **một dataset, một tháng và một detector seed**. AMI so cấu trúc phân nhóm trên cùng tập endpoint user; coverage là assigned/active, có phản ánh isolate nếu có.
- Summary canonical dùng seed 0 đã chốt. Seeds 1/2 là kiểm tra độ ổn định bổ sung; không gộp ba seed thành ba dataset độc lập. AMI 1 là phân hoạch khớp truth ở tập được chấm; coverage 1 là gán đủ active user trong những snapshot này.

## Kết quả nghiệm thu

| Phạm vi | Dataset / snapshot | Metrics / AMI hợp lệ / thiếu | AMI mean seed 0 | Coverage mean seed 0 |
|---|---|---|---:|---:|
| Stable | 3 / 6 | 18 / 18 / 0 | 1.0 | 1.0 |
| Grow | 3 / 6 | 18 / 18 / 0 | 1.0 | 1.0 |
| Toàn bộ stable/grow | 6 / 12 | **36 / 36 / 0** | **1.0** | **1.0** |

Mỗi report có **36 metrics, 9 summary, 12 stored month timings** đúng lịch. Cả 36 dòng có AMI **1**, coverage **1**, hai community dự đoán và không có isolate trong tập này. Seeds 1/2 cũng có mean 1, nhưng canonical vẫn là seed 0. Summary overall mỗi seed có 6 dataset/12 dòng, 12 hợp lệ/0 thiếu và **306 lượt user**; full trace ba seed có **918 lượt user**, không phải 918 người độc lập.

[Metrics đầy đủ](PHUC-004-T06-detection-metrics.csv), [summary](PHUC-004-T06-detection-summary.csv) và [dataset ledger](PHUC-004-T06-dataset-ledger.csv) được commit để thành viên xem ngay. Toàn bộ 36 dòng metrics khớp đúng các dòng stable/grow trong report T04. T06 chạy evaluator mới trên các input đã có; điểm giống T04 là đối chiếu tính tái lập, không phải thêm dataset hoặc phép đo độc lập.

Điểm cho thấy detector khôi phục đúng các phân hoạch easy đã chọn. Nó không chứng minh khả năng xử lý mọi tình huống: T04 đã giữ kết quả sáu case và các null ở dissolve; kiểm tra isolate/null/error nằm trong T05. Chưa suy rộng kết quả sang Reddit hoặc đánh giá tracker.

## Truy vết user, cấu hình và phiên bản

Proof local mới: `artifacts/verification/phuc-004-t06-001/`.

Report chính `artifacts/detection-tracking/phuc-004-t06-001/`, replay `phuc-004-t06-002/`, mỗi thư mục có năm file evaluator. Proof giữ bản sao tại `reports/first/` và `reports/replay/`.

- `inputs/source/<dataset-id>/` và `inputs/detected/<dataset-id>/`: 108 file input, gồm CSV graph/nodes/truth/predictions, metadata, cấu hình generator/detector và diagnostics. References/config hashes giữ nguyên từ gói nguồn.
- `dataset-ledger.csv`: sáu dataset, source/detector run IDs và đường dẫn gốc, metadata/config hashes, tháng, generator/detector seeds, gamma/canonical. Người đọc dùng đường dẫn trong ZIP nếu chuyển máy; đường dẫn producer trong metadata chỉ ghi xuất xứ.
- `scored-users.csv`: mỗi dòng có dataset/month/seed/user, nhãn truth và prediction, canonical và hai references. Khóa user phải đi kèm dataset/month; tên như `u001` lặp giữa dataset không chỉ cùng một người.
- `scored-sets.csv`: số active/scored và hash danh sách user đã sắp thứ tự cho từng dòng metrics. Đây là cách đối chiếu tập người được chấm, không chỉ nhìn điểm tổng hợp.
- `provenance/`: hai manifest run nguồn, bản sao benchmark JSON/TOML và source evaluator. `before.json` giữ source/config/artifact hashes cùng revision/working tree; `result.json` giữ phiên bản thư viện, lệnh, timing và kết quả kiểm tra.

Môi trường thực chạy: **Python 3.12.6, scikit-learn 1.9.1, numpy 2.5.4, scipy 1.18.1, igraph 1.0.0, leidenalg 0.12.0**. Benchmark JSON SHA-256 `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`; evaluator source SHA-256 `8dd7bda876d443b3defc31a3c33a206aecf5d111a71dcb8e1469cca68accc422`. Policy `synthetic-ami-v1`, arithmetic normalizer; runtime detector/config/source hashes từng dataset có trong ledger/metadata. Config generator lưu dạng canonical JSON nên hash file nguồn có thể khác file benchmark ban đầu dù nội dung cấu hình tương đương; ledger giữ cả source config và runtime config hashes.

ZIP `artifacts/verification/phuc-004-t06-001.zip`: **140 file, 238.372 byte**, đã kiểm tra CRC/từng entry khớp byte. SHA-256 **`0ac5f6ba6d33bad42211c3ac90519e55146c87822cf1e1a929fc70bb5061c75f`**; `.archive.json` và `.zip.sha256` giữ thông tin/checksum. Hash manifest trong gói ghi hash các file proof còn lại.

`read_report.py` đọc input/CSV và gọi trực tiếp sklearn, không import project hoặc igraph. Nó tự kiểm tra user sets, references, counts, policy null, AMI, summary support/means, metadata hashes và stored timing. Có thể đọc sau khi giải nén ZIP:

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/reports/first <thu-muc-giai-nen>/inputs
```

Thay `first` bằng `replay` để kiểm tra lượt thứ hai. Cần sklearn trong Python đang dùng. Full artifacts/ZIP bị ignore; người nhận cần nhận ZIP thực tế hoặc chạy lại hướng dẫn trong [README](../004-detection-evaluation/README.md). Recorder `verify.py` là script bằng chứng một lượt; không chạy lại vào output đã tồn tại.

## Kiểm tra đã thực hiện

| Kiểm tra | Kết quả |
|---|---|
| Test evaluator | **48/48 pass**, 0 skip/failure/error; unittest **54.530s**, process wall **56.473s**; `unittest.log` và `tests.csv` |
| Hai CLI process | Hash seed 0/137 và thứ tự pair đảo ngược; metrics/summary/policy **giống byte**; process wall **8.837s / 8.561s** |
| Reader độc lập | Cả hai report đạt: mỗi report 36 metrics/9 summary/12 timing, 36 AMI hợp lệ; không import project/igraph |
| Đọc ZIP sau relocation | Giải nén sang thư mục tạm mới có dấu cách và chạy reader bằng `python -I`: report first đạt 36 metrics/9 summary/12 timing; log sibling `artifacts/verification/phuc-004-t06-001-relocation.log` lưu riêng ngoài ZIP |
| No-overwrite | Lặp vào report chính exit 2 và giữ nguyên hash mọi file |
| Artifact cũ | **3.105 file giữ nguyên SHA-256**; 85 source/config/test files giữ hash trong lúc kiểm chứng |

Full repo **286/286 pass ở T05** tại `523f4d0`; T06 không chạy lại toàn bộ suite vì không sửa code/config. Log full suite cũ được bảo toàn; không trình bày thành một lượt full suite mới.

Timing detector **0.15951659996062517s** lấy từ diagnostics của run nguồn: 12 dataset-month, mỗi tháng đã gồm cả ba detector seeds, không cộng cùng thời gian ba lần. Report đầu đo evaluation **7.03137969999807s**, compute-only **4.991707300127018s**, policy+CSV export **0.00834890000987798s**. Generation và peak memory null vì không đo trong evaluator. Timestamp/timing mới không cần giống giữa replay; đây là chi phí có phạm vi của lượt thực thi, chưa phải benchmark hiệu năng.

Phần freeze, orchestration và tập evaluation giữ lại thuộc PHUC-005. Tracker, macro-F1 sự kiện và phản hồi nhận/review của Đăng chưa được thực hiện trong task này.

**FR05/T06 và PHUC-004 DONE. Tiếp theo PHUC-005-T01:** rà soát lịch case/seed/policy và cách tách development/evaluation trước khi ghép orchestration.
