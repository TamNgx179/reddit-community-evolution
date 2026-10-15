# Reddit Community Evolution

SNA course project: phát hiện, theo dõi và dự báo thay đổi của **community user** trên Reddit. Subreddit là ngữ cảnh hoạt động, không phải nhãn community chuẩn.

Source hiện là **bộ khung**: package Python, CLI, kiểm tra cấu hình, quy ước dữ liệu và quản lý thư mục output. Các thuật toán nghiên cứu và ba demo tuần 1 chưa triển khai. `check` thành công chỉ xác nhận cấu hình hợp lệ; `run` hiện trả mã 3 và không tạo kết quả đánh giá.

## Cài đặt

Yêu cầu Python **3.11 trở lên**. Ví dụ PowerShell tại thư mục repo:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\python.exe -m reddit_sna --help
& .\.venv\Scripts\python.exe -m reddit_sna pipelines
```

Linux/macOS dùng `.venv/bin/python` thay cho `.venv\Scripts\python.exe`. Dependencies được khai báo ở `pyproject.toml`; bộ khung chỉ dùng thư viện chuẩn. Khi thêm thuật toán, thêm đúng thư viện mà module cần và ghi phiên bản môi trường thực nghiệm. Không cài sẵn toàn bộ thư viện ML/graph cho các module chưa có code.

## Ba nhóm làm việc độc lập

| Pipeline | Nhóm | Đầu vào và phạm vi dự kiến | Cấu hình |
|---|---|---|---|
| `core` | Tâm–Thanh | Reddit pilot → snapshot/community → nhãn/features → mô hình → đánh giá | `configs/core.toml` |
| `detection-tracking` | Phúc–Đăng | Mạng động tổng hợp → detection/tracking → đánh giá | `configs/detection_tracking.toml` |
| `prediction` | Trâm–Anh | Bảng community–tháng tổng hợp → chia thời gian → baseline → đánh giá | `configs/prediction.toml` |

Mỗi nhóm tự chuẩn bị input và output, không chờ artifact của nhóm khác trong tuần 1. Các pipeline ghép hàm từ module chức năng; không import pipeline khác. Chi tiết ở [phân công 8 tuần](PHAN-CONG-SNA-8-TUAN.md).

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna check --config configs/core.toml
& .\.venv\Scripts\python.exe -m reddit_sna check --config configs/detection_tracking.toml
& .\.venv\Scripts\python.exe -m reddit_sna check --config configs/prediction.toml
```

Config `core` cần thư mục `data/raw` có sẵn; lệnh kiểm tra không đọc nội dung corpus và chưa kiểm chứng chất lượng dataset. Hai config tổng hợp không phụ thuộc Reddit. **Mọi đường dẫn bên trong TOML tính từ thư mục chứa TOML**, bao gồm `project_root`. Có thể gọi CLI từ thư mục khác bằng đường dẫn tuyệt đối đến config.

Lệnh dành cho pipeline sau khi có thuật toán:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna run --config configs/prediction.toml --run-id prediction-002
```

Hiện lệnh trên báo `Not implemented` và trả mã 3. Mã thoát: `0` cho help/list/check hợp lệ; `2` cho lỗi tham số/cấu hình/path; `3` khi pipeline nghiên cứu chưa triển khai. Không coi mã 3 là một lần chạy thành công.

CLI xuất UTF-8 cho cả stdout/stderr, bao gồm tên tiếng Việt và đường dẫn Unicode trên Windows. Các chương trình gọi CLI qua subprocess nên đọc output với encoding UTF-8.

## Tìm code ở đâu

```text
configs/                    Cấu hình riêng cho từng pipeline
notebooks/
  core/                     Tâm–Thanh: khám phá Reddit và thử core
  detection_tracking/       Phúc–Đăng: benchmark, detection/tracking
  prediction/               Trâm–Anh: baseline, đánh giá và biểu đồ
src/reddit_sna/
  cli.py                    Giao diện dòng lệnh
  config.py                 Đọc/kiểm tra TOML và đường dẫn
  contracts.py              Schema records, ID, tháng, sáu sự kiện
  artifacts.py              Tạo thư mục run mới và manifest provenance
  data/                     Đọc/chuẩn hóa dữ liệu, identity mapping, audit
  graphs/                   Graph dị thể, snapshot R/T, projection, coverage
  detection/                Leiden, Louvain, temporal/consensus
  tracking/                 Jaccard, GED
  features/                 Cấu trúc, dị thể, lịch sử thành viên
  models/                   B1/B2/B4/B5 và HeTCo
  evaluation/               Split thời gian, metrics, leakage, bootstrap
  benchmarks/               Sinh dữ liệu tổng hợp có kiểm soát
  pipelines/                Ba entrypoint của ba nhóm
tests/
  unit/                     Kiểm tra config, contracts, output
  integration/              Kiểm tra CLI qua subprocess
  fixtures/                 Chỉ chứa dữ liệu tổng hợp nhỏ
data/                       Dataset hiện có, không commit
artifacts/                  Output runtime, không commit
reports/                    Bảng/hình/báo cáo được chọn để bàn giao
experiments/                Protocol, registry E1–E5/A1–A7, feature/literature catalogs
```

Các thư mục thuật toán hiện chỉ có mô tả ranh giới; thêm file thật khi triển khai, ví dụ `detection/leiden.py`, `tracking/jaccard.py`, `models/majority.py`. Không tạo cây riêng theo người hoặc sao chép detector/metrics sang từng nhóm. Xem [ARCHITECTURE.md](ARCHITECTURE.md) để biết hướng phụ thuộc và phân công module.

## Làm việc với notebook

Dùng `.ipynb` trong `notebooks/<nhóm>/` để khám phá dữ liệu, thử thuật toán, phân tích lỗi và trình bày hình/bảng. Tuần 1 có thể phát triển prototype ngay trong notebook; không bắt buộc chuyển mọi cell sang `.py` ngay từ đầu. Khi một hàm đã ổn định, cần dùng lại hoặc cần test, chuyển hàm đó vào module tương ứng trong `src/reddit_sna` rồi import lại trong notebook. Pipeline CLI được hoàn thiện dần từ các bước đã kiểm chứng.

- Mỗi nhóm có `00_research_plan.ipynb` làm khung câu hỏi/protocol/đối chứng/kết quả/phản biện. Đây là template chưa thực thi; cell triển khai báo NotImplementedError cho đến khi có code thật. Không dùng template này như bằng chứng hoàn thành demo.
- Chọn kernel Python dùng cùng môi trường đã cài package bằng `pip install -e .`. Notebook import `reddit_sna` trực tiếp; không sửa `sys.path` hoặc copy source sang thư mục notebook. Công cụ notebook/kernel được thiết lập riêng theo editor nhóm dùng; lần dựng này chưa thêm dependency hay chạy notebook.
- Đặt tên theo bước và nội dung, ví dụ `01_data_audit.ipynb`, `02_tracking_pilot.ipynb`; người phụ trách ghi trong cell Markdown đầu. Mỗi nhóm giữ notebook riêng và tránh hai người sửa cùng một file cùng lúc.
- Đầu notebook ghi mục tiêu, loại/phạm vi dữ liệu, config, seed và output. Xác định đường dẫn config/repo một lần ở đầu; không mặc định cwd luôn là repo root. Sau khi truyền đúng file config vào `load_config`, các path bên trong TOML vẫn resolve theo thư mục config.
- Trước bàn giao, restart kernel và chạy lại các cell theo thứ tự từ đầu đến cuối. Không dựa vào biến hoặc kết quả còn sót từ lần chạy trước. Demo end-to-end bằng notebook hợp lệ khi có input, các bước xử lý và evaluation results thật, chạy lại được.
- Output lớn, bảng trung gian, model và log lưu trong `artifacts/<pipeline>/<run_id>/`; báo cáo chọn lọc ở `reports/`. Xóa cell output chứa dữ liệu cá nhân/dữ liệu thô hoặc output quá lớn trước khi commit. `.ipynb_checkpoints` đã được ignore; notebook `.ipynb` vẫn được quản lý bằng Git.

## Mục tiêu nghiên cứu và tiêu chí bàn giao

Theo rubric được cung cấp, đồ án A2 chiếm 50% và mức điểm tối đa yêu cầu tiềm năng paper; A1 thi lý thuyết chiếm 50% còn lại. Source này phục vụ một nghiên cứu có phân tích SNA. Câu hỏi và đóng góp cần kiểm chứng qua related work và dữ liệu thật; không thể suy ra điểm số từ cấu trúc repo.

Xem phần tự phản biện trong [ARCHITECTURE.md](ARCHITECTURE.md) và các hồ sơ thiết kế ở `experiments/`. Hồ sơ đó đang là draft/planned, **chưa được CLI thực thi/enforce**, và chưa có kết quả thực nghiệm. Chúng tách chất lượng graph/detection, tính đúng của tracker và hiệu quả dự báo; yêu cầu đối chứng cùng mẫu/nhãn và feature biết tại t. Đặc biệt không tính retention t→t+1 để dự đoán chính sự kiện đó.

## Dữ liệu và output

- Giữ nguyên `data/raw`, `data/processed`, `data/private`. Không đưa dữ liệu gốc, khóa, danh tính user hoặc nội dung thảo luận vào Git.
- Output chạy thật sau này ở `artifacts/<pipeline>/<run_id>/`. Mỗi lần chạy dùng ID mới; không ghi đè run cũ hoặc ghi vào input/cây `data`.
- `artifacts.create_run_directory` dành cho pipeline đã triển khai. Hàm tạo `manifest.json` trạng thái `started`, ghi phiên bản Python/package, seed và cấu hình đã resolve. Đây chưa phải evaluation hoàn tất; pipeline phải ghi metrics/log và trạng thái hoàn thành sau khi thực sự chạy xong.
- Không đổi `project_root` để lách ranh giới output. Chỉ dùng config đáng tin cậy; kiểm tra path giúp ngăn ghi nhầm, không phải sandbox chống mã tùy ý.
- Phân biệt Reddit thật với fixture; không so trực tiếp điểm từ ba đầu vào khác nhau.

## Kiểm tra và đóng gói

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir dist
```

Test dùng thư mục tạm và dữ liệu tổng hợp; không cần xử lý 15 corpus. Kiểm tra wheel bằng virtualenv khác giúp phát hiện package thiếu file hoặc import vô tình phụ thuộc repo.

## Cách cộng tác

Tạo nhánh công việc và pull request; không đẩy trực tiếp vào `main`. Mỗi người sở hữu module như bảng trong ARCHITECTURE, cùng người trong cặp review trước khi ghép demo. Khi đổi field/ý nghĩa nhãn, cập nhật `contracts.py`, `SCHEMA_VERSION`, config và các nơi sử dụng. Giữ notebook làm nơi thử nghiệm/trình bày và package làm nơi chứa logic ổn định dùng lại; không sửa `sys.path` hoặc hardcode đường dẫn máy cá nhân.
