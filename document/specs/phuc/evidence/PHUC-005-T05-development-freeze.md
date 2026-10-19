# Bằng chứng PHUC-005-T05 — full development và khóa protocol

**Trạng thái:** DOING; API/CLI freeze đang kiểm chứng, formal production run chưa ghi nhận hoàn tất.
**Owner:** Phúc. **Source cơ sở:** `6c3a7e1`, nhánh `feat/phuc-005-reproducible-runs`, PR #10.

**Kiểm tra code trước production:** 40/40 targeted tests pass, 0 skip/failure/error, 163.199s; gồm 7 freeze integration, 22 benchmark integration, 1 provenance unit và 10 protocol unit. Không chạy lại full repo suite T05. Log/source snapshots được giữ trong proof. Code đã kiểm tra sẽ được commit trước production để ghi clean source revision trong freeze.

T05 chạy đủ 18 development datasets với protocol đã chốt từ T01, giữ mọi điểm thấp/null, rồi tạo freeze run riêng trước evaluation. [Hướng dẫn](../005-reproducible-runs/README.md#chạy-đủ-development-và-tạo-bản-khóa--t05) và [contract](../contracts.md) mô tả API/CLI, source/version gate và phạm vi khóa. Không đổi recipe, scoring/split/summary policy hoặc canonical seed; T06 mới chạy giữ lại.

Lượt production sẽ dùng code đã commit, working tree sạch. Test/evidence ở `artifacts/verification/phuc-005-t05-001/`; full logs/run/source/ZIP local không tự có trên máy thành viên. Sau kiểm chứng sẽ cập nhật kết quả, thời điểm, hash và CSV thực tế tại file này cùng task board; chưa có tracker/receipt/review Đăng.
