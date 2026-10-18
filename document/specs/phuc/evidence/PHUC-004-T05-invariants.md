# Bằng chứng PHUC-004-T05 — Kiểm tra các điều kiện nghiệm thu evaluator

**Task:** [PHUC-004-T05](../tasks.md#phuc-004). **Kết quả:** DONE; PHUC-004 5/6, tổng 23/36 task.
**Source:** cơ sở `c27ade1` cộng T05 trên nhánh `feat/phuc-004-detection-evaluation`, PR #9.
**Kiểm chứng hoàn tất:** 18/10/2026 23:05:23, Asia/Bangkok (UTC+07:00).
**Môi trường:** Python 3.12.6, sklearn 1.9.1, numpy 2.5.4, scipy 1.18.1, igraph 1.0.0, leidenalg 0.12.0.

## Vừa làm gì và dùng để làm gì

Rà soát các test căn user, AMI, coverage, summary và export đã có; thêm **4 test** kiểm tra các tình huống dễ làm người đọc tin nhầm kết quả. Không sửa thuật toán evaluator, công thức AMI, policy hay cấu hình benchmark.

- **Prediction CSV sai nhưng hash đã khớp:** thử user trùng, thiếu endpoint, user lạ và gán nhóm cho isolate. Test cập nhật cả hash file và mapping trong metadata, rồi yêu cầu evaluator báo đúng lỗi membership, chưa tạo output và không sửa input. Hash khớp chỉ chứng minh nội dung file khớp metadata, không chứng minh dữ liệu đúng.
- **Truth CSV sai nhưng hash đã khớp:** thử user trùng/thiếu/lạ, cập nhật hash truth và chuỗi tham chiếu metadata nguồn của detector. Cả ba trường hợp vẫn phải bị chặn vì sai tập user. Tổng cộng **7 trường hợp dữ liệu lỗi** trong hai test, không phải bảy dataset độc lập.
- **Hai seed đồng ý nhưng cùng sai:** truth chia `(u0,u1)/(u2,u3)`, hai dự đoán cùng chia `(u0,u2)/(u1,u3)` dù tên nhóm khác. ARI giữa hai dự đoán bằng **1**, AMI mỗi dự đoán với truth bằng **-0.5**. Khi đổi sang phân hoạch đúng, AMI bằng **1**. Kiểm tra này giữ rõ ranh giới giữa ổn định giữa seed và chất lượng khôi phục truth.
- **Lỗi ở bước công bố cuối:** mô phỏng lỗi đổi `metadata.pending.json` thành `metadata.json`. Các file đã viết được giữ để xem lỗi, có `failure.json`, chưa có metadata hoàn tất. Thử lại vào thư mục ấy phải bị từ chối và không ghi đè file.

Test mới nằm ở [unit evaluator](../../../../tests/unit/test_detection_evaluation.py) và [integration exporter](../../../../tests/integration/test_detection_evaluation_export.py). Fixture integration dùng graph/Leiden thật, development stable seed 11; fixture isolate dùng `p_in=0.05, p_out=0` riêng cho kiểm tra. Các file sai chỉ được tạo trong thư mục tạm của test.

## Đối chiếu điều kiện nghiệm thu

| AC | Nội dung được kiểm tra | Test tiêu biểu |
|---|---|---|
| AC01 | Căn cùng user, đổi tên nhóm/thứ tự dòng không đổi AMI; phân hoạch đúng đủ điều kiện có điểm 1 | `test_aligns_by_user_instead_of_input_row_or_community_order`, `test_reordering_csv_rows_and_renaming_groups_preserves_ami`, `test_nontrivial_perfect_partition_returns_one` |
| AC02 | Isolate còn trong mẫu số coverage; AMI chỉ chấm endpoint đã xác minh | `test_isolate_stays_in_denominator_and_all_truth_group_count`, `test_counts_match_saved_csvs_for_real_detection_with_isolates`, `test_isolate_truth_is_excluded_from_ami_but_retained_in_coverage` |
| AC03 | Duplicate/missing/unknown/isolate prediction là lỗi kể cả hash file hợp lệ | `test_rejects_duplicate_missing_unknown_or_isolate_prediction_without_intersection`, hai test `test_rehashed_prediction_csv_...` / `test_rehashed_truth_csv_...` |
| AC04 | Empty/insufficient/constant/all-singletons có null/status/reason; input sai vẫn là lỗi | `test_null_cases_have_explicit_status_reason_and_never_import_sklearn`, `test_all_missing_ami_stays_blank_in_csv_with_reason_and_support`, `test_invalid_memberships_are_errors_before_missing_or_degenerate_policy` |
| AC05 | Summary giữ support/valid/missing và từng seed; timing tháng không nhân ba; ARI seed không thay AMI truth | `test_ami_mean_is_over_valid_snapshot_rows_not_users_or_missing_defaults`, `test_each_seed_has_separate_canonical_or_diagnostic_rows`, `test_two_datasets_write_metrics_summary_policy_timing_and_verified_provenance`, `test_identical_detector_runs_can_agree_while_both_disagree_with_truth` |

[CSV nghiệm thu](PHUC-004-T05-acceptance-matrix.csv) có **16 ánh xạ test → 5 AC**, xuất từ danh sách test thực sự đã chạy, với đầy đủ test ID và log để đối chiếu. Cả 5 AC pass. Đây là kiểm tra hành vi evaluator; T06 vẫn là mốc nghiệm thu kết quả stable/grow có truy vết input/config/version.

## Lệnh kiểm tra

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Chạy riêng phần evaluator khi cần phát triển tiếp:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_detection_evaluation tests.unit.test_detection_summary tests.integration.test_detection_alignment tests.integration.test_detection_evaluation_export -v
```

Cần môi trường repo đã cài extras `[graph,evaluation]`. T05 không thêm dependency. Bốn test mới đã chạy riêng thành công: **4/4 pass, 5.366s**. Sau khi chốt code/test, đã chạy full suite một lượt hoàn chỉnh như lệnh đầu; lệnh chạy riêng evaluator ở trên là hướng dẫn chạy lại, không phải một lượt targeted 48 test riêng của T05.

## Kết quả và bằng chứng lưu

| Kiểm chứng | Kết quả |
|---|---|
| Full repository suite | **286/286 pass**, 0 skip/failure/error, unittest **138.707s**, process wall **139.576s**, exit 0 |
| Evaluator trong full suite | **48 test pass**: unit alignment/counts/AMI/summary và integration loader/export |
| AC01–05 | 5/5 pass; CSV giữ 16 test tiêu biểu, các test khác vẫn có trong log/CSV full suite |
| Artifact cũ | **3.090 file giữ nguyên SHA-256**, gồm output/proof/ZIP/log đã có trong `artifacts/` trước lượt ghi bằng chứng mới |
| Code/config trong lúc chạy | 85 file đã theo Git tại `src/`, `tests/`, `configs/`, `pyproject.toml` giữ nguyên hash từ trước đến sau lượt full suite |

Proof local: `artifacts/verification/phuc-004-t05-001/`. Gồm `full-unittest.log`, `new-tests.log`, `tests.csv` (286 test), `acceptance-matrix.csv`, `before.json` (source/artifact hashes, base revision, working tree), `result.json` (versions/lệnh/timing), ba source snapshots, recorder `verify.py` và `proof-hashes.json`. Log đầy đủ giữ cả các lần audit/normalize của test cũ; chúng dùng fixture tổng hợp trong thư mục tạm, không phải bộ Reddit thật.

ZIP `artifacts/verification/phuc-004-t05-001.zip`: **11 file, 138.792 byte**, đã kiểm tra CRC và từng entry khớp byte với proof. SHA-256 **`01912a0ba4b59514024af073e9c6b2375f882374dc746b3ed7700e19aef2199f`**; thông tin/checksum còn ở `.archive.json` và `.zip.sha256`. Hash manifest trong ZIP ghi hash các file proof còn lại.

CSV nghiệm thu nhỏ được commit cùng docs. Full logs/proof/ZIP bị ignore và chỉ có local; thành viên cần nhận ZIP thực tế hoặc checkout nhánh/commit này, cài dependencies rồi chạy lại lệnh test. Recorder là script ghi bằng chứng một lượt, không chạy lại vào cùng thư mục đã có log/output.

T05 không chạy lại full development production report, không sử dụng tập evaluation giữ lại và không đổi output T04. Kết quả AMI development đã đo trước đó nằm ở [bằng chứng T04](PHUC-004-T04-export.md), không được trình bày thành phép đo mới của T05. Chưa có receipt/review từ Đăng.
