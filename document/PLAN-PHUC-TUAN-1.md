# Kế hoạch tuần 1 của Phúc: benchmark mạng động và Independent Leiden

> **Theo dõi triển khai:** dùng [bộ specs Phúc](specs/phuc/README.md) và [task list có trạng thái/bằng chứng](specs/phuc/tasks.md). Checklist trong kế hoạch này là hướng dẫn tham khảo; tiến độ triển khai chỉ cập nhật tại task list để tránh lệch giữa nhiều file.

> **Phân công chung để bắt đầu triển khai:** xem [Phân công Phúc–Đăng tuần 1, v1](PHAN-CONG-PHUC-DANG-TUAN-1.md). File đó cụ thể hóa người phụ trách, giao diện, quy tắc bản đầu và lịch bàn giao; tài liệu này là hướng dẫn chi tiết cho phần cá nhân Phúc.

> Ngày lập: **16/10/2026**. Mốc hoàn thành nội bộ dùng trong kế hoạch này: **tối 20/10/2026** theo yêu cầu hiện tại của Phúc.
>
> Lịch đang ghi trong `PHAN-CONG-SNA-8-TUAN.md`: hoàn thành tuần 1 trước tối **21/10/2026**, báo cáo **22/10/2026**. Vì vậy, ngày 21/10 là khoảng dự phòng để chạy lại và diễn tập. Bảng được gửi trong chat có ngày 20/10/2027; mốc đó lệch năm với lịch repo và không được dùng trong kế hoạch này.
>
> Đây là **kế hoạch thực hiện**, chưa phải báo cáo hoàn thành. Mọi tên file có ghi “dự kiến” đều chưa được tạo bởi tài liệu này. Các seed, kích thước, xác suất và quy tắc minh họa bên dưới là đề xuất để bắt đầu, không phải kết quả đã chạy hay quyết định đã được cả nhóm duyệt.

## 1. Đọc phần này trước nếu chưa biết bắt đầu từ đâu

Nhiệm vụ tuần 1 của bạn là tạo một bộ thí nghiệm nhỏ để trả lời:

**“Nếu tôi biết trước các cộng đồng thật và cách chúng thay đổi, thuật toán Leiden có tìm lại được các cộng đồng đó không?”**

Bạn sẽ làm theo đường chạy:

```text
Đặt ra cộng đồng chuẩn theo từng tháng
    -> sinh cạnh để tạo graph từng tháng
    -> chạy Independent Leiden
    -> lấy membership dự đoán
    -> so với membership chuẩn bằng AMI
    -> giao cả membership chuẩn và dự đoán cho Đăng
    -> ghép demo detection + tracking của hai người
```

Việc bạn cần có vào tối 20/10:

- [ ] Có code sinh mạng động, lưu cấu hình và seed.
- [ ] Có phân hoạch chuẩn: biết mỗi user thuộc cộng đồng nào ở mỗi tháng.
- [ ] Có tình huống chuẩn cho cả sáu sự kiện, thống nhất cách hiểu với Đăng.
- [ ] Có code chạy Independent Leiden trên từng snapshot.
- [ ] Có membership dự đoán, kiểm tra khóa và độ phủ.
- [ ] Có bảng AMI theo từng graph/tháng/seed detector, kèm thời gian chạy.
- [ ] Có notebook hoặc chuỗi lệnh chạy lại được từ đầu đến kết quả.
- [ ] Đăng đọc được đầu ra của bạn và hai người chạy được demo chung.
- [ ] Có ví dụ lỗi và ghi rõ hạn chế của benchmark tổng hợp.

**Chưa cần làm trong tuần 1:** B2 Random Forest, B5 Gradient Boosting, B6, detector temporal/multislice, consensus, HeTCo, dự báo trên toàn bộ Reddit. Các phần đó thuộc giai đoạn sau. Bạn cũng chưa cần xử lý lại 15 ZIP Reddit để hoàn thành demo của cặp mình.

## 2. Vai trò của bạn trong toàn đồ án

Đồ án có ba bài toán:

| Bài toán | Đầu vào | Đầu ra | Người phụ trách liên quan |
|---|---|---|---|
| Detection | Graph người dùng của một tháng | Người nào thuộc cộng đồng nào | Phúc làm đối chứng; Tâm làm phương pháp đề xuất |
| Tracking | Membership hai tháng liên tiếp | Nhóm nào tiếp tục, tăng, giảm, hợp nhất, tách, phân rã | Đăng làm Jaccard; Thanh làm GED |
| Forecasting | Features và lịch sử đã biết đến tháng t | Dự đoán sự kiện t sang t+1 | Thanh, Trâm; Phúc hỗ trợ B2/B5 ở các tuần sau |

Tuần 1 có ba cặp làm độc lập:

- Tâm–Thanh: dùng Reddit pilot thật để xây luồng core.
- **Phúc–Đăng: dùng mạng động tự sinh có đáp án chuẩn để kiểm chứng detection/tracking.**
- Trâm–Anh: dùng bảng community–tháng tự sinh để chạy baseline và đánh giá.

Bạn không phải chờ artifact của hai cặp còn lại. Tuy nhiên, hãy dùng lại code chung và schema đã có trong repo để việc ghép từ tuần 2 dễ hơn.

## 3. Những khái niệm cần hiểu trước khi viết code

| Khái niệm | Hiểu đơn giản | Ví dụ |
|---|---|---|
| Node/user | Một người dùng trong graph | `u001` |
| Edge/cạnh | Một quan hệ tương tác giữa hai user | `u001 -- u002` |
| Weight/trọng số | Mức độ tương tác trên cạnh | `1.0` trong benchmark đơn giản |
| Snapshot | Graph tại một mốc thời gian | Graph của tháng `2020-01` |
| Community | Một nhóm user | `{u001, u002, u003}` |
| Partition/phân hoạch | Cách chia toàn bộ user được xét thành các nhóm không chồng lấn | Nhóm A và nhóm B |
| Membership | Bảng ghi user thuộc nhóm nào | `u001 -> A` |
| Ground truth | Đáp án chuẩn do bộ sinh dữ liệu tạo ra | Membership trước khi chạy Leiden |
| Dynamic network | Một chuỗi graph thay đổi theo thời gian | Graph tháng 1 và graph tháng 2 |
| Detector | Thuật toán tìm cộng đồng từ graph | Leiden |
| Tracker | Thuật toán liên kết các cộng đồng giữa hai tháng | Jaccard tracker của Đăng |
| Seed | Số dùng để tái lập thao tác ngẫu nhiên | Seed sinh graph `11` |
| AMI | Chỉ số so hai phân hoạch trên cùng tập user | So membership chuẩn với kết quả Leiden |
| Coverage/độ phủ | Tỷ lệ user được detector gán cộng đồng trong tập cần xét | 38/40 user |
| Artifact | File đầu ra của một lần chạy | CSV membership, JSON cấu hình |
| Run ID | Tên riêng của một lần chạy | `phuc-week1-dev-001` |

Phân biệt ba loại seed:

1. **Seed sinh graph:** quyết định các cạnh ngẫu nhiên được sinh ra.
2. **Seed detector:** quyết định thao tác ngẫu nhiên bên trong Leiden.
3. **Seed hiển thị:** nếu dùng layout ngẫu nhiên để vẽ graph, seed này chỉ ảnh hưởng vị trí node trên hình.

Đổi seed hiển thị không làm thay đổi graph hay membership. Đổi seed detector không tạo ra một bộ dữ liệu đánh giá mới độc lập.

### 3.1. Ví dụ xuyên suốt

Bạn quy định trước:

```text
Tháng 2020-01:
  A = {u001, u002, u003, u004}
  B = {u005, u006, u007, u008}

Tháng 2020-02:
  C = {u001, u002, u003, u004, u005, u006, u007, u008}

Sự kiện chuẩn:
  A -> C: merge
  B -> C: merge
```

Đây là ví dụ giải thích, chưa phải cấu hình benchmark chính. Nhóm quá nhỏ và các cạnh nhiễu có thể làm detector khó khôi phục đáp án.

Bạn sinh graph tháng 1 có hai vùng tương tác rõ; graph tháng 2 có một vùng tương tác chung. Leiden chỉ được nhận graph. Membership chuẩn và nhãn `merge` được giữ riêng để đánh giá.

Các chuỗi tháng `2020-01`, `2020-02` trong benchmark chỉ là mốc giả lập hợp lệ về định dạng, không phải dữ liệu Reddit năm 2020.

### 3.2. Hai đáp án chuẩn khác nhau

- **Đáp án detection:** mỗi user ở nhóm nào trong từng tháng.
- **Đáp án tracking:** nhóm nguồn ở tháng t trải qua sự kiện gì khi sang t+1, liên kết đến nhóm đích nào.

Bạn cần phối hợp với Đăng để có cả hai. Chỉ có graph và membership vẫn chưa đủ để đánh giá sáu sự kiện.

## 4. Repo hiện có gì để dùng lại

| Đường dẫn | Hiện trạng lúc lập kế hoạch | Bạn dùng để làm gì |
|---|---|---|
| `src/reddit_sna/detection/leiden.py` | Đã có `detect_snapshots(...)` | Chạy Independent Leiden, xuất membership và diagnostics |
| `src/reddit_sna/contracts.py` | Đã có `SnapshotEdge`, `Membership`, `Event`, `TrackingLink` | Giữ schema và tên sự kiện tương thích |
| `src/reddit_sna/graphs/provenance.py` | Đã có kiểm tra CSV graph và fingerprint | Hiểu đúng đầu vào detector và reference |
| `src/reddit_sna/graphs/snapshots.py` | Đã có `write_csv(...)` | Có thể dùng lại hàm ghi CSV không ghi đè |
| `src/reddit_sna/artifacts.py` | Đã có tạo thư mục run và manifest ban đầu | Tạo output riêng, bổ sung trạng thái/kết quả thật trong pipeline |
| `src/reddit_sna/benchmarks/__init__.py` | Chưa có bộ sinh benchmark | Đây là nơi phù hợp để bổ sung generator |
| `src/reddit_sna/pipelines/detection_tracking.py` | Đang báo chưa triển khai | Nơi ghép luồng chung sau khi các module hoạt động |
| `src/reddit_sna/tracking/__init__.py` | Chưa có Jaccard tracker | Đăng triển khai phần này |
| `configs/detection_tracking.toml` | Đã có config bao ngoài, seed tổng 42 | Dùng chọn pipeline và output |
| `notebooks/detection_tracking/00_research_plan.ipynb` | Template, có `NotImplementedError` | Ghi và trình bày thí nghiệm thực tế |
| `tests/unit/test_leiden.py` | Có test graph hai clique, graph rỗng, reference và cạnh sai | Đọc mẫu gọi detector; chưa thay thế benchmark động sáu sự kiện |

Không cần tự viết lại thuật toán Leiden. Phần mới chính của bạn là **generator + ground truth + kiểm tra dữ liệu + đánh giá detection + demo**.

Lưu ý: code hiện tại có **ARI so các seed detector với nhau**. Nhiệm vụ của bạn là bổ sung **AMI so kết quả detector với phân hoạch chuẩn**; hai chỉ số phục vụ hai mục đích khác nhau.

## 5. Phối hợp với Đăng: chốt gì ngay ngày đầu

Bạn có thể dùng nội dung này để trao đổi với Đăng. Đây là mẫu trao đổi, tài liệu không tự gửi tin nhắn.

> Mình làm generator graph, membership chuẩn, Leiden và AMI. Bạn làm Jaccard tracker và đánh giá sự kiện. Hai đứa chốt trước schema membership, sáu tình huống, ngưỡng và thứ tự xử lý sự kiện. Ngày 17/10 mình giao bộ nhỏ đầu tiên gồm hai tháng, membership chuẩn và dự đoán để bạn ghép thử. Ngày 18/10 ghép đủ sáu sự kiện. Ngày 19/10 khóa cấu hình trên development, rồi chạy evaluation bằng seed riêng. Ngày 20/10 hoàn thành notebook và demo chung.

### 5.1. Danh sách cần thống nhất

- [ ] Tên sáu sự kiện dùng đúng `stable/grow/shrink/merge/split/dissolve`.
- [ ] Membership có đủ `reference_id, month, community_id, user_id`.
- [ ] Mỗi user chỉ thuộc một cộng đồng trong một tháng của một bộ tham chiếu.
- [ ] ID user giữ nhất quán trong cùng chuỗi snapshot.
- [ ] ID cộng đồng chỉ có ý nghĩa trong từng tháng; tracker không dựa vào tên nhóm.
- [ ] Quy ước một sự kiện cho mỗi cộng đồng nguồn, kèm các liên kết đích riêng.
- [ ] `merge`: mỗi nhóm nguồn tham gia hợp nhất có một nhãn `merge`.
- [ ] `split`: nhóm nguồn có một nhãn `split`, nhưng có thể có nhiều liên kết đích.
- [ ] Nhóm mới hình thành được báo cáo riêng; không tạo mẫu dự báo cho một nhóm chưa tồn tại ở tháng nguồn.
- [ ] Không tự gán `dissolve` cho tháng cuối thiếu tháng kế tiếp.
- [ ] Có cách xử lý trường hợp đồng thời hợp nhất/tách; ghi thứ tự ưu tiên rõ ràng.
- [ ] Chốt cách ánh xạ cộng đồng detector sang cộng đồng chuẩn khi đánh giá toàn luồng.
- [ ] Chọn ngưỡng bằng development; chưa dùng evaluation để sửa ngưỡng.
- [ ] Chốt file nào mỗi người xuất, thời điểm bàn giao và ai sửa khi lỗi thuộc module nào.

### 5.2. Bàn giao tối thiểu cho Đăng vào ngày 17/10

1. Một dataset nhỏ có hai tháng liên tiếp.
2. File graph từng tháng và danh sách user đang hoạt động.
3. Membership chuẩn của cả hai tháng.
4. Liên kết và nhãn sự kiện chuẩn.
5. Membership dự đoán của seed detector đầu tiên.
6. File mô tả schema và cách xác định `dataset_id/reference_id`.

Đăng có thể bắt đầu kiểm tra tracker trên membership chuẩn trước khi bạn hoàn thành phần Leiden hoặc AMI. Nếu Đăng chưa xong tracker, bạn vẫn tiếp tục generator, kiểm tra membership, AMI và phần notebook của mình.

## 6. Thiết kế benchmark nhỏ, đủ để làm trong tuần 1

### 6.1. Làm từng mức, không bắt đầu bằng graph lớn

| Mức | Mục đích | Nội dung |
|---|---|---|
| M0: smoke test | Hiểu đường chạy | Hai nhóm rõ ràng, một hoặc hai snapshot |
| M1: sáu sự kiện cơ bản | Hoàn thành phạm vi chính | Sáu tình huống riêng, mỗi tình huống có hai tháng |
| M2: trường hợp khó | Kiểm tra hạn chế | Nhóm nhỏ, cạnh nhiễu, thay đổi gần ngưỡng hoặc sự kiện mơ hồ |

M1 là ưu tiên trước tối 20/10. Sau khi M1 chạy được, bổ sung ít nhất một hoặc hai trường hợp khó có giải thích. Bộ nhỏ này vẫn là prototype, không đủ để khẳng định hiệu quả tổng quát của detector.

Mỗi tình huống nên là một dataset riêng. Cách này dễ hiểu hơn việc nhét sáu sự kiện vào cùng một graph ngay từ đầu. Với tình huống cần nhóm đích biến mất, giữ thêm nhóm nền tiếp tục hoạt động để tháng sau vẫn có dữ liệu quan sát được.

### 6.2. Sáu tình huống cơ bản đề xuất

| Case ID | Tháng t | Tháng t+1 | Đáp án cần kiểm tra |
|---|---|---|---|
| `stable` | Nhóm A có 12 user; có nhóm nền B | A giữ nguyên tập thành viên; cạnh có thể đổi | A là `stable`; B cũng có nhãn phù hợp |
| `grow` | A có 12 user | A tiếp tục với 18 user, gồm 12 user cũ | Nhóm nguồn A là `grow` |
| `shrink` | A có 18 user | A tiếp tục với 12 user cũ | Nhóm nguồn A là `shrink` |
| `merge` | A và B, mỗi nhóm 12 user | Một nhóm C gồm 24 user của A và B | Cả A và B ở tháng nguồn là `merge` |
| `split` | A có 24 user | B và C, mỗi nhóm 12 user, chia từ A | A ở tháng nguồn là `split`, có hai liên kết đích |
| `dissolve` | A có 12 user; nhóm nền B vẫn tồn tại | A bị loại khỏi tập user hoạt động theo kịch bản; B vẫn tiếp tục | A là `dissolve` theo ground truth đã thiết kế |

Các con số trên là điểm khởi đầu để kiểm tra code. Chưa được chọn chúng sau khi nhìn điểm evaluation nhằm tạo bảng kết quả đẹp.

Với `dissolve`, ghi rõ ý nghĩa: **nhóm được bộ sinh loại khỏi cộng đồng hoạt động ở tháng tiếp theo**. Không kết luận người dùng Reddit thật đã rời mạng xã hội. Không tạo tháng graph rỗng chỉ vì không quan sát được dữ liệu rồi coi mọi nhóm là phân rã.

Tất cả nhóm nguồn, kể cả nhóm nền, cần có ground truth tương ứng hoặc một quy tắc loại khỏi đánh giá đã định trước. Không bỏ các nhóm nền chỉ vì tracker dự đoán sai.

### 6.3. Cách sinh cạnh dễ hiểu

Đề xuất dùng graph vô hướng đơn giản, mọi trọng số bằng `1.0` trong bản đầu:

```text
Với mỗi cặp user khác nhau trong cùng snapshot:
    nếu cùng nhóm chuẩn:
        sinh cạnh với xác suất p_in
    nếu khác nhóm chuẩn:
        sinh cạnh với xác suất p_out
```

Ví dụ cấu hình ban đầu:

- Mức dễ: `p_in = 0.50`, `p_out = 0.02`.
- Mức khó bổ sung: `p_in = 0.25`, `p_out = 0.05`.
- Không self-loop; mỗi cặp vô hướng chỉ xuất một dòng.
- Sắp thứ tự user/cạnh ổn định trước khi ghi để cùng seed cho cùng output.
- Đây là graph tương tác giả lập, không phải graph đếm lượt reply thật.

Ngay cả khi `p_in > p_out`, graph ngẫu nhiên vẫn có thể có isolate hoặc cấu trúc khó khôi phục. Không hứa trước AMI bằng 1. Không tự nối thêm cạnh hoặc sinh lại seed sau khi thấy điểm thấp. Nếu cần generator có ràng buộc kết nối, phải mô tả và khóa quy tắc đó từ development, đồng thời ghi rõ nó làm benchmark dễ hơn.

Nhãn `stable` dựa trên cộng đồng/thành viên theo kịch bản. Cạnh có thể thay đổi ngẫu nhiên giữa hai tháng dù membership giữ nguyên. Đây là tình huống hữu ích để xem detector có tạo ra thay đổi giả hay không.

### 6.4. Seed và tập development/evaluation

Một lịch nhỏ đề xuất:

| Mục đích | Seed sinh graph | Có được dùng để sửa thuật toán/ngưỡng? |
|---|---|---|
| Development | `11, 12, 13` | Có, phải ghi lại thay đổi |
| Evaluation giữ lại | `101, 102, 103` | Chỉ đánh giá sau khi khóa cấu hình |
| Leiden | `0, 1, 2` trên mỗi graph | Lịch chạy cố định; seed 0 là đầu ra canonical |

Lịch M1 này có 6 case × 6 seed sinh graph = 36 dataset hai tháng, tương ứng 72 snapshot; mỗi snapshot chạy 3 seed Leiden. Đây là kế hoạch số lượt chạy, chưa phải lượt chạy đã hoàn thành. Hãy đo thử M0 trước khi cam kết thời gian.

Nếu quá tải, giảm số seed **trước khi mở kết quả evaluation**, lưu lịch rút gọn và nêu hạn chế. Giữ đủ sáu sự kiện. Không đổi seed giữ lại chỉ vì kết quả xấu.

Seed tổng `42` trong config hiện tại không tự mô tả toàn bộ lịch này. Phải lưu riêng lịch seed generator và seed detector trong cấu hình benchmark và manifest.

### 6.5. Những trường hợp khó nên thêm sau M1

- Một nhóm nhỏ nằm gần nhóm lớn: detector có thể nhập nhóm nhỏ vào nhóm lớn.
- `stable` về thành viên nhưng cạnh thay đổi: detector có thể chia nhóm khác đi.
- `grow/shrink` ở gần ngưỡng phân loại của tracker.
- Một tình huống có cả liên kết nhiều nguồn và nhiều đích: kiểm tra thứ tự ưu tiên merge/split.
- Có user đang hoạt động nhưng không có cạnh: kiểm tra coverage và cách báo thiếu membership.

Không cần giải quyết mọi trường hợp trong tuần 1. Cần ghi được ít nhất một lỗi cụ thể và giải thích nguồn lỗi có thể là graph, detector hay tracker.

## 7. Schema và cấu trúc output dự kiến

### 7.1. Thư mục mỗi lần chạy

```text
artifacts/detection-tracking/<run_id>/
├── manifest.json
├── benchmark_config.json
├── datasets/
│   └── <dataset_id>/
│       ├── metadata.json
│       ├── snapshots/
│       │   ├── 2020-01/
│       │   │   ├── R.csv
│       │   │   └── nodes.csv
│       │   └── 2020-02/
│       │       ├── R.csv
│       │       └── nodes.csv
│       ├── truth/
│       │   ├── membership.csv
│       │   ├── links.csv
│       │   └── events.csv
│       ├── memberships/
│       │   ├── 2020-01/membership-seed0.csv
│       │   ├── 2020-01/membership-seed1.csv
│       │   ├── 2020-01/membership-seed2.csv
│       │   └── 2020-02/...
│       └── detection.json
├── detection_metrics.csv
├── detection_summary.csv
├── tracking/                       # Đăng phụ trách
├── figures/
└── executed_demo.ipynb               # Bản đã thực thi, nếu xuất riêng
```

Đây là cấu trúc đề xuất cho cặp Phúc–Đăng, không phải cấu trúc đã tồn tại. `dataset_id` cần phân biệt được case, mức khó và seed, ví dụ `dev-merge-easy-g11`.

Mỗi lần chạy dùng run ID mới. Không ghi output vào `data/`, không ghi đè kết quả cũ. Hàm `detect_snapshots` tự tạo thư mục đầu ra của nó và yêu cầu thư mục đó chưa tồn tại; đừng tạo trước thư mục `memberships/` của từng dataset rồi mới gọi hàm.

### 7.2. Graph: dùng đúng schema mà detector hiện đọc

File `snapshots/2020-01/R.csv`:

```csv
month,source_user_id,target_user_id,weight
2020-01,u001,u002,1.0
2020-01,u001,u003,1.0
```

Quy tắc kiểm tra:

- Header và thứ tự cột đúng như trên.
- `month` trên mỗi dòng khớp tên thư mục.
- ID user không rỗng, có trong danh sách node của tháng.
- Không có cạnh từ user về chính nó.
- Không lặp cặp vô hướng `(u, v)` và `(v, u)`.
- Trọng số hữu hạn và lớn hơn 0.
- Các thư mục tháng trong một dataset liên tiếp nhau.

File `nodes.csv` dự kiến:

```csv
month,user_id
2020-01,u001
2020-01,u002
2020-01,u003
```

Danh sách node cần được lưu riêng vì chỉ nhìn cạnh sẽ làm mất user isolate. Detector hiện lấy user từ endpoint của `R.csv`; `nodes.csv` do phần đánh giá đọc để tính coverage. File này là schema mới đề xuất cho benchmark, không phải `users.csv` của Reddit pilot.

### 7.3. Membership chuẩn và dự đoán

Membership chuẩn:

```csv
reference_id,month,community_id,user_id
truth-dev-merge-easy-g11,2020-01,A,u001
truth-dev-merge-easy-g11,2020-01,A,u002
truth-dev-merge-easy-g11,2020-01,B,u013
```

Membership dự đoán do detector hiện có xuất cùng bốn cột đó, nhưng có reference detector riêng và community ID dạng `c0`, `c1`, ...

- Mỗi `(reference_id, month, user_id)` chỉ có một membership.
- Membership chuẩn bao phủ toàn bộ node hoạt động theo thiết kế của tháng.
- Membership detector phải bao phủ đúng tập endpoint của graph theo hành vi code hiện tại.
- Tên `A` và `c0` khác nhau không có nghĩa là phân hoạch sai.
- Không ép ground truth và prediction dùng chung `reference_id` để ghép cho tiện.
- Lưu bảng liên hệ `dataset_id`, reference chuẩn và reference detector trong metadata.

### 7.4. Sự kiện chuẩn và liên kết chuẩn: hai bảng riêng

Schema sự kiện dự kiến, một dòng cho mỗi cộng đồng nguồn được đánh giá:

```csv
reference_id,source_month,source_community_id,target_month,event
truth-dev-merge-easy-g11,2020-01,A,2020-02,merge
truth-dev-merge-easy-g11,2020-01,B,2020-02,merge
```

Schema liên kết dự kiến, có thể nhiều dòng cho một nguồn:

```csv
reference_id,source_month,source_community_id,target_month,target_community_id
truth-dev-merge-easy-g11,2020-01,A,2020-02,C
truth-dev-merge-easy-g11,2020-01,B,2020-02,C
```

Với `split`, bảng events có một nhãn cho nguồn, bảng links có nhiều đích. Với `dissolve`, bảng events vẫn có nhãn; quy ước không có liên kết đích trong bảng links cần được Đăng ghi rõ. Không nhân đôi số mẫu sự kiện chỉ vì một nguồn có nhiều đích.

Các schema này là đề xuất cần chốt trong cặp, không phải disk adapter đã được repo triển khai. Có thể dùng `SampleKey/TrackingLink` để biểu diễn trong bộ nhớ, rồi viết adapter CSV tương ứng.

## 8. Danh sách file dự kiến cần viết

| File dự kiến | Người chính | Chức năng |
|---|---|---|
| `src/reddit_sna/benchmarks/dynamic.py` | Phúc | Đặt cộng đồng theo tháng, sinh cạnh, lưu truth và metadata |
| `src/reddit_sna/evaluation/detection.py` | Phúc | Kiểm tra membership, căn user, tính AMI/coverage và tổng hợp |
| `src/reddit_sna/tracking/jaccard.py` | Đăng | Liên kết cộng đồng và gán sự kiện theo chính sách đã chốt |
| `src/reddit_sna/evaluation/tracking.py` | Đăng | Đánh giá sự kiện, support, confusion matrix, mapping toàn luồng |
| `src/reddit_sna/pipelines/detection_tracking.py` | Hai người | Ghép các bước; hiện đã có file khung |
| `configs/benchmark_week1.json` | Phúc phối hợp Đăng | Lịch case, seed, số node, xác suất, gamma, chính sách benchmark |
| `notebooks/detection_tracking/01_synthetic_demo.ipynb` | Hai người | Notebook demo đã thực thi; tên mới đề xuất |
| `tests/unit/test_dynamic_benchmark.py` | Phúc | Các kiểm tra quan trọng của generator |
| `tests/unit/test_detection_evaluation.py` | Phúc | Kiểm tra AMI, căn user và coverage |
| `tests/integration/test_detection_tracking.py` | Hai người | Kiểm tra luồng nhỏ từ graph đến đánh giá |
| `document/PHUC-DANG-WEEK1-HANDOFF.md` | Hai người | Schema, quy tắc sự kiện, hướng dẫn bàn giao và demo |

Không bắt buộc tạo hết file ngay ngày đầu. Viết theo từng bước nhỏ đã chạy được. Không tạo thư mục source theo tên người. Thuật toán không import CLI/pipeline; notebook và pipeline gọi các module chức năng.

**Lưu ý cấu hình:** `load_config` hiện kiểm tra TOML rất chặt và sẽ từ chối trường lạ. Không tự thêm `[benchmark]` vào `configs/detection_tracking.toml` rồi kỳ vọng parser đọc được. Bản đầu có thể đọc file JSON benchmark riêng bằng notebook/API và lưu bản sao vào output. Nếu sau đó cần CLI đọc cấu hình mới, phải cập nhật parser/giao diện và kiểm tra tương thích một cách rõ ràng.

## 9. Lịch thực hiện chi tiết từ 16/10 đến 20/10

Thời lượng dưới đây là ước tính để chia việc, không phải cam kết runtime hay số giờ bắt buộc. Nếu một bước kéo dài, ưu tiên đầu ra nghiệm thu và dùng ngày 21/10 làm dự phòng.

### Ngày 16/10 — Hiểu nhiệm vụ, dựng môi trường, có graph đầu tiên

**Mục tiêu cuối ngày:** hiểu input/output, chốt bản nháp với Đăng và sinh được một snapshot có membership chuẩn.

#### Buổi 1: đọc và trao đổi, khoảng 60–90 phút

- [ ] Đọc mục 1–5 của tài liệu này.
- [ ] Đọc phần Phúc–Đăng trong `PHAN-CONG-SNA-8-TUAN.md`.
- [ ] Đọc `Membership`, `Event` trong `contracts.py`.
- [ ] Mở `detect_snapshots` để biết nó nhận đường dẫn và xuất gì; chưa cần hiểu mọi dòng của Leiden.
- [ ] Thống nhất với Đăng schema membership, nhãn nguồn và sáu case cơ bản.
- [ ] Ghi các điểm chưa chốt, đặc biệt ngưỡng/thứ tự sự kiện và mapping khi đánh giá toàn luồng.

**Tự kiểm tra:** giải thích được bằng lời “graph là đầu vào, membership là đầu ra, AMI so với đáp án chuẩn”.

#### Buổi 2: môi trường, khoảng 30–90 phút

- [ ] Tạo môi trường Python riêng trong project nếu chưa có.
- [ ] Cài project với graph/notebook dependencies.
- [ ] Cài dependency tính AMI cho môi trường phát triển; ghi lại việc cần khai báo dependency trước khi bàn giao.
- [ ] Kiểm tra import `reddit_sna`, `igraph`, `leidenalg`, `sklearn`.
- [ ] Chọn đúng kernel `.venv` trong VS Code/Jupyter.
- [ ] Chạy nhóm test Leiden hiện có để kiểm tra môi trường graph.

Lệnh chi tiết ở mục 13. Chạy từng lệnh và đọc output; khi có lỗi import/cài thư viện, xử lý trước khi viết generator tiếp.

#### Buổi 3: M0, khoảng 90–150 phút

- [ ] Đặt hai nhóm user cố định.
- [ ] Tạo danh sách node và membership chuẩn.
- [ ] Sinh graph vô hướng, đầu tiên có thể dùng hai clique tách rời để kiểm tra adapter.
- [ ] Lưu `R.csv`, `nodes.csv`, membership chuẩn và cấu hình trong output mới.
- [ ] Kiểm tra không lặp user, self-loop hoặc cạnh trùng.
- [ ] Kiểm tra cùng seed cho cùng nội dung dữ liệu.

**Đầu ra cuối ngày:** một dataset M0 có thể mở CSV để hiểu bằng mắt, môi trường chạy được, bản nháp giao diện với Đăng.

**Nếu thiếu thời gian:** ưu tiên M0 một snapshot; chưa mở rộng ngay sáu sự kiện.

### Ngày 17/10 — Chạy được detector và AMI; bàn giao bộ đầu tiên

**Mục tiêu cuối ngày:** `graph -> Leiden -> membership -> AMI` chạy được; Đăng có membership chuẩn hai tháng để bắt đầu tracker.

#### Bước 1: nối detector, khoảng 60–120 phút

- [ ] Gọi lại `detect_snapshots` trên M0.
- [ ] Ban đầu chạy `seeds=(0,)`, `gamma=1.0` để dễ dò lỗi.
- [ ] Kiểm tra thư mục `memberships/<month>/membership-seed0.csv`.
- [ ] Kiểm tra tập user được gán đúng tập endpoint của R.
- [ ] Lưu dictionary diagnostics vào `detection.json`, vì hàm trả kết quả cho caller.

#### Bước 2: tính AMI đúng, khoảng 60–120 phút

- [ ] Tạo map `user_id -> true_community` và `user_id -> predicted_community` của cùng dataset/tháng.
- [ ] Căn hai vector bằng cùng một danh sách user đã sắp xếp.
- [ ] Kiểm tra duplicate, user ngoài graph và user thiếu.
- [ ] Tính AMI trên user có membership dự đoán, báo riêng coverage trên toàn bộ node hoạt động.
- [ ] Thử hai phân hoạch giống nhau nhưng đổi tên nhóm: AMI phải bằng 1.
- [ ] Thử graph hai clique đơn giản: ghi kết quả thực tế, kiểm tra nếu lệch; không dùng ví dụ này làm toàn bộ benchmark nghiên cứu.

#### Bước 3: thêm thời gian và bàn giao, khoảng 60–120 phút

- [ ] Thêm snapshot tháng tiếp theo cho `stable` và một case thay đổi, ví dụ `grow`.
- [ ] Lưu truth events/links.
- [ ] Giao schema, truth và membership seed 0 cho Đăng.
- [ ] Cùng Đăng mở thử file bằng code của tracker.
- [ ] Ghi lại lỗi giao diện và sửa ở module sở hữu.

**Đầu ra cuối ngày:** ít nhất một ví dụ hai tháng có đầy đủ graph, truth, predicted membership, AMI và thời gian; Đăng có thể đọc membership chuẩn.

### Ngày 18/10 — Đủ sáu sự kiện và ghép thử hai người

**Mục tiêu cuối ngày:** đủ M1 sáu sự kiện trên development; có lần chạy chung đầu tiên hoặc xác định rõ phần còn thiếu của tracker.

#### Bước 1: hoàn thành bộ sinh, khoảng 90–180 phút

- [ ] Thêm `shrink`, `merge`, `split`, `dissolve`.
- [ ] Kiểm tra thật sự có thay đổi tập thành viên đúng kịch bản.
- [ ] Với merge/split, kiểm tra liên kết nhiều nguồn/nhiều đích đúng.
- [ ] Giữ nhóm nền và tháng kế tiếp quan sát được cho case dissolve.
- [ ] Kiểm tra tất cả nhóm nguồn đều có nhãn hoặc lý do loại đã khai báo.
- [ ] Lưu case ID, seed, mức khó, p_in/p_out và graph hash.

#### Bước 2: chạy detection development, khoảng 60–120 phút

- [ ] Chạy lịch seed detector `0,1,2` cố định.
- [ ] Xuất metrics cho từng dataset/tháng/seed.
- [ ] So số nhóm chuẩn với số nhóm detector tìm được.
- [ ] Xem các tháng có AMI thấp, đọc graph/membership để tìm nguyên nhân.
- [ ] Bổ sung kiểm tra isolate, graph rỗng và trường hợp nhóm nhỏ.

#### Bước 3: ghép tracking, khoảng 60–120 phút

- [ ] Đăng chạy tracker trên membership chuẩn trước.
- [ ] Hai người đối chiếu từng sự kiện với truth.
- [ ] Sau đó Đăng chạy trên membership seed 0 của detector.
- [ ] Chốt và ghi cách mapping cộng đồng nguồn detector sang cộng đồng chuẩn.
- [ ] Kiểm tra không so nhãn dựa vào số `c0/c1` giữa hai tháng hoặc giữa truth/prediction.
- [ ] Ghi một trường hợp đúng và một trường hợp sai nếu có.

**Đầu ra cuối ngày:** sáu case development chạy detection được, tracker nhận đúng schema và có kết quả kiểm tra đầu tiên.

### Ngày 19/10 — Khóa protocol, chạy evaluation và phân tích lỗi

**Mục tiêu cuối ngày:** có bảng evaluation thật, cấu hình cố định và hiểu được ý nghĩa kết quả.

#### Bước 1: khóa trước khi mở evaluation

- [ ] Chốt danh sách case/mức khó và lịch seed giữ lại.
- [ ] Chốt gamma, seed canonical, chính sách isolate và cách tổng hợp AMI.
- [ ] Đăng chốt ngưỡng Jaccard, thứ tự sự kiện và mapping/đánh giá.
- [ ] Lưu cấu hình thành file; ghi thời điểm khóa và Git revision nếu có.
- [ ] Kiểm tra development và evaluation không trùng seed sinh graph và không tái sử dụng cùng file graph.

#### Bước 2: chạy và lưu

- [ ] Tạo run ID evaluation mới.
- [ ] Chạy toàn bộ lịch đã chốt; không nhập tay membership hoặc dự đoán để đủ bảng.
- [ ] Xuất AMI/coverage/thời gian theo snapshot/seed detector.
- [ ] Xuất bảng tổng hợp theo case và development/evaluation riêng.
- [ ] Đăng xuất macro-F1, F1/support từng sự kiện và confusion matrix cho tracking.
- [ ] Ghi rõ lần chạy thiếu/hỏng thay vì âm thầm bỏ hàng.

#### Bước 3: đọc kết quả

- [ ] Chọn một case dễ để giải thích bằng tay.
- [ ] Chọn một case khó hoặc AMI thấp để phân tích lỗi.
- [ ] Đối chiếu: tracker trên truth tốt nhưng trên detector kém hay cả hai đều kém?
- [ ] Kiểm tra điểm cao có đi kèm coverage thấp không.
- [ ] Báo số mẫu mỗi sự kiện; không chỉ đưa một số macro-F1.
- [ ] Ghi điều chưa biết, không cố giải thích mọi điểm thấp bằng một nguyên nhân chưa kiểm chứng.

Nếu phát hiện lỗi code sau khi đã xem evaluation, ghi rõ lỗi, sửa có kiểm tra và tạo run mới. Không tiếp tục gọi tập đã xem là holdout chưa từng sử dụng; nếu thay đổi ảnh hưởng lựa chọn phương pháp, cần một lịch đánh giá mới hoặc công khai giới hạn của lần đánh giá đó.

**Đầu ra cuối ngày:** bảng detection, bảng tracking do Đăng xuất, cấu hình khóa, output có nguồn gốc và vài ghi chú phân tích lỗi.

### Ngày 20/10 — Hoàn thành demo, tài liệu và bàn giao

**Mục tiêu cuối ngày:** người khác làm theo hướng dẫn có thể chạy demo; bạn giải thích được code và bảng kết quả của mình.

#### Buổi 1: notebook và kết quả, khoảng 90–150 phút

- [ ] Notebook có mô tả bài toán và phân công hai người.
- [ ] Có bảng cấu hình và seed; ghi rõ dữ liệu tổng hợp.
- [ ] Hiển thị một graph nhỏ với màu ground truth và màu detector.
- [ ] Hiển thị bảng AMI/coverage/thời gian.
- [ ] Hiển thị tracking trên truth và toàn luồng riêng biệt.
- [ ] Liên kết bảng/hình với run ID thực tế, không hardcode số kết quả mẫu.
- [ ] Ghi hạn chế và phần chưa hoàn thành.

#### Buổi 2: chạy lại và nghiệm thu, khoảng 90–150 phút

- [ ] Restart Kernel rồi Run All từ đầu, dừng khi có lỗi.
- [ ] Chạy lại vào output mới; không dựa vào biến còn từ lần chạy trước.
- [ ] Chạy các test liên quan; xử lý lỗi trước khi coi là xong.
- [ ] Ghi lệnh, kernel/Python, dependencies và thời gian thực tế.
- [ ] Đăng xác nhận đọc được graph/truth/membership và chạy tracker từ đó.
- [ ] Kiểm tra Git diff, chỉ đưa đúng code/tài liệu đã làm; không đưa môi trường hoặc artifact lớn.

#### Buổi 3: diễn tập, khoảng 30–60 phút

- [ ] Giải thích được “tôi sinh mạng như thế nào và đáp án chuẩn nằm ở đâu”.
- [ ] Giải thích được “Leiden nhận gì, trả gì và vì sao tên community không cần trùng”.
- [ ] Giải thích được “AMI khác ARI giữa seed và khác F1 tracking thế nào”.
- [ ] Chỉ ra ít nhất một hạn chế hoặc trường hợp sai.
- [ ] Trình bày phần của mình trong khoảng 3–5 phút, sau đó chuyển sang Đăng.

**Đầu ra cuối ngày:** bản demo tuần 1 của cặp, kết quả có thể kiểm tra và tài liệu bàn giao.

### Ngày 21–22/10 — Dự phòng và báo cáo theo lịch repo

- **21/10:** sửa lỗi tái lập, hoàn thiện phần trình bày, chạy lại vào output mới nếu cần; giữ lịch sử các lần chạy.
- **22/10:** báo cáo demo, phân biệt rõ việc đã làm, kết quả tổng hợp và phần chưa có kết quả Reddit.

Không tự mở thêm B2/B5 vào ngày dự phòng khi benchmark/tracking hiện tại còn lỗi.

## 10. Cách dùng lại detector hiện có

Hàm hiện tại nhận:

```python
detect_snapshots(
    snapshot_dir,
    output,
    identity_scope,
    seeds=(0, 1, 2),
    gamma=1.0,
    *,
    graph_protocol=...,
    expected_months=...,
)
```

Ý nghĩa:

| Tham số | Nội dung trong benchmark |
|---|---|
| `snapshot_dir` | Thư mục chứa các thư mục tháng và `R.csv` |
| `output` | Thư mục membership mới, chưa tồn tại |
| `identity_scope` | ID riêng của dataset tổng hợp, nhất quán qua các tháng |
| `seeds` | Seed Leiden, bản đầy đủ dùng lịch cố định `0,1,2` |
| `gamma` | Độ phân giải, ban đầu giữ `1.0` |
| `graph_protocol` | Tên/version nêu đúng ý nghĩa graph tổng hợp |
| `expected_months` | Danh sách tháng của dataset để kiểm tra đầu vào |

Ví dụ cách gọi dự kiến sau khi đã có generator; đoạn này chưa tạo graph hay chạy kết quả trong kế hoạch:

```python
from reddit_sna.detection.leiden import detect_snapshots

result = detect_snapshots(
    snapshot_dir=dataset_dir / "snapshots",
    output=dataset_dir / "memberships",
    identity_scope=dataset_id,
    seeds=(0, 1, 2),
    gamma=1.0,
    graph_protocol="synthetic-planted-undirected-v1",
    expected_months=["2020-01", "2020-02"],
)
```

Code hiện cho phép tên protocol không rỗng và chỉ yêu cầu `node_order.csv` khi chọn đúng protocol `reply-r-v3-order1`. Vì benchmark không xuất phát từ reply Reddit, đề xuất dùng protocol tổng hợp riêng, danh sách user tổng hợp cố định và thứ tự cạnh ổn định. Ghi rõ chính sách này trong metadata; không gọi graph giả lập là kết quả của protocol reply Reddit.

Nếu sau này muốn dùng adapter/consumer dành cho Reddit pilot, cần kiểm tra đầy đủ contract của consumer đó; chỉ có `R.csv` hợp lệ chưa đủ để thay thế một run Reddit hoàn chỉnh.

Hàm hiện ghi CSV membership, đồng thời trả diagnostics dạng dictionary. Caller cần lưu dictionary vào JSON và đo thời gian bao quanh thao tác cần báo cáo. Trạng thái hoàn thành detection không có nghĩa là tracking đã hoàn thành.

## 11. Tính AMI, coverage và chi phí đúng cách

### 11.1. Quy trình tính cho mỗi snapshot

1. Đọc danh sách node hoạt động và membership chuẩn.
2. Đọc membership detector của một seed cụ thể.
3. Kiểm tra mỗi user chỉ có một membership, không có user ngoài dataset.
4. Kiểm tra tập user detector đúng tập endpoint của graph theo contract hiện có.
5. Xác định tập user có cả truth và prediction; không để phép giao che giấu lỗi schema hoặc user lạ.
6. Sắp danh sách user một lần, tạo hai vector nhãn theo chính danh sách đó.
7. Tính AMI bằng thư viện; không so trực tiếp mã nhóm để tính “accuracy”.
8. Báo kèm số node hoạt động, số node được gán và coverage.
9. Trường hợp không đủ dữ liệu để tính có ý nghĩa: ghi `NA` và nguyên nhân, không gán AMI = 0 hoặc 1 tùy tiện.

Ví dụ:

```text
Danh sách user: [u001, u002, u003, u004]
Truth:         [A,    A,    B,    B   ]
Prediction:    [c7,   c7,   c2,   c2  ]

Hai phân hoạch giống nhau dù tên nhóm khác nhau -> AMI = 1.
```

AMI trên tập được gán chỉ mô tả chất lượng ở tập đó. Nếu generator tạo isolate, detector hiện không gán cộng đồng cho họ. Phải báo coverage và số bị thiếu; không tự loại isolate khỏi tổng số node để báo độ phủ 100%.

### 11.2. Bảng chi tiết dự kiến

```text
dataset_id, split, scenario, difficulty, generator_seed,
month, detector_seed, gamma,
active_nodes, endpoint_nodes, assigned_nodes, coverage,
true_communities_all_nodes, true_communities_scored_nodes,
predicted_communities, ami, ami_status,
generation_wall_seconds, detection_wall_seconds, evaluation_wall_seconds
```

Tên cột là đề xuất. Cần định nghĩa rõ `coverage = assigned_nodes / active_nodes`; nếu mẫu số bằng 0 thì để thiếu và ghi trạng thái. Số nhóm chuẩn trên toàn node có thể khác số nhóm chuẩn trên tập được chấm, nên tránh so hai số không cùng mẫu.

### 11.3. Cách tổng hợp

- Giữ bảng chi tiết trước, rồi mới tổng hợp theo case, mức khó và split.
- Báo riêng kết quả canonical seed 0.
- Các seed 1/2 phục vụ xem biến động; không chọn seed có AMI cao nhất để thay đầu ra canonical.
- Nếu báo trung bình/min/max, nói rõ trung bình trên đơn vị nào và số trường hợp hợp lệ/bị thiếu.
- Không xem các seed detector trên cùng graph là các graph đánh giá độc lập.
- Không đặt “AMI phải lớn hơn 0.9” làm điều kiện hoàn thành nghiên cứu. Điểm thấp vẫn là kết quả hợp lệ nếu dữ liệu, code và cách đo đúng.

### 11.4. Thời gian và bộ nhớ

- Đo bằng `time.perf_counter()` quanh từng bước có định nghĩa rõ.
- Tách thời gian sinh graph, detection và evaluation nếu có thể.
- Diagnostics hiện có của detector ghi wall time theo tháng, gồm phần xử lý của các seed; không tự coi đó là thời gian riêng từng seed.
- Nếu cần đo riêng từng seed, bổ sung cách đo phù hợp và ghi rõ thay đổi.
- Lưu graph scale, Python và phiên bản thư viện.
- Nếu chưa đo peak memory đúng cách, ghi `not_measured`/`null`. Không ghi 0 MB.

## 12. Kiểm tra tracking cùng Đăng

### 12.1. Hai đường đánh giá phải tách riêng

```text
A. Membership chuẩn -> Jaccard tracker -> so với sự kiện chuẩn
   Mục tiêu: kiểm tra riêng tracking.

B. Graph -> Leiden -> membership dự đoán -> Jaccard tracker
   -> đối chiếu với sự kiện chuẩn bằng mapping đã định nghĩa
   Mục tiêu: kiểm tra detection + tracking.
```

Nếu A tốt và B kém, hãy xem lỗi detection và ảnh hưởng lên tracking. Nếu A đã kém, cần kiểm tra định nghĩa sự kiện, ngưỡng, thứ tự xử lý và code tracker trước.

### 12.2. Vì sao toàn luồng cần mapping

Cộng đồng chuẩn có tên A/B, detector có c0/c1 và có thể tìm khác số nhóm. Không thể ghép hai bảng sự kiện bằng tên nhóm.

Trước evaluation, Đăng cần ghi một cách đối chiếu, ví dụ ghép cộng đồng nguồn trong cùng tháng bằng mức trùng thành viên và phép ghép một-một với tie-break cố định. Có thể chọn cách khác, nhưng phải nêu rõ. Việc dùng truth để ghép trong evaluator là thao tác đo kết quả, không được đưa truth vào detector/tracker khi chạy.

Phải báo:

- Số cộng đồng chuẩn được/không được ghép.
- Số cộng đồng detector dư/không được ghép.
- Support từng sự kiện và tỷ lệ nguồn chuẩn được đánh giá.
- Cách xử lý unmatched trong điểm toàn luồng.
- Nếu F1 chỉ tính trên tập matched, đặt tên là F1 có điều kiện trên tập matched và báo coverage bên cạnh; không gọi đó là điểm bao phủ toàn bộ dữ liệu.

Không bỏ các nguồn chưa ghép mà không báo vì chúng thường chính là các trường hợp detection khó.

### 12.3. Kết quả Đăng cần cung cấp cho demo chung

- Macro-F1 và precision/recall/F1/support từng sự kiện.
- Confusion matrix với thứ tự sáu nhãn cố định.
- Chính sách lớp không xuất hiện, zero division và cách tính macro-F1.
- Kết quả tracker trên truth và toàn luồng tách biệt.
- Một vài ví dụ nhầm `stable/grow`, `merge/split`, `shrink/dissolve` nếu xảy ra.

Đây là phần Đăng phụ trách chính. Bạn cần hiểu cách đọc, hỗ trợ dữ liệu và xác nhận file bàn giao của mình đúng.

## 13. Lệnh PowerShell để bắt đầu

Các lệnh bên dưới là hướng dẫn thực hiện, chưa được chạy khi tạo tài liệu. Dùng terminal tại thư mục gốc repo. Đọc output sau từng lệnh.

### 13.1. Vào đúng project và kiểm tra Python

```powershell
Set-Location 'C:\Users\MSi\reddit-community-evolution'
```

```powershell
python --version
```

Project yêu cầu Python 3.11 trở lên. Nếu chưa có `.venv`, tạo bằng:

```powershell
python -m venv .venv
```

Nếu đã có `.venv`, kiểm tra interpreter trước khi quyết định dùng lại; không xóa môi trường hoặc tạo chồng một cách tùy tiện.

### 13.2. Cài dependencies bằng đúng interpreter

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,notebook]'
```

Repo hiện chưa khai báo scikit-learn. Để thử tính AMI trong môi trường phát triển:

```powershell
& .\.venv\Scripts\python.exe -m pip install scikit-learn
```

Khi code đánh giá đã dùng thư viện này, phải bổ sung dependency phù hợp vào `pyproject.toml`, ghi lại phiên bản và thử cài trong môi trường sạch trước khi bàn giao. Cài bằng tay trên máy mình chưa làm dependency trở thành một phần của project.

```powershell
& .\.venv\Scripts\python.exe -c "import sys, reddit_sna, igraph, leidenalg, sklearn; print(sys.executable); print('Imports OK')"
```

Kết quả cần thấy là interpreter trong `.venv` và dòng `Imports OK`. Nếu import lỗi, sửa môi trường trước.

### 13.3. Kiểm tra config và test detector hiện có

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna check --config configs/detection_tracking.toml --run-id phuc-week1-configcheck-001
```

Lệnh `check` chỉ kiểm tra config/path, không sinh benchmark và không chạy detection/tracking. Nếu run ID đã tồn tại thì chọn một ID mới.

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_leiden -v
```

Đọc xem test chạy thật hay bị skip do thiếu dependency. Test pass ở đây mới chứng minh phần được kiểm tra của detector hiện có, chưa chứng minh sáu sự kiện của cặp.

### 13.4. Mở notebook

Trong VS Code: mở notebook của cặp, chọn **Select Kernel -> Python Environments -> `.venv\Scripts\python.exe`**. Không dùng `sys.path` để vá import.

Sau khi cài thêm thư viện, restart kernel. Khi nghiệm thu, dùng **Restart Kernel -> Run All**.

### 13.5. Lệnh demo sau khi đã triển khai

Lệnh này **hiện chưa chạy được pipeline nghiên cứu**, vì `detection_tracking.py` còn là khung:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna run --config configs/detection_tracking.toml --run-id phuc-dang-week1-final-001
```

Chỉ ghi nó là lệnh demo hoạt động sau khi hai người triển khai và kiểm chứng thật. Trong tuần 1, repo cho phép demo notebook đầy đủ từ input đến evaluation; có thể ưu tiên notebook trước nếu CLI chưa kịp ghép. Vẫn phải có hướng dẫn chạy đầy đủ và output tái lập, không chỉ các cell rời rạc.

### 13.6. Kiểm tra trước bàn giao code

Chạy test mới liên quan trong quá trình làm. Trước bàn giao, chạy bộ kiểm tra hiện có để phát hiện ảnh hưởng lên phần chung:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```powershell
git status --short
```

```powershell
git diff --check
```

Ghi số test thực chạy, skip và lỗi nếu có; không sao chép số test của báo cáo cũ. Chỉ stage đúng file của công việc; không stage toàn bộ khi có thay đổi của thành viên khác. Không tự merge/push thay phần review của cặp.

## 14. Các kiểm tra cần viết cho chức năng mới

Không cần kiểm tra lại công thức nội bộ của thư viện AMI/Leiden. Tập trung vào lỗi dữ liệu và cách nối module có thể làm sai kết quả nghiên cứu.

| Kiểm tra | Vì sao cần |
|---|---|
| Cùng cấu hình/seed cho cùng graph, truth và thứ tự file | Để tái lập |
| Mỗi node hoạt động có đúng một membership chuẩn | Tránh phân hoạch thiếu hoặc chồng lấn |
| Graph không có self-loop/cạnh trùng/user lạ | Giữ contract detector |
| Merge bảo toàn đúng hợp các thành viên theo kịch bản | Tránh nhãn chuẩn mâu thuẫn với dữ liệu |
| Split tạo đúng các nhóm đích và một nhãn nguồn | Tránh nhân đôi mẫu sự kiện |
| Dissolve chỉ gán khi tháng kế tiếp được quan sát theo kịch bản | Tránh nhầm thiếu dữ liệu với sự kiện |
| Đổi tên community không làm đổi AMI | Tránh đánh giá theo mã nhóm |
| Đảo thứ tự dòng CSV không làm lệch cặp user truth/prediction | Tránh AMI sai do căn hàng |
| User thiếu/isolate được phản ánh trong coverage | Tránh điểm cao do âm thầm bỏ mẫu |
| Graph rỗng/không có mẫu chấm có trạng thái rõ | Tránh tạo điểm giả |
| Development/evaluation tách seed và dataset | Giảm việc chọn theo bộ đánh giá |
| Integration nhỏ tạo được artifact và metrics thật | Chứng minh các module nối được |

Một integration nhỏ không cần chạy toàn bộ lịch benchmark. Lịch nghiên cứu và unit/integration test phục vụ các mục đích khác nhau.

## 15. Notebook demo nên kể câu chuyện gì

Các cell nên đi theo thứ tự:

1. **Mục tiêu và phạm vi:** kiểm chứng detection/tracking trên dữ liệu tổng hợp, ai làm gì.
2. **Môi trường:** interpreter, phiên bản thư viện, nguồn config.
3. **Protocol:** case, tháng, seed, gamma, development/evaluation, quy tắc sự kiện.
4. **Input:** sinh/load benchmark, kiểm tra schema và truth.
5. **Một ví dụ dễ hiểu:** hiển thị membership chuẩn và graph nhỏ.
6. **Detection:** gọi module dùng lại, đọc membership và diagnostics.
7. **Đánh giá Phúc:** AMI, coverage, số nhóm và thời gian.
8. **Tracking trên truth:** Đăng trình bày kết quả riêng tracker.
9. **Toàn luồng:** tracking trên membership detector, mapping và support.
10. **Phân tích lỗi:** một tình huống cụ thể, có file/run ID truy ngược được.
11. **Kết luận và hạn chế:** điều gì chạy được, điều gì chưa chứng minh.
12. **Bàn giao:** thư mục output mới, cấu hình, manifest và cách chạy lại.

Nên có tối thiểu:

- Một hình graph nhỏ so màu truth/prediction, có chú thích user/mẫu nào được vẽ.
- Một bảng AMI/coverage theo case.
- Một bảng thời gian và graph scale.
- Hai phần kết quả tracking tách biệt, kèm confusion matrix của Đăng.
- Một đoạn phân tích lỗi có bằng chứng.

Không cần xây website/dashboard. Không cần quá nhiều hình trước khi số liệu được kiểm tra. Không dùng hình vẽ đẹp làm bằng chứng AMI tốt hoặc sự kiện đúng.

## 16. Checklist nghiệm thu tối 20/10

### 16.1. Phần cá nhân Phúc

- [ ] Tôi chỉ được code generator và giải thích cách tạo cạnh.
- [ ] Tôi chỉ được file ground truth và cách tạo sáu tình huống.
- [ ] Tôi tái tạo được cùng dữ liệu bằng cấu hình và seed đã lưu.
- [ ] Tôi chạy Leiden trên graph, không đưa nhãn chuẩn vào detector.
- [ ] Tôi xuất được membership cho các snapshot và lịch seed đã công bố.
- [ ] Tôi tính AMI theo đúng user và báo coverage/isolate.
- [ ] Tôi lưu metrics chi tiết trước khi tổng hợp.
- [ ] Tôi đo và mô tả được thời gian; bộ nhớ chưa đo được ghi rõ.
- [ ] Tôi tách development/evaluation và không chọn seed đẹp trên evaluation.
- [ ] Tôi có ít nhất một trường hợp lỗi/hạn chế để giải thích.
- [ ] Tôi có notebook hoặc lệnh chạy lại từ đầu, không nhập tay đáp án dự đoán.
- [ ] Tôi ghi rõ file nào đã hoàn thành, test nào đã chạy và phần nào chưa có.

### 16.2. Phần chung Phúc–Đăng

- [ ] Hai người đã thống nhất schema và chính sách nhãn.
- [ ] Đăng đọc được membership chuẩn của tôi.
- [ ] Đăng đọc được membership detector của tôi.
- [ ] Có tracking trên truth và kết quả so với sự kiện chuẩn.
- [ ] Có tracking trên detector, mapping và báo cáo unmatched/support.
- [ ] Có kết quả từng sự kiện và confusion matrix, hoặc ghi rõ phần còn thiếu nếu chưa hoàn thành.
- [ ] Cả hai chạy lại được demo từ kernel sạch/output mới.
- [ ] README/tài liệu có đủ thứ tự lệnh, dependencies, config và run ID.
- [ ] Hai người review phần của nhau, ghi nhận bàn giao thực tế.

Nếu phần cá nhân đã xong mà tracker chưa xong, ghi riêng “Phúc hoàn thành detection; demo chung còn thiếu tracking”. Không coi toàn bộ prototype đã hoàn thành chỉ vì có AMI.

## 17. Khi bị kẹt, xử lý theo thứ tự này

| Vấn đề | Việc làm trước |
|---|---|
| Không import được thư viện | In interpreter thực tế; cài bằng đúng `.venv\Scripts\python.exe`; restart kernel |
| Detector báo schema graph sai | Kiểm tra header, tháng, cạnh trùng, self-loop và weight |
| Detector báo output tồn tại | Dùng run ID/output mới; không xóa run cũ để chạy lại |
| AMI thấp trên graph đơn giản | Kiểm tra căn user, graph sinh ra, gamma và truth trước khi đổi tham số |
| Cùng seed nhưng dữ liệu đổi | Kiểm tra RNG, thứ tự user/cạnh, cấu hình và đoạn code có dùng nguồn ngẫu nhiên khác |
| Coverage thấp | Đếm isolate và user thiếu; không âm thầm bỏ khỏi mẫu số |
| Tracker sai trên truth | Cùng Đăng xem quy tắc nhãn, ngưỡng, precedence và code tracking |
| Tracker chỉ sai sau detection | Xem detector đã tách/nhập nhóm nào; đối chiếu mapping và coverage |
| Chưa có tracker từ Đăng | Giao truth sớm; tiếp tục AMI, generator, test và notebook của bạn |
| Không kịp lịch đầy đủ | Giảm số lần lặp hoặc đồ họa theo chính sách trước evaluation; giữ sáu sự kiện và tính đúng |
| Không có đủ support một lớp | Báo rõ, kiểm tra ground truth/nhãn; không tạo dự đoán giả để lấp bảng |

## 18. Những câu bạn cần trả lời được khi báo cáo

1. Benchmark do bạn tạo khác dữ liệu Reddit thật ở đâu?
2. Đáp án chuẩn được tạo trước hay sau khi chạy Leiden?
3. Graph của bạn có hướng không, trọng số nghĩa là gì?
4. Membership khác nhãn sự kiện như thế nào?
5. Vì sao cùng tên nhóm giữa hai tháng không đủ để tracking?
6. Vì sao AMI phù hợp hơn so trực tiếp số nhóm hoặc mã nhóm?
7. Những user nào được tính AMI và những user nào chưa được gán?
8. Cấu hình, seed và output nào tái tạo được bảng đang trình bày?
9. Bạn chọn tham số/ngưỡng bằng tập nào?
10. Bạn phân biệt lỗi detection với tracking bằng cách nào?
11. Case nào khó nhất, có bằng chứng gì cho nhận định đó?
12. Kết quả hiện tại chứng minh được gì và chưa chứng minh được gì?

Câu mô tả phần việc có thể dùng khi đã hoàn thành thật:

> Tôi xây bộ mạng động tổng hợp với phân hoạch và sự kiện biết trước, lưu cấu hình/seed, chạy Independent Leiden độc lập theo tháng, đánh giá AMI và coverage, rồi bàn giao membership chuẩn và dự đoán để kiểm tra tracking riêng và toàn luồng. Kết quả hiện tại dùng để kiểm chứng module trên benchmark tổng hợp; chưa phải kết quả dự báo trên Reddit.

Chỉ dùng thì quá khứ trong câu trên đối với phần đã có code và artifact thật.

## 19. Mẫu cập nhật tiến độ hằng ngày

Copy mẫu này cho mỗi ngày; ghi việc đã làm bằng đường dẫn cụ thể.

```markdown
### Ngày .../10/2026

- Mục tiêu hôm nay:
- Code đã viết/sửa:
- Lệnh/notebook đã chạy:
- Run ID và đường dẫn output:
- Kết quả thực tế, gồm cả thiếu/sai:
- Test đã chạy, skip hoặc chưa chạy:
- Đã bàn giao gì cho Đăng:
- Vướng mắc:
- Việc tiếp theo:
```

Không đánh dấu checklist chỉ vì đã tạo file rỗng, đã đọc tài liệu hoặc lệnh mới tạo manifest `started`.

## 20. Việc làm sau tuần 1, để biết trước nhưng chưa triển khai

| Giai đoạn theo phân công repo | Việc của Phúc |
|---|---|
| Tuần 2 | Hoàn thiện benchmark/detector và dựng B5 bằng thư viện có sẵn |
| Tuần 3 | Chạy detector đối chứng trên pilot; triển khai B2 Random Forest và bàn giao B2/B5 |
| Tuần 4 | Chốt detector, độ phân giải; B6 trên graph con, cần chốt định nghĩa B6 trước |
| Tuần 5 | Thí nghiệm detection cho H1, tinh chỉnh baseline theo ngân sách công bằng |
| Tuần 6–7 | Community đối chứng, hỗ trợ B2/B5, ablation và độ nhạy |
| Tuần 8 | Kiểm tra tái lập, viết benchmark, detector và phần H1 |

Hoàn thành prototype tuần 1 trước khi mở rộng các phần này.

## 21. Nguồn đối chiếu và thứ tự đọc tiếp

Các link nội bộ dưới đây tính từ thư mục `document/`:

1. [Phân công 8 tuần](../PHAN-CONG-SNA-8-TUAN.md): đọc phần Phúc–Đăng tuần 1 và checklist trước báo cáo.
2. [Contracts](../src/reddit_sna/contracts.py): đọc `Membership`, `Event`, `SampleKey`, `TrackingLink`.
3. [Independent Leiden hiện có](../src/reddit_sna/detection/leiden.py): đọc chữ ký hàm, cách đọc R và cách xuất membership.
4. [Test detector hiện có](../tests/unit/test_leiden.py): xem ví dụ hai clique và graph rỗng.
5. [Notebook kế hoạch của cặp](../notebooks/detection_tracking/00_research_plan.ipynb): dùng các mục làm khung trình bày nghiên cứu.
6. [Kiến trúc](../ARCHITECTURE.md): tra ranh giới module, references và quy tắc đánh giá.
7. [Protocol nghiên cứu dự thảo](../experiments/study.toml): hiểu điều kiện đánh giá và các giả thuyết dài hạn.
8. [Tài liệu AMI chính thức](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_mutual_info_score.html): tra ý nghĩa điểm và cách gọi thư viện.
9. [Tài liệu Leiden](https://leidenalg.readthedocs.io/en/stable/intro.html): đọc nền tảng thuật toán khi đã chạy được ví dụ nhỏ.

**Bước bắt đầu ngay:** hoàn thành mục 5 với Đăng, sau đó làm phần ngày 16/10. Chỉ chuyển sang sáu sự kiện khi ví dụ nhỏ đã có graph, ground truth và một lần chạy detector có thể kiểm tra được.
