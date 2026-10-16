# Bằng chứng PHUC-001-T01 — môi trường Python và test Leiden

**Task:** [PHUC-001-T01](../tasks.md#phuc-001). **Kết quả:** DONE.
**Kiểm tra hoàn tất:** 16/10/2026 18:37:02, Asia/Bangkok (UTC+07:00).

## Môi trường thực tế

- Hệ điều hành Windows, kiến trúc AMD64.
- Python **3.12.6**, dùng bản 3.12 có sẵn để tạo project-local virtual environment.
- Interpreter: `C:\Users\MSi\reddit-community-evolution\.venv\Scripts\python.exe`.
- Đã xác minh `sys.prefix != sys.base_prefix` và package `reddit_sna` được import từ `src/reddit_sna` của checkout này qua editable install.
- Source cơ sở: commit `8d135c99deec56a6aaf51320f1f3f006dd9f911c`. Nhánh làm việc: `chore/phuc-001-t01-environment`; thay đổi task này là tài liệu và `.gitignore`, không sửa thuật toán/test hiện có.

| Package | Phiên bản đã cài |
|---|---|
| reddit-community-evolution | 0.1.0, editable |
| igraph | 1.0.0 |
| leidenalg | 0.12.0 |
| scikit-learn | 1.9.1 |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| matplotlib | 3.11.2 |
| nbclient | 0.11.0 |
| nbformat | 5.11.1 |
| ipykernel | 7.4.0 |
| pip | 24.2 |

scikit-learn được cài trong môi trường để kiểm tra sẵn sàng theo kế hoạch. Chưa bổ sung dependency này vào `pyproject.toml`: khai báo dependency evaluator thực dùng vẫn thuộc PHUC-004-T03, khi triển khai tính AMI trong source.

## Lệnh đã thực hiện

Chạy tại thư mục gốc project. Lệnh tạo môi trường chỉ dùng khi `.venv` chưa tồn tại:

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input -e '.[graph,notebook]' scikit-learn
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_leiden -v
& .\.venv\Scripts\python.exe -m pip freeze --all
```

Import verification đã chạy qua script cục bộ, kiểm tra: `reddit_sna`, `igraph`, `leidenalg`, `sklearn`, `numpy`, `matplotlib`, `nbclient`, `nbformat`, `ipykernel`; tất cả thành công. Đường dẫn từng module được lưu trong `import-check.json`.

Có thể kiểm tra nhanh lại bằng:

```powershell
& .\.venv\Scripts\python.exe -c "import sys, reddit_sna, igraph, leidenalg, sklearn, numpy, matplotlib, nbclient, nbformat, ipykernel; print(sys.executable); print('Imports OK')"
```

## Kết quả kiểm tra thực tế

- Cài dependencies: exit code **0**; thời gian cài 417.398 giây, từ 18:29:28 đến 18:36:25. Đây là thời gian cài môi trường, không phải benchmark detector.
- Import verification: **PASS**.
- `pip check`: exit code **0**, `No broken requirements found.`
- `unittest`: exit code **0**, **3 tests chạy, 3 pass, 0 skip, 0 failure, 0 error**.
- Thời gian do unittest báo: **1.124 giây**; wall time toàn subprocess test: **1.995 giây**.

```text
test_invalid_edge_is_rejected ... ok
test_known_disconnected_cliques_and_empty_graph ... ok
test_membership_reference_binds_graph_content_and_is_shared_across_months ... ok

Ran 3 tests in 1.124s
OK
```

Ba test kiểm tra cạnh không hợp lệ, graph hai clique/graph rỗng, và reference membership gắn nội dung graph dùng xuyên tháng. Chúng dùng dữ liệu tổng hợp trong thư mục tạm của test. Chưa chạy bộ benchmark tuần 1, chưa tính AMI và chưa nghiệm thu các task fixture/tracker.

## Log và snapshot cục bộ

Thư mục: `artifacts/environment/phuc-001-t01-001/` tại checkout này.

| File | Nội dung | SHA-256 |
|---|---|---|
| `install.log` | Log pip đầy đủ | `d153e3025d667ae6ac94f635cd9239b4142ab100c537201a4b26e5cb3e4ec537` |
| `import-check.json` | Interpreter, module paths và versions | `d9dd8e1990130ecd834c8cf361718412f2859acb2ac79b8d06db02dbec201aa2` |
| `pip-check.log` | Kiểm tra dependency | `672aec65a45bed50e70229c70934a7eebf0462595c459b83023027645d57cccf` |
| `leiden-tests.log` | Output unittest đầy đủ | `cb0376b0d5c3ecdc434df2a80325839c7994341cc1b73446ecc168d17458ba10` |
| `pip-freeze.txt` | Snapshot toàn bộ package đã cài | `120317fb70326841f28d3fa85c766f978cde2a64ad19b94aca87133439ef855e` |
| `verification-result.json` | Kết quả tổng hợp và hashes bằng chứng | `efbe7b99a25e1441a53072b9f86bd4cc143f05eda36860c8a41323ed4deef91d` |

Thư mục còn có `install-command.json`, `install-result.json`, `verification-commands.json` và script `verify_environment.py` dùng cho lượt kiểm tra này. Log/snapshot trong `artifacts/` là dữ liệu cục bộ được ignore; người xem repo có bản tóm tắt này và các lệnh để kiểm tra trên môi trường của họ, không mặc nhiên truy cập được log máy Phúc.

`.gitignore` được thêm cho `.venv`, Python cache, editable-install metadata và `artifacts/`. Các dependency được cài trong `.venv`; không tạo fixture hoặc module thuật toán mới trong task T01.
