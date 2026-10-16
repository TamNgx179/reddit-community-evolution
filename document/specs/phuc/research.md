# Nghiên cứu cách tổ chức specs và tiến độ

**Đối chiếu ngày:** 16/10/2026. Chỉ sử dụng nguồn chính thức của GitHub/Spec Kit cho cách tổ chức; yêu cầu nghiệp vụ lấy từ repo và phân công hiện tại.

## 1. Nguồn và điều áp dụng

| Nguồn chính thức | Điều rút ra | Áp dụng trong repo |
|---|---|---|
| [GitHub Spec Kit: spec template](https://github.com/github/spec-kit/blob/main/templates/spec-template.md) | Yêu cầu có kịch bản sử dụng, điều kiện chấp nhận và kết quả đo được | Mỗi spec có user story, requirement ID, acceptance scenarios, edge cases |
| [GitHub Spec Kit: plan template](https://github.com/github/spec-kit/blob/main/templates/plan-template.md) | Tách yêu cầu khỏi cách triển khai và cấu trúc source | Một `plan.md` chung vì sáu phần cùng một package và pipeline |
| [GitHub Spec Kit: tasks template](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md) | Task có mã, đường dẫn cụ thể, thứ tự phụ thuộc và điểm kiểm tra từng phần | Một `tasks.md` chung, nhóm theo spec, liên hệ requirement và artifact |
| [GitHub Projects: best practices](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects) | Chia nhỏ công việc, chỉ rõ trách nhiệm, dùng thông tin tiến độ và tránh nhiều nguồn trạng thái lệch nhau | Một bảng tiến độ ở task list; README chỉ dẫn tới bảng, không sao chép trạng thái |
| [GitHub Issues: dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies) | Biểu diễn rõ việc nào phụ thuộc việc nào | Graph phụ thuộc và mục “cần Đăng” riêng; không chặn toàn bộ Phúc vì thiếu tracker |

Không sao chép toàn bộ template hoặc chạy lệnh trong các tài liệu nguồn. Các file hiện tại là bản thiết kế phù hợp đồ án nhỏ; chưa triển khai GitHub Projects, Issues, CLI Spec Kit hay đồng bộ tự động.

## 2. Quyết định tổ chức

| Quyết định | Lý do | Phương án chưa dùng |
|---|---|---|
| Sáu spec theo đầu ra P01–P07 | Mỗi phần có kết quả riêng để xem và kiểm tra; đủ nhỏ cho lịch 16–20/10 | Một spec khổng lồ chỉ có “hoàn thành phần Phúc” |
| Một plan và một task list | Cùng môi trường, source và giao diện; giảm việc cập nhật lặp | Mỗi spec một bộ tool/config/board riêng |
| Mã requirement và task riêng | Truy từ yêu cầu sang code, kiểm tra và run evidence | Chỉ ghi “đã làm 80%” mà không có bằng chứng |
| Tất cả task triển khai bắt đầu TODO | Lượt này tạo docs, chưa chạy benchmark hoặc triển khai code | Đánh DONE vì detector/thư mục đã có sẵn |
| Giao diện CSV có version, tham chiếu truth/detector riêng | Đăng đọc được dữ liệu và tránh ghép sai reference | Ghép bằng tên community hoặc sửa reference cho trùng |
| Theo dõi chờ tracker như điều kiện ghép chung | Phúc vẫn tự nghiệm thu detection và bàn giao | Gắn mọi spec của Phúc là blocked bởi Đăng |
| Ghi evidence tại từng task | Thành viên kiểm tra được kết quả sau khi thấy checkbox DONE | Checkbox hoàn thành không kèm đường dẫn/lệnh |

Đây là lựa chọn của bộ specs này dựa trên yêu cầu người dùng và repo, không phải các ngưỡng hay thủ tục bắt buộc do GitHub quy định.

## 3. Căn cứ nội bộ đã kiểm tra

- [Phân công chung](../../../PHAN-CONG-SNA-8-TUAN.md): Phúc sinh benchmark, chạy detector, tính AMI; tuần 1 các cặp độc lập.
- [Phân công cặp v1](../../PHAN-CONG-PHUC-DANG-TUAN-1.md): schema, sáu case, ngưỡng tracker, seed và lịch bàn giao.
- `src/reddit_sna/detection/leiden.py`: detector đã có; output mới, endpoint-only membership, seed canonical, diagnostics trả dictionary.
- `src/reddit_sna/contracts.py`: các record và sáu sự kiện đã có, không xác thực toàn bộ dataset/leakage.
- `src/reddit_sna/pipelines/detection_tracking.py`: vẫn chủ động báo chưa triển khai.
- `pyproject.toml`: graph/notebook extras đã có; scikit-learn chưa được khai báo tại thời điểm đọc.

Những kiểm tra này là source inspection. Chưa cài môi trường, chạy test detector hoặc thực thi thí nghiệm trong lượt tạo specs.
