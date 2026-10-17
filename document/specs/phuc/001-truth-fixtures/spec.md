# PHUC-001 — Truth và fixture để bắt đầu độc lập

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P01.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-001). **Giao diện:** [contracts.md](../contracts.md).

## Mục tiêu và user story

**US1, P1:** Là Đăng, tôi nhận được membership chuẩn và sự kiện của stable/grow để phát triển tracker ngay, không phải chờ graph, detector hoặc kết quả Reddit.

Phúc có thể tự nghiệm thu fixture bằng contract validator; xác nhận Đăng đã nhận/đọc được là một ghi nhận bàn giao riêng.

## Yêu cầu

- **PHUC-001-FR01:** Tạo thành viên stable/grow qua hai tháng theo contract; nhóm nền K ổn định và đích chính đổi tên.
- **PHUC-001-FR02:** CSV đúng header/khóa/tháng/reference; mỗi node hoạt động có đúng một membership chuẩn; user nhất quán trong dataset.
- **PHUC-001-FR03:** Events/links xuất từ kịch bản trước thuật toán, mỗi nguồn một nhãn; nhóm nền có nhãn; tháng cuối không tự gán dissolve.
- **PHUC-001-FR04:** Export có metadata, cấu hình, phiên bản và seed, không ghi đè; đủ để bên khác đọc lại mà không import notebook.
- **PHUC-001-FR05:** Môi trường project chạy được import và test detector hiện có; evidence ghi interpreter/versions, lệnh, pass/skip/error thực tế.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Với stable, khi đọc hai tháng theo user ID, tập thành viên nguồn và đích bằng nhau dù tên nhóm khác; event là stable |
| AC02 | Với grow, đích có 18 user gồm trọn 12 user nguồn và 6 mới; event là grow; K vẫn stable |
| AC03 | Khi duplicate khóa hoặc membership user lạ/thiếu, validator báo lỗi rõ, không âm thầm sửa |
| AC04 | Khi export cùng cấu hình vào hai output mới, nội dung dữ liệu tương đương/tái lập; output cũ được giữ nguyên |
| AC05 | Một chương trình đọc CSV độc lập dựng lại được các tập thành viên và events; có record môi trường chạy thực |

## Phạm vi và edge cases

Chưa cần sinh cạnh hay viết tracker trong spec này. Kiểm tra reference bị trộn, month sai định dạng, user chỉ xuất hiện tháng sau và thiếu successor. Dữ liệu tổng hợp không chứa user/text Reddit thật.

## Output và kiểm chứng độc lập

- Module: `benchmarks/scenarios.py`, `benchmarks/io.py`, CLI `benchmarks/fixtures.py`; fixture được sinh bằng code, không nhập nhãn dự đoán thủ công.
- Artifact: `truth/{membership,events,links}.csv`, `metadata.json`, danh sách node/cấu hình theo contract.
- Test dự kiến: `tests/unit/test_synthetic_truth.py`; kiểm tra tập hợp thành viên, keys, links và tái lập.
- Evidence task phải có đường dẫn fixture, lệnh sinh/đọc lại và kết quả kiểm tra. Không cần phản hồi Đăng để chứng minh contract tự kiểm tra đã chạy; không tự ghi Đăng accepted.
- [Hướng dẫn export và đọc độc lập](README.md) dùng config truth riêng và `scripts/read_truth_fixture.py` chỉ phụ thuộc stdlib. Nghiệm thu T06 có [bằng chứng export](../evidence/PHUC-001-T06-export.md).
