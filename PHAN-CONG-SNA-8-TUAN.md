# Phân công công việc SNA trong 8 tuần

**Đề tài:** How Online Communities Change Over Time.

**Thời gian:** 15/10–09/12/2026. Báo cáo **midterm lần 1 vào 22/10/2026**, hoàn thành đầu ra tuần 1 trước tối 21/10. Các mốc sau là lịch nội bộ.

Mỗi người có nhiệm vụ riêng và cùng người trong cặp hoàn thành một đầu ra chung. Tâm–Thanh làm core, Phúc–Đăng làm detection/tracking đối chứng, Trâm–Anh làm dự báo/đánh giá. **Tuần 1, mỗi cặp triển khai và trình bày demo riêng cho ngày 22/10, không cần đầu ra từ cặp khác.** Baseline và mô hình phân tích cần có code chạy được, ghi rõ dùng dữ liệu thật hay giả lập. Từ tuần 2 mới ghép các đầu ra để so sánh trên cùng dữ liệu.

### Định hướng chất lượng theo rubric giảng viên

A1 thi lý thuyết 50%; A2 đồ án 50%. Điểm tối đa của đồ án đòi hỏi tiềm năng paper và quá trình tham gia. Nhóm định hướng nghiên cứu có phân tích SNA: tính mới cần kiểm chứng bằng related work; không xem source chạy được hoặc nhiều thuật toán là đủ.

Mỗi cặp dùng notebook `00_research_plan.ipynb` của mình để ghi câu hỏi, đầu vào, protocol, đối chứng, kết quả có artifact và phần phản biện. Notebook kế hoạch là tài liệu thiết kế; không coi template là kết quả. Thí nghiệm midterm đã chạy theo protocol được enforce tại `configs/midterm.toml`; các thí nghiệm mở rộng còn planned phải được phân biệt rõ. Không tạo phụ thuộc runtime giữa ba demo tuần 1.

Các mốc giữa/cuối kỳ cần kiểm chứng graph/coverage, tracker trên ground truth, split theo toàn tháng nhãn, đối chứng cùng mẫu/nhãn/budget, ablation có mục tiêu và phân tích lỗi/giới hạn. Test phần mềm không thay cho bằng chứng SNA. Xem docs/METHODS.md để biết thành phần source và câu hỏi cần bảo vệ.
## 1. Phần việc sở hữu

| Người | Trách nhiệm chính |
|---|---|
| **Tâm** | Tạo GitHub, dựng cấu trúc và môi trường, tái sử dụng pipeline dữ liệu. Tạo snapshot và hai tầng R/T. Triển khai detector đề xuất gồm multislice và consensus, tích hợp pipeline |
| **Thanh** | Triển khai GED thích nghi, đặc trưng community và HeTCo. Quản lý lịch sử thành viên, thời điểm biết đặc trưng và ablation của phương pháp chính |
| **Phúc** | Triển khai detector đối chứng, benchmark động và B6 trên graph con. Phụ trách B2 Random Forest/B5 Structural Gradient Boosting, kiểm tra chi phí và độ nhạy detection |
| **Đăng** | Triển khai Jaccard, kiểm chứng nhãn và chất lượng dữ liệu. Phụ trách bộ đánh giá nâng cao gồm test leakage, bootstrap theo thời gian và chạy thí nghiệm H2 |
| **Trâm** | Triển khai B1 Majority/Persistence và B4 Logistic Regression. Chạy các baseline bằng cấu hình đã bàn giao, quản lý kết quả, so sánh ablation và viết phần đối chứng |
| **Anh** | Tính chỉ số cơ bản, kiểm tra bảng mẫu, vẽ biểu đồ và tổng hợp kết quả. Viết phần protocol từ quy trình đã chốt, ghép báo cáo/slide và chuẩn bị trình bày |

Tâm–Thanh giữ core. Phúc và Đăng nhận thêm phần triển khai/tính toán nặng, Trâm và Anh có phần việc thực hành riêng nhưng thiên về baseline cơ bản, chạy cấu hình có sẵn, kết quả và báo cáo. Rà soát khối lượng hằng tuần để tránh dồn quá nhiều việc cho một người. Ưu tiên tái sử dụng script và thư viện, triển khai bản tối thiểu trước khi mở rộng.

### Cấu trúc GitHub do Tâm thiết lập

```text
reddit-community-evolution/
├── README.md
├── docs/                      # METHODS và RUNBOOK
├── pyproject.toml              # Package và dependencies
├── .gitignore
├── configs/                    # Cấu hình runtime ba nhóm
├── experiments/                # Protocol draft, E1–E5/A1–A7, features và related work
├── notebooks/                  # Thử nghiệm và trình bày bằng .ipynb
│   ├── core/                   # Tâm–Thanh
│   ├── detection_tracking/     # Phúc–Đăng
│   └── prediction/             # Trâm–Anh
├── src/reddit_sna/
│   ├── cli.py                  # Tâm điều phối giao diện chung
│   ├── config.py               # TOML, path và cấu hình từng lần chạy
│   ├── contracts.py            # Schema dữ liệu chung, không chứa kết quả nhóm khác
│   ├── artifacts.py            # Output theo pipeline/run_id, không ghi đè
│   ├── data/                   # Tâm: corpus, chuẩn hóa, identity/audit
│   ├── graphs/                 # Tâm: graph dị thể, snapshot R/T, projection/coverage
│   ├── detection/              # Phúc: đối chứng; Tâm: temporal/consensus
│   ├── tracking/               # Đăng: Jaccard; Thanh: GED
│   ├── features/               # Thanh
│   ├── models/                 # Trâm: B1/B4; Phúc: B2/B5; Thanh: HeTCo
│   ├── evaluation/             # Anh: chỉ số; Đăng: leakage/bootstrap
│   ├── benchmarks/             # Phúc: mạng động; Trâm: bảng mẫu
│   └── pipelines/
│       ├── core.py             # Tâm–Thanh
│       ├── detection_tracking.py # Phúc–Đăng
│       └── prediction.py       # Trâm–Anh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/               # Dữ liệu tổng hợp nhỏ
├── data/                       # Dataset đã duyệt qua Git/LFS; khóa riêng giữ local
├── artifacts/                  # Output riêng <pipeline>/<run_id>, không commit
└── reports/WEEK1_REPORT.md      # Báo cáo tổng hợp duy nhất của cả nhóm
```

Source chia theo chức năng để dùng lại khi tích hợp; mỗi nhóm có pipeline, config và output riêng, không phụ thuộc artifact nhóm khác trong tuần 1. Mỗi nhóm có thể phát triển và demo bằng notebook riêng, chạy lại được từ kernel sạch theo thứ tự cell. Logic đã ổn định hoặc cần dùng lại chuyển vào src/reddit_sna; notebook import lại, không copy source. Demo notebook đủ input đến evaluation được chấp nhận trong phạm vi nhóm; CLI tiếp tục phục vụ tự động hóa và tích hợp. Thêm thuật toán vào module tương ứng, không tạo cây proposed/baseline hoặc thư mục source theo tên người. Tâm tạo repository, mời năm thành viên còn lại và hướng dẫn cài đặt. Theo quyết định công bố dữ liệu sau đó của chủ repo, 15 corpus gốc và processed lịch sử đã được đưa lên Git/LFS kèm checksum. Khóa riêng, bảng ánh xạ danh tính, `.venv`, artifact runtime và bộ mẫu chấm nhãn vẫn giữ local.

## 2. Ranh giới công việc và cách làm song song

- Trong tuần 1, từng cặp tự chuẩn bị dữ liệu mẫu và thống nhất giao diện nội bộ. Tâm và Thanh không cần cung cấp features/nhãn cho Trâm và Anh ở mốc này.
- Tâm–Thanh tự chạy core tối thiểu từ Reddit pilot đến đánh giá bằng detector và chỉ số thư viện. Phúc–Đăng tự sinh benchmark để chạy và đánh giá detection/tracking. Trâm–Anh tự tạo bảng community–tháng để chạy baseline và đánh giá. Mỗi cặp tự có đủ đầu vào và code cho demo của mình.
- Trong 19–21/10, mỗi cặp ghép, đánh giá và chạy lại demo của mình. Mỗi nhóm dùng thư mục code, cấu hình và output riêng, không ghi đè artifact của nhóm khác. Từ tuần 2 mới thống nhất schema và bàn giao để tích hợp chung.
- Fixture chỉ phục vụ phát triển và test, không được trình bày như kết quả Reddit. Khi chưa có artifact thật, vẫn hoàn thiện code bằng fixture.
- Người nhận báo lỗi qua issue, người sở hữu sửa module. Đổi schema cần thông báo và cập nhật phiên bản.
- Tuần 1 có ba demo riêng và kết quả nghiên cứu sơ bộ phục vụ midterm 22/10; từ tuần 2 củng cố dữ liệu/nhãn trên bản tích hợp hiện có, sau đó phát triển và kiểm chứng phương pháp. Người nhận tiếp tục test bằng fixture nếu bàn giao chậm. Không gọi demo giả lập là kết quả Reddit.

**Bảng bàn giao dưới đây áp dụng từ tuần 2, không phải phụ thuộc của tuần 1.** Trong tuần 1, mỗi cặp tự chuẩn bị kết quả và lệnh demo; Anh tổng hợp báo cáo từ nội dung đã được người phụ trách xác nhận.

| Artifact | Người xuất | Người sử dụng |
|---|---|---|
| Snapshot và hai tầng R/T | Tâm | Thanh, Phúc, Đăng |
| Community đề xuất | Tâm | Thanh, Đăng, Anh |
| Community đối chứng | Phúc | Thanh, Đăng, Anh |
| Nhãn GED | Thanh | Trâm, Đăng, Anh |
| Nhãn Jaccard | Đăng | Thanh, Trâm, Anh |
| Đặc trưng community và cờ ablation | Thanh | Trâm, Anh |
| Benchmark có phân hoạch và sự kiện chuẩn | Phúc | Tâm, Thanh, Đăng, Anh |
| Dự đoán HeTCo | Thanh | Đăng, Anh |
| Mã B2/B5 và cấu hình | Phúc | Trâm |
| Dự đoán baseline | Trâm chạy, Phúc hỗ trợ kỹ thuật | Đăng, Anh |
| Kiểm tra leakage và khoảng tin cậy | Đăng | Anh |

Từ tuần 2 dùng khóa ghép mẫu `reference_id + month + community_id` để tích hợp. Chia tập theo tháng xảy ra sự kiện cần dự báo. Features chỉ dùng dữ liệu biết đến t. Nhãn GED/Jaccard là các bộ tham chiếu riêng. Benchmark chọn tham số tách khỏi benchmark đánh giá. So sánh trên pilot chung cần features/nhãn từ Thanh, demo baseline tuần 1 dùng bảng riêng do Trâm chuẩn bị.

## 3. Công việc từng tuần

### Tuần 1 — 15–21/10: prototype và kết quả sơ bộ cho midterm lần 1 ngày 22/10

Midterm lần 1 cần đủ experimental plan chi tiết, kết quả baseline và preliminary results của proposed method. Proposed chưa bắt buộc vượt baseline; phải có đặc tả, kết quả thật, đối chứng và phân tích giới hạn. Mỗi nhóm hoàn thành một prototype từ đầu vào riêng đến kết quả đánh giá. Mỗi người có công việc riêng và chỉ bàn giao kỹ thuật cho người cùng nhóm trong tuần 1. Không phải chờ hoặc sử dụng artifact của nhóm khác.

#### Nhóm Tâm–Thanh: prototype core trên Reddit pilot

**Đầu ra chung:** một đường chạy độc lập `Reddit pilot → snapshot R → community → tracking/nhãn → features → mô hình cơ bản → kết quả đánh giá sơ bộ`. Nhóm tự phụ trách toàn bộ đường chạy này, không cần nhận detector/tracker từ Phúc–Đăng hoặc bộ đánh giá từ Trâm–Anh.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Tâm** | Đã chuẩn bị sẵn bộ dataset Reddit gồm 15 corpus và các script xử lý ban đầu. Tạo repository GitHub cho đề tài, viết mô tả repo, mời năm thành viên còn lại và phân quyền cộng tác. Dựng cấu trúc thư mục, thiết lập chính sách quản lý dữ liệu và file riêng tư; dataset đã được chủ repo duyệt công bố qua Git/LFS, khai báo thư viện/môi trường và viết README hướng dẫn cài đặt, chạy demo, quy tắc đặt nhánh và gửi pull request. Rà soát dữ liệu đã có, tổ chức thư mục và manifest. Chọn phạm vi pilot nhỏ gồm các tháng liên tiếp trong train, chạy chuẩn hóa và dựng mạng trả lời R. Dùng thư viện Independent Leiden để tạo community tạm cho chính prototype core. Chốt giao diện nội bộ với Thanh, viết lệnh chạy và ghép đường chạy của nhóm. | Repository GitHub đã mời thành viên, cấu trúc thư mục, .gitignore, cấu hình môi trường/thư viện, README cộng tác và chạy demo; manifest pilot, snapshot thật, membership tạm và cấu hình detector. |
| **Thanh** | Nhận membership từ Tâm, triển khai tracking tối thiểu và bảng đặc trưng community. Ưu tiên GED bản đầu; nếu chưa hoàn thành, dùng quy tắc overlap/Jaccard được ghi rõ để giữ đường chạy thông suốt. Tạo nhãn chuyển tiếp t→t+1, features chỉ dùng thông tin đến t. Chạy một mô hình dự báo cơ bản và tính chỉ số bằng thư viện có sẵn trên phần giữ lại theo thời gian trong pilot. Ghi rõ phần nào của GED/HeTCo chưa triển khai. | Tracker, bảng features/nhãn, mô hình cơ bản, predictions, macro-F1 và confusion matrix của prototype core. |

**Giới hạn tuần 1:** detector tạm và mô hình cơ bản giúp kiểm tra luồng core. Chưa bắt buộc hoàn thành tầng T, multislice, consensus hoặc HeTCo đầy đủ. Không gọi mô hình cơ bản là HeTCo hoàn chỉnh. Tâm–Thanh tự làm phần detection và đánh giá tối thiểu bằng thư viện; Phúc–Đăng và Trâm–Anh vẫn phát triển phần chuyên trách riêng để tích hợp sau.

#### Nhóm Phúc–Đăng: prototype detection và tracking có kiểm chứng

**Đầu ra chung:** một đường chạy độc lập `benchmark mạng động → detection → membership → tracking → đánh giá với nhãn chuẩn`. Nhóm tự sinh dữ liệu, không cần snapshot của Tâm hoặc bảng nhãn của Thanh.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Phúc** | Sinh mạng động nhỏ với community và thành viên biết trước; cùng Đăng xác định các tình huống giữ nguyên, tăng, giảm, hợp nhất, tách và phân rã. Lưu phân hoạch chuẩn, seed và cấu hình. Chạy Independent Leiden trên từng snapshot, kiểm tra membership và độ phủ. Tính AMI so với phân hoạch chuẩn, ghi chi phí chạy và ghép phần detection vào demo nội bộ. | Bộ benchmark tổng hợp có ground truth, code detector, membership dự đoán và bảng AMI. |
| **Đăng** | Cùng Phúc xây quy tắc nhãn chuẩn và tình huống mơ hồ. Triển khai Jaccard tracker; cố định ngưỡng và thứ tự xử lý sự kiện. Trước tiên kiểm chứng tracker trên membership chuẩn, sau đó chạy trên membership detector của Phúc để phân biệt lỗi tracking với lỗi detection. Tính macro-F1, F1/support từng sự kiện và confusion matrix; tổng hợp trường hợp sai. | Tracker, test sáu sự kiện, nhãn dự đoán, kết quả tracking riêng và kết quả toàn luồng detection–tracking. |

**Điều kiện đánh giá:** tách các mạng dùng phát triển/chọn ngưỡng khỏi mạng dùng đánh giá. Kết quả là kiểm chứng trên dữ liệu tổng hợp có ground truth, không trình bày như kết quả dự báo Reddit.

#### Nhóm Trâm–Anh: prototype baseline dự báo và đánh giá

**Đầu ra chung:** một đường chạy độc lập `bảng community–tháng mẫu → split thời gian → huấn luyện baseline → predictions → evaluation results`. Nhóm tự tạo bảng mẫu có quy tắc, không cần features/nhãn từ Thanh hoặc tracker của Đăng.

| Thành viên | Nhiệm vụ riêng | Đầu ra cá nhân |
|---|---|---|
| **Trâm** | Tự tạo bảng community–tháng tổng hợp có lịch sử, features, nhãn và seed tái lập. Mô tả rõ cơ chế sinh nhãn để tránh kết quả khó hiểu. Triển khai B1 Majority/Persistence và B4 Logistic Regression; thêm fallback Majority khi thiếu lịch sử. Dùng split Anh cung cấp, chỉ fit xử lý dữ liệu và mô hình trên tập học, xuất dự đoán từng mẫu. | Script sinh bảng mẫu, bảng dữ liệu, code baseline, cấu hình/model và predictions B1/B4. |
| **Anh** | Thống nhất schema với Trâm, viết chia tập theo thời gian của tháng nhãn. Kiểm tra khóa mẫu, số lớp và thời điểm biết features; tạo các kiểm tra cơ bản ngăn dùng dữ liệu tương lai. Đánh giá dự đoán Trâm bàn giao, xuất macro-F1, balanced accuracy, precision/recall/F1/support từng lớp và confusion matrix. Viết hướng dẫn đọc kết quả và ghép phần trình bày của nhóm. | Split, code đánh giá, bảng kết quả baseline, confusion matrix, báo cáo giới hạn và lệnh demo của nhóm. |

**Điều kiện đánh giá:** tập học phải có ít nhất hai lớp để chạy Logistic Regression. Ghi rõ lớp thiếu và quy ước tính macro-F1. Điểm trên bảng tổng hợp chứng minh baseline và evaluation chạy được; chưa chứng minh khả năng dự báo trên Reddit. Không so trực tiếp điểm này với điểm của hai nhóm còn lại.

#### Lịch tuần 1

| Mốc | Công việc của từng nhóm |
|---|---|
| **15–16/10** | Mỗi cặp chốt phạm vi, schema và lệnh chạy nội bộ; chuẩn bị đầu vào riêng. Mỗi người bắt đầu module của mình. |
| **17–18/10** | Hai người trong mỗi cặp ghép module và chạy lần đầu từ input của nhóm đến output. Nhóm nào có lỗi tự xử lý trong phạm vi của mình. |
| **19–20/10** | Hoàn thành bước đánh giá, kiểm tra dữ liệu/nhãn/split, lưu kết quả và sửa lỗi. Không có mốc chờ artifact từ nhóm khác. |
| **21/10** | Mỗi cặp chạy lại bằng cấu hình cố định vào thư mục output mới; hoàn thiện README, log và kết quả cho báo cáo midterm. |
| **22/10** | Trình bày ba demo độc lập. Từng người giải thích nhiệm vụ, code, đầu ra và hạn chế của phần mình. |

#### Checklist nghiệm thu mỗi nhóm

- [ ] Có đầu vào xác định, nguồn dữ liệu và phạm vi được ghi rõ.
- [ ] Có code và cấu hình của cả hai người, ghép thành một lệnh hoặc chuỗi lệnh được ghi đầy đủ trong README.
- [ ] Chạy từ đầu vào của nhóm đến kết quả đánh giá mà không phải xin artifact từ nhóm khác hoặc nhập tay dự đoán để hoàn thành demo.
- [ ] Có bảng kết quả, kiểm tra phù hợp và ví dụ lỗi; phân biệt dữ liệu thật với tổng hợp.
- [ ] Lưu seed, phiên bản môi trường, cấu hình, log và output trong thư mục riêng của nhóm.
- [ ] Ghi rõ phần chưa hoàn thành, không coi sơ đồ hoặc code chưa chạy là prototype hoàn tất.


### Tuần 2 — 22–28/10: kiểm tra dữ liệu/nhãn và chốt thiết kế đánh giá

Tái sử dụng bản tích hợp và kết quả midterm hiện có; không làm lại B1/B2/B4/B5 hoặc metric đã chạy. Mỗi người xử lý vấn đề trong module sở hữu.

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Audit coverage, identity, snapshot và thời điểm quan sát; kiểm kê mức sử dụng các giai đoạn dữ liệu | Manifest chất lượng và danh sách kỳ đã xem/chưa xác nhận |
| **Thanh** | Phân tích nhãn dissolve, 732 mẫu bị loại và lịch sử thiếu; chuẩn bị mẫu review theo lớp/tháng | Bảng nguyên nhân loại mẫu, lỗi tracking/features và quy tắc nhãn |
| **Phúc** | Phân tích detection trên benchmark khó: phân mảnh, AMI, unmatched/extra; chọn phạm vi thử nghiệm phù hợp tài nguyên | Báo cáo lỗi detection và kế hoạch thử detector |
| **Đăng** | Phối hợp Phúc review nhãn Reddit độc lập, ghi bất đồng; kiểm tra leakage và đề xuất split theo tháng nhãn | Bảng review thực tế, kết quả leakage và split đề xuất |
| **Trâm** | Phân tích baseline theo lớp/tháng, fallback và lỗi so với proposed trên development | Bảng lỗi và danh sách thử nghiệm mô hình có giới hạn |
| **Anh** | Tổng hợp support, mẫu bị loại và độ phủ; ghi metric, budget, điều kiện đánh giá và trạng thái dữ liệu | Protocol đánh giá thống nhất và bảng chất lượng dữ liệu |

**Nghiệm thu:** giải thích được lớp lệch/thiếu và mẫu bị loại; sửa lỗi có bằng chứng, không đổi nhãn để tăng điểm. Cả nhóm chốt phạm vi train/validation và dự kiến giữ riêng test. Chỉ gọi test là chưa xem khi kiểm kê xác nhận được; nếu không, ghi rõ đánh giá development. Mỗi người đối chiếu related work thuộc phần mình và ghi nguồn/khác biệt cần kiểm chứng.

### Tuần 3 — 29/10–04/11: cải thiện proposed forecasting trên development

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Bổ sung khả năng quan sát/missing flags cho context; kiểm tra feature không đọc tương lai | Context được kiểm chứng, thống kê độ sẵn có |
| **Thanh** | Thiết kế proposed v1 từ giả thuyết context/history; thử LR cộng feature mới, có/bỏ lag và thay đổi hoạt động theo thời gian | Đặc tả proposed v1, feature blocks và ablation chạy được |
| **Phúc** | Thiết lập không gian tham số nhỏ cho RF/HGB; thống nhất budget với LR/proposed, kiểm tra chi phí | Cấu hình tìm kiếm công bằng và giới hạn tài nguyên |
| **Đăng** | Kiểm tra cùng mẫu/nhãn, train-only preprocessing và cutoff của feature mới | Kiểm tra hợp đồng và negative controls |
| **Trâm** | Chạy LR gốc/LR thêm context-history và RF/HGB trên validation theo thời gian; lưu tất cả lượt chạy | Bảng validation, predictions và lỗi từng lớp/tháng |
| **Anh** | Tổng hợp kết quả và ablation, phân biệt tác dụng feature với thay đổi estimator | Bảng so sánh và quyết định giữ/bỏ từng giả thuyết |

**Nghiệm thu:** có kết luận dựa validation, kể cả kết quả âm. LR hiện mạnh nhất phải được giữ làm đối chứng; không chỉ so proposed với B5 yếu hơn. Không dùng điểm test cuối để chọn feature hoặc tham số.

### Tuần 4 — 05–11/11: phát triển và kiểm chứng thành phần SNA đề xuất

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Dựng R/T và temporal/consensus bản tối thiểu, thêm từng thành phần trên fixture rồi development | Detector đề xuất có công tắc thành phần và provenance |
| **Thanh** | Kiểm tra GED thích nghi trên phân hoạch mới, giữ reference riêng; liên kết với forecasting v1 | Nhãn/features cho từng reference và phân tích lịch sử |
| **Phúc** | So Independent Leiden với detector mới trên benchmark dễ/khó và nhiều seed đã chốt | AMI, coverage, chi phí và kết quả detection thành phần |
| **Đăng** | Tách lỗi detection khỏi tracking bằng truth/detector routes; phân tích GED–Jaccard | Bảng lỗi sự kiện, matched/unmatched và reference sensitivity |
| **Trâm** | Chạy baseline/proposed trên cùng mẫu và nhãn bên trong từng reference | Kết quả forecasting development theo reference |
| **Anh** | Tổng hợp insight SNA và giải thích thay đổi kết quả theo cấu trúc mạng | Bảng liên kết detection → tracking → forecasting |

**Nghiệm thu:** xác định thành phần SNA có ích hoặc gây lỗi ở đâu. Không so trực tiếp F1 giữa các reference như cùng một bài toán. Nếu detector mở rộng chưa ổn, giữ cấu hình độc lập hiện có làm đường chạy chính và báo giới hạn, không chặn toàn nhóm.

### Tuần 5 — 12–18/11: validation, ablation và khóa thiết kế

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy phạm vi dữ liệu đã chốt; kiểm tra A2/A3/A5 nếu thành phần tương ứng thực sự triển khai; đo chi phí | Manifest development và ablation detection |
| **Thanh** | Hoàn thiện proposed, chạy A1/A4/A6; chọn cấu hình chỉ bằng validation | Mô hình ứng viên và giải thích đóng góp feature |
| **Phúc** | Hoàn thành budget baseline/detector; đánh giá độ nhạy trên development | Baseline mạnh nhất và bảng độ nhạy |
| **Đăng** | Kiểm tra review nhãn, fairness, bootstrap theo tháng và độ nhạy reference/ngưỡng | Audit trước test và quy tắc khoảng bất định |
| **Trâm** | Chạy đủ cấu hình đã đăng ký; lưu cả kết quả âm và chọn baseline theo quy tắc chung | Registry hoàn chỉnh và cấu hình baseline khóa |
| **Anh** | Tổng hợp kết quả validation, related work và tiêu chí chấp nhận/giới hạn | Bản protocol cuối và kết luận development |

**Nghiệm thu:** khóa dữ liệu/phạm vi, feature, nhãn, estimator, budget, metric và cấu hình trước test; lưu hash và lý do lựa chọn. Ablation phục vụ chọn phương pháp được thực hiện ở development trước khi mở test. Không bắt buộc proposed thắng; phải giải thích được bằng chứng ủng hộ hoặc bác bỏ giả thuyết. Khi thiếu tài nguyên, giảm B6/phạm vi độ nhạy trước, giữ đối chứng mạnh và kiểm tra chất lượng.

### Tuần 6 — 19–25/11: đánh giá cuối theo protocol đã khóa

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy pipeline trên kỳ giữ riêng đã được xác nhận; bảo toàn cutoff và input hashes | Community và manifest đánh giá cuối |
| **Thanh** | Xuất features/nhãn theo quy tắc khóa, chạy proposed và ablation xác nhận đã định trước | Predictions proposed và ablation |
| **Phúc** | Chạy detector đối chứng và hỗ trợ RF/HGB đúng cấu hình khóa | Artifact đối chứng và chi phí thực tế |
| **Đăng** | Audit mẫu/nhãn, paired differences và bất định theo thời gian; không pseudo-replication theo seed | Kết quả kiểm chứng và giới hạn thống kê |
| **Trâm** | Chạy toàn bộ baseline khóa trên cùng mẫu/nhãn với proposed trong từng reference | Predictions baseline cuối |
| **Anh** | Tổng hợp F1, từng lớp/tháng, support, confusion và chênh lệch với baseline mạnh nhất | Bảng kết quả cuối và kết luận H1–H3 theo bằng chứng |

**Nghiệm thu:** không tinh chỉnh sau khi xem test. Nếu không xác nhận được kỳ chưa xem hoặc support thời gian không đủ, báo rõ kết quả development/giới hạn bất định; không tự cấp chứng nhận unseen. Nếu phát hiện lỗi triển khai, lưu run lỗi, mô tả sửa đổi và công khai việc đánh giá lại.

### Tuần 7 — 26/11–02/12: phân tích kết quả và kiểm chứng tái lập

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy lại từ môi trường sạch, kiểm tra source/config/input và đo tài nguyên | Bằng chứng tái lập end-to-end |
| **Thanh** | Phân tích ca đúng/sai và đóng góp context/history theo ablation đã chốt | Giải thích phương pháp và giới hạn |
| **Phúc** | Kiểm tra kết quả benchmark, seed và chi phí; đối chiếu detector/reference | Phân tích độ ổn định detection |
| **Đăng** | Rà soát kết luận thống kê, review nhãn và các cách giải thích thay thế | Danh sách threats to validity và audit kết quả |
| **Trâm** | Tái lập predictions baseline và đối chiếu bảng mô hình với registry | Bảng so sánh đã kiểm tra độc lập |
| **Anh** | Tổng hợp insights SNA, kết quả âm và mức đóng góp so với related work | Bản thảo kết quả/thảo luận có nguồn và bằng chứng |

**Nghiệm thu:** các bảng tái lập được và kết luận không vượt bằng chứng. Phân tích mới phát sinh sau test phải ghi exploratory; không quay lại chọn mô hình theo test. Đánh giá độ nhạy đã định trước có thể hoàn tất ở đây nhưng không dùng để sửa cấu hình cuối.

### Tuần 8 — 03–09/12: tái lập và hoàn thiện bàn giao

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Thử môi trường sạch, hoàn thiện README/lệnh chạy. Viết pipeline, kiến trúc, detector đề xuất | Repository bàn giao và báo cáo core |
| **Thanh** | Rà soát GED/features/HeTCo, viết phương pháp chính, đóng góp và hạn chế | Phần tracking/features/HeTCo hoàn chỉnh |
| **Phúc** | Kiểm tra tái lập detector/B2/B5, viết benchmark, đối chứng detection và H1. Bàn giao mô tả B2/B5 cho Trâm | Module đối chứng hoàn chỉnh và báo cáo kỹ thuật |
| **Đăng** | Kiểm tra lại leakage/bootstrap, viết kiểm chứng dữ liệu/nhãn và H2. Xác nhận bảng số liệu/khoảng tin cậy với Anh | Bộ đánh giá nâng cao và phần kiểm chứng |
| **Trâm** | Viết baseline, kết quả dự báo/ablation, chuẩn bị demo so sánh mô hình | Phần đối chứng và kết quả H3 |
| **Anh** | Biên tập protocol từ nội dung Đăng bàn giao, ghép bảng biểu/báo cáo/slide và kiểm tra trình bày | Báo cáo tổng hợp, slide và kịch bản trình bày |

Cả sáu người diễn tập và giải thích được phần mình. Không thêm thí nghiệm sát hạn nếu chưa đủ thời gian kiểm tra lại kết luận.

**Ghép việc tuần 8:** từng người bàn giao phần báo cáo, bảng/hình và lệnh demo trước 06/12. Anh ghép báo cáo/slide, Tâm kiểm tra pipeline từ môi trường sạch. Người sở hữu sửa lỗi được phát hiện, các cặp review phần của nhau và cả sáu người diễn tập trước 09/12.

## 4. Quy tắc bàn giao

- Mỗi người cập nhật việc đã làm, đường dẫn code/artifact, lỗi và kế hoạch tiếp theo trong issue/registry chung theo module; không tạo thư mục source hoặc báo cáo theo tên người.
- Hoàn thành nghĩa là có đầu ra kiểm tra được, lệnh chạy và test phù hợp. Phân biệt kết quả fixture, pilot và toàn kỳ.
- Tâm–Thanh, Phúc–Đăng, Trâm–Anh review trong từng cặp trước khi merge. Review không chuyển quyền sở hữu module.
- Anh tổng hợp nội dung đã được từng người xác nhận, không viết thay mọi người. Tâm điều phối tích hợp, không chịu trách nhiệm sửa mọi module.
- Khi quá tải, giảm B6 hoặc độ nhạy mở rộng trước. Giữ dữ liệu hợp lệ, tracking được kiểm chứng, B5–HeTCo và A1/A4. Không bỏ kiểm tra leakage, tinh chỉnh theo test hoặc tạo kết quả cho đủ bảng.

### Checklist midterm lần 1 — 22/10

Trạng thái dưới đây là nghiệm thu đầu ra phần mềm trên main d0fde17, không chứng nhận mức tham gia hay khả năng trình bày của từng thành viên.

- [x] Repository, môi trường, cấu trúc source và dữ liệu đã được tổ chức; chủ repo xác nhận đã mời thành viên.
- [x] Ba demo độc lập chạy từ input đến evaluation; phân biệt Reddit và dữ liệu tổng hợp.
- [x] Experimental plan chi tiết và protocol midterm thực thi được.
- [x] Baseline và preliminary proposed HeTCo-v0 có predictions, metrics, so sánh và ablation.
- [x] Notebook nghiên cứu đã chạy kernel sạch: 7 code cells, 7 biểu đồ; tổng suite 584/584 tests đạt.
- [x] Báo cáo ghi kết quả âm, lớp thiếu/lệch, coverage và giới hạn dữ liệu đã xem; proposed chưa vượt LR.
- [ ] Từng thành viên kiểm tra, hiểu và xác nhận nội dung thuộc phần mình; không có đầu việc làm slide midterm trong phân công này.

Tuần 1 là midterm lần 1, không đợi đến tuần 4 mới có proposed sơ bộ. Từ tuần 2 ưu tiên chất lượng dữ liệu/nhãn và kiểm chứng đóng góp phương pháp; human annotation và unseen confirmation vẫn pending, được lên lịch thực hiện chứ không tự đánh dấu xong. Xem [reports/WEEK1_REPORT.md](reports/WEEK1_REPORT.md) và [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Bản tích hợp toàn nhóm tuần 1

Báo cáo hiện hành của cả sáu thành viên ở [reports/WEEK1_REPORT.md](reports/WEEK1_REPORT.md). Phúc–Đăng được tích hợp theo chức năng vào src, không còn thư mục document theo cá nhân. Các báo cáo/CSV phân tán đã được hợp nhất; dữ liệu runtime và bản cũ lưu local. Trạng thái nghiên cứu/hoạt động con người chỉ được ghi hoàn tất khi có bằng chứng thật.

### Đầu ra nghiên cứu của midterm lần 1

Các đầu ra phần mềm dưới đây đã có trong bản midterm; bảng thể hiện phạm vi sở hữu để kiểm tra/bảo trì, không tự xác nhận nghiệm thu cá nhân. Giữ nguyên ba demo độc lập tuần 1; thí nghiệm nghiên cứu mới dùng input core được chỉ định tường minh.

| Hạng mục | Phạm vi phụ trách/phối hợp | Evidence cần bàn giao |
|---|---|---|
| Context/cutoff và provenance | Tâm phối hợp Thanh | Feature từ corpus/thread quan sát đến t; manifest/hash/identity scope |
| HeTCo-v0 và history/lag ablation | Thanh phối hợp Tâm/Trâm | Proposed prototype có đặc tả, predictions và A1/A4/A6 trên cùng nhãn/mẫu |
| B2/B5 và harder detection benchmark | Phúc phối hợp Trâm/Đăng | Matched model budget và regime schema-2; AMI/coverage/errors |
| Tracking/reference và paired evaluation | Đăng phối hợp Anh | Không trộn reference; matched keys, confusion và giới hạn bootstrap |
| Chạy baseline–proposed | Trâm phối hợp Thanh | Models/seeds/budget cố định, negative results và fallback |
| Experimental plan/evaluation/report | Anh phối hợp cả nhóm | Protocol, bảng điểm/support, notebook và trạng thái pending đúng thực tế |

Protocol nghiên cứu mới ở `configs/midterm.toml`, lịch thực thi ở `experiments/midterm_plan.toml`. HeTCo-v0 chỉ là prototype dự báo dựa feature context/history, không phải detector T/temporal/consensus hay bằng chứng HeTCo đầy đủ. Human annotation, unseen confirmation và novelty vẫn cần evidence riêng.
