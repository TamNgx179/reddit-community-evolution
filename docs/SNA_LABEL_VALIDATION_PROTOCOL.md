# Protocol kiểm chứng nhãn chuyển tiếp cộng đồng

Trạng thái: bản thiết kế để nhóm khóa trước khi lấy mẫu. Kết quả dưới đây dựa trên nhãn cấu trúc của mạng reply Reddit theo tháng.

## Câu hỏi và bằng chứng

Câu hỏi chính là khi nào sự vắng mặt, phân tán hoặc tiếp nối của thành viên đủ để kết luận một chuyển tiếp cấu trúc. GED dùng mức độ bao hàm theo hai hướng dựa trên thành viên và tầm quan trọng. Các snapshot chỉ ghi nhận từng lần quan sát của mạng. Tách độ quan sát, tiếp nối cấu trúc và nhãn sự kiện là lựa chọn thiết kế của nhóm từ các ca đã rà. [GED](https://link.springer.com/article/10.1007/s13278-012-0058-8), [Greene và cộng sự](https://derekgreene.com/papers/greene10tracking.pdf).

Đã tái tạo đúng 11.745 nhãn frozen từ inclusion pairs và kích thước cộng đồng. Giữ nguyên graph và thay một ngưỡng mỗi lần. Ngưỡng nối 0,45 và 0,55 làm đổi 15 và 63 ca. Ngưỡng dissolve 0,05 làm 623 ca dissolve chuyển unresolved. Ngưỡng 0,15 làm 352 ca đổi chiều ngược lại. Coverage tương ứng là 59,39%, 64,78% ở mốc gốc và 67,83%. Đây là độ nhạy của định nghĩa nhãn, chưa xác định ngưỡng nào đúng hơn. [Bảng độ nhạy](../reports/tables/sna-feedback-20261111/ged_threshold_sensitivity.csv).

## Rubric đề xuất cho lượt mới

Phiếu ghi mã ca, mức quan sát, số nhánh tiếp nối có bằng chứng, nhãn, độ tin cậy và lý do. Dữ liệu thiếu được ghi rõ theo từng trường.

| Bước | Quy tắc |
| --- | --- |
| Quan sát | Xem snapshot t+1 có đủ theo phạm vi đã khai báo. Phân biệt số thành viên cũ có bài/bình luận, có reply edge và nằm trong partition. Ba số có thể khác nhau. Snapshot thiếu thì ghi censored ngoài lượt chấm. Nếu snapshot có nhưng không quan sát được thành viên nào, chọn unresolved do thiếu quan sát theo rubric đề xuất này. |
| Tiếp nối | Dùng overlap và cạnh giữa chính thành viên cũ trong từng target. Một thành viên đơn lẻ trong target chỉ cho thấy sự hiện diện. Với nhóm nhỏ, một cạnh giữa hai thành viên cũ có thể là bằng chứng tối thiểu để xem xét, còn nhãn cuối cần cân nhắc độ bao phủ và các target cạnh tranh. Ghi lý do khi bằng chứng mâu thuẫn. |
| Split | Cần ít nhất hai target có bằng chứng tiếp nối. Nếu mỗi target giữ một cá nhân, ghi phân tán thành viên và xét dissolve hoặc unresolved theo mức quan sát. |
| Merge | Cần ít nhất hai nhóm nguồn có đóng góp tiếp nối có thể kiểm tra trong cùng target. Khi chỉ biết overlap của nhóm nguồn thứ hai, chọn unresolved nếu bằng chứng chưa đủ phân biệt merge với nhập chung do partition. |
| Grow, shrink, stable | Một target trội có tiếp nối, kiểm tra các nguồn và đích cạnh tranh. Sau đó mới so kích thước nhóm. |
| Dissolve, unresolved | Chọn dissolve trong phạm vi mạng quan sát khi có đủ bằng chứng rằng cấu trúc cũ không tiếp nối. Nếu quan sát yếu hoặc bằng chứng không phân biệt được các nhãn, chọn unresolved và ghi lý do. |

Hiệu chỉnh cách hiểu bằng 4–6 ca đã công bố, nhất là zero-observation và singleton dispersal. Khóa phiên bản rubric sau calibration và trước khi phát bộ mới. Calibration đứng ngoài phép tính agreement.

## Thiết kế và nghiệm thu

1. **Panel mới.** Mục tiêu khả thi là 30–36 ca chẩn đoán từ tối thiểu sáu tháng development, gồm tracker dissolve có/thiếu quan sát, unresolved, và các ca đối chứng có tiếp nối. Dùng seed khóa trước, phân bổ ít nhất hai nhóm kích thước khi dữ liệu cho phép. Loại toàn bộ khóa và ca có bằng chứng đã công bố mà nhóm kiểm tra được. Lưu số ứng viên và số chọn mỗi tầng ở phía điều phối.
2. **Gói reviewer.** Cả hai nhận cùng dữ liệu và hai phiếu trống riêng. Bằng chứng gồm số người xuất hiện, overlap từng target, cạnh nội bộ hiện tại và tháng sau, cạnh còn giữ, và bằng chứng của nguồn cạnh tranh nếu cần phân biệt merge. Dùng mã ca riêng, bỏ nhãn tracker, predictions và mã community gốc. Nếu thiếu bằng chứng cần thiết, phiếu ghi unresolved kèm lý do.
3. **Khóa phiếu.** Hai người khác nhau chấm riêng. Ghi người thực hiện, phiên bản rubric, thời gian và prior exposure. Kiểm tra đủ khóa, giữ file gốc và SHA-256, sau đó mới ghép hai phiếu và mở khóa tracker. Người điều phối giữ phân xử thành bản riêng.
4. **Phân tích.** Báo ma trận nhãn, raw agreement, κ danh nghĩa, số ca theo nhãn và nhóm quan sát. Hai phiếu đầy đủ là điều kiện dùng κ trên toàn panel. Nếu có phiếu thiếu, báo thiếu và dùng α danh nghĩa như phép kiểm bổ sung khi phù hợp. Agreement đo khả năng áp dụng rubric nhất quán. Tracker concordance và các lý do bất đồng trả lời câu hỏi riêng. Panel phân tầng phục vụ chẩn đoán. [Krippendorff, Computing Alpha](https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf).

## Quyết định về mô hình

Giữ kết quả dự báo chính của Midterm 2 theo label reference frozen. Dùng độ nhạy GED và review để xác định nơi nhãn phụ thuộc quan sát. Nếu nhóm định nghĩa một label reference mới, khóa quy tắc trên development rồi tạo lại nhãn, split và baseline nhất quán. Báo coverage của mỗi phiên bản và báo điểm trên phần giao chung bên cạnh kết quả theo từng phạm vi.

Ứng viên dùng lịch sử có điều kiện chưa đạt tiêu chí ở cohort đối chiếu 286 ca. Đợt tiếp theo chỉ kiểm tra một thay đổi có giả thuyết rõ sau khi khóa đích, phạm vi và tiêu chí đánh giá. Nếu dùng bằng chứng t+1 để xác định chất lượng nhãn, giữ trường đó ở phía tạo nhãn và audit. Feature dự báo chỉ dùng thông tin đến t.
