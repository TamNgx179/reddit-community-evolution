# Phân công Phúc–Đăng tuần 1: benchmark, detection và tracking

> **Theo dõi phần Phúc:** xem [bộ specs](specs/phuc/README.md) và [task list có trạng thái/bằng chứng](specs/phuc/tasks.md). File phân công này giữ vai trò quy định trách nhiệm và giao diện v1; trạng thái triển khai của Phúc cập nhật tại task list.

> **Người đề xuất:** Phúc. **Phiên bản:** v1, ngày 16/10/2026.
>
> **Mốc nội bộ:** hoàn thành demo trước tối **20/10/2026**; ngày 21/10 chạy lại và diễn tập; báo cáo ngày **22/10/2026** theo lịch repo.
>
> Phúc chủ động đưa ra phạm vi, giao diện và cấu hình dưới đây để hai người có thể bắt đầu ngay. Đây là phương án triển khai v1 gửi Đăng phản hồi, chưa ghi nhận Đăng đã đồng ý hoặc hoàn thành công việc. Các quyết định kỹ thuật mới được ghi là mặc định v1; nếu cần đổi, ghi phiên bản và thông báo phần bị ảnh hưởng. Phúc có thể triển khai phần của mình và fixture bàn giao ngay trong lúc Đăng xem tài liệu.
>
> Tài liệu này quy định công việc chung của cặp. [Kế hoạch cá nhân chi tiết của Phúc](PLAN-PHUC-TUAN-1.md) giải thích thêm thuật ngữ, cài đặt và cách thực hiện. Tài liệu không tạo code, dữ liệu hoặc kết quả thí nghiệm.

## 1. Đầu ra chung cần hoàn thành

Một demo chạy được theo hai đường:

```text
Đường A — kiểm tra riêng tracker:
Membership chuẩn -> Jaccard tracker -> so với sự kiện chuẩn

Đường B — kiểm tra toàn luồng:
Graph tổng hợp -> Independent Leiden -> membership dự đoán
    -> Jaccard tracker -> đánh giá sự kiện trên các nguồn chuẩn
```

Phúc trình bày cách sinh dữ liệu, detection và AMI. Đăng trình bày quy tắc tracking, F1 từng sự kiện và confusion matrix. Cả hai giải thích được một trường hợp sai.

**Phạm vi tuần 1:** mạng tổng hợp nhỏ có ground truth và sáu sự kiện. B2/B5/B6, GED, HeTCo, temporal/consensus và chạy toàn bộ Reddit để các tuần sau. Dùng lại Leiden đã có trong repo.

## 2. Phân công cụ thể

### 2.1. Phúc phụ trách

| Mã | Công việc | Đầu ra bàn giao | Hạn nội bộ |
|---|---|---|---|
| P01 | Tạo fixture membership chuẩn của `stable` và `grow`, hai tháng | `truth/membership.csv`, `truth/events.csv`, `truth/links.csv`, metadata | Tối 16/10 |
| P02 | Sinh graph, lưu node hoạt động, seed và cấu hình | `snapshots/<month>/R.csv`, `nodes.csv`, `metadata.json` | Bộ đầu tiên 17/10 |
| P03 | Gọi Independent Leiden hiện có, xuất membership và diagnostics | `memberships/<month>/membership-seed*.csv`, `detection.json` | Bộ đầu tiên 17/10 |
| P04 | Kiểm tra khóa, endpoint, isolate, căn user và tính AMI/coverage | `detection_metrics.csv` và kiểm tra liên quan | Bản đầu 17/10; đủ case 18/10 |
| P05 | Hoàn thiện đủ sáu tình huống, toàn bộ ground truth | Suite development và các test generator | 18/10 |
| P06 | Lưu protocol, chạy detector trên lịch giữ lại sau khi khóa | Cấu hình, manifest, bảng chi tiết và tổng hợp evaluation | 19/10 |
| P07 | Giữ đầu mối ghép pipeline và notebook; viết hướng dẫn phần dữ liệu/detection | Demo chung và phần báo cáo của Phúc | 20/10 |

Phúc chịu trách nhiệm sửa lỗi generator, graph, membership detector và cách tính AMI. Phúc hỗ trợ giải thích dữ liệu khi Đăng phát hiện tình huống tracking khó.

### 2.2. Đăng phụ trách

| Mã | Công việc | Đầu ra bàn giao | Hạn nội bộ |
|---|---|---|---|
| D01 | Đọc fixture, kiểm tra schema, gom user thành tập thành viên từng nhóm | Hàm đọc/kiểm tra membership; xác nhận dữ liệu đọc được | Tối 16/10 hoặc lần ghép đầu 17/10 |
| D02 | Triển khai Jaccard tracker theo quy tắc v1 | Code tính liên kết, sự kiện và diagnostics | Bản đầu 17/10 |
| D03 | Kiểm tra sáu sự kiện trên membership chuẩn, thêm fixture mơ hồ | Test stable/grow/shrink/merge/split/dissolve và precedence | 18/10 |
| D04 | Đánh giá tracker trên truth: F1, support và confusion matrix | `truth_tracking/` và bảng kết quả | Bản đầu 18/10; khóa 19/10 |
| D05 | Ghép cộng đồng detector với truth để đánh giá toàn luồng | Bảng mapping, nguồn thiếu, nhóm dư và kết quả sự kiện | 19/10 |
| D06 | Viết phần tracking, ví dụ lỗi và hướng dẫn đọc kết quả | Hàm/đoạn trình bày để Phúc ghép notebook, bảng/hình có nguồn | 20/10 |

Đăng chịu trách nhiệm sửa lỗi tracker, mapping cộng đồng, tính chỉ số sự kiện và thứ tự xử lý sự kiện. Đăng có thể bắt đầu D01–D03 bằng membership chuẩn, không phải chờ graph hoặc Leiden.

### 2.3. Cùng làm

- Kiểm tra danh sách thành viên và nhãn chuẩn của sáu tình huống trước evaluation.
- Ghép thử bằng file thật vào ngày 17/10; phản hồi lỗi bằng case, tháng, file và ví dụ cụ thể.
- Khóa cấu hình trước khi xem evaluation ngày 19/10.
- Đối chiếu lỗi detection với tracking, không quy trách nhiệm chỉ từ một con số tổng hợp.
- Chạy lại demo từ kernel sạch và output mới; review phần của nhau trước khi merge.

## 3. Quyết định kỹ thuật mặc định v1

Các mặc định này dùng để bắt đầu development. Chỉ thay sau khi ghi rõ lý do và phiên bản; evaluation phải dùng cấu hình đã khóa.

| Nội dung | Mặc định v1 |
|---|---|
| Dữ liệu | Tổng hợp, không phải Reddit thật |
| Thời gian mỗi dataset | Hai tháng liên tiếp: `2020-01`, `2020-02`, chỉ là mốc giả lập |
| Tách dataset | Mỗi case × mức khó × seed generator là một dataset riêng |
| Graph | Vô hướng, không cạnh trùng/self-loop, weight `1.0` |
| Sinh cạnh mức dễ | `p_in = 0.50`, `p_out = 0.02` |
| Lịch generator development | `11, 12, 13`; dùng seed 11 để ghép trước |
| Lịch generator evaluation | `101, 102, 103`, chỉ chạy sau khóa protocol |
| Detector | Independent Leiden có sẵn; gamma `1.0`; seeds `0, 1, 2` |
| Đầu ra detector chính để ghép tracker | Seed `0`; không chọn seed điểm cao nhất |
| Protocol graph tổng hợp | `synthetic-planted-undirected-v1`; thứ tự ID user/cạnh cố định |
| Jaccard liên kết | `J >= 0.30` |
| Ngưỡng kích thước cho liên kết một–một | Tăng trên 10% là grow, giảm trên 10% là shrink; còn lại stable |
| Trường hợp vừa nhiều nguồn vừa nhiều đích | Ưu tiên split tại nguồn, gắn cờ mơ hồ |
| Chấm nguồn detector với nguồn truth | Greedy một–một theo Jaccard, ngưỡng `0.30`, tie-break cố định |
| AMI | Trên user có prediction, báo kèm coverage trên toàn bộ node hoạt động |
| Macro-F1 sự kiện | Sáu nhãn cố định, `zero_division=0`, báo support và nguồn chưa ghép |

Ba seed detector trên cùng graph không phải ba dataset độc lập. Không đặt điều kiện hoàn thành là AMI/F1 phải vượt một ngưỡng điểm tùy ý.

## 4. Sáu tình huống chuẩn Phúc tạo

Mỗi dataset có một nhóm nền K gồm 12 người, tiếp tục ổn định qua hai tháng. K dùng tập user riêng, không chia sẻ thành viên với A/B/C. Nhóm nền vẫn được gán nhãn và chấm điểm như các nguồn khác.

| Case | Tháng t, ngoài K | Tháng t+1, ngoài K | Ground truth cho các nguồn cần chú ý |
|---|---|---|---|
| `stable` | A: 12 người | C: đúng 12 người của A | A -> C: stable |
| `grow` | A: 12 người | C: 12 người cũ + 6 người mới | A -> C: grow |
| `shrink` | A: 18 người | C: giữ 12 trong 18 người cũ | A -> C: shrink |
| `merge` | A và B: mỗi nhóm 12 người | C: hợp của A và B, 24 người | A -> C: merge; B -> C: merge |
| `split` | A: 24 người | B và C: mỗi nhóm 12 người, chia đôi A | A -> B và C: một nhãn split |
| `dissolve` | A: 12 người | A và các thành viên của A không còn trong node hoạt động; K tiếp tục | A: dissolve, không có đích |

Tên nhóm đích khác nguồn để phát hiện code dựa vào tên thay vì tập thành viên. User ID giữ nhất quán trong mỗi dataset.

Ground truth được sinh từ kịch bản thành viên trước khi chạy thuật toán, không lấy kết quả Jaccard làm đáp án. Với dissolve, biết tháng sau được quan sát và A được bộ sinh chủ động loại khỏi hoạt động; không diễn giải thành người dùng Reddit thật rời mạng xã hội.

Không âm thầm thêm cạnh, bỏ isolate hoặc đổi seed để nâng điểm. Trường hợp khó bổ sung sau sáu case: nhóm nhỏ/cạnh nhiễu, hoặc membership có cả split và merge. Mọi thay đổi lịch đánh giá phải được ghi trước khi xem kết quả giữ lại.

## 5. File bàn giao và schema thống nhất

### 5.1. Vị trí output

```text
artifacts/detection-tracking/<run_id>/
├── manifest.json
├── benchmark_config.json
├── datasets/<dataset_id>/
│   ├── metadata.json
│   ├── snapshots/<month>/
│   │   ├── R.csv
│   │   └── nodes.csv
│   ├── truth/
│   │   ├── membership.csv
│   │   ├── events.csv
│   │   └── links.csv
│   ├── memberships/<month>/membership-seed0.csv
│   └── detection.json
├── detection_metrics.csv
├── detection_summary.csv
├── tracking/
│   ├── truth_tracking/
│   └── detector_seed0_tracking/
└── figures/
```

Các membership seed 1/2 lưu theo cách detector hiện có, dù tracker chính chỉ dùng seed 0 trong v1. Đây là output dự kiến, chưa phải artifact có sẵn.

- `dataset_id` ví dụ: `dev-grow-easy-g11` hoặc `eval-merge-easy-g101`.
- Mỗi run dùng thư mục mới, không ghi đè run cũ hoặc ghi output vào `data/`.
- Detector tự tạo thư mục `memberships`; caller không tạo trước thư mục đó.
- Metadata ánh xạ `dataset_id`, identity scope, reference chuẩn, reference detector và seed.

### 5.2. Membership — cả truth và prediction dùng bốn cột

```csv
reference_id,month,community_id,user_id
truth-dev-grow-easy-g11,2020-01,A,u001
truth-dev-grow-easy-g11,2020-02,C,u001
```

Ví dụ trên chỉ minh họa header và hai bản ghi, không phải dataset hoàn chỉnh.

Quy tắc:

1. Một `(reference_id, month, user_id)` có đúng một community.
2. Trong mỗi reference, cùng user ID là cùng người qua các tháng.
3. Community ID là cục bộ theo tháng, không mang sẵn quan hệ theo thời gian.
4. Truth và detector dùng reference khác nhau; evaluator ghép qua metadata và user, không sửa reference cho giống nhau.
5. Tracker chỉ nối các tháng trong cùng một reference. Không trộn truth với detector hoặc hai seed detector.
6. Truth bao phủ node hoạt động; detector hiện chỉ gán node có cạnh. Phúc báo coverage và isolate riêng.

### 5.3. Sự kiện chuẩn và dự đoán

```csv
reference_id,source_month,source_community_id,target_month,event
truth-dev-grow-easy-g11,2020-01,A,2020-02,grow
```

Một dòng cho mỗi cộng đồng nguồn. Danh sách sự kiện và thứ tự báo cáo cố định:

```text
stable, grow, shrink, merge, split, dissolve
```

### 5.4. Liên kết chuẩn và dự đoán

```csv
reference_id,source_month,source_community_id,target_month,target_community_id
truth-dev-grow-easy-g11,2020-01,A,2020-02,C
```

- Merge: nhiều nguồn nối một đích.
- Split: một nguồn có nhiều dòng liên kết, nhưng chỉ một dòng sự kiện.
- Dissolve: có dòng sự kiện, không có dòng liên kết đích.
- Nhóm đích mới không có nguồn: ghi trong diagnostics `forming_targets`; không tạo mẫu nguồn không tồn tại.
- Tháng cuối thiếu tháng kế tiếp: không sinh sự kiện; ghi trạng thái thiếu successor.

### 5.5. Graph và node do Phúc xuất

```csv
month,source_user_id,target_user_id,weight
2020-01,u001,u002,1.0
```

```csv
month,user_id
2020-01,u001
2020-01,u002
```

File đầu là `R.csv`, file sau là `nodes.csv`. Header R theo đúng detector hiện tại. `nodes.csv` là contract benchmark mới cho danh sách node hoạt động, gồm cả isolate; tracker có thể đọc để cảnh báo độ phủ.

## 6. Quy tắc Jaccard tracker v1 để Đăng triển khai

### 6.1. Tạo liên kết

Với cộng đồng nguồn A tại t và cộng đồng đích B tại t+1:

```text
J(A, B) = |A giao B| / |A hợp B|
```

Tạo liên kết nếu `J >= 0.30`, gồm cả bằng 0.30. Giữ toàn bộ liên kết vượt ngưỡng, không chỉ giữ đích tốt nhất; nếu chỉ giữ một đích sẽ mất split.

Không chấp nhận cộng đồng rỗng. Kiểm tra t+1 tồn tại trong metadata quan sát trước khi gán nhãn. Nếu graph t+1 rỗng nhưng tháng vẫn được quan sát, ghi diagnostics rõ; nếu tháng không được quan sát, không gán dissolve.

### 6.2. Gán một nhãn cho mỗi nguồn theo thứ tự sau

```text
Nếu không có tháng kế tiếp được quan sát:
    không gán sự kiện, ghi thiếu successor
Ngược lại, nếu nguồn không có liên kết đích:
    dissolve
Ngược lại, nếu nguồn có từ hai đích trở lên:
    split
Ngược lại, nguồn có đúng một đích B:
    nếu B nhận liên kết từ từ hai nguồn trở lên:
        merge
    ngược lại:
        growth = (size(B) - size(A)) / size(A)
        growth > 0.10  -> grow
        growth < -0.10 -> shrink
        còn lại        -> stable
```

- Bằng +10% hoặc -10% vẫn là stable trong v1; Đăng viết test hai biên này.
- Trường hợp nhiều nguồn/nhiều đích áp dụng split trước merge tại nguồn; ghi `ambiguous_many_to_many=true` nếu nguồn nhiều đích và có đích nhiều nguồn.
- `dissolve` của tracker là kết quả theo quy tắc và mức quan sát, có thể sai vì detection/coverage. Không coi đây là sự thật xã hội.
- Không lấy truth events làm đầu vào tracker.

### 6.3. Giao diện trong Python đề xuất

Đăng cung cấp hàm trong `src/reddit_sna/tracking/jaccard.py` với giao diện:

```python
track_memberships(
    memberships,        # Sequence[Membership] của một reference
    source_month,      # ví dụ "2020-01"
    target_month,      # ví dụ "2020-02"
    *,
    tau=0.30,
    size_tolerance=0.10,
    target_observed=True,
)
```

Trả dictionary với `links`, `events`, `diagnostics`; rows của links/events theo schema mục 5. Nếu `target_observed=False`, trả events/links rỗng với trạng thái thiếu successor; không coi danh sách target rỗng là bằng chứng thiếu quan sát hoặc ngược lại. Ghi kiểu/schema thực tế trong docstring khi triển khai.

Phúc đọc CSV thành `Membership` hoặc dùng adapter Đăng bàn giao. Hàm tracker không import notebook/CLI/pipeline và không tự chọn run đầu vào.

## 7. Quy định đánh giá và nguồn lỗi

### 7.1. Phúc: đánh giá detection

- Đối chiếu user trong cùng dataset/tháng, không so trực tiếp mã community.
- Kiểm tra tập user detector khớp endpoint; duplicate hoặc user lạ là lỗi dữ liệu.
- Tính AMI trên user có prediction, báo `assigned_nodes / active_nodes`, isolate và số nhóm ở tập được chấm.
- Lưu từng seed detector; seed 0 là đầu ra chính, các seed còn lại là diagnostics.
- Lưu wall time sinh graph, detection và evaluation với phạm vi đo rõ. Peak memory chưa đo thì để null.

### 7.2. Đăng: tracker trên membership chuẩn

- Chấm tất cả nguồn chuẩn có successor được quan sát, gồm cả nhóm nền.
- Xuất macro-F1 sáu lớp và F1/support từng lớp, `zero_division=0`.
- Xuất confusion matrix 6 × 6 với thứ tự nhãn ở mục 5.
- Nếu tracker không xuất một nguồn đáng lẽ phải có, báo lỗi/missing output; không bỏ nguồn đó khỏi bảng để tăng điểm.
- Điểm thấp phải được xem xét bằng fixture/thành viên, không sửa truth theo dự đoán.

### 7.3. Đăng: mapping và điểm sự kiện toàn luồng

Áp dụng mapping cho cộng đồng **tháng nguồn**, riêng từng dataset và detector reference:

1. Tính Jaccard mọi cặp cộng đồng truth–detector trên tập thành viên nguồn.
2. Giữ cặp có Jaccard `>= 0.30`.
3. Sắp giảm dần Jaccard; nếu bằng nhau, sắp tăng theo truth community ID rồi detector community ID.
4. Duyệt theo thứ tự; ghép nếu cả nguồn truth và detector chưa được dùng. Mỗi bên tối đa một ghép.
5. Với nguồn truth đã ghép, dùng sự kiện tracker dự đoán của nguồn detector tương ứng để chấm.
6. Nguồn truth chưa ghép hoặc nguồn detector được ghép nhưng thiếu event: giữ hàng đánh giá, `y_pred=__unmatched__`, ghi lý do.

Đây là greedy matching dễ triển khai, không phải phép ghép tối ưu tổng thể; báo rõ hạn chế khi các phân hoạch khác nhau nhiều.

Xuất kết quả:

- `source_mapping.csv`: truth source, detector source, Jaccard, trạng thái ghép.
- `event_predictions.csv`: một hàng mỗi nguồn truth, nhãn chuẩn, nhãn dự đoán/trạng thái thiếu.
- Macro-F1 trên sáu nhãn thật với toàn bộ nguồn truth; `__unmatched__` được tính là bỏ sót lớp thật tương ứng, không loại hàng.
- `__unmatched__` là trạng thái evaluator, không phải sự kiện thứ bảy trong `Event` và không ép vào dataclass dự báo yêu cầu Event.
- Confusion matrix toàn luồng: sáu hàng truth, bảy cột prediction gồm sáu nhãn và unmatched.
- Nếu báo thêm F1 trên tập matched, ghi rõ là điểm có điều kiện và báo matched coverage.
- Báo số cộng đồng detector dư không ghép được và nguồn truth thiếu. Nhóm detector dư được thống kê riêng, chưa bị phạt như mẫu nguồn trong điểm F1 này.

Điểm trên là **đánh giá sự kiện ở các nguồn chuẩn**. Không gọi nó là thước đo đầy đủ cho mọi lỗi liên kết/nhóm dư của toàn pipeline. Mapping dùng truth chỉ ở evaluator, không đưa vào thuật toán lúc chạy.

## 8. Tổ chức source để hai người làm song song

| File/module | Người giữ đầu mối |
|---|---|
| `src/reddit_sna/benchmarks/dynamic.py` | Phúc |
| `src/reddit_sna/evaluation/detection.py` | Phúc |
| `src/reddit_sna/tracking/jaccard.py` | Đăng |
| `src/reddit_sna/evaluation/tracking.py` | Đăng |
| Test generator và detection evaluation | Phúc |
| Test tracker, precedence, mapping và chỉ số sự kiện | Đăng |
| `configs/benchmark_week1.json`, `pyproject.toml` | Phúc ghép thay đổi; Đăng báo dependency/config cần thêm |
| `src/reddit_sna/pipelines/detection_tracking.py` | Phúc ghép lời gọi hai phần, Đăng kiểm tra nhánh tracking |
| `notebooks/detection_tracking/01_synthetic_demo.ipynb` | Phúc giữ file ghép; Đăng bàn giao code gọi module, bảng và nội dung tracking |

Tên file mới là phương án dự kiến, chưa được tạo bởi tài liệu này. Giữ source theo chức năng, không tạo cây source riêng theo tên người. Nếu Đăng cần file mới ngoài phạm vi trên, báo đường dẫn để tránh cùng sửa.

Config TOML hiện không nhận trường lạ. Dùng JSON benchmark riêng cho v1, không tự thêm `[benchmark]` mà chưa cập nhật parser. Phúc bổ sung dependency AMI/metrics vào cấu hình cài đặt khi thực sự triển khai; không chỉ cài tay rồi bàn giao.

Notebook đầy đủ được chấp nhận cho demo tuần 1 theo phân công repo. Lệnh `reddit_sna run` hiện còn khung; chỉ ghi là chạy được sau khi pipeline đã triển khai và kiểm tra.

## 9. Lịch bàn giao đến 20/10

| Ngày | Phúc | Đăng | Kết quả chung cần thấy |
|---|---|---|---|
| **16/10 — hôm nay** | Xuất fixture stable/grow hai tháng, truth events/links, metadata và schema | Đọc fixture, gom tập thành viên; bắt đầu Jaccard theo v1 | File Phúc xuất đọc được bằng code Đăng, hoặc có lỗi cụ thể để sửa |
| **17/10** | Sinh graph đầu tiên, chạy Leiden seed 0, tính AMI | Tracker stable/grow trên truth; nhận thử membership detector | Chạy được lần ghép đầu, chưa đợi đủ sáu case |
| **18/10** | Đủ sáu case development, seeds detector 0/1/2 | Test đủ sáu sự kiện; hoàn thiện evaluation và mapping | Có cả kết quả riêng tracker và bản đầu toàn luồng |
| **19/10** | Khóa benchmark/detector, chạy evaluation seeds riêng | Khóa tracker/evaluator; xuất F1, support, mapping, confusion matrix | Bảng kết quả giữ lại, log, ví dụ sai và giới hạn |
| **20/10** | Ghép notebook/hướng dẫn và phần detection | Bàn giao phần tracking, kiểm tra bảng/hình và demo | Run All từ đầu, output mới, hai người giải thích được phần mình |
| **21/10** | Sửa lỗi tái lập, diễn tập | Sửa lỗi tái lập, diễn tập | Ngày dự phòng theo lịch repo |
| **22/10** | Trình bày detection | Trình bày tracking | Báo cáo ba cặp theo phân công chung |

Không cần chờ toàn bộ module mới giao. Mỗi lần giao ghi: run/dataset ID, đường dẫn file, lệnh hoặc hàm đọc, điều đã kiểm tra và lỗi còn lại.

## 10. Checklist kiểm tra bắt buộc

### Phúc

- [ ] Cùng config/seed sinh cùng nội dung graph/truth và thứ tự ổn định.
- [ ] Sáu case có đúng thay đổi thành viên; các nguồn nền cũng có nhãn.
- [ ] Membership chuẩn không thiếu/trùng user hoạt động.
- [ ] Graph không self-loop, cạnh trùng, weight lỗi hoặc user lạ.
- [ ] Căn đúng user khi chấm; đổi tên nhóm không làm đổi AMI.
- [ ] Isolate/coverage không bị che giấu bởi phép lấy giao user.
- [ ] Lưu cấu hình, lịch seed, trạng thái, phiên bản và kết quả chi tiết.

### Đăng

- [ ] Tracker chạy được sáu sự kiện trên truth.
- [ ] Có test Jaccard bằng ngưỡng, growth ±10% và many-to-many.
- [ ] Thiếu tháng sau không bị gán dissolve.
- [ ] Split giữ nhiều liên kết nhưng chỉ một nhãn nguồn.
- [ ] Mapping không dựa vào tên community, xử lý tie có thứ tự cố định.
- [ ] Nguồn truth chưa ghép vẫn được ghi và phản ánh trong đánh giá.
- [ ] Báo support, missing output, nhóm dư và quy ước macro-F1.

### Cả hai

- [ ] Development/evaluation tách seed; cấu hình khóa trước evaluation.
- [ ] Demo có hai đường A/B và ít nhất một phân tích lỗi cụ thể.
- [ ] Restart Kernel -> Run All thành công với output mới.
- [ ] Test liên quan chạy thật; báo skip/lỗi/chưa chạy nếu có.
- [ ] Tài liệu ghi đúng kết quả tổng hợp, không gọi là kết quả Reddit.
- [ ] Hoàn thành chỉ khi có code, lệnh/notebook và artifact kiểm tra được.

## 11. Cách phản hồi để không kéo dài việc chốt

Phúc gửi file này và bắt đầu P01. Đăng có thể bắt đầu phần đọc membership/Jaccard từ schema đã ghi. Nếu có điểm không phù hợp, phản hồi theo mẫu ngắn:

```text
Mục muốn đổi:
Phương án thay thế cụ thể:
Lý do và phần code/file bị ảnh hưởng:
Mốc bàn giao có thay đổi không:
```

Không cần chờ thảo luận toàn bộ mới làm các bước độc lập. Những thay đổi ảnh hưởng schema hoặc semantics phải cập nhật phiên bản và thông báo trước khi ghép; không âm thầm đổi header/ngưỡng/nhãn. Phần nào thiếu do chưa bàn giao thì báo riêng, không tự nhập đáp án để hoàn thành demo.

Lời nhắn kèm file để Phúc tự gửi:

> Đăng ơi, mình viết trước phân công và giao diện v1 để hai đứa bắt tay làm luôn. Mình làm dữ liệu, ground truth, Leiden và AMI; bạn làm Jaccard, đánh giá sự kiện và mapping toàn luồng. Hôm nay mình bắt đầu fixture stable/grow hai tháng theo schema trong file; bạn có thể viết phần đọc membership và Jaccard trước, chưa phải đợi detector. Mục nào bạn thấy cần đổi thì ghi phương án cụ thể giúp mình, còn các bước độc lập mình triển khai ngay. Mốc là 17 ghép lần đầu, 18 đủ sáu sự kiện, 19 chạy đánh giá, tối 20 hoàn thành demo nhé.

## 12. Nguồn đối chiếu

- [Phân công chung tuần 1 và lịch báo cáo](../PHAN-CONG-SNA-8-TUAN.md).
- [Kế hoạch cá nhân Phúc](PLAN-PHUC-TUAN-1.md).
- [Contracts và sáu sự kiện](../src/reddit_sna/contracts.py).
- [Detector Independent Leiden hiện có](../src/reddit_sna/detection/leiden.py).
- [Kiến trúc, tham chiếu và giới hạn đánh giá](../ARCHITECTURE.md).

Các ngưỡng, mapping, fixture và API tracker v1 trong tài liệu này là thiết kế để triển khai, không phải bằng chứng thuật toán đã được kiểm chứng. Nếu đổi bản v1, ghi lịch sử thay đổi tại đây cùng lý do, ngày và người thực hiện.
