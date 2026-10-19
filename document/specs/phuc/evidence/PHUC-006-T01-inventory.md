# Bằng chứng PHUC-006-T01 — inventory và consumer bàn giao

**Trạng thái:** DONE; PHUC-006 **1/6**, tổng Phúc **31/36**. Owner Phúc, ngày 19/10/2026, Asia/Bangkok.
**Nhánh:** `feat/phuc-006-handoff-demo`, tách từ `08913a5` của PHUC-005. Bước này chỉ đọc lại outputs, không sinh graph/chạy Leiden hoặc AMI mới.
**Code/tests đã commit/push:** [`9ca1064`](https://github.com/TamNgx179/reddit-community-evolution/commit/9ca106468bde862ba4128e50d302ee9e6bc15102), bytes khớp source snapshot đã kiểm chứng. [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11) đang mở, base nhánh của PR #10, chưa merge.

## Vừa làm gì?

Thêm [consumer stdlib](../../../../src/reddit_sna/reporting/synthetic_handoff.py) và [25 unit tests](../../../../tests/unit/test_synthetic_handoff.py). Consumer kiểm tra complete schema-2 run, hashes/sizes/file inventory, identity/source linkage, truth membership/events/links và membership cả ba detector seeds. Kiểm tra user keys duy nhất, reference đúng, assigned users bằng chính xác endpoint R; isolate vẫn giữ trong nodes/truth. Graph cohort/reference được tính từ file hashes bằng stdlib, không gọi producer.

API `inspect_synthetic_handoff` chỉ đọc/trả inventory; `export_synthetic_handoff` ghi `inventory.json`, `snapshot_inventory.csv`, `metadata.json` vào thư mục mới. Metadata complete ghi cuối; khi ghi lỗi, partial files được giữ và không có complete metadata đọc được. Không ghi đè output cũ hoặc tạo output chồng source. [Hướng dẫn CLI/API và ý nghĩa từng file](../006-handoff-demo/README.md).

Mỗi snapshot inventory chỉ đường dẫn graph/nodes, truth membership/events/links và detector membership, kèm dataset/month/seed/reference/counts. Paths tính từ source run, không dùng absolute paths máy producer. Đăng dùng seed 0 canonical qua hai tháng của cùng dataset; reference truth và detector tách biệt. **Passing consumer không xác nhận Đăng đã nhận/đọc gói.**

## Đầu vào và kết quả thực tế

| Tập | Run đã có, không chạy lại | Dataset | Snapshot | Membership CSV | Canonical CSV | Tổng source files gồm manifest |
|---|---|---:|---:|---:|---:|---:|
| Development | `phuc-005-t05-development-001` | 18 | 36 | 108 | 36 | 378 |
| Evaluation | `phuc-005-t06-evaluation-001` | 18 | 36 | 108 | 36 | 434 |
| Tổng | Hai split giữ riêng | **36** | **72** | **216** | **72** | **812** |

Đã chạy consumer bằng Python 3.12.6 **`-I -S`** cho cả hai source run thật và hai full copies sau relocation: **4/4 lượt đạt**, mỗi output gồm ba files. Hai cặp output gốc/relocated giống từng byte, canonical vẫn 0. Một lượt retry cùng output exit **2**, stdout rỗng, output không đổi. Isolated import guard xác minh không import `reddit_sna`, `igraph`, `leidenalg`, `sklearn`.

Hai lệnh thực tế dùng bản consumer đã chụp tại `artifacts/verification/phuc-006-t01-001/consumer.py`:

```powershell
& .\.venv\Scripts\python.exe -I -S artifacts/verification/phuc-006-t01-001/consumer.py `
  artifacts/detection-tracking/phuc-005-t05-development-001 `
  --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e `
  --output artifacts/detection-tracking/phuc-006-t01-development-001

& .\.venv\Scripts\python.exe -I -S artifacts/verification/phuc-006-t01-001/consumer.py `
  artifacts/detection-tracking/phuc-005-t06-evaluation-001 `
  --expected-manifest-sha256 e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c `
  --output artifacts/detection-tracking/phuc-006-t01-evaluation-001
```

Commands/stdout/stderr/exit/timing thật có trong proof, bao gồm hai lượt dùng paths absolute sau relocation. Các output `-001` đã có; khi tái chạy dùng tên mới. Independent audit trong verification script đọc lại JSON/CSV/hash/key/count và đối chiếu mỗi inventory với full source copy; không dùng API của consumer để chứng nhận output consumer.

## Test và kiểm chứng bảo toàn

- **51/51 targeted tests pass**, 0 skip/failure/error, **162.499s unittest**: 25 consumer mới, 11 handoff hiện có, 7 freeze integration, 8 frozen driver integration. Full repo suite **không chạy lại** T01.
- Fixture unit độc lập, nhỏ, chỉ kiểm tra contract; không gọi generator/detector/AMI để tự xác nhận, không tạo thêm lượt evaluation benchmark. Có Unicode/CSV quoting, isolate/graph rỗng/tháng quan sát rỗng, relocated deterministic export, duplicate/missing/unknown user, sai reference/tháng/header/width, truth keys, thiếu seed mapping, source binding, full selection thiếu dataset, corruption/path, source mutation, partial publication và no-overwrite. Nhánh test tạo symlink chỉ chạy nếu Windows cho phép; path traversal vẫn được test độc lập.
- Đã đối chiếu **6.795 artifact cũ**, **98 code/config/test files cũ**: giữ nguyên hash. **42 frozen source files PHUC-005 giữ nguyên byte**. Consumer mới được thêm riêng; không sửa producer, config, freeze gate hoặc source đã khóa.
- Lượt gom test log đầu có **4 loader ImportErrors** vì gọi file runner trong thư mục proof làm Python không tìm thấy `tests`; chưa chạy product tests ở lượt đó. Gọi lại bằng `python -c`/`runpy` từ repo đạt 51/51. Log/summary thất bại đầu được giữ.
- Script preservation đầu dùng thiếu tiền tố `src/` khi đối chiếu tên source trong archive, lỗi sau khi bốn consumer và output audits đã đạt. `complete_verification.py` sửa cách ánh xạ đường dẫn và hoàn tất audit **12:00:31 +07**, không chạy lại consumption. Hai lỗi harness và cách sửa có trong proof; không giấu hoặc tính chúng là test pass.

## File đã lưu

Trong Git: [run summary 2 dòng](PHUC-006-T01-run-summary.csv), [dataset ledger 36 dòng](PHUC-006-T01-dataset-ledger.csv), [reference/hash](PHUC-006-T01-handoff-reference.json), consumer/tests và docs. Reference chỉ trỏ gói thật, không thay source bundle.

Local outputs: `artifacts/detection-tracking/phuc-006-t01-development-001/` và `phuc-006-t01-evaluation-001/`. Full inventory và CSV 108 hàng/split ở đây.

Proof: `artifacts/verification/phuc-006-t01-001/`; gồm full immutable source copies `runs/development`, `runs/evaluation` (kèm freeze), standalone `consumer.py`, hai inventories, source snapshots/tests/logs/commands/audit result/baseline hashes và README nhận gói. ZIP **859 files, 1.186.186 byte**, CRC và từng entry đã đối chiếu byte. SHA-256:

```text
c8039bd1fa2555c498ae86673b84f50d897db101db735f9cdcc59adca77626dc
```

ZIP local `artifacts/verification/phuc-006-t01-001.zip`; checksum và `.archive.json` ở cạnh ZIP. `artifacts/` bị ignore, full bundle chưa có trên GitHub. Người nhận cần nhận ZIP thật rồi mở terminal trong thư mục giải nén:

```powershell
python -I -S consumer.py runs/development --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e --output inventory-check-development
python -I -S consumer.py runs/evaluation --expected-manifest-sha256 e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c --output inventory-check-evaluation
```

## Phạm vi nghiệm thu

FR01/T01 và **AC01 phần consumer** đạt. Chưa có notebook/clean-kernel/clean install/hard-case analysis T02–T06; PHUC-006 chưa DONE toàn bộ. Các metric AMI và frozen chronology/runtime đã nghiệm thu ở PHUC-005, T01 chỉ inventory và kiểm tra contract/hash của chúng, không chứng nhận lại giá trị metric.

Package trên nhánh PHUC-006 thêm reporting module, nên closure runtime hiện tại khác bản khóa 42 file. Benchmark replay phải dùng driver `09623f1` và frozen source/versions; không sửa freeze để chấp nhận source mới. Consumer đọc output bằng stdlib độc lập với gate runtime đó.

**Tiếp theo PHUC-006-T02:** viết `document/PHUC-DANG-WEEK1-HANDOFF.md` cho người nhận. Tracker, receipt/review Đăng và demo chung vẫn pending riêng; kết quả chỉ là benchmark tổng hợp, không phải Reddit hoặc dự báo sự kiện.
