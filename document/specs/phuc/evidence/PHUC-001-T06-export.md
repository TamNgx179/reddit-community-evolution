# Bằng chứng PHUC-001-T06 — Export và đọc độc lập fixture truth

**Task:** [PHUC-001-T06](../tasks.md#phuc-001). **Kết quả:** DONE; PHUC-001 hoàn thành 6/6 task.
**Kiểm tra hoàn tất:** 17/10/2026 22:18:26, Asia/Bangkok (UTC+07:00).
**Môi trường:** `.venv`, Python 3.12.6, package `reddit-community-evolution` 0.1.0. Source cơ sở `9aba275` cộng thay đổi T06 khi kiểm tra; nhánh `feat/phuc-001-ground-truth-events`.

## Đã triển khai

- [benchmarks/io.py](../../../../src/reddit_sna/benchmarks/io.py): export một dataset stable/grow với năm CSV; đọc lại rồi ghi metadata cuối, kèm generator config/version/seed, môi trường, counts và hashes.
- [benchmarks/fixtures.py](../../../../src/reddit_sna/benchmarks/fixtures.py): API/CLI tạo hai dataset, dùng chính sách run/output của project; manifest truth-only complete/failed, hash cả metadata.
- [Config truth seed 11](../../../../configs/truth_fixtures.toml), [consumer stdlib](../../../../scripts/read_truth_fixture.py) và [hướng dẫn tái tạo/nhận gói](../001-truth-fixtures/README.md).
- [5 unit test mới](../../../../tests/unit/test_truth_fixture_export.py) và [4 integration test mới](../../../../tests/integration/test_truth_fixtures.py): complete/repeat/no-overwrite, config sai, failure, CLI, reader isolated, hash/semantic corruption.

Seed 11 được ghi nhận với `seed_used_for_truth=false`. Truth vẫn cố định theo thiết kế; seed sẽ dùng ở bước graph. Không coi đổi seed là đã sinh phân hoạch ngẫu nhiên khác.

## Lệnh và output thật

Đã chạy từ root repo:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.fixtures --config configs/truth_fixtures.toml --run-id phuc-001-t06-001
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.fixtures --config configs/truth_fixtures.toml --run-id phuc-001-t06-002
```

Gói chính: `artifacts/detection-tracking/phuc-001-t06-001/`. Gói đối chiếu: `artifacts/detection-tracking/phuc-001-t06-002/`. Mỗi gói có manifest và hai dataset sau:

| Dataset ID | Truth reference | Nodes 2020-01 / 2020-02 | Membership rows | Events / links |
|---|---|---|---|---|
| `dev-stable-easy-g11` | `truth-dev-stable-easy-g11` | 24 / 24 | 48 | 2 / 2 |
| `dev-grow-easy-g11` | `truth-dev-grow-easy-g11` | 24 / 30 | 54 | 2 / 2 |

Mỗi dataset có `metadata.json`, hai `snapshots/<month>/nodes.csv`, ba `truth/{membership,events,links}.csv`. Các nhãn/liên kết chuẩn là A→C stable/grow và K→K stable; tháng cuối không phát sinh event nguồn.

Đã chạy consumer isolated cho cả hai dataset ở **cả hai run**, tổng cộng **4 lần thành công**. Ví dụ ở gói chính:

```powershell
& .\.venv\Scripts\python.exe -I scripts/read_truth_fixture.py artifacts/detection-tracking/phuc-001-t06-001/datasets/dev-stable-easy-g11
& .\.venv\Scripts\python.exe -I scripts/read_truth_fixture.py artifacts/detection-tracking/phuc-001-t06-001/datasets/dev-grow-easy-g11
```

Consumer trả `verified: true`, xác minh hash/header, coverage/duplicate, tập thành viên, counts, events/links và metadata cơ bản. Consumer chỉ import stdlib, không phụ thuộc `reddit_sna` hay notebook.

**Tái lập:** cả 12 file trong hai thư mục `datasets/`, gồm cả metadata, bằng nhau từng byte. Root manifest có run ID/timestamp riêng nên không dùng để so byte giữa hai run.

**Không ghi đè:** gọi lại lệnh run `phuc-001-t06-001` trả exit code 2 với lỗi `already exists`; 13 file của run cũ (manifest + 12 file dataset) giữ nguyên byte.

## Kiểm thử và nghiệm thu

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_synthetic_io tests.unit.test_synthetic_truth tests.unit.test_contracts tests.unit.test_leiden tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures tests.unit.test_config tests.unit.test_artifacts -v
```

**75/75 test pass, 0 skip/failure/error**, unittest 13.847s; subprocess wall 14.959s. Đây là suite liên quan gồm cả chính sách config/artifact hiện có, không phải toàn bộ test của repo.

| Điều kiện PHUC-001 | Bằng chứng |
|---|---|
| AC01 — stable giữ nguyên thành viên dù đổi tên | Unit truth và reader thật: A12→C12, K12 giữ nguyên, stable/stable |
| AC02 — grow giữ 12 và thêm 6 | Unit truth và reader thật: A12→C18, K12, grow/stable |
| AC03 — duplicate/user thiếu/lạ báo lỗi | Suite CSV/fixture hiện có; reader mới còn từ chối sai nhãn/link dù đã cập nhật hash tương ứng |
| AC04 — export tái lập và giữ output cũ | Hai run thật, 12 file dataset bằng byte; repeat run exit 2 giữ nguyên 13 file; unit/integration no-overwrite |
| AC05 — đọc độc lập và có môi trường thực | Bốn lần `python -I` consumer stdlib, metadata có Python/package/config/version/seed; môi trường T01 có [bằng chứng riêng](PHUC-001-T01-environment.md) |

Test failure kiểm chứng: lỗi ghi links không để lại metadata complete dùng được; lỗi export grow đặt run manifest `failed` và giữ dataset stable đã hoàn tất. Các tình huống giả lập được tạo trong thư mục test tạm, không phải lỗi của run chính.

## Artifact và hashes

Artifact kiểm chứng **local, bị Git ignore**, ở `artifacts/verification/phuc-001-t06-001/`:

- `unit-integration-tests.log`, `verification-result.json`: command, số test, thời gian, source base và hashes.
- `export-1.log`, `export-2.log`, bốn `reader-<n>-<scenario>.log`, `repeat-existing-run.log`.
- `fixture-summary.json`: JSON consumer của bốn lần đọc; `verify.py`: runner local tạo/đối chiếu hai run.

SHA-256 file tại thời điểm kiểm tra:

| File | SHA-256 |
|---|---|
| `src/reddit_sna/benchmarks/io.py` | `ecdd6cb8106bf45609b19670aef73a0fe2e73312960475504bf371907f91b6b8` |
| `src/reddit_sna/benchmarks/fixtures.py` | `e8bbbee9d0667ed848081461dd2717d4468cea7eb48627d6258c6af1dc048d72` |
| `src/reddit_sna/benchmarks/__init__.py` | `1541ec3e851608569632848a82e31e594f21f0feb3d19d37d24508b7e278ad67` |
| `scripts/read_truth_fixture.py` | `bcfe90772d1141dd6894c8c71fa1514ef7e71376f50538550380860d27d722f2` |
| `configs/truth_fixtures.toml` | `857bc7f6153d62999fd86b1a06d7b29959ada7689f0ac7942bf3f766d9871f9f` |
| `tests/unit/test_truth_fixture_export.py` | `4c4180d2a6616b8958f33a94235c8bee0289723a2703f53109a3042bdc3ed37a` |
| `tests/integration/test_truth_fixtures.py` | `ae76c98d2a3b1dedfa593724b1a17e428fe673dbe87cafc3411b9c531678e48e` |
| Gói chính: stable `metadata.json` | `79d62e6430953ad5fb796549dc45b034819dfcf569de62dfac37a3877e0b99f6` |
| Gói chính: grow `metadata.json` | `018982550964e2d367e13b3812695f0ed0a175c39299baca6dea81c7b3e75945` |
| Gói chính: `manifest.json` | `8361ad894059407244edefbe0a810bd03f1c1fba4cfdb7025b59222f6b29f1c1` |

Manifest chứa đủ hashes của 12 file dataset; từng metadata chứa hash năm CSV tương ứng. `verification-result.json` lưu thêm hashes source/log/output để đối chiếu nguồn chạy trước commit.

## Phạm vi bàn giao

PHUC-001 đã được Phúc tự nghiệm thu đầy đủ. Gói hiện có là truth stable/grow; bước tiếp theo **PHUC-002-T01** sinh graph stable hai tháng với seed 11. Chưa có benchmark detection/AMI/tracker hoặc xác nhận Đăng đã nhận/accepted gói.

Artifact local không đi theo Git; thành viên khác tái tạo bằng code/config/script đã push hoặc nhận thư mục dataset được chia sẻ riêng theo [hướng dẫn](../001-truth-fixtures/README.md). Không tự đánh EXT-D01 DONE chỉ vì consumer trên máy Phúc pass.
