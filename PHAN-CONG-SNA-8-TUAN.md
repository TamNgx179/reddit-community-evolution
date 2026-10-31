# Phân công SNA: từ Midterm 1 đến Midterm 2 và cuối kỳ

**Đề tài:** How Online Communities Change Over Time. **Cập nhật:** 29/10/2026.

**Midterm 2 dự kiến: 12/11/2026**, theo thời hạn hai tuần nhóm cung cấp. Chốt nội dung và kết quả trước 10/11, nghiệm thu bản nộp và demo ngày 11/11. Đây là lịch làm việc nội bộ, điều chỉnh nếu lịch chính thức thay đổi. Mốc cuối kỳ nội bộ vẫn là 09/12.

Tâm–Thanh giữ core. Phúc–Đăng phụ trách kiểm chứng graph/nhãn và coverage. Trâm–Anh phụ trách đối chứng, phân tích lỗi và tổng hợp bằng chứng. Mỗi người có việc và đầu ra riêng, mỗi cặp chịu trách nhiệm một gói bàn giao chung. Kế hoạch này thay thế các lịch tuần 3–8 và cập nhật 28/10 trước đây.

## 1. Mục tiêu Midterm 2

Đi từ **kiểm tra nhãn → phạm vi áp dụng → phân tích lỗi → một cải tiến có lý do → ablation khớp cấu hình**. Không coi thêm mô hình phức tạp hoặc tăng điểm trên một kỳ đã xem là mục tiêu độc lập.

| Góp ý của giảng viên | Việc cần hoàn thành | Bằng chứng để nghiệm thu |
|---|---|---|
| Nhãn phụ thuộc detector và tracker | Hai người kiểm tra độc lập các ca dissolve, unresolved và ca grow/merge khó. Phân biệt mất quan sát với mất liên tục cấu trúc | Phiếu thật có lý do, mức tự tin, độ đồng thuận và biên bản xử lý bất đồng |
| Unresolved bị loại nhiều | Tính coverage đúng mẫu số, tách censored. So sánh phần được dự báo với phần bị loại | Bảng theo tháng/cohort, phân tầng kích thước và lịch sử, coverage theo community–tháng và member–tháng |
| Proposed chưa hơn HGB nhất quán | Phân tích theo lớp/tháng, các ca proposed đúng–HGB sai và ngược lại, đặc biệt grow/merge → dissolve | Dự báo ghép đúng khóa, bảng bốn nhóm đúng/sai, ca minh họa và thuộc tính tại t |
| Cần chọn cải tiến từ nguyên nhân lỗi | Chọn tối đa một giả thuyết chính sau khi có ba gói chẩn đoán trên | Lý do chọn, protocol khóa trước fit, đối chứng cùng đặc trưng và ablation chỉ đổi thành phần mục tiêu |

Mức hoàn thành được xác định bằng đầu ra kiểm tra được và cách giải thích kết quả, không bằng cam kết proposed phải thắng mọi baseline. Kết luận vẫn bám kết quả thật.

## 2. Trạng thái đã kiểm tra trước khi lập kế hoạch

- Lần tái lập 2016 đã hoàn tất đủ `prepare → forecast → research → hetco`. 13 tests HeTCo pass, 48 điểm được tính lại từ prediction CSV. Không còn job dở của lần chạy này.
- HeTCo V4 trên kỳ chính 10–12/2016 đạt 0,3468 so với LR 0,3250. V4 thắng 2/3 seed và 3/6 tháng rolling, CI rolling của chênh lệch là [−0,0392, 0,1025]. Mean pooling đạt 0,3816 và có độ lệch chuẩn giữa seed 0,0044, so với 0,0365 của attention. Đây là kết quả chẩn đoán, chưa phải căn cứ đổi primary sau khi nhìn điểm.
- Năm 2016 và các cohort 2018 đã xuất hiện trong nghiên cứu trước. Không ghi chúng là kỳ chưa từng xem. Bảng 2015, 2016 và nghiên cứu ba cohort được báo riêng theo reference và protocol.
- Audit nghiên cứu gốc: 7.490/11.562 chuyển tiếp có nhãn đủ điều kiện, tương ứng coverage community–tháng 64,78%. Có 4.072 unresolved và 183 cộng đồng cuối kỳ censored được đếm riêng. Coverage member–tháng là 79,31%, không phải tỷ lệ người dùng duy nhất.
- Trên final gốc: 1.269/1.832 chuyển tiếp được đánh giá, 563 unresolved, 183 censored riêng. So proposed LR dynamic với HGB dynamic: 29 ca chỉ proposed đúng, 35 ca chỉ HGB đúng, 86 ca cả hai sai và 1.119 ca cả hai đúng trên 1.269 ca mỗi seed. Ba seed cho cùng các nhóm này, không đếm thành 3.807 ca độc lập. Các số đếm đúng/sai không thay thế Macro-F1.
- Trung vị kích thước của cả phần được đánh giá và phần unresolved đều bằng 2. Cờ `history_missing` xuất hiện trên hơn 90% mẫu đủ điều kiện của nghiên cứu gốc. Cờ này nói về predecessor/lineage, không đồng nghĩa lịch sử hoạt động của thành viên trong D bị thiếu. Cần phân tầng nhóm nhỏ và kiểm tra cách duy trì lineage trước khi kết luận tracker sai hoặc thay cách dùng lịch sử.

Nguồn kết quả và phạm vi so sánh: [RESULTS](docs/RESULTS.md). Phương pháp: [METHODS](docs/METHODS.md). Lệnh chạy: [RUNBOOK](docs/RUNBOOK.md). Quy trình đánh giá nhãn: [LABEL_REVIEW](docs/LABEL_REVIEW.md).

**Dọn phần còn dở:** giữ artifact, prediction, notebook và kết quả bất lợi để truy vết. V3 ensemble đã bỏ khỏi code, không cần xóa lại. V1/V2 và hình pilot được giữ làm bằng chứng lịch sử, không chạy lại mặc định. Chỉ gọi các model nằm trong allowlist của protocol mới. Không xóa dữ liệu hay chạy lại raw/Leiden chỉ để đổi tên hoặc lập phân công. Hợp nhất lịch cũ vào kế hoạch hiện tại thay vì nối thêm nhiều bảng mâu thuẫn.

## 3. Quyền sở hữu và đầu ra của ba cặp

**Bàn giao chuẩn bị ngày 31/10:** đã chốt inventory và giao diện đầu vào của full-study/2016, chuẩn bị 60 ca chính và 6 ca thử riêng, tái tính 114.702 giá trị lịch sử và dựng lại 1.755 nhãn từ graph mà không thấy sai lệch. Chi tiết ở [RESULTS](docs/RESULTS.md#frozen-reference-and-lineage-audit-31-october-2026), hướng dẫn nhận bộ ca ở [LABEL_REVIEW](docs/LABEL_REVIEW.md#current-midterm-2-review-packet). Đây là hoàn tất khâu chuẩn bị và audit kỹ thuật của Tâm, chưa phải Phúc–Đăng đã chấm nhãn. Giữ answer key và theo dõi ba tháng ở phía điều phối, chỉ gửi ZIP reviewer riêng cho từng người.

**Đầu ra kỹ thuật thực hiện sớm ngày 31/10:** đã bổ sung pipeline coverage/error analysis và thí nghiệm có kiểm soát gồm 126 lượt fit, notebook chạy đủ 7 cell với 4 hình, cùng report tiếng Anh. Các lượt này là chẩn đoán trên dữ liệu đã xem, không thay thế bước chọn cải tiến sau review thật. Kết quả cho thấy kiến trúc LR hai tầng có ích trên bộ 2016, còn lợi ích bổ sung của member means trong LR hai tầng chưa được xác lập. Giữ lịch review và mốc quyết định 04/11 để kết hợp bằng chứng của ba cặp trước khi chốt phương pháp chính.

| Người | Phần chịu trách nhiệm | Đầu ra cá nhân |
|---|---|---|
| Tâm | Core dữ liệu, graph, cache/artifact, giao diện và tích hợp. Bảo đảm cutoff, reference và phiên bản dữ liệu. Điều tra lineage/history cùng Thanh | Gói input đóng băng, manifest/schema, lệnh chạy lại, kiểm tra cutoff và bản tích hợp |
| Thanh | Core nhãn GED, features và proposed. Điều tra tầng dissolve, lịch sử và độ nhạy seed. Thực hiện duy nhất cải tiến đã có bằng chứng | Bản phân tích cơ chế lỗi, cấu hình khóa, implementation kèm tests và ablation |
| Phúc | Kiểm tra graph và coverage, reviewer nhãn thứ nhất. Giữ sở hữu detector đối chứng, Random Forest và HGB, hỗ trợ đối chứng khớp đặc trưng | Coverage theo quy mô mạng, phiếu đánh giá thật, kiểm tra graph và cấu hình RF/HGB |
| Đăng | Reviewer nhãn thứ hai, kiểm tra sự kiện và observation. Giữ leakage, bootstrap theo thời gian và tính đúng của denominator | Phiếu độc lập, agreement/bất đồng, phân biệt unresolved/censored và audit đánh giá |
| Trâm | Giữ Majority/Persistence/LR và chạy baseline bằng cấu hình khóa. Ghép proposed–HGB và kiểm tra các ca lỗi | Prediction đối chứng, bảng bốn nhóm đúng/sai, phân tích lớp và ca minh họa |
| Anh | Tính lại metric, phân tích theo tháng/nhóm kích thước/lịch sử. Tổng hợp claim–evidence, biểu đồ và báo cáo/demo | Bảng/biểu đồ kiểm chứng, so sánh cùng mẫu, diễn giải kết quả và bản báo cáo thống nhất |

Không chuyển việc sửa core sang Phúc–Đăng hoặc Trâm–Anh. Hai cặp này cung cấp bằng chứng và tái lập độc lập, Tâm–Thanh chịu trách nhiệm sửa pipeline, tracker, features và proposed nếu phát hiện vấn đề.

### Giao diện bàn giao để làm song song

Tâm bàn giao snapshot artifact đã có ngay 29–30/10. Mọi cặp làm trên bản chỉ đọc có manifest, không chờ mô hình cải tiến. Phúc–Đăng dùng graph/membership/observation và bộ ca mù. Trâm–Anh dùng labels/features/predictions đóng băng. Tâm–Thanh dùng bản core riêng để chẩn đoán. Các cặp không ghi đè output của nhau.

Khóa ghép đầy đủ là `reference_id + feature_month + community_id + label_month + label_reference_id`. Thêm `model + seed + window` cho dự báo. `community_id` chỉ có nghĩa trong snapshot. Giữ tách ba nghiên cứu: full-study LR–HGB, HeTCo pilot 2015 và tái lập 2016. B4 trong pilot là LR, không được nhầm với ký hiệu baseline của bảng full-study.

Runtime output theo cặp và `run_id` riêng trong `artifacts/`. Phiếu chấm và answer key giữ local, chỉ công bố tổng hợp phù hợp. Notebook và báo cáo kỹ thuật dùng tiếng Anh. Phân công hành chính dùng tiếng Việt. Implementation và tests tương ứng đi cùng commit, chỉ đưa file sản phẩm cần thiết vào commit.

## 4. Tuần 3 — 29/10–04/11: chẩn đoán trước khi cải tiến

| Người | Việc thực hiện | Đầu ra bắt buộc trước 04/11 |
|---|---|---|
| Tâm | Đóng băng hai gói full-study và 2016. Chuẩn bị bộ ca mù mới và giữ answer key riêng. Kiểm tra ID, predecessor và cách reset tuổi/lịch sử trên ca thật | Manifest, inventory, khóa mẫu và sơ đồ lineage kèm ca truy vết. Các cặp chạy được từ artifact đã có |
| Thanh | Rà ca grow/merge bị tầng đầu dự báo dissolve. Kiểm tra khi nào history thiếu, chuỗi bị reset và attention dao động theo seed. Đối chiếu no-D/flat đã có trên cùng mẫu | Bảng cơ chế lỗi với bằng chứng tại t. Đề xuất tối đa một thay đổi, chưa tự thay nhãn hoặc chọn model theo final |
| Phúc | Rà 6 ca thử để kiểm tra đủ bằng chứng. Sau khi chốt hướng dẫn, chấm độc lập bộ ca chính. Tính coverage theo tháng, kích thước và member–tháng | Phiếu reviewer 1, bảng coverage và danh sách thiếu bằng chứng graph/quan sát |
| Đăng | Chấm cùng bộ ca độc lập, không trao đổi trước khi nộp. Kiểm tra successor quan sát được, censored và các lỗi leakage/denominator. Chỉ mở key sau khi khóa hai phiếu | Phiếu reviewer 2, agreement trước thảo luận, bảng bất đồng và biên bản xử lý |
| Trâm | Đối chiếu toàn bộ ca proposed–HGB trên final đã quan sát. Xuất bốn nhóm đúng/sai theo seed, phân tích grow/merge → dissolve. Đọc sâu 12–16 ca đại diện, nêu quy tắc chọn | Bảng ghép 1.269 ca/seed, danh sách 64 ca bất đồng, ví dụ đúng–sai hai chiều và kiểm tra RF/HGB |
| Anh | Tái tính Macro-F1/F1/recall/support và confusion theo lớp/tháng. Phân tầng nhóm 2 người, 3–4, 5–20 và trên 20, lịch sử có/thiếu. Tổng hợp ca nào được lợi từ D hoặc hai tầng | Bảng lớp/tháng/strata, biểu đồ coverage và bản kết luận chẩn đoán ngắn |

### Quy trình kiểm tra nhãn

- Mục tiêu bộ chính là 60 ca development: 24 dissolve, 24 unresolved, 6 grow và 6 merge. Điều chỉnh quota theo số ca thực có, ghi rõ số lấy được. Không đưa 6 ca thử vào số kiểm chứng chính. Mẫu này để chẩn đoán, không suy ra độ chính xác toàn dataset bằng trung bình không trọng số.
- Tâm chọn mẫu có seed, phân bố qua các tháng và kích thước, giữ mapping/nhãn máy/ngưỡng/prediction ngoài gói reviewer. Không dùng chính bộ ca error analysis do prediction chọn làm bằng chứng review đại diện.
- Bằng chứng gồm membership, topology tiền nhiệm/kế nhiệm, cạnh liên quan và coverage. Bỏ tóm tắt top-k gây thiếu predecessor hoặc đánh dấu rõ dữ liệu bị cắt. Theo dõi thêm tối đa ba tháng ở ca dissolve khi đủ quan sát, tách khỏi định nghĩa nhãn một bước. Bằng chứng tương lai chỉ dùng đánh giá ca, không trở thành feature.
- Phúc và Đăng thực sự đọc và điền nhãn/độ tự tin/lý do trong hai phiếu riêng. Ghi exposure và vai trò từng người. Hai phiếu được khóa trước khi so sánh hoặc mở answer key. Sau đó tính raw agreement, confusion gồm unresolved và Cohen kappa khi xác định được. Giữ cả phiếu gốc và quyết định đồng thuận sau thảo luận.
- Cho phép kết luận thiếu bằng chứng hoặc unresolved. Phân biệt phù hợp quy tắc máy, hợp lý về cấu trúc quan sát và tồn tại xã hội. Kiểm tra tự động không được ghi thành kiểm chứng bởi người thật.

### Quy trình coverage và lỗi

- Coverage community–tháng = eligible / (eligible + unresolved) trên các chuyển tiếp quan sát được. Censored cuối kỳ có số đếm riêng. Báo cả coverage ở graph/user để người ngoài graph không bị biến thành cộng đồng dissolve.
- Báo thêm member–tháng có trọng số kích thước, nói rõ có lặp người dùng qua các tháng. So sánh phân phối kích thước, mật độ trong cùng strata kích thước, tuổi/lịch sử, activity và observation. Không dùng riêng trung vị để kết luận hai nhóm giống nhau.
- Macro-F1 chỉ áp dụng cho tập có nhãn resolved. Không ép unresolved thành dissolve, không bỏ ca khó khỏi mẫu số để tăng điểm. Báo subgroup nhóm nhỏ riêng nhưng giữ nguyên kết quả primary.
- Tính riêng lỗi tầng dissolve và lỗi tầng năm sự kiện còn lại. So sánh proposed-only, HGB-only, both-wrong, both-correct theo lớp/tháng và history. Không cộng ba seed thành ba lần số ca độc lập, không suy ra nguyên nhân chỉ từ tương quan feature.

**Mốc quyết định 04/11:** ba cặp bàn giao cùng một bản chẩn đoán. Tâm–Thanh chọn một giả thuyết chính, chỉ ra nhóm ca được kỳ vọng cải thiện và đối chứng nào có thể bác bỏ giả thuyết. Nếu có lỗi pipeline/nhãn thật, sửa tính đúng trước rồi chạy lại mọi mô hình trên reference mới.

## 5. Tuần 4 — 05–11/11: một cải tiến, ablation và bản nộp

| Người | Việc thực hiện | Đầu ra bắt buộc |
|---|---|---|
| Tâm | Chốt schema/reference, cache feature để tránh dựng lại raw/Leiden. Tích hợp runner khớp mẫu, kiểm tra split và tái lập. Xử lý lỗi core cùng Thanh | Gói chạy có manifest, source/config hash, log và kiểm tra đầu vào/output |
| Thanh | Thực hiện đúng giả thuyết đã chọn. Khóa cấu hình và tuning budget trên development/validation. Chạy primary và ablation, giữ nguyên cả kết quả bất lợi | Proposed phiên bản khai báo, tests tương ứng, dự báo và bảng ablation khớp |
| Phúc | Hoàn tất coverage và review, rà ca nghi ngờ graph. Bàn giao HGB với cùng đặc trưng khi cần kiểm tra công bằng, không mở thêm detector | Báo cáo nhãn/coverage, đối chứng HGB khớp và runtime theo lượt đo |
| Đăng | Kiểm tra lại cutoff, key/label joins, cùng mẫu giữa model và bootstrap theo khối tháng. Kiểm tra version khi có sửa nhãn | Audit leakage/denominator, CI ghép cặp và kết quả review/adjudication thật |
| Trâm | Chạy năm baseline tham chiếu theo protocol, chỉ refit khi input/model/reference đổi. Đối chiếu proposed với HGB mạnh nhất và LR, tái kiểm tra ca mục tiêu | Bảng so sánh primary, per-class/per-month và paired wins/losses sau cải tiến |
| Anh | Ghép một báo cáo mở rộng từ Mini Proposal, bổ sung bảng nhãn/coverage/error analysis và ablation. Hoàn thiện notebook/demo từ output đã lưu | Report, notebook có hình/output, bảng claim–evidence và gói code/log cần thiết |

### Cải tiến được phép lựa chọn sau chẩn đoán

| Nếu bằng chứng chỉ ra | Hướng Tâm–Thanh ưu tiên | Kiểm tra bắt buộc |
|---|---|---|
| Lỗi ID/cutoff/lineage hoặc thiếu bằng chứng predecessor | Sửa semantics/bug core, giữ phiên bản reference cũ để đối chiếu | Tests tái hiện, dữ liệu/label mới có reference mới, mọi baseline chạy lại cùng reference |
| History có ích khi quan sát đủ nhưng nhiễu khi thiếu | Rà định nghĩa/cờ observation hoặc cách dùng lịch sử có điều kiện | Full so với no-D khớp, strata quan sát đủ/thiếu, không dùng dữ liệu tương lai để điền lịch sử |
| Tầng đầu bỏ sót grow/merge thành dissolve | Rà loss/class weighting hoặc quy tắc quyết định trên validation | Hai tầng so với flat với cùng feature/scaler/budget, recall và false alarms từng lớp |
| Attention dao động, mean pooling có tín hiệu tốt hơn | Ưu tiên tổng hợp thành viên đơn giản. Dùng LR/HGB với cùng thuộc tính thành viên tổng hợp để tách hiệu ứng feature khỏi kiến trúc | Community-only so với community+member trên cùng head. Flat so với hierarchical trên cùng feature. Giữ attention/mean-pool đã chạy như bằng chứng chẩn đoán |

Chỉ chọn một hàng chính cho Midterm 2. Không mặc định mean pooling là primary mới sau khi đã xem điểm 2016. Nếu chọn hướng pooling, kiểm tra nhỏ dạng 2×2: flat/hierarchical × community-only/community+member, cùng scaler, seed và budget, kèm HGB khớp thuộc tính khi kiểm tra đóng góp. Không gộp các thay đổi nhãn, detector và mô hình vào một lượt rồi gọi đó là ablation.

### Mốc hoàn thành trong tuần

| Ngày | Điều kiện hoàn thành |
|---|---|
| 05/11 | Khóa giả thuyết, feature schema, nguồn/split, metric và danh sách hữu hạn lượt chạy trước fit |
| 06–08/11 | Chạy các đối chứng/ablation cần thiết. Sửa bug đúng workflow, giữ implementation và tests cùng commit |
| 09/11 | Chốt kết quả, rà paired cases và kiểm tra số liệu. Không thêm mô hình mới sau mốc này |
| 10/11 | Hoàn tất report, notebook và bảng bằng chứng, ghi rõ phần development/replication |
| 11/11 | Tái lập từ artifact đóng băng, nghiệm thu PDF/code/logs và demo. Mỗi người giải thích được phần mình |
| 12/11 dự kiến | Nộp/báo cáo Midterm 2 theo lịch chính thức |

Nguồn/giai đoạn xác nhận mới chỉ được gọi là chưa xem khi đã kiểm tra lịch sử tiếp xúc, khóa protocol trước khi mở kết quả và đủ thời gian xử lý. Nếu chưa xác minh được, báo đúng là đánh giá development/replication. Không biến 2016 hay cohort 2018 đã xem thành test mới bằng đổi tên folder.

## 6. Checklist nghiệm thu Midterm 2

- [ ] Có hai phiếu review thật, độc lập trước khi mở key, cùng rubric và bằng chứng đủ để đánh giá dissolve/unresolved. Có số ca/strata, agreement và cách xử lý bất đồng.
- [ ] Coverage có đúng mẫu số, censored riêng, bảng theo tháng/quy mô và so sánh eligible–unresolved. Có coverage member–tháng với định nghĩa rõ.
- [ ] Phân tích proposed–HGB đầy đủ bốn nhóm đúng/sai, lớp/tháng và ca grow/merge → dissolve, không chỉ trình bày ca proposed đúng.
- [ ] Cải tiến nối được với một cơ chế lỗi có bằng chứng. Ablation và đối chứng khớp đặc trưng tách được feature khỏi kiến trúc.
- [ ] Cùng key, label, split, seed và ngân sách chọn cấu hình. Mọi thay đổi reference được version và chạy lại đúng các tầng phụ thuộc.
- [ ] Report đi một mạch Problem → RQ → input/output → graph/labels → coverage/evaluation → baseline/proposed → kết quả/diễn giải. Code/logs và notebook khớp số liệu.
- [ ] Phân biệt việc đã làm với kế hoạch và việc cần người thật. Không cam kết điểm số, social ground truth hoặc ưu thế ổn định nếu bằng chứng chưa hỗ trợ.

## 7. Sau Midterm 2 đến cuối kỳ

| Tuần | Tâm–Thanh: core | Phúc–Đăng: graph/nhãn/kiểm chứng | Trâm–Anh: đối chứng/kết quả |
|---|---|---|---|
| 5 — 12–18/11 | Tâm chốt nguồn/split cho lần xác nhận phù hợp sau phản hồi. Thanh khóa đúng một phiên bản proposed | Phúc rà graph/cohort. Đăng khóa nhãn, eligibility và protocol đánh giá | Trâm khóa baseline và budget. Anh chuẩn bị bảng kết quả theo protocol |
| 6 — 19–25/11 | Tâm chạy pipeline từ nguồn đã xác nhận. Thanh chạy proposed một lần theo cấu hình khóa | Phúc kiểm tra tài nguyên và graph. Đăng tái kiểm tra leakage, coverage và CI | Trâm chạy baseline cùng mẫu. Anh tính lại metric và đối chiếu bằng chứng |
| 7 — 26/11–02/12 | Tâm chỉ thêm độ nhạy detector nếu chẩn đoán cho thấy cần và đủ budget. Thanh chạy ablation mục tiêu, không retune theo kỳ xác nhận | Phúc giữ benchmark detection. Đăng đối chiếu reference/observation và kiểm chứng ca mới | Trâm đối chứng khớp feature/reference. Anh phân tích kết quả xác nhận, giữ riêng các nghiên cứu |
| 8 — 03–09/12 | Tâm tái lập và đóng gói. Thanh hoàn thiện phương pháp và diễn giải | Phúc viết graph/chi phí. Đăng hoàn thiện nhãn/coverage/leakage và bằng chứng review | Trâm chốt baseline/kết quả. Anh hợp nhất report và notebook/demo, cả nhóm nghiệm thu |

Multislice, consensus, B6, ensemble và thay nhãn Jaccard toàn kỳ không còn là việc bắt buộc trước Midterm 2. Chỉ mở khi góp ý/chẩn đoán tạo ra câu hỏi rõ, có đối chứng và thời gian kiểm chứng. Giữ sở hữu module cũ, không dồn các việc mở rộng vào giai đoạn cuối.

## 8. Quy tắc làm việc và bàn giao

- Review kỹ thuật trong từng cặp trước khi bàn giao. Tâm điều phối tích hợp, người sở hữu sửa module. Không yêu cầu nhóm khác tự sửa core để chạy được.
- Đầu ra chung của cặp gồm schema/input version, lệnh hoặc notebook chạy được, cấu hình, log, bảng/hình và diễn giải ngắn. Kết quả fixture, Reddit và review người thật được ghi đúng nguồn.
- Tận dụng artifact đã có. Chỉ dựng lại raw/graph khi nguồn hoặc semantics đổi. Đổi report hoặc phân công không phải lý do chạy lại thí nghiệm nặng.
- Không bỏ unresolved hoặc negative results khỏi hồ sơ. Không chọn tháng/seed/đối chứng thuận lợi sau khi nhìn điểm. Nếu cải tiến không vượt ổn định, báo đúng điều kiện có ích và bằng chứng còn cần kiểm tra.
- Không tạo thư mục source theo tên người, không nhân bản file phân công. Notebook import logic từ `src/reddit_sna`, không copy implementation. Không bắt buộc làm slide cho Midterm 2 trong kế hoạch này.

## 9. Lưu trữ kế hoạch Midterm 1

<details>
<summary>Kế hoạch tuần 1–2 cũ, giữ để truy vết. Không dùng phần này làm lịch công việc hiện tại.</summary>

Các checklist dưới đây thuộc kế hoạch lịch sử, không tự xác nhận hoàn thành. Quy tắc về artifact, review, staging và tiến độ hiện hành ở các mục phía trên được ưu tiên.

### Tuần 1 — 15–21/10: ba prototype độc lập, báo cáo ngày 22/10

Mỗi nhóm hoàn thành một prototype từ đầu vào riêng đến kết quả đánh giá. Mỗi người có công việc riêng và chỉ bàn giao kỹ thuật cho người cùng nhóm trong tuần 1. Không phải chờ hoặc sử dụng artifact của nhóm khác.

#### Nhóm Tâm–Thanh: prototype core trên Reddit pilot

**Đầu ra chung:** một đường chạy độc lập `Reddit pilot → snapshot R → community → tracking/nhãn → features → mô hình cơ bản → kết quả đánh giá sơ bộ`. Nhóm tự phụ trách toàn bộ đường chạy này, không cần nhận detector/tracker từ Phúc–Đăng hoặc bộ đánh giá từ Trâm–Anh.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Tâm** | Đã chuẩn bị sẵn bộ dataset Reddit gồm 15 corpus và các script xử lý ban đầu. Tạo repository GitHub cho đề tài, viết mô tả repo, mời năm thành viên còn lại và phân quyền cộng tác. Dựng cấu trúc thư mục, thiết lập chính sách quản lý dữ liệu và file riêng tư; dataset đã được chủ repo duyệt công bố qua Git/LFS, khai báo thư viện/môi trường và viết README hướng dẫn cài đặt, chạy demo, quy tắc đặt nhánh và gửi pull request. Rà soát dữ liệu đã có, tổ chức thư mục và manifest. Chọn phạm vi pilot nhỏ gồm các tháng liên tiếp trong train, chạy chuẩn hóa và dựng mạng trả lời R. Dùng thư viện Independent Leiden để tạo community tạm cho chính prototype core. Chốt giao diện nội bộ với Thanh, viết lệnh chạy và ghép đường chạy của nhóm. | Repository GitHub đã mời thành viên, cấu trúc thư mục, .gitignore, cấu hình môi trường/thư viện, README cộng tác và chạy demo; manifest pilot, snapshot thật, membership tạm và cấu hình detector. |
| **Thanh** | Nhận membership từ Tâm, triển khai tracking tối thiểu và bảng đặc trưng community. Ưu tiên GED bản đầu; nếu chưa hoàn thành, dùng quy tắc overlap/Jaccard được ghi rõ để giữ đường chạy thông suốt. Tạo nhãn chuyển tiếp t→t+1, features chỉ dùng thông tin đến t. Chạy một mô hình dự báo cơ bản và tính chỉ số bằng thư viện có sẵn trên phần giữ lại theo thời gian trong pilot. Ghi rõ phần nào của GED/HeTCo chưa triển khai. | Tracker, bảng features/nhãn, mô hình cơ bản, predictions, macro-F1 và confusion matrix của prototype core. |

**Giới hạn tuần 1:** detector tạm và mô hình cơ bản giúp kiểm tra luồng core. Chưa bắt buộc hoàn thành tầng T, multislice, consensus hoặc HeTCo đầy đủ. Không gọi mô hình cơ bản là HeTCo hoàn chỉnh. Tâm–Thanh tự làm phần detection và đánh giá tối thiểu bằng thư viện; Phúc–Đăng và Trâm–Anh vẫn phát triển phần chuyên trách riêng để tích hợp sau.

#### Nhóm Phúc–Đăng: prototype detection và tracking có kiểm chứng

**Đầu ra chung:** một đường chạy độc lập `benchmark mạng động → detection → membership → tracking → đánh giá với nhãn chuẩn`. Nhóm tự sinh dữ liệu, không cần snapshot của Tâm hoặc bảng nhãn của Thanh.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Phúc** | Sinh mạng động nhỏ với community và thành viên biết trước; cùng Đăng xác định các tình huống giữ nguyên, tăng, giảm, hợp nhất, tách và phân rã. Lưu phân hoạch chuẩn, seed và cấu hình. Chạy Independent Leiden trên từng snapshot, kiểm tra membership và độ phủ. Tính AMI so với phân hoạch chuẩn, ghi chi phí chạy và ghép phần detection vào demo nội bộ. | Bộ benchmark tổng hợp có ground truth, code detector, membership dự đoán và bảng AMI. |
| **Đăng** | Cùng Phúc xây quy tắc nhãn chuẩn và tình huống mơ hồ. Triển khai Jaccard tracker; cố định ngưỡng và thứ tự xử lý sự kiện. Trước tiên kiểm chứng tracker trên membership chuẩn, sau đó chạy trên membership detector của Phúc để phân biệt lỗi tracking với lỗi detection. Tính macro-F1, F1/support từng sự kiện và confusion matrix; tổng hợp trường hợp sai. | Tracker, test sáu sự kiện, nhãn dự đoán, kết quả tracking riêng và kết quả toàn luồng detection–tracking. |

**Điều kiện đánh giá:** tách các mạng dùng phát triển/chọn ngưỡng khỏi mạng dùng đánh giá. Kết quả là kiểm chứng trên dữ liệu tổng hợp có ground truth, không trình bày như kết quả dự báo Reddit.

#### Nhóm Trâm–Anh: prototype baseline dự báo và đánh giá

**Đầu ra chung:** một đường chạy độc lập `bảng community–tháng mẫu → split thời gian → huấn luyện baseline → predictions → evaluation results`. Nhóm tự tạo bảng mẫu có quy tắc, không cần features/nhãn từ Thanh hoặc tracker của Đăng.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Trâm** | Tự tạo bảng community–tháng tổng hợp có lịch sử, features, nhãn và seed tái lập. Mô tả rõ cơ chế sinh nhãn để tránh kết quả khó hiểu. Triển khai B1 Majority/Persistence và B4 Logistic Regression; thêm fallback Majority khi thiếu lịch sử. Dùng split Anh cung cấp, chỉ fit xử lý dữ liệu và mô hình trên tập học, xuất dự đoán từng mẫu. | Script sinh bảng mẫu, bảng dữ liệu, code baseline, cấu hình/model và predictions B1/B4. |
| **Anh** | Thống nhất schema với Trâm, viết chia tập theo thời gian của tháng nhãn. Kiểm tra khóa mẫu, số lớp và thời điểm biết features; tạo các kiểm tra cơ bản ngăn dùng dữ liệu tương lai. Đánh giá dự đoán Trâm bàn giao, xuất macro-F1, balanced accuracy, precision/recall/F1/support từng lớp và confusion matrix. Viết hướng dẫn đọc kết quả và ghép phần trình bày của nhóm. | Split, code đánh giá, bảng kết quả baseline, confusion matrix, báo cáo giới hạn và lệnh demo của nhóm. |

**Điều kiện đánh giá:** tập học phải có ít nhất hai lớp để chạy Logistic Regression. Ghi rõ lớp thiếu và quy ước tính macro-F1. Điểm trên bảng tổng hợp chứng minh baseline và evaluation chạy được; chưa chứng minh khả năng dự báo trên Reddit. Không so trực tiếp điểm này với điểm của hai nhóm còn lại.

#### Lịch tuần 1

| Mốc | Công việc của từng nhóm |
|---|---|
| **15–16/10** | Mỗi cặp chốt phạm vi, schema và lệnh chạy nội bộ; chuẩn bị đầu vào riêng. Mỗi người bắt đầu module của mình. |
| **17–18/10** | Hai người trong mỗi cặp ghép module và chạy lần đầu từ input của nhóm đến output. Nhóm nào có lỗi tự xử lý trong phạm vi của mình. |
| **19–20/10** | Hoàn thành bước đánh giá, kiểm tra dữ liệu/nhãn/split, lưu kết quả và sửa lỗi. Không có mốc chờ artifact từ nhóm khác. |
| **21/10** | Mỗi cặp chạy lại bằng cấu hình cố định vào thư mục output mới; hoàn thiện README, log và slide riêng. |
| **22/10** | Trình bày ba demo độc lập. Từng người giải thích nhiệm vụ, code, đầu ra và hạn chế của phần mình. |

#### Checklist nghiệm thu mỗi nhóm

- [ ] Có đầu vào xác định, nguồn dữ liệu và phạm vi được ghi rõ.
- [ ] Có code và cấu hình của cả hai người, ghép thành một lệnh hoặc chuỗi lệnh được ghi đầy đủ trong README.
- [ ] Chạy từ đầu vào của nhóm đến kết quả đánh giá mà không phải xin artifact từ nhóm khác hoặc nhập tay dự đoán để hoàn thành demo.
- [ ] Có bảng kết quả, kiểm tra phù hợp và ví dụ lỗi; phân biệt dữ liệu thật với tổng hợp.
- [ ] Lưu seed, phiên bản môi trường, cấu hình, log và output trong thư mục riêng của nhóm.
- [ ] Ghi rõ phần chưa hoàn thành, không coi sơ đồ hoặc code chưa chạy là prototype hoàn tất.


### Tuần 2 — 22–28/10: hoàn thiện module độc lập

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Hoàn thiện snapshot, R/T và dựng multislice trên fixture. Kiểm tra ID, trọng số và self-loop | R/T pilot, detector đề xuất bản đầu |
| **Thanh** | Củng cố GED/features/HeTCo từ demo tuần 1, bổ sung lịch sử và nhận community để ghép pilot thật | Core được kiểm thử, features mở rộng và bảng pilot |
| **Phúc** | Hoàn thiện Louvain/Independent Leiden và benchmark bản tối thiểu. Dựng B5 bằng thư viện có sẵn, thống nhất giao diện với Thanh/Trâm | Detector, benchmark và B5 chạy fixture |
| **Đăng** | Hoàn thiện Jaccard, kiểm tra snapshot. Viết test split thời gian và đặc trưng không dùng dữ liệu tương lai | Tracker đối chứng và test leakage |
| **Trâm** | Hoàn thiện B1/B4, viết chương trình chạy baseline và nhận B5 từ Phúc để chạy thử | Baseline cơ bản và chương trình chạy chung |
| **Anh** | Hoàn thiện macro-F1/confusion matrix, bảng kết quả và kiểm tra khóa mẫu bằng dữ liệu giả lập | Chỉ số cơ bản và mẫu báo cáo kết quả |

**Đầu ra chung:** Tâm–Thanh mở rộng core, Phúc–Đăng hoàn thiện đối chứng và kiểm tra kỹ thuật, Trâm–Anh hoàn thiện chương trình chạy baseline/báo cáo. B5 do Phúc bàn giao là đầu vào mới từ tuần 2, không ảnh hưởng tính độc lập của demo tuần 1.

**Bàn giao cuối tuần 2:** Phúc gửi benchmark/membership cho Tâm–Thanh và B5 cho Trâm. Thanh gửi features/nhãn cho Trâm, Đăng kiểm tra tính hợp lệ. Anh cung cấp chỉ số cơ bản và bảng kết quả, Đăng cung cấp test leakage. Chạy thử pilot sau thay đổi, chưa yêu cầu chạy hết corpus.

## Nghiệm thu prototype core tuần 1 — cập nhật 17/10

- [x] Tâm: audit/manifest, snapshot R và Independent Leiden trên Reddit thật; giao diện membership được forecast tiêu thụ.
- [x] Thanh: Jaccard/GED thích nghi, features/nhãn, split theo tháng nhãn, Majority/Logistic Regression, predictions và evaluation.
- [x] Kiểm chứng độc lập tại main aa110ac: 148/148 tests pass; forecast thật tái lập đúng báo cáo; model lưu ra dự đoán lại đúng file predictions.
- [x] Chủ repo xác nhận đã mời đủ năm thành viên; việc nhận lời mời/quyền thực tế chưa được audit độc lập.
- [x] Bản bàn giao mới được chạy xác nhận: raw → evaluation thành công; 161/161 tests pass không skip; hai notebook 10/10 và 7/7 cell, tổng 20 biểu đồ; bộ review có 31 trường hợp với 62 hàng chấm trống. Chi tiết ở `docs/RESULTS.md#final-delivery-verification`.
- [ ] Hai người rà soát nhãn độc lập và xử lý bất đồng; bộ mẫu được chuẩn bị không đồng nghĩa nhãn đã được xác nhận.
- [ ] Xác nhận kỳ đánh giá tiếp theo chưa từng xem, khóa protocol trước khi chạy; không dùng điểm 2015 như test xác nhận mới.
- [ ] Nhóm tập trình bày, đi học và báo cáo ngày 22/10; dàn ý slide không phải bằng chứng đã thuyết trình.

Lệnh demo và nội dung trình bày ở `docs/RUNBOOK.md` và `docs/RESULTS.md#presentation-outline`. Các hạn chế về ground truth, lớp thiếu và coverage phải được trình bày cùng điểm số. HeTCo đầy đủ và detector đề xuất thuộc các tuần sau, không phải thiếu sót bắt buộc của baseline tuần 1.

</details>
