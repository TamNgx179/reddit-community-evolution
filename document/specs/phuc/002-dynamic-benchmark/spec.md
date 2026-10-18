# PHUC-002 — Sinh benchmark mạng động sáu sự kiện

**Owner:** Phúc. **Thiết kế:** v1, 16/10/2026. **Phân công:** P02, P05.
**Tiến độ, hạn và bằng chứng:** [tasks.md](../tasks.md#phuc-002). **Giao diện:** [contracts.md](../contracts.md).

## Mục tiêu và user story

**US1, P1:** Là người chạy detection, tôi có graph theo tháng và ground truth đã biết để đo khả năng khôi phục cộng đồng, không dùng subreddit làm đáp án.

Có thể bắt đầu với stable seed 11; nghiệm thu toàn spec cần sáu case, không bắt đầu bằng toàn bộ corpus Reddit.

## Yêu cầu

- **PHUC-002-FR01:** Sinh cạnh vô hướng theo seed và `p_in/p_out` cấu hình; không dùng detector hoặc điểm evaluation để quyết định truth/cạnh.
- **PHUC-002-FR02:** R không có self-loop/cạnh trùng, weight hợp lệ; `nodes.csv` giữ mọi node hoạt động, gồm isolate.
- **PHUC-002-FR03:** Hỗ trợ stable/grow/shrink/merge/split/dissolve và K; biến đổi thành viên đúng contract, events/links chuẩn tương ứng.
- **PHUC-002-FR04:** Thứ tự user/cạnh cố định, config/seed/observed months/identity scope/hashes được lưu; từ chối ghi đè hoặc input không hợp lệ.
- **PHUC-002-FR05:** Development và evaluation có dataset/seed riêng; kiểm tra generator bằng case dễ và ít nhất một diagnostic nhóm nhỏ/isolate để nêu giới hạn.

## Điều kiện chấp nhận

| ID | Given / When / Then |
|---|---|
| AC01 | Cùng config/seed, hai output mới có cùng dữ liệu graph/truth; không phụ thuộc thứ tự set/dict tùy ý |
| AC02 | Với sáu case, tất cả nguồn chuẩn gồm K có event/link đúng thiết kế; merge/split bảo toàn các tập thành viên đã định |
| AC03 | Với p_in=p_out=0 ở diagnostic, R có header nhưng không cạnh, nodes và truth vẫn giữ user hoạt động |
| AC04 | Với xác suất ngoài [0,1], cạnh/user/tháng sai hoặc output đã tồn tại, báo lỗi trước khi ghi đè dữ liệu |
| AC05 | Lịch generator seed development/evaluation không trùng; isolate được báo, không tự thêm cạnh hoặc đổi seed vì điểm thấp |

## Phụ thuộc và ngoài phạm vi

Nghiệm thu dựa trên schema/truth của 001. Không cần tracker, Leiden hoặc AMI để xác định generator đúng. Chưa yêu cầu benchmark quy mô lớn, temporal detector, bảo đảm mọi nhóm được Leiden khôi phục hoặc kết quả AMI cao.

## Output và kiểm chứng độc lập

- Module: `benchmarks/dynamic.py`, cấu hình `configs/benchmark_week1.json`; dùng lại scenarios/io từ 001.
- Artifact: `snapshots/<month>/{R,nodes}.csv`, truth và metadata theo dataset; trường hợp diagnostic đánh dấu riêng.
- Test: `tests/unit/test_dynamic_benchmark.py`, kiểm tra invariants/tái lập/nhóm nhỏ/isolate và lịch dataset.
- Evidence: config, seed, số node/cạnh/nhóm/tháng của từng case, hash hoặc lệnh đối chiếu hai lần sinh. Báo diagnostic không phải kết quả Reddit.
- [Hướng dẫn sampler stable hiện có](README.md) và [bằng chứng T01](../evidence/PHUC-002-T01-stable-graphs.md) ghi bước đầu; chưa đại diện cho nghiệm thu toàn bộ sáu case của spec.
- [Bằng chứng T02](../evidence/PHUC-002-T02-six-event-truth.md) xác minh membership/events/links đủ sáu case trong bộ nhớ; export graph/metadata và lịch evaluation vẫn thuộc các task sau.
- [Bằng chứng T03](../evidence/PHUC-002-T03-benchmark-config.md) ghi JSON chung, validator/lịch split và mẫu sampler từ config. Lịch evaluation được khai báo; chạy/freeze evaluation vẫn thuộc PHUC-005.
- [Bằng chứng T04](../evidence/PHUC-002-T04-graph-export.md) ghi exporter graph/truth sáu case, config/metadata/hashes, đọc lại/tái lập và giữ output cũ. Đây là kiểm chứng exporter ở development seed 11; suite generator T05 và nghiệm thu development/diagnostic T06 vẫn riêng.
- [Bằng chứng T05](../evidence/PHUC-002-T05-generator-tests.md) ghi suite generator 18 test, tổng 100 test liên quan, bốn fixture tiny version riêng và hai bộ diagnostic CSV đã lưu. T06 vẫn nghiệm thu lượt development và báo cáo đầy đủ.
- [Bằng chứng T06](../evidence/PHUC-002-T06-development.md) nghiệm thu AC01–05: hai full development run 18 dataset/36 snapshot, khớp 162 file, 36 lần đọc độc lập, diagnostic/báo cáo CSV/ZIP đã lưu và 105 test pass. Hoàn thành generator; chưa chạy detection/tracking/evaluation.
