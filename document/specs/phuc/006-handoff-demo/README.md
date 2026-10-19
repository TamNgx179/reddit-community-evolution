# PHUC-006 — Kiểm tra và lập danh mục gói bàn giao

Owner: Phúc. [Spec](spec.md), [task board](../tasks.md#phuc-006), [contract](../contracts.md).

**Tiến độ:** T01 DONE, PHUC-006 **1/6**, tổng **31/36**. 51/51 targeted tests đạt; đã đọc đủ 36 dataset/72 snapshot/216 membership CSV, hai cặp output sau relocation giống byte. [Bằng chứng T01 và ZIP](../evidence/PHUC-006-T01-inventory.md), [run summary](../evidence/PHUC-006-T01-run-summary.csv), [dataset ledger](../evidence/PHUC-006-T01-dataset-ledger.csv). T02 hướng dẫn bàn giao tiếp theo; chưa có xác nhận Đăng.

## T01 làm gì?

Consumer [synthetic_handoff.py](../../../../src/reddit_sna/reporting/synthetic_handoff.py) đọc kết quả PHUC-005 đã hoàn tất, kiểm tra rồi tạo bản đồ file cho người nhận. Không cần chạy lại generator, Leiden hoặc AMI. Đây là bước chuẩn bị đầu vào để Đăng làm tracker; phản hồi Đăng nhận/đọc được vẫn phải ghi riêng.

Hai đầu vào hiện có:

| Split | Run ID | Dataset / snapshot / membership CSV | SHA-256 manifest |
|---|---|---|---|
| Development | `phuc-005-t05-development-001` | 18 / 36 / 108 | `34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e` |
| Evaluation | `phuc-005-t06-evaluation-001` | 18 / 36 / 108 | `e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c` |

Run nằm dưới `artifacts/detection-tracking/` trên máy Phúc. `artifacts/` bị ignore: clone GitHub chỉ có code, docs và bảng nhỏ; người nhận cần nhận thêm bundle đầy đủ. Evidence T01 ghi ZIP thực tế và cách đọc sau giải nén. Không tự thay hai manifest pins theo file vừa nhận nếu chưa đối chiếu nguồn giao.

## Dùng CLI

Chạy từ root repo với Python 3.11 trở lên. Lệnh standalone chỉ dùng standard library, không cần cài graph/sklearn hoặc package dự án:

```powershell
& .\.venv\Scripts\python.exe -I -S src/reddit_sna/reporting/synthetic_handoff.py `
  artifacts/detection-tracking/phuc-005-t05-development-001 `
  --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e `
  --output artifacts/detection-tracking/phuc-006-t01-development-002
```

Với evaluation, thay input bằng `phuc-005-t06-evaluation-001`, pin bằng hash tương ứng và output bằng tên mới. `-002` là ví dụ cho lượt đọc tiếp; nếu output đã có, chọn tên mới. Không chạy lại vào `-001` đã lưu bằng chứng. Parent output phải tồn tại, output không được chồng vào source.

API khi package đã cài:

```python
from pathlib import Path
from reddit_sna.reporting.synthetic_handoff import inspect_synthetic_handoff, export_synthetic_handoff

inventory = inspect_synthetic_handoff(Path("<complete-source-run>"), expected_manifest_sha256="<trusted-sha256>")
metadata = export_synthetic_handoff(Path("<complete-source-run>"), Path("<new-output-directory>"),
                                   expected_manifest_sha256="<trusted-sha256>")
```

API inspect chỉ đọc. API export ghi vào thư mục mới sau khi kiểm tra input; publication lỗi giữ partial files, không có complete metadata đọc được. CLI thành công exit 0/JSON summary; input sai hoặc output cũ exit 2/stderr, không có success JSON. Tham số pin tùy chọn trong API/CLI; khi bàn giao thực tế nên dùng hash đã đối chiếu từ người giao. Hash xác minh tính toàn vẹn, không tự chứng minh danh tính người giao.

## Đầu ra và cách Đăng dùng

Mỗi split có một index directory gồm:

- `inventory.json`: schema 1, hash/size của toàn bộ source run gồm manifest; run scope/split, dataset IDs, counts, canonical seed 0 và mapping từng dataset/tháng/seed.
- `snapshot_inventory.csv`: một hàng cho mỗi dataset/tháng/detector seed; 108 hàng mỗi split. Có reference truth/detector, paths graph/nodes/truth membership/events/links/detector membership và counts active/endpoint/isolate/nhóm. Cột `canonical` là `True`/`False`.
- `metadata.json`: ghi cuối, `status=complete`, hashes/sizes của hai file trên; `source_bundle_included=false`, `partner_acceptance=not_verified`.

Paths trong inventory là đường dẫn tương đối **từ source run**, không từ index directory; các absolute paths cũ trong provenance không được dùng để tìm dữ liệu. Có thể chuyển source run và index sang máy khác mà không đổi byte. Phải giữ cả source run đầy đủ và index; index không chứa lại graph hoặc membership CSV.

Để bắt đầu tracker, Đăng chọn một `dataset_id`, lấy hai tháng cùng dataset; dùng cặp `truth_*` cho kiểm chứng tracker trên truth và `detector_membership_file` của **canonical seed 0** cho tracker trên Leiden. Mỗi seed detector có reference riêng, dùng chung reference đó qua hai tháng. Tên nhóm truth và detector không dùng để nối trực tiếp; không ghép user giữa hai dataset. Seeds 1/2 giữ để chẩn đoán, không thay seed chính theo AMI.

## Consumer xác minh những gì?

- Root schema 2/type/scope phù hợp development hoặc heldout evaluation; manifest complete, đủ stages/progress/counts, không có failure/pending marker.
- Inventory file phải đủ/đúng, không có file lạ hoặc hash/size lệch; path tương đối an toàn, không nhận symlink. Pin manifest nếu caller cung cấp.
- Dataset identity/split/generator seed/tháng liên tiếp; config và source linkage; toàn lịch phải đủ khi selection ghi full, subset chỉ cho development đã ghi rõ.
- Node keys; cạnh vô hướng đơn, unit weight, endpoint thuộc active nodes; truth membership đúng một nhóm mỗi user; event/link keys, reference, source coverage và số links theo loại event.
- Cả ba seed detector: reference gắn đúng graph cohort/dataset/seed, mapping đủ và duy nhất, mỗi user đúng một nhóm; assigned users bằng chính xác endpoint R. Isolate vẫn ở active nodes và truth, không bị tự gán nhóm detector.
- Report evaluation complete và file hashes được kiểm tra. AMI, chất lượng phân hoạch và frozen runtime không tính/chứng nhận lại ở consumer này. Evidence PHUC-005 giữ các kiểm tra đó.

Input được kiểm tra lại trước khi trả kết quả/công bố metadata để phát hiện thay đổi trong lúc đọc. Tháng rỗng và graph không có cạnh vẫn có hàng mapping tường minh, membership header-only hợp lệ nếu endpoint rỗng. Đây là kiểm tra contract, không phải tự sinh lại planted truth hoặc nghiệm thu tracker.

## Nguồn benchmark đã khóa và bước sau

PHUC-006 thêm một reporting module mới; **42 file của frozen source PHUC-005 giữ nguyên byte**. Package hiện tại có thêm file nên không còn đúng closure 42 file của runtime đã khóa. Không nới source gate hoặc tạo lại freeze để chạy benchmark từ nhánh mới này. Muốn chạy lại generator/Leiden/evaluator theo T05/T06, dùng checkout driver `09623f1` cùng frozen source và đúng versions đã archive; consumer T01 đọc output mà không cần khớp runtime graph.

T01 chưa làm notebook, clean-kernel replay hoặc cài môi trường mới. Các phần đó thuộc T02–T06. Tracker, receipt/review và demo chung vẫn theo các mốc EXT-D riêng trên task board.
