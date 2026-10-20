# Kiểm tra bàn giao tracker/evaluator của Đăng — 20/10/2026

**Cập nhật sau review:** theo yêu cầu hoàn thành trong ngày, PR #12 đã được merge vào nhánh Phúc và tích hợp tại `89173ce`. Đã có `document/guide.md`, notebook chính 14 cells/8 hình, runner/config/provenance/diagnostics và gói output cuối; 94 tests liên quan đạt. [Bản bàn giao hiện tại](PHUC-DANG-FINAL-HANDOFF.md). Những phần bên dưới giữ kết quả review trước tích hợp; hai artifact/freeze lịch sử gốc của Đăng vẫn chưa đối chiếu, nhưng đã có output tái lập để bàn giao kỹ thuật.

**Kết luận:** source PR #12 chạy được và tái lập đúng các số Đăng báo. Đường truth khớp toàn bộ events/links; một notebook kiểm tra riêng đọc được cả hai đường. **Bàn giao artifact gốc và demo chung vẫn ở REVIEW**, chưa merge hoặc xác nhận nghiệm thu thay Đăng.

- PR: [#12 — Implement Jaccard tracking and evaluation artifacts](https://github.com/TamNgx179/reddit-community-evolution/pull/12).
- Nhánh Đăng: `feat/dang-001-tracking`, commit `57a39c67835e9a08efe0fe22eea99e5095b0c3d1`.
- Base đúng: `feat/phuc-006-handoff-demo`; merge-base là `5b460b1`, nghĩa là đã có phần Phúc T06.
- Kiểm tra source bằng bản snapshot riêng, không merge PR và không sửa bốn module của Đăng.
- Đầu vào là gói T02 đã gửi trước; không đổi seed/ngưỡng, không sinh graph hoặc chạy Leiden/AMI lại.

## 1. Có gì trên GitHub, còn thiếu gì?

PR có đủ bốn module `.py`, file test và `document/DANG-WEEK1.md` (474 dòng). **Không có `document/guide.md`** như tin nhắn bàn giao. Báo cáo DANG-WEEK1 có mô tả thuật toán/layout, nhưng mục lệnh batch chỉ ghi run ID và chưa có lệnh/API invocation đầy đủ để chạy hai split.

Hai đường dẫn sau **không có trên máy Phúc và không có trong Git tree của PR**:

```text
artifacts/detection-tracking/dang-week1-development-001/
artifacts/detection-tracking/dang-week1-evaluation-001/
```

`artifacts/` bị Git ignore. PR cũng không có file đính kèm hoặc release asset cung cấp hai thư mục trong lần kiểm tra này. Vì vậy, không thể xác nhận byte/checksum/metadata của **hai run gốc Đăng đã chạy** chỉ bằng việc pull nhánh. Không suy ra các run đó thiếu hoặc sai trên máy Đăng.

Để không chờ giao file mới, Phúc đã tái chạy **source đúng commit PR** trên input cũ, với run ID riêng. Các kết quả tái chạy là bằng chứng kiểm tra độc lập, không đóng vai run gốc của Đăng.

## 2. Kiểm thử và tái lập

| Kiểm tra | Kết quả thực tế |
|---|---|
| `tests.unit.test_jaccard_tracking` | 11/11 PASS |
| Regression `tests.unit.test_contracts`, `tests.unit.test_synthetic_io` | 23/23 PASS |
| Integrity handoff từng split trước khi chạy | Consumer API xác minh manifest/input, đủ 18 dataset/36 snapshot/108 lượt detector mỗi split |
| Development, source PR không sửa | 18/18 dataset; truth events và links khớp 18/18 |
| Evaluation, cùng source/ngưỡng/seed | 18/18 dataset; truth events và links khớp 18/18 |
| Output mỗi run tái lập | 254 file; `metadata.json`, `manifest.json`, đủ hai đường và 18 mapping CSV |
| Manifest output | 253 payload entries/run khớp SHA-256 và inventory, manifest tự loại khỏi hash |
| Đối chiếu metrics | Precision/recall/F1/support từng dataset và confusion khớp phép tính độc lập bằng sklearn |
| Bảo toàn input | 821 file gói T02 giữ nguyên hash trước/sau |
| Notebook kiểm tra riêng, kernel mới | 5/5 code cell, 2 hình confusion, không lỗi, 16,198 giây |

Không chạy lại full suite 385 test hoặc thí nghiệm detection. 34 test nêu trên là phạm vi kiểm tra mới. Không dùng kết quả evaluation để chỉnh tracker.

## 3. Số liệu Đăng báo được tái lập

| Chỉ số | Development | Evaluation |
|---|---:|---:|
| Dataset hoàn tất | 18/18 | 18/18 |
| Truth events/links khớp | 18/18 | 18/18 |
| Mean dataset detector macro-F1, sáu nhãn | 0,2561728395061728 | 0,2175925925925926 |
| Matched coverage | 1,0 | 1,0 |
| Unmatched truth | 0 | 0 |
| Detector source community dư | 3 | 6 |

**Hai cách tính F1 phải ghi rõ tên.** Mỗi dataset chỉ có 2–3 nguồn và không xuất hiện đủ sáu lớp; macro-F1 của dataset vẫn lấy trung bình sáu lớp với `zero_division=0`. Vì vậy, trung bình 18 điểm dataset có thể thấp ngay cả khi mọi dự đoán truth đều đúng.

Khi gộp đủ **39 nguồn truth trong từng split** rồi tính macro-F1 sáu lớp, nhận được:

| Đường chạy | Development | Evaluation |
|---|---:|---:|
| Truth → tracker, pooled macro-F1 | **1,0** | **1,0** |
| Leiden seed 0 → tracker, pooled macro-F1 | **0,85** | **0,655142599045038** |
| Số dự đoán detector đúng | 33/39 | 28/39 |

Không thay hoặc đổi tên số cũ của Đăng thành số gộp. Bảng trên là phép tổng hợp bổ sung từ cùng predictions. Mỗi split giữ support theo thứ tự stable/grow/shrink/merge/split/dissolve là **21/3/3/6/3/3**, gồm nhóm nền K. Khi gộp phải thêm dataset/reference/tháng từ metadata vì ID nguồn lặp giữa các dataset. Bảng CSV gộp đã giữ các khóa đó.

Coverage mapping 1,0 không có nghĩa dự đoán sự kiện đúng. Ví dụ development có 3 stable bị dự đoán split, 2 merge bị dự đoán split và 1 split bị dự đoán stable. Các trường hợp này được giữ, không sửa truth hoặc chọn seed khác.

## 4. Những điểm cần bổ sung trước khi chốt bàn giao

1. **Đưa đúng guide lên Git:** thêm `document/guide.md` hoặc đính chính dùng DANG-WEEK1; ghi đầy đủ lệnh chạy/API, input, output và môi trường.
2. **Giao hai artifact gốc:** gửi đường dẫn tải/ZIP của `dang-week1-development-001` và `dang-week1-evaluation-001`, kèm checksum. Đây là output tracker của Đăng, không phải yêu cầu Phúc gửi lại ZIP input. Khi nhận, Phúc đối chiếu manifest, references, predictions và metrics với run độc lập.
3. **Config/freeze:** source `run_split()` hiện không ghi `tracker-config.json`, mặc dù báo cáo dẫn đến file đó và mô tả đã khóa trước evaluation. Metadata có ngưỡng/seed, nhưng không đủ để xác nhận thời điểm khóa code/evaluator. Cần nhận file config/freeze gốc và provenance tương ứng; không tạo bằng chứng hồi tố rồi gọi là đã khóa trước evaluation.
4. **Confusion đường truth:** `_write_evaluation()` hiện xuất 6×7 cho cả hai đường, thêm cột `__unmatched__`. Handoff yêu cầu truth 6×6 và detector 6×7. Số liệu hiện đúng và cột unmatched bằng 0; cần thống nhất định dạng khi ghép chính thức.
5. **Diagnostics:** file `diagnostics.json` hiện lưu diagnostics của evaluator, không lưu `track(...)["diagnostics"]` như ambiguous source count. Nên bổ sung file riêng nếu demo/báo cáo muốn dẫn trực tiếp thông tin many-to-many.
6. **Integrity đầu vào:** `run_split()` chỉ ghi chuỗi `input_manifest_sha256` được truyền vào, không tự đối chiếu hash. Wrapper kiểm tra lần này đã chạy `inspect_synthetic_handoff()` trước batch. Guide chính thức cần giữ bước preflight này hoặc bổ sung xác minh trong runner.

Các điểm trên không phủ nhận kết quả tái lập; chúng là giới hạn bàn giao/format/provenance cần ghi rõ. Chưa đăng comment/review, gửi tin nhắn hoặc merge PR thay người dùng.

## 5. Đầu ra và notebook kiểm tra trên máy Phúc

Tính từ root repo:

```text
artifacts/review/dang-pr12-20261020-001/
    source.zip                         # snapshot đúng PR, không gồm raw Reddit
    source/                            # source/tests đã chạy
    tracker-tests.log                  # 11 tests
    contract-regression-tests.log      # 23 tests
    verify_delivery.py                 # batch + audit, output mới; không ghi đè run cũ
    replay.log
    replay-audit.json
    dataset-audit.csv                  # 36 dataset
    pooled-event-predictions.csv        # 156 hàng: 2 split × 2 đường × 39 nguồn
    pooled-per-class-metrics.csv        # 24 hàng
    run_notebook_check.py
    02_tracking_review.ipynb            # source không cache output
    02_tracking_review.executed.ipynb   # mở để xem ngay
    notebook-result.json
    development-confusion.png
    evaluation-confusion.png

artifacts/detection-tracking/
    phuc-review-dang-development-20261020-001/
    phuc-review-dang-evaluation-20261020-001/
```

Notebook này **đọc trực tiếp `truth_tracking` và `detector_tracking` từ hai run mới**, xác minh manifest, gộp đúng khóa mẫu, tính chỉ số và hiển thị confusion. Bản `01_synthetic_demo.ipynb` chính hiện vẫn chỉ có phần detection; chưa sửa notebook đó hoặc nhập tracker vào source nhánh Phúc.

Đầu ra review có thể đọc ngay, không phải chạy lại để xem. Hai script review chủ động từ chối output đã tồn tại. Nếu cần lặp lại, chọn proof/run ID mới và giữ gói T02 cùng source PR đã chốt; không ghi đè các run này.

Các JSON/CSV nhỏ được lưu cùng [reference](specs/phuc/evidence/PHUC-DANG-PR12-review.json), [bảng dataset](specs/phuc/evidence/PHUC-DANG-PR12-datasets.csv) và [chỉ số từng lớp](specs/phuc/evidence/PHUC-DANG-PR12-per-class.csv). Artifacts lớn vẫn local; không tự gửi ZIP hoặc đưa chúng lên Git.

## 6. Việc còn lại để demo chung

Phúc đã xác minh source và đọc được layout; có thể dùng các run review để chuẩn bị demo ngay. Khi Đăng gửi hai artifact gốc/guide/config, đối chiếu chúng với kết quả này, ghép vào notebook chính, giữ cả mean-dataset và pooled metrics cùng bảng lỗi, rồi hai người xác nhận demo. `EXT-D02/03` có bằng chứng replay kỹ thuật, nhưng artifact gốc và `PAIR-DEMO` chưa được nghiệm thu.

Tin nhắn có thể gửi Đăng:

> Ông ơi, tui kiểm tra PR #12 rồi, code chạy được, 11 test tracker pass. Tui chạy lại cả hai split thì ra đúng số ông báo, với notebook cũng đọc được output rồi. Trên Git tui thấy `document/DANG-WEEK1.md`, chưa thấy `document/guide.md`; ông push giúp tui guide có lệnh chạy đầy đủ nha. Hai folder artifact nằm trong `artifacts/` nên pull Git chưa có, ông gửi giúp tui hai bộ output gốc với checksum và file config/freeze đã dùng để tui đối chiếu rồi ghép demo. ZIP dữ liệu cũ của tui vẫn giữ nguyên, không cần tải lại. Tui cũng đã tính thêm F1 gộp 39 mẫu: development 0,85, evaluation khoảng 0,65514; số 0,25617/0,21759 ông báo vẫn giữ và ghi rõ là trung bình theo dataset nha.
