# PHUC-005 — Development/evaluation và lượt chạy tái lập

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P06.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-005). **Giao diện:** [contracts.md](../contracts.md).

**Triển khai hiện tại:** T01–T05 DONE, PHUC-005 **5/6 DOING**. Full development 18 dataset/36 snapshot/108 metrics (99 valid/9 null), canonical AMI mean 0.955879927; freeze đã tạo sau development từ clean source `d4fe76b`, config/policy không đổi. **T05 40/40 targeted tests pass**, không chạy lại full suite; 314/314 là lượt T03. Source/config/report/versions, ba independent consumer logs, CSV/ZIP và freeze reference đã lưu. [Hướng dẫn](README.md), [T05](../evidence/PHUC-005-T05-development-freeze.md), [T04](../evidence/PHUC-005-T04-acceptance.md). AC01–03 pass, phần khóa AC05 đã có; full schedule AC04 và evaluation verification AC05 còn T06.

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

- `configs/benchmark_week1.json` giữ graph recipe schema 1; `configs/benchmark_week1_protocol.json` binding hash/policy/expected counts cho đường chạy mới, loader trong `benchmarks/protocol.py`. API detection trong `pipelines/detection_tracking.py`, quản lý artifacts được dùng lại khi phù hợp.
- Artifact: config khóa, manifests, dataset ledger, metrics/summary và log kiểm tra hashes/tái lập.
- Tests hiện có: `tests/integration/test_synthetic_benchmark_run.py` (22 tests), `tests/unit/test_run_provenance.py` (1 test), `tests/integration/test_benchmark_freeze.py` (7 tests T05); kiểm tra orchestration/failure/no-overwrite/provenance/concurrent run ID và freeze gating. Suite nghiên cứu chạy riêng.
- T05 bổ sung `benchmarks/freeze.py`: tạo/verify freeze run riêng sau full development, archive source/config/policy và development evidence; gate source/versions và audit metadata trước evaluation. [Hướng dẫn](README.md#chạy-đủ-development-và-tạo-bản-khóa--t05), [bằng chứng](../evidence/PHUC-005-T05-development-freeze.md). T06 driver ngoài frozen package ghi source/hash riêng, sử dụng module và archived protocol đã khóa.
- Evidence: development run, thời điểm/config freeze, evaluation run, expected/actual counts, exclusions/failures và nguồn chạy. Chưa đo bộ nhớ ghi null.
