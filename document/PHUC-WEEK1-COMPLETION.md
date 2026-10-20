# Phúc — kết thúc phần cá nhân tuần 1

**36/36 task cá nhân đã hoàn thành; sáu spec đều 6/6.** Phần của bạn tạo dữ liệu tổng hợp biết trước đáp án, chạy Leiden tìm nhóm qua từng tháng, đo mức khớp với đáp án và chuẩn bị gói để Đăng viết tracker. **Cập nhật 20/10:** đã ghép code Đăng, hoàn thành demo kỹ thuật 14 cells/8 hình và 94 tests liên quan. [Bàn giao cuối](PHUC-DANG-FINAL-HANDOFF.md), [guide chạy](guide.md). Nghiệm thu của thành viên và artifact/freeze lịch sử gốc Đăng vẫn ghi riêng; các mục T06 bên dưới là lịch sử phần cá nhân.

| Phần | Bạn đã có gì? | Trạng thái |
|---|---|---|
| PHUC-001 | Truth/membership/events/links và fixture stable/grow | DONE 6/6 |
| PHUC-002 | Graph có seed, sáu case stable/grow/shrink/merge/split/dissolve, ground truth | DONE 6/6 |
| PHUC-003 | Independent Leiden từng snapshot, ba seeds, canonical 0 và detector memberships | DONE 6/6 |
| PHUC-004 | AMI/coverage, policy null, bảng metrics/summary và kiểm tra alignment | DONE 6/6 |
| PHUC-005 | Development/freeze/evaluation đã khóa, provenance/hashes và outputs | DONE 6/6 |
| PHUC-006 | Consumer, notebook/case analysis, clean-install gate, gói bàn giao cuối | DONE 6/6 |

[Task board và ledger](specs/phuc/tasks.md) là nguồn trạng thái chính. [Bằng chứng chốt T06](specs/phuc/evidence/PHUC-006-T06-final-handoff.md), [acceptance](specs/phuc/evidence/PHUC-006-T06-acceptance.csv), [checksum/reference](specs/phuc/evidence/PHUC-006-T06-final-reference.json), [hướng dẫn đầu tiên](specs/phuc/006-handoff-demo/FINAL-START-HERE.md).

## Gói T06 cá nhân — lịch sử

File `phuc-week1-final-20261019-001.zip` ở `artifacts/handoff/` là bản lưu đầy đủ phần cá nhân, khoảng **10 MB**, có **976 files**. Đăng đã nhận input T02, không cần gửi lại ZIP này. Bản giao demo kỹ thuật ngày 20/10 dùng gói **kết quả** `phuc-dang-demo-results-20261020-001.zip`, được mô tả trong bàn giao cuối; không thay dataset/reference input cũ.

GitHub có code, docs và bằng chứng nhỏ; ZIP lớn chưa có trên GitHub, chưa tự gửi/upload. Không cần gửi từng ZIP proof riêng. Người nhận cần ZIP thật hoặc gói T02 đã nhận trước; chỉ pull nhánh không tự tải dữ liệu synthetic local.

## Kết quả để bạn trình bày

Toàn lịch **36 dataset, 72 snapshot, 216 metrics**. Canonical seed 0 có AMI mean development **0.955879927**, evaluation **0.933116751**; coverage 1.0. Có **198 AMI valid/18 null** trên cả ba seeds/hai splits, giữ nguyên lý do thiếu. Đây là kết quả detection tổng hợp, chưa phải tracking/forecast/Reddit.

Ví dụ: nhóm chuẩn 24 người bị Leiden chia 12+12 thì coverage vẫn 100% nhưng AMI chỉ 0.724164871. Ở dissolve còn một nhóm truth, policy trả AMI null dù detector chia 5/4/3; null không phải khớp hoàn hảo. Notebook giải thích hai case và nguồn từng hình.

T05: môi trường Python sạch, pip check, **385/385 tests**, hai kernel replays đạt. T06: **4 consumer reads**, notebook gói 10/10 cells/6 hình, CSV/PNG giống T05, ZIP/fresh extraction/hashes đạt. T06 không chạy full suite hoặc benchmark mới; giữ kết quả cũ.

## Phối hợp sau khi chốt kỹ thuật

Đăng đã phản hồi nhận input và gửi tracker/evaluator trong PR #12. Phúc đã merge source, tái lập hai split, đối chiếu predictions và ghép notebook chính. Có thể bàn giao kỹ thuật ngay bằng run tái lập có provenance. Hai artifact/freeze gốc Đăng có thể bổ sung đối chiếu sau; không ghi chúng là đã nhận hoặc tự ghi xác nhận nghiệm thu thay thành viên.

Bạn có thể bàn giao code/guide/notebook/gói kết quả theo bản cuối rồi chuyển sang môn khác. Xác nhận của nhóm theo dõi riêng trên task board; không còn task PHUC cá nhân hoặc công việc ghép kỹ thuật phải chờ Đăng.
