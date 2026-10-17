# Tạo và đọc fixture truth stable/grow

Đây là đầu ra PHUC-001-T06 để Đăng kiểm tra tracker trực tiếp trên membership chuẩn. Dữ liệu tổng hợp gồm hai tháng và nhóm nền K; community chính đổi tên A→C. Export chạy bằng code Python, tách khỏi notebook.

## 1. Chuẩn bị và tạo gói

Chạy từ root repo trên nhánh `feat/phuc-001-ground-truth-events`, dùng Python 3.11 trở lên. Project của Phúc đã có `.venv` Python 3.12.6. Máy khác cần môi trường Python và cài package từ checkout này:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e .
```

Tạo gói vào run mới:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.fixtures --config configs/truth_fixtures.toml --run-id my-truth-001
```

- [Config](../../../../configs/truth_fixtures.toml) dùng generator seed 11, dữ liệu development; API mặc định hai tháng `2020-01`, `2020-02`. Có thể truyền `--start-month 2020-12` để kiểm tra đổi năm.
- Mỗi lần chạy chọn `--run-id` mới. Run đã tồn tại bị từ chối, kể cả thư mục rỗng; không có chế độ ghi đè/resume.
- Seed được lưu trong metadata với `seed_used_for_truth=false`: membership, events và links hiện cố định theo kịch bản. Seed được giữ để dùng cho graph ở bước sau.
- Export chỉ dùng package project và thư viện chuẩn Python. Phần này tạo truth; graph, detector, AMI và kết quả tracker thuộc các bước sau.

## 2. Cấu trúc output

```text
artifacts/detection-tracking/my-truth-001/
  manifest.json
  datasets/
    dev-stable-easy-g11/
      metadata.json
      snapshots/2020-01/nodes.csv
      snapshots/2020-02/nodes.csv
      truth/membership.csv
      truth/events.csv
      truth/links.csv
    dev-grow-easy-g11/
      ... cùng cấu trúc
```

Mỗi `metadata.json` ghi schema/version, dataset/scenario/split/difficulty, identity scope, truth reference, tháng quan sát, cấu hình/seed generator, phiên bản Python/package, counts và SHA-256 năm CSV. Metadata được ghi sau khi CSV đã đọc lại đúng.

Manifest run có `scope="truth-fixtures"`, `completed_stages=["truth"]` và hash cả 12 file dataset. `status="complete"` chỉ xác nhận bước truth của gói này. Nếu export lỗi sau khi tạo run, manifest ghi `failed`, giữ nguyên file đã tạo để kiểm tra; lần chạy tiếp dùng run ID mới.

## 3. Đọc độc lập để dùng cho tracker

[scripts/read_truth_fixture.py](../../../../scripts/read_truth_fixture.py) chỉ dùng thư viện chuẩn Python; có thể copy script cùng thư mục dataset sang máy khác. Ví dụ với gói vừa sinh:

```powershell
& .\.venv\Scripts\python.exe -I scripts/read_truth_fixture.py artifacts/detection-tracking/my-truth-001/datasets/dev-stable-easy-g11
& .\.venv\Scripts\python.exe -I scripts/read_truth_fixture.py artifacts/detection-tracking/my-truth-001/datasets/dev-grow-easy-g11
```

`-I` chạy Python isolated. Script không import `reddit_sna`. Thành công trả exit code 0, JSON có `verified: true`, counts, số thành viên từng nhóm và nội dung events/links. Sai hash/schema/coverage/truth trả exit code 2 và thông báo ở stderr; script không sửa file.

| Dataset | Node tháng đầu → tháng sau | Membership cả hai tháng | Nhãn nguồn A / K | Liên kết |
|---|---|---|---|---|
| `dev-stable-easy-g11` | 24 → 24 | 48 | stable / stable | A→C, K→K |
| `dev-grow-easy-g11` | 24 → 30 | 54 | grow / stable | A→C, K→K |

Header/khóa theo [contracts.md](../contracts.md). `reference_id` là `truth-<dataset_id>`. Mỗi nguồn tháng đầu có một event; tháng cuối có membership nhưng không có nhãn nguồn vì thiếu tháng kế tiếp.

Đăng dùng `truth/membership.csv` làm đầu vào tracker, rồi đối chiếu predictions với `truth/events.csv` và `truth/links.csv`. Nhãn chuẩn được sinh từ thiết kế, độc lập với thuật toán tracking.

## 4. Gói đã kiểm tra trên máy Phúc

- `artifacts/detection-tracking/phuc-001-t06-001/`: gói chính gồm hai dataset seed 11.
- `artifacts/detection-tracking/phuc-001-t06-002/`: gói đối chiếu tái lập, cả 12 file dataset bằng byte với gói chính.
- [Bằng chứng T06](../evidence/PHUC-001-T06-export.md): lệnh thực tế, kết quả test/reader, hashes và giới hạn.

`artifacts/` bị Git ignore. Thành viên khác lấy code/config/script đã push rồi chạy lệnh ở mục 1, hoặc nhận nguyên thư mục dataset và script được chia sẻ riêng. Các đường dẫn local trên máy Phúc không tự xuất hiện khi pull Git.

Phúc đã tự xác minh gói đọc được; xác nhận Đăng thực sự nhận/đọc gói được ghi riêng tại EXT-D01 khi có phản hồi.
