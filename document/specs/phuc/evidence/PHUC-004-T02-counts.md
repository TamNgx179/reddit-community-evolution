# Bằng chứng PHUC-004-T02 — Counts, coverage và số nhóm

**Task:** [PHUC-004-T02](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 2/6, tổng 20/36 task.
**Kiểm chứng hoàn tất:** 18/10/2026 21:15:09, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `a673909` cộng T02, nhánh `feat/phuc-004-detection-evaluation`, tiếp tục PR #9.
**Môi trường:** Python 3.12.6; fixture detector dùng igraph 1.0.0/leidenalg 0.12.0. Hàm đếm mới chỉ dùng stdlib/module hiện có, không thêm dependency.

## Vừa làm gì và cách dùng

Thêm `DetectionCounts` và `count_snapshot` trong [evaluation/detection.py](../../../../src/reddit_sna/evaluation/detection.py). Sau khi loader T01 xác minh gói dữ liệu và căn nhãn, hàm đếm một snapshot. Hàm cũng kiểm tra record được tự dựng: lengths phải khớp, ID phải duy nhất/đã sort, endpoint thuộc active và truth của cùng user phải thống nhất giữa hai tập.

```python
from reddit_sna.evaluation.detection import load_aligned_detection, count_snapshot

# source và detection là Path của hai dataset directory PHUC-002/003 tương ứng.
result = load_aligned_detection(source, detection, detector_seed=0)
for snapshot in result.snapshots:
    counts = count_snapshot(snapshot)
    print(counts.month, counts.assigned_nodes, counts.active_nodes, counts.coverage)
```

Counts gồm active/endpoint/assigned/isolate, coverage/status và ba số nhóm: truth trên toàn active, truth trên endpoint được chấm, predicted trên endpoint. Coverage lấy **assigned / active**, giữ isolate trong mẫu số. Active > 0 nhưng không có cạnh cho coverage 0.0/status `defined`; active = 0 cho None/status `no_active_users` (CSV trống/JSON null). Group counts rỗng bằng 0; partition constant/singleton vẫn đếm bình thường. [README](../004-detection-evaluation/README.md#đếm-người-coverage-và-số-nhóm--t02) có bảng field và ví dụ dễ đọc.

T02 trả record trong bộ nhớ. Các CSV dưới đây là bằng chứng kiểm chứng, chưa thay exporter metrics/summary/timing production của T04. AMI, policy missing/degenerate, tập evaluation và tracker còn ở các task sau.

## Kiểm tra đã chạy

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.integration.test_detection_alignment -v
```

**20/20 test liên quan pass**, 0 skip/failure/error, log cuối **6.804s**, process wall **8.749s**. Lượt kiểm tra đầu cũng 20/20 pass (7.564s); sau khi bỏ import thừa, lượt cuối ghi log và source hashes để bàn giao. Không chạy lại toàn bộ test repo ở T02; giới hạn discover của lượt T01 vẫn được giữ trong [bằng chứng T01](PHUC-004-T01-alignment.md).

T02 thêm **6 unit test và 1 integration test**: isolate giữ trong mẫu số và số nhóm truth toàn bộ; full coverage/đổi tên nhóm/thứ tự dòng; all-isolate khác empty-active; singleton/constant counts; cùng user ở hai tháng đếm riêng; malformed aligned record bị chặn; counts từ detection thật có isolate khớp CSV. Test zero-edge cũ bổ sung kiểm tra coverage/groups. 20 test gồm cả 13 test alignment T01.

## Đầu ra thực tế

Đọc lại 18 dataset development của `phuc-002-t06-001` và detection tương ứng `phuc-003-t06-001`, generator 11/12/13, detector 0/1/2, gamma 1/canonical 0, hai tháng giả lập 2020-01/2020-02. Giữ runtime JSON/config/seed hiện có. **108 dòng development** đều có assigned = endpoint = active và coverage **1.0**, isolate = 0; tổng assigned qua các dòng là **3.024**, có lặp user qua tháng/seed.

Sinh thêm hai gói diagnostic stable g11 trong proof: `mixed-isolates` dùng p_in=0.05/p_out=0, `zero-edges` dùng p_in=p_out=0. Đây là fixture kiểm tra coverage, có config và graph references riêng; không trộn vào cohort development hoặc thay cấu hình benchmark mặc định. Cả hai dùng ba seed detector, tạo 12 dòng. Thêm hai record trong bộ nhớ cho nhóm chỉ gồm isolate và tháng không có active: tổng **14 dòng diagnostic**.

| Ví dụ, seed 0 nếu có detector | Active | Endpoint / assigned | Isolate | Coverage | Truth nhóm toàn bộ / được chấm | Nhóm dự đoán |
|---|---:|---:|---:|---:|---:|---:|
| Mixed-isolates 2020-01 | 24 | 12 | 12 | 0.5 | 2 / 2 | 5 |
| Mixed-isolates 2020-02 | 24 | 5 | 19 | 0.208333… | 2 / 1 | 2 |
| Zero-edges, mỗi tháng | 24 | 0 | 24 | 0.0 | 2 / 0 | 0 |
| Memory: nhóm K chỉ có isolate | 3 | 2 | 1 | 0.666666… | 2 / 1 | 1 |
| Memory: không có active | 0 | 0 | 0 | null, `no_active_users` | 0 / 0 | 0 |

Coverage 100% chỉ phản ánh tập người được gán; số nhóm và nhãn vẫn có thể khác truth. Chưa kết luận chất lượng phân hoạch hoặc tính AMI. Mọi dữ liệu trên là benchmark tổng hợp, không phải Reddit.

## Bằng chứng độc lập và file đã lưu

- [CSV development 108 dòng](PHUC-004-T02-development-counts.csv) và [CSV diagnostic 14 dòng](PHUC-004-T02-diagnostic-counts.csv) theo Git. Giữ dataset/context/seed/canonical, hai reference, input paths và tất cả counts/status; đường dẫn tương đối với proof đã giải nén.
- Full proof local `artifacts/verification/phuc-004-t02-001/`: `counts.csv` 122 dòng, hai bảng trên, `memory-examples.json`, **360 file input/fixture**, runner/consumer, raw test log, 20-row test CSV, before/result/proof hashes.
- Consumer `read_counts.py` chạy bằng `python -I`, chỉ stdlib: đọc nodes/R/truth/prediction trực tiếp, xác minh hashes/reference/tháng/tập người và tự đếm/tính tỉ lệ. **122/122 dòng khớp**; không import project, igraph hoặc sklearn.
- **1.246 artifact có trước giữ nguyên hash**, gồm 904 file detection-tracking và proof/ZIP final T01. Source/config/test hashes cũng khớp trước/sau kiểm chứng.
- ZIP `artifacts/verification/phuc-004-t02-001.zip`: **372 file, 294.838 byte**; CRC/từng entry/proof hash manifest đều đã kiểm tra. SHA-256 **`7d06b50ffa9ec1f3b8d46e483fd39c3cf43e263badf3ea68831dbeb899cc89ac`**. Sibling `.zip.sha256` và `.archive.json` lưu thông tin archive.

Giải nén ZIP rồi kiểm tra bằng stdlib:

```powershell
python -I <thu-muc-giai-nen>/read_counts.py <thu-muc-giai-nen>
```

Muốn tính lại bằng API, chọn các dataset trong `inputs/development/source/` và `inputs/development/detected/`; [README](../004-detection-evaluation/README.md) có lệnh loader. Hoặc tái tạo source/detection theo PHUC-002/003 rồi thay paths. Recorder `verify.py` ghi nhận một lượt với paths/run IDs cụ thể, không retry vào proof cũ; chưa phải CLI export metric production. Full artifact/ZIP bị ignore, cần chia sẻ ZIP thực tế hoặc tái tạo để người khác truy cập.

**FR02/T02 DONE. Tiếp theo PHUC-004-T03:** tính AMI bằng thư viện, ghi policy missing/degenerate và khai báo dependency thực dùng; chưa có receipt/review Đăng.
