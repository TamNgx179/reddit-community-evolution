# Phân công công việc SNA trong 8 tuần

**Đề tài:** How Online Communities Change Over Time.

**Thời gian:** 15/10–09/12/2026. Báo cáo tiến độ lần đầu vào **22/10/2026**, hoàn thành đầu ra tuần 1 trước tối 21/10. Các mốc sau là lịch nội bộ.

Mỗi người có nhiệm vụ riêng và cùng người trong cặp hoàn thành một đầu ra chung. Tâm–Thanh làm core, Phúc–Đăng làm detection/tracking đối chứng, Trâm–Anh làm dự báo/đánh giá. **Tuần 1, mỗi cặp triển khai và trình bày demo riêng cho ngày 22/10, không cần đầu ra từ cặp khác.** Baseline và mô hình phân tích cần có code chạy được, ghi rõ dùng dữ liệu thật hay giả lập. Từ tuần 2 mới ghép các đầu ra để so sánh trên cùng dữ liệu.

### Định hướng chất lượng theo rubric giảng viên

A1 thi lý thuyết 50%; A2 đồ án 50%. Điểm tối đa của đồ án đòi hỏi tiềm năng paper và quá trình tham gia. Nhóm định hướng nghiên cứu có phân tích SNA: tính mới cần kiểm chứng bằng related work; không xem source chạy được hoặc nhiều thuật toán là đủ.

Mỗi cặp ghi câu hỏi, đầu vào, protocol, đối chứng, kết quả và phần phản biện trong notebook demo thuộc thư mục của mình. Bản tổng hợp Midterm 1 nằm ở `notebooks/core/05_temporal_activity_study.ipynb` và `reports/WEEK1_REPORT.md`. Cấu hình thực chạy nằm trong `configs/`; danh sách thí nghiệm và hướng nghiên cứu tiếp theo được gom vào report, không tạo phụ thuộc output giữa các cặp tuần 1.

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
├── docs/                      # METHODS, RUNBOOK, RESULTS, LABEL_REVIEW
├── pyproject.toml              # Package và dependencies
├── .gitignore
├── configs/                    # Cấu hình runtime ba nhóm
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
└── reports/                    # Bảng claim/evidence và đóng góp dạng CSV
```

Source chia theo chức năng để dùng lại khi tích hợp; mỗi nhóm có pipeline, config và output riêng, không phụ thuộc artifact nhóm khác trong tuần 1. Mỗi nhóm có thể phát triển và demo bằng notebook riêng, chạy lại được từ kernel sạch theo thứ tự cell. Logic đã ổn định hoặc cần dùng lại chuyển vào src/reddit_sna; notebook import lại, không copy source. Demo notebook đủ input đến evaluation được chấp nhận trong phạm vi nhóm; CLI tiếp tục phục vụ tự động hóa và tích hợp. Thêm thuật toán vào module tương ứng, không tạo cây proposed/baseline hoặc thư mục source theo tên người. Tâm tạo repository, mời năm thành viên còn lại và hướng dẫn cài đặt. Theo quyết định công bố dữ liệu sau đó của chủ repo, 15 corpus gốc và processed lịch sử đã được đưa lên Git/LFS kèm checksum. Khóa riêng, bảng ánh xạ danh tính, `.venv`, artifact runtime và bộ mẫu chấm nhãn vẫn giữ local.

## 2. Ranh giới công việc và cách làm song song

- Trong tuần 1, từng cặp tự chuẩn bị dữ liệu mẫu và thống nhất giao diện nội bộ. Tâm và Thanh không cần cung cấp features/nhãn cho Trâm và Anh ở mốc này.
- Tâm–Thanh tự chạy core tối thiểu từ Reddit pilot đến đánh giá bằng detector và chỉ số thư viện. Phúc–Đăng tự sinh benchmark để chạy và đánh giá detection/tracking. Trâm–Anh tự tạo bảng community–tháng để chạy baseline và đánh giá. Mỗi cặp tự có đủ đầu vào và code cho demo của mình.
- Trong 19–21/10, mỗi cặp ghép, đánh giá và chạy lại demo của mình. Mỗi nhóm dùng thư mục code, cấu hình và output riêng, không ghi đè artifact của nhóm khác. Từ tuần 2 mới thống nhất schema và bàn giao để tích hợp chung.
- Fixture chỉ phục vụ phát triển và test, không được trình bày như kết quả Reddit. Khi chưa có artifact thật, vẫn hoàn thiện code bằng fixture.
- Người nhận báo lỗi qua issue, người sở hữu sửa module. Đổi schema cần thông báo và cập nhật phiên bản.
- Tuần 1 có ba demo riêng phục vụ 22/10, tuần 2 bàn giao và ghép thử, tuần 3 chạy pilot chung, tuần 4 hoàn thiện luồng chính. Người nhận tiếp tục test bằng fixture nếu bàn giao chậm. Không gọi demo giả lập là kết quả Reddit.

**Bảng bàn giao dưới đây áp dụng từ tuần 2, không phải phụ thuộc của tuần 1.** Trong tuần 1, slide và kết quả cũng do từng cặp tự chuẩn bị; Anh phụ trách phần của nhóm Trâm–Anh.

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

### Tuần 1 — 15–21/10: ba prototype độc lập, báo cáo ngày 22/10

Mỗi nhóm hoàn thành một prototype từ đầu vào riêng đến kết quả đánh giá. Mỗi người có công việc riêng và chỉ bàn giao kỹ thuật cho người cùng nhóm trong tuần 1. Không phải chờ hoặc sử dụng artifact của nhóm khác.

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
| **21/10** | Mỗi cặp chạy lại bằng cấu hình cố định vào thư mục output mới; hoàn thiện README, log và slide riêng. |
| **22/10** | Trình bày ba demo độc lập. Từng người giải thích nhiệm vụ, code, đầu ra và hạn chế của phần mình. |

#### Checklist nghiệm thu mỗi nhóm

- [ ] Có đầu vào xác định, nguồn dữ liệu và phạm vi được ghi rõ.
- [ ] Có code và cấu hình của cả hai người, ghép thành một lệnh hoặc chuỗi lệnh được ghi đầy đủ trong README.
- [ ] Chạy từ đầu vào của nhóm đến kết quả đánh giá mà không phải xin artifact từ nhóm khác hoặc nhập tay dự đoán để hoàn thành demo.
- [ ] Có bảng kết quả, kiểm tra phù hợp và ví dụ lỗi; phân biệt dữ liệu thật với tổng hợp.
- [ ] Lưu seed, phiên bản môi trường, cấu hình, log và output trong thư mục riêng của nhóm.
- [ ] Ghi rõ phần chưa hoàn thành, không coi sơ đồ hoặc code chưa chạy là prototype hoàn tất.


### Tuần 2 — 22–28/10: hoàn thiện module độc lập

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Hoàn thiện snapshot, R/T và dựng multislice trên fixture. Kiểm tra ID, trọng số và self-loop | R/T pilot, detector đề xuất bản đầu |
| **Thanh** | Củng cố GED/features/HeTCo từ demo tuần 1, bổ sung lịch sử và nhận community để ghép pilot thật | Core được kiểm thử, features mở rộng và bảng pilot |
| **Phúc** | Hoàn thiện Louvain/Independent Leiden và benchmark bản tối thiểu. Dựng B5 bằng thư viện có sẵn, thống nhất giao diện với Thanh/Trâm | Detector, benchmark và B5 chạy fixture |
| **Đăng** | Hoàn thiện Jaccard, kiểm tra snapshot. Viết test split thời gian và đặc trưng không dùng dữ liệu tương lai | Tracker đối chứng và test leakage |
| **Trâm** | Hoàn thiện B1/B4, viết chương trình chạy baseline và nhận B5 từ Phúc để chạy thử | Baseline cơ bản và chương trình chạy chung |
| **Anh** | Hoàn thiện macro-F1/confusion matrix, bảng kết quả và kiểm tra khóa mẫu bằng dữ liệu giả lập | Chỉ số cơ bản và mẫu báo cáo kết quả |

**Đầu ra chung:** Tâm–Thanh mở rộng core, Phúc–Đăng hoàn thiện đối chứng và kiểm tra kỹ thuật, Trâm–Anh hoàn thiện chương trình chạy baseline/báo cáo. B5 do Phúc bàn giao là đầu vào mới từ tuần 2, không ảnh hưởng tính độc lập của demo tuần 1.

**Bàn giao cuối tuần 2:** Phúc gửi benchmark/membership cho Tâm–Thanh và B5 cho Trâm. Thanh gửi features/nhãn cho Trâm, Đăng kiểm tra tính hợp lệ. Anh cung cấp chỉ số cơ bản và bảng kết quả, Đăng cung cấp test leakage. Chạy thử pilot sau thay đổi, chưa yêu cầu chạy hết corpus.

### Tuần 3 — 29/10–04/11: mở rộng pilot và phương pháp đề xuất

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy snapshot/multislice trên các tháng pilot liên tiếp, thêm consensus và đo tài nguyên | Community đề xuất pilot, thời gian/bộ nhớ |
| **Thanh** | Ghép GED, features và HeTCo. Kiểm tra lịch sử thành viên và thời điểm biết đặc trưng | Nhãn, features và dự đoán HeTCo pilot |
| **Phúc** | Chạy detector đối chứng, đánh giá AMI và triển khai B2 thích nghi bằng Random Forest. Bàn giao B2/B5 cùng cấu hình cho Trâm | Community đối chứng, B2/B5 và chất lượng detection |
| **Đăng** | Đánh giá Jaccard/GED, kiểm tra nhãn/mẫu mất khi ghép và test leakage trong pilot | Bảng lỗi tracking và kiểm tra tích hợp |
| **Trâm** | Chạy B1/B2/B4/B5 bằng chương trình đã có, kiểm tra file dự đoán và lưu cấu hình | Dự đoán baseline pilot |
| **Anh** | Tính chỉ số cơ bản từ dự đoán, vẽ bảng/biểu đồ và ghi phạm vi pilot | Báo cáo kết quả sơ bộ |

**Ghép việc tuần 3:** đầu tuần Tâm xuất pilot, Phúc tạo community đối chứng và Đăng kiểm tra snapshot. Giữa tuần Thanh bàn giao features/nhãn pilot để Trâm chạy baseline. Anh đánh giá dự đoán của Thanh và Trâm cuối tuần. Trong lúc chờ artifact, từng người tiếp tục test bằng fixture, không đổi phạm vi sở hữu.

### Tuần 4 — 05–11/11: mở rộng dữ liệu và chốt quy trình

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Hoàn thiện snapshot 45 tháng, kiểm tra tháng nặng và chọn cấu hình detector đề xuất trên benchmark/train | Manifest toàn kỳ và cấu hình detector |
| **Thanh** | Hoàn thiện GED/features/lịch sử, chọn ngưỡng tracking trên benchmark/train và hoàn thiện HeTCo | Nhãn/features phiên bản chính, core hoàn chỉnh |
| **Phúc** | Chọn cấu hình detector đối chứng, chạy B6 trên graph con, kiểm tra độ phân giải | Cấu hình đối chứng và kết quả B6 |
| **Đăng** | Chốt Jaccard, test sự kiện mơ hồ và triển khai bootstrap ghép cặp theo khối thời gian. Kiểm tra split và mẫu cuối kỳ thiếu nhãn | Tracker cố định, bộ đánh giá nâng cao |
| **Trâm** | Lập danh sách lượt chạy theo cấu hình đã chốt, kiểm tra kết quả thiếu/lỗi và quản lý bảng baseline | Lịch chạy và bảng kiểm tra baseline |
| **Anh** | Tổng hợp phân phối sáu lớp, số mẫu và mô tả protocol từ kiểm tra của Đăng | Bảng thống kê và phần protocol |

**Ghép việc tuần 4:** Tâm bàn giao snapshot theo tháng, Phúc bàn giao community đối chứng, Thanh xuất features/nhãn cho từng bộ tham chiếu. Đăng kiểm tra nhãn và phân phối lớp, Trâm–Anh kiểm tra bảng ghép và split. Cuối tuần chốt phiên bản dữ liệu, schema và protocol dùng cho thực nghiệm.

**Mốc tích hợp chính:** đủ snapshot, community, nhãn và features. Nếu quá nặng, dùng phạm vi định trước và ghi rõ giới hạn, không chọn phạm vi thuận lợi sau khi xem điểm.

### Tuần 5 — 12–18/11: chạy train/validation

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy detector đề xuất, hoàn thiện cờ bỏ thread/liên kết thời gian/consensus | Community chính và công tắc A2/A3/A5 |
| **Thanh** | Xuất nhãn/features, tinh chỉnh HeTCo và chuẩn bị hiệu chỉnh xác suất theo validation | Cấu hình HeTCo, kết quả validation |
| **Phúc** | Chạy Experiment 2, kiểm chứng H1. Chốt cách tinh chỉnh B2/B5 và xử lý mất cân bằng lớp với cùng ngân sách như HeTCo | Detection và cấu hình baseline nâng cao |
| **Đăng** | Kiểm chứng tracking, đối chiếu mẫu Reddit độc lập với Phúc. Chạy Experiment 3 trong train bằng baseline để kiểm chứng H2 | Báo cáo tracking, kết quả leakage |
| **Trâm** | Chạy lịch tinh chỉnh baseline đã thống nhất, lưu kết quả validation và chuẩn bị danh sách lượt chạy ablation | Kết quả validation và lịch ablation |
| **Anh** | Tổng hợp kết quả validation/leakage, vẽ biểu đồ và viết phần tiến độ/hạn chế | Bảng biểu và báo cáo cập nhật |

**Ghép việc tuần 5:** Thanh cung cấp features cho Trâm, Phúc chốt cấu hình B2/B5, Trâm thực hiện các lượt chạy. Đăng kiểm tra leakage bằng baseline, không cần đợi HeTCo tinh chỉnh xong. Thanh và Phúc thống nhất ngân sách, Đăng kiểm tra tính công bằng, Anh tổng hợp bảng kết quả đã xác nhận.

### Tuần 6 — 19–25/11: khóa cấu hình và đánh giá test

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Khóa detector, xuất community test chỉ từ cửa sổ quá khứ, lưu phiên bản pipeline | Community test đề xuất và manifest |
| **Thanh** | Xuất features/nhãn đúng thời điểm, khóa HeTCo rồi chạy test | Dự đoán HeTCo và cấu hình đã khóa |
| **Phúc** | Xuất community Independent Leiden với cấu hình đã chốt, kiểm tra cấu hình B2/B5 và xử lý lỗi triển khai khi Trâm chạy | Community tham chiếu thay thế và baseline được kiểm tra |
| **Đăng** | Kiểm tra nhãn test, xuất Jaccard riêng và tính khoảng tin cậy/chênh lệch HeTCo–B5 bằng bootstrap | Nhãn đối chứng và kết quả đánh giá nâng cao |
| **Trâm** | Khóa baseline, chạy B1/B2/B4/B5 trên cùng mẫu/nhãn với HeTCo | Dự đoán baseline test |
| **Anh** | Tính chỉ số cơ bản từng lớp/tháng, ghép khoảng tin cậy do Đăng xuất và vẽ bảng/biểu đồ | Bảng Experiment 4 và trình bày kết quả H3 |

**Ghép việc tuần 6:** Tâm/Phúc xuất community, Thanh xuất features/nhãn, Đăng kiểm tra nhãn. Thanh và Trâm chạy mô hình, Đăng tính đánh giá nâng cao, Anh tổng hợp chỉ số và bảng biểu. Phúc xử lý lỗi B2/B5, không yêu cầu Trâm sửa thuật toán. Khóa cấu hình trước test.

Không học lại từ nhãn test hoặc đổi ngưỡng theo kết quả test. Nhãn tháng kế tiếp chỉ dùng đánh giá. Mẫu cuối corpus không có nhãn kế tiếp được loại khỏi dự báo và ghi rõ số lượng.

### Tuần 7 — 26/11–02/12: ablation và độ nhạy

| Người | Công việc | Đầu ra |
|---|---|---|
| **Tâm** | Chạy A2/A3/A5 bằng detector đề xuất, đo tài nguyên và kiểm tra tái lập | Artifact ablation detection và chi phí |
| **Thanh** | Chạy HeTCo A1/A4/A6, tạo features cho community/nhãn thay thế | Dự đoán ablation, features tham chiếu riêng |
| **Phúc** | Đánh giá AMI/sự kiện benchmark của A2/A3/A5, chạy độ phân giải A7 và hỗ trợ kỹ thuật B2/B5 trên bộ nhãn thay thế | Ablation phân hoạch và đối chứng dự báo hợp lệ |
| **Đăng** | Chạy tracker A7/B3, phân tích sai khác GED–Jaccard và độ nhạy khoảng tin cậy | Bộ nhãn thay thế, sai khác tracking và độ bất định |
| **Trâm** | Chạy baseline trên các bộ tham chiếu thay thế, so sánh ablation với HeTCo | Kết quả đối chứng/ablation dự báo |
| **Anh** | Tổng hợp Experiment 5 từ artifact đã kiểm tra, vẽ biểu đồ và viết kết luận H1–H3 để người phụ trách xác nhận | Bảng tổng hợp, biểu đồ và dự thảo kết luận |

A1/A4/A6 giữ cùng mẫu/nhãn. A2/A3/A5 chủ yếu đánh giá detection/tracking. Nếu dự báo với phân hoạch mới, Thanh và Trâm chạy lại HeTCo/baseline trên cùng nhãn mới, Anh báo cáo riêng từng bộ tham chiếu.

**Ghép việc tuần 7:** Tâm gửi phân hoạch cho Thanh, Phúc đánh giá detection và hỗ trợ kỹ thuật baseline. Đăng gửi nhãn Jaccard cho Thanh, nhận dự đoán của Thanh/Trâm để tính khoảng tin cậy. Anh nhận kết quả đã kiểm tra để tổng hợp riêng từng bộ nhãn. Chạy A1/A4/A6 song song với kiểm tra phân hoạch.

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

- Mỗi người cập nhật việc đã làm, đường dẫn code/artifact, lỗi và kế hoạch tiếp theo trong thư mục mang tên mình.
- Hoàn thành nghĩa là có đầu ra kiểm tra được, lệnh chạy và test phù hợp. Phân biệt kết quả fixture, pilot và toàn kỳ.
- Tâm–Thanh, Phúc–Đăng, Trâm–Anh review trong từng cặp trước khi merge. Review không chuyển quyền sở hữu module.
- Anh tổng hợp nội dung đã được từng người xác nhận, không viết thay mọi người. Tâm điều phối tích hợp, không chịu trách nhiệm sửa mọi module.
- Khi quá tải, giảm B6 hoặc độ nhạy mở rộng trước. Giữ dữ liệu hợp lệ, tracking được kiểm chứng, B5–HeTCo và A1/A4. Không bỏ kiểm tra leakage, tinh chỉnh theo test hoặc tạo kết quả cho đủ bảng.

### Checklist trước báo cáo 22/10

- [x] **Tâm:** đã chuẩn bị sẵn bộ dataset Reddit gồm 15 corpus và các script xử lý ban đầu.
- [ ] **Tâm:** tạo repo GitHub, mời thành viên, dựng cấu trúc thư mục, .gitignore, môi trường/thư viện và README hướng dẫn cộng tác/chạy demo; có manifest, snapshot Reddit pilot và membership tạm của nhóm core.
- [ ] **Thanh:** tracking/features/nhãn, mô hình cơ bản và kết quả đánh giá trên pilot của nhóm Tâm–Thanh.
- [ ] **Phúc:** benchmark mạng động có phân hoạch chuẩn, Independent Leiden và bảng AMI.
- [ ] **Đăng:** Jaccard, kiểm chứng sáu sự kiện, bảng điểm và confusion matrix trên benchmark của Phúc–Đăng.
- [ ] **Trâm:** bảng community–tháng tổng hợp, code baseline và dự đoán B1/B4.
- [ ] **Anh:** split thời gian, bộ đánh giá, bảng điểm/confusion matrix và phần trình bày của nhóm Trâm–Anh.
- [ ] **Từng cặp:** chạy từ input riêng đến evaluation results, có README/lệnh chạy, cấu hình, log và output riêng; không cần artifact từ nhóm khác.
- [ ] **Từng người:** trình bày code và đầu ra phụ trách; ghi rõ dữ liệu thật/giả lập, phần chưa hoàn thành và chưa dùng test chính thức.

Ba prototype độc lập là đầu ra tuần 1. Pipeline Reddit tích hợp toàn project tiếp tục từ tuần 2; điểm trên dữ liệu tổng hợp chỉ dùng kiểm chứng module, không thay thế kết quả Reddit.

## Nghiệm thu prototype core tuần 1 — cập nhật 17/10

- [x] Tâm: audit/manifest, snapshot R và Independent Leiden trên Reddit thật; giao diện membership được forecast tiêu thụ.
- [x] Thanh: Jaccard/GED thích nghi, features/nhãn, split theo tháng nhãn, Majority/Logistic Regression, predictions và evaluation.
- [x] Kiểm chứng độc lập tại main aa110ac: 148/148 tests pass; forecast thật tái lập đúng báo cáo; model lưu ra dự đoán lại đúng file predictions.
- [x] Chủ repo xác nhận đã mời đủ năm thành viên; việc nhận lời mời/quyền thực tế chưa được audit độc lập.
- [x] Bản bàn giao mới được chạy xác nhận: raw → evaluation thành công; 161/161 tests pass không skip; hai notebook 10/10 và 7/7 cell, tổng 20 biểu đồ; bộ review có 31 trường hợp với 62 hàng chấm trống. Chi tiết ở `docs/RESULTS.md#final-delivery-verification`.
- [ ] Hai người rà soát nhãn độc lập và xử lý bất đồng; bộ mẫu được chuẩn bị không đồng nghĩa nhãn đã được xác nhận.
- [ ] Xác nhận kỳ đánh giá tiếp theo chưa từng xem, khóa protocol trước khi chạy; không dùng điểm 2015 như test xác nhận mới.
- [ ] Nhóm tập trình bày, đi học và báo cáo ngày 22/10; dàn ý slide không phải bằng chứng đã thuyết trình.

Lệnh demo và nội dung trình bày ở `docs/RUNBOOK.md` và `docs/RESULTS.md#presentation-outline`. Các hạn chế về ground truth, lớp thiếu và coverage phải được trình bày cùng điểm số. HeTCo đầy đủ và detector đề xuất thuộc các tuần sau, không phải thiếu sót bắt buộc của baseline tuần 1.

## Cập nhật 28/10 — trạng thái HeTCo và chia phần việc còn lại

**Đã xong (Thanh, nhánh `feat/hetco-v1`):** HeTCo_v1 (attention trên thành viên) và HeTCo_v2 (trọng số lớp và head phân cấp, chọn cấu hình trên các tháng 07–09). Có ablation A1/A4/A6/A7, bootstrap theo khối tháng và theo community, test, hình trong `reports/figures/hetco-v*`. Chi tiết ở `docs/RESULTS.md#hetco-v1-development-comparison`.

**Kết quả hiện tại:** trên main window 2015-10..12, HeTCo_v2 đạt macro-F1 0.365, B4 đạt 0.361. Theo tiêu chí của giảng viên (phương pháp đề xuất phải ≥ baseline), v2 đã đạt. Tuy nhiên chênh lệch là +0.005 với khoảng tin cậy [−0.06, +0.07], nên chỉ được trình bày là **ngang B4**, không phải thắng. Attention chưa tốt hơn lấy trung bình. Ý tưởng của v2 xuất phát từ việc xem lỗi trên tập test 2015, nên cần kiểm định lại trên giai đoạn chưa xem.

**Phần còn lại, mỗi người 2 việc, giữ đúng phạm vi sở hữu:**

| Người | Việc | Hạn |
|---|---|---|
| **Tâm** | (1) Chuẩn bị giai đoạn đánh giá chưa xem cho HeTCo: cohort 2018 trong `configs/prospective.toml`, hoặc các tháng 2016 nếu dữ liệu đủ. Gồm snapshot, membership và preparation. (2) Tích hợp `hetco` vào `temporal-study` để so HeTCo với proposed hierarchical LR trên cùng mẫu, đồng thời review PR `feat/hetco-v1`. | 04/11 |
| **Thanh** | (1) Sửa tenure bị cắt trái bằng cách dùng các tháng đầu làm lịch sử, và khai báo trước một biến thể attention ghép trung bình; chọn bằng các tháng 07–09, không nhìn test. (2) Khóa cấu hình v2 (file config có hash, commit trước khi chạy) rồi chạy một lần trên giai đoạn chưa xem của Tâm. Thắng hay thua đều báo cáo nguyên kết quả. | 11/11 |
| **Phúc** | (1) Chạy B2/B5 trên giai đoạn chưa xem với cấu hình đã khóa và cùng mẫu với HeTCo. (2) Đo thời gian và bộ nhớ của `hetco` (khoảng 10 phút trên pilot 2015) và đề xuất giới hạn khi chạy nhiều corpus hơn. | 11/11 |
| **Đăng** | (1) Test leakage cho `features/members.py`: xác nhận không đọc bản ghi sau t, membership t+1 hay nhãn. Kiểm tra nhãn ở lớp hiếm grow/merge. (2) Đối chiếu bootstrap theo community (`community_delta`) với bootstrap theo khối tháng, và ghi rõ giới hạn khi phụ thuộc trong cùng tháng. | 11/11 |
| **Trâm** | (1) Chạy B1/B4 trên giai đoạn chưa xem, cùng mẫu và cấu hình đã khóa. (2) Lập bảng so sánh B1/B2/B4/B5/HeTCo_v2 theo từng lớp; B4 là baseline mạnh nhất cần vượt. | 11/11 |
| **Anh** | (1) Đánh giá độc lập predictions HeTCo, gồm `artifacts/hetco/hetco-v2-001/predictions.csv` và bản chạy trên giai đoạn chưa xem; tính lại macro-F1 và confusion bằng code của mình. (2) Đưa phần HeTCo vào report và slide, ghi đúng "ngang B4 trên dữ liệu phát triển" kèm các giới hạn. | 18/11 |

**Quy tắc:** không chỉnh cấu hình HeTCo sau khi đã xem điểm trên giai đoạn chưa xem. Mọi mô hình dùng cùng mẫu, cùng nhãn và cùng seed. Nếu HeTCo thấp hơn B4 trên giai đoạn mới thì vẫn báo cáo, đồng thời phân tích lỗi theo lớp.
