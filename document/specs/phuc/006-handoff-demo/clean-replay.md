# Chạy notebook từ môi trường mới — PHUC-006-T05

Dùng [notebook hiện tại](../../../../notebooks/detection_tracking/01_synthetic_demo.ipynb), gói dữ liệu T02 đầy đủ và [script replay](../../../../scripts/replay_synthetic_notebook.py). Script mở kernel mới bằng **đúng Python đang gọi script**, chạy từ đầu, lưu executed notebook/log JSON riêng; không cần đăng ký kernel toàn máy. Gói T02 phải nhận riêng, không có trong Git clone.

[replay-constraints-py312.txt](replay-constraints-py312.txt) ghi các versions đã dùng trên **Windows, CPython 3.12.6**. Đây là constraints cho môi trường replay/test, không thay `pyproject.toml`, source closure hoặc freeze của benchmark PHUC-005. Không suy ra đã kiểm chứng mọi Python/platform/phiên bản được khoảng dependency cho phép. Replay đọc AMI cũ; full repo tests dùng fixtures tạm, không chạy lại production evaluation giữ lại.

## Chuẩn bị môi trường mới

Chạy PowerShell tại root repo. Dùng interpreter **Python 3.12.6**; trên máy Phúc là `.venv/Scripts/python.exe`. Ví dụ dưới dùng tên mới `phuc-006-replay-002`; nếu đã tồn tại, chọn tên khác. Không chạy lại vào thư mục evidence đã lưu.

```powershell
$replayRoot = Join-Path (Get-Location) 'artifacts/environments/phuc-006-replay-002'
if (Test-Path -LiteralPath $replayRoot) { throw 'Chọn replayRoot mới.' }
New-Item -ItemType Directory -Path $replayRoot | Out-Null
& .\.venv\Scripts\python.exe -m venv (Join-Path $replayRoot 'venv')
$replayPython = Join-Path $replayRoot 'venv/Scripts/python.exe'
```

Để build không tạo `build/` trong root đang làm, lấy source package đã commit vào thư mục mới. Archive này chỉ lấy `src`, `pyproject.toml`, `README.md`, không đưa dữ liệu Reddit vào build. Nếu đang review thay đổi local chưa commit, archive HEAD chưa chứa các thay đổi đó.

```powershell
git archive --format=zip --output (Join-Path $replayRoot 'source.zip') HEAD src pyproject.toml README.md
Expand-Archive -LiteralPath (Join-Path $replayRoot 'source.zip') -DestinationPath (Join-Path $replayRoot 'source')
& $replayPython -m pip --isolated --disable-pip-version-check --no-cache-dir wheel --no-deps --wheel-dir (Join-Path $replayRoot 'wheels') (Join-Path $replayRoot 'source')
$replayWheels = @(Get-ChildItem -LiteralPath (Join-Path $replayRoot 'wheels') -Filter '*.whl')
if ($replayWheels.Count -ne 1) { throw 'Cần đúng một project wheel.' }
$replayRequirement = $replayWheels[0].FullName + '[graph,evaluation,notebook]'
& $replayPython -m pip --isolated --disable-pip-version-check --no-cache-dir install --constraint document/specs/phuc/006-handoff-demo/replay-constraints-py312.txt $replayRequirement
& $replayPython -m pip --isolated check
```

Cài **regular wheel**, không editable và không dùng system site-packages. Ba extras cho phép kiểm tra đủ graph/evaluation/notebook trong một môi trường; đây không phải thử nghiệm cài tối thiểu chỉ extra notebook. Dừng và đọc lỗi nếu lệnh cài hoặc `pip check` thất bại; không dùng output cũ để thay bằng chứng cài đặt mới.

## Input và chạy tất cả cell

Giải nén ZIP T02 vào một thư mục mới có `delivery-manifest.json`, `runs`, `inventories`. Đối chiếu ZIP SHA-256 theo [reference T02](../evidence/PHUC-006-T02-delivery-reference.json); không thay pin theo hash do input lạ tự khai báo. Notebook còn kiểm tra lại manifest và từng file input trước/sau đọc/export.

```powershell
& $replayPython scripts/replay_synthetic_notebook.py `
  --bundle artifacts/handoff/phuc-dang-week1-20261019-001 `
  --output artifacts/detection-tracking/phuc-006-replay-002 `
  --report artifacts/verification/phuc-006-replay-002
```

`--bundle` trỏ **root thư mục giải nén**, không phải ZIP. `--project` mặc định root repo từ vị trí script. `--cwd` tùy chọn để thử chạy từ thư mục khác; notebook dùng `REDDIT_SNA_PROJECT` để tìm đúng project, không sửa `sys.path`.

Output/report phải mới, nằm trong `artifacts/`, không chồng input hoặc nhau; thư mục sibling `--output` thêm `-cases` cũng phải mới. Khi notebook lỗi, report vẫn giữ notebook đã chạy tới đâu và `notebook-result.json` trạng thái failed; không coi partial export là complete. Chạy lại bằng tên mới.

Thành công hiện tại: **10 code cells**, counts 1→10, không cell error, **6 inline PNG**. Output replay có 14 files; sibling `-cases` có 12 files, metadata/inventory riêng. Executed notebook và kết quả kernel ở `--report`. Script kiểm tra output complete/hash/size và source notebook không bị sửa trong lúc chạy; notebook nguồn trong Git không cache output.

Chạy test từ root bằng cùng Python:

```powershell
& $replayPython -m unittest discover -s tests -t . -v
```

Đây là unit/integration suite trên fixtures tổng hợp tạm; không phải benchmark tốc độ hoặc chạy lại toàn dữ liệu Reddit. Số pass/skip/error của lượt T05 thực tế, source/wheel hash và full logs nằm trong [evidence T05](../evidence/PHUC-006-T05-clean-replay.md). Receipt Đăng, tracker và demo cặp vẫn theo task board riêng.
