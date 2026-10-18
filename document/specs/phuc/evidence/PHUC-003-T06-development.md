# Bằng chứng PHUC-003-T06 — Full development Independent Leiden

**Task:** [PHUC-003-T06](../tasks.md#phuc-003). **Kết quả:** DONE; PHUC-003 6/6, tổng 18/36 task.
**Kiểm tra chính hoàn tất:** 18/10/2026 20:06:05, Asia/Bangkok (UTC+07:00).
**Source:** cơ sở `3b44d04` cộng T06, nhánh `feat/phuc-003-leiden-adapter`; manifest ghi code hashes và working-tree state trước commit.
**Môi trường:** Python 3.12.6, package 0.1.0, igraph 1.0.0, leidenalg 0.12.0.

## Vừa làm gì và cách chạy lại

Thêm [batch command](../../../../scripts/run_development_detection.py) gọi `export_synthetic_detection` hiện có trên toàn bộ lịch development; không sửa Leiden, adapter per-dataset hoặc dependencies. [TOML mới](../../../../configs/detection_development.toml) dùng seed 0 đúng vai trò canonical detector; generator schedule vẫn trong JSON. Hai lượt chạy thật dùng lại graph/truth full development của PHUC-002.

```powershell
& .\.venv\Scripts\python.exe scripts/run_development_detection.py --source-run artifacts/detection-tracking/phuc-002-t06-001 --run-id phuc-003-t06-replay-new
```

Source phải có đủ dataset đúng lịch, manifest complete/generation+truth và hash graph/config/metadata khớp; runner chỉ chọn development. Output run ID phải mới và nằm trong project artifacts. Nếu chưa có source local, tái tạo theo [PHUC-002 full development](../002-dynamic-benchmark/README.md#chạy-đủ-bộ-development-và-đọc-lại-độc-lập--t06), đổi `--source-run` cho đúng; code/CSV trên Git không tự chứa full artifact.

Runner lưu root config byte copy, manifest, từng dataset 9 file. Manifest có scope `development-detection`, actual dataset list/expected counts, canonical/schedule, config/source/code/output hashes, Git revision/working-tree state, Python/package versions và timing; versions graph libraries ở diagnostics/metadata từng dataset. Source hashes gồm manifest + 108 graph/config/metadata, không đưa CSV truth vào detector. Complete chỉ đến detection; lỗi giữ completed/partial dataset và failed manifest/current_dataset/exception.

## Cấu hình đã dùng, giữ nguyên trước/sau run

- Source `artifacts/detection-tracking/phuc-002-t06-001/`, sáu case stable/grow/shrink/merge/split/dissolve, mỗi case generator seeds **11/12/13**.
- Hai tháng giả lập **2020-01/2020-02**, graph vô hướng đơn giản, weight 1, **p_in=0.50/p_out=0.02**.
- Detector **0/1/2**, gamma 1, canonical **0**, protocol `synthetic-planted-undirected-v1`; không chọn seed/gamma theo điểm hoặc loại case khác nhau.
- Runtime `configs/benchmark_week1.json` SHA-256 **`950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`**. Đây là runtime byte copy, có thể khác whitespace của archived source config; recipe được đối chiếu semantic.
- Không sinh hoặc chạy evaluation 101/102/103; không thực hiện AMI/tracker hoặc config freeze PHUC-005.

## Test và kiểm chứng thực tế

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_development_detection -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**4/4 test runner mới pass**, targeted **8.579s**. Test đủ lịch/scope/hashes, CLI no-overwrite/source thiếu dataset, lỗi giữa chừng giữ gói đã xong/partial/failed manifest, seed/namespace/overlap/source hash lỗi trước output. Fixture test dùng đủ sáu case ở một generator seed để kiểm chứng orchestration; lượt thực bên dưới dùng đủ 18 dataset.

**238/238 test repo pass**, 0 skip/failure/error, unittest **123.046s**, toàn process **124.814s**. Full log/test CSV đã lưu; gồm cả 24 test adapter T05. Config CLI check cũng pass. Tests dùng synthetic temporary data, không phải thí nghiệm Reddit.

| Kiểm chứng actual development | Kết quả |
|---|---|
| Hai process mới, `PYTHONHASHSEED=0/137` | `phuc-003-t06-001/` và `phuc-003-t06-002/` |
| Mỗi run | **18 dataset, 36 snapshot, 108 membership CSV**, 54 detector refs, 164 file toàn run |
| Schedule/canonical | Đủ generator 11/12/13 × sáu case; đủ detector 0/1/2/tháng; canonical luôn 0 |
| Replay | **108/108 CSV giống byte**; 108 partition cũng bằng nhau khi bỏ tên nhóm |
| Consumer stdlib `python -I` | **36 dataset readers/216 CSV** kiểm tra hashes, identity/reference/month/seed, versions/config/counts và exact endpoint set |
| ARI độc lập | **216 seed-pair checks** từ CSV qua hai run; absolute tolerance 1e-12, sai số lớn nhất 3.331e-16 |
| No-overwrite | CLI chạy lại vào run đầu exit 2; toàn bộ output cũ giữ nguyên hash |
| Bảo toàn | Runtime/TOML/source và **576 output file có trước** không đổi hash |
| Process wall time | 4.410s / 4.506s, gồm startup/preflight/detection/I/O; không có generation và chưa phải benchmark hiệu năng |

Reader sử dụng graph-only copy gồm 108 file metadata/config/R/nodes, không cần CSV truth. Root manifest hash đối chiếu 163 output file khác; không tự hash chính manifest. Gói từng dataset giữ schema/layout T03; root `completed_stages=["detection"]`, không báo full pipeline xong.

## Kết quả diagnostics và cách hiểu

Default cohort có **7/36 snapshot** khác partition giữa detector seeds. ARI seed trung bình **0.941167**, nhỏ nhất **0.502139** ở `dev-merge-easy-g12`, tháng 2020-02, seed 0 so với 2. Không thay canonical 0 hoặc chạy lại bằng seed được chọn để làm kết quả đẹp hơn.

| Case | Số cặp seed/tháng | ARI nhỏ nhất | ARI trung bình |
|---|---:|---:|---:|
| stable | 18 | ≈1 | ≈1 |
| grow | 18 | ≈1 | ≈1 |
| shrink | 18 | ≈1 | ≈1 |
| merge | 18 | 0.502139 | 0.844177 |
| split | 18 | 0.506195 | 0.858118 |
| dissolve | 18 | 0.502356 | 0.944706 |

Đây là **108 so sánh cặp seed trong 36 snapshot của 18 dataset**, không phải 108 dataset độc lập hoặc AMI với truth. Cả 108 cặp có ít nhất hai nhóm ở hai partition trong lượt này; CSV vẫn có status/flag riêng cho trường hợp constant ở các lượt khác. Không dùng diagnostics để kết luận detector khôi phục truth tốt đến đâu.

Canonical seed 0 có 23 snapshot tìm 2 nhóm và 13 snapshot tìm 3 nhóm. Mọi snapshot default ở lượt này đều assigned đúng toàn bộ endpoint, không có isolate; tests T04/T05 vẫn kiểm tra fixture có isolate/empty. Timing lưu **72 dòng tháng×run**, mỗi giá trị bao gồm cả ba seed; không gán cùng thời gian thành ba phép đo riêng. Chưa đo peak memory.

## File đã lưu

- Hai run đầy đủ: `artifacts/detection-tracking/phuc-003-t06-001/` và `phuc-003-t06-002/`.
- Proof: `artifacts/verification/phuc-003-t06-001/`: runner/consumer, graph-only input view, source manifest copy, config check/full test log và 238-row test CSV, detect/read/no-overwrite logs, kết quả/hashes/strict ARI analysis.
- [Detection CSV 108 dòng](PHUC-003-T06-development-detection.csv): dataset/split/case/seed/month, canonical, active/endpoint/assigned/isolate, edges, predicted groups/sizes/status, reference/path/hash.
- [Seed repeatability CSV 108 dòng](PHUC-003-T06-seed-repeatability.csv): raw ARI theo cặp và trạng thái, không phải AMI.
- [Timing CSV 72 dòng](PHUC-003-T06-month-timings.csv): run/dataset/month và scope ba detector seeds/tháng.
- ZIP `artifacts/verification/phuc-003-t06-001.zip`: **489 file, 438,041 byte**, đã mở lại kiểm tra CRC và từng entry đúng byte. SHA-256 **`6cd06a398402048bb41042a68d963fa12fdc6e0ac9d194a6505edc1647c74e14`**; sibling `.zip.sha256`/`.archive.json` lưu kiểm chứng.

Code/config/tests/docs/ba CSV đi theo Git; full output/ZIP local bị ignore. ZIP có graph-only view phục vụ đọc lại, không thay gói nguồn graph/truth đầy đủ cần cho evaluator. Muốn chạy lại toàn bộ, dùng command trên với source đã tạo và run ID mới; muốn xem metadata một dataset, chọn `run/datasets/<dataset-id>/` như [README](../003-leiden-detection/README.md). Helper proof lưu record của lượt kiểm chứng, không retry vào log/output cũ.

## Chốt PHUC-003 và bước tiếp theo

**FR01–FR05, AC01–AC05 và cả sáu task đã nghiệm thu kỹ thuật:** API/protocol không nhận truth labels, đủ seed/canonical, membership/diagnostics/versions/mapping được lưu, endpoint/empty/error/no-overwrite có test và full development thật có output đối chiếu. Gate empty/isolate thuộc fixture tests, không bị giả thành quan sát trong default run.

Đây là phần detection của Phúc; chưa có AMI evaluator, evaluation/freeze/full orchestration, tracker hoặc receipt/review Đăng. **Tiếp theo PHUC-004-T01:** xác minh dataset/reference/month/user keys và căn vectors theo cùng user ID trước khi tính AMI/coverage.
