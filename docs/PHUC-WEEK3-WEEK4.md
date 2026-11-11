# Công việc Phúc: review nhãn, graph và coverage

**Bản làm việc ngày 03/11/2026.** Deadline tuần 3: **04/11**. Deadline tuần 4: **11/11**. Phạm vi dựa trên bảng người dùng gửi và [phân công chung](../PHAN-CONG-SNA-8-TUAN.md); tài liệu này không đổi việc của các thành viên khác.

**Cập nhật 04/11:** đã kiểm tra `main` tại `3016220` và PR #21. Gói reviewer 2 có trên Release; chưa thấy phản hồi mới trên PR về điều kiện quan sát hoặc xác nhận thống nhất hướng dẫn. Bản bàn giao local nằm ở `artifacts/handoff/phuc-pilot-20261104-001/README.md`, kèm trạng thái và hash nguồn. Không tạo thêm ZIP dữ liệu.

**Quyết định chủ động của Phúc ngày 04/11:** chọn v1.1 làm bản hướng dẫn làm việc và đề nghị Đăng áp dụng cùng bản. Mở [cách chấm từng bước và tin nhắn giao việc cho Đăng](PHUC-DANG-CACH-CHAM.md). Phúc đã chọn hướng dẫn; xác nhận của Đăng, phiên bản chung sau pilot và thời điểm khóa vẫn ghi theo thực tế.

**Đã triển khai chuẩn bị bộ chính ngày 04/11:** workspace `artifacts/review/phuc-main-20261104-001/` có đủ 60 ca và phiếu làm việc. Intake kỹ thuật thành công, kiểm tra nhất quán đạt 60/60 ca và 181 link HTML hợp lệ. Mở `README.md` trong workspace để bắt đầu tra file. Báo cáo và bảng bằng chứng nằm ở `artifacts/review/phuc-main-audit-20261104-001/`. Phiếu chấm hiện ghi nhận 0/60 ca, xác nhận hướng dẫn chung và ngày khóa còn pending.

**Đã hoàn thành bản nhận xét AI cho 60 ca ngày 04/11:** thư mục `artifacts/review/phuc-main-assisted-20261104-001/` có `README.md` tiếng Việt, `automated-main-v1.1.csv`, `assessment.json`, bằng chứng đã đọc và kết quả kiểm chứng. Mỗi ca có nhãn đề xuất, confidence, rationale và ambiguity với `reviewer_type=automated`. CSV/JSON khớp 60 mã ca duy nhất; hash bằng chứng và phiếu gốc đã được kiểm tra. Phúc rà bản này khi quyết định phần chấm của mình. Đầu vào để đối chiếu hai reviewer và bản khóa chung còn pending.

## Đọc trước: “rubric” là gì?

**Rubric là bộ quy tắc chấm**, giống hướng dẫn chấm bài của thầy. Trong phần này, Phúc và Đăng nhìn bằng chứng của một nhóm qua hai tháng rồi chọn cách mô tả sự thay đổi. Hai bạn cần hiểu cùng một quy tắc để kết quả có thể so sánh được.

| Từ trong phiếu | Nói dễ hiểu | Điều cần xem |
|---|---|---|
| `stable` | Nhóm tiếp tục, quy mô giữ nguyên | Có bằng chứng đây là nhóm tiếp nối một–một của nhóm cũ. |
| `grow` | Nhóm tiếp tục và lớn lên | Xác định được nhóm kế tiếp của nhóm cũ rồi mới so số người. |
| `shrink` | Nhóm tiếp tục và thu nhỏ | Xác định được nhóm kế tiếp của nhóm cũ rồi mới so số người. |
| `merge` | Nhiều nhóm hợp thành một nhóm | Nhiều nhóm cũ có đóng góp thành viên rõ vào nhóm mới. |
| `split` | Một nhóm tách thành nhiều nhánh | Có ít nhất hai nhóm kế tiếp với bằng chứng tiếp nối về thành viên và tương tác. |
| `dissolve` | Không còn tiếp nối trong mạng quan sát | Điều kiện dữ liệu/phạm vi/bộ lọc phải được xác nhận; không suy thành nhóm ngoài đời biến mất. |
| `unresolved` | Chưa đủ bằng chứng để kết luận | Ghi cụ thể thiếu gì hoặc đang có những cách giải thích cạnh tranh nào. |

Ví dụ minh họa quy tắc, không phải đáp án của ca pilot: không thấy thành viên tháng sau mà chưa biết dữ liệu có đủ không thì chọn `unresolved`. Thấy nhóm đích rất lớn cũng chưa đủ để gọi `grow`: phải biết đó là nhóm tiếp nối của nhóm cũ hay nơi nhiều nhóm nhập vào.

**v1.1** là số phiên bản của hướng dẫn Tâm đề xuất. **Chốt/khóa rubric** nghĩa là ghi lại bản mà hai reviewer thực sự thống nhất dùng, cùng thời điểm và người xác nhận. Việc khóa giúp tránh mỗi người hiểu một kiểu hoặc đổi cách chấm giữa chừng mà không lưu lại.

**Pilot** là 6 ca thử để luyện cách đọc và phát hiện chỗ hướng dẫn chưa rõ. **Bộ chính** là 60 ca chấm theo phiên bản đã thống nhất; 6 ca thử không cộng vào đó. Mỗi ca ghi nhãn, mức tin tưởng (`low`/`medium`/`high`) và lý do dựa trên bằng chứng. Phần này đánh giá cách diễn giải chuyển tiếp có hợp lý hay không; chưa phải kết quả mô hình dự đoán sự kiện tương lai.

Đọc [hướng dẫn đề xuất v1.1](REVIEW-RUBRIC-V1.1.md) để xem đầy đủ. Bảng trên chỉ giải thích thuật ngữ, không thêm ngưỡng hoặc thay đổi quy tắc. Phúc hiện đã dùng gợi ý AI và cần khai đúng điều đó; sự đồng ý của Đăng và các thời điểm khóa vẫn phải ghi theo thực tế.

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
| P3-02 | Nhận đúng snapshot và hai ZIP reviewer 1 | Ghi SHA-256, version, terminal month, nguồn và đường dẫn; không nhận key | Đã tải hai ZIP reviewer 1, hash khớp Release; snapshot có sẵn nhưng chưa mở trước khi khóa phiếu | 03/11 |
| P3-03 | Kiểm tra kỹ thuật gói pilot | CRC/path/field checks, 6 ca có payload, phiếu còn trống, bản làm việc riêng | Đã kiểm tra gói thật: 6 payload, 19 link nội bộ, phiếu gốc và bản làm việc trống | 03/11 |
| P3-04 | Rà 6 ca thử với rubric | Bạn kiểm tra membership, đầy đủ topology/cạnh/observation và ghi thiếu gì | Đã đối chiếu kỹ thuật toàn bộ 6 ca và có bảng đọc riêng; phiếu chấm người thật vẫn trống | 03–04/11 |
| P3-05 | Chốt hướng dẫn sau pilot | Version rubric và ghi ai đã phê duyệt; không tính pilot vào 60 ca | Phúc đã chọn v1.1 làm bản làm việc, có hướng dẫn từng bước để Đăng dùng; xác nhận của Đăng và ngày khóa chung chưa được ghi nhận | 04/11 |
| P3-06A | Nhận xét AI bổ trợ theo bản Phúc chọn | 60 đề xuất có bằng chứng, ambiguity, provenance và hash nguồn | Đã hoàn thành 60/60, CSV/JSON khớp, có bản đọc tiếng Việt; lưu local riêng | 04/11 |
| P3-06 | Chấm bộ chính độc lập | 60 ca, nhãn/confidence/rationale thật, ghi exposure; nộp nguyên phiếu | Có bản bổ trợ AI 60/60 để Phúc rà; phiếu người thật 0/60, đầu vào đối chiếu Đăng và khóa chung còn pending | 04/11 |
| P3-07 | Xuất coverage và phân tầng | eligible/unresolved/censored riêng; community–tháng/member–tháng; theo tháng, size, history | Hoàn thành full-study ngày 11/11. Community-month 64,78%; member-month 79,31%; output có month/size/history strata | 11/11 |
| P3-08 | Kiểm tra graph với snapshot đóng băng | Đúng hash, đúng month, membership phủ endpoint, cỡ nhóm khớp features, đúng mẫu số observation | Hoàn thành 45/45 tháng. SHA ZIP và 622 checksum nội bộ khớp; graph audit `verified` | 11/11 |
| P3-09 | Bàn giao thiếu bằng chứng và coverage | Anh nhận CSV; Tâm–Thanh nhận danh sách graph/history đáng ngờ, không lộ nhãn cho Đăng | Báo cáo Week 4 và artifact coverage đã sẵn sàng; không có graph mismatch được audit ghi nhận | 11/11 |
| P4-01 | Hoàn tất review/coverage và sửa thiếu bằng chứng | Giữ phiếu gốc, version gói; mọi sửa nhãn do core quyết định | Hoàn thành technical agreement/adjudication và coverage graph-verified. Giới hạn provenance AI-assisted được giữ nguyên | 11/11 |
| P4-02 | Đối chứng HGB khớp nếu phương pháp thay đổi | Cùng đặc trưng/cutoff/mẫu/reference/split/seed/budget, runtime đo thật | Chưa chạy vì chưa có cấu hình/HGB hypothesis do Tâm–Thanh bàn giao; không tự thay run khác | 05–09/11 |
| P4-03 | Gửi báo cáo tổng hợp cho Anh | Báo cáo nhãn/coverage, graph audit, matched HGB và logs nếu có fit | Báo cáo tại `docs/PHUC-WEEK4-RESULTS.md` đã sẵn sàng để Anh ghép; nêu rõ HGB chưa có kết quả | 11/11 |

## 3. Ai liên quan đến bạn và chờ phần nào?

| Người | Bạn cần nhận | Bạn trả lại | Có cần chờ? |
|---|---|---|---|
| **Tâm** | Hai ZIP reviewer 1 và checksum đã có ở Release; snapshot chứa nhãn máy mở sau khóa phiếu | Kết quả nhận gói, lỗi graph/thiếu evidence, phiếu reviewer 1 đã khóa | Bắt đầu pilot ngay; gói reviewer 2 của Đăng cũng đã có trên Release |
| **Đăng** | Chỉ thống nhất rubric, schema, thời điểm khóa và quy trình cùng Tâm | Phiếu 1 đã khóa cho điều phối; sau khi cả hai nộp mới so sánh và xử lý bất đồng | Không chờ Đăng chấm mới bắt đầu; không xem nhãn/phiếu của nhau trước khi khóa |
| **Anh** | Xác nhận giao diện các bảng tổng hợp; dùng quy ước size 2, 3–4, 5–20, >20 | `coverage.csv`, `distributions.csv`, `summary.json`, graph audit và pins theo reference | Có thể thống nhất ngay; không cần đợi mô hình mới |
| **Thanh** | Giả thuyết duy nhất, feature schema và các ca graph/history cần xem sau review | Bằng chứng kỹ thuật có nguồn; HGB khớp nếu được yêu cầu | Chỉ chờ khi cần fit đối chứng cho phương pháp mới |
| **Trâm** | Mô hình HGB chuẩn, danh sách đặc trưng và schedule đã khóa nếu cần chạy lại | Đối chứng HGB khớp, runtime; không tự chọn lại model theo final | Dùng output có sẵn nếu input/model/reference không đổi |

Không cần gửi ZIP mới cho Đăng khi chưa có thay đổi đầu vào. Đăng tải đúng gói reviewer 2 từ Release của Tâm. Không gửi reviewer 1 hoặc bản nhãn gợi ý của Phúc cho Đăng để chấm cùng một phiếu.

## 4. Đã kiểm tra GitHub được gì?

Ngày 03/11 đã nhận được [Draft Release của Tâm](https://github.com/TamNgx179/reddit-community-evolution/releases), tên `Midterm 2 frozen team handoff - 3 November 2026`, tag hiển thị `midterm2-review-handoff-20261103`. Mở trang Releases rồi chọn đúng tên này khi đã đăng nhập tài khoản cộng tác viên. Link draft dạng `untagged-...` đã thay đổi khi cập nhật asset; các lệnh bên dưới dùng tag do GitHub CLI nhận diện. Đây là gói bàn giao cho cộng tác viên, giữ nguyên draft; không tự publish.

| Asset | Trạng thái tại máy Phúc |
|---|---|
| `pilot-reviewer_1.zip` | Đã tải 41.685.542 byte; SHA-256 khớp checksum Release; đã chuẩn bị workspace pilot |
| `main-reviewer_1.zip` | Đã tải 515.012.951 byte, SHA-256 khớp; đã mở 60 payload để chuẩn bị và kiểm tra kỹ thuật ngày 04/11; phiếu chấm 0/60 |
| `RELEASE_SHA256SUMS.txt` | Đã tải, dùng đối chiếu cả hai ZIP |
| `pilot-reviewer_2.zip` | Đã có trên Release, 41.685.542 byte; Phúc không tải/mở gói của Đăng |
| `main-reviewer_2.zip` | Đã có trên Release, 515.012.951 byte; Đăng mở sau khi thống nhất rubric |
| `REVIEWER_2_SHA256SUMS.txt` | Đã tải riêng file checksum để cập nhật hướng dẫn; không chứa phiếu chấm |
| `Phuc_Coverage_Snapshots_AFTER_REVIEW_LOCK_20261103.zip` | Có trên Release, 1.491.566.746 byte; chưa tải/mở vì chứa nhãn máy |

Hai ZIP reviewer 1 có sẵn trong `artifacts/handoff/midterm2-release-20261103/`. SHA-256 pilot: `fae601660eee8c37c35a935717417fc2273a25ad86432123cb403c3b315158aa`; main: `71839e3145a74b56fc84f1f16207993034c7e5474ddf084b7c44dff8f5cbd8dc`. So checksum chỉ xác nhận khớp asset được bàn giao, không tự chứng nhận nội dung đúng về mặt xã hội.

Cập nhật đã kiểm tra ngày 03/11: **Release có đủ hai ZIP reviewer 2 và checksum riêng**. Đăng không cần chờ được gửi ZIP qua chat. Việc asset xuất hiện và checksum được tải không có nghĩa Đăng đã nhận, mở hoặc chấm xong. Không thay gói reviewer 2 bằng reviewer 1, không gửi bản làm việc của Phúc cho Đăng.

**Tin nhắn để bạn tự gửi Đăng** (chưa có tin nào được công cụ gửi):

> Ông ơi, Tâm đã up đủ gói của ông lên Release rồi nha: https://github.com/TamNgx179/reddit-community-evolution/releases . Ông đăng nhập GitHub, mở bản “Midterm 2 frozen team handoff - 3 November 2026”, tải `pilot-reviewer_2.zip` với `REVIEWER_2_SHA256SUMS.txt` trước nha. Mình đọc 6 ca thử theo rubric đề xuất v1.1 rồi thống nhất cách hiểu chung; sau đó mới chấm `main-reviewer_2.zip` gồm 60 ca. Tui đã dùng gợi ý AI và sẽ khai rõ. Hai đứa không gửi nhãn từng ca cho nhau trước khi khóa phiếu; nộp riêng cho Tâm xong mới so kết quả. Không tải/mở file coverage có nhãn máy trước khi khóa phiếu nha.

**Đăng tải pilot bằng PowerShell** (nếu đã cài và đăng nhập `gh`; chạy từ repo, không chạy lại lên thư mục đã dùng):

```powershell
gh release download midterm2-review-handoff-20261103 --repo TamNgx179/reddit-community-evolution --pattern pilot-reviewer_2.zip --pattern REVIEWER_2_SHA256SUMS.txt --dir artifacts/handoff/dang-reviewer2-20261103
Get-FileHash -Algorithm SHA256 artifacts/handoff/dang-reviewer2-20261103/pilot-reviewer_2.zip
```

SHA-256 pilot reviewer 2 theo checksum điều phối: `cdfb3d043fa1fc72b5ee616c6e788a54dec6253d766e5b1d2253de60ca6126f0`. Chỉ giải nén nếu kết quả khớp. Máy Phúc chỉ đọc file checksum, chưa tự xác minh byte của ZIP reviewer 2.

```powershell
Expand-Archive -LiteralPath artifacts/handoff/dang-reviewer2-20261103/pilot-reviewer_2.zip -DestinationPath artifacts/review/dang-pilot-20261103-001
```

Mở `index.html` của phase pilot trong thư mục vừa giải nén. Giữ `reviewer_2.csv` gốc trống, sao chép thành phiếu làm việc riêng để ghi `label`, `confidence`, `rationale`. `scripts/prepare_phuc_review.py` chỉ nhận reviewer 1; Đăng không dùng script đó cho ZIP reviewer 2.

Sau khi pilot và rubric đã thống nhất, tải gói chính bằng lệnh riêng:

```powershell
gh release download midterm2-review-handoff-20261103 --repo TamNgx179/reddit-community-evolution --pattern main-reviewer_2.zip --dir artifacts/handoff/dang-reviewer2-20261103
Get-FileHash -Algorithm SHA256 artifacts/handoff/dang-reviewer2-20261103/main-reviewer_2.zip
```

SHA-256 main reviewer 2 theo checksum điều phối: `e5dc7c638775ed103e6d2913110e01ea8cee3778e030f35456f20e98c7e93e1e`. Đối chiếu với file checksum tải cùng đợt. Giữ cả hai worksheet gốc và ghi exposure/thời điểm nộp thực tế; không tự ghi đã nộp hoặc đã khóa chỉ vì file tải xong.

## 5. Bắt đầu pilot ngay trên máy này

**Hướng dẫn hiện tại:** [rubric đề xuất v1.1 theo tin nhắn Tâm](REVIEW-RUBRIC-V1.1.md). Dùng bản này để rà pilot, ghi rõ Phúc đã xem gợi ý AI. `dissolve` cần xác nhận điều kiện dữ liệu hai tháng/phạm vi/bộ lọc; nếu thiếu dữ liệu hoặc mức quan sát chưa rõ, dùng unresolved. Không tự coi file đọc được và overlap khớp là đã chứng minh dữ liệu tháng sau đầy đủ. Sau khi hai reviewer thống nhất mới ghi ngày khóa và mở bộ chính để chấm. Các bản nháp AI trước v1.1 được giữ nguyên, không phải phiếu người thật.

Đã rà lại bản AI bổ trợ của 6 ca theo v1.1, lưu riêng tại `artifacts/review/phuc-pilot-v1.1-20261103-001/`. Có `RA-PILOT-V1.1.md`, `automated-pilot-v1.1.csv`, metadata và revision log. Những quyết định phụ thuộc xác nhận phạm vi quan sát còn được giữ unresolved khi chưa có nguồn xác nhận trong gói reviewer. Đây không phải đổi nhãn máy, chốt rubric hoặc khóa phiếu của Phúc. Bản nháp cũ và mọi phiếu người thật được so hash, không thay đổi. Không công bố nhãn từng ca AI lên Git hoặc gửi cho Đăng trước lượt chấm độc lập.

Phúc tiếp tục nhờ AI lựa chọn và giải thích một ca pilot. Ghi nhận riêng tại `artifacts/review/phuc-pilot-decisions-20261103-001/`, gồm phần giải thích và provenance; vẫn là **lựa chọn AI**, không phải nhãn do Phúc tự chấm. Không cộng lặp vào sáu ca nháp đã có, không điền thay vào phiếu người thật. Số quyết định người thật được ghi nhận hiện vẫn là 0.

Đã [gửi Tâm đề xuất v1.1 và hỏi nguồn metadata không lộ nhãn xác nhận điều kiện quan sát](https://github.com/TamNgx179/reddit-community-evolution/pull/21#issuecomment-6604710346). Khi kiểm tra đợt này chưa thấy phản hồi trên PR. Release vẫn chỉ mô tả cơ chế bàn giao và topology; chưa có xác nhận riêng được tìm thấy về phạm vi/bộ lọc đủ dùng cho kết luận không quan sát ở từng cặp tháng. Đây là câu hỏi về đầu vào, không phải xin Tâm quyết định hộ từng ca.

- Mở `artifacts/review/phuc-pilot-20261103-001/packet/pilot/index.html`.
- Bạn điền `artifacts/review/phuc-pilot-20261103-001/annotations-working.csv`.
- Ghi thiếu bằng chứng trong `evidence-checklist.csv` cùng thư mục.
- `packet/pilot/reviewer_1.csv` là bản gốc trống, giữ nguyên.
- Sáu JSON.gz đã đọc được, 19 link HTML nội bộ hợp lệ, kiểm tra metadata completeness/observation đã chạy. Đây là intake kỹ thuật, chưa phải bạn đã đọc/chấm đủ 6 ca hay đã đồng ý rubric.
- Không mở main để chấm trước khi rubric chốt. Không mở snapshot chứa nhãn máy hoặc followup trước khi khóa lượt chấm độc lập.

### Bảng đọc pilot đã chuẩn bị

Mở `artifacts/review/phuc-pilot-audit-20261103-001/PILOT-READING-GUIDE.md` để xem từng ca bằng tiếng Việt. Bảng đọc nêu kích thước nhóm, thành viên chung, các successor liên quan, tỷ trọng thành viên và hai loại quan sát. Không có nhãn sự kiện gợi ý, không chứa đáp án máy và không điền thay reviewer. Nếu sử dụng trợ giúp AI/công cụ, ghi đúng trong exposure/provenance.

Đã đối chiếu toàn bộ membership của các nhóm được cung cấp, mọi overlap giữa những nhóm đó, tính hợp lệ/cạnh trùng và cờ quan sát focal members: **6/6 ca nhất quán nội bộ, không có lỗi kiểm tra**. Đây là kiểm tra trên gói thực nhận, không phải tái dựng toàn bộ nguồn raw hoặc chứng minh mọi cạnh đều được xuất đủ. Global completeness vẫn được ghi là declaration của người tạo gói. Có ca thiếu quan sát thành viên ở tháng sau và có ca gồm hàng trăm nghìn cạnh; đây là vấn đề cần cân nhắc/chốt cách đọc trong pilot, không tự động là lỗi file hoặc nhãn dissolve.

Output local gồm `technical-evidence.csv`, `focal-successors.csv`, `summary.json`, `input-pins.json`, `REPORT.md` và hai script tái lập trong thư mục audit trên. Giữ output riêng, không công bố evidence từng ca lên Git và không cộng số cạnh lặp giữa các ca thành số cạnh duy nhất. Phiếu gốc, phiếu làm việc, checklist và intake metadata đã được so hash trước/sau và không đổi. Chưa có reviewer submission, approval rubric, agreement hay nhãn người thật nào được tạo từ kiểm tra này.

### Lệnh nhận lại ở một output mới khi cần

Nguồn rubric là [LABEL_REVIEW](LABEL_REVIEW.md#current-midterm-2-review-packet). Công cụ nhận gói:

```powershell
& .\.venv\Scripts\python.exe scripts/prepare_phuc_review.py --zip artifacts/handoff/midterm2-release-20261103/pilot-reviewer_1.zip --phase pilot --reviewer-id phuc --output artifacts/review/phuc-pilot-20261103-002 --expected-sha256 fae601660eee8c37c35a935717417fc2273a25ad86432123cb403c3b315158aa
```

Workspace pilot `...-001` đã có sẵn. Ví dụ trên dùng output mới `...-002`. Công cụ dùng giới hạn giải nén mỗi ca 128 MiB vì ca pilot thật lớn nhất 93.781.624 byte; kiểm thử tràn đã pass. Với bộ chính, `--phase main` chuẩn bị workspace kỹ thuật 60 ca. Phúc đã chạy bước này ngày 04/11 theo bản v1.1 đã chọn. Phiên bản dùng để chấm chính thức và thời điểm thống nhất sau pilot được ghi theo thực tế.

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

Chạy **tách từng reference**. Không ghép full-study với 2016 hoặc nhân số cộng đồng lên ba lần theo seed mô hình. **Thứ tự mới theo gói Release: Phúc chỉ mở snapshot coverage sau khi khóa phiếu chấm độc lập.** Nếu cần coverage song song, Tâm/Anh hoặc người không tham gia chấm nhận snapshot để chạy. Không coi việc tải được file là đã được mở nhãn trước review.

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

1. Gửi Đăng thông tin reviewer 2 như mẫu trên. Không chờ Đăng làm xong mới bắt đầu.
2. Mở workspace pilot đã chuẩn bị, rà 6 ca bằng checklist. Chưa mở gói chính để chấm khi rubric chưa chốt.
3. Thống nhất rubric/version với điều phối dựa trên pilot; sau đó mỗi người chấm bộ chính riêng.
4. Sau khi khóa phiếu, mở snapshot coverage và chạy riêng full-study/2016 với graph audit. Nếu chạy song song, giao người không chấm độc lập thực hiện để không lộ nhãn máy.
5. Nộp phiếu 1 nguyên bản đã khóa cho điều phối. Gửi Anh output coverage, Tâm–Thanh danh sách thiếu/đáng ngờ. Không gửi các quyết định chưa khóa cho Đăng.
6. Sau 04/11 mới phối hợp đối chứng HGB theo giả thuyết đã chọn; dùng output sẵn nếu input/model/reference chưa đổi.

## 8. Kiểm chứng phần công cụ

Đã chạy cập nhật ngày 03/11: **27/27 kiểm thử liên quan pass**, thêm hai kiểm thử về payload lớn hơn 64 MiB và chặn vượt giới hạn. Hai lệnh CLI trước đó cũng chạy trên fixture tổng hợp nhỏ tại `artifacts/verification/phuc-week3-20261103-001/`. Sau khi nhận Release, intake pilot thật chạy thành công với 6 ca và phiếu trống; kiểm tra riêng xác nhận 19 link, đầy đủ case_id và hàng observation của focal members. Log/hash/inventory lưu tại `artifacts/verification/phuc-release-20261103-001/`. Không có ca nào được tự động gán nhãn người thật; chưa chạy lại coverage thật hoặc toàn bộ test suite.

Ngày 03/11 đã audit sáu ca pilot tại `artifacts/review/phuc-pilot-audit-20261103-001/`. Ngày 04/11, lệnh CLI nhận bộ chính chạy thành công và audit 60 ca tại `artifacts/review/phuc-main-audit-20261104-001/` đạt 60/60 nhất quán nội bộ. Kiểm tra HTML xác nhận 181 link hợp lệ. Phiếu làm việc giữ trạng thái trống 60 dòng. Các kết quả này ghi nhận chuẩn bị kỹ thuật; lượt chấm người thật và xử lý bất đồng vẫn pending. Coverage thật cần thực hiện ở giai đoạn mở snapshot sau khóa phiếu. Thay đổi được gom theo đợt.

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_coverage_audit tests.integration.test_coverage_audit tests.unit.test_review_intake tests.unit.test_diagnostics -v
```

Test dùng mạng/bảng/ZIP **tổng hợp nhỏ**, không phải review người thật hoặc kết quả mới của Reddit. Các kết quả thật trên máy chỉ được thêm vào trạng thái sau khi có đúng gói và chạy thành công. Không tự đánh dấu toàn bộ công việc tuần 3 là hoàn thành từ việc code/test pass.
