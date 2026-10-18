# Progress — Lan Anh



## Phạm vi công việc



Phụ trách đánh giá cho prototype dự báo tiến hóa cộng đồng:

- Temporal split theo `label_month`.

- Kiểm tra tính hợp lệ của mẫu và nguy cơ leakage.

- Tính metrics, per-class metrics và confusion matrices.

- Tích hợp evaluation vào prediction pipeline.

- Viết hướng dẫn đọc kết quả và giới hạn thực nghiệm.



## Tiến độ ngày 18/10/2026



### Đã triển khai

- `src/reddit_sna/evaluation/splits.py`: temporal split và tổng hợp thống kê split.

- `src/reddit_sna/evaluation/sample_checks.py`: kiểm tra khóa, nhãn, thời gian, catalog và feature leakage.

- `src/reddit_sna/evaluation/metrics.py`: metrics tổng hợp, metrics từng lớp và confusion matrices.

- Tích hợp evaluation stage vào `src/reddit_sna/pipelines/prediction.py`.

- Bổ sung unit tests cho sample checks và metrics.

- Tạo negative control `tests/fixtures/prediction/samples_leaky.csv` và test xác nhận feature `t+1` bị phát hiện.



### Bằng chứng kiểm thử

- Toàn bộ unit tests ở lần chạy gần nhất: 147 passed, 48 skipped, 65 subtests passed.

- `tests/unit/test_sample_checks.py` sau khi bổ sung negative control: 14 passed.

- Pipeline run ID: `lan-eval-guide-20261018`.

- Pipeline hoàn thành các stage table, split, baselines và evaluation.

- Evaluation xử lý 4.572 dòng prediction và xuất 9 dòng metrics theo model/split.



### Môi trường

- Python 3.12.13.

- Hệ điều hành: Windows.

- Virtual environment: `.venv`.

- Các thư viện: pandas 3.0.6, NumPy 2.5.4, scikit-learn 1.9.1.



### Giới hạn và công việc tiếp theo

- Dữ liệu hiện tại là synthetic; kết quả không chứng minh hiệu quả dự báo trên dữ liệu Reddit thực.

- Các mô hình B2 Random Forest, B5 Gradient Boosting, HeTCo và feature Reddit thực chưa hoàn thành trong pipeline hiện tại.

- Đã chạy lại toàn bộ unit tests sau khi cập nhật báo cáo: 147 passed, 48 skipped, 65 subtests passed.

- Cần review chéo, hoàn thiện demo và slide trước code freeze ngày 20/10/2026.
