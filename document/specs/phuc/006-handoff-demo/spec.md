# PHUC-006 — Bàn giao, notebook và demo

**Owner phần cá nhân:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P07.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-006). **Giao diện:** [contracts.md](../contracts.md).

**Hiện tại:** T01–T02 DONE, PHUC-006 **2/6**, tổng Phúc **32/36**. [Consumer stdlib](../../../../src/reddit_sna/reporting/synthetic_handoff.py) có 25 unit tests mới; 51/51 targeted tests pass ở T01. Đã kiểm tra đủ hai source run PHUC-005 (36 dataset/72 snapshot/216 membership CSV), hai cặp index sau relocation giống byte. T02 có [hướng dẫn bàn giao](../../../PHUC-DANG-WEEK1-HANDOFF.md), ZIP dữ liệu 821 files/956.285 byte và lệnh CLI/API đã thử sau giải nén; [reference](../evidence/PHUC-006-T02-delivery-reference.json), [bằng chứng T02](../evidence/PHUC-006-T02-handoff-guide.md). **AC01 phần consumer đạt**; hướng dẫn môi trường/lệnh FR03 đã có, clean install/kernel/notebook và AC02–AC04 còn T03–T06. Tracker/receipt/review Đăng chưa có evidence. [Hướng dẫn consumer](README.md), [bằng chứng T01](../evidence/PHUC-006-T01-inventory.md).

## Mục tiêu và user story

**US1, P1:** Là thành viên nhóm, tôi mở notebook/hướng dẫn để hiểu phần Phúc, tái tạo kết quả và nhận đúng gói dữ liệu cho tracker mà không hỏi lại ý nghĩa từng file.

**US2, P2, mốc chung:** Là Phúc–Đăng, chúng tôi ghép tracker trên truth và detector để phân tích hai nguồn lỗi. Mốc chung được theo dõi riêng ở task list, không gán việc viết tracker cho Phúc.

## Yêu cầu

- **PHUC-006-FR01:** Gói bàn giao có inventory, schema/version, run/dataset/reference, hash, cách đọc/tái tạo; xác nhận người nhận tách khỏi kiểm tra tự động.
- **PHUC-006-FR02:** Notebook import module package, chạy kernel sạch, hiển thị cấu hình, dữ liệu tổng hợp, metrics và hình có nguồn, không hardcode kết quả.
- **PHUC-006-FR03:** Có hướng dẫn môi trường/lệnh và bằng chứng test/clean-kernel replay; ghi lỗi/skip/giới hạn thực tế.
- **PHUC-006-FR04:** Có phân tích trường hợp khó/sai hoặc null result và phạm vi kết luận; không coi chart/test là bằng chứng novelty hay dự báo Reddit.
- **PHUC-006-FR05:** Tách rõ nghiệm thu Phúc và demo chung cần tracker, mapping, F1/confusion của Đăng; chưa có thì báo pending, không tạo số giả.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Từ manifest/inventory, một consumer độc lập xác minh membership keys, references, endpoint và file hashes; log có lệnh/kết quả |
| AC02 | Từ môi trường đúng và input được hướng dẫn, Restart Kernel -> Run All tái tạo/replay phần detection không cần biến cũ hoặc sửa sys.path |
| AC03 | Notebook chỉ rõ nguồn từng bảng/hình, AMI/coverage/timing và diagnostics; sample display không thay chỉ số graph đầy đủ |
| AC04 | Có ít nhất một case khó để phân tích bằng graph/truth/prediction; nếu không tìm thấy lỗi ở suite hiện tại, ghi null finding/giới hạn, không bịa lỗi |
| AC05 | Nếu Đăng chưa giao tracker, phần detection vẫn nghiệm thu được và mốc chung chưa accepted; nếu đã giao thì có hai nhánh A/B và kết quả Đăng thật |

## Phụ thuộc và ngoài phạm vi

Nghiệm thu phần detection cần kết quả 005; fixture có thể bàn giao sớm từ 001. Không viết Jaccard/GED/evaluator tracking thay Đăng, không tự gửi tin nhắn, push hoặc tạo issue online trong phạm vi tạo specs.

## Output và kiểm chứng độc lập

- Notebook: `notebooks/detection_tracking/01_synthetic_demo.ipynb`; hướng dẫn `document/PHUC-DANG-WEEK1-HANDOFF.md` dự kiến.
- Consumer dự kiến: `src/reddit_sna/reporting/synthetic_handoff.py`, đọc contract CSV/JSON bằng standard library, không gọi generator/detector để tự xác nhận output của producer; kiểm tra hành vi tại `tests/unit/test_synthetic_handoff.py`.
- Gói artifact có manifest/inventory, bản notebook thực thi và figures trong output mới; report được chọn để chia sẻ có record nguồn.
- Kiểm tra consumer/clean-kernel/test repo phù hợp; ghi version, commands, pass/skip/failure. Passing consumer không phải Đăng đã nhận.
- Phúc đóng các task cá nhân bằng bằng chứng thật; trạng thái mốc chung ở `tasks.md` không suy ra tự động từ checkbox Phúc.
