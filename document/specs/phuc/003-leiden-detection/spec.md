# PHUC-003 — Adapter Independent Leiden cho benchmark

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P03.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-003). **Giao diện:** [contracts.md](../contracts.md).

## Mục tiêu và user story

**US1, P1:** Là Phúc/Đăng, tôi nhận được membership detector có reference và diagnostics từ graph tổng hợp để đánh giá/track mà không viết lại thuật toán Leiden.

`detect_snapshots` đã có trong source; task của Phúc là chuẩn bị input, gọi đúng, lưu kết quả và kiểm tra adapter trên benchmark mới.

## Yêu cầu

- **PHUC-003-FR01:** Gọi detector hiện có trên snapshot đã kiểm tra, protocol tổng hợp và identity scope của dataset; không đưa truth labels vào detector.
- **PHUC-003-FR02:** Bản đầu seed 0/gamma 1; bản đủ lịch seed 0/1/2 cố định, canonical 0; không chọn seed theo điểm.
- **PHUC-003-FR03:** Lưu membership mỗi tháng/seed, dictionary diagnostics, dependency versions và mapping reference detector với dataset.
- **PHUC-003-FR04:** User được gán đúng tập endpoint; empty graph/isolate có trạng thái rõ; input sai hoặc output cũ không bị sửa tại chỗ.
- **PHUC-003-FR05:** Có kiểm tra hành vi adapter và một lượt development thật; ARI giữa seeds không được báo như AMI ground truth.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Có graph stable hợp lệ, khi gọi seed 0, membership đúng bốn cột và đúng tập endpoint, diagnostics được lưu |
| AC02 | Khi chạy ba seed, có ba membership mỗi tháng, canonical vẫn là seed đầu 0, metadata không trộn references |
| AC03 | Khi R trống nhưng nodes có isolate, detector không tạo membership/chất lượng giả và metadata vẫn mô tả node hoạt động |
| AC04 | Khi input lỗi hoặc output tồn tại, thao tác thất bại rõ và không ghi đè run cũ |
| AC05 | Người nhận xác minh được dataset, tháng, protocol, gamma, seed và nguồn graph của membership qua metadata/hashes |

## Phụ thuộc và ngoài phạm vi

Cần ít nhất graph stable của 002 để chạy đầu tiên; có thể viết adapter bằng fixture trước khi suite sáu case hoàn chỉnh. Không cần tracker Đăng. Không thay Leiden bằng thuật toán mới hoặc sửa ordering/protocol Reddit để phục vụ giả lập.

## Output và kiểm chứng độc lập

- Dùng `src/reddit_sna/detection/leiden.py`; caller tích hợp trong API detection của pipeline, không tạo cây source riêng.
- Artifact: `memberships/<month>/membership-seed*.csv`, `detection.json`, metadata references.
- Test dự kiến: `tests/integration/test_synthetic_detection.py`, gọi thật graph nhỏ, kiểm tra refs/endpoint/empty/output cũ.
- Evidence: lệnh/API, run/dataset ID, paths và diagnostics thực tế. Modularity/seed ARI chỉ là diagnostics, không phải độ đúng xã hội hay accuracy dự báo.
- T01 đã có [API/hướng dẫn](README.md) và [bằng chứng](../evidence/PHUC-003-T01-leiden-adapter.md): gọi detector thật seed 0/gamma 1 trên stable, 57 test liên quan pass, membership/diagnostics/ZIP đã lưu. Đây là bước đầu; lịch ba seed, mapping/persistence và nghiệm thu toàn spec vẫn thuộc T02–T06.
- T02 đã có [bằng chứng lịch detector](../evidence/PHUC-003-T02-detector-schedule.md): đọc runtime config, chạy 0/1/2/canonical 0, 61 test liên quan pass, sáu membership mỗi run và seed ARI được lưu. T03–T06 còn persistence/mapping, bộ lỗi/dependency và nghiệm thu cohort đầy đủ.
- T03 đã có [gói detection và bằng chứng](../evidence/PHUC-003-T03-detection-package.md): exporter lưu diagnostics/config/metadata và mapping dataset–tháng–seed–reference/path/hash; 66 test liên quan pass, hai gói stable và gói relocated đọc lại bằng stdlib. Mapping này định danh file, chưa matching cộng đồng truth/prediction. T04–T06 còn bộ lỗi/dependency và nghiệm thu integration/cohort đầy đủ.
