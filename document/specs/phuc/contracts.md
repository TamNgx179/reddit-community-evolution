# Contract dataset và bàn giao Phúc–Đăng v1

**Thiết kế v1:** 16/10/2026. Cụ thể hóa schema trong [phân công cặp](../../PHAN-CONG-PHUC-DANG-TUAN-1.md). PHUC-001 có CSV/truth/export stable/grow và consumer độc lập. PHUC-002-T01 có sampler graph; T02 bổ sung membership/events/links trong bộ nhớ cho đủ sáu tình huống. Export graph/sáu case đầy đủ và kết quả detection/tracking vẫn thuộc các bước sau. Specs 001–006 dùng chung contract này, không tạo biến thể riêng cho mỗi spec.

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
