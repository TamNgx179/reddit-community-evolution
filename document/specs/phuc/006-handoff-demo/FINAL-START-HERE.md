# Bắt đầu ở đây — gói bàn giao cuối phần Phúc

**Phần cá nhân Phúc: 36/36 task hoàn thành; demo cặp còn chờ Đăng.**

**Ngày:** 19/10/2026. **Owner:** Phúc. **Phạm vi:** dữ liệu tổng hợp, truth, Independent Leiden, AMI/coverage, notebook và bằng chứng. Đăng phụ trách tracker/mapping/đánh giá sự kiện. Trạng thái ghép chung vẫn chờ receipt và artifact thật của Đăng.

File cần gửi là **`phuc-week1-final-20261019-001.zip`**. Đối chiếu SHA-256 ZIP với [reference T06 trên Git](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/specs/phuc/evidence/PHUC-006-T06-final-reference.json) hoặc checksum Phúc gửi riêng, rồi giải nén vào **thư mục mới**. Mở terminal tại root có file này, `pyproject.toml`, `src/` và `artifacts/`. Không cần Git để đọc dữ liệu hoặc dùng wheel trong gói.

## 1. Trong gói có gì?

| Mục | Nội dung |
|---|---|
| `PHUC-FINAL-MANIFEST.json` | Inventory/hash/size, nguồn code/dữ liệu/bằng chứng, trạng thái tự kiểm tra và phần còn chờ Đăng |
| `src/`, `scripts/`, `configs/`, `tests/` | Source/config/tests của package tại `b7b3920`; không kèm raw Reddit hoặc venv |
| `artifacts/handoff/phuc-dang-week1-20261019-001/` | Gói T02 nguyên byte: 36 dataset/72 snapshot/216 membership CSV, graph/nodes/truth/metrics và independent consumer |
| `notebooks/detection_tracking/01_synthetic_demo.ipynb` | Notebook nguồn 21 cells/10 code cells, không cache output |
| `artifacts/detection-tracking/phuc-006-t05-notebook-002/` và sibling `-cases` | CSV đầy đủ, sáu hình PNG/SVG, source hashes/metadata và case analysis đã lưu |
| `artifacts/verification/phuc-006-t05-001/replay-002/` | Notebook đã chạy có bảng/hình và JSON kết quả; mở để xem ngay |
| `artifacts/verification/phuc-006-t05-001.zip` | Full proof T05: clean install, pip check/freeze, 385-test logs, hai executed notebooks và audits |
| `wheels/reddit_community_evolution-0.1.0-py3-none-any.whl` | Regular wheel đã dùng trong T05; 44 Python files khớp source |
| `document/PHUC-DANG-WEEK1-HANDOFF.md` | Chi tiết schema/path/reference, thứ tự Đăng làm, case khó/null và phần chốt T06 |

Đây là gói runtime/dữ liệu/kết quả cho phần Phúc, không phải toàn bộ repository/dataset Reddit. Task board và toàn bộ specs tiếp tục theo dõi trên [nhánh bàn giao](https://github.com/TamNgx179/reddit-community-evolution/tree/feat/phuc-006-handoff-demo). Source package/config/script/notebook không thay sau gate T05; tài liệu đóng gói được cập nhật ở T06. ZIP T02/guide cũ bên trong thư mục dữ liệu giữ nguyên; guide hiện tại ở `document/` có phần bổ sung mới.

## 2. Đăng bắt đầu tracker ngay

Cần Python 3.11+ chỉ standard library. Tại root gói đã giải nén, chạy kiểm tra **development**:

```powershell
python -I -S src/reddit_sna/reporting/synthetic_handoff.py artifacts/handoff/phuc-dang-week1-20261019-001/runs/development --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e --output artifacts/detection-tracking/dang-check-development-001
```

Chọn output mới nếu tên đã tồn tại. Exit 0, JSON complete và counts **18 dataset/36 snapshot/108 detector runs** nghĩa là tự kiểm tra input đạt; không phải nghiệm thu tracker hoặc xác nhận người nhận đã đọc. `snapshot_inventory.csv` có paths tương đối từ `.../runs/development/`, chọn `canonical=True` (seed 0).

Làm stable/grow generator seed 11 trên **truth membership** trước; sau đó đủ sáu case development. Đọc truth events/links để đánh giá, không đưa đáp án vào tracker. Khi chạy trên Leiden, giữ reference riêng và thêm truth–detector mapping. **Khóa tracker/evaluator của Đăng trước khi dùng evaluation**; detection đã khóa của Phúc không tự khóa phần Đăng. Xem mục 8 trong guide để biết code/config/predictions/F1/support/confusion và receipt cần gửi lại.

## 3. Xem hoặc chạy notebook

Để xem ngay, mở executed notebook trong bảng mục 1; PNG/CSV nằm ở hai output directories. Để chạy lại, môi trường đã kiểm chứng là **Windows, CPython 3.12.6**, versions trong `document/specs/phuc/006-handoff-demo/replay-constraints-py312.txt`. Cài Python phù hợp trước; lệnh `py -3.12` bên dưới cần Windows Python Launcher. Nếu dùng đường dẫn Python khác, kiểm tra đúng interpreter/version.

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check --no-cache-dir install --constraint document/specs/phuc/006-handoff-demo/replay-constraints-py312.txt 'wheels/reddit_community_evolution-0.1.0-py3-none-any.whl[graph,evaluation,notebook]'
& .\.venv\Scripts\python.exe -m pip --isolated check
& .\.venv\Scripts\python.exe scripts/replay_synthetic_notebook.py --bundle artifacts/handoff/phuc-dang-week1-20261019-001 --output artifacts/detection-tracking/recipient-replay-001 --report artifacts/verification/recipient-replay-001
```

Output/report và sibling `-cases` phải mới. Script chọn đúng Python đang gọi làm kernel; không cài package hoặc sửa `sys.path` trong notebook. Gói wheel dùng để đọc/replay và chạy tests; muốn sinh lại scientific benchmark đã khóa phải dùng driver `09623f1`, archived source/versions và freeze gốc theo hướng dẫn Git. Không nới source gate vì package hiện có thêm reporting modules.

Notebook thành công có 10 code cells chạy theo thứ tự, 6 hình, output replay 14 files và output case 12 files, metadata riêng. Môi trường/platform/versions khác chưa được nghiệm thu bằng gate T05. Hướng dẫn `clean-replay.md` dành cho người làm từ Git clone có bước `git archive`; gói ZIP này dùng wheel đã kèm như lệnh trên.

## 4. Hiểu kết quả và phần chưa có

Recorded seed 0: AMI mean **development 0.955879927**, **evaluation 0.933116751**, coverage **1.0**. Toàn bộ 216 metrics có **198 valid/18 null**; không thay null bằng 0/1. Đây là detection trên dữ liệu tổng hợp, không phải event-F1, forecast accuracy hoặc kết quả Reddit. Seeds 1/2 diagnostic, không đổi seed chính theo điểm.

Case merge `dev-merge-easy-g11/2020-02`: truth C24 bị chia thành 12/12, K12 riêng; AMI **0.724164871**, coverage 1. Case dissolve `dev-dissolve-easy-g11/2020-02`: truth K12, detector 5/4/3; AMI **null/truth_constant** theo policy, hai phân hoạch vẫn khác. Bảng đếm user không phải confusion matrix sự kiện; edge densities mô tả graph, chưa chứng minh nguyên nhân tối ưu Leiden.

T05 đã đạt **385/385 full repo tests, 0 skip/failure/error**, hai fresh kernels trên môi trường cài mới; đó là bằng chứng lịch sử đã kèm, không phải số tests tự chạy khi giải nén. Kết quả kiểm tra đóng gói T06 và checksum ZIP xem reference ngoài ZIP. Phúc báo đã nhắn Đăng; chưa có receipt đọc gói, tracker truth/detector, mapping, event-F1/confusion hoặc demo cặp để nghiệm thu. Passing consumer/notebook không thay phản hồi của Đăng.

Mẫu Đăng phản hồi sau khi chạy thật:

```text
Tên ZIP / SHA-256 thực tế:
Python version:
Lệnh đã chạy / exit code hoặc traceback:
Dataset / reference đã đọc:
Nhánh, commit, module/API tracker và cấu hình:
Đầu ra truth trước / detector + mapping sau:
```
