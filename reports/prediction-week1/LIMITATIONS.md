# Limitations and Remaining Work

## 1. Phạm vi dữ liệu

Run tham chiếu Week 1 (`lan-demo-final-20261020`) dùng dữ liệu `synthetic`, seed 42. Kết quả kiểm tra luồng prototype table → temporal split → baseline prediction → evaluation; không phải kết quả dự báo trên cộng đồng Reddit thật.

Hoàn tất các stage với trạng thái `complete_through_baselines` không có nghĩa tracking, feature engineering, mô hình dự báo đầy đủ hoặc pipeline Reddit end-to-end đã hoàn tất. Kết quả cũng không tự xác nhận giả thuyết H3 hoặc chứng minh tính mới khoa học.

## 2. Phạm vi mô hình

Run tham chiếu đánh giá ba baseline:

- B1 Majority.
- B1 Persistence.
- B4 Logistic Regression.

B2 Random Forest, B5 Gradient Boosting, HeTCo và feature từ Reddit thật nằm ngoài phạm vi run này. Không đưa ra so sánh với các mô hình chưa được chạy trong cùng điều kiện, cùng mẫu và cùng quy trình đánh giá.

## 3. Temporal split và leakage

Run tham chiếu có:

- Train: 1.000 mẫu, 23 `label_month`.
- Validation: 263 mẫu, 6 `label_month`.
- Test: 261 mẫu, 6 `label_month`.
- Mẫu không nhãn bị loại: 46.

Split phải giữ mỗi `label_month` hoàn chỉnh trong một tập. Quan hệ nhãn dự kiến là `label_month == next_month(feature_month)`, dùng `next_month()` từ `contracts.py`. Các sample checks và negative-control fixture `tests/fixtures/prediction/samples_leaky.csv` hỗ trợ kiểm tra một số rủi ro leakage đã biết.

Những kiểm tra này không chứng minh mọi dạng leakage đã bị loại bỏ. Cần review feature catalog và code thực tế, bảo đảm feature chỉ dùng dữ liệu khả dụng tại thời điểm dự báo. Không dùng `community_id` làm feature hoặc xem nó là identity xuyên tháng. `prev_label` là lịch sử riêng cho B1 Persistence; không được gộp vào numeric feature set của B4.

## 4. Metrics và diễn giải

Metrics trên test của run tham chiếu:

| Model | n | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|
| B1 Majority | 261 | 0.1125 | 0.1667 |
| B1 Persistence | 261 | 0.2557 | 0.2586 |
| B4 Logistic Regression | 261 | 0.2160 | 0.2155 |

B1 Persistence đạt macro-F1 cao nhất trong ba baseline trên test của run synthetic này. Test gồm 261 mẫu trên sáu `label_month`; tài liệu hiện tại không đưa ra khoảng tin cậy hay kiểm định thống kê. Không diễn giải các con số này thành kết luận về dữ liệu Reddit thật hoặc mọi lần chạy synthetic.

Theo quy ước hiện tại, `macro_f1` trung bình trên các lớp có support trong `y_true`; `macro_f1_six` tính trên đủ sáu lớp với `zero_division=0`. Hai chỉ số trùng nhau trong run này; không giả định điều đó đúng cho run khác. Khi diễn giải từng lớp, cần xem `per_class.csv` và confusion matrices, không chỉ xem điểm tổng hợp.

## 5. Trạng thái pipeline và kiểm thử

Manifest của `lan-demo-final-20261020` ghi `status: complete_through_baselines`, `data_kind: synthetic`, seed 42, revision `696cbb61da2faebb75f06a701afee943fe0199c0`, `dirty: false`; các stage table, split, baselines và evaluation đều `complete`.

Lần chạy test được cung cấp cho tài liệu này hoàn tất với:

```text
Ran 253 tests in 94.716s

OK
```

Đây là kết quả của lần chạy test được báo cáo. Test pass hỗ trợ độ tin cậy về hành vi phần mềm trong phạm vi được kiểm thử; không thay thế đánh giá nghiên cứu hoặc đánh giá ngoài mẫu trên Reddit thật.

## 6. Artifact, run ID và khả năng tái lập

Mỗi lần chạy mới phải dùng run ID chưa tồn tại; không ghi đè run cũ. Khi báo cáo kết quả, ghi run ID và lấy `manifest.json`, `split_summary.csv`, `metrics.csv`, `per_class.csv`, `predictions.csv` từ cùng một thư mục `artifacts/prediction/<run_id>/`.

Các run khác có thể dùng seed, revision hoặc dữ liệu tổng hợp khác, nên số lượng mẫu và metrics có thể khác nhau. Không trộn kết quả của các run. Một lần chạy mới không tự động xác nhận lại số liệu của run tham chiếu.

## 7. Notebook nghiên cứu

`notebooks/prediction/00_research_plan.ipynb` sử dụng run tham chiếu lan-demo-final-20261020 và trình bày các giới hạn nghiên cứu. Notebook không thay thế entry point của pipeline. Khi thay đổi source, cấu hình hoặc run tham chiếu, cần kiểm tra lại bằng chứng và bảo đảm các kết quả được trích dẫn vẫn thuộc đúng run.

## 8. Công việc còn lại

- Review chéo schema, ranh giới `label_month`, feature availability, fallback behavior và metrics.
- Dùng artifact của đúng run khi cập nhật báo cáo hoặc slide.
- Bổ sung và đánh giá các mô hình/dữ liệu Reddit thật theo phạm vi các tuần tiếp theo.
- Trình bày rõ đây là prototype synthetic và không đưa ra tuyên bố khoa học vượt quá bằng chứng hiện có.
- Chỉ ghi nhận contribution là reviewed khi review thực tế đã diễn ra.