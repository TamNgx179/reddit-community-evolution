# Bàn giao demo Phúc–Đăng — 20/10/2026

**Đã hoàn thành bản bàn giao kỹ thuật.** Source tracker/evaluator Đăng từ PR #12 đã được merge vào nhánh `feat/phuc-006-handoff-demo`. Notebook chính hiện có cả detection và hai đường tracking, đã chạy thành công **14/14 code cell, 8 hình**. Code tích hợp: `89173ce`; phần thuật toán Jaccard, membership và evaluator giữ nguyên commit Đăng.

## Bạn cần giao gì?

Code, notebook nguồn và hướng dẫn ở nhánh hiện tại, [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11). [Guide chạy đầy đủ](guide.md) có lệnh test, batch hai split và chạy notebook bằng kernel mới.

**Gói output kết quả demo trên máy Phúc:**

```text
artifacts/handoff/phuc-dang-demo-results-20261020-001.zip
artifacts/handoff/phuc-dang-demo-results-20261020-001.zip.sha256
```

Gói **692 file, 2.882.422 byte**, SHA-256:

```text
ffbcde13b5a52748b3a9e789a33bf85fdbee3967c3b6fa144b96e33e072c3b97
```

Giải nén rồi mở **`REPORT.html`** để đọc bảng/hình ngay. Có notebook đã chạy, đầy đủ output hai split, cấu hình/provenance, CSV/PNG/SVG, log test và source runtime snapshot. `manifest.json` ghi hash/kích thước mọi payload; ZIP đã kiểm tra CRC và byte từng entry.

**Đây là gói kết quả cuối để bàn giao nhóm, không thay ZIP input T02 Đăng đã nhận.** Input cũ giữ nguyên, không yêu cầu Đăng tải lại dữ liệu hoặc làm lại tracker. Các file `artifacts/` vẫn local, chưa tự gửi/upload lên GitHub hay nhắn thay người dùng.

## Hai người đã hoàn thành gì?

- **Phúc:** sinh sáu kịch bản graph có ground truth, lưu seed/config, chạy Independent Leiden từng tháng và đánh giá AMI/coverage; hoàn tất 36/36 task cá nhân.
- **Đăng:** adapter membership nhiều tháng, Jaccard tracker/sáu sự kiện, greedy source mapping, evaluator event metrics và test thuật toán; giữ nguyên tác giả/commit khi tích hợp.
- **Tích hợp Phúc:** kiểm tra input hashes trước batch, xuất config/provenance/diagnostics, truth confusion 6×6 và detector 6×7, bảng gộp giữ đúng khóa, notebook chính, HTML và gói kết quả.

Hai đường có trong notebook:

```text
Truth membership → tracker → đối chiếu truth events/links
Graph → Leiden seed 0 đã lưu → tracker → source mapping → đối chiếu truth events
```

Không chạy lại generator/Leiden/AMI và không đổi ngưỡng theo evaluation trong lần tích hợp này. Tracker giữ Jaccard 0,30, size tolerance 0,10, split trước merge.

## Kết quả đã chạy

| Chỉ số | Development | Evaluation |
|---|---:|---:|
| Dataset | 18/18 | 18/18 |
| Truth events/links khớp | 18/18 | 18/18 |
| Truth pooled macro-F1 | 1,0 | 1,0 |
| Detector mean dataset macro-F1 | 0,2561728395 | 0,2175925926 |
| Detector pooled macro-F1 | **0,85** | **0,6551425990** |
| Detector event đúng | 33/39 | 28/39 |
| Matched coverage | 1,0 | 1,0 |
| Unmatched truth | 0 | 0 |
| Detector community dư | 3 | 6 |

Mỗi split có đủ 39 nguồn truth, gồm K, support sáu nhãn 21/3/3/6/3/3. **Mean dataset và pooled dùng hai cách tổng hợp**, cùng giữ trong báo cáo; không thay số Đăng báo bằng số gộp. Coverage mapping 1,0 không có nghĩa dự đoán sự kiện đúng.

## Bằng chứng và đường dẫn local

```text
artifacts/detection-tracking/phuc-dang-final-20261020-001/
    development/                      # 292 files, 18 datasets
    evaluation/                       # 292 files, 18 datasets
    tracking-index.json

artifacts/detection-tracking/phuc-dang-demo-20261020-002/
artifacts/detection-tracking/phuc-dang-demo-20261020-002-cases/
artifacts/detection-tracking/phuc-dang-demo-20261020-002-tracking/

artifacts/verification/phuc-dang-final-20261020-001/
    tracking-tests.log                # 20/20, gồm 11 test Đăng + 9 test tích hợp
    regression-tests.log              # 74/74
    notebook-final/
        01_synthetic_demo.executed.ipynb
        notebook-result.json          # 14 cells/8 PNG, 66,753 giây
    PR12-output-comparison.csv         # 468 file tương thích giống từng byte
    delivery-result.json
    package-verification.json
```

94/94 test liên quan đạt, không skip/failure/error. Full repo gate 385/385 thuộc T05 lịch sử, không gọi đó là một lần chạy mới. Lượt notebook đầu đạt 14/8; sau đó bổ sung cell IDs chuẩn định dạng và chạy lại kernel mới, lượt cuối đạt 14/8. Predictions/events/links/metrics/mapping và các payload tương thích giữ byte so với run PR12 chưa sửa; khác biệt có chủ đích là schema truth confusion, config/provenance và tracker diagnostics được bổ sung.

Reference và số liệu nhỏ trên Git: [delivery reference](specs/phuc/evidence/PHUC-DANG-final-delivery.json), [tracking summary](specs/phuc/evidence/PHUC-DANG-final-summary.csv), [chỉ số từng lớp](specs/phuc/evidence/PHUC-DANG-final-per-class.csv), [trường hợp sai](specs/phuc/evidence/PHUC-DANG-final-errors.csv).

## Giới hạn còn ghi riêng

Hai artifact gốc `dang-week1-development-001` và `dang-week1-evaluation-001`, cùng freeze lịch sử của Đăng chưa được đối chiếu ở máy Phúc. Bản giao hiện tại sử dụng output **Phúc tái lập minh bạch từ code Đăng**, có source hashes/config/provenance của lần chạy này; không tạo chứng cứ freeze hồi tố hoặc tuyên bố evaluation độc lập mới.

Điều đó không chặn việc giao và xem demo kỹ thuật đã chạy. Phần nghiệm thu trực tiếp của hai thành viên vẫn chưa được ghi nhận, tách khỏi kết quả chạy tự động. Các kết quả này là benchmark tổng hợp, chưa phải forecasting hay kết luận trên Reddit thật.

Tin nhắn gửi nhóm/Đăng có thể dùng:

> Ông ơi, tui ghép xong tracker vào notebook chính rồi nha. PR #12 của ông đã vào nhánh `feat/phuc-006-handoff-demo`, tui push cả guide và kết quả kiểm tra lên rồi. Demo chạy đủ 14 cell/8 hình, hai split đều 18/18. Tui có bản báo cáo HTML với gói kết quả cuối để bàn giao; ZIP dữ liệu cũ vẫn giữ nguyên, ông không cần làm lại gì nha. Output demo này tui tái chạy từ code ông, có ghi rõ nguồn; hai bộ output gốc của ông mình bổ sung đối chiếu sau cũng được.
