# Bằng chứng PHUC-006-T02 — hướng dẫn và gói giao dữ liệu cho Đăng

**Trạng thái:** DONE; PHUC-006 **2/6**, tổng Phúc **32/36**. Owner Phúc, 19/10/2026. Nhánh `feat/phuc-006-handoff-demo`, [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11), base trước T02 `2bf7cfe`.

## Đã làm và mục đích

Viết [PHUC-DANG-WEEK1-HANDOFF.md](../../../PHUC-DANG-WEEK1-HANDOFF.md): cách nhận/checksum/giải nén, lệnh consumer thật, actual layout, schema/reference, ví dụ grow seed 11, thứ tự Đăng làm đường A trên truth rồi đường B trên detector seed 0, đầu ra tracker/evaluator cần gửi lại và mẫu receipt/lời nhắn Phúc tự gửi. Phân biệt bản khóa detection Phúc với phần tracker Đăng chưa có artifact; Đăng chỉ dùng evaluation sau khi khóa phần mình.

Tạo **ZIP giao dữ liệu T02**, từ nguyên source runs/inventories T01 và consumer `9ca1064`; kèm bản hướng dẫn đúng bytes. Không thêm tracker, không sinh lại graph/Leiden/AMI và không coi đây là gói notebook cuối T06.

## Gói có thể gửi ngay

- **File local:** `artifacts/handoff/phuc-dang-week1-20261019-001.zip`.
- **821 files, 956.285 byte**; 820 file được hash trong `delivery-manifest.json`, cộng manifest. ZIP đã kiểm tra CRC và từng entry bằng source bytes.
- Có guide, standalone consumer, `runs/development`/`runs/evaluation` đầy đủ **378/434 files**, hai inventories (ba file/split), manifest hash/size toàn gói. Không đưa test logs/proof T01 vào ZIP giao đơn giản này; bằng chứng vẫn giữ riêng.
- Tổng **36 dataset, 72 snapshot, 216 membership CSV**, gồm 72 canonical seed-0 CSV. `partner_acceptance=not_verified`, tracker/notebook chưa có.
- SHA-256 **`e1a611092a8273b30570abdb4f6810ef9e07a0264ab07f0ce69ce4bce3880a14`**; sibling `.zip.sha256`. [Reference đã version](PHUC-006-T02-delivery-reference.json) giữ hash ZIP, guide, consumer, delivery manifest và hai source manifest pins.
- ZIP bị ignore, **chưa upload/chưa gửi Đăng**. Phúc cần gửi ZIP thật và checksum; guide có sẵn trong ZIP. Repo chỉ có guide/reference/bảng nhỏ để nhóm theo dõi.

## Kiểm tra đúng lệnh người nhận sẽ chạy

Đã copy ZIP vào `artifacts/verification/phuc-006-t02-001/recipient-test/`, chạy nguyên các PowerShell blocks/Python block lấy từ guide, bổ sung error-exit guard cho harness:

1. `Get-FileHash`, `Expand-Archive` sang thư mục mới, `Set-Location`, `python --version`, development consumer `python -I -S ...`: exit **0**.
2. Evaluation consumer trên cùng bản giải nén mới: exit **0**. Đây là Phúc xác minh delivery, không xác nhận Đăng đã xem hoặc khóa tracker.
3. `Import-Csv`/lọc canonical grow seed 11/`Select-Object`: exit **0**.
4. API `inspect_synthetic_handoff` của package đã cài, cwd là root gói: exit **0**, counts 18/36/108.
5. Probe Python version: exit **0**.

**Hai bộ index tạo lại giống từng byte** so với inventories giao sẵn, gồm cả metadata; 820 hashes/sizes và manifest pins khớp sau giải nén. Ví dụ grow được đối chiếu CSV thật: 24→30 active/endpoint users, A12→C18 và K12→K12, events A=grow/K=stable, refs trong guide khớp metadata. [Validation 9 checks](PHUC-006-T02-validation.csv) đều PASS; không gọi đây là 9 unit tests.

PowerShell resolve `python` theo PATH là **3.14.4**, được in trong `documented-development.stdout`; API dùng venv **3.12.6**. Probe subprocess trực tiếp từ Python venv resolve **3.12.6** theo cơ chế tìm executable trên Windows. `validation-summary.json` phân biệt các quan sát này; raw `result.json` giữ probe trực tiếp, không dùng trường đó để gán version cho PowerShell CLI.

Mỗi split có **39 truth source events**, support thứ tự stable/grow/shrink/merge/split/dissolve = **21/3/3/6/3/3**. Đã đếm từ mọi `truth/events.csv`; [support CSV 12 dòng](PHUC-006-T02-truth-event-support.csv) theo Git. Đây là phân bố đáp án, **chưa có tracker/F1**, không bỏ K hoặc đổi nhãn để tăng cân bằng.

Không viết unit tests mới cho thay đổi docs/packaging. **Không chạy lại full suite, clean install, notebook hoặc scientific evaluation** ở T02. 51/51 targeted tests là bằng chứng T01 trước đó. **7.664 artifact cũ và 100 code/config/test files cũ giữ nguyên hash**, không sửa producer/config/consumer/tests/freeze gate.

## Bằng chứng và giới hạn

Proof local `artifacts/verification/phuc-006-t02-001/` có plan/baseline, builder/recipient-verifier, command argv/cwd/exit/timing/stdout/stderr, full fresh extraction, support CSV, `result.json`, version clarification `validation-summary.json` và `proof-sha256.json`. Audit hoàn tất **19/10/2026 12:18:00 +07**. Delivery ZIP là artifact gửi Đăng; proof folder này dùng đối chiếu nội bộ, không phải bắt người nhận chạy toàn bộ quy trình của Phúc.

T02/FR01 và hướng dẫn môi trường/lệnh của FR03 đạt. PHUC-006 còn T03 notebook, T04 phân tích case, T05 clean-kernel/clean install phù hợp và T06 chốt bàn giao cá nhân. EXT-D01/02/03/PAIR-DEMO vẫn pending vì chưa có receipt hoặc artifact tracker thật. Không tự gửi tin nhắn hoặc ghi Đăng accepted.

**Tiếp theo: PHUC-006-T03**, tạo notebook detection có nguồn. Đăng có thể bắt đầu development ngay từ ZIP T02, không cần đợi notebook.
