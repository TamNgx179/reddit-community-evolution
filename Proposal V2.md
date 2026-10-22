# Mini ProposalA. Information

- **Project / Mã và Tên đề tài:** B.6 – How Online Communities Change Over Time
- **Course / Môn học:** IS353.R11
- **Duration / Thời gian thực hiện:** 09/2026 12/2026
- **Group / Nhóm**: 02 Nhóm 2
- **Members / Thành viên:**

1.  Nguyễn Văn Thanh, 23521456, 23521456@gm.uit.edu.vn
2.  Nguyễn Minh Tâm, 23521390, 23521390@gm.uit.edu.vn
3.  Nguyễn Thị Ngọc Trâm, 23521615, 23521615@gm.uit.edu.vn
4.  Mai Lan Anh, 23520052, 23520052@gm.uit.edu.vn
5.  Phan Đình Phúc, 23521216, 23521216@gm.uit.edu.vn
6.  Nguyễn Khắc Hải Đăng, 23520229, 23520229@gm.uit.edu.vn

- **Supervisor / Giảng viên hướng dẫn**: Trần Hưng Nghiệp, nghiepth@uit.edu.vn

### 
<br/>

## **1\. Experimental plan (proposal version 2)**

Dựng snapshot dị thể theo tháng, phát hiện community user, tạo nhãn tiến hóa và dự báo tại t+1. Kiểm chứng bằng baseline và ablation trên split thời gian.

- Platform-defined community: subreddit do nền tảng tạo sẵn. Subreddit chỉ được dùng làm ngữ cảnh và thuộc tính của user, không phải đối tượng cần phát hiện.
- SNA community: nhóm user có tương tác nội bộ dày hơn với bên ngoài. Đây là định nghĩa vận hành, không phải định nghĩa chung cho mọi mạng. Leiden tạo phân hoạch không chồng lấp nên có thể bỏ sót các nhóm xã hội chồng lấp.

Các snapshot theo tháng giữ cùng ánh xạ node, còn cạnh và thuộc tính thay đổi theo thời gian. Mỗi mẫu là một community ở tháng hiện tại, dùng để dự báo sự kiện tháng kế tiếp: giữ nguyên, tăng, giảm, hợp nhất, tách hoặc phân rã. Đầu vào chỉ dùng dữ liệu đã quan sát đến thời điểm dự báo.

Ba giả thuyết cần kiểm chứng. H1: ghép thời gian và consensus tăng độ ổn định mà vẫn giữ chất lượng cấu trúc (Experiment 2). H2: dùng dữ liệu sau mốc dự báo có thể làm điểm đánh giá cao hơn (Experiment 3). H3: thông tin dị thể và động lực thành viên tăng macro-F1 so với B5 (Experiment 4, A1/A4). Mục tiêu là dự báo nhóm thu hẹp hoặc phân rã. Kết quả chỉ mô tả hành vi trong corpus, không xác định nguyên nhân chính trị.

**1\. Dataset:**

- **Detailed stats table:** Nghiên cứu sử dụng dữ liệu ConvoKit từ 15 subreddit trong giai đoạn 01/2015–09/2018. Thông tin tác giả, thời gian và quan hệ trả lời cho phép xây dựng mạng tương tác theo tháng. Các bảng dưới đây trình bày quy mô dữ liệu và cách chia tập.

| Thành phần | Số lượng / tỷ lệ |
| --- | --- |
| Bản ghi | 19,731,802 |
| --- | --- |
| Post / Comment | 1,163,921 / 18,567,881 |
| --- | --- |
| User sau lọc / Subreddit | 594,099 / 15 |
| --- | --- |
| Cạnh User–Post / User–Comment | 963,062 / 16,124,144 |
| --- | --- |
| Comment trả lời Post / Comment | 5,078,004 / 13,489,876 cạnh |
| --- | --- |
| Lượt trả lời user–user | 14,766,168 |
| --- | --- |
| Cặp user–thread | 9,034,596 |
| --- | --- |
| Snapshot tháng | 45  |
| --- | --- |
| Comment thiếu bản ghi cha | 1 (<0.00001%) |
| --- | --- |
| User ở ≥2 subreddit | 30.6%, tạo 69.1% tổng bản ghi |
| --- | --- |

- Đồ thị gồm User, Post, Comment và Subreddit, với các cạnh User → writes → Post/Comment, Comment → replies_to → Post/Comment và Post → belongs_to → Subreddit. Leiden chạy trên hai phép chiếu user vô hướng có trọng số. Hướng tương tác được giữ cho đặc trưng reciprocity. Giữ metadata của bản ghi có tác giả bị loại để bảo toàn thread, nhưng không tạo node User cho các tác giả đó.
- Nguồn dữ liệu: ConvoKit Reddit Corpus theo subreddit (https://convokit.cornell.edu/documentation/subreddit.html). Thống kê user và cạnh không bao gồm tác giả không xác định, tài khoản đã xóa và AutoModerator. Chưa loại được đầy đủ các bot khác. Bản ghi thiếu liên kết cha hoặc sai thứ tự thời gian không được dùng để tạo cạnh trả lời. Mạng trả lời không tính self-loop.
- **Train / validation / test statistics:** Dữ liệu được chia theo thời gian. Mẫu “community tại t → sự kiện tại t+1” thuộc tập của tháng nhãn t+1.

| Chỉ số | Train | Validation | Test |
| --- | --- | --- | --- |
| Giai đoạn | 01/2015–06/2017 | 07/2017–12/2017 | 01/2018–09/2018 |
| --- | --- | --- | --- |
| Snapshot | 30  | 6   | 9   |
| --- | --- | --- | --- |
| Post | 880,488 | 120,924 | 162,509 |
| --- | --- | --- | --- |
| Comment | 14,692,458 | 1,709,126 | 2,166,297 |
| --- | --- | --- | --- |
| User có viết sau lọc | 471,498 | 127,475 | 144,043 |
| --- | --- | --- | --- |
| User mới trong tập | 471,498 | 53,167 | 69,434 |
| --- | --- | --- | --- |
| Lượt trả lời | 11,761,215 | 1,332,343 | 1,672,610 |
| --- | --- | --- | --- |

- Số snapshot không đồng nghĩa số mẫu dự báo. Sau tracking, thống kê số community–tháng, phân phối sáu lớp và tỷ lệ user mới cho từng tập. Báo cáo số mẫu và độ bất định cho từng lớp. Lớp quá ít mẫu hoặc không xuất hiện trong train/test chỉ được mô tả, không dùng để khẳng định hiệu quả. Giữ nguyên sáu nhãn, không gộp sau khi xem kết quả. Mẫu được chia theo tháng xảy ra sự kiện cần dự báo.
- **Detailed data pipeline:**
    1.  Tải corpus theo manifest của 15 subreddit: SandersForPresident, PoliticalDiscussion, Conservative, EnoughTrumpSpam, AskTrumpSupporters, hillaryclinton, socialism, AskThe_Donald, Political_Revolution, NeutralPolitics, democrats, Republican, AskALiberal, Ask_Politics và moderatepolitics. Kiểm tra checksum/kích thước và lưu bản gốc bất biến.
    2.  Chuyển JSONL sang Parquet, chuẩn hóa timestamp về UTC, tách namespace t3_ cho post và t1_ cho comment. Không lưu văn bản. Độ dài lúc thu thập chỉ là trường phụ trợ, chưa được duyệt làm đặc trưng biết tại t.
    3.  Kiểm tra ID trùng, timestamp thiếu, liên kết cha thiếu và tác giả đã xóa. Loại AutoModerator và bot theo danh sách có phiên bản, không mặc định mọi tên kết thúc bằng “bot” đều là bot. Xuất báo cáo chất lượng theo tháng.
    4.  Xây dựng ánh xạ ID toàn cục ổn định cho bốn loại đỉnh. ID chỉ phục vụ lưu trữ, sự tồn tại và thuộc tính tương lai của node không được đưa vào đầu vào tại t.
    5.  Tạo snapshot theo tháng với ánh xạ node ổn định. Chỉ xử lý đồ thị con đang hoạt động để tiết kiệm bộ nhớ, không đưa thông tin tương lai của node vào đầu vào.
    6.  Dựng R_t từ trả lời trực tiếp và T_t từ cùng tham gia thread, trích xuất thuộc tính subreddit.
    7.  Phát hiện community user, theo dõi qua các tháng và tạo nhãn tiến hóa. Đặc trưng gồm trạng thái hiện tại và lịch sử đã quan sát. Không dùng score lúc thu thập vì chưa biết giá trị tại thời điểm dự báo. Xử lý dữ liệu thiếu và chọn đặc trưng chỉ học từ train.
- Mỗi bảng trung gian lưu tháng nguồn, phiên bản script và checksum. Tên user được băm trước khi xuất artifact, chỉ công bố thống kê tổng hợp, không công bố nội dung bài viết.

**2\. Evaluation Protocol:**

- **Detailed evaluation pipeline, evaluation data:**
    1.  Kiểm chứng phát hiện/tracking: dùng benchmark mạng động có phân hoạch và lịch sự kiện biết trước, tách mạng dùng chọn tham số khỏi mạng dùng đánh giá. Thay đổi độ rõ của community để kiểm tra cả sáu sự kiện. Đánh giá tracker riêng trên phân hoạch chuẩn, sau đó đánh giá toàn pipeline để phân biệt lỗi tracking với lỗi detection. Trên Reddit, hai người độc lập đối chiếu một mẫu chuỗi community dựa trên thành viên và tương tác, ghi nhận trường hợp mơ hồ. Việc đối chiếu hỗ trợ diễn giải, không thay thế nhãn chuẩn.
    2.  Phát hiện chỉ dùng dữ liệu quá khứ: phát hiện community bằng cửa sổ kết thúc ở tháng hiện tại. Reddit không có nhãn community chuẩn. Subreddit chỉ dùng để kiểm tra mức tập trung hoạt động và diễn giải, không phải nhãn chuẩn.
    3.  Chọn tham số: chọn độ phân giải, mức liên kết thời gian và ngưỡng tracking bằng benchmark và train. Cross-validation theo thứ tự thời gian, mỗi lượt chỉ học từ giai đoạn trước giai đoạn đánh giá. Không chọn tham số bằng kết quả test.
    4.  Khóa mô hình: chọn cấu hình bằng nhãn 07–09/2017 và hiệu chỉnh xác suất bằng 10–12/2017. Nếu tập hiệu chỉnh thiếu lớp, giữ xác suất gốc và báo cáo hạn chế. Khóa cấu hình trước test. Trong test chỉ cập nhật graph/đặc trưng đã quan sát, không học lại từ nhãn test.
    5.  Ước lượng độ bất định: so sánh trên cùng mẫu test, dùng bootstrap ghép cặp theo khối thời gian để báo cáo chênh lệch và khoảng tin cậy. Kiểm tra độ ổn định khi lặp lại thuật toán và thay đổi nhẹ cạnh hoặc node trên train.
- Community tham chiếu dùng HeTCo với cấu hình khóa từ benchmark/train. Lưu C_t khi kết thúc t, không sửa bằng dữ liệu tương lai. B1/B2/B4/B5 và HeTCo dùng cùng C_t, mẫu và nhãn GED. Lặp các so sánh với Independent Leiden để kiểm tra thiên lệch do chọn detector. Nhãn tracker không phải ground truth xã hội. Thí nghiệm thay đổi thông tin dị thể và động lực thành viên, đo macro-F1, giữ nguyên split, nhãn, seed và ngân sách trong mỗi bộ tham chiếu. Đánh giá ảnh hưởng của dữ liệu tương lai bằng cách so hai tập học có cùng số mẫu: một tập gồm cả mẫu sau mốc đánh giá, tập còn lại chỉ có mẫu trước mốc. Giữ cùng mô hình và tập đánh giá. Chênh lệch phản ánh độ nhạy với thông tin tương lai, không được diễn giải như quan hệ nhân quả.
- **Evaluation metrics:**

| Thành phần | Chỉ số chính | Bổ sung |
| --- | --- | --- |
| Phát hiện benchmark | AMI với nhãn chuẩn | Khả năng khôi phục community |
| --- | --- | --- |
| Phát hiện Reddit | AMI giữa các lần chạy | Modularity, metadata enrichment, AMI sau perturbation và độ phủ user |
| --- | --- | --- |
| Theo dõi | Macro-F1 sự kiện | F1 từng lớp, % dissolve |
| --- | --- | --- |
| Dự báo | Macro-F1 | Balanced accuracy, PR-AUC, Brier |
| --- | --- | --- |

- Chỉ so modularity trên cùng graph và cùng γ. Điểm cao cần đi kèm độ ổn định, metadata enrichment, độ phủ và phân phối kích thước. Quét γ để kiểm tra resolution limit khi nhóm nhỏ bị gộp.
- Macro-F1 cân bằng vai trò sáu sự kiện. Recall của nhóm thu hẹp/phân rã đo khả năng phát hiện suy giảm, precision đo cảnh báo sai, Brier score đánh giá xác suất. Báo cáo kết quả toàn test và theo tháng, diễn giải thận trọng với lớp hiếm. Kiểm tra độ nhạy của khoảng tin cậy vì giai đoạn test ngắn.

**3\. Baseline:**

- Baseline 1 — Majority và Persistence. Majority luôn đoán lớp phổ biến nhất, Persistence lặp sự kiện gần nhất. Đây là mức sàn và phép đo quán tính.
- Baseline 2 — Structural Random Forest + GED. Dùng đặc trưng cấu trúc nhóm và thống kê đỉnh theo Saganowski trên cùng community tham chiếu. Đây là bản thích nghi của baseline tài liệu, không phải tái lập nguyên trạng. Independent Leiden được kiểm tra riêng như detector thay thế.
- Baseline 3 — Jaccard tracker control. Thay GED bằng Jaccard để kiểm tra độ nhạy của nhãn. Chọn ngưỡng trên benchmark/train, chạy lại các mô hình trên cùng bộ nhãn mới ở Experiment 5.
- Baseline 4 — Logistic Regression. Dùng kích thước t,t−1,t−2, tuổi community và tốc độ tăng trưởng, kiểm tra liệu mô hình đơn giản đã đủ.
- Baseline 5 — Structural Gradient Boosting. Dùng cùng bộ phân loại, quy trình tinh chỉnh và tracker như HeTCo nhưng chỉ giữ đặc trưng cấu trúc user–user. Đây là matched-capacity control giúp phần chênh lệch phản ánh thông tin dị thể thay vì chỉ phản ánh một bộ phân loại mạnh hơn.
- Baseline 6 — Kiểm tra lựa chọn thuật toán. So Louvain trên cùng phép chiếu user. Girvan–Newman và Spectral chỉ chạy trên graph con phân tầng vì chi phí edge betweenness và phép toán ma trận lớn. Spectral cần chọn trước số cụm k. B6 dùng kiểm tra detection, không tham gia dự báo chính.

Mọi baseline dự báo dùng cùng community tham chiếu, nhãn, split và ngân sách tinh chỉnh. B2 tham khảo Saganowski et al. (2015), DOI 10.3390/e17053053. B5 là đối chứng chính cho H3. B6 chỉ đánh giá detection ở Experiment 2.

**4\. Proposed Method:**

- **Main idea, description:** HeTCo (Heterogeneous Temporal Community Forecaster) kết hợp mạng trả lời, quan hệ cùng tham gia thread và lịch sử thành viên để dự báo tiến hóa của community user. Câu hỏi trọng tâm là liệu ngữ cảnh thảo luận và biến động thành viên có bổ sung giá trị dự báo ngoài cấu trúc user–user hay không. So sánh với B5 dùng cùng bộ phân loại và nhãn giúp kiểm tra phần đóng góp này, thay vì chỉ so hai mô hình khác nhau.
    1.  Multiplex theo meta-path: tạo hai tầng user từ quan hệ trả lời trực tiếp và cùng tham gia thread. Trọng số tầng trả lời phản ánh số lượt tương tác. Tầng thread được điều chỉnh theo quy mô thảo luận để nhóm đông người không lấn át. Chuẩn hóa các tầng trước khi kết hợp, không tạo self-loop. Subreddit chỉ cung cấp ngữ cảnh hoạt động.
    2.  Phát hiện multislice theo cửa sổ quá khứ. Dùng Leiden kết hợp hai tầng tương tác và liên kết cùng user qua các tháng. Điều chỉnh độ phân giải và mức liên kết thời gian trên train. Lặp thuật toán để chọn phân hoạch đại diện ổn định, chỉ xuất community của tháng hiện tại. Kiểm tra để việc làm ổn định phân hoạch không che mất biến động thật.
    3.  Theo dõi community. Thích nghi GED để nối các nhóm qua tháng dựa trên thành viên chung và mức quan trọng của họ trong mạng trả lời. Từ liên kết kế tiếp và thay đổi kích thước, gán sáu sự kiện đã nêu. Chọn ngưỡng trên benchmark/train và cố định quy tắc xử lý trường hợp vừa tách vừa hợp nhất trước khi đánh giá. Nhóm quá nhỏ được báo cáo riêng, xét mọi nhóm đích để tránh gán phân rã sai. Nhóm mới hình thành được thống kê riêng vì chưa có nhóm nguồn để dự báo.
    4.  Biểu diễn community. Dùng ba nhóm đặc trưng: cấu trúc tương tác, hoạt động dị thể và biến động thành viên. Cấu trúc gồm kích thước, mật độ và mức tương tác hai chiều. Hoạt động dị thể gồm phân bố subreddit và đặc điểm thread. Thành viên gồm người mới, giữ chân, rời đi và thâm niên. Bổ sung lịch sử đã quan sát, gắn cờ merge/split và xử lý dữ liệu thiếu bằng train. Không suy diễn quan điểm chính trị cá nhân từ subreddit.
    5.  Dự báo. Dùng Gradient Boosting có trọng số lớp để dự báo sáu sự kiện, hiệu chỉnh xác suất trên validation. Kiểm tra thời điểm có thể biết từng đặc trưng để ngăn sử dụng dữ liệu tương lai.
- Đóng góp dự kiến là bằng chứng về giá trị bổ sung của ngữ cảnh dị thể và lịch sử thành viên trong dự báo theo thời gian, không phải một thuật toán nền mới. Nếu không cải thiện so với B5 hoặc ghép thời gian che khuất biến động, báo cáo kết quả đó và ưu tiên phương án đơn giản hơn.

**5\. Ablation:**

- Ablation 1 — Heterogeneous information. Bỏ đặc trưng Post–Comment–Subreddit.
- Ablation 2 — Thread meta-path. Bỏ T_t, chỉ giữ R_t.
- Ablation 3 — Temporal coupling. Bỏ liên kết giữa các tháng, phát hiện độc lập từng snapshot.
- Ablation 4 — Membership dynamics. Bỏ người mới, giữ chân, rời đi và thâm niên.
- Ablation 5 — Consensus. Bỏ bước chọn phân hoạch đại diện, đánh giá độ ổn định khi lặp lại thuật toán.
- Ablation 6 — Temporal history. Bỏ t−1,t−2, chỉ dùng trạng thái t.
- Ablation 7 — Tracker and resolution. Đổi GED sang Jaccard và lặp với nhiều γ, không dùng để chọn hậu nghiệm kết quả thuận lợi.

A1/A4/A6 đo Δ macro-F1 trên cùng mẫu/nhãn. A2/A3/A5 thay phân hoạch nên đánh giá AMI và sự kiện benchmark ở Experiment 2. Nếu dự báo trên phân hoạch mới, chạy lại mọi baseline trên cùng nhãn mới và báo cáo riêng. A7 kiểm tra độ nhạy. Mỗi lần đổi một yếu tố, giữ split, seed và ngân sách.

**6\. Experiment specifications:**

Ưu tiên dữ liệu, detection/tracking, dự báo chính và ablation kiểm chứng H3. Leakage và các ablation còn lại là phân tích bổ sung. Theo dõi thời gian, bộ nhớ và chỉ chạy thuật toán chi phí cao trên graph con.

- Experiment 1 — Validate graph and community definition  
    Procedure: kiểm tra ánh xạ ID, loại node, cạnh và độ phủ theo tháng.  
    Success: 100% thành viên community là User, ID nhất quán trong 45 snapshot, lỗi cấu trúc dưới 1%.  
    Output: bảng thống kê chất lượng dữ liệu và sơ đồ mạng dị thể.
- Experiment 2 — Community detection and tracking  
    Procedure: so Louvain, Independent Leiden, multislice và multislice + consensus trên benchmark và train, lặp lại để đánh giá độ ổn định. B6 bổ sung kiểm tra trên graph con.

Metrics: AMI, macro-F1 sự kiện benchmark, độ phủ và chất lượng cấu trúc theo mục 2.

Success: so với Independent Leiden, AMI giữa các lần chạy tăng và macro-F1 sự kiện benchmark không giảm quá hai điểm phần trăm. Kiểm tra riêng thời điểm biến động để tránh nhầm phân hoạch bất biến với ổn định.

- Experiment 3 — Leakage audit  
    Procedure: trong train, so hai tập học có và không có mẫu sau mốc đánh giá, giữ cùng số mẫu, mô hình và tập đánh giá.  
    Metrics: macro-F1 và chênh lệch ghép cặp.  
    Success: H2 được ủng hộ khi cận dưới CI 95% của optimism gap lớn hơn 0, nếu không thì báo cáo chưa đủ bằng chứng.
- Experiment 4 — Main prediction  
    Procedure: so B1, B2, B4, B5 và HeTCo trên cùng mẫu/nhãn. Chọn cấu hình bằng validation, khóa mô hình trước khi đánh giá test.  
    Metrics: macro-F1 là chính, các chỉ số bổ sung theo mục 2.  
    Success: H3 được ủng hộ khi HeTCo vượt B5 ít nhất hai điểm phần trăm macro-F1 và khoảng tin cậy 95% của chênh lệch nằm trên 0. Không mặc định sẽ cải thiện. Phân tích lỗi theo sự kiện, tháng, kích thước nhóm và kiểm tra lại với community từ Independent Leiden.
- Experiment 5 — Ablation and robustness  
    Procedure: chạy A1–A7, kiểm tra lại với GED/Jaccard và các mức γ định trước theo mục 5.  
    Metrics: Δ macro-F1, AMI và thay đổi phân phối lớp.  
    Success: kiểm tra đóng góp từng thành phần và độ nhạy của so sánh HeTCo–B5, kể cả khi không cải thiện.