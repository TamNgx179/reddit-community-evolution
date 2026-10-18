# Bằng chứng PHUC-004-T01 — Xác minh và căn nhãn theo user ID

**Task:** [PHUC-004-T01](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 1/6, tổng 19/36 task.
**Kiểm chứng dữ liệu hoàn tất:** 18/10/2026 20:47:01, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `27f198a` cộng T01, nhánh `feat/phuc-004-detection-evaluation`, tách sau PHUC-003/PR #8.
**Môi trường:** Python 3.12.6. Loader mới chỉ dùng stdlib và module project hiện có; chưa thêm dependency. Integration fixture dùng igraph 1.0.0/leidenalg 0.12.0.

## Vừa làm gì?

Thêm [evaluation/detection.py](../../../../src/reddit_sna/evaluation/detection.py) với `align_memberships` cho record trong bộ nhớ và `load_aligned_detection` cho gói graph/truth + detector đã lưu. Hàm xác minh dataset/identity/reference/tháng/user, source/runtime config, file hashes và graph cohort/mapping; chỉ sau đó mới xếp hai vector nhãn theo cùng user ID.

Ví dụ hai CSV xếp người khác thứ tự: truth có `u002 → B, u001 → A`, detector có `u001 → c1, u002 → c0`. Kết quả phải là users `[u001,u002]`, truth `[A,B]`, prediction `[c1,c0]`. Community giữ tên riêng; không coi `A` và `c1` là khác partition chỉ vì tên khác, cũng không tự tracking qua tháng.

Truth phải có đúng mọi active user; prediction phải có đúng endpoint của R. Duplicate, user thiếu/lạ, prediction trên isolate, sai reference/tháng hoặc graph khác bị từ chối. Không âm thầm chỉ chấm phần giao. Tháng rỗng vẫn có snapshot/vector rỗng; truth của isolate được giữ trong `truth_labels_all`. [Hướng dẫn API và chạy lại](../004-detection-evaluation/README.md) mô tả đầy đủ hai tập người.

T01 chuẩn bị dữ liệu cho các bước sau: **chưa tính coverage/số nhóm/AMI**, chưa triển khai policy metric missing/degenerate hoặc output metrics/summary của T04. Không thay adapter Leiden, canonical seed hoặc config; không chạy evaluation/tracker.

## Test đã chạy và giới hạn lượt discover

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.integration.test_detection_alignment -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_validation -v
```

- Lượt targeted ban đầu **13/13 pass, 9.813s**. Sau đó thêm guard scope/stage/diagnostics schema và ba tình huống tương ứng vào test integration hiện có; cả 13 test mới được chạy lại thành công trong discover.
- Lượt discover bị helper dừng ở **300 giây**, đã ghi **250 test `ok`**, đang chạy test cuối `unit.test_validation.ValidationPipelineTests.test_validation_new_run_hashes_handoff_and_no_overwrite`; không có final `OK` cho cả lượt này. Log được giữ nguyên ở `unittest-timeout-300s.log`.
- Chạy lại **toàn bộ module validation: 11/11 pass, 25.545s** (process wall 26.722s), gồm test bị ngắt. Hai log được đối chiếu theo test ID: **251 test khác nhau được kiểm chứng pass**, 0 skip/failure/error được ghi nhận; đây là tổng bao phủ qua hai lượt, không phải một lượt discover hoàn tất. `tests.csv` có 251 dòng và chỉ rõ log làm bằng chứng cho mỗi test.

Unit tests kiểm tra thứ tự user thay vì dòng/community, đổi tên nhóm giữ đúng mapping, khóa theo tháng, truth/prediction trùng/thiếu/lạ/sai ref/tháng, maps sai, one-shot iterables, active isolate và tháng hoàn toàn rỗng. Integration tests tạo graph/detection thật để kiểm tra ba seed, relocation/read-only, metadata/mapping/seed/path lỗi, hash bị sửa, graph đã rehash nhưng cohort cũ, graph không có cạnh. AMI invariance và metric policy còn ở T03/T05.

## Đối chiếu actual development đã lưu

Đọc lại source `artifacts/detection-tracking/phuc-002-t06-001/datasets/` và detection `artifacts/detection-tracking/phuc-003-t06-001/datasets/`. Đây là **benchmark tổng hợp**, không phải kết quả Reddit. Sáu case, generator development 11/12/13, hai tháng giả lập 2020-01/2020-02; gamma 1, detector 0/1/2, canonical vẫn 0.

| Kiểm chứng | Kết quả |
|---|---|
| Dataset gốc | 18 |
| Lần gọi loader, mỗi lần một dataset/seed | 54 |
| Snapshot vectors, tháng × dataset × detector seed | 108 |
| Cặp nhãn theo `(dataset, seed, month, user_id)` | 3.024 |
| Ví dụ stable g11 seed 0 | 48 dòng, hai tháng |
| Consumer độc lập `python -I`, chỉ stdlib | 54 gói/108 snapshot/3.024 cặp khớp CSV gốc |
| Input copy trong proof | 324 file: 18 source và 18 detection package |
| Bảo toàn output cũ | 904 file không đổi SHA-256; source/runtime/code kiểm tra cũng giữ nguyên |

Consumer đọc trực tiếp `nodes.csv`, `R.csv`, truth và membership seed tương ứng; tạo map theo user ID, đối chiếu active/endpoints/reference/month và từng phần tử của vector. Consumer không import project, sklearn hoặc igraph. 3.024 là số cặp nhãn có lặp người qua tháng/seed; không phải số người độc lập. Default data không có isolate; empty/isolate được kiểm tra bằng fixture riêng.

## Output đã lưu và cách xem

- [Bảng alignment 108 dòng](PHUC-004-T01-alignment.csv): dataset/context/seed/month, số cặp nhãn, thứ tự user và hai reference; trạng thái `aligned-only`.
- [CSV ví dụ 48 dòng](PHUC-004-T01-user-example.csv): mở để xem mỗi user có nhãn truth/prediction nào trong stable g11 seed 0.
- Full proof local: `artifacts/verification/phuc-004-t01-001/`: `aligned-vectors.json`, `aligned-user-pairs.csv` 3.024 dòng, hai CSV trên, input copies, recorder/consumer, hai test logs, 251-row test CSV, result/before/proof hashes.
- ZIP final `artifacts/verification/phuc-004-t01-001-final.zip`: **339 file, 285.748 byte**, đã kiểm tra CRC, từng entry đúng byte và toàn bộ `proof-hashes.json` bên trong. SHA-256 **`4eb1c361db2a683552cdf10cf94052f0532959ee228fb69c5cb3518c0ca67d82`**; sibling `.zip.sha256` và `.archive.json` lưu kiểm chứng. ZIP final là bản bàn giao của T01.

Sau khi giải nén ZIP, có thể kiểm tra các vector đã lưu mà không cài package:

```powershell
python -I <thu-muc-giai-nen>/read_alignment.py <thu-muc-giai-nen>
```

Để tính lại vectors từ source, dùng API trong [README](../004-detection-evaluation/README.md), chọn hai thư mục `inputs/source/<dataset-id>` và `inputs/detected/<dataset-id>` trong ZIP hoặc dataset gốc đã tạo. Recorder `verify.py` là record lượt kiểm chứng với paths/logs của lần này, không phải CLI export production và không retry vào proof đã tồn tại. File `initial-verifier.py` giữ script của lượt timeout; ZIP final đã hoàn thiện manifest hash trước khi kiểm tra.

Code/tests/docs/hai CSV nhỏ theo Git; full artifacts/ZIP chỉ có local, cần chia sẻ ZIP thực tế hoặc tái tạo input để thành viên chạy lại. Chưa có receipt/review Đăng. **Tiếp theo PHUC-004-T02:** đếm active/endpoint/assigned/isolate, coverage và số nhóm trên đúng tập người; AMI đến T03.
