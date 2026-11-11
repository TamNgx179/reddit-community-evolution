# Rubric review nhãn cộng đồng — v1.1 đã xác nhận

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | `1.1` |
| Trạng thái | **`frozen_v1.1` cho lượt chấm độc lập** |
| Nguồn nội dung | Đề xuất của Tâm ngày 03/11/2026, được Tâm xác nhận áp dụng trong tin nhắn chuyển ngày 04/11/2026 |
| Soạn thành tài liệu | Phúc với trợ giúp AI |
| Phạm vi hiện tại | Rà pilot và chấm riêng 60 ca reviewer 1/reviewer 2; pilot không tính vào 60 ca chính |
| Mốc khóa hướng dẫn | Tâm đã xác nhận dùng v1.1 ngày 04/11/2026; điều phối lưu thời điểm chat gốc nếu cần |
| Phiếu người thật đã khóa | Chưa được xác nhận trong cuộc trao đổi này |

Tài liệu này văn bản hóa đề xuất của Tâm. Bản nháp AI trước đó không phải nhãn chuẩn hoặc phiếu độc lập của Phúc. Không đổi nhãn máy, reference hay metric của thí nghiệm dự báo bằng các quyết định review này.

## 1. Đang chấm điều gì?

Chọn sự kiện của **nhóm nguồn `source-0` từ tháng t sang t+1**, dựa trên cấu trúc và bằng chứng quan sát được. Không kết luận một nhóm xã hội ngoài đời đã hình thành hoặc biến mất.

Đọc membership, topology tiền nhiệm/kế nhiệm, cạnh liên quan và quan sát thành viên. HTML là phần xem trước; JSON.gz giữ đầy đủ dữ liệu được bàn giao. Có thể dùng thống kê tính từ toàn bộ payload để hỗ trợ đọc, nhưng phải giữ nguồn và ghi việc dùng công cụ/AI.

Không chọn nhãn để khớp quota chọn mẫu, nhãn máy, prediction hoặc bản gợi ý của người khác. `unresolved` là một kết quả hợp lệ, không phải ca cần ép thành một trong sáu sự kiện.

## 2. Ba tình huống theo đề xuất của Tâm

| Tình huống | Cách xử lý v1.1 |
|---|---|
| Không còn thành viên trong graph và không có bài/bình luận tháng sau | Chọn **dissolve trong mạng quan sát** nếu dữ liệu hai tháng đầy đủ, đúng phạm vi và bộ lọc. Nếu tháng sau thiếu dữ liệu hoặc chưa xác định được mức quan sát, chọn **unresolved**. Không diễn giải thành nhóm ngoài đời biến mất. |
| Nhóm nhỏ còn đủ thành viên nhưng nằm trong một nhóm rất lớn | Không kết luận chỉ từ kích thước. Chọn **grow** khi có bằng chứng tiếp nối một–một rồi bổ sung thành viên. Chọn **merge** khi nhóm đích tiếp nhận nhiều nhóm tiền nhiệm có đóng góp thành viên rõ ràng. Nếu mới thấy nhóm nhỏ “lọt vào” nhóm lớn mà chưa phân biệt hai cơ chế, chọn **unresolved**. |
| Thành viên phân tán sang nhiều nhóm lớn | Chỉ chọn **split** khi có ít nhất hai nhánh kế tiếp với bằng chứng tiếp nối rõ về thành viên và tương tác. Vài thành viên rơi rải rác vào các nhóm lớn chưa đủ chứng minh split; khi đó chọn **unresolved** và ghi lý do. |

Điểm quan trọng: **không có hoạt động của thành viên** và **không đủ dữ liệu để quan sát hoạt động** là hai tình huống khác nhau. v1.1 không bắt buộc chuyển mọi ca không hoạt động thành unresolved; phải xem điều kiện về dữ liệu trước.

## 3. Kiểm tra điều kiện dữ liệu trước khi gán dissolve

Reviewer ghi điều kiện này ở checklist hoặc metadata phụ, không cần đổi schema phiếu gốc:

| Kiểm tra | Bằng chứng cần có |
|---|---|
| Hai tháng đúng và có thể quan sát | Tháng t và t+1 tồn tại trong phạm vi bàn giao; phân biệt tháng cuối bị censored với một tháng có dữ liệu nhưng không thấy nhóm kế tiếp. |
| Đúng phạm vi | Cùng corpus/cohort, quy tắc người dùng và định nghĩa graph; không nối token giữa các ca độc lập. |
| Đúng bộ lọc | Nguồn hoặc metadata xác nhận các bộ lọc tương ứng, không coi thay đổi bộ lọc là cộng đồng tan rã. |
| Không thiếu/truncated evidence liên quan | Có đầy đủ membership, các nhánh liên quan và thông tin quan sát theo giao diện gói; các chỗ thiếu phải được ghi nhận. |
| Nguồn xác nhận điều kiện quan sát | Metadata không lộ nhãn hoặc xác nhận phạm vi từ điều phối. Ghi file/trường hoặc lời xác nhận nào được dùng. Không mở answer key hay snapshot chứa nhãn để tìm xác nhận. |

Dùng ba trạng thái `confirmed`, `not_confirmed`, `unknown` cho điều kiện phạm vi quan sát. Đây là ghi chú bằng chứng, không phải một loại sự kiện mới.

- `confirmed`: có nguồn xác nhận điều kiện cần thiết; vẫn phải đánh giá xem có tiếp nối cấu trúc hay không.
- `not_confirmed`: biết dữ liệu thiếu hoặc phạm vi/bộ lọc không tương ứng.
- `unknown`: bằng chứng hiện có chưa xác định được điều kiện đó.

Nếu không còn người trong graph/không có authored record và trạng thái điều kiện dữ liệu là `not_confirmed` hoặc `unknown`, ghi `unresolved`, nêu rõ điều còn thiếu. Đọc được file, CRC đúng và overlap nhất quán chỉ xác nhận tính hợp lệ/nội bộ của gói; **chưa tự chứng minh dữ liệu hai tháng đầy đủ, đúng phạm vi và bộ lọc**.

## 4. Định nghĩa các nhãn

Các định nghĩa dưới đây đọc cùng ba tình huống ở mục 2 và hướng dẫn gốc trong [LABEL_REVIEW](LABEL_REVIEW.md).

| Nhãn | Bằng chứng cần có |
|---|---|
| `stable` | Có tiếp nối một–một hợp lý và bằng quy mô nhóm nguồn. |
| `grow` | Có tiếp nối một–một hợp lý, sau đó nhóm đích lớn hơn. Không dùng riêng việc target lớn để suy ra grow. |
| `shrink` | Có tiếp nối một–một hợp lý, sau đó nhóm đích nhỏ hơn. Không dùng riêng việc vài thành viên không xuất hiện để suy ra shrink. |
| `merge` | Nhóm đích tiếp nhận nhiều tiền nhiệm hợp lý, có đóng góp thành viên rõ ràng; giải thích vai trò của nguồn đang được chấm. |
| `split` | Có ít nhất hai nhánh successor với bằng chứng tiếp nối rõ về thành viên và tương tác; không chỉ đếm số nhóm lớn chứa vài người nguồn. |
| `dissolve` | Không còn bằng chứng tiếp nối hợp lý trong mạng quan sát và điều kiện dữ liệu/phạm vi/bộ lọc cho kết luận đó đã xác nhận. Chỉ có nghĩa cấu trúc quan sát một bước. |
| `unresolved` | Thiếu bằng chứng, mức quan sát chưa rõ, liên hệ yếu, nhiều cơ chế cạnh tranh hoặc không phân biệt được sự kiện theo hướng dẫn chung. Ghi lý do cụ thể. |

Không có nhãn birth cho một nhóm nguồn đã tồn tại. Censored là trạng thái quan sát cần ghi riêng; không ép thành dissolve. Nếu gói ca không có tháng đích cần thiết, ghi thiếu bằng chứng và báo điều phối thay vì tự cho rằng danh sách target rỗng là censored.

### Đọc tiếp nối một–một và topology

Xem cả hai chiều: nhóm nguồn giữ được những ai, phần nào của target đến từ nguồn, các nhóm tiền nhiệm khác đóng góp ra sao, có successor thay thế không và cạnh tương tác hỗ trợ cách nối nào. Không quyết định chỉ từ một số như 100% giữ lại hoặc kích thước tăng mạnh.

Với nhiều tiền nhiệm và nhiều kế nhiệm có các cách diễn giải cạnh tranh, có thể chọn unresolved và mô tả các nhánh. Không bê thứ tự ưu tiên split/merge hoặc các ngưỡng của tracker thành đáp án bắt buộc của reviewer. v1.1 này không tự thêm ngưỡng overlap, dung sai kích thước hoặc ngưỡng “đóng góp rõ ràng” theo những ca đã xem.

## 5. Ghi một quyết định như thế nào?

Giữ nguyên các cột phiếu bàn giao: `case_id`, `label`, `confidence`, `rationale`. Nếu gói có cột định danh reviewer, giữ cột đó theo đúng vai trò. Ghi thêm phạm vi quan sát, nguồn dẫn và điểm mơ hồ trong rationale/checklist/metadata phụ thay vì sửa phiếu gốc.

Mỗi quyết định phải chứa:

1. **Bằng chứng:** thành viên chung, quy mô, topology, cạnh và quan sát cần thiết. Dẫn nhóm hoặc file thực tế, không chỉ ghi “theo cảm nhận”.
2. **Nhãn và lý do:** vì sao bằng chứng hỗ trợ sự kiện được chọn; với unresolved, nói rõ thiếu gì hoặc có hai cách hiểu nào.
3. **Mức tin tưởng:** `high`, `medium` hoặc `low`.
4. **Điểm còn mơ hồ:** ghi ngay cả khi đã chọn một nhãn resolved. Độ tin tưởng thấp không thay thế việc kiểm tra điều kiện dữ liệu của dissolve.

| Confidence | Cách sử dụng |
|---|---|
| `high` | Bằng chứng rõ và phù hợp hướng dẫn, ít cách giải thích cạnh tranh đáng kể. |
| `medium` | Có căn cứ cho quyết định nhưng còn giới hạn hoặc một phần topology/quan sát cần thận trọng. |
| `low` | Quyết định còn nhiều bất định; nếu không đủ chọn giữa các sự kiện thì dùng unresolved và nêu lý do. |

Confidence mô tả mức tin tưởng của người chấm vào quyết định, không phải xác suất đúng đã được hiệu chuẩn. Với unresolved, ghi rõ đang chắc về việc thiếu bằng chứng hay chỉ còn phân vân.

## 6. AI, tính độc lập và phiếu gốc

- Phúc ghi rõ đã được cung cấp/xem nhãn gợi ý AI, cùng bản nào đã dùng. Không mô tả là chấm hoàn toàn không có hỗ trợ.
- Phúc và Đăng vẫn có thể chấm độc lập **với nhau** khi không trao đổi quyết định từng ca trước khi nộp. Trao đổi định nghĩa chung được phép; trao đổi nhãn ca cụ thể trước khi khóa sẽ làm thay đổi mức độc lập và phải ghi exposure.
- Không gửi bản nhãn AI/pilot riêng của Phúc cho Đăng như đáp án cần theo. Nếu ai đã thấy một bản gợi ý hoặc quyết định, ghi thực tế đó.
- Nhãn do AI thực hiện lưu riêng với `reviewer_type=automated`; không ghi thành phiếu người thật, không dùng để tạo human agreement.
- Reviewer giữ bản gốc, làm trên bản riêng. Điều phối khóa **cả hai phiếu** và giữ hash/thời điểm nộp thật trước khi mở nhãn máy hoặc snapshot coverage có nhãn.
- Followup nhiều tháng chỉ dùng ở giai đoạn sau khi khóa lượt một bước, lưu riêng; không sửa âm thầm câu trả lời đầu tiên.

## 7. Version, khóa hướng dẫn và rà lại ca

Tâm đã xác nhận dùng ba nguyên tắc trong tài liệu này cho lượt chấm độc lập ngày 04/11/2026. Vì vậy version dùng cho bộ chính là `frozen_v1.1`. Điều này **không** có nghĩa phiếu của Phúc hoặc Đăng đã nộp/đã khóa; điều phối chỉ mở nhãn máy và snapshot coverage sau khi nhận đủ hai phiếu nguyên bản, checksum và thời điểm nộp.

Biên bản điều phối vẫn cần ghi thực tế vào bảng sau:

| Mục | Giá trị hiện tại |
|---|---|
| Tâm xác nhận áp dụng hướng dẫn | Có — tin nhắn chuyển ngày 04/11/2026 |
| Phúc xác nhận/khóa phiếu riêng | Pending |
| Đăng xác nhận/khóa phiếu riêng | Pending |
| Điều kiện quan sát của gói đã được giải thích | Pending evidence hoặc dẫn xác nhận thực tế |
| Phiên bản được dùng cho bộ chính | `frozen_v1.1` |
| SHA-256 của mỗi phiếu đã khóa | Chờ điều phối tính sau khi nhận đủ hai phiếu |
| Ngày/giờ nộp, người ghi | Chờ thời điểm nộp thật của từng reviewer |

Sau khi rà pilot và thống nhất, mới ghi ngày khóa và chấm 60 ca chính. Không tự điền chữ ký, ngày đồng ý hay thời điểm nộp hộ người khác.

Nếu sửa rubric sau đó, lưu phiên bản mới và lý do, liệt kê những ca bị ảnh hưởng, giữ phiếu cũ và rà lại các ca đó. Kết quả AI cũ cũng giữ nguyên phiên bản; không ghi đè để trông như ban đầu đã dùng v1.1.

Không dùng answer key để chọn giữa các cách diễn giải hoặc thay hướng dẫn cho khớp nhãn máy. Pilot giúp làm rõ quy trình, không được cộng vào 60 ca kiểm chứng chính. Review này không tự xác nhận toàn dataset hoặc tính mới của phương pháp.
