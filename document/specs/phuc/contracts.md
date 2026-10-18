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

API trong bộ nhớ dựa vào scope/reference/user maps caller cung cấp; API file bổ sung xác minh dataset/metadata/hash. Hai API chưa tính AMI/coverage/số nhóm hoặc ghi metric. Loader chỉ đối chiếu hash diagnostics, chưa đánh giá nội dung timing. [Hướng dẫn và ví dụ](004-detection-evaluation/README.md), [bằng chứng T01](evidence/PHUC-004-T01-alignment.md); T02–T06 vẫn cần hoàn thiện spec.

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
