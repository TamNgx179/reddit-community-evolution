# PHUC-006-T05 — cài mới và chạy lại notebook

**DONE**, PHUC-006 **5/6**, tổng Phúc **35/36**; owner Phúc, ngày 19/10/2026. Base `8a010de`, nhánh `feat/phuc-006-handoff-demo`, [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11). **FR02/FR03 và AC02 đạt**. T06 chốt phần Phúc còn riêng; receipt/tracker/demo cặp chưa được nghiệm thu.

## Kết quả chính

Đã tạo **venv mới**, xác minh ban đầu chỉ có `pip==24.2`, `include-system-site-packages=false`, không tìm thấy project/graph/notebook/evaluation packages. Build regular wheel từ 46 file input của package/README/pyproject tại base, cài mới ba extras `graph,evaluation,notebook` bằng pip isolated/no-cache và [constraints đã version](../006-handoff-demo/replay-constraints-py312.txt). Không thay venv cũ hoặc freeze PHUC-005.

- CPython **3.12.6**, Windows; **55 distributions** sau cài. `pip check` exit 0: **No broken requirements found**.
- Wheel `reddit_community_evolution-0.1.0-py3-none-any.whl`, **119.260 byte**, SHA-256 `4367f739298a4fa007954406cca140f502ba197b14944f990d8dcb493efce405`.
- Probe `python -I` xác minh import từ `venv/Lib/site-packages/reddit_sna`, **44 file Python khớp source**, không editable/system site-packages. Wheel không chứa root `pyproject.toml`; đây là runtime replay cài mới, không phải closure 42 file của scientific freeze cũ.
- ZIP T02 được giải nén lại vào `artifacts/handoff/phuc-006-t05-input-001/`: đủ **821 files**, CRC/bytes từng entry và mọi manifest hash/size đúng. ZIP/dữ liệu nguồn cũ không đổi.
- Hai **fresh kernels** dùng đúng Python mới: mỗi lượt **21 cells/10 code cells**, execution counts **1→10**, **0 cell error**, **6 inline PNG**. Lượt 001 cwd thư mục notebook, **132.980s**; lượt 002 cwd ngoài repo trong `%TEMP%`, **60.981s**. Cell đầu in đúng clean interpreter; không sửa source notebook hoặc `sys.path`, không cài package trong cell.
- **18 CSV comparisons và 12 PNG comparisons đều giống byte T04**: mỗi lượt bốn CSV/bốn hình replay và năm CSV/hai hình case analysis. Full **216 metrics/42 summary, 198 valid/18 null**, canonical seed 0, các seed/split/status/reason giữ nguyên. Không tính lại source AMI hoặc chạy production benchmark/evaluation giữ lại.
- **Full repo 385/385 tests PASS**, **0 skip/0 failure/0 error**, **451.564s wall** ở lượt hoàn chỉnh. Unit/integration tests dùng fixtures tổng hợp và output tạm; các metrics test không phải lượt benchmark production mới. Đã giữ nguyên **9.507 artifact cũ**, 42 frozen source files và tất cả source/config/notebook đã track trước cập nhật tài liệu trạng thái.

Hai lượt replay chạy cùng thời điểm với suite và có cache/load khác nhau; thời gian trên là wall time thực thi notebook, không phải benchmark thuật toán hay bằng chứng tăng tốc. Recorded producer timings trong CSV vẫn là số cũ.

## Chạy lại bằng một lệnh

Thêm [scripts/replay_synthetic_notebook.py](../../../../scripts/replay_synthetic_notebook.py). Script dùng `sys.executable` làm kernel argv, cleanup kernel tường minh, lưu executed notebook và JSON kết quả vào report mới, kiểm tra complete metadata/hash/size/source notebook. Cả output, sibling `-cases` và report phải mới, trong `artifacts/`, không chồng input hoặc nhau. Failed execution giữ notebook chạy dở/status failed; không coi output partial là complete. Bốn CLI checks đạt: help exit 0; existing output/overlap/outside-artifacts exit 2 trước khi tạo output/report.

Sau khi cài package, từ root repo với **đúng Python kernel**, ví dụ trên máy Phúc:

```powershell
& artifacts/environments/phuc-006-t05-clean-001/venv/Scripts/python.exe scripts/replay_synthetic_notebook.py `
  --bundle artifacts/handoff/phuc-006-t05-input-001 `
  --output artifacts/detection-tracking/phuc-006-replay-NEW `
  --report artifacts/verification/phuc-006-replay-NEW
```

`NEW` là tên chưa tồn tại, không tái sử dụng output đã lưu. Bundle là thư mục giải nén đầy đủ có `delivery-manifest.json`; Git clone không tự có bundle. [Hướng dẫn môi trường sạch](../006-handoff-demo/clean-replay.md) có cách build wheel ngoài root, constraints, kernel/cwd và lệnh unit/integration đầy đủ. Python/platform khác hoặc dependency versions khác chưa được nghiệm thu bằng lượt này.

## Lệnh và artifact thật

Harness thực hiện đúng các bước: `.venv/Scripts/python.exe -m venv <new-venv>`; probe thiếu package; clean Python `pip --isolated --no-cache-dir wheel --no-deps ...`; `pip --isolated --no-cache-dir install --constraint ... <wheel>[graph,evaluation,notebook]`; `pip check`, `pip freeze --all`; installed source probe; hai CLI replay; unittest discovery tương đương lệnh:

```powershell
& artifacts/environments/phuc-006-t05-clean-001/venv/Scripts/python.exe -m unittest discover -s tests -t . -v
```

Runner dùng cùng unittest discovery/verbosity và ghi progress/log/JSON, không sửa test hoặc bỏ test. Đường dẫn tương đối dưới root repo:

| Nơi lưu | Nội dung |
|---|---|
| `artifacts/environments/phuc-006-t05-clean-001/` | Venv cài mới, build source, wheel; không đóng gói cả môi trường lớn vào proof ZIP |
| `artifacts/detection-tracking/phuc-006-t05-notebook-001/002` và sibling `-cases` | Mỗi lượt 14 replay files + 12 case files, PNG/SVG/CSV/JSON/metadata riêng |
| `artifacts/verification/phuc-006-t05-001/replay-001/002` | Hai executed notebooks, result JSON và output copies |
| `artifacts/verification/phuc-006-t05-001/` | Baseline, build/input/install steps/logs, pip freeze/check, installed probe, full suite log/result/progress, CLI guards, source/tests/wheel, input ZIP nguyên byte và audits |
| `artifacts/verification/phuc-006-t05-001.zip` | **154 files/5.713.130 byte**, CRC/từng entry bytes verified, SHA-256 `c91f11b09d4d3a46041c4369bb045094be5a8a0a8b5f1de8adb5686ad1e29cc7` |

[Reference/checksum](PHUC-006-T05-clean-replay-reference.json) và [30 dòng đối chiếu CSV/PNG](PHUC-006-T05-output-comparison.csv) có trong Git. Full artifacts, venv, executed notebooks và proof ZIP lưu local, bị Git ignore. Hình không đổi byte nên dùng [preview T04](PHUC-006-T04-case-analysis.md), không commit thêm các PNG trùng lặp.

## Timeout trước đó và kiểm tra launcher Windows

Lượt full suite đầu bị ngắt khi phiên trước timeout: còn `full-suite.log`/`full-suite-process.log`, không có final summary. Giữ nguyên hai log và `full-suite-001-interrupted.json`; không suy ra pass/fail hoặc cộng lượt đó vào số tests đạt. Lượt 002 bắt đầu discovery lại và chạy đủ **385 tests**.

Ở lượt 002, native `reddit-sna.exe` có độ trễ vượt timeout giao tiếp được đặt trong test, rồi **tự trả về, test đạt**. Source entry point và test giữ nguyên; hai PID được xem xét đã thoát trước lúc thử cleanup, không process nào bị dừng. `launcher-inspection.json`/`launcher-observation.json` giữ quan sát và embedded entry point; chưa xác định nguyên nhân độ trễ. Không ghi là lỗi source đã sửa, không bỏ test hoặc nới gate.

T05 chứng minh chạy lại notebook detection từ môi trường cài mới trên máy hiện tại. Chưa có kết quả Reddit/forecast/event-F1 hoặc receipt/tracker Đăng. **Tiếp theo PHUC-006-T06** chốt gói phần Phúc và cập nhật riêng các mốc phối hợp bằng artifact thật.
