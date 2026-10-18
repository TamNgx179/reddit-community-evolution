# Adapter Leiden tổng hợp — lịch detector seed 0/1/2

**T01** nối graph benchmark với `detect_snapshots` có sẵn; **T02** đọc và chạy đủ detector seeds 0/1/2 từ cấu hình, giữ canonical 0. Đầu vào là các cạnh quan hệ theo tháng; đầu ra là bảng mỗi người được detector gán vào nhóm nào. Thuật toán tự tìm nhóm từ graph, không đọc membership/events/links chuẩn để tạo kết quả.

## API và cách chạy

API nằm trong [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py):

```python
detect_synthetic_dataset(source: Path, output: Path, *, benchmark_config: Path | None = None) -> dict
```

`source` là một dataset graph/truth schema 1 đã xuất, ví dụ `dev-stable-easy-g11`; không truyền cả run 18 dataset. Hàm kiểm tra metadata/config, dataset/identity, tháng, hash của config/R/nodes, cạnh/unit weight/thứ tự và node coverage. Sau đó gọi detector với **seeds `(0,1,2)`, gamma `1.0`, canonical 0, protocol `synthetic-planted-undirected-v1`**, identity scope và observed months của dataset. Đây là seed detector, khác generator seed 11 đã dùng sinh graph.

`benchmark_config` chọn file JSON runtime, ví dụ `Path("configs/benchmark_week1.json")`. Nếu không truyền, API đọc bản `benchmark-config.json` đã lưu trong dataset. Các trường công thức sinh graph phải khớp bản nguồn; riêng mục detector được đọc từ file runtime. API ghi path/hash của file thực đọc trong `result["detector_config"]` và kiểm tra file không đổi trước khi xuất membership.

Protocol tuần 1 yêu cầu đúng thứ tự `[0,1,2]`, gamma 1, canonical 0. Lịch rút gọn/đảo thứ tự/đổi canonical hoặc công thức graph lệch bị từ chối trước output; không bỏ qua config để chạy default khác. Generic JSON validator có thể nhận lịch khác, nhưng adapter tuần 1 chỉ nhận protocol này. T01 là lượt lịch sử chạy riêng seed 0, artifact/evidence cũ giữ nguyên; API hiện tại chạy ba seed. Lượt kiểm chứng T02 vẫn chỉ dùng stable development, không chạy evaluation.

Từ repo đã cài editable package cùng `[graph]`, chạy ví dụ sau và chọn tên folder mới:

```powershell
@'
import json
from pathlib import Path
from reddit_sna.pipelines.detection_tracking import detect_synthetic_dataset

source = Path("artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11")
run = Path("artifacts/detection-tracking/phuc-003-three-seed-demo")
run.mkdir(parents=True, exist_ok=False)
result = detect_synthetic_dataset(source, run / "memberships",
                                  benchmark_config=Path("configs/benchmark_week1.json"))
with (run / "prototype-detection.json").open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
    handle.write("\n")
print("canonical_seed:", result["canonical_seed"])
print([(m["month"], [(r["seed"], r["assigned_users"], r["sizes"]) for r in m["runs"]])
       for m in result["months"]])
'@ | & .\.venv\Scripts\python.exe -
```

Nếu chưa có source local, tái tạo nó bằng [lệnh full development PHUC-002](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06), chọn run ID mới rồi đổi path `source` cho đúng. Artifact local không tự đi theo Git.

Ví dụ API lưu:

```text
artifacts/detection-tracking/<new-folder>/
  memberships/2020-01/membership-seed0.csv
  memberships/2020-01/membership-seed1.csv
  memberships/2020-01/membership-seed2.csv
  memberships/2020-02/membership-seed0.csv
  memberships/2020-02/membership-seed1.csv
  memberships/2020-02/membership-seed2.csv
  prototype-detection.json
```

Parent của `output` phải tồn tại; `output` phải mới và không chồng source. API không sửa input, config hoặc output cũ. Ví dụ này tạo folder rồi lưu diagnostics trả về, chưa phải runner nghiên cứu đầy đủ. Gói kiểm chứng T01/T02 có thêm manifest scope `synthetic-detection-prototype`; mapping/persistence chính thức của adapter thuộc T03.

## Cách đọc kết quả

- CSV đúng header `reference_id,month,community_id,user_id`, UTF-8/LF, sort tháng/nhóm/user. Chỉ gán đúng endpoint của R: mỗi người có cạnh một hàng. Isolate vẫn nằm trong source nodes.csv, không bị âm thầm coi là đã được detector gán.
- `c0`, `c1` là tên nhóm cục bộ theo tháng. Không tự suy ra `c0` tháng 1 là cùng cộng đồng với `c0` tháng 2; tracking cần liên kết riêng.
- Mỗi seed có reference detector riêng, khác truth; cùng seed giữ chung reference qua các tháng. Reference gắn identity scope + graph cohort fingerprint + gamma/seed. API chặn thiếu/thừa/trùng endpoint, đảo run hoặc lẫn reference giữa các seed.
- Dict trả về có diagnostics của detector, phiên bản igraph/leidenalg, input hashes, active/isolate counts và context dataset. `schema_version=2` là version diagnostics của detector có sẵn; `membership_schema_version=1` là schema CSV chung của benchmark.
- `modularity`/`rb_objective` là diagnostics, không phải AMI/accuracy. `seed_pair_ARI` có thứ tự cặp **(0,1), (0,2), (1,2)** khi graph không rỗng, đo độ giống nhau giữa các seed. Canonical luôn là seed đầu đã cấu hình (0), không chọn điểm cao nhất.
- R rỗng cho ba membership header-only/tháng, assigned 0, `empty_graph_no_partition`, modularity/objective null và `seed_pair_ARI=[]`. API vẫn giữ active/isolate counts đúng, không điền ARI giả cho graph rỗng.

Thuật toán Leiden và quy tắc graph Reddit không bị sửa để phục vụ giả lập. Wrapper dùng source CSV canonical và protocol synthetic riêng; chỉ xuất membership đã kiểm tra. Full `run` detection–tracking vẫn báo chưa triển khai, vì tracker/evaluator chưa được nối.

## Kiểm tra và phần tiếp theo

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection tests.unit.test_leiden tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_graph_export tests.unit.test_benchmark_config tests.integration.test_cli -v
```

Suite hiện **61/61 test liên quan pass**. T02 thêm bốn test cho config runtime, lịch lỗi bị chặn trước output, canonical không đổi dù seed khác có quality cao hơn và reference/order không bị trộn. Các test có sẵn đã mở rộng sang đủ ba seed, kể cả graph rỗng. [Bằng chứng T02](../evidence/PHUC-003-T02-detector-schedule.md) ghi hai run stable, mỗi tháng/seed có 24 assigned và hai nhóm 12/12, sáu membership tái lập, ARI seed ≈1 và ZIP đã lưu. [T01](../evidence/PHUC-003-T01-leiden-adapter.md) giữ lượt lịch sử 57 test và prototype một seed. Test hiện có chưa thay thế nghiệm thu đầy đủ của T04/T05.

Tiếp theo **PHUC-003-T03** lưu `detection.json` và mapping dataset/reference/tháng/seed trong metadata, để evaluator/tracker đọc kết quả có nguồn rõ ràng. AMI/coverage evaluator thuộc PHUC-004; không cần chờ tracker của Đăng để tiếp tục.
