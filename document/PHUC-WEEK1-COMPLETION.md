# Phúc — kết thúc phần cá nhân tuần 1

**36/36 task cá nhân đã hoàn thành; sáu spec đều 6/6.** Phần của bạn tạo dữ liệu tổng hợp biết trước đáp án, chạy Leiden tìm nhóm qua từng tháng, đo mức khớp với đáp án và chuẩn bị gói để Đăng viết tracker. **Demo chung với Đăng vẫn chưa hoàn thành.**

| Phần | Bạn đã có gì? | Trạng thái |
|---|---|---|
| PHUC-001 | Truth/membership/events/links và fixture stable/grow | DONE 6/6 |
| PHUC-002 | Graph có seed, sáu case stable/grow/shrink/merge/split/dissolve, ground truth | DONE 6/6 |
| PHUC-003 | Independent Leiden từng snapshot, ba seeds, canonical 0 và detector memberships | DONE 6/6 |
| PHUC-004 | AMI/coverage, policy null, bảng metrics/summary và kiểm tra alignment | DONE 6/6 |
| PHUC-005 | Development/freeze/evaluation đã khóa, provenance/hashes và outputs | DONE 6/6 |
| PHUC-006 | Consumer, notebook/case analysis, clean-install gate, gói bàn giao cuối | DONE 6/6 |

[Task board và ledger](specs/phuc/tasks.md) là nguồn trạng thái chính. [Bằng chứng chốt T06](specs/phuc/evidence/PHUC-006-T06-final-handoff.md), [acceptance](specs/phuc/evidence/PHUC-006-T06-acceptance.csv), [checksum/reference](specs/phuc/evidence/PHUC-006-T06-final-reference.json), [hướng dẫn đầu tiên](specs/phuc/006-handoff-demo/FINAL-START-HERE.md).

## Gửi gì cho Đăng?

Gửi **một file `phuc-week1-final-20261019-001.zip`**, ở `artifacts/handoff/` trên máy bạn, khoảng **10 MB**; kèm checksum từ reference. ZIP có **976 files**, dữ liệu/code/wheel/notebook/CSV/hình/log T05. Đăng giải nén, mở `START-HERE.md`, kiểm tra development rồi làm tracker trên truth trước. Nếu Đăng đã có gói T02, input cũ vẫn đúng; không cần đổi dataset/reference.

GitHub có code, docs và bằng chứng nhỏ; ZIP lớn chưa có trên GitHub, chưa tự gửi/upload. Không cần gửi từng ZIP proof riêng. Người nhận cần ZIP thật hoặc gói T02 đã nhận trước; chỉ pull nhánh không tự tải dữ liệu synthetic local.

## Kết quả để bạn trình bày

Toàn lịch **36 dataset, 72 snapshot, 216 metrics**. Canonical seed 0 có AMI mean development **0.955879927**, evaluation **0.933116751**; coverage 1.0. Có **198 AMI valid/18 null** trên cả ba seeds/hai splits, giữ nguyên lý do thiếu. Đây là kết quả detection tổng hợp, chưa phải tracking/forecast/Reddit.

Ví dụ: nhóm chuẩn 24 người bị Leiden chia 12+12 thì coverage vẫn 100% nhưng AMI chỉ 0.724164871. Ở dissolve còn một nhóm truth, policy trả AMI null dù detector chia 5/4/3; null không phải khớp hoàn hảo. Notebook giải thích hai case và nguồn từng hình.

T05: môi trường Python sạch, pip check, **385/385 tests**, hai kernel replays đạt. T06: **4 consumer reads**, notebook gói 10/10 cells/6 hình, CSV/PNG giống T05, ZIP/fresh extraction/hashes đạt. T06 không chạy full suite hoặc benchmark mới; giữ kết quả cũ.

## Còn cần chờ gì?

Phúc đã báo nhắn Đăng; chưa có phản hồi nhận/đọc gói. Còn chờ Đăng cung cấp tracker truth, tracker detector/mapping, predictions và F1/support/confusion. Khi có artifact thật, hai bạn ghép đường A trên truth và B trên Leiden, thử notebook/demo cặp rồi mới cập nhật EXT-D02/03/PAIR-DEMO. Không viết tracker hoặc ghi chỉ số thay Đăng để đóng mốc.

Bạn có thể chuyển sang đồ án môn khác sau khi gửi gói và giữ lại nhánh/ZIP này. Phần phối hợp còn mở được theo dõi riêng trên task board; không còn task PHUC cá nhân đang chờ Đăng.
