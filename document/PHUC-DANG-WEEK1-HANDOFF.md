# Bàn giao Phúc → Đăng: dữ liệu và detection tuần 1

**Bản hiện tại — 20/10/2026:** demo kỹ thuật đã tích hợp tracker Đăng, chạy notebook chính 14 cells/8 hình và có gói kết quả cuối. [Bàn giao cuối](PHUC-DANG-FINAL-HANDOFF.md), [guide chạy](guide.md). ZIP input T02 cũ giữ nguyên. Các ghi chú review/T06 bên dưới là lịch sử; output tái lập hiện tại đủ để bàn giao, artifact/freeze gốc của Đăng được bổ sung đối chiếu sau.

**Cập nhật 20/10/2026:** Đăng đã gửi source PR #12; Phúc kiểm tra 34 tests và replay hai split thành công, notebook kiểm tra riêng đọc được hai đường. [Review, số liệu và việc còn thiếu](PHUC-DANG-PR12-REVIEW.md). Đăng tiếp tục dùng **ZIP input T02 đã nhận**; không cần Phúc gửi lại ZIP cuối. Hai artifact output gốc của Đăng và `document/guide.md` chưa có trên Git/máy Phúc; chưa merge PR hoặc nghiệm thu demo chung. Nội dung T06 bên dưới là lịch sử chốt phần cá nhân.

**Bản chốt phần Phúc:** 19/10/2026, PHUC-006-T06. Phần dữ liệu tổng hợp/detection và 36 task cá nhân Phúc đã hoàn tất; tracker/mapping/F1/confusion và demo cặp còn chờ artifact Đăng. Notebook/clean-install đã có bằng chứng. **Gửi gói cuối `phuc-week1-final-20261019-001.zip`**, mở `START-HERE.md`; [hướng dẫn đầu tiên](specs/phuc/006-handoff-demo/FINAL-START-HERE.md). Các mục T02/T04 bên dưới giữ lịch sử nguồn; mục 11 chốt T06.

**Tình trạng nhận:** Phúc báo đã nhắn Đăng; chưa có receipt nhận/đọc ZIP, xác nhận mặc định v1, tracker hoặc demo chung. Tự kiểm tra gói thành công không thay phản hồi người nhận. Đăng có thể dùng development ngay; nếu đã có gói T02 thì tiếp tục dùng input đó nguyên byte.

## 1. Phúc gửi gì, Đăng làm gì trước?

Phúc gửi file **`phuc-dang-week1-20261019-001.zip`** trong `artifacts/handoff/` trên máy Phúc, kèm SHA-256 của ZIP. [Reference công khai trong nhánh PR #11](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/specs/phuc/evidence/PHUC-006-T02-delivery-reference.json) ghi checksum/kích thước đã đối chiếu. ZIP chứa toàn bộ input thật và consumer, không yêu cầu người nhận clone repo để đọc CSV. `artifacts/` bị ignore, nên **ZIP không có sẵn khi clone GitHub**; Phúc cần gửi file này thật qua kênh chia sẻ của nhóm.

Đăng làm theo thứ tự:

1. Nhận ZIP, đối chiếu SHA-256, giải nén vào thư mục mới; kiểm tra development bằng lệnh mục 2.
2. Đọc `dev-stable-easy-g11` và `dev-grow-easy-g11`, gom membership thành tập user của từng `(reference_id, month, community_id)`.
3. Viết Jaccard trên **truth membership** trước, rồi kiểm tra đủ sáu case development. So với truth events/links ở bước đánh giá; không đưa đáp án vào tracker.
4. Chạy tracker trên **detector seed 0**, giữ reference riêng; thêm mapping nguồn truth–detector để đánh giá toàn luồng.
5. Gửi lại code/config, predictions, bảng chỉ số và một phản hồi nhận gói theo mục 8. Khóa tracker/evaluator trước khi xem hoặc dùng evaluation để đánh giá.

Phúc sửa lỗi graph/truth/Leiden/AMI; Đăng sửa tracker, precedence, mapping và event metrics. Khi gặp lỗi dữ liệu, báo dataset/tháng/file, lệnh, traceback hoặc hàng CSV gây lỗi để Phúc xử lý.

## 2. Mở gói và kiểm tra ngay

Môi trường đọc gói: **Python 3.11+**, chỉ standard library; không cần cài igraph, Leiden hoặc sklearn để chạy consumer. Đã kiểm tra standalone ở Python 3.12.6 tại T01; T02 ghi thêm kết quả thử ở máy giao. Đây là kiểm tra đọc gói, chưa phải thử cài toàn bộ repo trên máy Đăng.

Trên PowerShell, tại thư mục chứa ZIP:

```powershell
Get-FileHash -LiteralPath .\phuc-dang-week1-20261019-001.zip -Algorithm SHA256
Expand-Archive -LiteralPath .\phuc-dang-week1-20261019-001.zip -DestinationPath .\phuc-dang-week1
Set-Location .\phuc-dang-week1
python --version
python -I -S .\consumer.py .\runs\development --expected-manifest-sha256 34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e --output .\check-development-001
```

So sánh kết quả `Get-FileHash` với SHA-256 Phúc gửi/reference; khi chưa khớp thì nhận lại gói. Chọn destination/output mới nếu tên đã tồn tại; không dùng `-Force` hoặc sửa output cũ để vượt kiểm tra.

Consumer thành công exit **0**, in JSON có `status="complete"`, `split="development"`, `counts={datasets:18,snapshots:36,snapshot_detector_runs:108}` và `partner_acceptance="not_verified"`. Thư mục `check-development-001/` có `inventory.json`, `snapshot_inventory.csv`, `metadata.json`. Có thể so với `inventories/development/` đã kèm trong ZIP. Consumer từ chối input sai/output có sẵn bằng exit **2**, in lỗi trên stderr, không có success JSON.

Consumer kiểm tra hashes/sizes, completeness, khóa membership, references, endpoint coverage, truth events/links và đủ ba detector seeds. Nó không chạy lại generator, Leiden, AMI hoặc tracker. Không dùng JSON thành công để kết luận Đăng đã review hoặc F1 đã đạt.

Evaluation đã được Phúc chạy sau khi khóa detection. Với Đăng, chỉ mở/sử dụng tập này **sau khi lưu bản khóa tracker/evaluator**; bản khóa của Phúc không tự khóa phần Đăng. Lệnh kiểm tra evaluation, thực hiện ở giai đoạn đó:

```powershell
python -I -S .\consumer.py .\runs\evaluation --expected-manifest-sha256 e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c --output .\check-evaluation-001
```

Không đổi ngưỡng/seed rồi tiếp tục gọi cùng tập đã xem là evaluation chưa từng dùng. Nếu đã mở để chọn quy tắc, ghi rõ việc đó và giới hạn khi báo kết quả.

## 3. Layout thật và file cần đưa vào tracker

Trong thư mục giải nén:

```text
PHUC-DANG-WEEK1-HANDOFF.md       # chính tài liệu này
consumer.py                    # consumer stdlib, bytes từ code 9ca1064
delivery-manifest.json         # hash/size mọi file khác trong gói
inventories/
  development/                 # inventory.json, snapshot_inventory.csv, metadata.json
  evaluation/
runs/
  development/                 # run phuc-005-t05-development-001, manifest giữ nguyên
    manifest.json
    inputs/source/<dataset_id>/
      metadata.json
      benchmark-config.json
      snapshots/2020-01/{R.csv,nodes.csv}
      snapshots/2020-02/{R.csv,nodes.csv}
      truth/{membership.csv,events.csv,links.csv}
    inputs/detected/<dataset_id>/
      metadata.json
      detector-config.json
      detection.json
      memberships/2020-01/membership-seed{0,1,2}.csv
      memberships/2020-02/membership-seed{0,1,2}.csv
    evaluation/                # detection_metrics.csv, detection_summary.csv, timing, policy, metadata
    provenance/                # source/environment/config bằng chứng của run cũ
  evaluation/                  # run phuc-005-t06-evaluation-001, cùng layout, có thêm freeze/
```

Các dấu `{...}` trong cây là viết gọn tên file, không phải tên thư mục thật. Mỗi split có **18 dataset, 36 snapshot, 108 membership CSV**; cả gói có **36/72/216**, trong đó **72 CSV canonical seed 0**. Detector seeds là các lượt chạy trong cùng dataset, không phải dataset mới.

`inventories/<split>/snapshot_inventory.csv` là bản đồ chính. **Mọi path trong bảng tính từ `runs/<split>/`**, không tính từ thư mục inventory. Chọn đúng hàng canonical để nối hai tháng; không thay absolute paths máy Phúc trong metadata để đọc dữ liệu sau relocation.

Ví dụ lấy hai hàng cho grow bằng PowerShell, tại root gói:

```powershell
$index = Import-Csv .\inventories\development\snapshot_inventory.csv
$index | Where-Object { $_.canonical -eq 'True' -and $_.dataset_id -eq 'dev-grow-easy-g11' } | Select-Object month,truth_reference,detector_reference,truth_membership_file,detector_membership_file
```

| Muốn làm gì? | File tương đối từ root gói, ví dụ grow seed 11 |
|---|---|
| Tracker trên truth, đường A | `runs/development/inputs/source/dev-grow-easy-g11/truth/membership.csv` gồm cả hai tháng |
| Đáp án cho evaluator đường A/B | `runs/development/inputs/source/dev-grow-easy-g11/truth/events.csv` và `truth/links.csv` |
| Tracker trên detector, đường B | Hai file `runs/development/inputs/detected/dev-grow-easy-g11/memberships/<month>/membership-seed0.csv` |
| Tháng quan sát/reference/identity | `metadata.json` ở hai dataset directories trên, đối chiếu inventory |
| Node hoạt động và cạnh | `runs/development/inputs/source/dev-grow-easy-g11/snapshots/<month>/nodes.csv` và `R.csv` |
| Xem AMI/coverage detection đã tính | `runs/development/evaluation/detection_metrics.csv`, lọc dataset/month/seed 0 |

Đường A chỉ cần truth membership làm input tracker. Đường B dùng detector membership; không dùng truth để sửa nhóm detector. Mapping với truth chỉ thuộc evaluator đường B.

## 4. Schema và reference phải giữ

CSV UTF-8, có header; community ID có phạm vi theo tháng. Khóa mẫu tracker là `(reference_id, source_month, source_community_id, target_month)`, phải giữ thêm `dataset_id` khi ghép nhiều dataset thành một bảng.

| File | Header đúng thứ tự | Quy tắc |
|---|---|---|
| nodes | `month,user_id` | Có cả isolate, mỗi user một hàng/tháng |
| R | `month,source_user_id,target_user_id,weight` | Vô hướng, một chiều canonical, không self-loop/cạnh trùng, weight 1 |
| Membership truth/detector | `reference_id,month,community_id,user_id` | Mỗi reference/month/user đúng một nhóm |
| Events truth/predicted | `reference_id,source_month,source_community_id,target_month,event` | Mỗi nguồn có successor quan sát được đúng một nhãn |
| Links truth/predicted | `reference_id,source_month,source_community_id,target_month,target_community_id` | Mỗi cặp nguồn–đích một dòng; split nhiều links, dissolve không có link |

Reference thật của `dev-grow-easy-g11`:

```text
truth-dev-grow-easy-g11
dev-grow-easy-g11:synthetic-planted-undirected-v1:b7482417aac29cf74606f5ef9b262f1448ef62ff0eb7f300a856bdb16faaf26c:leiden-rb-v2-gamma1-seed0
```

Reference đầu là truth, reference sau là detector seed 0. Mỗi reference giữ qua hai tháng. Không đổi reference cho giống nhau; không nối hai seed hoặc hai dataset, dù user/community strings có thể trùng. Với detector, hai CSV tháng phải được ghép trong cùng reference trước khi tracking.

Trong ví dụ thật này, tháng 01 có **24** active/assigned users, tháng 02 có **30**, cả hai không có isolate. A gồm 12 người thành C gồm 18 người; K gồm 12 người giữ nguyên. File events có A=`grow`, K=`stable`; links có A→C và K→K. Đây là **đáp án dữ liệu để kiểm tra**, chưa phải dự đoán từ tracker Đăng.

Truth bao phủ toàn active nodes; detector chỉ gán endpoint R, isolate không tự có nhóm. Nếu tháng sau không được quan sát thì không gán dissolve; nếu tháng vẫn được quan sát nhưng graph/membership rỗng thì xử lý theo contract và ghi diagnostics. Tháng cuối không tự trở thành mẫu nguồn.

## 5. Lịch dữ liệu, cấu hình và kết quả detection đã có

Sáu case theo thứ tự **stable, grow, shrink, merge, split, dissolve**; mỗi dataset hai tháng giả lập `2020-01`, `2020-02`, có nhóm nền K cũng được chấm.

| Tập | Generator seeds | Detector seeds / seed chính | Run ID gốc |
|---|---|---|---|
| Development | 11, 12, 13 | 0, 1, 2 / **0** | `phuc-005-t05-development-001` |
| Evaluation | 101, 102, 103 | 0, 1, 2 / **0** | `phuc-005-t06-evaluation-001` |

Graph: `synthetic-planted-undirected-v1`, easy, `p_in=0.50`, `p_out=0.02`, weight 1; Leiden RB gamma 1.0. Seed chính đã chốt là 0; không chọn seed điểm cao nhất. Run manifests/config/provenance/freeze giữ nguyên trong ZIP.

Mỗi split có **39 nguồn truth** cần chấm sự kiện: support theo thứ tự sáu nhãn là **21, 3, 3, 6, 3, 3**. Đây là số dòng đáp án events, không phải support dự đoán hoặc kết quả F1. Có 21 stable vì nhóm nền K ở cả 18 dataset cùng ba nguồn A của case stable. Không bỏ K để làm bảng cân bằng hơn.

AMI mean canonical development **0.955879927**, evaluation **0.933116751**, coverage mean 1.0. Mỗi split/seed có 33 AMI valid và 3 null; cả ba seeds có 99 valid/9 null. Null dissolve tháng cuối do truth constant theo policy, không điền AMI bằng 1 và không coi là lỗi pipeline. Đây là chỉ số **detection trên dữ liệu tổng hợp**, không phải event-F1 hoặc kết quả Reddit. Timing/phiên bản và null reason có trong report; peak memory chưa đo.

## 6. Quy tắc tracker/evaluator v1 để Đăng triển khai

Đây là mặc định đề xuất trong [phân công cặp v1](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/PHAN-CONG-PHUC-DANG-TUAN-1.md), **không phải code tracker đã chạy**:

- Jaccard `|A ∩ B| / |A ∪ B| >= 0.30`: giữ mọi links đạt ngưỡng, gồm cả bằng ngưỡng.
- Khi successor được quan sát: không đích → dissolve; từ hai đích → split; đúng một đích nhưng đích nhận từ nhiều nguồn → merge; còn lại so thay đổi kích thước. Tăng **trên 10%** → grow, giảm **dưới -10%** → shrink, hai biên ±10% vẫn stable. Split ưu tiên merge, ghi cờ many-to-many.
- Test đủ sáu case, ngưỡng bằng 0.30, hai biên ±10%, thiếu successor, empty observed month và many-to-many. API tracker/module Đăng chọn và ghi rõ trong bàn giao; `tracking/jaccard.py`, `evaluation/tracking.py` là vị trí dự kiến, chưa có implementation trong nhánh Phúc.
- Đường A: chấm toàn bộ 39 nguồn truth mỗi split, gồm K; macro-F1 sáu nhãn cố định, `zero_division=0`, precision/recall/F1/support từng lớp, confusion **6×6**. Thiếu output là lỗi/missing cần báo, không bỏ mẫu.
- Đường B: greedy one-to-one matching **ở tháng nguồn**, Jaccard >= 0.30, giảm dần score rồi tăng truth ID/detector ID khi hòa. Nguồn truth không ghép được hoặc thiếu predicted event vẫn giữ hàng, `y_pred=__unmatched__`; confusion **6×7** với cột unmatched cuối. Báo matched coverage/nhóm detector dư; unmatched không phải sự kiện thứ bảy của tracker.

Không thêm ngưỡng AMI/F1 tùy ý làm điều kiện hoàn thành. Nếu đổi mặc định, ghi cấu hình/version/lý do và ảnh hưởng trước lượt đánh giá; phản hồi Phúc phần interface cần cập nhật.

## 7. Môi trường và API đã kiểm tra

Môi trường **đã sinh/chấm** dữ liệu: CPython **3.12.6**, package 0.1.0, igraph **1.0.0**, leidenalg **0.12.0**, sklearn **1.9.1**, numpy **2.5.4**, scipy **1.18.1**, Windows 11. Đây là provenance của run, không phải dependencies bắt buộc để đọc CSV.

Consumer lấy nguyên bytes từ code `9ca1064`, SHA-256 **`628fac71936509b36d134c3719182998296918469db6536b38c1f9c55b7d2725`**. T01 có 51/51 targeted tests pass; T02 chỉ thử hướng dẫn/đóng gói trên dữ liệu cũ, không chạy lại benchmark hoặc full test suite.

Nếu đã cài package từ nhánh `feat/phuc-006-handoff-demo`, API đọc tương đương, với cwd là root gói giải nén:

```python
from pathlib import Path
from reddit_sna.reporting.synthetic_handoff import inspect_synthetic_handoff

info = inspect_synthetic_handoff(
    Path("runs/development"),
    expected_manifest_sha256="34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e",
)
print(info["counts"])
```

Nguồn benchmark tái lập là driver **`09623f1`**, package 42 file đã khóa tại **`d4fe76b`** và versions trên; source/config/manifest nằm trong run archives. Nhánh PHUC-006 thêm reporting module, nên không dùng current-runtime freeze gate để sinh lại benchmark rồi nới gate khi bị từ chối. Đọc kết quả có sẵn bằng consumer là đường đi ngắn để Đăng bắt đầu. Hướng dẫn replay benchmark: [PHUC-005](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/specs/phuc/005-reproducible-runs/README.md).

## 8. Đăng gửi lại gì để Phúc ghép?

| Phần | Đầu ra cần Đăng cung cấp |
|---|---|
| Receipt đọc gói | ZIP SHA-256, Python version, dataset/run, lệnh và kết quả thật hoặc traceback |
| Tracker | Commit/nhánh, module/API thực tế, config Jaccard/growth/precedence, seed nếu dùng, lệnh chạy/tests |
| Đường A trên truth | `events.csv`, `links.csv`, diagnostics; macro-F1, per-class metrics/support và confusion 6×6 có thứ tự nhãn |
| Đường B trên detector 0 | Events/links detector, `source_mapping.csv`, `event_predictions.csv` giữ đủ nguồn truth; unmatched/matched coverage/nhóm dư, metrics và confusion 6×7 |
| Ghép notebook | Lệnh hoặc hàm module có input/output rõ, bảng/hình có nguồn, một case sai/khó hoặc null finding, giới hạn đã biết |

Không ghi vào source run Phúc giao; tạo output tracker mới, giữ run/dataset/reference/config/hash của input trong metadata. Phúc sẽ ghép module sau khi nhận artifact thật. Nếu chỉ xong development hoặc đường A, ghi đúng phần đã làm; không cần đợi đủ toàn bộ mới phản hồi.

Mẫu phản hồi Đăng có thể copy, tự điền sau khi chạy:

```text
Gói nhận: phuc-dang-week1-20261019-001.zip
SHA-256 thực tế:
Python version:
Lệnh đã chạy:
Exit code/kết quả hoặc lỗi:
Dataset/reference đã đọc:
Nhận được/đang lỗi ở:
Nhánh/module/API tracker và mốc giao tiếp:
```

Phúc chỉ cập nhật EXT-D01/02/03 và PAIR-DEMO sau phản hồi/artifact thật. [Task board](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/specs/phuc/tasks.md) là nơi theo dõi; phần cá nhân hiện qua T02, notebook/analysis/clean-kernel/chốt gói cuối còn T03–T06. [PR #11](https://github.com/TamNgx179/reddit-community-evolution/pull/11) đang mở, chưa merge.

## 9. Lời nhắn để Phúc tự gửi kèm ZIP

> Đăng ơi, mình đã có đủ dữ liệu tổng hợp sáu case, truth và membership Leiden seed 0 để bạn làm tracker. Mình gửi ZIP kèm SHA-256 và hướng dẫn này; bạn giải nén, chạy lệnh kiểm tra development ở mục 2 rồi bắt đầu stable/grow seed 11 trước nhé. Bạn làm Jaccard và đánh giá trên truth trước, sau đó ghép detector/mapping. Evaluation giữ lại chỉ dùng sau khi bạn khóa tracker/evaluator. Bạn phản hồi giúp mình Python version, lệnh đọc và kết quả hoặc lỗi; phần notebook mình làm tiếp nên bạn không cần chờ. Schema, paths và đầu ra cần gửi lại đều có trong tài liệu.


## 10. Bổ sung phân tích detection — PHUC-006-T04, 19/10/2026

**Bản cập nhật trên Git:** mục 1–9 phía trên là nguyên văn guide T02, kể cả trạng thái lịch sử “qua T02”. Hiện đã bổ sung notebook T03 và case analysis T04; T05 clean environment/replay và T06 chốt gói còn riêng. ZIP `phuc-dang-week1-20261019-001.zip` giữ nguyên bytes/checksum, vẫn chứa guide T02; `guide_sha256` trong reference T02 chỉ tới bản guide nằm trong ZIP cũ, không phải tài liệu Git đã thêm mục 10 này. Không cần đổi input tracker hoặc chờ gói dữ liệu khác để bắt đầu.

Mở [notebook](../notebooks/detection_tracking/01_synthetic_demo.ipynb), mục 7. Helper `reporting/synthetic_cases.py` chỉ đọc graph/truth/membership/metrics đã hash trong bundle T02, không sinh graph, chạy lại Leiden hoặc tính AMI. Chọn **development, seed 0**, dòng AMI hợp lệ thấp nhất; hòa thì dataset ID/tháng tăng dần. Case null đầu tiên theo dataset/tháng. Đây là **phân tích post-hoc**, không phải một test set mới hoặc lý do chọn lại gamma/seed. Evaluation đã khóa vẫn giữ nguyên bảng chung, không dùng để chọn hai ví dụ này.

| Trường hợp và nguồn | Quan sát từ input thật | Ý nghĩa/giới hạn |
|---|---|---|
| `dev-merge-easy-g11`, `2020-02`, generator 11/detector 0 | 36 active users, 185 cạnh; truth `C=24, K=12`, Leiden `c0=12, c1=12, c2=12`; C vào c0/c1 mỗi nhóm 12, K vào c2. AMI ghi sẵn **0.7241648712463861**, coverage **1.0** | Có **144 cặp** cùng truth C nhưng khác nhóm detector; 0 cặp khác truth mà cùng detector, trên 630 cặp được xét. Đây là chia nhỏ nhóm tại một snapshot, chưa phải tracker dự đoán sự kiện split. Coverage đủ không chứng minh phân hoạch đúng |
| Cạnh case merge theo nhóm detector | c0: **46/66**, c1: **42/66**, c2: **41/66** cạnh trong nhóm; c0–c1: **52/144**; c0–c2 và c1–c2: mỗi cặp nhóm **2/144** | Density là cạnh thực/số cạnh có thể nối. Hai phần của C có mật độ cạnh nội bộ cao hơn mật độ cạnh giữa chúng trong graph này. Đây là mô tả quan sát, chưa chứng minh nguyên nhân tối ưu của Leiden hoặc cơ sở tuning sau đánh giá |
| `dev-dissolve-easy-g11`, `2020-02`, generator 11/detector 0 | 12 active users, 25 cạnh; truth chỉ `K=12`, Leiden chia **5/4/3**. Coverage **1.0**; AMI **null**, status `degenerate_partition`, reason `truth_constant` | Policy `synthetic-ami-v1` đã khóa không chấm AMI cho truth hằng. Hai phân hoạch vẫn khác: **47/66 cặp** cùng truth bị tách; không điền AMI bằng 0/1 hoặc bỏ hàng thiếu khỏi support |

Paths được lấy từ inventory, tương đối với `runs/development`: `inputs/source/<dataset>/snapshots/2020-02/{R,nodes}.csv`, `inputs/source/<dataset>/truth/membership.csv`, `inputs/detected/<dataset>/memberships/2020-02/membership-seed0.csv`; AMI/coverage từ `evaluation/detection_metrics.csv`, policy từ `evaluation/ami-policy.json`. Run nguồn `phuc-005-t05-development-001`, manifest SHA `34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e`. Mỗi hình có ledger paths/hash riêng. Hình vẽ toàn bộ nodes/cạnh, contingency là số user truth × detector, **không phải confusion matrix sự kiện**; ID/màu nhóm chỉ dùng trong từng panel.

Notebook lưu bốn hình/bảng replay vào output mới, phân tích hai case vào thư mục cùng cấp có đuôi `-cases` với PNG/SVG, CSV contingency/edge blocks/summary, analysis JSON và metadata riêng. [Bằng chứng T04 và preview](specs/phuc/evidence/PHUC-006-T04-case-analysis.md) ghi run, kiểm chứng và đường dẫn đầy đủ. Các kết luận chỉ về detection tổng hợp; chưa có F1/confusion tracker, forecasting hoặc Reddit. Phúc báo đã nhắn Đăng; việc nhận/đọc gói và demo chung vẫn chờ bằng chứng thật.

## 11. Chốt phần Phúc — PHUC-006-T06

**Phần cá nhân Phúc hoàn thành 36/36, PHUC-006 6/6**: truth/graph sáu case, Independent Leiden, AMI/coverage, reproducible development/freeze/evaluation, consumer, notebook, case analysis và clean replay. Đây là nghiệm thu tự kiểm tra phần detection; chưa phải Đăng/nhóm đã review hoặc demo cặp hoàn thành.

Gói cuối trên máy Phúc: `artifacts/handoff/phuc-week1-final-20261019-001.zip`, kèm `.sha256`. [Reference T06 trên Git](https://github.com/TamNgx179/reddit-community-evolution/blob/feat/phuc-006-handoff-demo/document/specs/phuc/evidence/PHUC-006-T06-final-reference.json) có SHA-256/kích thước/manifest/checks thật; checksum ZIP nằm ngoài ZIP để tránh tự tham chiếu. Mở `START-HERE.md` trong root giải nén. Git có code, specs, bằng chứng nhỏ và hướng dẫn; ZIP lớn vẫn local, cần Phúc tự gửi file qua kênh nhóm. Không cần gửi từng proof ZIP riêng cho Đăng.

Gói cuối gồm source/scripts/config/tests, notebook không cache, wheel đã kiểm tra T05, dữ liệu T02 nguyên byte, sáu hình/CSV/metadata, executed notebook và full proof T05. `PHUC-FINAL-MANIFEST.json` ghi inventory/hash/size/nguồn và trạng thái cá nhân/phối hợp; đây là gói runtime cho synthetic detection, không kèm raw Reddit, Git metadata hoặc môi trường `.venv`. Toàn bộ task board/specs theo dõi trên Git; báo cáo T04/T05 trong gói giữ mốc lịch sử của từng task.

Kiểm tra đóng gói đọc hai source runs bằng consumer stdlib và replay notebook từ cấu trúc gói mới bằng kernel sạch, không sinh graph/chạy lại Leiden/AMI production. Khi thử nhận lại ZIP, kiểm tra CRC/entry bytes/inventory/pins và consumer trên bản giải nén mới. Kết quả/counts/durations/checksum thực tế ở reference T06; gate **385/385 tests và clean install** là kết quả T05 đã kèm, không báo là full suite mới T06. Runtime source/config/notebook và original scientific freeze giữ nguyên.

Kết quả detection đã khóa: **36 dataset/72 snapshot/216 metrics**, **198 valid/18 null**, seed chính **0**; canonical mean development **0.955879927**, evaluation **0.933116751**, coverage **1.0**. Mean bỏ null nhưng support/reason vẫn giữ. Case merge C24→12/12 và dissolve K12→5/4/3/null đã giải thích ở mục 10; coverage đủ không đảm bảo nhóm đúng, null không có nghĩa hoàn hảo. Timing là producer wrapper scopes đã ghi, không phải thời gian notebook; peak memory chưa đo. Không có event-F1, forecasting hoặc Reddit result trong phần nghiệm thu này.

**AC01–AC04:** đạt theo consumer/kernel/nguồn bảng-hình/case analysis. **AC05:** đạt nhánh điều kiện “chưa có tracker”: detection chạy độc lập, thiếu artifact được ghi thật. AC05 không biến demo cặp thành accepted. EXT-D01 vẫn chưa receipt; EXT-D02 tracker truth, EXT-D03 tracker detector/mapping và PAIR-DEMO vẫn pending. Khi Đăng giao thật, kiểm tra nhánh/commit/config/reference/predictions, ghép hai nhánh A/B và đánh giá bằng kết quả thật; không tạo số thay thế để đóng mốc.
