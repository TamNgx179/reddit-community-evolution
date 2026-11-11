# Kết quả Week 4 của Phúc — agreement, coverage và graph audit

**Cập nhật:** 11/11/2026  
**Phạm vi:** gói `Phuc_Week4_Review_Coverage_20261111.zip` do Tâm bàn giao và snapshot graph đã mở sau khi hai phiếu review được khóa.

## Kết luận ngắn

Coverage full-study và graph audit đã chạy thành công. Có 7.490 transition
eligible trong 11.562 transition quan sát được. Coverage theo community-month là
**64,78%** và theo member-month là **79,31%**. Toàn bộ **45/45 tháng** từ
2015-01 đến 2018-09 đã qua graph audit.

Đây là coverage của dữ liệu/transition được quan sát, **không phải** độ chính xác
event, chất lượng dự báo hay bằng chứng đại diện cho toàn bộ cộng đồng Reddit.

## 1. Đầu vào và tính toàn vẹn

| Đầu vào | Kiểm tra |
| --- | --- |
| Gói review/coverage của Tâm | 10 checksum nội bộ khớp sau khi giải nén |
| Snapshot graph full-study | SHA-256 ZIP khớp `dfef0d02d5c99d65dbdddfc63700a8f971f3bf83a7d3ce310a5fd35277657f72` |
| File trong snapshot | 622 checksum khớp |
| Cohort coverage | Một `reference_id`, một `label_reference_id`, tháng liên tiếp 2015-01 → 2018-09 |
| Output coverage | Manifest output và 45 hàng `graph-audit.csv` đều đã kiểm tra |

Artifact cục bộ:

- Gói Tâm: `artifacts/handoff/phuc-week4-review-coverage-20261111-001/`
- Snapshot graph: `artifacts/handoff/phuc-coverage-snapshots-20261111-001/`
- Kết quả cuối: `artifacts/diagnostics/phuc-coverage-full-study-graph-20261111-001/`

## 2. Agreement và adjudication

| Chỉ số trước adjudication | Giá trị |
| --- | ---: |
| Số ca panel | 60 |
| Đồng ý thô | 47/60 = 78,33% |
| Cohen's kappa không trọng số | 0,443255 |
| Ca bất đồng | 13 |

Adjudication riêng chốt 13 ca gồm **10 `unresolved`**, **2 `grow`** và
**1 `shrink`**. Hai CSV gốc được giữ nguyên, kết quả chung nằm ở
`adjudication.csv`.

Reviewer 1 là bản được Phúc chấp nhận có hỗ trợ AI. Summary nhận từ Tâm cũng
ghi reviewer 2 là AI-assisted theo xác nhận của Đăng, trong khi receipt reviewer
2 còn thiếu metadata provenance đầy đủ. Vì vậy kappa ở trên chỉ là **đối chiếu
nhãn kỹ thuật của panel**, không được trình bày là agreement giữa hai người chấm
độc lập không dùng AI.

## 3. Coverage full-study

| Đại lượng | Giá trị |
| --- | ---: |
| Transition quan sát | 11.562 |
| Eligible | 7.490 |
| Unresolved | 4.072 |
| Terminal censored | 183 |
| Community-month coverage | 0,647812 (64,78%) |
| Observed member-month | 1.787.503 |
| Eligible member-month | 1.417.626 |
| Member-month coverage | 0,793076 (79,31%) |
| Terminal censored member-month | 30.543 |

`coverage.csv` có phân tầng `month` (45 tháng), `size` (4 nhóm),
`lineage_history` (2 nhóm) và tổng thể. `distributions.csv` giữ các thống kê
phân bố theo toàn bộ và nhóm size. Terminal-censored được tách riêng, không bị
đếm thành `unresolved` hoặc `dissolve`.

## 4. Graph audit

Trạng thái là `coverage_complete_graph_verified`.

- Kiểm đủ 45/45 tháng full-study.
- Membership và số community/member của từng tháng khớp feature inventory.
- Edge không trùng, đúng tháng; reply endpoint và các mẫu số observed user/active
  author khớp metadata snapshot.
- Không có missing evidence trong output coverage.

## 5. Phần chưa có kết quả

Đối chứng HGB (P4-02) **chưa chạy**. Không có giả thuyết, feature/cutoff,
reference, split, seed và runtime budget đã được Tâm–Thanh chốt/bàn giao cho
Phúc. Không tự thay thế bằng một run HGB khác vì như vậy không còn là đối chứng
khớp.

## 6. Nội dung để Anh ghép báo cáo

> Phúc đã xác minh gói coverage, 622 checksum snapshot graph và chạy graph audit
> đủ 45 tháng full-study. Coverage theo community-month là 64,78% và member-month
> là 79,31%; 7.490/11.562 transition quan sát được đủ điều kiện, 4.072 unresolved
> và 183 terminal censored được tách riêng. Panel review 60 ca có raw agreement
> 78,33%, kappa 0,443255 trước adjudication; 13 ca bất đồng được lưu ở
> adjudication riêng. Đây là đối chiếu kỹ thuật AI-assisted, không phải human
> agreement thuần túy. HGB matched-control chưa có cấu hình bàn giao nên không có
> kết quả để báo cáo.
