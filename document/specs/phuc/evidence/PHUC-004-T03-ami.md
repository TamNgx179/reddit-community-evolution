# Bằng chứng PHUC-004-T03 — AMI và policy dữ liệu thiếu/degenerate

**Task:** [PHUC-004-T03](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 3/6, tổng 21/36 task.
**Kiểm chứng hoàn tất:** 18/10/2026 21:46:17, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `6a55b6f` cộng T03, nhánh `feat/phuc-004-detection-evaluation`, PR #9.
**Môi trường:** Python 3.12.6, scikit-learn **1.9.1**, numpy 2.5.4, scipy 1.18.1, igraph 1.0.0/leidenalg 0.12.0.

## Vừa làm gì và policy đã chốt

Thêm `DetectionAMI`, `score_snapshot` và immutable `AMI_POLICY` trong [evaluation/detection.py](../../../../src/reddit_sna/evaluation/detection.py). Hàm kiểm tra frame bằng T02 trước khi áp dụng policy, chỉ chấm endpoint users đã căn theo ID ở T01. Gọi thư viện `sklearn.metrics.adjusted_mutual_info_score` với **`average_method="arithmetic"`**, giữ nguyên điểm âm; không tự viết công thức AMI. [Tài liệu chính thức](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_mutual_info_score.html) được tra cứu ở phiên bản 1.9.1 ngày 18/10/2026.

Policy ID **`synthetic-ami-v1`** áp dụng theo thứ tự:

| Trường hợp | Điểm / trạng thái |
|---|---|
| Input sai keys/user/lengths/truth mapping | Báo lỗi, không lấy giao hoặc điền điểm mặc định |
| n_scored = 0 | null / `empty_scored`, reason `no_scored_users` |
| n_scored = 1 | null / `insufficient_users`, reason `fewer_than_2_scored_users` |
| Một phía chỉ có một nhóm | null / `degenerate_partition`, reason truth/prediction `_constant` |
| Một phía gán mỗi user thành một nhóm riêng | null / `degenerate_partition`, reason truth/prediction `_all_singletons` |
| Còn lại | Điểm thư viện / `ok`, reason null |
| Thiếu dependency, backend lỗi hoặc trả nonfinite | Báo lỗi rõ; không biến thành điểm 0/1 hoặc hàng null theo policy |

Flags nối theo thứ tự truth rồi prediction. Null thành ô trống trong CSV. Việc loại constant/all-singletons là **policy của đồ án**, không phải hạn chế của sklearn; counts/coverage và hàng có cờ vẫn được giữ. Quality summary T04 sẽ tổng hợp hàng `ok` đồng thời báo n thiếu/reason/canonical. N = 2 với hai partition all-singletons bị đánh dấu degenerate, dù đã đạt minimum_scored_users = 2.

[JSON policy đã lưu](PHUC-004-T03-ami-policy.json) là bản sao trực tiếp từ code, ghi trước khi chấm development, hash **`6c5bffaf35a9a3a1ab7a3af3a2a7204a7e411a913dda6aefbbdc82982d3f0f08`**. `policy-record.json` lưu thời điểm/hash. Đây chưa phải config freeze/evaluation của PHUC-005.

## Dependency và test

[pyproject.toml](../../../../pyproject.toml) khai báo extra `evaluation = ["scikit-learn>=1.5,<2"]`. Alignment/counts/null policy không import sklearn; frame đủ điều kiện mới cần extra. Lượt kiểm chứng dùng 1.9.1, không kiểm thử mọi phiên bản trong range.

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[evaluation]'
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.integration.test_detection_alignment -v
```

Cài editable extra thành công; **pip check: No broken requirements found**. Lệnh thử đầu dùng `--no-build-isolation` thất bại vì venv không có setuptools; giữ `pip-install.log`, chuyển về lệnh chuẩn để pip tự tạo build environment, thành công trong `pip-install-isolated.log`. Không thay phiên bản sklearn đã có để chọn điểm tốt hơn.

**32/32 test liên quan pass**, 0 skip/failure/error; log cuối **18.863s**, process wall **20.657s**. Lượt đầu trước khi đăng ký extra cũng 32/32 pass (56.242s). T03 thêm **11 unit test và 1 integration test**, giữ 20 test T01/T02. Kiểm tra perfect/nontrivial = 1, điểm âm ≈ -0.5, đổi tên nhóm/thứ tự CSV, đối xứng, so trực tiếp sklearn arithmetic, isolate tách khỏi AMI nhưng giữ coverage, null policy theo lý do, malformed frame, dependency thiếu, nonfinite/backend lỗi và gói stable thật ba seed không bị sửa input. Không chạy lại full repo suite ở T03; log/giới hạn full discover lịch sử vẫn ở evidence T01.

## Kết quả development và diagnostic

Tái sử dụng input copies của T02: **360 file**, gồm 18 dataset development graph/truth + detection và hai diagnostic graph mixed-isolates/zero-edges. Config/seed/canonical mặc định của development giữ nguyên. Có 108 dòng development (18 dataset × 2 tháng × 3 detector seed), cộng 27 diagnostic/memory-policy rows, tổng **135 dòng**.

| Phạm vi | `ok` | Null có cờ | Tổng |
|---|---:|---:|---:|
| Development | 99 | 9 `degenerate_partition` | 108 |
| Diagnostic/policy fixture | 6 | 12 degenerate, 8 empty, 1 insufficient | 27 |
| Toàn bộ kiểm chứng | 105 | 30 | 135 |

9 dòng development null là dissolve tháng 2020-02, generator 11/12/13 × detector 0/1/2: truth chỉ còn nhóm K nên `truth_constant`. Không xóa các dòng này, không thay bằng AMI 0 hoặc 1 và không chọn seed để né policy.

| Ví dụ | Tháng / seed | Coverage | AMI / trạng thái |
|---|---|---:|---|
| dev-stable-easy-g11 | Cả hai tháng, seed 0 | 1.0 | 1.0 / ok |
| dev-grow-easy-g11 | Cả hai tháng, seed 0 | 1.0 | 1.0 / ok |
| dev-merge-easy-g12 | 2020-02, seed 0 | 1.0 | 0.7636346653571817 / ok |
| dev-dissolve-easy-g11 | 2020-02, seed 0 | 1.0 | null / degenerate, truth_constant |
| Memory: AABB vs xyxy | n = 4 | 1.0 | -0.49999999999999944 / ok |
| Memory: perfect + isolate | 4 scored / 5 active | 0.8 | 1.0 / ok |

Đây là AMI prediction-vs-truth trên benchmark tổng hợp, khác ARI giữa detector seeds của PHUC-003. Coverage đầy đủ vẫn có thể đi kèm phân hoạch chưa trùng truth. Các dòng qua seed/tháng lặp user và không phải mẫu/dataset độc lập. Chưa tính production summary hoặc kết luận trên Reddit; không truy cập/chạy evaluation 101/102/103.

## Đối chiếu độc lập và output đã lưu

- Consumer `read_ami.py`, chạy `python -I`, đọc nodes/R/truth/prediction CSV và gọi thẳng sklearn, **không import project/igraph**. Kiểm chứng 135/135 status/reason/support/value; 105 dòng có điểm, 30 null; sai số lớn nhất **0.0**. Thêm **210 kiểm tra** đổi tên/đảo dòng và đối xứng trên các dòng đủ điều kiện. Consumer độc lập với wrapper project, dùng cùng thư viện metric, không phải công thức AMI thứ hai.
- [Development AMI CSV 108 dòng](PHUC-004-T03-development-ami.csv), [diagnostic/policy CSV 27 dòng](PHUC-004-T03-diagnostic-ami.csv), [policy JSON](PHUC-004-T03-ami-policy.json) theo Git. Giữ context/reference/seed/canonical/counts/coverage, support, AMI/status/reason/policy/method và sklearn version.
- Full proof local `artifacts/verification/phuc-004-t03-001/`: `ami.csv`, hai CSV riêng, policy/record, 360 input files, memory examples, runner/consumer, pip install/check logs, raw unittest log + 32-row test CSV, before/result/proof hashes.
- **1.621 artifact cũ giữ nguyên hash**, gồm 904 detection-tracking files và proof/ZIP T01/T02. Code/config/pyproject/test hashes cũng khớp trước/sau kiểm chứng.
- ZIP `artifacts/verification/phuc-004-t03-001.zip`: **377 file, 315.156 byte**; CRC/từng entry/proof hash manifest đã kiểm tra. SHA-256 **`05f08b821023a2efba1688319610dfefffbc2adc3b089289403e6d113877e2e1`**; sibling `.zip.sha256` và `.archive.json` lưu thông tin archive.

Sau khi cài extra evaluation và giải nén ZIP:

```powershell
python -I <thu-muc-giai-nen>/read_ami.py <thu-muc-giai-nen>
```

Dùng API theo [README](../004-detection-evaluation/README.md) với `inputs/development/source/<dataset-id>` và `inputs/development/detected/<dataset-id>` để tính lại. Có thể tái tạo source/detection theo PHUC-002/003 thay cho ZIP. Full artifact/ZIP local bị ignore; người nhận cần ZIP thực tế hoặc tự tái tạo. `verify.py` là recorder lịch sử gồm bước tiếp tục sau lỗi build setup, không phải CLI production để retry vào proof cũ.

**FR03/T03 DONE. Tiếp theo PHUC-004-T04:** exporter metrics/summary có n hợp lệ/thiếu, canonical riêng và timing đúng phạm vi. Các CSV T03 là evidence, chưa thay phần nghiệm thu exporter/T06. Chưa có receipt/review Đăng.
