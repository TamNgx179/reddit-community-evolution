# Source architecture

## Quyết định cấu trúc

Một package `src/reddit_sna` chia theo chức năng. Đây là bố cục source đã tạo; thuật toán bên trong còn cần triển khai. Thư mục không gắn với tên người, độ khó hoặc phương pháp đề xuất/đối chứng. Detector mới nằm cạnh detector cũ và trả cùng kiểu membership; mô hình mới dùng cùng khóa mẫu và định dạng prediction.

Ba pipeline là nơi ghép các bước, không phải ba bản sao source. `pipelines/core.py`, `pipelines/detection_tracking.py`, `pipelines/prediction.py` hiện trả lỗi chưa triển khai. CLI chỉ import entrypoint được chọn khi gọi `run`; `check` chỉ kiểm tra cấu hình.

## Đối chiếu tiêu chí chấm và mức sẵn sàng nghiên cứu

Rubric người học cung cấp: A1 thi lý thuyết 50%, A2 đồ án nhóm 50%; mức điểm tối đa của đồ án đòi hỏi **tiềm năng paper**, cùng quá trình tham gia và các mốc proposal/giữa kỳ/cuối kỳ. Đây không phải rubric chấm chi tiết; không suy ra bảo đảm 9–10 từ một cấu trúc source.

Định hướng là **nghiên cứu có phân tích SNA**, với câu hỏi kiểm chứng giá trị bổ sung của ngữ cảnh thread và lịch sử thành viên so với cấu trúc reply. Tính mới chưa được xác nhận. Các nguồn phương pháp trong `experiments/literature_matrix.csv` chỉ là điểm xuất phát; còn phải tìm công trình gần nhất về temporal/multiplex community forecasting, so dữ liệu/nhiệm vụ/protocol và chỉ ra khoảng trống cụ thể trước khi gọi là đóng góp mới.

Source hiện có hạ tầng và khung trách nhiệm, chưa có kết quả nghiên cứu. Phân biệt ba tầng bằng chứng: **test phần mềm**, **kiểm chứng phương pháp trên ground truth**, **kết quả ngoài thời gian trên Reddit**. Không dùng số test hoặc số notebook để thay cho hai tầng sau.

## Hướng phụ thuộc

```text
CLI → config + pipeline được chọn
notebooks/<nhóm> → config + module chức năng hoặc pipeline đã triển khai
pipeline → data / graphs / benchmarks / detection / tracking / features / models / evaluation
pipeline → artifacts
domain modules → contracts
artifacts → config + contracts
```

Module thuật toán không import CLI/pipeline; pipeline không import pipeline khác. Không đọc file hoặc tính toán nặng khi import. `contracts.py` giữ records nhỏ và bất biến dữ liệu, không import thư viện graph/ML. Chưa cần factory, plugin registry, dependency injection, repository/service layer hoặc một file utils tổng hợp.

## Notebook và source dùng lại

`notebooks/core`, `notebooks/detection_tracking`, `notebooks/prediction` là không gian thử nghiệm và trình bày riêng cho ba cặp. Mỗi nhóm có `00_research_plan.ipynb` với câu hỏi, dữ liệu, protocol, đối chứng, kết quả/bằng chứng và phản biện. Đây là template chưa chạy; cell triển khai chủ động báo NotImplementedError để không bị nhầm là demo hoàn tất. Notebook có thể chứa prototype mới; khi logic ổn định hoặc cần dùng lại thì chuyển vào module chức năng. Source không import hoặc phụ thuộc vào thứ tự thực thi notebook.

Cả notebook và CLI dùng chung contracts/config và quy tắc output. Chọn kernel có package được cài trong cùng môi trường; notebook không chỉnh sys.path. Đầu notebook xác định path config rõ ràng vì cwd có thể khác vị trí notebook. Bàn giao từ kernel sạch theo thứ tự cell, ghi seed/dữ liệu nguồn, dừng khi lỗi. Template chưa được thực thi; chưa thêm công cụ chạy notebook tự động hoặc dependency notebook vào bộ khung.

Notebook chạy đủ input → xử lý → evaluation có thể là demo end-to-end của cặp ở tuần 1. CLI là đường chạy để tự động hóa/tích hợp về sau; không bắt buộc mọi thử nghiệm phải bắt đầu bằng CLI.

## Ranh giới và người sở hữu

| Nơi | Trách nhiệm | Người sở hữu |
|---|---|---|
| `data/` | Corpus adapters, chuẩn hóa, ID nhất quán và audit dữ liệu | Tâm |
| `graphs/` | Graph dị thể, cutoff, snapshot R/T, projection và coverage | Tâm |
| `detection/` | Leiden/Louvain; temporal/consensus | Phúc; Tâm cho phương pháp đề xuất |
| `tracking/` | Liên kết community, gán sự kiện | Đăng cho Jaccard; Thanh cho GED |
| `features/` | Cấu trúc, dị thể, lịch sử thành viên | Thanh |
| `models/` | Dự báo trên bảng mẫu | Trâm cho B1/B4; Phúc cho B2/B5; Thanh cho HeTCo |
| `evaluation/` | Split, chỉ số, leakage, độ bất định | Anh cho metrics/report; Đăng cho kiểm tra nâng cao |
| `benchmarks/` | Mạng chuẩn; bảng dự báo tổng hợp | Phúc; Trâm cho bảng dự báo |
| `pipelines/core.py` | Demo core riêng | Tâm–Thanh |
| `pipelines/detection_tracking.py` | Demo detection/tracking riêng | Phúc–Đăng |
| `pipelines/prediction.py` | Demo baseline/evaluation riêng | Trâm–Anh |
| `notebooks/core/` | Khám phá, prototype và trình bày core | Tâm–Thanh |
| `notebooks/detection_tracking/` | Thử benchmark/detector/tracker và phân tích lỗi | Phúc–Đăng |
| `notebooks/prediction/` | Thử baseline, evaluation và biểu đồ | Trâm–Anh |
| `config.py`, `contracts.py`, `artifacts.py`, CLI | Giao diện chung; thay đổi cần review các nơi sử dụng | Tâm điều phối |

Shared code không đồng nghĩa phải chờ shared output. Phúc–Đăng dùng benchmark tự sinh; Trâm–Anh dùng bảng tự sinh; Tâm–Thanh dùng Reddit pilot và thư viện có sẵn. Sau tuần 1 có thể đổi đầu vào/pipeline composition trong khi giữ module chức năng.

## Các thành phần cần triển khai để bảo vệ kết luận khoa học

Đường dẫn dưới đây là **điểm đặt code khi triển khai**, chưa phải file/thuật toán đã tồn tại. Giữ cây theo chức năng, không tạo hàng loạt file rỗng chỉ để lấp sơ đồ.

| Thành phần | File dự kiến | Trách nhiệm kiểm chứng được |
|---|---|---|
| Data audit | `data/audit.py` | Duplicate IDs, UTC, parent links, deleted/bot policy và loss counts theo tháng |
| Graph semantics | `graphs/snapshots.py`, `graphs/projections.py` | Reply có hướng, R/T đúng định nghĩa, cutoff, trọng số/version và coverage; tính trước chi phí projection |
| Detection | `detection/leiden.py`, các module temporal/consensus khi cần | Membership User-only, objective/gamma/seed, coverage và độ ổn định; đóng băng C_t trước khi đọc t+1 |
| Tracking | `tracking/jaccard.py`, `tracking/ged.py`, `tracking/events.py` | Tách liên kết, lineage và gán sự kiện; precedence rõ cho merge/split; GED có member importance |
| Features | Các module cấu trúc/dị thể/lịch sử trong `features/` | Nguồn, window và thời điểm biết từng feature; không biến nhãn hoặc tương lai thành input |
| Forecasting | Model modules trong `models/` | Chung giao diện fit/predict; B1/B4 và B2/B5/HeTCo với ngân sách phù hợp |
| Evaluation | `evaluation/splits.py`, `metrics.py`, `comparison.py`, `uncertainty.py` | Chia toàn tháng nhãn, kiểm tra sample/reference/truth trùng khớp, metrics có support và so sánh ghép cặp |
| Benchmark | Generator trong `benchmarks/` | Ground truth độc lập, mạng dễ/khó, nhóm nhỏ, sáu sự kiện và seed phát triển/đánh giá tách biệt |

**Một bẫy quan trọng:** số community mỗi tháng không đều; áp dụng bộ chia theo chỉ số dòng có thể tách một tháng sang nhiều tập. Chia bằng danh sách toàn bộ `label_month` rồi ánh xạ về row indices; không chỉ sort rồi chia số dòng. [TimeSeriesSplit docs](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) cũng lưu ý điều kiện khoảng cách mẫu khi muốn so các fold có cùng độ dài thời gian; quyết định chia theo nhóm tháng ở đây là thiết kế của project.

## Hồ sơ thí nghiệm và bằng chứng

`experiments/` chứa **hồ sơ thiết kế được version bằng Git**, còn `artifacts/` chứa output runtime. CLI hiện chỉ đọc `configs/`; không đọc hoặc enforce các hồ sơ `experiments/`.

- `study.toml`: draft định nghĩa nhiệm vụ, graph/nhãn, split, giả thuyết H1–H3, fairness, provenance và điều kiện không được kết luận.
- `experiment_registry.csv`: E1–E5, người phụ trách, loại bằng chứng và điều kiện hoàn tất; tất cả còn trạng thái planned.
- `ablation_registry.csv`: A1–A7, phân biệt ablation chỉ đổi features trên cùng mẫu với thay đổi partition/reference cần chạy lại mọi predictor.
- `feature_catalog.csv`: từng nhóm feature, window, thời điểm biết tại t và các feature cấm vì leakage.
- `literature_matrix.csv`: nguồn, phạm vi đã kiểm tra và ý nghĩa với project; cột novelty hiện chưa có bằng chứng xác nhận tính mới.

Mỗi bảng/hình cuối cùng phải truy được về run ID, data/graph/reference version, cấu hình, seed, môi trường, prediction keys và số mẫu loại. Manifest runtime hiện chỉ ghi cấu hình/Python/package và trạng thái started; checksum, Git revision/dirty state, resource metrics và status hoàn tất **chưa triển khai**. Hồ sơ thiết kế không tự tạo ra bảo đảm runtime.

`reports/claim_evidence.csv` nối H1–H3 và novelty với bằng chứng; các hàng hiện đều chưa được kiểm chứng. `reports/contribution_log.csv` là biểu mẫu trống ghi việc thật/đầu ra/review theo người và mốc báo cáo. Không điền lịch sử tham gia hoặc kết quả chưa xảy ra. Hai bảng này giúp chuẩn bị báo cáo quá trình và bảo vệ kết luận, không thay cho điểm danh hoặc đánh giá trực tiếp của giảng viên.

## Tự phản biện trước mỗi mốc báo cáo

| Câu hỏi người chấm có thể hỏi | Bằng chứng cần có để trả lời |
|---|---|
| Tại sao đây là SNA thay vì chỉ phân loại bảng? | Định nghĩa tương tác, đồ thị dị thể/projection, chất lượng cộng đồng, lineage và đóng góp thông tin mạng |
| Community có đúng không? | Benchmark có phân hoạch chuẩn; trên Reddit dùng coverage, kích thước, connectivity, stability và diễn giải thận trọng; không gọi subreddit là ground truth |
| Tracker đúng hay mô hình chỉ học lại lỗi nhãn? | Tracker trên membership chuẩn trước, detection+tracking sau; ví dụ mơ hồ, phân phối nhãn và reference thay thế |
| Modularity cao đã đủ chưa? | Objective/graph/gamma nhất quán và phân tích nhóm nhỏ, coverage, stability; [resolution-limit paper](https://arxiv.org/abs/physics/0607100) cho thấy giới hạn của tối ưu modularity |
| Temporal coupling có nhìn thấy tương lai không? | Regression check: thêm snapshot tương lai không đổi C_t đã lưu; audit cutoff trên feature/tracking |
| HeTCo hơn vì dữ liệu hay chỉ vì mô hình mạnh hơn? | B5 matched-capacity, cùng mẫu/nhãn/budget; A1/A4 và kiểm tra detector tham chiếu khác |
| Chênh lệch có đáng tin không? | Paired predictions, kết quả từng tháng/lớp, time-block uncertainty và giới hạn khi test chỉ có chín tháng; seed repeats không phải thêm test sets độc lập |
| Insight có mới và có thể giải thích không? | Đối chiếu related work, vài case community/lineage có bằng chứng định lượng, phân tích lỗi và alternative explanations |
| Tại sao không đạt giả thuyết? | Báo cáo null/negative results, giới hạn dữ liệu/nhãn và hiệu quả so với mô hình đơn giản; không đổi test sau khi xem điểm |

Ưu tiên thực nghiệm đủ sức trả lời câu hỏi nghiên cứu: audit/graph đúng, tracker có kiểm chứng, baseline công bằng, dự báo ngoài thời gian, A1/A4 và phân tích lỗi. B6 đắt hoặc các phân tích phụ có thể lùi sau nếu thiếu thời gian. Tuần 1 vẫn ba demo riêng; các mốc giữa/cuối kỳ phải có một câu chuyện nghiên cứu và so sánh trên cùng dữ liệu thật.

Nguồn phương pháp nền: [ConvoKit](https://convokit.cornell.edu/documentation/subreddit.html), [Leiden](https://doi.org/10.1038/s41598-019-41695-z), [GED](https://doi.org/10.1007/s13278-012-0058-8), [notebook execution](https://nbclient.readthedocs.io/en/latest/client.html). Khả năng bài báo của đề tài vẫn cần đánh giá qua related work và kết quả thực tế.

## Data contracts v1

Dataclass trong `contracts.py` là giao diện in-memory. Khi viết adapter CSV/Parquet, serialize thành cột tường minh và lưu `schema_version=1` trong metadata. Chưa có adapter hoặc migration dữ liệu ở bộ khung này.

| Record | Field và quy tắc |
|---|---|
| `SnapshotEdge` | `month`, `source_user_id`, `target_user_id`, `weight`; YYYY-MM, không self-loop, trọng số hữu hạn >0 |
| `Membership` | `reference_id`, `month`, `community_id`, `user_id`; community ID cục bộ theo tháng |
| `SampleKey` | `reference_id`, `feature_month`, `community_id`; khóa ghép duy nhất của mẫu dự báo |
| `TrackingLink` | `source`, `target` là SampleKey; target có thể thiếu, nếu có phải cùng reference và tháng kế tiếp |
| `CommunitySample` | `key`, `label_month`, `label`, `features`; label_month = feature_month + 1 |
| `Prediction` | `key`, `label_month`, `model`, `y_true`, `y_pred`; nhãn theo Event |

Sáu mã nhãn: `stable`, `grow`, `shrink`, `merge`, `split`, `dissolve`. Link chưa có target **không tự động chứng minh dissolve**: thuật toán cần xét độ phủ, nhóm nhỏ và tháng kế tiếp thật sự có tồn tại. Không gán dissolve cho tháng cuối thiếu quan sát.

Reference ID cần rõ nghĩa như `leiden-jaccard-v1`; đổi detector/tracker hoặc quy tắc nhãn phải phân biệt bộ tham chiếu. Hai community có cùng ID ở hai tháng không mặc nhiên là cùng nhóm. Split/merge có thể có nhiều TrackingLink; gán một nhãn mẫu theo quy tắc được cố định trước đánh giá.

Contracts kiểm tra cấu trúc và quan hệ tháng cơ bản. Chất lượng dữ liệu, thời điểm biết từng feature, tính duy nhất của bảng, sáu sự kiện và chống leakage vẫn cần kiểm chứng khi triển khai. Chia tập theo `label_month`, fit preprocessing chỉ trên train; Reddit tracker labels không phải ground truth xã hội.

## Config và artifact

TOML phải có đúng `schema_version`, `pipeline`, `project_root`, `seed`, `input`, `output`. Không âm thầm bỏ qua field lạ. Mọi path resolve từ thư mục config, không từ cwd/vị trí cài package. Seed là số nguyên [0, 2^32); run ID dài 1–64 ký tự chữ/số/gạch ngang/gạch dưới, không chứa dấu chấm, path separator hoặc tên thiết bị Windows.

`core` dùng `input.kind="reddit"` và input directory có sẵn. Hai pipeline khác dùng `synthetic`, có thể không có path vì generator được triển khai trong nhóm; nếu chỉ định path thì phải tồn tại. Đây là policy tuần 1; khi hỗ trợ bảng thật cho prediction, sửa policy có kiểm chứng thay vì đổi tên kind.

Output nằm trong `project_root/artifacts`; path resolve không được chồng lên input hoặc `project_root/data`. Mỗi run ở `<output.root>/<pipeline>/<run_id>/`. Kiểm tra path trước khi tạo thư mục và mkdir độc quyền để không ghi đè. Run đã tồn tại, kể cả thất bại, cần ID mới. Manifest chỉ ghi trạng thái `started`; chưa có trạng thái giả thành công.

Pipeline tương lai kiểm tra đủ dependency/stage trước khi tạo run; gọi `create_run_directory`, chạy các bước rồi lưu metrics/log thật. Không import hoặc đọc output nhóm khác để hoàn thành demo tuần 1.

## Mở rộng theo thứ tự

1. Tâm–Thanh thêm reader/audit trong data và snapshot/projection trong graphs, detector thư viện tạm, tracking/features và mô hình cơ bản; chưa cần multislice để ghép luồng tối thiểu.
2. Phúc–Đăng thêm generator mạng chuẩn, Leiden và Jaccard; kiểm chứng tracker riêng rồi toàn luồng.
3. Trâm–Anh thêm generator bảng, Majority/Persistence/Logistic Regression, split thời gian và metrics.
4. Ghép với Reddit thật qua contracts; thêm GED, tầng T, HeTCo và đối chứng nâng cao tại module tương ứng.

Không thêm file thuật toán rỗng cho mọi kế hoạch trước khi có implementation. Mỗi thuật toán có test hành vi phù hợp và dependency trong pyproject. Cấu trúc này giảm sửa lại khi tích hợp, không bảo đảm schema sẽ không bao giờ đổi.
