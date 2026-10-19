# PHUC-006-T06 — chốt gói bàn giao phần Phúc

**DONE**, PHUC-006 **6/6**, tổng Phúc **36/36**. Owner Phúc, 19/10/2026; runtime source base `b7b3920`, nhánh `feat/phuc-006-handoff-demo`, [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11). **AC01–AC04 đạt; AC05 đạt nhánh chưa có tracker**, ghi thật phần detection đã hoàn tất và demo cặp chưa accepted. Đây là nghiệm thu tự kiểm tra cá nhân, không ghi thay review/receipt Đăng.

## File cần gửi

**Chỉ cần gửi ZIP cuối `phuc-week1-final-20261019-001.zip`**, kèm SHA-256 hoặc link [reference T06](PHUC-006-T06-final-reference.json). File nằm ở `artifacts/handoff/phuc-week1-final-20261019-001.zip` trên máy Phúc, **10.037.861 byte, 976 files**, SHA-256:

```text
1a6f4d63cd0bd0e6304465a5557eb1ac8b3361300ad5d48dbdf5eb12875e31a3
```

ZIP đã kiểm tra CRC/bytes từng entry, giải nén mới và xác minh đầy đủ inventory/hash/size. Root có `START-HERE.md` và `PHUC-FINAL-MANIFEST.json` (SHA `919d32f61c2bdd633df098dfdc3ae45b235d5d156208756498d7d2f64ab62e8e`); manifest hash 975 file khác, không tự hash chính nó. [Hướng dẫn bắt đầu](../006-handoff-demo/FINAL-START-HERE.md) có cách kiểm tra input, cài wheel và chạy notebook. Gói lớn vẫn local/bị ignore; chưa upload hoặc gửi thay Phúc.

Gói có code/config/scripts/tests, 44 package Python files, notebook nguồn không cache, regular wheel T05, dữ liệu T02 đầy đủ nguyên byte, executed notebook, sáu PNG/SVG/CSV/metadata và full proof T05. Không kèm raw Reddit, venv, Git hoặc toàn task board/specs. `README.md`/`START-HERE.md` là hướng dẫn riêng cho gói; task board/specs hiện tại theo Git. Không phải ZIP toàn bộ repository.

Gói T02 cũ giữ nguyên SHA `e1a611092a8273b30570abdb4f6810ef9e07a0264ab07f0ce69ce4bce3880a14`. Đăng đã có T02 thì dùng tiếp input đó; ZIP cuối bổ sung môi trường replay/kết quả/tài liệu. Guide T02/T04 trong bằng chứng cũ vẫn lịch sử, guide Git và `document/` của ZIP cuối cập nhật T06, hash mới nằm ở reference; không sửa checksum lịch sử để giả rằng ZIP cũ chứa tài liệu mới.

## Kiểm tra thực tế T06

| Bước | Kết quả |
|---|---|
| Staging source/data | 44 Python files khớp wheel/installed T05, configs/notebook/runtime scripts giữ byte; toàn bộ T02 input giữ pins |
| Consumer stdlib trên staging | Development + evaluation đều exit 0, mỗi split 18 dataset/36 snapshot/108 memberships; inventory JSON/CSV giống byte T02 |
| Notebook từ cấu trúc gói | Một fresh kernel bằng clean T05 Python 3.12.6, **10/10 code cells, 6 inline PNG**, **26.161s**; output/report mới, source không cache và không sửa sys.path |
| Đối chiếu replay | **9 CSV/6 PNG** giống byte T05; 216 metrics/42 summary, 198 valid/18 null và canonical 0 không đổi |
| ZIP cuối | 976 entry bytes/CRC đúng; fresh extraction exact inventory/hash/size, links tài liệu trong gói và wheel/input/proof pins đạt |
| Consumer từ fresh extraction | Development + evaluation exit 0 lần nữa, inventory/CSV giống byte T02; tổng **4 consumer invocations** đạt, `partner_acceptance=not_verified` |
| Bảo toàn | **10.539 file artifact dữ liệu/bằng chứng cũ** và **42 frozen source files** giữ byte; không hash lại toàn bộ thư viện venv trong `artifacts/environments` |

Đây là kiểm tra chuyển gói/replay; **không thêm unit tests hoặc chạy full suite mới**, không sinh graph/chạy lại Leiden/AMI production. Gate **385/385 full repo tests, clean install và hai kernels** thuộc T05; full proof T05 đã nằm trong ZIP. T06 tái sử dụng môi trường sạch đó, không giả rằng vừa cài lần nữa hoặc đã thử trên máy Đăng. Source package/config/scripts/notebook giữ nguyên nên không lặp lại full test suite cho thay đổi đóng gói/tài liệu.

File lớn được thử từ staging, sau đó chỉ cập nhật tài liệu đóng gói; ZIP cuối chứa đúng runtime/code/data đã replay. Không rerun notebook chỉ vì đổi tài liệu; fresh extraction đã đối chiếu mọi byte runtime/input và consumer lại. Benchmark freeze vẫn theo driver `09623f1`/source/versions gốc, không nới gate cho package có thêm reporting modules.

## Bằng chứng và giới hạn

[Acceptance matrix 5 dòng](PHUC-006-T06-acceptance.csv), [reference/checksums](PHUC-006-T06-final-reference.json), [guide mục 11](../../../PHUC-DANG-WEEK1-HANDOFF.md#11-chốt-phần-phúc--phuc-006-t06), [báo cáo kết thúc cá nhân](../../../PHUC-WEEK1-COMPLETION.md). Proof local `artifacts/verification/phuc-006-t06-001.zip`: **66 files/2.742.699 byte**, CRC/entry bytes verified, SHA `1ee85f038c192ae78e840b22a59d64a3686a2ad61aed78ef9f3831a1f9670725`. Có commands/logs/four indexes, executed notebook/output copies, baseline/source/doc snapshots, final manifest và audits. Không cần gửi proof ZIP này riêng cho Đăng; ZIP cuối đã kèm full proof T05 để xem gate test/install.

Kết quả chỉ về synthetic detection: mean seed 0 dev **0.955879927**, eval **0.933116751**, coverage **1.0**; thiếu AMI giữ null/reason/support. Merge C24→12/12 và dissolve K12→5/4/3/null đã phân tích. Không có event-F1/confusion, forecast accuracy hoặc Reddit result/novelty được chứng minh bằng lượt này.

**EXT-D01:** Phúc báo đã nhắn Đăng, chưa receipt nhận/đọc ZIP. **EXT-D02/03:** chưa tracker truth/detector/mapping/predictions/metrics. **PAIR-DEMO:** chưa accepted. AC05 chỉ hoàn tất nhánh điều kiện chưa có tracker: chạy độc lập và ghi giới hạn. Khi Đăng giao thật mới ghép hai nhánh A/B, đánh giá và cập nhật mốc chung bằng artifact thật.
