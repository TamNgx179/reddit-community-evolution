# Xác nhận integrity pipeline của Tâm — 22/11/2026

## Kết luận

Kiểm tra lại từ `origin/main` tại `e2c29d5` xác nhận các guard cần cho phần
pipeline integrity của Tâm đã có trong mã nguồn (PR #33, commit `61f173b`)
và các regression test liên quan đều đạt. Không tạo lại pipeline hay sửa code
trùng với phần đã merge.

## Những gì được bảo vệ

| Rủi ro | Guard đã kiểm tra | Kết quả |
|---|---|---|
| Dữ liệu tháng `t+1` làm đổi feature tháng `t` | Dựng cùng fixture với cutoff ngắn và cutoff mở rộng; feature/sample trước cutoff phải giống byte/nội dung | PASS |
| Khóa sample bị thiếu, trùng hoặc sai | Prediction key phải là `(reference_id, feature_month, community_id, label_month, label_reference_id)` hợp lệ; mọi model/seed phải có cùng cohort | PASS |
| Trộn nhãn từ version khác | Một cohort phải dùng đúng một `label_reference_id`; model có tập key khác hoặc nhãn version khác bị từ chối | PASS |

Các check này chỉ chứng minh pipeline từ chối dữ liệu không nhất quán. Chúng
không tự chứng minh nhãn tracker là ground truth xã hội, cũng không thay thế
một lần fit/đánh giá mô hình Reddit đầy đủ.

## Lệnh đã chạy

```powershell
$env:PYTHONPATH = 'src'
python -m unittest `
  tests.unit.test_temporal_study.EvaluationTests.test_label_reference_mismatch_is_rejected `
  tests.unit.test_temporal_study.EvaluationTests.test_matching_models_cannot_score_mixed_label_references `
  tests.integration.test_temporal_study.PreparationIntegrationTests.test_extended_observations_preserve_uncached_features_before_cutoff

python -m unittest `
  tests.unit.test_temporal_study.EvaluationTests.test_missing_duplicate_truth_and_reference_controls
```

Kết quả: **4/4 PASS**. Log cục bộ (Git-ignore) là
`artifacts/verification/tam-pipeline-integrity-20261122-001/test.log`, SHA-256:

`346559ca70a7659ecc5a67155c107982955ad36d56509e9e95ed0b19d46a571d`.
