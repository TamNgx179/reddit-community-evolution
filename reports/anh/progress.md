# Progress — Lan Anh

## Phạm vi công việc

Phụ trách đánh giá cho prototype dự báo tiến hóa cộng đồng:

- Temporal split theo `label_month`.
- Kiểm tra tính hợp lệ của mẫu và nguy cơ data leakage.
- Tính metrics tổng hợp, per-class metrics và confusion matrices.
- Tích hợp evaluation vào prediction pipeline.
- Viết hướng dẫn đọc kết quả và giới hạn thực nghiệm.

## Tiến độ ngày 19/10/2026

### Đã triển khai

- `src/reddit_sna/evaluation/splits.py`: chia tập theo thời gian và tổng hợp thống kê split.
- `src/reddit_sna/evaluation/sample_checks.py`: kiểm tra khóa, nhãn, thời gian, catalog và feature leakage.
- `src/reddit_sna/evaluation/metrics.py`: metrics tổng hợp, metrics từng lớp và confusion matrices.
- Tích hợp evaluation stage vào `src/reddit_sna/pipelines/prediction.py`.
- Bổ sung unit tests cho sample checks, temporal split và metrics.
- Tạo negative control `tests/fixtures/prediction/samples_leaky.csv` để kiểm tra khả năng phát hiện feature leakage liên quan đến thời điểm `t+1`.
- Cập nhật trạng thái CLI để phân biệt baseline/evaluation đã triển khai với các phần prediction mở rộng còn trong kế hoạch.

### Bằng chứng kiểm thử

- Toàn bộ test suite: 253 tests, kết quả `OK`, không có test failure hoặc error.
- `tests/unit/test_sample_checks.py`: 14 tests passed, bao gồm kiểm tra mẫu hợp lệ và phát hiện leakage.
- Pipeline run ID: `lan-week1-final-20261019`.
- Pipeline đã tạo bảng mẫu, chạy baseline và hoàn thành evaluation stage.
- Tổng số dòng prediction: 4.572.
- Tổng số dòng metrics theo model/split: 9.
- Các đầu ra đã xác nhận gồm `samples.csv`, `predictions.csv`, `split.csv`, `split_summary.csv`, `metrics.csv`, `per_class.csv`, các confusion matrices và `evaluation_notes.md`.

Lệnh chạy pipeline:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config .\configs\prediction.toml --run-id lan-week1-final-20261019
```

Lệnh chạy toàn bộ test suite:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Môi trường

- Python 3.12.13.
- Hệ điều hành: Windows.
- Virtual environment: `.venv`.
- Các thư viện đã ghi nhận: pandas 3.0.6, NumPy 2.5.4, scikit-learn 1.9.1.

### Giới hạn và công việc tiếp theo

- Dữ liệu hiện tại là synthetic. Kết quả kiểm thử và metrics hiện có xác nhận hoạt động của pipeline trên dữ liệu tổng hợp, không chứng minh hiệu quả dự báo trên dữ liệu Reddit thực.
- Các mô hình B2 Random Forest, B5 Gradient Boosting, HeTCo và các feature Reddit thực vẫn chưa hoàn thành trong pipeline hiện tại.
- Notebook `notebooks/prediction/00_research_plan.ipynb` vẫn ở trạng thái template chưa thực thi. Chưa có thí nghiệm nghiên cứu hoàn chỉnh được xác nhận từ notebook này.
- Cần review chéo, hoàn thiện demo và slide trước code freeze ngày 20/10/2026.
- Contribution log tiếp tục ở trạng thái `pending_review` cho đến khi có xác nhận review thực tế.
