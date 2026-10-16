# Contract dataset và bàn giao Phúc–Đăng v1

**Thiết kế v1:** 16/10/2026. Cụ thể hóa schema trong [phân công cặp](../../PHAN-CONG-PHUC-DANG-TUAN-1.md); chưa phải adapter đã triển khai. Specs 001–006 dùng chung contract này, không tạo biến thể riêng cho mỗi spec.

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
