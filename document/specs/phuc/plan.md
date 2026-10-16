# Plan triển khai sáu spec của Phúc

**Nguồn yêu cầu:** sáu `spec.md`. **Tiến độ/hạn/bằng chứng:** chỉ cập nhật ở [tasks.md](tasks.md). **Giao diện:** [contracts.md](contracts.md).

## 1. Luồng tối thiểu tối 16/10

Không cố làm xong toàn bộ từng spec mới chuyển bước. Làm một lát nhỏ xuyên suốt:

1. PHUC-001-T01: kiểm tra/cài môi trường theo interpreter project, chạy test Leiden hiện có.
2. PHUC-001-T02 và T03: tạo truth stable/grow, validator/adapter và bộ CSV bàn giao ban đầu.
3. PHUC-002-T01: sinh graph stable hai tháng, seed generator 11.
4. PHUC-003-T01: dùng detector có sẵn, gamma 1, seed detector 0.
5. PHUC-004-T01 đến T03: căn user, báo coverage, tính AMI và lưu một bảng nhỏ.
6. Lưu output mới và ghi task nào đã chạy/chưa chạy. Giao truth cho Đăng ngay khi có, không cần đợi bước 5.

Mốc dừng tối nay: truth stable/grow đã xuất và ít nhất stable chạy từ graph đến AMI đúng. Nếu còn thời gian, chạy cùng luồng cho grow. Chưa cần suite đủ 216 hàng, hình đẹp hoặc tracker.

## 2. Thứ tự hoàn thiện sau luồng nhỏ

| Giai đoạn | Đầu vào | Đầu ra kiểm tra được |
|---|---|---|
| Truth và graph | Cấu hình v1 | Sáu case với membership/events/links chuẩn và R/nodes |
| Detection | Snapshot đã kiểm tra | Seed 0/1/2, reference và diagnostics |
| Evaluation | Truth + detector cùng dataset | AMI/coverage/size/timing, kiểm tra dữ liệu thiếu |
| Runs | Lịch development/evaluation tách riêng | Manifest, config khóa, bảng chi tiết và tổng hợp |
| Handoff | Output detection đã xác minh | Gói bàn giao và notebook từ kernel sạch |
| Ghép chung | Thêm tracker/evaluator của Đăng | Hai nhánh đánh giá riêng và toàn luồng, ghi xác nhận người nhận |

## 3. Source dự kiến và quyền sửa

| Đường dẫn dự kiến | Nội dung | Owner |
|---|---|---|
| `src/reddit_sna/benchmarks/scenarios.py` | Tập thành viên, truth và quy tắc sinh sáu case | Phúc |
| `src/reddit_sna/benchmarks/io.py` | Đọc/ghi/kiểm tra contract dataset tổng hợp | Phúc |
| `src/reddit_sna/benchmarks/dynamic.py` | Sinh cạnh ngẫu nhiên có seed | Phúc |
| `src/reddit_sna/evaluation/detection.py` | Căn user, AMI, coverage và tổng hợp | Phúc |
| `src/reddit_sna/reporting/synthetic_handoff.py` | Consumer độc lập kiểm tra gói CSV/JSON tổng hợp | Phúc |
| `src/reddit_sna/pipelines/detection_tracking.py` | API chạy riêng detection, sau đó ghép tracker khi đã có | Phúc giữ đầu mối |
| `configs/benchmark_week1.json` | Lịch case, seed, probabilities, gamma và protocol | Phúc |
| `notebooks/detection_tracking/01_synthetic_demo.ipynb` | Gọi API, xem kết quả và export có nguồn | Phúc ghép, Đăng cung cấp phần tracking |
| `src/reddit_sna/tracking/jaccard.py`, `evaluation/tracking.py` | Tracker, mapping, F1 sự kiện | Đăng; không thuộc task triển khai Phúc |

Các file mới là đường dẫn thiết kế, chưa được tạo ngoài các tài liệu spec. Tách module chỉ khi có logic thực tế. Không cần tạo stub hàng loạt. Có thể điều chỉnh tên module trước triển khai nếu cập nhật task/contract liên quan.

## 4. Cách triển khai phù hợp code hiện tại

- Giữ Python 3.11+, package layout hiện có; không sửa `sys.path` trong notebook.
- Tái sử dụng `Membership`, `SnapshotEdge`, `Event`, `detect_snapshots`, `write_csv` và quản lý output hiện có khi phù hợp.
- Dataset tổng hợp có protocol riêng, `R.csv` đúng header hiện hành; không tuyên bố là artifact reply Reddit v3.
- Code algorithm không import CLI/pipeline. Notebook/pipeline import module chức năng.
- TOML parser hiện strict. JSON benchmark được đọc rõ ràng bởi API/notebook và lưu bản sao; không thêm khóa TOML lạ để lách parser.
- Bổ sung dependency tính AMI trong `pyproject.toml` khi evaluator thực sự dùng; record phiên bản môi trường.
- Run detection độc lập có completion riêng. Giữ full `run` chưa hoàn thành nếu tracker chưa có; không báo thành công toàn luồng vì mới có membership.
- Output chọn thư mục mới; manifest `started/failed/complete` phản ánh thật, hash config/source/output, peak memory null nếu chưa đo.

## 5. Kiểm tra theo rủi ro

- Truth: các tập hợp thành viên, sự kiện, nhóm nền và successor đúng; truth không lấy từ output tracker.
- Generator: tái lập, cạnh hợp lệ, isolate được giữ trong danh sách node.
- Detector adapter: header/reference/endpoint đúng; graph rỗng không tạo chất lượng giả.
- Evaluation: bất biến đổi tên nhóm/thứ tự CSV; lỗi duplicate/user lạ bị chặn; thiếu/isolate có coverage và trạng thái rõ.
- Integration nhỏ: một graph -> membership -> AMI và output không ghi đè. Lịch nghiên cứu đủ bộ chạy riêng, không nhét toàn bộ vào unit test.
- Trước bàn giao: test liên quan và gate hiện có của repo; clean-kernel notebook. Không có yêu cầu điểm AMI/F1 tối thiểu.

## 6. Phụ thuộc ngoài và cách tiếp tục

Không có spec 001–005 nào yêu cầu artifact của Đăng. Spec 006 có hai mốc: bàn giao/detection replay do Phúc tự làm, nghiệm thu demo chung cần Đăng. Nếu tracker chưa có, ghi trạng thái mốc chung và tiếp tục phần cá nhân; không viết tracker thay hoặc giả output để đóng task.

Nếu Đăng phản hồi contract v1, ghi phiên bản, thay đổi và dataset/run bị ảnh hưởng; không sửa artifact cũ tại chỗ. Nếu đã xem evaluation rồi đổi phương pháp, công khai hoặc dành bộ đánh giá mới.
