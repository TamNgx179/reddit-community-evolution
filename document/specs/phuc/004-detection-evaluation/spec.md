# PHUC-004 — AMI, coverage và đánh giá detection

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P04.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-004). **Giao diện:** [contracts.md](../contracts.md).

**Triển khai hiện tại:** T01 DONE — kiểm tra identity/keys/hash/cohort và căn hai vector theo user ID; [hướng dẫn](README.md), [bằng chứng và output](../evidence/PHUC-004-T01-alignment.md). PHUC-004 đang làm 1/6 task; coverage, AMI/policy và metric export còn ở T02–T06.

## Mục tiêu và user story

**US1, P1:** Là thành viên nhóm, tôi xem được detector khôi phục nhóm chuẩn đến đâu, đang chấm trên bao nhiêu user và chi phí chạy là gì; không bị nhầm điểm cao với dữ liệu bị bỏ sót.

Evaluator có thể phát triển độc lập bằng membership fixture. Nghiệm thu có thêm kết quả từ detector thật của 003.

## Yêu cầu

- **PHUC-004-FR01:** Kiểm tra dataset/reference/month/user keys; chặn duplicate/user lạ/tập prediction khác endpoint trước khi tính điểm.
- **PHUC-004-FR02:** Đếm active/endpoint/assigned/isolate; báo coverage trên active, số nhóm chuẩn trên toàn bộ và tập được chấm riêng.
- **PHUC-004-FR03:** Căn hai vector nhãn theo cùng user ID rồi tính AMI bằng thư viện; bất biến tên nhóm/thứ tự dòng; missing/degenerate có policy và trạng thái rõ.
- **PHUC-004-FR04:** Xuất metrics chi tiết và summary có đơn vị tổng hợp/support; canonical seed 0 riêng, timing có phạm vi, peak memory null nếu chưa đo.
- **PHUC-004-FR05:** Có kiểm tra lỗi/invariants và kết quả stable/grow development thật truy ngược được tới config/input/run.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Hai phân hoạch trùng cấu trúc nhưng đổi tên nhóm/thứ tự CSV thì AMI không đổi; phân hoạch hoàn toàn khớp, đủ điều kiện, cho AMI 1 |
| AC02 | Graph có isolate thì assigned vẫn bằng endpoint và coverage < 1 khi active > endpoint; không bỏ isolate khỏi mẫu số |
| AC03 | Duplicate/user lạ/missing endpoint thì báo lỗi dữ liệu; không chỉ lấy giao để che lỗi |
| AC04 | Empty/insufficient/constant partitions theo policy đã ghi có trạng thái riêng, không tạo điểm mặc định để lấp bảng |
| AC05 | Summary ghi số hàng hợp lệ/thiếu và nhóm tổng hợp; không gọi ARI seed là AMI truth, không biến wall time tháng thành timing riêng từng seed |

## Phụ thuộc và ngoài phạm vi

Schema từ 001; nghiệm thu integration cần output 003. Không cần tracker hay macro-F1 sự kiện. Không tự triển khai lại công thức AMI hoặc yêu cầu AMI phải vượt 0.9 để task hoàn thành.

## Output và kiểm chứng độc lập

- Module: `src/reddit_sna/evaluation/detection.py`; dependency trong `pyproject.toml` khi dùng.
- Artifact: `detection_metrics.csv`, `detection_summary.csv`, timing/status JSON và config policy.
- Test: `tests/unit/test_detection_evaluation.py`, meaningful cases căn user, đổi nhãn, lỗi keys, coverage và dữ liệu không đủ.
- Evidence: bảng thực tế stable/grow, tập user chấm, version scikit-learn và lệnh đã chạy. Mọi kết quả là benchmark tổng hợp.
