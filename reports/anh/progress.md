# Progress — Lan Anh

## 1. Phạm vi công việc

Phụ trách phần đánh giá của prototype dự báo tiến hóa cộng đồng trong Week 1 theo `ARCHITECTURE.md` và `reports/prediction-week1/01_PLAN_TUAN1_TRAM_ANH.md`:

- Chia mẫu theo các khoảng `label_month` hoàn chỉnh, không chia ngẫu nhiên theo từng dòng.
- Kiểm tra schema, khóa mẫu, nhãn, quan hệ tháng, feature catalog và thời điểm khả dụng của feature.
- Tạo aggregate metrics, per-class metrics và confusion matrices.
- Tích hợp evaluation stage vào prediction pipeline theo phân công, giữ nguyên các giao diện và ranh giới phụ thuộc hiện có.
- Viết hướng dẫn chạy demo, đọc artifact và trình bày giới hạn.
- Cập nhật `notebooks/prediction/00_research_plan.ipynb` để cố định run tham chiếu lan-demo-final-20261020; notebook vẫn là tài liệu nghiên cứu, không thay thế entry point của pipeline.

## 2. Phần việc và hợp đồng cần duy trì

Các module đánh giá thuộc `src/reddit_sna/evaluation/`:

- `splits.py`: temporal split theo `label_month` và thống kê split.
- `sample_checks.py`: kiểm tra schema, khóa, nhãn, quan hệ tháng, catalog và feature availability.
- `metrics.py`: aggregate metrics, per-class metrics và confusion matrices.

Evaluation stage được tích hợp trong `src/reddit_sna/pipelines/prediction.py` theo phạm vi phối hợp với Trâm. Trâm sở hữu skeleton và các stage tạo bảng/baselines; phần evaluation cần giữ đúng giao diện dùng chung.

Các module đánh giá phải sử dụng `Event` và `next_month()` từ `contracts.py`, không tự định nghĩa lại các hợp đồng này. `community_id` là định danh cục bộ trong tháng, không phải feature và không chứng minh danh tính cộng đồng xuyên tháng. Feature dùng để dự báo không được lấy thông tin chỉ khả dụng sau thời điểm dự báo.

Fixture `tests/fixtures/prediction/samples_leaky.csv` là negative control có chủ đích để kiểm tra khả năng phát hiện leakage; không phải dữ liệu hợp lệ để train/evaluate.

## 3. Run tham chiếu đã kiểm tra

Dùng run `lan-demo-final-20261020` làm run tham chiếu trong các tài liệu Week 1 này. Theo `manifest.json` được kiểm tra:

- `status`: `complete_through_baselines`
- `data_kind`: `synthetic`
- `seed`: `42`
- `git revision`: `696cbb61da2faebb75f06a701afee943fe0199c0`
- `git dirty`: `false`
- Các stage `table`, `split`, `baselines`, `evaluation`: `complete`
- Có các artifact `split_summary.csv`, `metrics.csv`, `per_class.csv`, `predictions.csv`, `evaluation_notes.md`.

Các kết quả dưới đây thuộc run này; không trộn với những run khác, kể cả các run có seed hoặc revision khác.

### Phân chia mẫu

| Split | Số mẫu | Số `label_month` |
|---|---:|---:|
| Train | 1.000 | 23 |
| Validation | 263 | 6 |
| Test | 261 | 6 |
| Mẫu không nhãn bị loại | 46 | 0 |
| **Tổng mẫu có nhãn** | **1.524** | **35** |

### Metrics trên test

| Model | Macro-F1 | Macro-F1 (6 lớp) | Balanced accuracy |
|---|---:|---:|---:|
| B1 Majority | 0.1125 | 0.1125 | 0.1667 |
| B1 Persistence | 0.2557 | 0.2557 | 0.2586 |
| B4 Logistic Regression | 0.2160 | 0.2160 | 0.2155 |

B1 Persistence có macro-F1 cao nhất trong ba baseline ở run synthetic này. Đây không phải bằng chứng rằng mô hình này luôn tốt hơn các mô hình khác hoặc dự báo tốt trên Reddit thật.

## 4. Trạng thái kiểm thử

Lệnh sau đã chạy và kết quả được cung cấp là:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```text
Ran 253 tests in 94.716s

OK
```

Tức là 253 test được phát hiện trong lần chạy đó đều pass. Kết quả này là bằng chứng kiểm thử phần mềm cho môi trường/revision được chạy; không tự chứng minh tính mới khoa học hay hiệu quả dự báo trên dữ liệu Reddit thực tế.

## 5. Chạy lại pipeline

Từ repository root, dùng run ID mới chưa tồn tại:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction `
  --config .\configs\prediction.toml `
  --run-id <unique-run-id>
```

Artifact được lưu dưới `artifacts/prediction/<run_id>/`. Không tái sử dụng run ID đã có và không ghi đè artifact cũ. Khi báo cáo kết quả, lấy manifest và các CSV từ cùng một thư mục run.

## 6. Giới hạn và việc tiếp theo

Week 1 hiện xác nhận prototype trên dữ liệu synthetic với luồng table → temporal split → B1/B4 baselines → evaluation. Kết quả không xác nhận pipeline Reddit end-to-end, không tự xác nhận giả thuyết H3 và không chứng minh tính mới khoa học.

B2 Random Forest, B5 Gradient Boosting, HeTCo và feature từ Reddit thật nằm ngoài phạm vi của run ba baseline này.  Contribution chỉ nên ghi là `reviewed` khi review thực tế đã diễn ra.