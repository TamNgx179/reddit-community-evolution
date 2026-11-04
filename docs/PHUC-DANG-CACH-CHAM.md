# Cách chấm Phúc đề xuất để Phúc và Đăng dùng chung

**Ngày soạn: 04/11/2026. Người chủ động chọn hướng dẫn: Phúc, với trợ giúp AI.**

Phúc chọn [rubric v1.1 theo đề xuất của Tâm](REVIEW-RUBRIC-V1.1.md) làm hướng dẫn làm việc và đề nghị Đăng áp dụng cùng bản. Tài liệu này diễn giải thành các bước thực hiện; không thêm ngưỡng, không thay định nghĩa sự kiện và không phải bộ đáp án. Đăng đã nhận/đồng ý dùng chưa: **chưa có xác nhận**. Phiên bản chung cho bộ chính và ngày khóa sẽ ghi theo thực tế sau pilot.

## 1. Việc hai bạn đang làm

Nhìn một nhóm ở tháng này và bằng chứng tháng sau, rồi trả lời: **nhóm đó thay đổi như thế nào?**

- `source-0`: nhóm đang cần nhận xét.
- `target`: một nhóm tháng sau có thành viên chung với nhóm nguồn.
- Tiền nhiệm: nhóm ở tháng này đóng góp người vào một nhóm tháng sau.
- Tiếp nối: có căn cứ về thành viên, các nhóm liên quan và tương tác để coi nhóm sau là sự tiếp tục của nhóm trước.
- `rubric`: bộ quy tắc chấm; `pilot`: 6 ca thử; bộ chính: 60 ca riêng.

Phúc chấm gói reviewer 1. Đăng chấm gói reviewer 2. Cùng cách chấm nhưng mỗi người tự quyết định từng ca.

## 2. Mỗi ca làm theo sáu bước

1. **Xác định đúng ca:** đọc `case_id`, tháng nguồn, tháng đích và nhóm nguồn. Thiếu tháng đích hoặc thiếu file thì ghi chỗ thiếu; không tự xem đó là nhóm tan rã.
2. **Đọc bằng chứng:** đếm người nguồn, người còn ở graph tháng sau, người có bài/bình luận tháng sau, các nhóm đích và số thành viên chung. HTML chỉ xem trước; dùng thống kê từ JSON.gz đầy đủ khi cần.
3. **Nhìn các nhóm liên quan:** nhóm đích có nhận người từ nhóm cũ nào khác không? Nhóm nguồn còn đi sang các nhóm đích nào? Có cạnh tương tác hỗ trợ mối tiếp nối không? Một người xuất hiện ở đầu mút cạnh không đồng nghĩa người đó có authored record trong tháng.
4. **Kiểm tra điều kiện quan sát:** có nguồn xác nhận phạm vi, bộ lọc và dữ liệu hai tháng không? Ghi `confirmed`, `not_confirmed` hoặc `unknown` trong ghi chú. File đọc được chưa chứng minh đủ dữ liệu. Nếu kết luận dựa trên việc không quan sát được hoạt động mà điều kiện này chưa rõ, giữ unresolved theo v1.1.
5. **Chọn nhãn bằng bảng dưới:** nếu có nhiều cách diễn giải cạnh tranh và chưa đủ phân biệt, chọn `unresolved`, ghi rõ lý do. Không ép một nhãn chỉ để điền đủ bảng.
6. **Ghi mức tin tưởng và lý do:** dẫn số liệu/nhóm/cạnh thực tế, giải thích vì sao chọn nhãn đó và điểm còn mơ hồ. Ca khó vẫn được ghi unresolved rồi tiếp tục ca khác.

## 3. Bảng chọn nhãn

| Nhãn điền vào phiếu | Khi nào dùng? | Chỗ dễ nhầm |
|---|---|---|
| `stable` | Có tiếp nối một–một hợp lý và quy mô bằng nhóm nguồn. | Cùng số người nhưng khác thành viên chưa chứng minh tiếp nối. |
| `grow` | Có tiếp nối một–một hợp lý, nhóm kế tiếp lớn hơn. | Nhóm đích lớn chưa đủ; có thể là hợp nhất hoặc chỉ chứa vài người nguồn. |
| `shrink` | Có tiếp nối một–một hợp lý, nhóm kế tiếp nhỏ hơn. | Mất quan sát vài người chưa đủ chứng minh nhóm đã thu nhỏ. |
| `merge` | Một nhóm đích tiếp nhận nhiều nhóm tiền nhiệm hợp lý, có đóng góp thành viên rõ. | Không chỉ đếm có bao nhiêu nhóm chạm vào một nhóm rất lớn. |
| `split` | Có ít nhất hai nhánh tiếp nối rõ, được hỗ trợ bởi thành viên và tương tác. | Vài người rơi rải rác vào các nhóm lớn chưa đủ gọi tách. |
| `dissolve` | Không còn tiếp nối hợp lý trong mạng quan sát; điều kiện dữ liệu/phạm vi/bộ lọc đã được xác nhận. | Nếu không thấy người/hoạt động mà mức quan sát chưa rõ thì unresolved. Không kết luận nhóm ngoài đời biến mất. |
| `unresolved` | Thiếu bằng chứng, liên hệ yếu, mức quan sát chưa rõ hoặc không phân biệt được các cơ chế. | Đây là câu trả lời hợp lệ, phải ghi cụ thể thiếu gì. |

Đọc toàn bộ bằng chứng trước khi chọn. Thứ tự các dòng không phải thứ tự ưu tiên nhãn; không lấy thứ tự/ngưỡng của tracker làm đáp án bắt buộc. Không thêm nhãn birth cho một nhóm nguồn đang tồn tại. Trạng thái censored do thiếu tháng quan sát cần ghi riêng, không đổi thành dissolve.

## 4. Điền phiếu thế nào?

Giữ phiếu gốc, tạo bản làm việc riêng. Giữ các cột được bàn giao, trong đó có:

| Cột | Nội dung |
|---|---|
| `case_id` | Mã ca, giữ nguyên. |
| `label` | Một trong bảy nhãn ở bảng trên. |
| `confidence` | `high`: bằng chứng rõ; `medium`: có căn cứ nhưng còn giới hạn; `low`: còn nhiều bất định. |
| `rationale` | Bằng chứng, cách diễn giải và điểm còn mơ hồ. |

Mẫu ghi lý do, thay các chỗ trong ngoặc bằng dữ liệu thực tế:

> Nhóm nguồn có [N] người; tháng sau quan sát [K] người trong graph và [A] người có authored record. Các nhóm kế tiếp liên quan là [tên nhóm và số người chung]. Em chọn [nhãn] vì [bằng chứng tiếp nối/thiếu bằng chứng]. Điều kiện quan sát là [trạng thái và nguồn dẫn]. Điểm còn mơ hồ: [nêu cụ thể].

Confidence là mức tin tưởng vào quyết định, không phải điểm dự đoán của mô hình. Với unresolved, nói rõ đang tin rằng bằng chứng chưa đủ hay đang phân vân giữa những cách giải thích nào.

## 5. Chia việc và cách bàn giao

| Người | Làm ngay | Đầu ra |
|---|---|---|
| **Phúc** | Chủ động cung cấp hướng dẫn này; rà pilot reviewer 1; hỏi Tâm metadata quan sát không lộ nhãn; ghi rõ trợ giúp AI đã dùng. | Phiếu làm việc reviewer 1 đúng nguồn người/AI, ghi chú thiếu bằng chứng; không gửi nhãn riêng cho Đăng trước khi khóa. |
| **Đăng** | Tải `pilot-reviewer_2.zip` và checksum riêng từ Release; dùng hướng dẫn này để rà 6 ca; ghi chỗ quy tắc khó hiểu. | Phiếu làm việc reviewer 2 riêng và phản hồi về cách hiểu hướng dẫn. |
| **Tâm / điều phối** | Giải thích phạm vi/bộ lọc của gói bằng metadata không lộ nhãn; nhận phiếu thực nộp và giữ bản gốc. | Nguồn xác nhận quan sát, bản hướng dẫn/version được ghi nhận sau pilot, hash và thời điểm khóa thực tế. |

Gói tải tại [GitHub Releases](https://github.com/TamNgx179/reddit-community-evolution/releases), draft “Midterm 2 frozen team handoff - 3 November 2026”. [Kế hoạch Phúc](PHUC-WEEK3-WEEK4.md) có lệnh tải và kiểm tra checksum reviewer 2. `scripts/prepare_phuc_review.py` chỉ dùng cho reviewer 1; Đăng giải nén gói riêng và giữ phiếu gốc.

Thống nhất cách hiểu chung sau pilot rồi ghi phiên bản dùng cho 60 ca chính. Mỗi người chấm bộ chính riêng. Khóa cả hai phiếu trước khi mở nhãn máy, prediction, followup hoặc snapshot coverage có nhãn. Sau đó mới tính agreement và xử lý bất đồng, giữ riêng bản gốc và bản sau đối chiếu. Nếu sửa quy tắc, lưu phiên bản mới và rà lại ca bị ảnh hưởng.

Phúc đã xem gợi ý AI. Nhãn do AI chọn phải giữ provenance automated; việc nhờ AI làm không tự trở thành phiếu người thật. Hai người có thể làm độc lập với nhau khi không trao đổi nhãn từng ca trước khi khóa và ghi đúng exposure thực tế.

## 6. Tin nhắn Phúc có thể gửi Đăng

> Ông ơi, tui chủ động chọn cách chấm theo bản v1.1 Tâm gửi nha. Tui viết lại từng bước ở đây cho dễ làm: https://github.com/TamNgx179/reddit-community-evolution/blob/codex/phuc-week3-coverage-review/docs/PHUC-DANG-CACH-CHAM.md . Ông dùng cùng bản này, lấy `pilot-reviewer_2.zip` với checksum trên Release rồi làm 6 ca thử trước nha. Chỗ quy tắc nào chưa rõ thì báo đúng chỗ đó để mình chỉnh trước bộ 60 ca. Hai đứa giữ phiếu riêng, chưa gửi nhãn từng ca cho nhau; xong nộp riêng cho Tâm rồi mới so kết quả. Tui có dùng gợi ý AI và sẽ khai rõ phần đó. Phần nào thiếu bằng chứng thì ghi unresolved cùng lý do, không cần cố đoán nha.

Tin nhắn trên là bản soạn sẵn, chưa được gửi tự động. Việc Phúc chọn bản làm việc không được ghi thành Đăng đã đồng ý hoặc hai phiếu đã khóa.
