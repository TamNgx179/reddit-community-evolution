# Kế hoạch nâng chất lượng đồ án SNA

Căn cứ: *Lec00. Course overview – SNA – TranHungNghiep – 2026*, 33 slide. Slide 9 yêu cầu đi từ bài toán đến dữ liệu, đánh giá, phương pháp, thí nghiệm và kết quả. Slide 14 cho biết A2 là đồ án nhóm, chiếm 50% điểm học phần, và mức tối đa đòi hỏi tiềm năng paper. Slide 25 và 30 phân biệt trọng tâm của Midterm 1 và Midterm 2. Các tiêu chí nghiệm thu bên dưới là đề xuất của nhóm để đáp ứng góp ý, không phải thang điểm do giảng viên công bố.

## Part 1 — Bài toán, kế hoạch thực nghiệm và bằng chứng Midterm 2

Câu hỏi chính: Với các nhóm người dùng phát hiện từ mạng reply Reddit ở tháng t, những tín hiệu nào quan sát được đến t giúp dự báo chuyển tiếp cấu trúc ở t+1, và dự báo áp dụng được cho phần nào của mạng quan sát?

| Thí nghiệm | Thiết kế và phép đo | Đầu ra đã có |
| --- | --- | --- |
| E1. Phạm vi áp dụng | 15 corpus, 45 snapshot. Tách resolved, unresolved và censored, so phân bố theo kích thước, lịch sử, tháng. | 7.490/11.562 chuyển tiếp đủ điều kiện. Coverage 64,78% theo cộng đồng–tháng và 79,31% theo thành viên–tháng. Phúc xác minh graph 45/45 tháng. |
| E2. So sánh trên full-study | Năm baseline tham chiếu và các đối chứng đã khóa, cùng 1.269 khóa final mỗi seed. Macro-F1 sáu lớp, recall theo lớp, phân tích theo tháng và ghép cặp. | Proposed 0,4117, HGB 0,3880. Chênh lệch +0,0237, CI 95% [−0,0694, +0,0945]. 29 ca proposed đúng riêng và 35 ca HGB đúng riêng. |
| E3. Đóng góp thành phần | Dùng ablation đã lưu trên cùng khóa. Tách kiến trúc hai tầng khỏi đặc trưng động. | Hai tầng so với flat +0,0796 [0,0292, 0,1321]. Dynamic so với no-dynamics +0,0474 [−0,0073, 0,0934]. |
| E4. Rà nhãn | So hai phiếu 60 ca, giữ dữ liệu trước phân xử và quyết định cuối. Đối chiếu graph và tracker. | Đồng ý 47/60, κ 0,4433, 13 phân xử. Có 24 ca review unresolved trong số các ca tracker dissolve. Hai phiếu có hỗ trợ AI, nên bằng chứng kiểm chứng độc lập cần bổ sung ở Part 2. |
| E5. H1 pilot 2015 | Đổi quy tắc quyết định tầng đầu với cùng cấu hình. Chọn ngưỡng trước main, theo dõi F1, missed events và recall ở nhóm có overlap. | 90 lượt fit tái lập. Main Macro-F1 tăng 0,3976 → 0,4109, missed events tăng 18 → 22, overlap recall giảm 0,651 → 0,508. Giữ v4 ở pilot. |
| E6. Demo | Từ ZIP frozen kiểm tra checksum, khóa ghép và tái tính metric. Mở notebook để xem bảng theo tháng và một ca nhãn. | Tâm đã tái tính 123 nhóm metric. Anh có notebook đã lưu output. |

Full-study dùng cutoff final 2018-01, validation bắt đầu 2017-07. Các CI ở E2–E3 dùng phân tích khám phá với 1.000 lượt bootstrap theo khối hai tháng, seed 20261031. Protocol thực nghiệm chính có cấu hình bootstrap riêng. Pilot 2015 và replication 2016 có reference và cửa sổ riêng.

## Part 2 — Rà nhãn tự động và chuẩn bị kiểm chứng độc lập

Đã đóng hai gói chấm mù cục bộ trong `artifacts/review/sna-independent-review-20261111/`. Hai gói dùng chung 12 ca development từ bốn tháng, mỗi tháng gồm một ca dissolve, một unresolved và một ca đối chứng grow hoặc merge. Seed 20261111. Đã loại các khóa từng xuất hiện trong ba bảng mapping/answer key sẵn có và kiểm tra hash tám manifest theo tháng. Bằng chứng gồm overlap, cạnh giữa thành viên nhóm, hoạt động đăng bài/bình luận và hiện diện trong mạng reply. Hai agent đã nộp riêng trên cùng bằng chứng chấm mù. Hai agent đồng ý 11/12 ca (91,7%, κ = 0,868), mỗi agent khớp tracker 0/12. Cả hai đánh dấu unresolved cho bốn ca tracker dissolve vì tháng sau không quan sát được thành viên nào. Bước kiểm chứng bằng người chấm vẫn đang chờ. [Kết quả tổng hợp](../reports/tables/sna-feedback-20261111/automated_label_review_summary.json). File điều phối chứa khóa và nhãn máy, lưu riêng.

Lấy mẫu mới, tránh lặp ca đã mở đáp án. Khóa seed, tháng, nhóm kích thước và mức quan sát trước khi chọn. Dùng dissolve và unresolved làm trọng tâm, kèm ca đối chứng có tiếp nối rõ. Hai người chấm riêng từ cùng evidence, lưu nhãn, lý do và provenance, khóa hai phiếu trước khi đối chiếu tracker. Tách kết quả từng người khỏi quyết định phân xử.

Đầu ra nghiệm thu gồm danh sách ca có khóa và hash, rubric, hai phiếu khóa, confusion matrix, κ, phân xử và bảng lý do bất đồng. Panel phân tầng dùng để chẩn đoán. Muốn ước lượng tỷ lệ toàn cohort phải có thiết kế lấy mẫu và trọng số tương ứng.

Đã bổ sung 12 ca chấm mù khác do Tâm chấm thay Thanh theo ủy quyền. Sau khi khóa đủ phiếu bằng SHA-256, đối chiếu nhãn frozen khớp 7/12. Bốn ca không quan sát được thành viên trong mạng reply tháng sau đều được cả Tâm và tracker gán dissolve. Năm bất đồng tập trung vào cách diễn giải việc thành viên phân tán hoặc đi vào nhóm lớn khi mất cạnh nội bộ. Đây là đối chiếu giữa một người và tracker. [Tổng hợp](../reports/tables/sna-feedback-20261111/delegated_human_review_summary.json).

## Part 3 — Tìm điều kiện có ích và khóa một cải tiến

Đã chạy phép thử khám phá với xác suất dự báo đã lưu. Chỉ thay nhãn dissolve đang được argmax chọn khi xác suất dissolve dưới 0,5. Trên 1.269 ca, số grow/merge bị đoán thành dissolve giảm 22 → 13, số báo động sự kiện sai trên 1.167 ca dissolve tăng 64 → 134. Chênh lệch Macro-F1 với proposed hiện tại là +0,0012, CI 95% [−0,0288, +0,0423]. Giữ proposed hiện tại. Phép thử dùng kỳ đã xem và không fit lại.

Đã xuất các bảng theo tháng, kích thước, lineage và lịch sử hoạt động. So với no-dynamics, dynamic có Δ Macro-F1 +0,0569 trong nhóm có lịch sử hoạt động (n=730), −0,0053 trong nhóm thiếu lịch sử (n=539). Đây là mô tả theo nhóm trên kỳ đã xem, cần xác nhận trước khi chọn cách dùng lịch sử có điều kiện. [Bảng kết quả](../reports/tables/sna-feedback-20261111/)

Dùng 64 ca chênh về đúng/sai và 34 ca grow/merge như dữ liệu chẩn đoán đã xem. So cả hai chiều thắng/thua theo tháng, kích thước, predecessor và lịch sử tương tác. Giữ support của từng lớp trong bảng. Khi giải thích tác động lịch sử, so full với no-dynamics trong cùng nhóm thay vì diễn giải chênh lệch giữa hai nhóm khác thành phần lớp.

Đã kiểm tra quy tắc có điều kiện trên cùng mẫu frozen: dùng dynamic khi có lịch sử hoạt động, dùng no-dynamics khi thiếu. Macro-F1 tăng 0,4117 → 0,4136, báo động sai giảm 64 → 60, còn 22 lỗi grow/merge → dissolve. Δ so với proposed +0,0018, CI [−0,00008, +0,0027]. Bỏ lần lượt từng tháng vẫn cho Δ dương, từ +0,0006 đến +0,0027. Đây là ứng viên để khóa trước cho phép xác nhận tiếp theo. Giữ proposed hiện tại cho Midterm 2. [Kết quả](../reports/tables/sna-feedback-20261111/history_conditional_intervals.csv).

Trước lần xác nhận, ghi lại lịch sử tiếp xúc với cohort, khóa reference, split, cutoff, seed và tiêu chí chấp nhận. So ứng viên với proposed hiện tại và HGB trên cùng mẫu. Báo cáo cả recall grow/merge, báo động sai trên dissolve, Macro-F1 và CI ghép cặp.

Kiểm tra trực tiếp hiệu ứng theo lịch sử bằng cùng tháng lấy mẫu cho hai nhóm. Chênh lệch giữa hai mức lợi ích là +0,0622. CI 95% chứa 0 với cả khối hai tháng [−0,0099, +0,1123] và khối ba tháng [−0,0137, +0,1151]. [Bảng độ nhạy](../reports/tables/sna-feedback-20261111/history_interaction_sensitivity.csv).

### Tiêu chí đề xuất cho lần xác nhận

- Ghi cohort, lịch sử tiếp xúc, manifest nguồn, cutoff, reference, model hashes và người giữ kết quả trước khi mở dự báo. Nếu không xác minh được lịch sử tiếp xúc, báo kết quả là replication.
- So đúng một ứng viên dùng dynamic khi có lịch sử và no-dynamics khi thiếu, với proposed hiện tại và HGB trên cùng mẫu, seed 42/43/44. Khóa trường xác định lịch sử ở tháng t.
- So chính là Δ Macro-F1 sáu lớp với proposed hiện tại. Công bố CI ghép cặp khối hai tháng, độ nhạy khối ba tháng, số tháng, support và confusion theo lớp. Chỉ gọi lợi thế xác nhận nếu cận dưới CI chính lớn hơn 0. Để đề xuất thay cấu hình, đồng thời yêu cầu tỷ lệ báo động sai trên dissolve không tăng và recall grow hoặc merge không giảm. Nếu một lớp không có support, ghi phép kiểm bảo vệ lớp đó chưa đánh giá được.
- Rubric nhãn phải khóa trước khi giao phiếu. Dùng hai người chưa xem nhãn agent hoặc tracker. Thu phiếu riêng và giữ SHA-256 từng phiếu. Sau khi khóa mới mở khóa đối chiếu và phân xử. Báo riêng tình trạng quan sát tháng sau và bằng chứng tiếp nối bằng cạnh.

## Part 4 — Kể hai kết quả theo yêu cầu Midterm 2

1. **Coverage và tính hợp lệ của nhãn.** Kết quả là 64,78% chuyển tiếp đủ điều kiện, còn 24 ca chẩn đoán tracker dissolve được review là unresolved. Insight là khả năng quan sát và quy tắc nối nhóm ảnh hưởng đến tập có nhãn. Kết luận là báo coverage cùng metric, và dùng bằng chứng hai tháng để rà ca cụ thể.
2. **Macro-F1 và lỗi từng ca.** Proposed hơn HGB 0,0237 Macro-F1 nhưng HGB đúng riêng thêm sáu ca và CI chứa 0. Insight là trung bình theo lớp và số ca đúng phản ánh hai mặt khác nhau. Kết luận là giữ so sánh theo lớp, công bố CI, chọn một lỗi mục tiêu để kiểm chứng tiếp.

### Abstract draft

We study whether structural changes in Reddit user communities can be forecast from monthly reply networks. Communities are detected with weighted Leiden and linked across months by a GED adaptation. Of 11,562 observed transitions, 7,490 receive a resolved label. On 1,269 chronological evaluation cases, hierarchical logistic regression reaches six-class Macro-F1 of 0.4117 versus 0.3880 for hierarchical gradient boosting. The paired month-block interval for the difference includes zero, and boosting correctly predicts six more cases per seed. A stratified review panel exposes disagreements between tracker-assigned dissolution and unresolved transitions. A separate 2015 pilot finds that a threshold change raises Macro-F1 slightly while increasing missed events. Together, these results locate the applicability boundary and motivate targeted checks of label validity and forecasting errors.

### Outline báo cáo

Bài toán và RQ → dữ liệu và graph → nhãn và coverage → protocol và baseline → proposed và ablation → hai kết quả chính → giới hạn → kết luận. Appendix chứa bảng thí nghiệm, nguồn artifact, checksum và lệnh tái lập.

## Nguồn bằng chứng trong repo

- [Báo cáo chẩn đoán](../reports/MIDTERM2_DIAGNOSTIC_REPORT.md)
- [Bảng so sánh Week 4](../reports/WEEK4_COMPARISON_REPORT.md)
- [Audit của Đăng](https://github.com/TamNgx179/reddit-community-evolution/blob/afec18c/docs/AUDIT_LEAKAGE_DENOMINATOR.md)
- [Kết quả Phúc](https://github.com/TamNgx179/reddit-community-evolution/blob/afec18c/docs/PHUC-WEEK4-RESULTS.md)
- [Báo cáo H1](../reports/H1_ABLATION_REPORT.md)
- [Hướng dẫn tái lập](WEEK4_HANDOFF.md)
