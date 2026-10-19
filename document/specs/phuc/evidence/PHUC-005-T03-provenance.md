# Bằng chứng PHUC-005-T03 — hồ sơ và trạng thái lượt chạy

**Task:** [PHUC-005-T03](../tasks.md#phuc-005). **Kết quả:** DONE; PHUC-005 **3/6 DOING**, tổng **27/36 task**.
**Ngày:** 19/10/2026, Asia/Bangkok. **Source cơ sở:** `3c9e872`, nhánh `feat/phuc-005-reproducible-runs`, PR #10.
**Kiểm chứng hoàn tất:** 19/10/2026 10:11:41 (UTC+07:00).

## Vừa làm gì

T02 đã ghép được đường chạy từ config đến bảng điểm. T03 bổ sung hồ sơ để nhóm biết **bảng điểm đó được tạo từ code/config nào, bằng môi trường nào, chạy đến đâu và các file còn nguyên không**.

[artifacts.py](../../../../src/reddit_sna/artifacts.py) có source/environment capture, output inventory và `RunRecorder`; [API benchmark](../../../../src/reddit_sna/pipelines/detection_tracking.py) gọi recorder tại các bước configuration, generation, detection và evaluation. Root manifest lên schema 2; các metadata con giữ schema cũ. Không đổi sampler, Leiden, công thức AMI, summary policy, seed canonical hay graph recipe.

## Hồ sơ lưu trong run

- Protocol/recipe/TOML nguyên byte cùng SHA-256 và JSON config thực dùng, gồm run ID override.
- Bản sao package Python đang được import và pyproject nếu có, source hashes, Git revision/branch/working tree. Nếu Git không lấy được thì ghi unavailable/null; không giả định config.project_root là nơi chứa package.
- Python/executable/platform, versions package/igraph/leidenalg/sklearn/numpy/scipy và hash seed nếu đặt. Không dump toàn bộ biến môi trường.
- Inventory SHA-256/bytes của mọi output file, gồm metadata con; root manifest và pending replacement không tự hash.
- Trạng thái/timestamps UTC/wall seconds cho từng stage; từng dataset có generation/detection durations, metadata path và trạng thái đánh giá. `progress_counts` ghi số dataset thực sự xong.
- Kiểm tra output đã niêm phong sau mỗi stage và source trước complete. File/source thay đổi làm failed, giữ expected/actual hashes để xem nguyên nhân.

Manifest ghi qua pending/replace. Lỗi giữ artifact, trạng thái failed và lỗi gốc; nếu ghi failed manifest lỗi thì cố lưu đầy đủ hồ sơ vào `failure.json`. Reader phải ưu tiên failure marker, không coi started hoặc child report complete là run thành công. Ctrl+C được xử lý theo exception; hard kill/mất điện/không ghi được file có thể để lại checkpoint started. Retry dùng run ID mới. [README](../005-reproducible-runs/README.md#hồ-sơ-của-mỗi-lượt-chạy--t03) mô tả trường và phạm vi timing.

## Test bổ sung

Thêm **9 tests**, gồm 8 integration và 1 unit; targeted **18/18 pass, 100.221s**, không skip/failure/error:

1. Inventory phủ đúng file/hashes/bytes, config override, source archives, environment và các scope timing.
2. Generator lỗi sau khi tạo file dở vẫn giữ file/hash; bước chưa chạy còn pending/null.
3. Detector dataset thứ hai lỗi: giữ dataset đầu hoàn tất, phần dở thứ hai và progress đúng.
4. Output đã niêm phong bị sửa: root failed, ghi hash expected/actual.
5. Source drift: giả lập thay hash khi kiểm tra cuối, không sửa source thật; root failed dù report con đã có.
6. Ghi complete manifest lỗi: root failed, lỗi gốc vẫn được ném lại.
7. Ghi failed manifest cũng lỗi: giữ lỗi generation gốc và full fallback failure record.
8. KeyboardInterrupt: failed, timing đã đo giữ lại, bước chưa chạy không có thời gian giả.
9. Git unavailable: source hashes vẫn đủ, environment chỉ có các trường cho phép.

Lệnh targeted:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_run_provenance tests.integration.test_synthetic_benchmark_run -v
```

## Demo và kiểm chứng độc lập

Plan trước khi chạy: stable/grow development generator seed 11, hai tháng 2020-01/02, detector seeds 0/1/2, canonical 0. Mỗi successful run dự kiến 2 dataset/4 snapshot/12 metrics/9 summary; không dùng ngưỡng điểm để chọn kết quả. Hai process đặt hash seed 0/137 và đảo thứ tự subset; API chuẩn hóa về lịch protocol.

Hai output mới: `artifacts/detection-tracking/phuc-005-t03-001/` và `phuc-005-t03-002/`. Một controlled failure tại `phuc-005-t03-failure-001/` giả lập detector grow lỗi sau khi stable đã xong, giữ partial file và ném lỗi dự kiến; đây là bằng chứng failure handling, không phải một lượt benchmark thành công.

Proof local `artifacts/verification/phuc-005-t03-001/` giữ full-suite log/test CSV, source/config snapshots, bản sao cả ba run, `read_run.py` stdlib audit manifest và `read_report.py` CSV/direct sklearn đã dùng ở T02. Hai consumer chạy bằng `python -I`, không import producer; đọc bản sao sau relocation, không dựa vào absolute producer paths.

Các số đo run/stage/dataset lồng nhau; không cộng tất cả. Run wall không gồm preflight hay công bố final manifest; stage wrapper có checkpoints và integrity overhead; exporter dataset có đọc/ghi. Evaluation chạy chung batch nên duration từng dataset null. Stored Leiden month timing giữ phạm vi diagnostics; report generation/peak memory vẫn null, peak memory toàn run cũng chưa đo.

## Kết quả đã lưu

| Kiểm chứng | Kết quả |
|---|---|
| Full repo suite | **314/314 pass**, 0 skip/failure/error, unittest **294.763s**, process **296.398s**; full log và CSV 314 test trong proof |
| Mỗi successful demo | **2 dataset/4 snapshot/12 metrics/9 summary/4 stored detection month timings**; 89 file gồm root manifest, **88 file được hash** |
| Source và config | Mỗi run lưu **41 source files** có hashes; ba input configs và JSON resolved config đối chiếu đúng byte/hash |
| Điểm trong demo nhỏ | 12 AMI hợp lệ, 0 thiếu; AMI/coverage 1.0 cho stable/grow seed 11; không suy rộng sang mọi case hoặc Reddit |
| Replay | **29 CSV/policy files giống byte**; timing/timestamp/provenance khác được giữ nguyên |
| Reader độc lập | **3/3 root manifest audit**, **2/2 report CSV/sklearn audit** pass trên copies sau relocation |
| Controlled failure | Root failed tại detection/grow; progress **2 generated/1 detected/0 evaluated**, **75 file được hash**, gồm partial file; không có evaluation report |
| No overwrite | Chạy lại successful run ID exit 2, toàn bộ hash output giữ nguyên |
| Bảo toàn | **3.503 artifact cũ** và **91 source/config/test files** giữ hash trong lúc kiểm chứng |

[Run summary](PHUC-005-T03-run-summary.csv) có ba dòng success/replay/failed; [stage timing](PHUC-005-T03-stage-timing.csv) có 12 dòng, giữ evaluation của failed run pending với thời gian trống. Hai replay cùng dataset IDs nên không cộng thành bốn dataset độc lập.

Run wall thành công lần đầu/replay **3.274s / 3.710s**; process wall **15.083s / 11.368s**. Process còn startup/preflight/manifest publication; không lấy chênh lệch này làm timing của một thuật toán. Failed run có run wall **2.429s**, process **10.387s**, scope failure capture ghi trong manifest.

ZIP local `artifacts/verification/phuc-005-t03-001.zip`: **282 file, 544.317 byte**, CRC và từng entry đã đối chiếu byte. SHA-256 **`5c9cf6aecf50ae3d0fa7c68a73f3bcaa266e3f94699addd6f49d1df3dcf1c091`**. `proof-hashes.json`, sibling `.archive.json` và `.zip.sha256` giữ checksum. Gói được ghi mới, không sửa log hoặc artifact cũ.

## Đọc lại khi có gói ZIP

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_run.py <thu-muc-giai-nen>/runs/first complete
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/runs/first/evaluation <thu-muc-giai-nen>/runs/first/inputs
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_run.py <thu-muc-giai-nen>/runs/failed failed
```

Thay `first` bằng `replay` để đọc lần hai. `read_run.py` là consumer cho các artifact bằng chứng T03, không phải generic public validator cho mọi schema hoặc kiểu lỗi. Code/config/tests/docs và CSV nhỏ được version; full artifacts/ZIP local bị Git ignore, chưa tự xuất hiện trên máy thành viên.

**Tiếp theo PHUC-005-T04:** nghiệm thu lifecycle/replay với schema đã hoàn thiện. Freeze ở T05; evaluation giữ lại ở T06; chưa có tracker/receipt/review Đăng.
