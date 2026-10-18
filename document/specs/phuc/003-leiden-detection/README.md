# Adapter Leiden tổng hợp — xuất gói detection có nguồn rõ ràng

**T01** nối graph benchmark với `detect_snapshots` có sẵn; **T02** đọc và chạy đủ detector seeds 0/1/2 từ cấu hình, giữ canonical 0; **T03** xuất membership, diagnostics, config và metadata mapping thành một gói. Đầu vào là các cạnh quan hệ theo tháng; đầu ra là bảng mỗi người được detector gán vào nhóm nào. Thuật toán tự tìm nhóm từ graph, không đọc membership/events/links chuẩn để tạo kết quả.

**PHUC-003 đã DONE cả 6 task.** T04/T05 kiểm tra lỗi và integration; T06 chạy đủ development mặc định qua hai process, mỗi run có 18 dataset/36 snapshot/108 membership. Toàn repo 238 test pass; output, diagnostics và bằng chứng đã lưu. Đây là hoàn thành bước detection; AMI/tracking/full pipeline còn riêng.

## API và cách chạy

API nằm trong [pipelines/detection_tracking.py](../../../../src/reddit_sna/pipelines/detection_tracking.py):

```python
detect_synthetic_dataset(source: Path, output: Path, *, benchmark_config: Path | None = None) -> dict
export_synthetic_detection(source: Path, output: Path, *, benchmark_config: Path | None = None) -> dict
```

`source` là một dataset graph/truth schema 1 đã xuất, ví dụ `dev-stable-easy-g11`; không truyền cả run 18 dataset. Hàm kiểm tra metadata/config, dataset/identity, tháng, hash của config/R/nodes, cạnh/unit weight/thứ tự và node coverage. Metadata nguồn cũng được ghi hash và kiểm tra không đổi. Sau đó gọi detector với **seeds `(0,1,2)`, gamma `1.0`, canonical 0, protocol `synthetic-planted-undirected-v1`**, identity scope và observed months của dataset. Đây là seed detector, khác generator seed 11 đã dùng sinh graph.

- `detect_synthetic_dataset` giữ giao diện T01/T02: ghi trực tiếp `<output>/<month>/membership-seed*.csv`, trả dictionary diagnostics. Chỉ dùng khi caller cần tự quản lý lưu diagnostics.
- `export_synthetic_detection` là cách xuất gói từ T03: gọi API trên, ghi `<output>/memberships/...`, `detection.json`, bản config thực đọc và `metadata.json`; trả metadata. Không bọc thêm một thư mục `memberships` khi gọi exporter.

`benchmark_config` chọn file JSON runtime, ví dụ `Path("configs/benchmark_week1.json")`. Nếu không truyền, API đọc bản `benchmark-config.json` đã lưu trong dataset. Các trường công thức sinh graph phải khớp bản nguồn; riêng mục detector được đọc từ file runtime. API ghi path/hash của file thực đọc trong `result["detector_config"]` và kiểm tra file không đổi trước khi xuất membership.

Protocol tuần 1 yêu cầu đúng thứ tự `[0,1,2]`, gamma 1, canonical 0. Lịch rút gọn/đảo thứ tự/đổi canonical hoặc công thức graph lệch bị từ chối trước output; không bỏ qua config để chạy default khác. Generic JSON validator có thể nhận lịch khác, nhưng adapter tuần 1 chỉ nhận protocol này. T01 là lượt lịch sử chạy riêng seed 0, artifact/evidence cũ giữ nguyên; API hiện tại chạy ba seed. Lượt kiểm chứng T02 vẫn chỉ dùng stable development, không chạy evaluation.

Từ repo đã cài editable package cùng `[graph]`, chạy ví dụ sau và chọn tên folder mới:

```powershell
@'
from pathlib import Path
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection

source = Path("artifacts/detection-tracking/phuc-002-t06-001/datasets/dev-stable-easy-g11")
run = Path("artifacts/detection-tracking/phuc-003-package-demo")
metadata = export_synthetic_detection(source, run,
                                     benchmark_config=Path("configs/benchmark_week1.json"))
print("dataset:", metadata["dataset_id"])
print("canonical_seed:", metadata["detector"]["canonical_seed"])
print([(m["month"], m["seed"], m["assigned_users"], m["path"])
       for m in metadata["memberships"]])
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
  detection.json
  detector-config.json
  metadata.json
```

Parent của `output` phải tồn tại; `output` phải mới và không chồng source, kể cả thư mục rỗng có sẵn cũng bị từ chối. Exporter chuẩn bị gói trong thư mục tạm rồi tạo output mới và chuyển `metadata.json` cuối cùng. Lỗi chuẩn bị không tạo output cuối; lỗi I/O khi chuyển file có thể để lại gói dở dang, không được retry vào đó. Không sửa input, metadata/config nguồn hoặc output cũ. Gói T01/T02 cũ và manifest prototype của chúng giữ nguyên; gói T03 có metadata `scope="detection"`, chưa phải manifest toàn pipeline của PHUC-005.

## Đọc gói và chọn file cho Đăng

`metadata.json` schema 1, artifact type `synthetic-detection`, lưu:

- Dataset/identity, split/scenario/generator seed, truth reference và các tháng thực quan sát. Truth reference chỉ là định danh để nối với gói nguồn; chưa phải matching cộng đồng detector–truth.
- `detector`: gamma, lịch seed, canonical 0, versions igraph/leidenalg, file config và hash. `detector-config.json` là bản sao **đúng byte của runtime JSON**, có cả công thức sinh graph/difficulty; có thể khác bản config archived trong source ở phần detector.
- `memberships`: một entry mỗi tháng/seed, gồm dataset, identity, reference, cờ canonical, đường dẫn CSV, SHA-256, graph/nodes nguồn, graph fingerprint và counts active/assigned/isolate/status. Graph rỗng vẫn có entry; không phải đoán reference từ CSV rỗng.
- `files`: hash của tám file khác trong gói; không tự hash `metadata.json`. `source.files`: hash sáu file graph/config/metadata đã đọc, không gồm CSV truth. `source.directory` và đường dẫn runtime trong diagnostics là dấu vết máy tạo gói.

Đường dẫn `memberships[*].path`, `diagnostics_file`, `detector.config_file` và keys `files` tương đối với **gói detection**. `graph_file`, `nodes_file`, keys `source.files` tương đối với **dataset graph nguồn**. Có thể chuyển gói detection sang chỗ khác và vẫn đọc/hash được các file trong gói; để kiểm tra endpoint hoặc tính AMI, phải cung cấp thêm gói nguồn tương ứng, không phụ thuộc đường dẫn tuyệt đối cũ.

Ví dụ kiểm tra toàn bộ hash rồi chọn hai membership canonical:

```powershell
@'
from hashlib import sha256
import json
from pathlib import Path

root = Path("artifacts/detection-tracking/phuc-003-package-demo")
meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
for name, info in meta["files"].items():
    assert sha256((root / name).read_bytes()).hexdigest() == info["sha256"]
for entry in meta["memberships"]:
    if entry["canonical"]:
        print(entry["dataset_id"], entry["month"], entry["seed"], root / entry["path"])
'@ | & .\.venv\Scripts\python.exe -
```

## Cách đọc kết quả

- CSV đúng header `reference_id,month,community_id,user_id`, UTF-8/LF, sort tháng/nhóm/user. Chỉ gán đúng endpoint của R: mỗi người có cạnh một hàng. Isolate vẫn nằm trong source nodes.csv, không bị âm thầm coi là đã được detector gán.
- `c0`, `c1` là tên nhóm cục bộ theo tháng. Không tự suy ra `c0` tháng 1 là cùng cộng đồng với `c0` tháng 2; tracking cần liên kết riêng.
- Mỗi seed có reference detector riêng, khác truth; cùng seed giữ chung reference qua các tháng. Reference gắn identity scope + graph cohort fingerprint + gamma/seed. API chặn thiếu/thừa/trùng endpoint, đảo run hoặc lẫn reference giữa các seed.
- `detection.json` lưu toàn bộ dictionary diagnostics của adapter: phiên bản igraph/leidenalg, input hashes, active/isolate counts, context dataset, chất lượng và timing mỗi tháng. `schema_version=2` là version diagnostics của detector có sẵn, khác metadata/membership schema 1. Timing tháng bao gồm cả ba seed, không phải thời gian riêng từng seed; JSON không hứa giống byte giữa hai lần chạy vì timing thay đổi.
- `modularity`/`rb_objective` là diagnostics, không phải AMI/accuracy. `seed_pair_ARI` có thứ tự cặp **(0,1), (0,2), (1,2)** khi graph không rỗng, đo độ giống nhau giữa các seed. Canonical luôn là seed đầu đã cấu hình (0), không chọn điểm cao nhất.
- R rỗng cho ba membership header-only/tháng, assigned 0, `empty_graph_no_partition`, modularity/objective null và `seed_pair_ARI=[]`. API vẫn giữ active/isolate counts đúng, không điền ARI giả cho graph rỗng.

Thuật toán Leiden và quy tắc graph Reddit không bị sửa để phục vụ giả lập. Wrapper dùng source CSV canonical và protocol synthetic riêng; chỉ xuất membership đã kiểm tra. Full `run` detection–tracking vẫn báo chưa triển khai, vì tracker/evaluator chưa được nối.

## Khi input hoặc môi trường có lỗi — T04

Adapter kiểm tra membership với đúng tập endpoint R, không lấy giao để bỏ user sai. CSV thiếu/thừa/trùng người, tháng/reference/header sai đều bị từ chối trước output cuối. Số nhóm và sizes trong diagnostics phải khớp CSV; node/edge counts phải khớp nguồn. Graph có cạnh cần status complete và quality hữu hạn; graph rỗng cần quality/connectivity null và ARI rỗng. Seed ARI graph không rỗng phải có đủ ba cặp, hữu hạn trong [-1,1] với tolerance số thực 1e-12, không sửa raw value.

| Trường hợp | API báo lỗi / cách xử lý |
|---|---|
| Thiếu igraph hoặc leidenalg | `ValueError` có hướng dẫn cài project `[graph]`; không gỡ/cài lại package khi chỉ kiểm chứng giả lập lỗi |
| Metadata sai cấu trúc/thiếu field, files/hash/counts sai, truth reference lệch dataset | `ValueError` rõ nguyên nhân; sửa hoặc tái tạo source theo exporter graph |
| CSV nguồn sai hoặc SHA-256 không khớp | `ValueError`; không chỉnh hash chỉ để bỏ qua lỗi trên dữ liệu thật |
| File nguồn thiếu | `FileNotFoundError` kèm path; cung cấp lại input đầy đủ |
| Output tồn tại, kể cả thư mục rỗng hoặc file | `FileExistsError`; chọn output mới, không tự xóa kết quả cũ |
| Source/config thay đổi trong khi detector chạy | `ValueError`; không xuất kết quả từ các phiên bản nguồn lẫn nhau |
| Backend lỗi sau khi đã ghi file tạm | Giữ nguyên lỗi backend, dọn scratch bằng context manager, không xuất output cuối hoặc sửa run cũ |

Isolate là người có trong nodes.csv nhưng không có cạnh R. Ví dụ diagnostic riêng `p_in=0.05, p_out=0` giữ đủ 24 active users mỗi tháng; chỉ endpoint có membership, số còn lại ghi rõ trong metadata. Đây là kiểm tra adapter với cấu hình riêng, không thêm vào cohort development mặc định và không đánh giá AMI trên tập giao tùy ý.

## Kiểm thử tích hợp — T05

Bốn test T05 chạy detector thật, thêm kiểm tra hành vi đầu cuối vào các test lỗi của T04:

- Hai clique rời nhau, mỗi clique 12 người, config riêng p_in=1/p_out=0. Kiểm tra chính xác 132 cạnh/tháng và partition gồm hai tập user đã khai báo độc lập, qua đủ hai tháng × ba seed. So sánh tập thành viên, không phụ thuộc tên `c0`/`c1`; không đọc CSV truth làm đáp án của detector.
- Hai tháng R rỗng được quan sát hợp lệ có đủ mapping; nếu một thư mục tháng bị thiếu, cả hai API phải từ chối thay vì coi là tháng rỗng.
- Stable và grow có graph tháng đầu giống byte nhưng tháng sau khác nhau: graph reference của toàn cohort phải khác, mỗi seed vẫn giữ reference nhất quán qua tháng trong dataset riêng.
- Hai process mới có `PYTHONHASHSEED=0/137`, input chuyển vị trí và thêm ba CSV truth giả không hợp lệ: membership/reference phải giữ nguyên. Thử chạy lại vào gói complete để xác minh không ghi đè bất kỳ file nào.

Các cấu hình 1/0 và 0/0 là diagnostic riêng để kiểm tra đáp án biết trước, không thay công thức 0.50/0.02 của cohort development. Không có AMI hoặc tracker trong gate này.

## Chạy đủ development — T06

[Lệnh chạy](../../../../scripts/run_development_detection.py) dùng lại gói graph/truth đã xuất ở PHUC-002, không sinh lại graph hoặc đọc CSV truth để partition. [TOML riêng](../../../../configs/detection_development.toml) có seed 0 với vai trò canonical detector; lịch generator/detector đầy đủ đọc từ JSON benchmark.

```powershell
& .\.venv\Scripts\python.exe scripts/run_development_detection.py --source-run artifacts/detection-tracking/phuc-002-t06-001 --run-id phuc-003-development-demo
```

Chọn run ID mới mỗi lần. Nếu source chưa có ở máy clone repo, chạy [PHUC-002 full development](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06) rồi thay `--source-run`. Có thể truyền `--config` và `--benchmark-config`; runner yêu cầu namespace synthetic/detection-tracking, TOML seed trùng canonical 0 và lịch detector `[0,1,2]`/gamma 1. Gói nguồn phải complete và có đúng toàn bộ danh sách development trong JSON; thiếu/thừa dataset hoặc hash graph/config/metadata không khớp thì từ chối trước output.

Config mặc định cho **6 case × 3 generator seed = 18 dataset**, **36 snapshot**, **108 membership CSV**. Ba detector seed là ba lần chạy trên cùng graph, không phải ba dataset độc lập. CLI không chọn evaluation hoặc seed tốt nhất và không sửa cấu hình theo kết quả.

Output mới:

```text
artifacts/detection-tracking/<run-id>/
  manifest.json
  benchmark-config.json
  datasets/<dataset-id>/
    memberships/<month>/membership-seed0.csv
    memberships/<month>/membership-seed1.csv
    memberships/<month>/membership-seed2.csv
    detection.json
    detector-config.json
    metadata.json
```

Manifest có scope `development-detection`, lịch/expected counts, config/source/code/output hashes, Git revision và trạng thái working tree khi chạy, Python/package versions và timing; dependency versions ở metadata/diagnostics từng dataset. `complete` chỉ nghĩa bước detection hoàn thành, `completed_stages=["detection"]`. Nếu lỗi, giữ gói đã xong/output dở dang, ghi `failed`, dataset đang lỗi và exception; không resume/ghi đè run cũ. CLI thành công exit 0; lỗi input/config/I/O exit 2. Lỗi backend bất ngờ vẫn ghi failed rồi truyền lỗi ra, không tạo kết quả thay thế. Full pipeline `reddit_sna run` và PHUC-005 chưa được báo hoàn tất.

Để dùng đoạn đọc/hash/chọn canonical ở trên cho một dataset trong batch, đặt `root = Path("artifacts/detection-tracking/<run-id>/datasets/<dataset-id>")`. Metadata từng dataset giữ nguyên schema của API một dataset.

Lượt thực T06: `phuc-003-t06-001/` và `phuc-003-t06-002/`, cả 108 membership giống byte giữa hai run; 36 reader stdlib kiểm tra 216 CSV. ARI giữa seed trung bình 0.941167, nhỏ nhất 0.502139; 7/36 snapshot có partition khác nhau giữa seed. Không đổi canonical hoặc loại case/seed vì kết quả khác nhau. Xem [bằng chứng](../evidence/PHUC-003-T06-development.md), [detection 108 dòng](../evidence/PHUC-003-T06-development-detection.csv), [seed ARI 108 dòng](../evidence/PHUC-003-T06-seed-repeatability.csv) và [timing tháng](../evidence/PHUC-003-T06-month-timings.csv). Đây là repeatability trong 36 snapshot của 18 dataset, không phải AMI hoặc 108 dataset độc lập.

## Kiểm tra và phần tiếp theo

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_synthetic_detection -v
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_development_detection -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

T05 đã chạy **24/24 test adapter** và **234/234 test toàn repo**, không skip/failure/error. Tests tự sinh fixture trong thư mục tạm, không cần artifact local hoặc dữ liệu Reddit để chạy. Cần cài `[graph]`; nếu test adapter bị skip vì thiếu dependency thì chưa đạt gate T05. Không đổi source runtime, thuật toán hoặc dependencies trong task này.

T06 thêm **4 test runner**: đủ lịch development/scope detection-only, CLI không ghi đè và từ chối source thiếu dataset, failed manifest giữ output đã xong/dở dang, config/overlap/source hash lỗi bị chặn trước output. Cả 4 pass; chạy lại full repo đạt **238/238 pass**, không skip/failure/error. Thuật toán/adapter per-dataset và dependencies không đổi ở T06; chỉ thêm batch command/config cùng tests.

[Bằng chứng T05](../evidence/PHUC-003-T05-integration.md) và [CSV gate AC01–AC05](../evidence/PHUC-003-T05-acceptance-gates.csv) nối từng điều kiện chấp nhận với tên test đã pass. Bốn gói kiểm chứng có 24 membership được reader stdlib kiểm tra và so partition với các tập người khai báo độc lập; CSV/ZIP đã lưu. Đây là nghiệm thu integration FR01–FR04; không thay lượt development thật FR05.

Các lượt lịch sử giữ nguyên: [T04](../evidence/PHUC-003-T04-adapter-errors.md) có 73 test liên quan/20 fault checks; [T03](../evidence/PHUC-003-T03-detection-package.md) có 66 test/relocated copy; [T02](../evidence/PHUC-003-T02-detector-schedule.md) có 61 test/ba seed; [T01](../evidence/PHUC-003-T01-leiden-adapter.md) có 57 test/một seed.

Tiếp theo **PHUC-004-T01** xác minh dataset/reference/tháng/user và căn nhãn theo cùng user ID trước khi đánh giá AMI/coverage. Chưa có điểm AMI trong các bảng T06 và không cần chờ tracker của Đăng để làm evaluator.
