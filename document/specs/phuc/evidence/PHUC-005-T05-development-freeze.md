# Bằng chứng PHUC-005-T05 — full development và khóa protocol

**Kết quả:** DONE; PHUC-005 **5/6 DOING**, tổng **29/36 task**. **Owner:** Phúc.
**Ngày:** 19/10/2026, Asia/Bangkok. Nhánh `feat/phuc-005-reproducible-runs`, PR #10.
**Source production:** [`d4fe76b02962009dddb1d042da3fb084dd79582c`](https://github.com/TamNgx179/reddit-community-evolution/commit/d4fe76b02962009dddb1d042da3fb084dd79582c), working tree sạch; commit code sau 40 tests, trước production.
**Freeze:** 19/10/2026 **10:58:31.148600 UTC+07:00** (`2026-10-19T03:58:31.148600+00:00`). **Kiểm chứng hoàn tất:** 10:59:41 UTC+07:00.

## Vừa làm gì và dùng để làm gì

Chạy đủ 18 development datasets từ đầu qua graph/truth → Independent Leiden → evaluator, giữ mọi điểm thấp/null. Sau khi run complete, tạo **bản khóa riêng** để T06 biết chính xác config/policy/source/versions nào được chốt trước khi xem kết quả giữ lại. Không đổi recipe, scoring/split/summary policy hoặc canonical seed từ T01.

Thêm [benchmarks/freeze.py](../../../../src/reddit_sna/benchmarks/freeze.py): `create_benchmark_freeze` tạo run mới; `load_benchmark_freeze`/CLI verify kiểm tra archive/hash, source bytes và versions hiện tại mà không sinh/chấm dữ liệu. Full development phải complete đúng lịch/counts/stages, inventory verified, config/source/versions khớp. Có graph/detection metadata evaluation trong namespace thì không được tạo claim pre-evaluation freeze. Lỗi giữ failed/partial bundle, không ghi đè.

Freeze lưu nguyên `config/`, `provenance/`, report `evaluation/` của development và `development/manifest.json`; **không sửa development run đã đóng**. `evaluation/` trong hai output này là thư mục report chấm development, không phải tập giữ lại. Metadata audit chỉ xem nhận diện graph/detection artifacts trong `artifacts/detection-tracking`, không mở graph/truth/prediction giữ lại. Danh sách evaluation IDs trong freeze là kế hoạch.

## Lệnh đã chạy

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.detection_tracking `
    --config configs/detection_development.toml `
    --protocol configs/benchmark_week1_protocol.json `
    --run-id phuc-005-t05-development-001

& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.freeze create `
    --config configs/detection_development.toml `
    --protocol configs/benchmark_week1_protocol.json `
    --development-run artifacts/detection-tracking/phuc-005-t05-development-001 `
    --run-id phuc-005-t05-freeze-001

& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.freeze verify `
    artifacts/detection-tracking/phuc-005-t05-freeze-001
```

Production dùng process hash seed 0, detector seeds 0/1/2, canonical 0, gamma 1. Development seeds 11/12/13; evaluation 101/102/103 chỉ planned, chưa chạy. Lịch sáu case stable/grow/shrink/merge/split/dissolve giữ nguyên, không loại trường hợp theo điểm. [Hướng dẫn API/schema/phạm vi khóa](../005-reproducible-runs/README.md#chạy-đủ-development-và-tạo-bản-khóa--t05) có lệnh dùng run ID mới để tái tạo.

## Kết quả development

| Nội dung | Kết quả |
|---|---|
| Lịch production | **18 dataset / 36 snapshot / 108 snapshot×detector-seed units**, counts/stages/progress complete |
| Bảng xuất | **108 metrics, 21 summary, 36 stored month timings**, ledger 18 dòng |
| Valid/missing | **99 AMI hợp lệ, 9 null** với `degenerate_partition/truth_constant`; cả 9 là dissolve tháng cuối, giữ đủ support và cả ba detector seeds |
| Coverage | **1.0** trên cả 108 metric rows; không thay AMI bằng coverage |
| Development inventory | **377 file được hash + root manifest**; không ghi lại root khi tạo freeze |
| Freeze inventory | **54 file được hash + root manifest**, gồm **42 source files**, raw configs/policy và development evidence |
| Consumer độc lập | Root development, CSV/direct sklearn report và freeze stdlib consumer đều pass trên copies sau relocation, chạy `python -I`, không import producer |
| No overwrite | Retry cả development và freeze IDs đều exit 2; mọi byte/hash của hai output giữ nguyên |
| Bảo toàn | **4.610 artifact cũ**, **93 source/config/test files** giữ hash trong lúc kiểm chứng |

| Detector seed | Vai trò đã chốt | AMI mean trên các dòng hợp lệ | AMI nhỏ nhất | Valid / null | Coverage mean |
|---|---|---:|---:|---:|---:|
| 0 | **Canonical** | **0.9558799269999274** | 0.7241648712463861 | 33 / 3 | 1.0 |
| 1 | Diagnostic | 0.9487475264624783 | 0.7241648712463861 | 33 / 3 | 1.0 |
| 2 | Diagnostic | 0.9546409700892936 | 0.7251609881533845 | 33 / 3 | 1.0 |

Mean theo **dataset-month**, mỗi seed riêng, chỉ tính dòng `ami_status=ok`; luôn giữ missing/support. Không gộp ba seeds thành dataset độc lập hoặc chọn seed theo điểm. Hai điểm canonical thấp nhất là `dev-merge-easy-g11 / 2020-02` và `dev-split-easy-g13 / 2020-01`, cùng **0.7241648712463861**; đã giữ nguyên. Null của dissolve theo policy dự án khi truth tháng cuối chỉ còn background K; không gán điểm 0 hoặc bỏ dòng.

[Metrics 108 dòng](PHUC-005-T05-detection-metrics.csv), [summary 21 dòng](PHUC-005-T05-detection-summary.csv) và [dataset ledger 18 dòng](PHUC-005-T05-dataset-ledger.csv) theo Git để nhóm xem kết quả. Các full-development fixture trong tests là dữ liệu tạm cùng lịch, không cộng thành thêm production datasets. Đây là dữ liệu tổng hợp, chưa phải kết quả Reddit.

## Bản khóa thực tế

- Output: `artifacts/detection-tracking/phuc-005-t05-freeze-001/`, root scope `benchmark-protocol-freeze`, `freeze_record_created=true`, `evaluation_executed=false`.
- Freeze manifest SHA-256: **`8c3749cce905e5d416929bddd931cbb4a7104f047ad9273ab22561d5ccdf8ff9`**.
- Development manifest SHA-256: **`34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e`**.
- Protocol SHA-256: `cc78f961de7e3c83a343362035ccf84756a39cdc89c5c9cc1e5fd5115fe3a347`; recipe SHA-256: `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc`; không thay binding T01.
- `changes_from_development=[]`; metadata audit trước khóa không thấy evaluation graph/detection metadata trong namespace được kiểm tra.
- Expected development/evaluation **mỗi tập 18/36/108**, tổng **36/72/216**; mới development đã thực thi.

[Freeze reference JSON](PHUC-005-T05-freeze-reference.json) là **file tham chiếu** theo Git: source revision sạch, thời điểm, manifest/config hashes, counts/seeds/versions và đường dẫn/checksum ZIP. API verify cần đủ freeze directory, không nhận file tham chiếu này thay cho bundle.

Phạm vi khóa là mọi `.py` trong package `reddit_sna`, pyproject nếu có, recipe/policies/seeds và các versions đã ghi. T06 có thể thêm driver ngoài package, phải ghi source/hash driver và gọi các module đã khóa; không sửa thuật toán/canonical/policy. HEAD tiến do docs/driver không làm mất khóa nếu source bytes/versions vẫn khớp. Khóa dựa trên kiểm chứng hashes, không phải chỉ đặt file readonly.

## Test và gói bằng chứng

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.integration.test_benchmark_freeze tests.integration.test_synthetic_benchmark_run tests.unit.test_run_provenance tests.unit.test_benchmark_protocol -v
```

**40/40 pass**, 0 skip/failure/error, **163.199s**: 7 freeze integration, 22 benchmark integration, 1 provenance unit, 10 protocol unit. Kiểm tra freeze/verify/relocation/no-algorithm execution, namespace/subset/failed/pending input, drift config/output/source/versions, immutable freeze, publication failure, heldout-identity guard và CLI ngoài cwd. Guard dùng metadata giả lập trong temp, không sinh/đọc nhãn giữ lại. **Không chạy lại full repo suite T05**.

Code được commit **trước** production tại `d4fe76b`; script so hash 93 code/config/test files từ lượt test đến production, kiểm tra working tree sạch và source revision ghi trong development/freeze. Các số đo process gồm startup/I/O/verification; stored month timing vẫn giữ scope Leiden/report, peak memory chưa đo.

Proof local `artifacts/verification/phuc-005-t05-001/` có plan/before/test logs/test CSV/source snapshots, commands/stdout/stderr, full copies hai runs, ba independent readers, dataset ledger, result/hashes. ZIP **465 file, 676.018 byte**, CRC và từng entry đã đối chiếu byte; SHA-256 **`4282c57e8c7ec2bf7d534291c3814e92a6292f9f3fe8b3626a5df3ab0d0581a7`**. Sibling `.archive.json` và `.zip.sha256` giữ checksum. Full artifacts/ZIP local bị ignore; chưa tự có trên máy người khác.

Sau khi nhận ZIP và giải nén, có thể chạy:

```powershell
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_run.py <thu-muc-giai-nen>/runs/development complete
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_report.py <thu-muc-giai-nen>/runs/development/evaluation <thu-muc-giai-nen>/runs/development/inputs
& .\.venv\Scripts\python.exe -I <thu-muc-giai-nen>/read_freeze.py <thu-muc-giai-nen>/runs/freeze <thu-muc-giai-nen>/runs/development
```

**Tiếp theo T06:** dùng freeze đã xác minh để chạy đủ 18 evaluation datasets, ghi source driver/hash/freeze reference và đối chiếu tổng lịch. AC04 còn evaluation; phần khóa của AC05 đã có, kiểm chứng evaluation/final acceptance còn T06. Chưa có tracker/receipt/review Đăng.
