# PHUC-005 — Development/evaluation và lượt chạy tái lập

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P06.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-005). **Giao diện:** [contracts.md](../contracts.md).

## Mục tiêu và user story

**US1, P1:** Là người review, tôi tái tạo được lượt benchmark, biết tham số được khóa lúc nào và phân biệt đầu ra thật với run mới started hoặc bị lỗi.

Spec này chạy riêng phần detection; không cần tracker/F1 sự kiện của Đăng để đánh dấu phần Phúc hoàn thành.

## Yêu cầu

- **PHUC-005-FR01:** Lịch case/seed, config gamma/probabilities, policy thiếu dữ liệu và protocol được lưu/version; development/evaluation tách dataset/seed.
- **PHUC-005-FR02:** Có API chạy từ config đến graph/detection/metrics, không phụ thuộc notebook state hoặc tracker; completion nói rõ chỉ đến detection evaluation.
- **PHUC-005-FR03:** Run ID mới, manifest đủ input/config/source/output hashes, môi trường, stage state, timing, lỗi; không overwrite run hay data gốc.
- **PHUC-005-FR04:** Khóa cấu hình trước evaluation; bảo toàn dữ liệu lỗi/điểm thấp, seed canonical không thay, thay đổi sau khi xem holdout được công khai.
- **PHUC-005-FR05:** Có kiểm tra tái lập và lịch chạy, bảng đầy đủ/trạng thái thiếu; không coi seed detector là dataset độc lập hoặc claim kết quả Reddit.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Chưa có tracker Đăng, API vẫn chạy được từ input tổng hợp tới metrics detection; full core/tracking không bị báo complete |
| AC02 | Khi run lỗi giữa chừng, manifest ghi failed/stage, artifact đã có được giữ; không tạo kết quả giả để đủ số hàng |
| AC03 | Khi chạy cùng config/seed ở output mới và môi trường phù hợp, dữ liệu/partition được so dưới đổi tên nhóm; timing/timestamp không bắt buộc giống |
| AC04 | Với lịch cơ bản đầy đủ, có 36 dataset, 72 snapshot, 216 đơn vị snapshot × detector seed, development/evaluation riêng; mọi thiếu/lỗi có record |
| AC05 | Config evaluation có bản khóa và nguồn revision; summary và artifact hash đối chiếu được; không đọc nhãn/điểm giữ lại để chọn seed thắng |

## Phụ thuộc và phạm vi

Nghiệm thu cần 002–004 và truth từ 001. Có thể viết orchestration/config trước khi mọi module xong. Không cần phát triển CLI mới nếu API/notebook được hướng dẫn rõ; không chỉnh TOML parser ngoài phạm vi chỉ để nhận cấu hình tùy ý.

Nếu rút lịch do thời gian/tài nguyên, phải quyết định và version trước evaluation, ghi lý do và số lượt kỳ vọng mới; không tự đạt AC04 bằng cách âm thầm bỏ dataset. Mức khó bổ sung có thống kê riêng với lịch cơ bản.

## Output và kiểm chứng độc lập

- `configs/benchmark_week1.json`; API detection trong `pipelines/detection_tracking.py`, quản lý artifacts được dùng lại khi phù hợp.
- Artifact: config khóa, manifests, dataset ledger, metrics/summary và log kiểm tra hashes/tái lập.
- Test dự kiến: `tests/integration/test_synthetic_benchmark_run.py`; một dataset nhỏ đủ kiểm tra orchestration/failure/no-overwrite. Suite nghiên cứu chạy riêng.
- Evidence: development run, thời điểm/config freeze, evaluation run, expected/actual counts, exclusions/failures và nguồn chạy. Chưa đo bộ nhớ ghi null.
