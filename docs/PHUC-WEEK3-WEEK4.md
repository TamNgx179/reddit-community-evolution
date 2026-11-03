# Công việc Phúc: review nhãn, graph và coverage

**Bản làm việc ngày 03/11/2026.** Deadline tuần 3: **04/11**. Deadline tuần 4: **11/11**. Phạm vi dựa trên bảng người dùng gửi và [phân công chung](../PHAN-CONG-SNA-8-TUAN.md); tài liệu này không đổi việc của các thành viên khác.

## 1. Hiểu phần của bạn bằng một ví dụ

Hệ thống nói một cộng đồng đã “tan rã”. Bạn cần xem những thành viên đó ở tháng sau xuất hiện ở đâu, nhóm nào có liên hệ với nhóm cũ, và dữ liệu có đủ quan sát không. Không thấy một nhóm kế tiếp chưa chứng minh người thật đã ngừng giao tiếp.

Công việc của bạn gồm ba phần:

1. **Kiểm tra graph:** danh sách người và cạnh có khớp nhau không, có thiếu bằng chứng predecessor/successor hay quan sát không.
2. **Coverage:** trong tất cả chuyển tiếp có thể quan sát, bao nhiêu chuyển tiếp có nhãn đủ điều kiện để đánh giá; phần nào còn unresolved.
3. **Reviewer 1:** bạn thực sự đọc ca và tự chấm nhãn, độ tin tưởng, lý do. Script chỉ giúp nhận gói và kiểm tra định dạng, không chấm thay rồi ghi thành ý kiến của bạn.

Bạn tiếp tục giữ đối chứng detector, Random Forest và HGB. Đợt này không mở thêm detector hay tự sửa nhãn để tăng điểm.

## 2. Bảng việc và trạng thái

Trạng thái “xong công cụ” khác với “đã chạy trên gói dữ liệu thật”. Checkbox để trống nếu chưa có bằng chứng hoàn thành.

| ID | Việc | Đầu ra/điều kiện xong | Trạng thái ngày 03/11 | Hạn |
|---|---|---|---|---|
| P3-01 | Đồng bộ source và đọc phân công mới | Bắt đầu từ `main` 7725b57, nhánh riêng cho Phúc | Đã làm | 03/11 |
| P3-02 | Nhận đúng snapshot và hai ZIP reviewer 1 | Ghi SHA-256, version, terminal month, nguồn và đường dẫn; không nhận key | Chờ Tâm bàn giao ngoài Git | 03/11 |
| P3-03 | Kiểm tra kỹ thuật gói pilot | CRC/path/field checks, 6 ca có payload, phiếu còn trống, bản làm việc riêng | Công cụ đã viết; chưa thử gói Tâm thật | 03/11 |
| P3-04 | Rà 6 ca thử với rubric | Bạn kiểm tra membership, đầy đủ topology/cạnh/observation và ghi thiếu gì | Chờ gói; cần bạn thực hiện | 03–04/11 |
| P3-05 | Chốt hướng dẫn sau pilot | Version rubric và ghi ai đã phê duyệt; không tính pilot vào 60 ca | Chờ kết quả pilot | 04/11 |
| P3-06 | Chấm bộ chính độc lập | 60 ca, nhãn/confidence/rationale thật, ghi exposure; nộp nguyên phiếu | Chưa làm; cần bạn thực hiện | 04/11 |
| P3-07 | Xuất coverage và phân tầng | eligible/unresolved/censored riêng; community–tháng/member–tháng; theo tháng, size, history | Công cụ đã viết; chưa có snapshot thật | 04/11 |
| P3-08 | Kiểm tra graph với snapshot đóng băng | Đúng hash, đúng month, membership phủ endpoint, cỡ nhóm khớp features, đúng mẫu số observation | Công cụ đã viết; chưa có graph thật | 04/11 |
| P3-09 | Bàn giao thiếu bằng chứng và coverage | Anh nhận CSV; Tâm–Thanh nhận danh sách graph/history đáng ngờ, không lộ nhãn cho Đăng | Đang chuẩn bị giao diện, chưa có kết quả thật | 04/11 |
| P4-01 | Hoàn tất review/coverage và sửa thiếu bằng chứng | Giữ phiếu gốc, version gói; mọi sửa nhãn do core quyết định | Chờ các bước tuần 3 | 11/11 |
| P4-02 | Đối chứng HGB khớp nếu phương pháp thay đổi | Cùng đặc trưng/cutoff/mẫu/reference/split/seed/budget, runtime đo thật | Chờ Tâm–Thanh khóa một giả thuyết và cấu hình ngày 05/11 | 05–09/11 |
| P4-03 | Gửi báo cáo tổng hợp cho Anh | Báo cáo nhãn/coverage, graph audit, matched HGB và logs nếu có fit | Chưa làm | 10–11/11 |

## 3. Ai liên quan đến bạn và chờ phần nào?

| Người | Bạn cần nhận | Bạn trả lại | Có cần chờ? |
|---|---|---|---|
| **Tâm** | `pilot-reviewer_1.zip`, `main-reviewer_1.zip`, SHA-256/version, snapshot full-study và 2016, sample/graph manifest, terminal month | Kết quả nhận gói, lỗi graph/thiếu evidence, phiếu reviewer 1 đã khóa | Cần gói để chạy thật; vẫn chuẩn bị code/docs trước |
| **Đăng** | Chỉ thống nhất rubric, schema, thời điểm khóa và quy trình cùng Tâm | Phiếu 1 đã khóa cho điều phối; sau khi cả hai nộp mới so sánh và xử lý bất đồng | Không chờ Đăng chấm mới bắt đầu; không xem nhãn/phiếu của nhau trước khi khóa |
| **Anh** | Xác nhận giao diện các bảng tổng hợp; dùng quy ước size 2, 3–4, 5–20, >20 | `coverage.csv`, `distributions.csv`, `summary.json`, graph audit và pins theo reference | Có thể thống nhất ngay; không cần đợi mô hình mới |
| **Thanh** | Giả thuyết duy nhất, feature schema và các ca graph/history cần xem sau review | Bằng chứng kỹ thuật có nguồn; HGB khớp nếu được yêu cầu | Chỉ chờ khi cần fit đối chứng cho phương pháp mới |
| **Trâm** | Mô hình HGB chuẩn, danh sách đặc trưng và schedule đã khóa nếu cần chạy lại | Đối chứng HGB khớp, runtime; không tự chọn lại model theo final | Dùng output có sẵn nếu input/model/reference không đổi |

Không cần gửi ZIP mới cho Đăng khi chưa có thay đổi đầu vào. Đăng dùng đúng gói reviewer 2 do Tâm phân phối riêng. Không gửi reviewer 1 cho Đăng để chấm cùng một phiếu.

## 4. Đã kiểm tra GitHub được gì?

Ngày 03/11, kiểm tra `main`, hai nhánh bàn giao/reference liên quan, danh sách Release và PR #18/#20:

- `main` mới nhất lúc kiểm tra là `7725b57`; source/docs mới đã cập nhật trên máy.
- Không có GitHub Release để tải ZIP.
- Hướng dẫn ghi gói audit local: `artifacts/diagnostics/midterm2-reference-label-audit-20261031-003`.
- PR #18 ghi các gói ca/private keys/source mappings ở ngoài Git. PR #20 cũng yêu cầu Tâm gửi frozen handoff riêng; báo cáo/CSV thực của Trâm nằm trong `artifacts/`.
- Máy này chưa có snapshot full-study/2016 và gói reviewer mới được mô tả. Không suy ra các gói không tồn tại ở máy Tâm; chỉ chưa được bàn giao tại checkout này.

**Tin nhắn để bạn tự gửi Tâm** (chưa có tin nào được công cụ gửi):

> Tâm ơi, tui đã cập nhật main và đang làm coverage/reviewer 1. Trên GitHub docs ghi bộ ca với snapshot để local nên tui chưa tải được. Ông gửi riêng giúp tui `pilot-reviewer_1.zip`, `main-reviewer_1.zip`, SHA-256/version và snapshot full-study + 2016 có manifest nha. Cho tui đường dẫn sample-run chứa features/labels, các monthly graph run và tháng cuối quan sát của từng reference để tui chạy coverage. Đừng kèm answer key, followup ba tháng hay phiếu của Đăng trong gói reviewer nha.

## 5. Nhận và rà bộ ca

Nguồn rubric là [LABEL_REVIEW](LABEL_REVIEW.md#current-midterm-2-review-packet). Công cụ nhận gói:

```powershell
& .\.venv\Scripts\python.exe scripts/prepare_phuc_review.py --zip "DUONG_DAN/pilot-reviewer_1.zip" --phase pilot --reviewer-id phuc --output artifacts/review/phuc-pilot-20261103-001 --expected-sha256 SHA256_TAM_GUI
```

Các phần `DUONG_DAN`/`SHA256_TAM_GUI` là chỗ điền sau khi Tâm gửi, không phải đường dẫn có sẵn. Output mới, không ghi đè input. Chạy riêng `--phase main` cho gói chính sau khi rubric được chốt.

Output:

- `packet/`: bản gói nguyên nội dung, không sửa phiếu gốc.
- `annotations-working.csv`: bản để **bạn** điền.
- `evidence-checklist.csv`: mỗi ca có ô kiểm tra bằng chứng và ghi thiếu gì.
- `intake.json`: hash và kết quả kiểm tra kỹ thuật, luôn để human annotation pending lúc tạo.

Công cụ kiểm tra số hàng theo phase, CRC, đường dẫn ZIP, một số field/filename có thể lộ key, đọc được JSON/gzip và có evidence cho từng case_id. Nó không chứng minh mọi bằng chứng đều đầy đủ, HTML đã hiển thị tốt hoặc người thật đã nhận/chấm; bạn phải kiểm tra nội dung và link thực tế của gói. Nếu schema gói Tâm khác hợp đồng này, dừng để đối chiếu, không tự sửa gói gốc.

### Mỗi ca, bạn làm lần lượt

1. Xác định nhóm nguồn và hai tháng đang xét.
2. Đọc full membership trong JSON.gz; HTML chỉ preview, không coi 10 token hiển thị là toàn bộ nhóm.
3. Xem mọi successor có thành viên chung, mọi predecessor liên quan và successor khác của các predecessor đó. Không chỉ xem nhóm lớn nhất.
4. Xem cạnh có trọng số, coverage và việc thành viên có record hoạt động hoặc nằm trong mạng reply ở tháng sau.
5. Chọn stable/grow/shrink/merge/split/dissolve/unresolved, độ tin tưởng low/medium/high và lý do theo bằng chứng.
6. Nếu thiếu bằng chứng, ghi thiếu gì và có thể chọn unresolved. Không đoán cho đủ.

Không dùng nhãn máy/ngưỡng/prediction/answer key hoặc followup ba tháng để chấm lượt một bước. Không trao đổi nhãn từng ca với Đăng trước khi cả hai nộp. Sáu pilot để thử rubric, không cộng vào 60 ca chính. Script không tự khẳng định người dùng đã ký attestations hay nộp phiếu.

## 6. Coverage tính như thế nào?

Ví dụ có 10 cộng đồng–tháng với chuyển tiếp quan sát được, 7 có nhãn đủ điều kiện và 3 unresolved: coverage là 7/(7+3)=70%. Hai nhóm ở tháng cuối chưa có tháng sau để quan sát được đếm `censored=2`, không đưa vào mẫu số 10 và không đổi thành dissolve.

Member–tháng dùng trọng số kích thước: tổng số thành viên của các cộng đồng eligible chia tổng số thành viên của eligible + unresolved, đếm riêng theo từng tháng. Một người có thể xuất hiện ở nhiều tháng nên đây không phải số người duy nhất.

Chạy **tách từng reference**. Không ghép full-study với 2016 hoặc nhân số cộng đồng lên ba lần theo seed mô hình.

```powershell
& .\.venv\Scripts\python.exe scripts/run_phuc_coverage.py --sample-run "DUONG_DAN_SAMPLE_RUN" --terminal-month YYYY-MM --output artifacts/diagnostics/phuc-coverage-full-study-001
```

Nguồn phải có `complete.json` ghi `status=complete`, `artifact_hashes` cho `features.csv` và `labels.csv`. Nếu nguồn dùng `manifest.json`, thêm `--manifest-name manifest.json`. Hash chỉ chứng minh khớp bản metadata đã nhận, không tự xác nhận người tạo/độ đúng xã hội. `--terminal-month` phải lấy từ gói đã đóng băng, không đoán để hợp thức hóa dữ liệu thiếu.

### Kiểm tra graph thật kèm coverage

Tâm cung cấp JSON index có mọi feature month, mỗi giá trị là thư mục chuẩn bị tháng đã seal bằng `complete.json`. Đường dẫn tương đối được tính từ thư mục chứa index. Ví dụ minh họa:

```json
{"2016-01": "month-2016-01/attempt-001", "2016-02": "month-2016-02/attempt-001"}
```

Thêm `--graph-index DUONG_DAN_GRAPH_INDEX.json`. Công cụ yêu cầu hash monthly manifest đúng `input_month_manifests` của sample-run, kiểm tra membership/endpoint, cỡ nhóm khớp feature, cạnh trùng và mẫu số quan sát. Nếu không có graph index, chỉ xuất coverage, trạng thái graph là `not_checked`; không nhận là đã kiểm tra graph.

Coverage graph/user và label coverage là hai đại lượng khác nhau. Tỷ lệ user nằm trong graph dùng số reply endpoints trên observed users. Tỷ lệ tác giả có reply edge dùng **edge-covered active authors / active authors**; parent-only endpoints không được đưa vào tử số tác giả hoạt động.

### Giao diện output cho Anh và Đăng

| File | Nội dung |
|---|---|
| `coverage.csv` | `reference_id`, `label_reference_id`, axis/stratum, observed/eligible/unresolved/censored, coverage, trọng số member–tháng; month là **feature_month** |
| `distributions.csv` | So sánh eligible/unresolved bằng n, mean, q10, median, q90 theo toàn bộ và size; không kết luận từ một trung vị |
| `graph-audit.csv` | Chỉ có khi đã đưa đủ monthly graph; count và kết quả kiểm tra từng tháng |
| `summary.json` | Reference, tháng cuối, tổng, graph status, thiếu evidence, human review pending |
| `input-pins.json` | Đường dẫn và SHA-256 các input thực sự dùng |
| `manifest.json` | Inventory/hash output, timestamp và source-manifest pin |
| `REPORT.md` | Báo cáo kỹ thuật ngắn bằng tiếng Anh |

Không xuất phiếu reviewer vào những bảng tổng hợp này. Việc tính agreement do Đăng phối hợp Anh sau khi khóa hai phiếu. Giữ unresolved là một nhãn riêng trong confusion của review. Mọi sửa reference/nhãn do core quản lý và buộc đối chiếu lại downstream.

## 7. Việc làm ngay hôm nay theo thứ tự

1. Gửi yêu cầu gói cho Tâm như mẫu trên. Không chờ Đăng làm xong mới bắt đầu.
2. Khi nhận ZIP pilot, chạy intake, mở HTML và rà 6 ca bằng checklist. Chưa mở gói chính để chấm khi rubric chưa chốt.
3. Thống nhất rubric/version với điều phối dựa trên pilot; sau đó mỗi người chấm bộ chính riêng.
4. Song song, chạy coverage riêng full-study và 2016 từ snapshot đã đóng băng. Chạy graph audit khi nhận đủ monthly manifests.
5. Nộp phiếu 1 nguyên bản đã khóa cho điều phối. Gửi Anh output coverage, Tâm–Thanh danh sách thiếu/đáng ngờ. Không gửi các quyết định chưa khóa cho Đăng.
6. Sau 04/11 mới phối hợp đối chứng HGB theo giả thuyết đã chọn; dùng output sẵn nếu input/model/reference chưa đổi.

## 8. Kiểm chứng phần công cụ

Đã chạy ngày 03/11: **25/25 kiểm thử liên quan pass**, gồm 14 kiểm thử mới và 11 hồi quy diagnostics có sẵn. Hai lệnh CLI cũng đã chạy thành công trên fixture tổng hợp nhỏ, có manifest và output giữ tại `artifacts/verification/phuc-week3-20261103-001/`. Coverage fixture có 4 chuyển tiếp quan sát, 2 eligible, 2 unresolved và 2 censored riêng; reviewer fixture vẫn có 0 nhãn được chấm. Đây là kiểm chứng phần mềm, không phải số liệu Reddit mới hoặc review người thật. Chưa chạy toàn bộ test suite.

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_coverage_audit tests.integration.test_coverage_audit tests.unit.test_review_intake tests.unit.test_diagnostics -v
```

Test dùng mạng/bảng/ZIP **tổng hợp nhỏ**, không phải review người thật hoặc kết quả mới của Reddit. Các kết quả thật trên máy chỉ được thêm vào trạng thái sau khi có đúng gói và chạy thành công. Không tự đánh dấu toàn bộ công việc tuần 3 là hoàn thành từ việc code/test pass.
