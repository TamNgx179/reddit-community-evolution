# Bàn giao phần Phúc — review nhãn và coverage

**Cập nhật:** 04/11/2026  
**Người phụ trách:** Phúc  
**PR theo dõi:** [#21](https://github.com/TamNgx179/reddit-community-evolution/pull/21)  
**Trạng thái tổng:** `rubric_frozen_human_forms_pending`

## 1. Phần Phúc đã hoàn thành

| Hạng mục | Bằng chứng | Trạng thái |
| --- | --- | --- |
| Rubric chung | `docs/REVIEW-RUBRIC-V1.1.md` ghi đúng ba tình huống Tâm đề xuất, nhãn `unresolved`, cách ghi evidence/confidence/ambiguity và quy tắc khai báo AI | Tâm đã xác nhận dùng `frozen_v1.1` ngày 04/11/2026 |
| Hướng dẫn phối hợp Phúc–Đăng | `docs/PHUC-DANG-CACH-CHAM.md` và `docs/PHUC-WEEK3-WEEK4.md` mô tả gói riêng, thứ tự pilot → khóa phiếu → main → coverage | Hoàn thành |
| Kiểm tra gói reviewer 1 | Pilot 6/6 ca và main 60/60 ca có cấu trúc/evidence nội bộ đọc được. Audit main kiểm tra thêm 181 liên kết HTML cục bộ | Hoàn thành về mặt kỹ thuật |
| Bản đánh giá bổ trợ tự động | Có 60/60 ca cùng provenance, source hash và lý do. Toàn bộ ghi `reviewer_type=automated` | Hoàn thành, **không phải** phiếu người thật |
| Mở coverage snapshot | Chưa mở | Đúng quy trình, chờ khóa hai phiếu độc lập |

Các artifact cục bộ được giữ ở `artifacts/review/` và không commit dữ liệu/nhãn vào Git. Các thư mục liên quan là `phuc-pilot-audit-20261103-001`, `phuc-main-audit-20261104-001` và `phuc-main-assisted-20261104-001`.

## 2. Điều chưa thể tự chốt

Không thể gọi 60 kết quả tự động là lượt chấm của Phúc, hoặc tự tạo phiếu của Đăng. Hai việc đó sẽ làm sai ý nghĩa của kiểm tra độc lập. Cũng chưa có bằng chứng mới trên GitHub cho thấy Đăng đã nộp reviewer 2 hoặc Tâm đã khóa rubric v1.1.

Vì vậy các trạng thái sau vẫn là `pending`:

| Việc | Chủ sở hữu | Điều kiện hoàn thành |
| --- | --- | --- |
| Lưu xác nhận rubric | Tâm / điều phối | Đã xác nhận dùng `frozen_v1.1`; giữ tin nhắn gốc và version tài liệu |
| Phiếu reviewer 1 | Phúc | Người chấm xác nhận nhãn, confidence, rationale và exposure cho 60 ca |
| Phiếu reviewer 2 | Đăng | Nộp gói riêng, không xem nhãn reviewer 1 hay bản AI của Phúc trước khi khóa |
| Agreement và xử lý bất đồng | Phúc–Đăng, Anh hỗ trợ đánh giá | Chỉ mở hai phiếu sau khi cả hai đã khóa |
| Coverage và liên kết với graph thật | Phúc, sau khi khóa phiếu | Mở snapshot có nhãn máy, chạy coverage theo từng reference và ghi giới hạn quan sát |

## 3. Cách bàn giao để không bị rối

1. Phúc và Đăng dùng đúng ZIP riêng trên Draft Release `Midterm 2 frozen team handoff - 3 November 2026` và rubric `frozen_v1.1`.
2. Mỗi người lưu worksheet gốc không sửa và một bản làm việc riêng có `label`, `confidence`, `rationale`, `evidence` và `exposure`.
3. Mỗi người nộp nguyên phiếu đã khóa cho Tâm. Không gửi quyết định từng ca qua chat cho nhau.
4. Tâm ghi ngày khóa rubric và ngày nhận hai phiếu. Khi đó mới chạy agreement, đọc machine labels/follow-up hoặc mở coverage snapshot.
5. Nếu thiếu thông tin về phạm vi, bộ lọc hay độ đầy đủ của tháng sau, dùng `unresolved` thay vì suy diễn `dissolve`.

## 4. Nội dung có thể gửi Tâm ngay

> Tâm ơi, phần Phúc đã xong phần kỹ thuật: rubric `frozen_v1.1`, hướng dẫn phối hợp, audit pilot 6/6 và main 60/60, trong đó main có 181 link HTML cục bộ đọc được. Mình cũng có một bản đánh giá **tự động** 60/60 được lưu riêng với provenance, không ghi thành phiếu người thật và không gửi cho Đăng để giữ độc lập. Mình sẽ nộp reviewer_1.csv cùng thời điểm nộp và khai báo AI; Đăng nộp reviewer_2.csv riêng. Sau khi Tâm nhận đủ, lưu nguyên bản và checksum, mình mới chạy agreement và coverage theo đúng quy trình.

## 5. Giới hạn cần nói rõ khi bàn giao

- Audit ZIP chỉ chứng minh cấu trúc gói và evidence cục bộ đọc được. Nó không chứng minh dữ liệu Reddit đầy đủ, nhóm ngoài đời đã biến mất hay nhãn máy là đúng.
- Bản tự động hỗ trợ rà soát kỹ thuật. Nó không tạo human agreement, không thay thế reviewer và không phải social ground truth.
- Coverage chưa chạy trên snapshot có nhãn máy để không làm lộ thông tin trước lượt chấm độc lập.
