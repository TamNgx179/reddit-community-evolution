# Week 4 frozen-core handoff

## Phạm vi và người nhận

Gói này giúp Thanh–Trâm ghép dự báo và tái tính metric, Phúc–Đăng đối chiếu coverage, Anh tổng hợp bằng chứng. Không cần tải lại Reddit hoặc chạy lại Leiden. Hai cohort có reference và cửa sổ riêng, không gộp thành một tập kiểm thử.

| Gói | Dữ liệu và phạm vi |
| --- | --- |
| Full-study | 7.490 mẫu resolved trong bảng nhãn. Predictions chỉ có 1.269 mẫu final, tháng nhãn 01–09/2018, cho từng model và seed. Không phải dự báo toàn bộ 7.490 mẫu. |
| 2016 | 2.721 mẫu resolved. Predictions có 494 mẫu main và 1.107 mẫu rolling. Hai cửa sổ có giao nhau, không cộng số mẫu. |
| H1 của Thanh | Đã dựng lại pilot 2015 và qua verifier với 90 lượt fit. Kết quả H1 có ZIP riêng. |

Khóa ghép gồm `reference_id`, `feature_month`, `community_id`, `label_month`, `label_reference_id`. Predictions còn có `model`, `seed`, `window`. File full-study cũ không có `window`, runner chỉ bổ sung `final` theo contract đã khóa. Giữ nguyên cả năm cột khóa khi ghép. Không ghép bằng community ID đơn lẻ.

Coverage lấy từ features và labels, không lấy từ số dòng predictions. Terminal snapshot được tính censored ngay cả khi bảng labels 2016 cũ không ghi các dòng terminal. Unresolved, censored và resolved được báo riêng.

## Tải và kiểm tra

Đăng nhập GitHub bằng tài khoản có quyền ghi vào repo để mở [Release bàn giao Week 4](https://github.com/TamNgx179/reddit-community-evolution/releases/tag/untagged-78c2cda4ed4d982e186d).

| Gói | Tệp tải |
| --- | --- |
| Full-study và 2016 | [ZIP](https://github.com/TamNgx179/reddit-community-evolution/releases/download/untagged-78c2cda4ed4d982e186d/Week4_Frozen_Core_Acceptance_20261109.zip) · [SHA-256](https://github.com/TamNgx179/reddit-community-evolution/releases/download/untagged-78c2cda4ed4d982e186d/Week4_Frozen_Core_Acceptance_20261109.zip.sha256) |
| H1 pilot 2015 | [ZIP](https://github.com/TamNgx179/reddit-community-evolution/releases/download/untagged-78c2cda4ed4d982e186d/Week4_H1_Acceptance_20261109.zip) · [SHA-256](https://github.com/TamNgx179/reddit-community-evolution/releases/download/untagged-78c2cda4ed4d982e186d/Week4_H1_Acceptance_20261109.zip.sha256) |

Phúc–Đăng và Anh có thể lấy gói frozen để đối chiếu coverage và metric. Thanh–Trâm dùng thêm gói H1 để xem dự báo, fit log, bảng ablation và biên bản nghiệm thu. Hướng dẫn này cập nhật trạng thái H1 sau khi ZIP frozen được đóng.

```powershell
Get-FileHash .\Week4_Frozen_Core_Acceptance_20261109.zip -Algorithm SHA256
```

Giải nén vào một thư mục mới. Cấu trúc tương ứng checkout, có source tối thiểu, config, bảng frozen và kết quả replay. Đây là selected export, không chứa toàn bộ payload của các manifest lịch sử. Không dùng nó để tuyên bố đã xác minh toàn bộ runtime huấn luyện.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[research]"
.venv/Scripts/python.exe scripts/package_week4_handoff.py --verify PATH_TO_ZIP
.venv/Scripts/python.exe scripts/verify_week4_inputs.py --output artifacts/acceptance/local-inputs-001
.venv/Scripts/python.exe scripts/run_week4_acceptance.py --accepted-input artifacts/acceptance/local-inputs-001 --output artifacts/acceptance/local-replay-001
```

Luôn chọn output mới. Runner từ chối ghi đè, kiểm tra checksum, thứ tự schema, reference, truth và lịch model/seed/window trước khi tính metric. Nó không fit mô hình. Các cột số được kiểm tra hữu hạn và cutoff đặc trưng phải bằng tháng quan sát. Cutoff huấn luyện chỉ được đối chiếu ở mức protocol vì gói này không có fit logs.

## Đầu ra và việc tiếp theo

`acceptance.json` ghi số mẫu, coverage, schema và SHA-256 đầu vào. `replayed-metrics.csv` có metric từng cohort/window/model/seed. `manifest.json` khóa các file kết quả và source runner. `run.log` ghi thời gian, phạm vi và trạng thái H1. `bundle-manifest.json` kiểm kê toàn bộ file trong ZIP.

Gói H1 lưu 27.954 dòng dự báo, cấu hình, provenance và kết quả verifier của lần tái lập tại máy Tâm. Bảng chọn ngưỡng, bảng so sánh và file đánh giá khớp SHA-256 với báo cáo của Thanh. SHA-256 của file dự báo chi tiết khác bản Thanh. Giữ v4 làm phương pháp chính và báo cáo v5 dưới dạng ablation.

Muốn fit lại H1 từ dữ liệu nguồn, chạy chuỗi prepare → forecast GED với history → research → HeTCo v4 → H1 → verifier theo hướng dẫn trong RUNBOOK và báo cáo H1 đi kèm. Dùng run ID mới cho từng lần chạy.

Các cặp dùng các bảng đã khóa để phân tích lỗi theo lớp/tháng và coverage. Mọi thay đổi mô hình cần experiment ID, protocol và ablation riêng. Kết quả replay hiện có chỉ tái lập predictions đã lưu, không phải một lần kiểm thử độc lập mới.
