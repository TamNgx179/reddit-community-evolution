# Bằng chứng PHUC-004-T04 — Metrics, summary và timing có phạm vi

**Task:** [PHUC-004-T04](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 4/6, tổng 22/36 task.
**Kiểm chứng hoàn tất:** 18/10/2026 22:08:49, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `6151258` cộng T04, nhánh `feat/phuc-004-detection-evaluation`, PR #9.
**Môi trường:** Python 3.12.6, sklearn 1.9.1, numpy 2.5.4, scipy 1.18.1. Không thêm dependency.

## Vừa làm gì

Thêm `export_detection_evaluation(pairs, output)` và CLI trong [evaluation/detection.py](../../../../src/reddit_sna/evaluation/detection.py). API nhận một hoặc nhiều cặp dataset graph/truth + detection đã lưu, xác minh/hash/recheck input, gọi loader/counts/AMI hiện có rồi ghi report mới. Dataset ID phải duy nhất trong report; khác cohort nhưng cùng ID cần report riêng.

Report thành công có **năm file**: `detection_metrics.csv`, `detection_summary.csv`, `ami-policy.json`, `timing.json`, `metadata.json`. Metrics key `(dataset_id,month,detector_seed)`, giữ context/reference/canonical/counts/coverage/AMI/status/reason/support/version. Metadata có input paths/hashes, versions, evaluator source hash, policy và output hashes; complete được publish cuối. Scope chỉ `detection-evaluation-only`, stage evaluation, chưa phải full-run orchestration.

Summary có hai mức scenario/all_scenarios, giữ split/difficulty/gamma và **từng detector seed riêng**. Seed 0 canonical, 1/2 diagnostic. Đơn vị là dataset-month; AMI mean trên các dòng `ok` với trọng số bằng nhau, không theo số người hoặc trung bình case means. Counts n_rows/n_datasets/valid/missing/status/reasons được giữ. All-null group vẫn hiện diện với mean/min/max trống; coverage 0 tính vào mean, coverage None được đếm thiếu. User support là số quan sát qua dòng, có lặp người.

## Cách chạy lại

[README](../004-detection-evaluation/README.md#xuất-metrics-summary-và-timing--t04) có lệnh CLI một dataset và schema từng file. Ví dụ sau tái tạo report development từ source run đã có, dùng output ID mới:

```powershell
@'
from pathlib import Path
from reddit_sna.evaluation.detection import export_detection_evaluation

root = Path("artifacts/detection-tracking")
source = root / "phuc-002-t06-001/datasets"
detection = root / "phuc-003-t06-001/datasets"
pairs = [(dataset, detection / dataset.name) for dataset in sorted(source.iterdir()) if dataset.is_dir()]
meta = export_detection_evaluation(pairs, root / "phuc-004-t04-replay-new")
print(meta["metric_rows"], meta["summary_rows"])
'@ | & .\.venv\Scripts\python.exe -
```

Source run trên phải được tạo theo PHUC-002 và detection theo PHUC-003; nếu nhận ZIP T04, thay hai paths bằng `inputs/development/source` và `inputs/development/detected` đã giải nén. Cài extra `[evaluation]` khi cần. Evaluator chỉ đọc lại input, không sinh graph/chạy Leiden mới hoặc truy cập bộ evaluation giữ lại.

## Test đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_summary tests.integration.test_detection_evaluation_export -v
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.unit.test_detection_summary tests.integration.test_detection_alignment tests.integration.test_detection_evaluation_export -v
```

**12/12 test T04 mới pass** (16.608s): 5 unit summary và 7 integration export. **44/44 test liên quan pass**, 0 skip/failure/error, log cuối **16.182s**, process wall **17.436s**. Gồm 32 test T01–T03 và exporter/summary/timing mới; chưa chạy full repo suite ở T04.

Unit tests dùng oracle cố định: mean 0.25 từ điểm 1/-0.5 dù số user khác nhau, null không biến thành 0, seed tách riêng, all-null support/reason, coverage 0 khác None, không gộp split/difficulty/gamma. Integration tests kiểm tra 5-file package/hashes, key/support, raw timing không nhân ba, CLI replay/no-overwrite, duplicate ID/output overlap/input lỗi, diagnostics timing bị sửa rồi rehash, partial I/O failure chưa có complete metadata và input thay đổi trong lúc chấm bị chặn. Cases timing lỗi có negative/bool/NaN/thiếu tháng/sai cohort/schedule/run references.

## Kết quả thực tế

Đọc input copies T03: 18 development dataset của PHUC-002/003, sáu case × generator 11/12/13, hai tháng giả lập, detector 0/1/2, gamma 1/canonical 0. Runtime/config/source không đổi. Xuất hai CLI process với `PYTHONHASHSEED=0/137`; lượt hai đảo thứ tự dataset pairs.

| Kiểm chứng | Kết quả |
|---|---|
| Mỗi lượt development | 18 dataset, **108 metrics, 21 summary, 36 stored detection month timings** |
| AMI support mỗi lượt | 99 ok / 9 null có cờ; cả 108 dòng AMI/ref/coverage khớp T03 |
| Replay | Metrics CSV, summary CSV, policy JSON **giống byte**, dù đảo input order/hash seed |
| No-overwrite | CLI vào output cũ exit 2, cả năm file giữ nguyên hash |
| Diagnostic mixed-isolates | 6 metrics, 6 summary, 2 timing; 3 AMI ok / 3 null |
| Diagnostic zero-edges | 6 metrics, 6 summary, 2 timing; AMI đều null/empty, summary giữ 2 missing rows mỗi seed/level |
| Consumer độc lập | **4 report / 228 metrics / 54 summaries / 76 timing entries** đều kiểm tra thành công |
| Bảo toàn | **2.001 artifact cũ** giữ hash, gồm 904 file detection-tracking và proof/ZIP T01–T03; code/config/test hashes cũng giữ nguyên |

Consumer đọc CSV/input được chỉ định, gọi thẳng sklearn cho AMI, tự tính counts/means/support/reasons và đối chiếu raw stored timing/hashes; không import project/igraph. Dùng cùng thư viện metric, không tự viết lại công thức AMI. 228 dòng là số lượt đọc qua các report có replay, không phải 228 dataset độc lập. Dữ liệu là benchmark tổng hợp, không phải kết quả Reddit.

Các hàng `all_scenarios` của report đầu:

| Seed | Vai trò | Dataset / dòng | AMI hợp lệ / thiếu | AMI mean trên dòng hợp lệ | Coverage mean |
|---|---|---|---|---:|---:|
| 0 | canonical | 18 / 36 | 33 / 3 | 0.9558799269999274 | 1.0 |
| 1 | diagnostic | 18 / 36 | 33 / 3 | 0.9487475264624783 | 1.0 |
| 2 | diagnostic | 18 / 36 | 33 / 3 | 0.9546409700892936 | 1.0 |

Mỗi seed có ba hàng truth_constant từ dissolve tháng thứ hai. Riêng summary dissolve seed 0 có 6 dòng, 3 valid/3 missing; AMI mean 1 chỉ của ba dòng valid tháng đầu. Canonical vẫn là 0 theo cấu hình, không chọn seed theo mean vừa xem.

## Timing và output đã lưu

Timing detection **0.4645643999974709s** là tổng 36 `wall_seconds` nguồn, mỗi tháng gồm cả ba seed; không chạy lại detector và không cộng cùng thời gian ba lần. Report đầu đo evaluation **6.54213489999529s** gồm preflight/input verify/load/counts/AMI/summary, trước output writes; compute-only **2.8529200998600572s**, policy+CSV writes **0.016973899997537956s**. Generation/peak memory null vì chưa đo. Full CLI process wall **9.238s / 8.645s**, gồm startup và I/O; các số trên là record phạm vi chạy, chưa phải benchmark hiệu năng.

- Report chính `artifacts/detection-tracking/phuc-004-t04-001/`, replay `phuc-004-t04-002/`, mỗi gói năm file. Metadata không tự hash chính nó, hash bốn file output khác; absolute producer paths là provenance, consumer nhận input root mới để relocation.
- Theo Git: [metrics 108 dòng](PHUC-004-T04-detection-metrics.csv), [summary 21 dòng](PHUC-004-T04-detection-summary.csv), [timing JSON](PHUC-004-T04-timing.json), đúng byte từ report đầu.
- Proof local `artifacts/verification/phuc-004-t04-001/`: 360 input files, bản sao bốn report, runner/consumer, T03 reference CSV, test/export/reader/no-overwrite logs, 44-row test CSV, before/result/proof hashes.
- ZIP `artifacts/verification/phuc-004-t04-001.zip`: **397 file, 371.964 byte**, CRC/từng entry/proof hash manifest đã kiểm tra. SHA-256 **`5585b0ca39759dc9caee1e853121644e114b4ee169342c9a1fb89329ff4807c9`**; sibling `.zip.sha256` và `.archive.json` lưu thông tin archive.

Cài sklearn extra, giải nén ZIP rồi đọc độc lập, không cần import package project:

```powershell
python -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/reports/development-first <thu-muc-giai-nen>/inputs/development
```

Thay `development-first`/`development` bằng `mixed-isolates` hoặc `zero-edges` để đọc diagnostic. Full artifacts/ZIP bị ignore, người nhận cần ZIP thực tế hoặc tự tái tạo; `verify.py` là recorder một lượt, không retry vào output/log cũ.

**FR04/T04 DONE. Tiếp theo PHUC-004-T05:** kiểm tra tổng hợp invariants/AC của evaluator; T06 giữ mốc nghiệm thu stable/grow. Chưa thực hiện evaluation/freeze/full orchestration PHUC-005 hoặc có receipt/review Đăng.
