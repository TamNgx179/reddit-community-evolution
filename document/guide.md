# Chạy demo Phúc–Đăng và bàn giao kết quả

**Bản tích hợp ngày 20/10/2026**, trên nhánh `feat/phuc-006-handoff-demo`. Code tracker/evaluator của Đăng từ PR #12 đã được ghép; thuật toán và ngưỡng giữ nguyên. Phúc bổ sung preflight, config/provenance, diagnostics, notebook, bảng gộp và hướng dẫn này.

**Dùng ZIP input T02 đã gửi trước. Không tải lại hoặc thay ZIP đó.** Các artifact có tên `phuc-dang-*` là output tái lập/tích hợp do Phúc chạy; không giả thành hai run gốc `dang-week1-*` và không xác nhận freeze lịch sử của Đăng. Có thể bàn giao demo kỹ thuật bằng các run này mà không chờ hai thư mục gốc.

## 1. Mở kết quả đã chạy

Tại máy Phúc, các đường dẫn tính từ root repo:

- Kết quả hai split: `artifacts/detection-tracking/phuc-dang-final-20261020-001/{development,evaluation}/`.
- Notebook chính: `notebooks/detection_tracking/01_synthetic_demo.ipynb`.
- Notebook đã chạy, log và kiểm tra: `artifacts/verification/phuc-dang-final-20261020-001/`.
- Hình/CSV detection: `artifacts/detection-tracking/phuc-dang-demo-20261020-002/`.
- Phân tích graph khó/null: thư mục cùng tên thêm `-cases`.
- Hình/CSV tracking: thư mục cùng tên thêm `-tracking`.
- Bản trình bày để giao nhóm: `artifacts/handoff/phuc-dang-demo-results-20261020-001/`; xem `README.md` và `REPORT.html`. ZIP cùng tên chỉ đóng gói **kết quả demo**, không thay ZIP input T02.

`artifacts/` không có trên GitHub khi pull code. Nhóm đã có input T02 có thể tự chạy các lệnh dưới, hoặc nhận gói output kết quả. Git chứa source/notebook không cache, guide và bảng số liệu nhỏ; gói output chứa bản notebook đã chạy/hình/toàn bộ CSV.

## 2. Môi trường

Chạy PowerShell ở root repo. Dùng môi trường dự án sẵn có; nếu chưa có thì tạo `.venv` với Python 3.12:

```powershell
py -3.12 -m venv .venv
```

Cài package và dependencies:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,evaluation,notebook]' -c .\document\specs\phuc\006-handoff-demo\replay-constraints-py312.txt
```

Constraints trên đã kiểm tra ở Windows CPython 3.12.6. Không cần cài lại nếu môi trường hiện tại đã chạy được. Benchmark source gốc vẫn giữ khóa riêng; những lệnh bên dưới đọc graph/membership/AMI đã có, không sinh thí nghiệm detection mới.

## 3. Unit test và contract test

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_jaccard_tracking tests.unit.test_tracking_delivery tests.unit.test_synthetic_handoff tests.unit.test_synthetic_demo tests.unit.test_synthetic_cases tests.unit.test_contracts tests.unit.test_synthetic_io -v
```

Các test mới kiểm tra đọc layout, mẫu có cùng community ID ở dataset khác nhau, nguồn thiếu dự đoán, hash hỏng, reference sai dù đã hash lại, input pin sai, truth confusion 6×6 và chống ghi đè. Test PR #12 kiểm tra thuật toán Jaccard/mapping/sáu sự kiện.

## 4. Chạy hai đường tracking trên cả hai split

Input mặc định ở đây là root ZIP T02 đã giải nén, có `delivery-manifest.json` và `runs/`. Nếu bạn giải nén ở chỗ khác, đổi `--handoff` tới chỗ đó.

```powershell
& .\.venv\Scripts\python.exe .\scripts\run_tracking_handoff.py --handoff .\artifacts\handoff\phuc-dang-week1-20261019-001 --run-id phuc-dang-final-20261020-001
```

Lệnh chạy `development` rồi `evaluation` bằng cùng PR #12 algorithm: Jaccard ≥ 0,30; ±10%; split trước merge; seed detector chính 0. Nó kiểm tra SHA-256 của toàn source split với pins đã version trong code trước khi đọc dữ liệu; output mới có config/provenance và manifest. Config mới ghi lại lần tái lập hiện tại, **không phải chứng cứ khóa trước evaluation hồi tố**.

Lệnh từ chối output đã tồn tại. Trên máy đã có kết quả `001`, chọn run ID mới như `phuc-dang-final-20261020-002`. Không xóa/ghi đè run cũ. Thư mục mới có:

```text
<run-id>/
  tracking-index.json
  development/
    metadata.json
    manifest.json
    tracker-config.json
    provenance.json
    datasets/<dataset_id>/
      truth_tracking/
        events.csv
        links.csv
        event_predictions.csv
        metrics.csv
        confusion_matrix.csv         # 6 hàng × 6 cột số
        diagnostics.json             # evaluator
        tracker_diagnostics.json     # links, ambiguous sources, ...
      detector_tracking/
        events.csv
        links.csv
        source_mapping.csv
        event_predictions.csv
        metrics.csv
        confusion_matrix.csv         # 6 hàng × 7 cột số, unmatched ở cuối
        diagnostics.json
        mapping_diagnostics.json
        tracker_diagnostics.json
  evaluation/                        # cùng cấu trúc, dataset IDs eval-*
```

Mỗi split có 18 dataset, hai tháng và 39 nguồn truth cần chấm. Header tên dòng của confusion không tính là cột số. Các output có identity/reference theo metadata; không ghép `A`, `K`, `c0` giữa các dataset chỉ vì trùng tên.

## 5. Chạy notebook chính bằng kernel mới

Với hai run `001` ở bước 4:

```powershell
& .\.venv\Scripts\python.exe .\scripts\replay_synthetic_notebook.py --project . --bundle .\artifacts\handoff\phuc-dang-week1-20261019-001 --output .\artifacts\detection-tracking\phuc-dang-demo-20261020-002 --report .\artifacts\verification\phuc-dang-final-20261020-001\notebook-final
```

Nếu chọn run ID khác, thêm hai tham số:

```text
--tracking-development <run-id>/development --tracking-evaluation <run-id>/evaluation
```

Các đường dẫn trên là đường dẫn đầy đủ từ cwd root repo, ví dụ `artifacts/detection-tracking/phuc-dang-final-20261020-002/development`. Chọn output/report mới mỗi lần. Notebook nguồn trong Git vẫn không cache; script lưu bản đã chạy, thời gian, cell execution counts, số PNG và hash output trong report.

Để xem/chạy trực tiếp trong VS Code/Jupyter: mở notebook chính, chọn kernel `.venv/Scripts/python.exe`, Restart Kernel → Run All. Mặc định notebook tìm gói T02 và hai run `001` ở vị trí trên. Nếu để chỗ khác, đặt `REDDIT_SYNTHETIC_BUNDLE`, `REDDIT_TRACKING_DEVELOPMENT`, `REDDIT_TRACKING_EVALUATION` trước khi mở kernel. `REDDIT_SNA_PROJECT` đặt root repo khi cwd nằm ngoài repo.

Notebook có **14 code cell**, gồm sáu hình detection/case và hai hình confusion tracking. Nó đọc kết quả đã lưu và kiểm tra hashes; không chạy lại detector hoặc dùng evaluation để chọn ngưỡng mới.

## 6. Cách đọc kết quả

| Chỉ số | Development | Evaluation |
|---|---:|---:|
| Truth events/links khớp | 18/18 | 18/18 |
| Truth pooled macro-F1, 39 nguồn | 1,0 | 1,0 |
| Detector mean dataset macro-F1 | 0,2561728395 | 0,2175925926 |
| Detector pooled macro-F1, 39 nguồn | 0,85 | 0,6551425990 |
| Số event detector đúng | 33/39 | 28/39 |
| Matched coverage | 1,0 | 1,0 |
| Unmatched truth | 0 | 0 |
| Detector source community dư | 3 | 6 |

Mean dataset và pooled F1 dùng hai cách tổng hợp. Dataset nhỏ không có đủ sáu lớp, nhưng mỗi điểm vẫn tính sáu lớp và lớp vắng nhận 0. Vì vậy, giữ số Đăng đã báo dưới tên mean dataset, đồng thời trình bày pooled trên đủ 39 nguồn. Support sáu nhãn là 21/3/3/6/3/3; giữ K, unmatched và nhóm detector dư.

AMI đo phân hoạch ở từng tháng, F1 đo sự kiện chuyển tiếp. AMI null ở dissolve không bị điền thành 1. Coverage 1 chỉ có nghĩa nguồn truth match được, không có nghĩa sự kiện đúng. Lỗi giữ nguyên để phân tích, không sửa truth/chọn seed đẹp hơn.

## 7. Phạm vi chốt trong hôm nay

Phần bàn giao kỹ thuật gồm source Đăng có tác giả, runner/config/provenance, notebook tích hợp đã chạy, output hai đường/cả hai split, CSV/hình và báo cáo. Kết quả dùng dữ liệu tổng hợp; chưa chứng minh forecasting/Reddit và chưa thay xác nhận nghiệm thu trực tiếp của thành viên nhóm. Hai artifact/freeze gốc của Đăng có thể bổ sung đối chiếu sau, không cản trở sử dụng các run tái lập minh bạch này để trình bày demo.
