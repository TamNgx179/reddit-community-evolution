# BÁO CÁO PHÂN TÍCH ĐỘ NHẠY THEO NGƯỠNG GED

## 1. Mục tiêu

Phân tích độ nhạy của kết quả theo các ngưỡng phân loại sự kiện GED (Graph Evolution Detection), nhằm đánh giá mức độ ảnh hưởng của việc thay đổi ngưỡng liên kết cộng đồng (`link threshold`) và ngưỡng giải thể (`dissolve threshold`).

Phân tích tập trung vào ba nội dung:

- Số lượng ca thay đổi nhãn và trạng thái đủ điều kiện đánh giá.
- Mức độ thay đổi độ phủ của tập dữ liệu.
- Ảnh hưởng của các ngưỡng GED đến Macro-F1 của hai mô hình `hier_lr_dynamic` và `hier_hgb_dynamic` trên các dự báo frozen.

## 2. Phương pháp thực hiện

### 2.1. Các cấu hình ngưỡng

Sử dụng năm cấu hình để so sánh:

| Cấu hình | Link threshold | Dissolve threshold |
|---|---:|---:|
| Baseline | 0.50 | 0.10 |
| Link thấp | 0.45 | 0.10 |
| Link cao | 0.55 | 0.10 |
| Dissolve thấp | 0.50 | 0.05 |
| Dissolve cao | 0.50 | 0.15 |

Mỗi lần phân tích chỉ thay đổi một loại ngưỡng so với baseline để xác định ảnh hưởng của từng yếu tố.

### 2.2. Tái lập nhãn GED

Sử dụng dữ liệu membership theo tháng và logic phân loại sự kiện trong mã nguồn `src/reddit_sna/tracking/ged.py`.

Các trạng thái được phân biệt gồm:

- Sáu nhãn sự kiện: stable, grow, shrink, merge, split, dissolve.
- Unresolved: trường hợp không thể xác định chắc chắn sự kiện.
- Censored: trường hợp bị giới hạn bởi snapshot cuối cùng.

Unresolved và censored không được xem là dissolve. Chỉ các trường hợp có nhãn thuộc sáu lớp sự kiện mới được tính vào tập đánh giá.

Trước khi phân tích các cấu hình mới, kết quả baseline được đối chiếu với dữ liệu nhãn gốc. Kết quả tái lập khớp chính xác với baseline và các CSV lịch sử.

### 2.3. Đánh giá dự báo frozen

Sử dụng dự báo frozen tại:

`artifacts/acceptance/lan-week4-input-001/full-study-2016/artifacts/temporal/activity-study-001/stages/evaluation/attempt-001/predictions.csv`

Hai mô hình được đánh giá:

- `hier_lr_dynamic`
- `hier_hgb_dynamic`

Dữ liệu gồm 1.269 ca, với ba seed 42, 43 và 44 cho mỗi mô hình.

Macro-F1 được tính riêng cho từng seed theo quy ước cố định sáu lớp, sau đó lấy trung bình ba seed. Các seed không được xem là những quan sát độc lập.

Khi thay đổi ngưỡng, chỉ sử dụng những ca có dự báo frozen sẵn có. Không tạo dự báo giả định cho các ca mới đủ điều kiện và không huấn luyện lại mô hình.

Để tách ảnh hưởng của việc thay đổi tập đánh giá và việc đổi nhãn, sử dụng:

- **Selection effect:** Macro-F1 trên tập ca chung với nhãn cũ trừ Macro-F1 baseline trên toàn bộ tập frozen.
- **Label effect:** Macro-F1 trên tập ca chung với nhãn mới trừ Macro-F1 trên tập ca chung với nhãn cũ.

## 3. Kết quả phân tích GED

### 3.1. Thay đổi số lượng ca và độ phủ

Tập dữ liệu ban đầu có 11.745 ca, trong đó:

- 11.562 ca có thể quan sát.
- 7.490 ca đủ điều kiện đánh giá.
- 4.072 ca unresolved.
- 183 ca censored.

Độ phủ baseline là 64,78%.

| Link | Dissolve | Observed denominator | Eligible | Unresolved | Censored | Changed labels | Coverage |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.10 | 11.562 | 7.490 | 4.072 | 183 | 0 | 64,78% |
| 0.45 | 0.10 | 11.562 | 7.501 | 4.061 | 183 | 15 | 64,88% |
| 0.55 | 0.10 | 11.562 | 7.446 | 4.116 | 183 | 63 | 64,40% |
| 0.50 | 0.05 | 11.562 | 6.867 | 4.695 | 183 | 623 | 59,39% |
| 0.50 | 0.15 | 11.562 | 7.842 | 3.720 | 183 | 352 | 67,83% |

Kết quả cho thấy ngưỡng dissolve có ảnh hưởng lớn đến độ phủ. Khi giảm dissolve threshold xuống 0.05, số ca đủ điều kiện giảm từ 7.490 xuống 6.867. Ngược lại, khi tăng lên 0.15, số ca đủ điều kiện tăng lên 7.842.

Thay đổi link threshold tạo ra ảnh hưởng nhỏ hơn đến độ phủ. Khi giảm link threshold xuống 0.45, số ca đủ điều kiện tăng nhẹ. Khi tăng lên 0.55, số ca đủ điều kiện giảm.

### 3.2. Chuyển đổi nhãn

Một số chuyển đổi đáng chú ý:

- Với link threshold 0.45, một số ca unresolved được xác định lại thành grow hoặc merge; đồng thời có một số ca thay đổi giữa các nhãn sự kiện.
- Với link threshold 0.55, xuất hiện các chuyển đổi từ nhãn sự kiện sang unresolved, đặc biệt là merge sang unresolved.
- Với dissolve threshold 0.05, có 623 ca chuyển từ dissolve sang unresolved.
- Với dissolve threshold 0.15, có 352 ca chuyển từ unresolved sang dissolve.

Điều này cho thấy ngưỡng dissolve ảnh hưởng trực tiếp đến ranh giới giữa dissolve và unresolved. Vì vậy, việc lựa chọn ngưỡng có thể làm thay đổi đáng kể số lượng ca được đưa vào đánh giá.

## 4. Kết quả đánh giá frozen LR–HGB

### 4.1. Macro-F1 theo từng cấu hình

| Link | Dissolve | Model | Original F1 | Alternative F1 | Selection delta | Label delta |
|---:|---:|---|---:|---:|---:|---:|
| 0.45 | 0.10 | LR | 0.41174 | 0.40518 | 0.00000 | -0.00656 |
| 0.45 | 0.10 | HGB | 0.38805 | 0.38210 | 0.00000 | -0.00594 |
| 0.50 | 0.05 | LR | 0.41174 | 0.41356 | +0.00182 | 0.00000 |
| 0.50 | 0.05 | HGB | 0.38805 | 0.39120 | +0.00315 | 0.00000 |
| 0.50 | 0.10 | LR | 0.41174 | 0.41174 | 0.00000 | 0.00000 |
| 0.50 | 0.10 | HGB | 0.38805 | 0.38805 | 0.00000 | 0.00000 |
| 0.50 | 0.15 | LR | 0.41174 | 0.41174 | 0.00000 | 0.00000 |
| 0.50 | 0.15 | HGB | 0.38805 | 0.38805 | 0.00000 | 0.00000 |
| 0.55 | 0.10 | LR | 0.41174 | 0.40065 | -0.01608 | +0.00499 |
| 0.55 | 0.10 | HGB | 0.38805 | 0.37569 | -0.01352 | +0.00116 |

Trong bảng, Original F1 là Macro-F1 baseline trên toàn bộ 1.269 ca. Alternative F1 là Macro-F1 theo nhãn mới trên tập ca chung còn được giữ lại.

### 4.2. Phân tích ảnh hưởng

**Cấu hình link 0.45, dissolve 0.10**

Không có ca nào bị loại khỏi tập frozen, nhưng có một ca đổi nhãn. Macro-F1 giảm 0.00656 đối với LR và 0.00594 đối với HGB. Do đó, mức giảm đến từ thay đổi nhãn chứ không phải thay đổi thành phần tập đánh giá.

**Cấu hình link 0.50, dissolve 0.05**

Có 68/1.269 ca bị loại khỏi tập đánh giá và không có ca còn lại đổi nhãn. Macro-F1 tăng 0.00182 đối với LR và 0.00315 đối với HGB. Toàn bộ mức tăng đến từ selection effect.

Vì vậy, không thể diễn giải mức tăng này là mô hình dự báo tốt hơn. Đây là kết quả của việc đánh giá trên một tập ca nhỏ hơn.

**Cấu hình link 0.55, dissolve 0.10**

Có 7 ca bị loại và 4 ca còn lại đổi nhãn. Selection effect làm Macro-F1 giảm 0.01608 đối với LR và 0.01352 đối với HGB. Label effect bù lại một phần mức giảm, lần lượt là 0.00499 và 0.00116.

Sau khi kết hợp hai tác động, Macro-F1 vẫn thấp hơn baseline ở cả hai mô hình.

**Cấu hình link 0.50, dissolve 0.15**

Không có thay đổi đối với 1.269 ca frozen. Do đó, Macro-F1 của hai mô hình giữ nguyên so với baseline.

### 4.3. So sánh LR và HGB

Trong cả năm cấu hình, `hier_lr_dynamic` đều có Macro-F1 cao hơn `hier_hgb_dynamic`.

Tại baseline, LR đạt 0.41174 trong khi HGB đạt 0.38805. Thứ tự này không thay đổi khi điều chỉnh các ngưỡng GED.

## 5. Kết luận

Phân tích cho thấy ngưỡng GED có ảnh hưởng đến cả nhãn sự kiện lẫn độ phủ của tập dữ liệu. Trong các cấu hình được thử nghiệm, dissolve threshold tạo ra thay đổi lớn nhất về số lượng ca đủ điều kiện đánh giá.

Việc giảm dissolve threshold xuống 0.05 làm giảm độ phủ xuống 59,39%, đồng thời khiến 68 ca trong tập frozen bị loại. Macro-F1 tăng nhẹ nhưng mức tăng hoàn toàn đến từ thay đổi thành phần tập đánh giá, không phải từ việc đổi nhãn.

Ngược lại, link threshold 0.55 làm Macro-F1 giảm ở cả hai mô hình. Mặc dù việc đổi nhãn giúp bù lại một phần tác động tiêu cực của việc loại ca, kết quả cuối cùng vẫn thấp hơn baseline.

Trong phạm vi các cấu hình được thử nghiệm, baseline 0.50/0.10 là mốc so sánh phù hợp vì giữ nguyên tập đánh giá frozen và không tạo ra thay đổi nhãn. Tuy nhiên, kết quả này chưa đủ để khẳng định đây là ngưỡng tối ưu cho mọi tập dữ liệu hoặc mọi mục tiêu phân tích.

Một giới hạn quan trọng là các ca mới đủ điều kiện sau khi thay đổi ngưỡng không có dự báo frozen tương ứng. Vì vậy, phần đánh giá LR–HGB chỉ phản ánh tác động trên các ca có dự báo sẵn, không phải kết quả của một lần huấn luyện và đánh giá lại toàn bộ mô hình.

## 6. Tệp kết quả và khả năng tái lập

Các script được sử dụng:

- `scripts/analyze_ged_threshold_sensitivity.py`
- `scripts/analyze_ged_frozen_prediction_sensitivity.py`

Kết quả được lưu trong Git theo hai nhóm, nhằm phân biệt dữ liệu tổng hợp đã có từ đợt phân tích ngày 11/11 và các kết quả chi tiết được bổ sung trong lần tái lập ngày 19/11.

### 6.1. Các bảng tổng hợp đã có từ ngày 11/11

Các bảng tổng hợp được lưu tại:

`reports/tables/sna-feedback-20261111/`

| Tệp | Nội dung |
|---|---|
| `ged_threshold_sensitivity.csv` | Tổng hợp số ca, trạng thái và độ phủ theo ngưỡng |
| `ged_threshold_transitions.csv` | Số lượng ca chuyển đổi giữa các nhãn |
| `ged_frozen_prediction_sensitivity.csv` | Macro-F1 LR–HGB theo cấu hình ngưỡng |

Các bảng này được tái lập độc lập trong lần phân tích ngày 19/11 và kết quả khớp với dữ liệu đã lưu trước đó. Vì vậy, không tạo thêm bản sao của ba CSV này.

### 6.2. Các kết quả chi tiết bổ sung ngày 19/11

Các kết quả bổ sung được lưu tại:

`reports/tables/ged-threshold-sensitivity-20261119/`

| Tệp | Nội dung |
|---|---|
| `ged_threshold_case_changes.csv` | Chi tiết từng ca thay đổi nhãn hoặc trạng thái đủ điều kiện theo từng cấu hình ngưỡng |
| `ged_frozen_prediction_sensitivity_per_seed.csv` | Kết quả đánh giá frozen chi tiết theo từng mô hình và seed |

Thư mục này còn có `README.md` mô tả nội dung và `manifest.json` lưu thông tin cấu hình, nguồn dữ liệu, đường dẫn script, kết quả và SHA256 để hỗ trợ kiểm tra tính toàn vẹn.

### 6.3. Kết quả chạy trung gian

Thư mục `analysis_outputs_20261119_ged_sensitivity/` được sử dụng làm nơi lưu kết quả chạy và kiểm tra trong quá trình phân tích trên máy cá nhân. Đây không phải thư mục kết quả chính thức được đưa vào Git.

Các tệp trong thư mục này gồm những bản kết quả tái lập trung gian, chẳng hạn:

- `ged_threshold_sensitivity_reproduced.csv`
- `ged_threshold_case_changes_reproduced.csv`
- `ged_threshold_transitions_reproduced.csv`
- `ged_frozen_prediction_sensitivity_reproduced.csv`
- `ged_frozen_prediction_sensitivity_per_seed.csv`

### 6.4. Khả năng tái lập

Kết quả baseline GED khớp chính xác với nhãn gốc. Các bảng tổng hợp theo cấu hình ngưỡng và kết quả Macro-F1 frozen cũng được tái lập khớp với các bảng lịch sử ở cả 10 dòng kết quả.

Phân tích sử dụng dữ liệu membership và dự báo frozen có sẵn. Không có bước huấn luyện lại mô hình trong quá trình thực hiện.

Unresolved và censored được giữ tách biệt, không được quy đổi thành dissolve khi tính Macro-F1 sáu lớp. Các kết quả LR–HGB chỉ phản ánh những ca có dự báo frozen tương ứng, không đại diện cho việc huấn luyện và đánh giá lại trên toàn bộ tập dữ liệu.