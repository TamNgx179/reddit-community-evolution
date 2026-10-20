# Báo cáo Tuần 1 — Hệ thống mô hình tham chiếu (baseline) cho bài toán dự báo sự kiện tiến hóa cộng đồng

**Đề tài:** B.6 — How Online Communities Change Over Time (IS353.R11, Nhóm 2)
**Phạm vi báo cáo:** nhánh dự báo (`prediction`) trong Tuần 1, do Nguyễn Thị Ngọc Trâm và Mai Lan Anh thực hiện
**Lần chạy làm căn cứ số liệu:** `week1-merged-001` (seed 42, dữ liệu synthetic `synthetic-v1`)

---

## Phần 1. Quá trình thực hiện, logic thiết kế và đặc điểm của từng module

### 1.1. Vị trí của phần việc trong đề tài và lý do dùng dữ liệu synthetic

Đề tài nghiên cứu sự tiến hóa của các cộng đồng trực tuyến theo thời gian. Ở nhánh dự báo, bài toán được phát biểu như sau: với mỗi cộng đồng tại tháng *t*, dựa trên thông tin có được đến hết tháng *t*, dự báo sự kiện xảy ra ở tháng *t+1*, thuộc một trong sáu lớp: `stable`, `grow`, `shrink`, `merge`, `split`, `dissolve`. Mục tiêu của Tuần 1 không phải là đạt độ chính xác cao, mà là thiết lập các mô hình tham chiếu và một quy trình thực nghiệm đáng tin cậy, để các mô hình phức tạp hơn ở những tuần sau được so sánh trên cùng một nền tảng.

Bảng đặc trưng cộng đồng theo tháng từ dữ liệu Reddit thật phụ thuộc vào ba khâu do các thành viên khác thực hiện song song: dựng đồ thị tương tác, phát hiện cộng đồng và theo dõi tiến hóa cộng đồng. Vì vậy ở Tuần 1, nhóm chủ động xây dựng một bảng dữ liệu tổng hợp (synthetic) có cấu trúc trùng khớp với hợp đồng dữ liệu đã thống nhất (14 cột, sáu lớp nhãn, khóa mẫu gồm `reference_id`, `feature_month`, `community_id`). Cách làm này có hai ý nghĩa phương pháp luận. Thứ nhất, toàn bộ quy trình từ sinh mẫu, chia dữ liệu, huấn luyện, dự đoán đến đánh giá được kiểm chứng trên dữ liệu có cơ chế sinh đã biết, nên sai sót của quy trình có thể được tách khỏi sai sót do dữ liệu thật. Thứ hai, khi bảng đặc trưng thật sẵn sàng, chỉ nguồn dữ liệu đầu vào cần thay đổi, còn các bước phía sau giữ nguyên. Cần nhấn mạnh rằng mọi số liệu trong báo cáo này phản ánh khả năng của mô hình trên dữ liệu tổng hợp, không phải khả năng dự báo trên Reddit.

### 1.2. Sinh bảng dữ liệu tổng hợp (`community_table.py`)

Bảng được sinh cho 36 tháng, gồm 1570 dòng, mỗi dòng là một cặp (cộng đồng, tháng) với 14 cột. Mỗi cộng đồng mang một trạng thái nội tại gồm quy mô, mật độ liên kết, mức tương hỗ, xu hướng tăng trưởng riêng và tăng trưởng của tháng trước. Tốc độ tăng trưởng mỗi tháng được tạo bằng công thức `g = mu + 0.5 × g_prev + N(0, 0.12)`, tức là gồm xu hướng riêng của cộng đồng, một thành phần quán tính từ tháng trước và nhiễu ngẫu nhiên. Nhãn của tháng kế tiếp được xác định theo thứ tự ưu tiên `dissolve` → `split` → `merge` → (`grow` / `shrink` / `stable` theo ngưỡng 0,15 của `g`), sau đó 5% số dòng được gán nhãn ngẫu nhiên (`label_noise = 0.05`).

Nhóm thiết kế như vậy vì nhãn cần có quan hệ thống kê thật sự với đặc trưng (để mô hình có thể học), nhưng không được xác định hoàn toàn bởi đặc trưng (để bài toán không tầm thường). Thành phần quán tính 0,5 × `g_prev` cố ý tạo ra sự phụ thuộc giữa nhãn liên tiếp, cho phép kiểm tra giả thuyết rằng thông tin lịch sử nhãn có giá trị dự báo. Ba ràng buộc bảo đảm tính hợp lệ của thực nghiệm:

- **Không rò rỉ thông tin tương lai.** Mọi đặc trưng tại tháng *t* chỉ được tính từ thông tin đến hết tháng *t*; bảng không chứa đại lượng nào thuộc *t+1*.
- **Không có đường dò theo định danh.** `community_id` chỉ là mã cục bộ được hoán vị trong từng tháng, không nối được một cộng đồng qua các tháng, nên mô hình không thể khai thác định danh để suy ra nhãn.
- **Tháng cuối không có nhãn.** Các dòng có `feature_month = 2017-12` (46 dòng) không có tháng kế tiếp nên nhãn rỗng và bị loại khỏi huấn luyện và đánh giá.

Trong quá trình kiểm thử, nhóm phát hiện cột `size_tm1` (quy mô tháng trước) ban đầu được gán sau khi quy mô đã cập nhật, khiến `size_tm1` bằng `size_t` và `growth_rate` luôn bằng 0. Lỗi được sửa và bổ sung kiểm thử hồi quy; kiểm thử này được xác nhận là thất bại khi cố tình đưa lại lỗi cũ.

### 1.3. Chia dữ liệu và kiểm tra mẫu (`splits.py`, `sample_checks.py`)

Dữ liệu được chia theo tháng của nhãn (`label_month`) chứ không chia ngẫu nhiên theo dòng: tập huấn luyện gồm 23 tháng (2015-02 đến 2016-12, 1000 dòng), tập kiểm định gồm 6 tháng (2017-01 đến 2017-06, 263 dòng), tập kiểm tra gồm 6 tháng (2017-07 đến 2017-12, 261 dòng). Chia theo thời gian phản ánh đúng tình huống ứng dụng, trong đó mô hình học từ quá khứ để dự báo tương lai; chia ngẫu nhiên sẽ cho phép thông tin của các tháng sau xuất hiện trong huấn luyện và làm kết quả bị thổi phồng.

Trước khi huấn luyện, bảng mẫu qua 16 kiểm tra tự động (đủ cột, không trùng khóa, nhãn hợp lệ, không có đặc trưng khả dụng ở *t+1*, tính hợp lệ của phép chia, v.v.), tất cả đều đạt. Trong quá trình rà soát chéo, nhóm nhận thấy kiểm tra chống rò rỉ ban đầu chỉ bắt đúng chuỗi `t+1` và chỉ xác nhận tập huấn luyện có ít nhất hai lớp. Bốn kiểm tra bổ sung đã được thêm vào: giá trị nhãn tập hợp hợp lệ; khóa của phép chia trỏ đúng vào các dòng có nhãn; ba tập không chồng lấn về thời gian; và cột `available_at` của danh mục đặc trưng chỉ nhận thời điểm không muộn hơn *t*.

### 1.4. Ba mô hình tham chiếu (`majority_persistence.py`, `logistic_regression.py`)

Ba mô hình được chọn để lần lượt đo ba mức thông tin: không dùng gì, chỉ dùng nhãn tháng trước, và dùng đặc trưng quy mô có chuẩn hóa.

**B1_majority** luôn dự báo lớp phổ biến nhất của tập huấn luyện (`stable`). Mô hình này không dùng thông tin đầu vào nào và đóng vai trò mức sàn: mọi mô hình có ý nghĩa phải vượt qua nó trên chỉ số macro-F1.

**B1_persistence** dự báo sự kiện của tháng *t+1* bằng đúng nhãn đã quan sát của tháng trước (`prev_label`). Khi cộng đồng chưa có nhãn tháng trước (tháng đầu tiên), mô hình quay về Majority và đánh dấu `used_fallback`. Đây là mô hình tham chiếu đo mức độ quán tính của nhãn.

**B4_logreg** là hồi quy logistic đa lớp trên năm đặc trưng `size_t`, `size_tm1`, `size_tm2`, `age_months`, `growth_rate`. Các lựa chọn thiết kế đáng lưu ý gồm: bộ chuẩn hóa `StandardScaler` chỉ được học trên tập huấn luyện để không rò rỉ thống kê của tập kiểm định và kiểm tra; `class_weight = balanced` để các lớp hiếm không bị lấn át; khi một đặc trưng bị thiếu, mô hình quay về Majority; và `prev_label` cố ý không được dùng, nhằm tách bạch giá trị của đặc trưng quy mô với giá trị của lịch sử nhãn đã được đo ở B1_persistence. Lỗi phát sinh khi huấn luyện B4 được truyền lên chứ không bị che bằng mô hình khác, để kết quả không bị thay thế ngầm.

### 1.5. Pipeline tích hợp và khả năng tái lập (`prediction.py`)

Pipeline nối các bước thành một lệnh duy nhất: sinh bảng, chia dữ liệu, kiểm tra mẫu, huấn luyện chỉ trên tập huấn luyện, dự báo trên cả ba tập, và tính chỉ số. Mọi lần chạy đều ghi một tệp `manifest.json` gồm seed, phiên bản mã nguồn (git revision, trạng thái sạch hay không), phiên bản thư viện, trạng thái từng giai đoạn và mã băm của từng tệp kết quả, nhờ đó kết quả có thể được kiểm chứng và tái lập. Trạng thái được ghi là `complete_through_baselines`, cố ý không dùng `complete`, vì các mô hình còn lại của kế hoạch chưa hoàn thành và báo cáo không được khẳng định vượt quá bằng chứng hiện có.

### 1.6. Chỉ số đánh giá (`metrics.py`)

Chỉ số chính là **macro-F1**, tính bằng trung bình không trọng số của F1 từng lớp. Lựa chọn này xuất phát từ sự mất cân bằng của dữ liệu: lớp `stable` chiếm khoảng 50,9% số dòng có nhãn (775/1524), nên một mô hình chỉ dự báo `stable` đạt độ chính xác (accuracy) trên 50% nhưng hoàn toàn không phát hiện được năm lớp còn lại. Macro-F1 phạt trực tiếp tình trạng đó. Báo cáo bổ sung `balanced_accuracy`, ma trận nhầm lẫn và chỉ số theo từng lớp, đồng thời ghi tỉ lệ dòng phải dùng fallback để người đọc biết bao nhiêu dự báo không đến từ cơ chế chính của mô hình.

---

## Phần 2. Đầu ra hiện có, phân tích kết quả và đánh giá chuyên môn

### 2.1. Các tệp đầu ra và mối liên hệ giữa chúng

Toàn bộ kết quả của lần chạy `week1-merged-001` nằm trong `artifacts/prediction/week1-merged-001/`. Các tệp được tổ chức thành năm nhóm theo vai trò trong chuỗi thực nghiệm.

| Nhóm | Tệp | Vai trò |
|---|---|---|
| Dữ liệu và phép chia | `samples.csv` (1570 dòng, 14 cột), `feature_catalog.csv`, `split.csv`, `split_summary.csv` | Dữ liệu đầu vào, danh mục đặc trưng cùng thời điểm khả dụng, gán từng mẫu vào tập huấn luyện/kiểm định/kiểm tra, thống kê số dòng mỗi tập |
| Cấu hình và mô hình | `baseline_config.json`, `model_B4.joblib` | Tham số của ba mô hình và mô hình B4 đã huấn luyện |
| Dự báo | `predictions.csv` (4572 dòng = 3 mô hình × 1524 mẫu có nhãn) | Nhãn thật, nhãn dự báo, cờ `used_fallback` và xác suất (B4) cho từng mẫu |
| Đánh giá | `metrics.csv`, `per_class.csv`, 9 tệp `confusion_<mô hình>_<tập>.csv`, `evaluation_notes.md` | Chỉ số tổng, chỉ số theo lớp, ma trận nhầm lẫn của 3 mô hình trên 3 tập, ghi chú diễn giải |
| Bằng chứng tái lập | `manifest.json` | Seed, git revision, thư viện, trạng thái giai đoạn, mã băm tệp |

Chuỗi liên kết như sau: `samples.csv` và `split.csv` xác định phần dữ liệu mỗi mô hình được phép thấy; `baseline_config.json` và `model_B4.joblib` cố định mô hình; `predictions.csv` là nguồn gốc duy nhất từ đó `metrics.csv`, `per_class.csv` và các ma trận nhầm lẫn được tính; `manifest.json` neo toàn bộ chuỗi vào một phiên bản mã nguồn và một seed. Khi báo cáo, nhóm đề xuất dùng các số liệu sau: phân bố nhãn và kích thước ba tập (từ `split_summary.csv`), macro-F1 và `balanced_accuracy` trên kiểm định và kiểm tra (`metrics.csv`), F1 và recall theo lớp trên tập kiểm tra (`per_class.csv`), tỉ lệ fallback (`predictions.csv`). Các số liệu trên tập huấn luyện chỉ mang tính nội suy (in-sample) và không dùng để kết luận.

### 2.2. Đặc điểm dữ liệu

Bảng có 1570 dòng, trong đó 1524 dòng có nhãn và 46 dòng của tháng cuối bị loại vì không có nhãn. Phân bố nhãn: `stable` 775 (50,9%), `grow` 253, `shrink` 232, `merge` 103, `dissolve` 89, `split` 72. Dữ liệu vì vậy mất cân bằng rõ rệt: một lớp chiếm một nửa, ba lớp hiếm (`merge`, `dissolve`, `split`) cộng lại chỉ chiếm khoảng 17%. Trên tập kiểm tra (261 dòng), số mẫu của các lớp lần lượt là `stable` 133, `grow` 46, `shrink` 37, `merge` 22, `dissolve` 14, `split` 9. Với chỉ 9 mẫu `split`, việc dự báo đúng thêm một mẫu làm recall của lớp này thay đổi khoảng 11 điểm phần trăm; điều này cần được tính đến khi diễn giải các lớp hiếm.

### 2.3. So sánh ba mô hình trên chỉ số tổng hợp

| Mô hình | Macro-F1 (kiểm định) | Macro-F1 (kiểm tra) | Balanced accuracy (kiểm tra) | Tỉ lệ fallback (kiểm tra) |
|---|---|---|---|---|
| B1_majority | 0,1169 | 0,1125 | 0,1667 | 0% |
| B1_persistence | 0,2575 | 0,2557 | 0,2586 | 4,98% |
| B4_logreg | 0,2291 | 0,2160 | 0,2155 | 11,49% |

Hai nhận xét chính. Thứ nhất, cả B1_persistence và B4_logreg đều vượt B1_majority khoảng gấp đôi, xác nhận rằng thông tin lịch sử (nhãn tháng trước hoặc đặc trưng quy mô) có giá trị dự báo trên dữ liệu này, còn B1_majority đúng như vai trò mức sàn. Thứ hai, thứ hạng giữa các mô hình nhất quán giữa kiểm định và kiểm tra (B1_persistence > B4_logreg > B1_majority), cho thấy kết quả không phụ thuộc vào việc chọn tập đánh giá. Khoảng cách giữa B4_logreg và B1_persistence trên tập kiểm tra là 0,0397.

### 2.4. Kết quả theo từng lớp và ma trận nhầm lẫn (tập kiểm tra)

| Lớp (số mẫu) | F1 của B1_persistence | F1 của B4_logreg |
|---|---|---|
| stable (133) | 0,6246 | 0,5405 |
| grow (46) | 0,4318 | 0,3218 |
| shrink (37) | 0,3889 | 0,2796 |
| merge (22) | 0,0889 | 0 |
| split (9) | 0 | 0,1538 |
| dissolve (14) | 0 | 0 |

**B1_majority** chỉ dự báo `stable`, nên recall của `stable` là 1 và của năm lớp còn lại bằng 0; macro-F1 thấp (0,1125) dù độ chính xác của nó khoảng 51%, đúng bằng tỉ lệ lớp `stable`.

**B1_persistence** mạnh ở ba lớp thường xuyên (`stable` 0,6246, `grow` 0,4318, `shrink` 0,3889). Cơ chế là quán tính đã được cài trong dữ liệu: tăng trưởng tháng này phụ thuộc vào tăng trưởng tháng trước nên nhãn tháng trước là chỉ báo tốt cho nhãn tháng sau. Ngược lại, recall của `split` và `dissolve` bằng 0. Đối với `dissolve` có một lý do mang tính cấu trúc: cộng đồng đã giải thể thì không xuất hiện ở tháng kế tiếp nên không có mẫu nào có `prev_label = dissolve`, và quy tắc "lặp lại nhãn cũ" không thể dự báo lớp này. Đối với `split`, nhãn tháng trước hầu như không báo trước một sự kiện tách, nên quy tắc cũng thất bại; giải thích này là giả thuyết, chưa được kiểm chứng riêng.

**B4_logreg** thấp hơn B1_persistence ở các lớp thường xuyên nhưng là mô hình duy nhất bắt được một phần lớp `split` (F1 = 0,1538), trong khi recall của `merge` và `dissolve` bằng 0. Điều này phù hợp với việc `class_weight = balanced` dịch chuyển ranh giới quyết định từ lớp `stable` sang các lớp hiếm: B4 đánh đổi độ chính xác ở lớp đa số để có thêm khả năng phát hiện lớp hiếm, nhưng với năm đặc trưng quy mô thì tín hiệu phân biệt `merge` và `dissolve` chưa đủ. Về tổng thể, B4 thấp hơn B1_persistence 0,0397 điểm macro-F1. Nhóm đưa ra hai giả thuyết, chưa tách riêng từng nguyên nhân: (i) B4 không sử dụng `prev_label`, trong khi nhãn tháng trước là thông tin mạnh vì cơ chế sinh có tính quán tính; (ii) B4 phải dùng fallback ở 11,49% mẫu kiểm tra (so với 4,98% của B1_persistence) do thiếu `size_tm1` hoặc `size_tm2` ở các cộng đồng mới, và các dự báo fallback đều quy về `stable`.

**Minh họa bằng dự báo cụ thể.** Xét tháng nhãn 2017-06 (tháng cuối của tập kiểm định, gồm 44 cộng đồng có `feature_month = 2017-05`). B1_majority dự báo `stable` cho cả 44 cộng đồng; trong đó 29 cộng đồng thực sự `stable` nên đúng, còn 15 cộng đồng còn lại sai, thuộc đủ năm lớp khác: `shrink` 5 (ví dụ `c0023`, `c0008`), `grow` 5 (ví dụ `c0024`, `c0030`, `c0000`), `merge` 3 (`c0018`, `c0013`, `c0040`), `split` 1 (`c0034`) và `dissolve` 1 (`c0038`). Độ chính xác trong tháng này là 29/44 (khoảng 66%), nhưng không sự kiện thay đổi nào được phát hiện: đây là hình ảnh cụ thể của việc accuracy cao có thể đi kèm macro-F1 thấp. Cũng vì vậy, `balanced_accuracy` của B1_majority trên tập kiểm tra chỉ là 0,1667, đúng bằng 1/6, tức mức của một mô hình không phân biệt được lớp nào.

Các ca sai của B1_persistence và B4_logreg được liệt kê trong mục phân tích lỗi của `progress.md`; khi trình bày nên chọn một ca của mỗi mô hình để minh họa các cơ chế nêu trên.

### 2.5. Đánh giá: giá trị đạt được và giới hạn

**Những gì Tuần 1 đã chứng minh.**
Thứ nhất, quy trình thực nghiệm chặt chẽ và tái lập được: phép chia theo thời gian, bộ chuẩn hóa chỉ học trên tập huấn luyện, 16 kiểm tra mẫu đều đạt (kể cả các kiểm tra chống rò rỉ được bổ sung), và toàn bộ kết quả neo vào một seed và một phiên bản mã nguồn sạch (`git dirty = false`). Thứ hai, bộ ba mô hình tham chiếu cho thứ hạng nhất quán và giải thích được, cung cấp mức so sánh cụ thể cho các mô hình sau: ngưỡng cần vượt trên tập kiểm tra là macro-F1 khoảng 0,26 (B1_persistence). Thứ ba, các hạn chế của từng mô hình đã được định vị rõ, chủ yếu ở các lớp hiếm.

**Giới hạn hiện tại.**
Dữ liệu là synthetic, nhãn được sinh theo quy tắc do nhóm đặt ra nên điểm số chỉ cho biết mô hình nắm bắt quy tắc đó đến mức nào, chưa cho phép kết luận về Reddit. Tập kiểm tra nhỏ (261 dòng, lớp `split` chỉ 9 mẫu), nên chênh lệch nhỏ giữa các mô hình chưa đủ cơ sở thống kê chắc chắn; chưa có khoảng tin cậy hoặc lặp lại theo nhiều seed. Mới có ba mô hình tham chiếu; B4 chưa dùng `prev_label`; các nguyên nhân ở mục 2.4 mới là giả thuyết.

**Hướng chuyển giao sang Tuần 2.**
Chuẩn bị đầu vào thật cho nhánh dự báo bằng cách thay bảng synthetic bằng bảng đặc trưng cộng đồng–tháng từ dữ liệu Reddit, giữ nguyên hợp đồng dữ liệu và chuỗi đánh giá. Bổ sung các mô hình còn lại của kế hoạch (B2, B5, HeTCo) để so sánh với mốc B1_persistence. Về phương pháp, bổ sung lặp lại theo nhiều seed và khoảng tin cậy cho macro-F1, và thử biến thể B4 có `prev_label` để tách riêng hai giả thuyết ở mục 2.4.
