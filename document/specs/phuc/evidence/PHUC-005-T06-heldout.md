# Bằng chứng PHUC-005-T06 — evaluation giữ lại theo khóa T05

**Trạng thái:** DOING; driver/control-flow đã có, production evaluation chưa ghi nhận hoàn tất.
**Owner:** Phúc. **Source cơ sở:** `59f8282`, nhánh `feat/phuc-005-reproducible-runs`, PR #10.

Freeze bắt buộc: `phuc-005-t05-freeze-001`, manifest SHA-256 `8c3749cce905e5d416929bddd931cbb4a7104f047ad9273ab22561d5ccdf8ff9`, frozen source `d4fe76b`, thời điểm 19/10/2026 10:58:31 +07. Không sửa package/config/policy/canonical sau khóa.

Driver ngoài package được kiểm tra bằng identity-only stubs trước production, không tạo graph/truth/metric values giữ lại. Kế hoạch: một production run đủ 18 evaluation datasets seeds 101/102/103, 36 snapshot/108 metric rows; không đặt ngưỡng điểm hay chọn valid/null counts. Test/plan/source/log ở `artifacts/verification/phuc-005-t06-001/`. Production dùng driver đã commit sạch; sau khi đọc/audit sẽ lưu mọi kết quả, đối chiếu với development T05 thành 36/72/216 và cập nhật task/evidence.

**Kiểm tra trước production:** 25/25 targeted tests pass, 0 skip/failure/error, 106.216s; 8 driver tests bằng stubs, 7 freeze integration fixtures chỉ dùng development, 10 protocol unit. Không chạy lại full repo suite T06. Package source/config vẫn giữ nguyên hashes T05; driver sẽ được commit trước lần đầu chạy evaluation thật.
