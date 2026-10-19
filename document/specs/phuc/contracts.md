# Contract dataset và bàn giao Phúc–Đăng v1

**Thiết kế v1:** 16/10/2026. Cụ thể hóa schema trong [phân công cặp](../../PHAN-CONG-PHUC-DANG-TUAN-1.md). PHUC-001 có CSV/truth/export stable/grow và consumer độc lập. PHUC-002 đã có sampler/truth sáu case, config, gói graph/truth và full development 18 dataset đọc lại độc lập. PHUC-003 đã DONE: adapter/metadata/guards/integration, full development 0/1/2 canonical 0; hai run có 108 membership tái lập. AMI/tracking và full orchestration/freeze còn riêng. Specs 001–006 dùng chung contract này, không tạo biến thể riêng cho mỗi spec.

## 1. Định danh và phạm vi

- `dataset_id`: case + split + difficulty + generator seed, ví dụ `dev-grow-easy-g11`.
- Mỗi dataset có các tháng liên tiếp `2020-01`, `2020-02`; đây là mốc giả lập.
- User nhất quán qua tháng trong dataset; không tự ghép user/reference của hai dataset khác nhau.
- Community ID cục bộ theo tháng; truth/detector có reference khác nhau. Metadata ánh xạ dataset, identity scope, truth reference và reference của từng seed detector.
- Trạng thái tháng quan sát phải có trong metadata. Tháng trống được quan sát khác với thiếu tháng kế tiếp.
- `schema_version=1` cho contract benchmark này; không ép bằng version diagnostics/reference của module khác.

## 2. CSV và khóa

| File | Header theo đúng thứ tự | Khóa/phạm vi |
|---|---|---|
| `snapshots/<month>/R.csv` | `month,source_user_id,target_user_id,weight` | Cặp vô hướng duy nhất trong tháng; không self-loop; weight hữu hạn > 0 |
| `snapshots/<month>/nodes.csv` | `month,user_id` | Mỗi user hoạt động một hàng, có cả isolate |
| `truth/membership.csv` và membership detector | `reference_id,month,community_id,user_id` | Mỗi reference/month/user đúng một nhóm |
| `truth/events.csv` hoặc events tracker | `reference_id,source_month,source_community_id,target_month,event` | Một nhãn cho mỗi nguồn có successor được quan sát |
| `truth/links.csv` hoặc links tracker | `reference_id,source_month,source_community_id,target_month,target_community_id` | Một cặp nguồn–đích duy nhất; split có nhiều đích |

File UTF-8, CSV có header; JSON lưu UTF-8. Sort user/cạnh/tháng cố định. R chỉ ghi một trong hai chiều của mỗi cặp. Chỉ tên file `R.csv` được dùng lại từ detector; graph giả lập không trở thành dữ liệu Reddit thật vì tên đó.

Truth phải phủ toàn node hoạt động. Detector hiện gán endpoint của R, không gán isolate. Evaluator phải xác minh tập prediction đúng endpoint, không chỉ lấy giao rồi âm thầm bỏ user sai.

### API CSV node/membership hiện có

Module: [benchmarks/io.py](../../../src/reddit_sna/benchmarks/io.py).

| Hàm | Đầu vào chính | Kết quả |
|---|---|---|
| `write_nodes(path, month, user_ids)` | Một tháng và các user hoạt động duy nhất | Tạo CSV mới, user được sort; không tự tạo thư mục cha |
| `read_nodes(path, expected_month=...)` | CSV và tháng mong đợi tường minh | Tuple user ID đã kiểm tra/sort |
| `validate_memberships(rows, expected_reference=..., expected_users_by_month=...)` | Record `Membership`, một reference và map tháng -> user mong đợi | Tuple membership canonical, hoặc lỗi dữ liệu |
| `write_memberships(path, rows, expected_reference=..., expected_users_by_month=...)` | Record và kỳ vọng như validator | Kiểm tra trước khi mở file mới, ghi đúng bốn cột |
| `read_memberships(path, expected_reference=..., expected_users_by_month=...)` | CSV và kỳ vọng độc lập từ caller | Membership đọc lại được kiểm tra đầy đủ |

- `expected_users_by_month` phải khai báo ít nhất một tháng quan sát, các tháng liên tiếp. Mỗi danh sách user duy nhất, không rỗng ID; không truyền một chuỗi đơn làm danh sách.
- Tập user membership phải bằng đúng tập mong đợi ở từng tháng. Dùng toàn bộ active users cho truth; nếu kiểm tra detector thì caller phải cung cấp endpoint users. Adapter không suy ra tập kỳ vọng từ chính membership đang kiểm tra.
- Tháng quan sát rỗng được khai báo bằng danh sách user rỗng; CSV header-only hợp lệ trong trường hợp đó. Không tự suy ra tháng không được quan sát hay nhãn dissolve.
- Header phải đúng tên và thứ tự; UTF-8 không BOM, parser strict; từ chối dòng sai số cột, dòng trống và quoting hỏng. ID Unicode/dấu phẩy/dấu nháy hợp lệ được giữ bằng CSV quoting, không tự trim/đổi tên.
- Writer dùng UTF-8 và newline LF cố định, sort membership theo tháng/community/user, mở file exclusive `x`. Input lỗi về keys/tháng/reference/user bị từ chối trước khi mở file; file đã tồn tại không bị ghi đè.
- Caller chọn thư mục artifact hợp lệ và tạo parent theo run policy. Các hàm này chưa tạo manifest, events/links hoặc gói bàn giao hoàn chỉnh.

### API truth events/links hiện có

Module: [benchmarks/scenarios.py](../../../src/reddit_sna/benchmarks/scenarios.py).

`build_transitions(scenario, reference_id, start_month="2020-01", observed_months=None)` trả về `PlantedTransitions` với hai tuple `.events` và `.links`. `start_month` và `observed_months` là tham số keyword-only; hiện hỗ trợ đủ `stable/grow/shrink/merge/split/dissolve`, cùng phạm vi với `build_memberships`. Hằng `SCENARIOS` công bố thứ tự sáu case này.

- Mỗi `TruthEvent` có `source: SampleKey`, `target_month` và `event: Event`. Trong `source`, `reference_id`, `feature_month`, `community_id` lần lượt ánh xạ sang ba cột CSV `reference_id,source_month,source_community_id`.
- Mỗi link dùng record `TrackingLink` có `.source` và `.target` là `SampleKey`, cùng reference và nối hai tháng liên tiếp. Truth chỉ tạo link có đích thật: split có hai link từ A; dissolve không tạo link cho A, không tạo record đích rỗng.
- Hai tháng được coi là quan sát đầy đủ khi `observed_months=None`. Nếu truyền tường minh, phải là iterable không rỗng, không trùng, chỉ chứa các tháng thuộc fixture hai tháng; thứ tự truyền không ảnh hưởng kết quả.
- Khi chỉ quan sát một trong hai tháng, cả events và links rỗng. Thiếu successor không phải dissolve; tháng cuối không trở thành nguồn. Tháng ngoài fixture bị báo lỗi, không tự tạo thêm dữ liệu.
- Khi có đủ hai tháng, mỗi nguồn có đúng một event theo thiết kế ở bảng sáu case bên dưới; mọi nguồn gồm K được gán nhãn. Merge gán A và B mỗi nguồn một `merge`; split gán A một `split` với hai links; dissolve gán A một `dissolve` với không link, K vẫn stable. Records được sort theo source/target. Không tính overlap/Jaccard, không gọi detector/tracker và không phân loại từ membership để sinh truth.
- API `build_transitions` chỉ sinh records trong bộ nhớ; T06 dùng exporter bên dưới để ghi CSV và metadata. Xem [bằng chứng T04](evidence/PHUC-001-T04-transitions.md).

### Export fixture truth và consumer độc lập

- `export_truth_fixture(destination, scenario=..., dataset_id=..., generator_seed=..., start_month="2020-01")` trong [io.py](../../../src/reddit_sna/benchmarks/io.py) tạo một thư mục dataset mới, trả metadata. Thư mục cha phải tồn tại; dataset/run ID dùng quy tắc portable hiện có; seed là int trong `[0, 2**32)`, không nhận bool.
- Exporter/CLI/consumer PHUC-001 hiện vẫn chỉ hỗ trợ stable/grow. Bốn case mới chỉ có API truth trong bộ nhớ; exporter từ chối trước khi tạo output để tránh ghi metadata stable/grow cho case khác. T04 sẽ mở rộng gói graph/truth/metadata đủ sáu case.
- Export ghi hai node CSV và ba bảng truth; đọc lại CSV rồi mới ghi `metadata.json` với config/version/seed, tháng quan sát, reference/identity scope, counts và SHA-256 năm CSV. `seed_used_for_truth=false` thể hiện truth cố định theo thiết kế.
- `export_truth_fixtures(config, start_month="2020-01")` trong [fixtures.py](../../../src/reddit_sna/benchmarks/fixtures.py) dùng `RunConfig`/quy tắc output an toàn hiện có, tạo hai dataset stable/grow trong run mới. [Config truth](../../../configs/truth_fixtures.toml) dùng seed 11; đây là cấu hình cho bước fixture, chưa thay cấu hình benchmark sáu case.
- Manifest có `scope="truth-fixtures"`, trạng thái started/failed/complete và `completed_stages=["truth"]` khi thành công. Hash trong manifest phủ cả metadata. Không tự coi gói này là full detection/tracking đã hoàn thành.
- `python -I scripts/read_truth_fixture.py <dataset-directory>` đọc bằng stdlib, kiểm tra hash/schema/coverage, tập thành viên và nhãn/link stable/grow; không import project. Xem [hướng dẫn chạy/nhận gói](001-truth-fixtures/README.md) và [bằng chứng T06](evidence/PHUC-001-T06-export.md).

## 3. Sáu case và nhóm nền

Mỗi case có nhóm nền K gồm 12 user riêng, ổn định qua hai tháng và được chấm như mọi nguồn khác.

| Case | Thành viên nhóm chính t -> t+1 | Truth nguồn chính |
|---|---|---|
| stable | 12 -> đúng 12 người cũ | stable |
| grow | 12 -> 18 gồm 12 cũ + 6 mới | grow |
| shrink | 18 -> 12 người cũ | shrink |
| merge | A12 + B12 -> C24 | A và B mỗi nguồn một merge |
| split | A24 -> B12 + C12, chia đôi không chồng | A một split, hai liên kết |
| dissolve | A12 -> không còn trong node hoạt động, K vẫn tiếp tục | A dissolve, không liên kết đích |

Đích chính được đặt tên khác nguồn để kiểm tra không tracking theo tên. Truth lấy từ kịch bản, không từ Jaccard/Leiden. Nhóm mới xuất hiện ghi diagnostics riêng; tháng cuối thiếu successor không gán dissolve.

## 4. Mặc định chạy

- Graph vô hướng đơn giản, mỗi cạnh weight 1.0; `p_in=0.50`, `p_out=0.02`.
- Generator development `11,12,13`; evaluation `101,102,103`; seed 11 cho luồng nhỏ.
- Leiden gamma 1, detector seeds `0,1,2`, canonical 0; protocol `synthetic-planted-undirected-v1`.
- Jaccard 0.30, growth ±10%, split ưu tiên trước merge và mapping theo [quy tắc cặp](../../PHAN-CONG-PHUC-DANG-TUAN-1.md). Chưa thay bằng GED.
- Không thêm cạnh/sinh lại seed sau khi thấy điểm xấu. Case khó là phần bổ sung có lịch/version riêng.

### Sampler graph hiện có — PHUC-002-T01

`sample_snapshots(memberships, expected_reference=..., expected_users_by_month=..., generator_seed=11, p_in=0.50, p_out=0.02)` trong [dynamic.py](../../../src/reddit_sna/benchmarks/dynamic.py) trả tuple `SampledSnapshot(month, nodes, edges)`; các tham số sau membership là keyword-only. Membership được kiểm tra bằng validator PHUC-001 với user lists độc lập do caller cung cấp.

- Giữ mọi active node, gồm isolate và tháng quan sát rỗng. Mỗi cặp user chỉ xét một lần; cạnh có source < target, weight 1.0. Stable giữ thành viên nhưng lấy mẫu cạnh mới theo tháng.
- Sampler version 1, RNG protocol `python-random-sequential-months-sorted-pairs-v1`: local `random.Random(seed)`, tháng/user/pair được sort, một draw mỗi cặp kể cả p=0/1. Không gọi tracker/detector hoặc sửa global RNG.
- Seed int `[0,2**32)`; p_in/p_out là int/float hữu hạn `[0,1]`, không nhận bool. Trước khi lấy mẫu, chặn scope/month/user sai, thiếu user hoặc membership trùng.
- API này chưa ghi file hay tạo gói graph hoàn chỉnh. [Hướng dẫn sampler](002-dynamic-benchmark/README.md) và [bằng chứng T01](evidence/PHUC-002-T01-stable-graphs.md) phân biệt graph CSV kiểm chứng với adapter export production của T04.

### Cấu hình benchmark hiện có — PHUC-002-T03

[benchmark_week1.json](../../../configs/benchmark_week1.json) lưu schema v1, graph protocol, hai tháng, sáu case easy, probabilities/weight, sampler/RNG version, generator seeds theo split, detector gamma/seeds/canonical và ordering. [benchmarks/config.py](../../../src/reddit_sna/benchmarks/config.py) đọc JSON riêng; TOML `RunConfig` hiện có không đổi.

- `load_benchmark_config(path)` đọc UTF-8, từ chối JSON key trùng/số không chuẩn và kiểm tra schema/giá trị. `validate_benchmark_config(config)` kiểm tra object không sửa input. Chỉ hỗ trợ đúng protocol/ordering đã triển khai; không âm thầm bỏ khóa lạ hoặc giá trị chưa hỗ trợ.
- Development generator seeds `11,12,13`, evaluation `101,102,103`; hai tập không được trùng. Mỗi danh sách seed không rỗng, duy nhất, đúng kiểu int `[0,2**32)`, không nhận bool.
- Detector seeds `0,1,2`, gamma 1.0, canonical 0. Canonical phải là seed đầu tiên; seed detector là các lần chạy lại trên cùng dataset, không phải dataset độc lập.
- `dataset_schedule(config, split)` tạo tuple record dataset theo thứ tự case rồi seed cấu hình, với ID `dev/eval-<case>-easy-g<seed>` và fields split/scenario/difficulty/generator_seed. Helper chỉ lập lịch, không sinh graph hay ghi output; từ chối split không hợp lệ.
- Lịch mặc định có 36 dataset, 72 snapshot, 216 đơn vị snapshot×detector-seed **dự kiến**. CLI `python -m reddit_sna.benchmarks.config configs/benchmark_week1.json` chỉ xác minh/in lịch. [Bằng chứng T03](evidence/PHUC-002-T03-benchmark-config.md) phân biệt lịch với mẫu stable development đã chạy; evaluation/freeze thuộc PHUC-005.

### Binding protocol và policy — PHUC-005-T01

[benchmark_week1_protocol.json](../../../configs/benchmark_week1_protocol.json) schema 1, ID `week1-detection-evaluation-v1`, liên kết hash của graph recipe ở trên với toàn bộ AMI/summary/split policy và expected counts. Graph recipe schema 1 giữ nguyên byte/hash để các artifact cũ tiếp tục đọc được. Loader `load_benchmark_protocol(path)` trong [benchmarks/protocol.py](../../../src/reddit_sna/benchmarks/protocol.py) trả recipe/protocol snapshots, paths và hai hashes; kiểm tra strict JSON, sibling path, hash recipe, policy khớp runtime, detector 0/1/2-gamma 1-canonical 0, tách seed/dataset IDs và đơn vị dự kiến.

`python -m reddit_sna.benchmarks.protocol configs/benchmark_week1_protocol.json` chỉ lập kế hoạch, trả `planned_counts`, `evaluation_executed=false`, `freeze_record_created=false`; lỗi exit 2. Không gọi generator/detector/metric hoặc tạo run. T01 có 68/68 test liên quan pass, kiểm tra checkout Windows `core.autocrlf=true` giữ hash; [hướng dẫn](005-reproducible-runs/README.md), [bằng chứng](evidence/PHUC-005-T01-protocol.md). Các gate orchestration/manifest/freeze/evaluation còn ở T02–T06; policy khai báo trong T01 chưa tự chặn các API sinh dữ liệu hiện có.

### API development từ protocol đến report — PHUC-005-T02

`run_synthetic_benchmark(RunConfig, protocol=Path, dataset_ids=None)` trong [pipelines/detection_tracking.py](../../../src/reddit_sna/pipelines/detection_tracking.py) tạo run mới, ghép graph/truth → Leiden → evaluator và trả đường dẫn. Config dùng synthetic/detection-tracking, input.path bỏ trống, seed 0 canonical. None chọn đủ 18 development datasets; subset phải nonempty/unique và giữ protocol order. Evaluation IDs bị chặn trước output. CLI riêng `python -m reddit_sna.pipelines.detection_tracking --run-id ...` nhận `--config`, `--protocol`, `--dataset-id` lặp lại.

Run lưu config snapshots, `inputs/source/<id>/`, `inputs/detected/<id>/`, `evaluation/` và manifest stage/status/counts. Complete có scope `development-detection-evaluation`, tracking `not_implemented`, freeze false; stage lỗi giữ output và failed manifest, run cũ bị từ chối. `evaluation/` là bước chấm development; shared full-pipeline `run` vẫn chưa triển khai tracking. [T02](evidence/PHUC-005-T02-api.md): 305/305 test repo pass, hai demo mới mỗi run 2 dataset/12 metrics/9 summary, 29 CSV/policy files tái lập và hai consumer độc lập pass.

### Run provenance và lifecycle — PHUC-005-T03

API trên xuất **root manifest schema 2** qua `RunRecorder` trong `artifacts.py`; graph/detection/report con giữ schema cũ. Manifest ghi `config_inputs` (source/archive/hash), `resolved_config` (JSON gồm override thật), `source` (package được import, archived Python files/pyproject, hashes, Git revision/branch/working tree), environment versions và output `files` (SHA-256/bytes). Archive paths tương đối với run; path tuyệt đối chỉ ghi xuất xứ. Inventory phủ cả metadata con, không tự hash root `manifest.json` hay `manifest.pending.json`.

`stages` có configuration/generation/detection/evaluation; `dataset_records` có generation/detection/evaluation từng dataset; `progress_counts` ghi số đã xong. Root complete chỉ công bố sau stages/counts/source/inventory verification. Output đã niêm phong bị đổi hoặc source thay đổi trong run làm failed và giữ hash expected/actual. Ghi manifest qua pending/replace; lỗi giữ output và lỗi gốc, cố ghi failed manifest, sau đó `failure.json` đầy đủ nếu publication lỗi. Reader phải ưu tiên failure marker; started/pending/failed không đủ điều kiện tiêu thụ như kết quả hoàn tất. Hard kill/mất khả năng ghi có thể chỉ giữ checkpoint started.

Timing có scope riêng cho preflight, run, stage wrappers và từng exporter dataset; evaluator chạy batch nên duration từng dataset là null. Diagnostics Leiden tháng/report timing giữ scope cũ, không coi là toàn stage detection. Peak memory null/not measured. [Schema, cách đọc timing và xử lý lỗi](005-reproducible-runs/README.md#hồ-sơ-của-mỗi-lượt-chạy--t03), [bằng chứng T03](evidence/PHUC-005-T03-provenance.md). Snapshots config/source là provenance, chưa là freeze evaluation T05.

T04 nghiệm thu contract bằng 23/23 test liên quan (thêm 5 integration), runtime/config không đổi; full suite 314/314 là baseline T03, không phải lượt mới T04. Hai demo stable/dissolve giữ 12 metrics/run (9 valid/3 null truth_constant), 29 CSV/policy giống byte và 12 partitions khớp dưới đổi tên nhóm/thứ tự dòng. Complete/failed/started đều không overwrite; concurrent same-ID chỉ một CLI process thành công. Child report complete không thay thế root status: counts mismatch vẫn root failed/CLI exit 2. Artifact consumer T04 chặn failure/pending marker và byte thay đổi; đây chưa là public handoff consumer PHUC-006. [Bằng chứng và AC matrix T04](evidence/PHUC-005-T04-acceptance.md): AC01–03 pass, AC04/05 còn formal freeze/evaluation T05/T06.

### Bản khóa sau full development — PHUC-005-T05

`create_benchmark_freeze(RunConfig, development_run=Path, protocol=Path) -> Path` trong `benchmarks/freeze.py` tạo run riêng scope `benchmark-protocol-freeze`, root schema 1/type `synthetic-benchmark-freeze`. Chỉ chấp nhận full development complete/verified đúng 18 dataset/36 snapshot/108 units, config/source/runtime khớp; không sửa completed development manifest. Lưu `config/`, `provenance/`, `evaluation/` của development và `development/manifest.json`; freeze manifest hash toàn bộ các file này, ghi source/environment, `frozen_at`, `changes_from_development`, lịch/expected counts hai tập và kết quả audit metadata holdout trong namespace. Có heldout graph/detection metadata thì từ chối tạo pre-evaluation freeze. Lỗi giữ failed/partial output, không overwrite.

`load_benchmark_freeze(directory) -> BenchmarkFreeze` đọc bản lưu, kiểm tra file set/hashes, development record/counts, protocol/lịch, chronology và source/Python/package versions hiện tại; không dùng absolute producer path để tìm input và không chạy dữ liệu. CLI `python -m reddit_sna.benchmarks.freeze create ...` / `verify <directory>` lỗi exit 2. Complete freeze có `freeze_record_created=true`, `evaluation_executed=false`; development run vẫn có cờ freeze false. [Lệnh/schema/phạm vi khóa](005-reproducible-runs/README.md#chạy-đủ-development-và-tạo-bản-khóa--t05).

Package Python source/pyproject bytes cùng recipe/policies/seeds được khóa; T06 driver ngoài package được bổ sung và lưu hash riêng, gọi thuật toán đã khóa. Docs/driver commit mới được phép làm HEAD tiến mà không đổi frozen package hashes. Bản khóa dùng hashes và version checks, không phải ACL/file readonly; mọi thay đổi thuật toán/policy sau freeze cần record công khai thay vì silently rebind.

### Thực thi lịch giữ lại — PHUC-005-T06

`run_frozen_evaluation(config, freeze=Path) -> Path` tại `scripts/run_frozen_evaluation.py` chỉ orchestration ngoài frozen package, không đổi algorithm/policy. Gate freeze/source/versions, canonical 0, frozen TOML, output không overlap freeze/development và chronology trước output/heldout access. Chạy đầy đủ `freeze.schedules.evaluation` theo thứ tự khóa; không nhận subset hay override detector/generator params. CLI `python scripts/run_frozen_evaluation.py --config ... --freeze ... --run-id ...`, lỗi exit 2.

Root schema 2/type `synthetic-frozen-evaluation-run`, scope `heldout-detection-evaluation`, split evaluation; `freeze_reference` pin manifest SHA/thời điểm/revision T05, `driver` archive/hash riêng. Run chứa bản sao `freeze/` nguyên byte, configs, current package source/environment, driver source, source/detected datasets và report. `evaluation_executed` ghi việc bắt đầu truy cập heldout; `freeze_record_created=false`, tracking not_implemented; completed stages/root status mới xác nhận completion. Giữ scope timing/progress/error/partial outputs từ `RunRecorder`. Cuối run kiểm tra actual counts và nguồn freeze/TOML/driver, không overwrite input/run cũ. Tests driver trước production dùng stubs không có heldout labels/scores; kết quả thật được ghi riêng tại [evidence T06](evidence/PHUC-005-T06-heldout.md).

T06 đã nghiệm thu từ clean driver `09623f1`: full evaluation 18/36/108, 99 valid/9 null, 0 dataset lỗi; canonical mean 0.933116751, coverage 1.0. Kết hợp immutable development T05 đủ 36/72/216, 198 valid/18 null; 42 frozen package files/versions/config/policies giữ nguyên. 25/25 targeted tests và 4 audit invocations từ 3 independent consumers đạt; full suite không chạy lại T06. [AC01–AC05 PASS](evidence/PHUC-005-T06-acceptance-matrix.csv), [ledger](evidence/PHUC-005-T06-dataset-ledger.csv), [split/seed comparison](evidence/PHUC-005-T06-split-comparison.csv). PHUC-005 DONE, handoff/notebook và tracker/demo cặp không tự được accepted theo kết quả này.

### Export graph/truth hiện có — PHUC-002-T04

- `export_graph_dataset(destination, benchmark=..., scenario=..., generator_seed=..., split="development")` trong [io.py](../../../src/reddit_sna/benchmarks/io.py) xuất một dataset theo lịch hợp lệ, parent phải tồn tại, destination mới. Gói có bảy CSV theo schema trên, `benchmark-config.json` và `metadata.json`.
- `validate_edges`/`write_edges`/`read_edges` nhận `expected_month`, `expected_users` tường minh, không suy ra active users từ cạnh. Endpoint phải source < target, cùng tháng, thuộc user list; chặn duplicate/self-loop/weight sai. Writer sort source/target, weight float, UTF-8/LF, exclusive. CSV rỗng vẫn có header.
- Metadata artifact type `synthetic-graph-truth`, schema 1, identity/reference/tháng, generator seed/config/protocol, Python/package versions, counts node/cạnh/nhóm/isolate và hash tám file dữ liệu/config. Metadata ghi cuối sau khi đọc lại CSV và config; `detector_references={}`, seed không dùng để sinh truth. Config JSON được serialize canonical, không giữ nguyên whitespace của input.
- CLI `python -m reddit_sna.benchmarks.graphs --run-id <new-id>` dùng `configs/graph_benchmark.toml` và `configs/benchmark_week1.json`; sinh sáu case tại **một** development seed trong TOML. Run helper dùng boundary `project_root/artifacts`, từ chối run đã tồn tại kể cả rỗng. Không tự chạy evaluation.
- T06 thêm `--all-development-seeds`, lấy đủ lịch JSON development (hiện 18 dataset/36 snapshot), không dùng evaluation hoặc nhân dataset theo detector seed. `manifest.selection` ghi mode và actual generator seeds; TOML seed vẫn phải thuộc development. `python -I scripts/read_graph_dataset.py <dataset-dir>` đọc stdlib độc lập đủ sáu case, kiểm tra hashes/schema/invariants/tập người và nhãn/link; không sinh lại cạnh, không sửa file. Thành công exit 0 JSON verified, lỗi exit 2. [Bằng chứng T06](evidence/PHUC-002-T06-development.md) và CSV tổng hợp trong Git ghi nghiệm thu generator, diagnostic và ZIP local.
- Manifest `scope="graph-truth"`, chỉ hoàn tất `generation/truth`, hash cả metadata. Khi lỗi giữ output dở dang và ghi failed, không retry vào run cũ. Đây chưa phải manifest/freeze đầy đủ PHUC-005. Artifact local không đi theo Git; [hướng dẫn](002-dynamic-benchmark/README.md) và [bằng chứng T04](evidence/PHUC-002-T04-graph-export.md) ghi cách tái tạo/kiểm chứng. Exporter/consumer PHUC-001 cũ giữ nguyên phạm vi stable/grow.

### Fixture diagnostic sampler — PHUC-002-T05

[tests/fixtures/dynamic_diagnostics.json](../../../tests/fixtures/dynamic_diagnostics.json) khai báo protocol riêng `tiny-sampler-diagnostics-v1`, seed 11, nhóm/người, tháng quan sát, probabilities và counts mong đợi. Bốn case zero-edges/small-groups/empty-singleton/singleton-empty chỉ kiểm tra sampler với nhóm nhỏ/isolate/tháng rỗng; không thuộc sáu case easy hoặc evaluation. K trong tiny có một người có chủ ý.

CSV node/edge/membership dùng schema chung, luôn giữ observed months và mọi active user, kể cả không có cạnh. Artifact local của T05 mang type `synthetic-sampler-diagnostic`, scope generator-only, difficulty diagnostic, config/seed/identity/counts và hashes; không có events/links, không tự suy ra dissolve và không đại diện cho gói benchmark đã nghiệm thu. Xem [bằng chứng](evidence/PHUC-002-T05-generator-tests.md) và [ví dụ lưu CSV](002-dynamic-benchmark/README.md#kiểm-tra-generator-và-lưu-mẫu-nhỏ--t05). Đây là version fixture riêng, không nới validator JSON benchmark easy v1.

### API detection, lịch seed và gói kết quả — PHUC-003-T01–T06

`detect_synthetic_dataset(source, output, benchmark_config=None)` trong [pipeline](../../../src/reddit_sna/pipelines/detection_tracking.py) nhận một dataset đã xuất, kiểm tra config/metadata/identity/tháng/hashes R/nodes, gọi detector hiện có với protocol synthetic. T01 là lượt lịch sử seed 0; từ T02 API chạy lịch 0/1/2 đọc từ JSON, gamma 1.0/canonical 0. Không đọc truth membership/events/links để partition; source chỉ cần phần graph và metadata/config tương ứng. Lượt T01/T02 dùng stable development, chưa chạy evaluation.

Truyền `benchmark_config=Path("configs/benchmark_week1.json")` để chọn runtime config; không truyền thì dùng bản archived trong source. Graph recipe phải khớp source, mục detector đọc từ runtime; adapter tuần 1 từ chối lịch khác `[0,1,2]`, gamma khác 1 hoặc canonical khác 0 trước output. Dict trả về ghi path/hash runtime và policy canonical là seed đầu, không chọn theo score. Mỗi seed có reference riêng, shared qua tháng; chặn run đảo thứ tự hoặc ref lẫn seed.

Membership phủ đúng endpoint R, UTF-8/LF canonical, output mới ngoài source. Isolate không được gán; R rỗng cho ba file header-only, chất lượng null và ARI rỗng. Dict có versions/input hashes/active/isolate counts; diagnostics schema 2, membership schema 1. ARI theo cặp (0,1)/(0,2)/(1,2) đo repeatability, không phải AMI truth. Gói/manifest prototype T01/T02 cũ giữ nguyên. Full pipeline chưa hoàn thành.

T03 thêm `export_synthetic_detection(source, output, *, benchmark_config=None) -> dict` trong cùng module, gọi API detection và trả metadata của gói mới. Gói gồm sáu `memberships/<month>/membership-seed*.csv`, `detection.json` (toàn bộ diagnostics), `detector-config.json` (runtime JSON đúng byte), `metadata.json` schema 1/type `synthetic-detection`, scope/completed stage chỉ `detection`. Output parent phải tồn tại, output phải mới kể cả không nhận thư mục rỗng. Chuẩn bị trong thư mục tạm; metadata được chuyển cuối, không sửa source hoặc ghi đè kết quả cũ. Nếu lỗi I/O ở bước publish, giữ phần output dở dang và dùng đường dẫn mới để chạy lại.

Metadata lưu dataset/identity/split/scenario/generator seed, observed months, truth reference, graph protocol/cohort fingerprint, detector seeds/gamma/canonical/versions và source hashes gồm metadata/config/R/nodes (sáu file, không đọc CSV truth). `detector_references` map string seed -> reference; `memberships` có một entry mỗi tháng/seed với path/hash, dataset/identity/reference/canonical, graph/nodes source paths, graph fingerprint, active/assigned/isolate/status; có entry ngay cả CSV rỗng. Đây là mapping nguồn file, chưa phải matching nhóm detector với nhóm truth.

`files` hash tám file khác, không tự hash metadata. Output paths tương đối với gói detection; graph/nodes và `source.files` tương đối với dataset nguồn. Path tuyệt đối source/runtime chỉ ghi provenance, không dùng để tìm CSV khi gói đã chuyển chỗ. Người nhận cần gói graph/truth tương ứng để kiểm tra endpoint/AMI; gói detection không chứa lại các file nguồn. Công thức generator/difficulty có trong bản config và source metadata được hash. Xem [README/cách đọc](003-leiden-detection/README.md), [T01](evidence/PHUC-003-T01-leiden-adapter.md), [T02](evidence/PHUC-003-T02-detector-schedule.md), [T03](evidence/PHUC-003-T03-detection-package.md).

T04 kiểm tra rõ cấu trúc metadata bắt buộc, hash entries và counts int không âm theo đúng tháng (không nhận bool), truth reference theo dataset. Đối chiếu diagnostics với graph/CSV thật: assigned/endpoints, số nhóm/sizes, status/quality hữu hạn khi có cạnh, null quality/connectivity và ARI rỗng khi không có cạnh. Seed ARI không rỗng có đủ ba cặp, hữu hạn và trong [-1,1] với tolerance 1e-12. Thiếu dependency báo cài `[graph]`; lỗi input/backend/source thay đổi không xuất output cuối; output có sẵn không bị ghi đè. Mixed-isolate/zero-edge fixtures với probabilities riêng chỉ là diagnostics, không thêm vào cohort hay thành kết quả AMI. Xem [bằng chứng T04](evidence/PHUC-003-T04-adapter-errors.md).

T05 nghiệm thu integration/AC01–05; T06 thêm [batch command](../../../scripts/run_development_detection.py) với [TOML canonical seed 0](../../../configs/detection_development.toml), nhận complete graph/truth source run và chạy **tất cả development dataset** theo JSON. Source manifest/dataset directories phải khớp đúng lịch; hash metadata/config/R/nodes được kiểm tra trước output, không đưa CSV truth vào detector. Run mới qua helper artifact an toàn, manifest scope `development-detection`, source/config/code/output hashes, Git revision/working tree và timing. Complete stage chỉ `["detection"]`; failed giữ các gói đã xong/output dở dang cùng dataset gây lỗi, không retry/overwrite run cũ.

Default có 18 dataset/36 snapshot/108 membership, mỗi dataset giữ layout/schema như API. Top run có `benchmark-config.json`, `manifest.json`, `datasets/<dataset-id>/...`; 164 file/run. Hai lượt T06 giữ 108 CSV giống byte; ARI seed thay đổi ở 7/36 snapshot được ghi nguyên kết quả, canonical vẫn 0. Timing CSV một dòng mỗi tháng/run cho cả ba seed, không nhân bản thành timing mỗi seed. [Bằng chứng T06](evidence/PHUC-003-T06-development.md) và CSV trong Git chốt FR05; chưa tính AMI hoặc thực hiện evaluation/freeze PHUC-005.

### Căn nhãn đánh giá hiện có — PHUC-004-T01

[evaluation/detection.py](../../../src/reddit_sna/evaluation/detection.py) có hai API chỉ đọc/chuẩn bị input:

- `align_memberships(truth, predictions, truth_reference=..., detector_reference=..., active_users_by_month=..., endpoint_users_by_month=...)`: xác minh truth bằng đúng tập active và prediction bằng đúng tập endpoint độc lập; chặn duplicate/user thiếu/lạ/sai tháng/reference rồi sort hai vector nhãn theo cùng `(month, user_id)`. Không ghép community theo tên hoặc theo vị trí CSV.
- `load_aligned_detection(source, detection, detector_seed=0)`: nhận hai **dataset directory** PHUC-002/003, kiểm tra identity/config/lịch/tháng/seed, relative paths/hashes và graph cohort/mapping trước khi đọc membership. Chỉ hỗ trợ lịch tuần 1 gamma 1, seed 0/1/2. Giữ hai reference riêng; đường dẫn tuyệt đối producer không dùng để tìm input sau relocation.
- `AlignedDetection.snapshots` chứa `AlignedSnapshot`: `active_user_ids` đi cùng `truth_labels_all`; `user_ids` endpoint đi cùng `truth_labels` và `predicted_labels`. Các tuple sort theo user ID; tháng endpoint rỗng vẫn hiện diện với vector rỗng. Không bỏ isolate khỏi tập active.

API trong bộ nhớ dựa vào scope/reference/user maps caller cung cấp; API file bổ sung xác minh dataset/metadata/hash. Hai API này chuẩn bị vector; hàm đếm T02 bên dưới dùng kết quả của chúng. Loader chỉ đối chiếu hash diagnostics, chưa đánh giá nội dung timing. [Hướng dẫn và ví dụ](004-detection-evaluation/README.md), [bằng chứng T01](evidence/PHUC-004-T01-alignment.md).

### Counts và coverage — PHUC-004-T02

`count_snapshot(snapshot: AlignedSnapshot) -> DetectionCounts` trong module evaluation trên trả `month`, `active_nodes`, `endpoint_nodes`, `assigned_nodes`, `isolated_nodes`, `coverage`, `coverage_status`, `true_communities_all_nodes`, `true_communities_scored_nodes`, `predicted_communities`. Kiểm tra vector lengths/ID/tập người và truth mapping trước khi đếm, kể cả record được tự dựng.

- Assigned phải bằng endpoint theo T01; isolate = active - endpoint. Coverage = assigned/active, giữ isolate trong mẫu số. Active > 0 nhưng endpoint = 0 cho coverage 0.0/status `defined`; active = 0 cho coverage None/status `no_active_users` (JSON null/CSV trống).
- Số nhóm truth trên toàn active và trên scored users được tính riêng; predicted groups chỉ trên endpoint. Tập rỗng cho group count 0; partition constant/singleton vẫn có counts hợp lệ, policy AMI riêng ở T03.
- Mỗi record là một snapshot của một dataset/seed; caller giữ context/reference ở `AlignedDetection`, không cộng seed/tháng thành số người độc lập. T02 chưa xuất summary/timing hoặc AMI; CSV kiểm chứng development và diagnostic có scope riêng. [Bằng chứng T02](evidence/PHUC-004-T02-counts.md).

### AMI và policy — PHUC-004-T03

`score_snapshot(snapshot: AlignedSnapshot) -> DetectionAMI` dùng validator/counts T02 rồi gọi `sklearn.metrics.adjusted_mutual_info_score` với `average_method="arithmetic"`. Kết quả có month/n_scored_users/ami/ami_status/ami_reason/ami_policy_id/ami_average_method; dataset/seed/reference vẫn do `AlignedDetection` giữ. Extra `[evaluation]` khai báo scikit-learn; dependency chỉ được import khi snapshot đủ điều kiện chấm.

- Policy immutable `AMI_POLICY`, ID `synthetic-ami-v1`: n = 0 → null/`empty_scored`; n = 1 → null/`insufficient_users`; một trong hai phía constant hoặc all-singletons → null/`degenerate_partition` với reason theo truth rồi prediction. Các trường hợp còn lại `ok`, giữ nguyên điểm âm. Đây là policy của đồ án; thư viện vẫn có thể tính điểm cho các trường hợp đồ án loại.
- User/key/length/reference lỗi vẫn bị từ chối qua T01/T02, không lấy giao hoặc điền metric mặc định. Thiếu sklearn báo cách cài `.[evaluation]`; lỗi dependency/backend khác và metric không hữu hạn được báo lỗi. Isolate không vào vector AMI, vẫn ở mẫu số coverage.
- Lưu `dict(AMI_POLICY)` và hash trước lượt chấm, ghi sklearn version và giữ hàng null/status/reason. Quality summary T04 chỉ tổng hợp `ok` nhưng phải báo n thiếu/reason/canonical riêng; T03 chưa triển khai exporter/summary/timing production. Xem [hướng dẫn](004-detection-evaluation/README.md), [policy JSON](evidence/PHUC-004-T03-ami-policy.json), [bằng chứng T03](evidence/PHUC-004-T03-ami.md).

### Export evaluation report — PHUC-004-T04

`export_detection_evaluation(pairs, output) -> dict` nhận iterable các `(source_dataset_dir, detection_dataset_dir)` có ID duy nhất, chạy loader/counts/AMI cho cả seed 0/1/2 và ghi report mới. CLI `python -m reddit_sna.evaluation.detection --pair SOURCE DETECTION [--pair ...] --output NEW_DIR`. Parent phải tồn tại; output không được có sẵn hoặc chồng lên input.

- Report có `detection_metrics.csv`, `detection_summary.csv`, `ami-policy.json`, `timing.json`, `metadata.json`. Metrics key `(dataset_id,month,detector_seed)` giữ context/reference/canonical/counts/coverage/AMI/status/reason/support/version. Input file hashes được kiểm tra/recheck, complete metadata publish cuối; lỗi I/O giữ partial/failure.json khi có thể, chưa báo complete.
- Summary group theo `(split,scenario,difficulty,gamma,detector_seed)` và thêm mức `all_scenarios` trong cùng split/difficulty/gamma/seed. Mỗi seed riêng; canonical 0, diagnostic 1/2. Đơn vị là dataset-month, AMI mean không trọng số theo user, dùng dòng `ok`; all_scenarios mean trên các dòng hợp lệ, không trên case means. Giữ n_datasets/n_rows/n_valid/n_missing, missing status/reason counts, coverage support; all-null mean để trống. User support là số quan sát qua dòng.
- Timing detection lấy một lần mỗi dataset-tháng cho cả ba seed từ diagnostics đã hash/kiểm tra context. Timing evaluation/compute/CSV mới đo với scope rõ, generation/peak memory null. Report metadata scope `detection-evaluation-only`, completed stage chỉ evaluation; full-run lifecycle/freeze vẫn thuộc PHUC-005.

[Hướng dẫn schema/cách đọc](004-detection-evaluation/README.md), [bằng chứng T04](evidence/PHUC-004-T04-export.md) và CSV/timing nhỏ trong Git ghi kết quả export thực tế. [T05](evidence/PHUC-004-T05-invariants.md) kiểm chứng AC01–05: full repo 286/286 test pass, gồm 48 test evaluator; chặn membership sai dù hash đúng và giữ report chưa hoàn tất khi lỗi công bố metadata cuối. [T06](evidence/PHUC-004-T06-stable-grow.md) nghiệm thu stable/grow development: hai report 6 dataset/36 metrics/9 summary tái lập, trace 918 lượt user, config/versions/hashes; 48/48 test pass và PHUC-004 DONE 6/6. Đây chưa phải orchestration/freeze/evaluation giữ lại của PHUC-005.

## 5. Metadata, manifest và metric tối thiểu

`metadata.json` của mỗi dataset: schema version, dataset ID, split, scenario, difficulty, generator config/seed, observed months, identity scope, truth reference, detector references khi đã có, relative paths và hashes file đã hoàn thành.

`manifest.json` của run: run ID, status, thời điểm, config hash/bản sao, source revision/hashes/dirty state, Python/dependency versions, lịch seed, cohort thực tế, stage đã xong/lỗi, output hashes và timing. Không ghi `complete` trước khi các đầu ra được kiểm tra. Các helper hiện có chỉ là khởi đầu, caller phải hoàn thiện manifest.

`detection_metrics.csv` dự kiến:

```text
dataset_id,split,scenario,difficulty,generator_seed,month,detector_seed,gamma,
active_nodes,endpoint_nodes,assigned_nodes,coverage,
true_communities_all_nodes,true_communities_scored_nodes,predicted_communities,
ami,ami_status
```

- AMI chỉ trên user có prediction và truth đã xác minh; coverage = assigned/active. Mẫu số 0 hoặc AMI không có ý nghĩa thì để thiếu kèm trạng thái, không điền 0/1 giả.
- Case không đủ user hoặc phân hoạch hằng: ghi trạng thái degenerate và không dùng làm bằng chứng khôi phục cộng đồng; quy ước cụ thể phải được test và lưu config trước evaluation.
- Timing lưu riêng trong JSON: generation/detection/evaluation wall seconds, phạm vi đo rõ. Diagnostics Leiden hiện đo tổng theo tháng qua nhiều seed; không nhân bản thành thời gian riêng từng seed.
- Peak memory chưa đo để null. Bảng summary ghi đơn vị tổng hợp, n hợp lệ/n thiếu, canonical seed riêng và diagnostics seed khác.

## 6. Gói giao và việc người nhận xác nhận

Một gói giao gồm run/dataset ID, manifest/metadata, graph+nodes, truth membership/events/links, membership detector, diagnostics, metrics và cách đọc/tái tạo. Có thể giao truth sớm trước khi đủ cả gói.

Phúc tự kiểm tra contract và hash, ghi evidence bàn giao. Việc Đăng đọc/nhận thành công phải có phản hồi thật; không suy ra từ validator pass. Handoff chưa có phản hồi không chặn việc Phúc tự nghiệm thu generator/detection/evaluation.

Nếu cần public report trong Git, chỉ xuất bảng tổng hợp nhỏ đã rà soát; artifact local và manifest không tự có trên máy thành viên khác. Hướng dẫn phải chỉ cách tái tạo hoặc nhận gói được chia sẻ thực tế.

### Consumer inventory tổng hợp — PHUC-006-T01

[reporting/synthetic_handoff.py](../../../src/reddit_sna/reporting/synthetic_handoff.py) là consumer standard library riêng cho **complete schema-2 synthetic development/evaluation runs PHUC-005**, không dùng schema của `reporting/handoff.py` cho mạng Reddit. `inspect_synthetic_handoff(run_directory, *, expected_manifest_sha256=None)` chỉ đọc và trả inventory; `export_synthetic_handoff(run_directory, output, *, expected_manifest_sha256=None)` ghi thư mục index mới, trả metadata. CLI standalone: `python -I -S <synthetic_handoff.py> RUN --expected-manifest-sha256 HASH --output NEW_DIR`; thành công exit 0, lỗi exit 2. Pin phải được đối chiếu từ nguồn giao; không suy ra tính xác thực chỉ từ hash tự khai báo.

Consumer kiểm tra inventory/hash/size, dataset identity/source linkage, truth keys/reference/coverage/events/links, cả ba detector seeds và assigned users đúng endpoint. Không gọi generator/detector/metric library. Output `inventory.json` schema 1 và `snapshot_inventory.csv` mapping từng dataset/month/seed có paths graph/nodes/truth/detector/reference/counts; `metadata.json` ghi cuối và hash hai file trên. Paths tương đối từ **source run**; index không chứa lại source bundle (`source_bundle_included=false`). Không overwrite/chồng output vào source; failed publication giữ partial, không có complete metadata đọc được. `partner_acceptance=not_verified` luôn tách khỏi passing consumer.

T01 đã consume hai source runs nguyên byte: 36 dataset/72 snapshot/216 membership CSV; relocated output giống byte cho cả hai split. 51/51 targeted tests đạt; 42 frozen source files giữ byte. Reporting module mới nằm ngoài runtime closure đã khóa: benchmark replay dùng driver `09623f1`/frozen package versions, consumer không gọi current-runtime freeze gate. AMI và frozen runtime không chứng nhận lại ở T01. [Hướng dẫn](006-handoff-demo/README.md), [bằng chứng](evidence/PHUC-006-T01-inventory.md), [reference](evidence/PHUC-006-T01-handoff-reference.json). Notebook/clean-kernel và receipt Đăng còn riêng.

### Gói gửi Đăng — PHUC-006-T02

[Hướng dẫn bàn giao](../../PHUC-DANG-WEEK1-HANDOFF.md) dùng layout thật của ZIP `artifacts/handoff/phuc-dang-week1-20261019-001.zip`: `runs/<split>/` giữ nguyên PHUC-005, `inventories/<split>/` giữ index T01, `consumer.py`, guide và `delivery-manifest.json` hash/size 820 file khác. ZIP 821 file/956.285 byte, [reference/checksum](evidence/PHUC-006-T02-delivery-reference.json). Paths trong index vẫn tính từ source run, không từ thư mục index. Gói đủ 36 dataset/72 snapshot/216 memberships; chưa có tracker/notebook, chưa gửi/upload hoặc ghi receipt người nhận.

T02 đã thử nguyên CLI/PowerShell/API trong guide trên bản giải nén mới, hai index giống byte với bản giao; ví dụ grow và 39 source events/split (support 21/3/3/6/3/3) đối chiếu từ CSV thật. Standalone PowerShell CLI dùng Python 3.14.4, package API dùng 3.12.6; không sinh graph/chạy detector/AMI hoặc full suite/clean install mới. Đăng viết/debug tracker trên development, tự khóa tracker/evaluator trước dùng evaluation; frozen detection không tự nghiệm thu tracker. [Bằng chứng T02](evidence/PHUC-006-T02-handoff-guide.md).
