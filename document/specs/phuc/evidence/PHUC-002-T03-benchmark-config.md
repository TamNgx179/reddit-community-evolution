# Bằng chứng PHUC-002-T03 — Cấu hình và lịch benchmark chung

**Task:** [PHUC-002-T03](../tasks.md#phuc-002). **Kết quả:** DONE; PHUC-002 hiện 3/6 task.
**Kiểm tra hoàn tất:** 18/10/2026 10:23:42, Asia/Bangkok (UTC+07:00).
**Môi trường:** `.venv`, Python 3.12.6; source cơ sở `93437d7` cộng thay đổi T03 khi kiểm tra, nhánh `feat/phuc-002-stable-graphs`.

## Vừa làm gì, dùng để làm gì

Đưa công thức chạy chung vào [configs/benchmark_week1.json](../../../../configs/benchmark_week1.json), để thành viên nhóm đọc cùng tham số thay vì tự nhập lại. Seed là mã giúp tái tạo dữ liệu. Bộ phát triển dùng để thử/chỉnh code; bộ evaluation được giữ riêng cho bước đánh giá sau.

Thêm [benchmarks/config.py](../../../../src/reddit_sna/benchmarks/config.py) để đọc/kiểm tra JSON và lập lịch dataset. Bộ đọc không sửa file, không tạo run và không chạy evaluation. TOML `RunConfig` hiện có không thay đổi.

| Nhóm tham số | Giá trị |
|---|---|
| Schema/protocol | schema 1, `synthetic-planted-undirected-v1` |
| Tháng/case/difficulty | 2020-01→2020-02; stable/grow/shrink/merge/split/dissolve; easy |
| Generator | p_in 0.50, p_out 0.02, weight 1.0; sampler 1 và RNG protocol T01 |
| Generator seeds | development 11/12/13; evaluation 101/102/103 |
| Detector | gamma 1.0, seeds 0/1/2, canonical 0 ở đầu danh sách |
| Ordering | Tháng tăng dần, user/cạnh theo thứ tự từ điển, endpoint source < target |

Validator chặn khóa lạ/thiếu/trùng, JSON không hợp lệ, NaN/Infinity, seed sai/trùng/chồng split, probabilities sai, gamma/canonical không hợp lệ và protocol/ordering chưa được hỗ trợ. Schema hiện dùng đủ sáu case theo protocol, hai tháng liên tiếp và easy; thay đổi protocol cần version/consumer phù hợp.

## Lịch dự kiến đã kiểm tra

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.benchmarks.config configs/benchmark_week1.json
```

Lệnh thật trả exit code 0, `scope="benchmark-config"`, `status="valid"`:

- 18 dataset development và 18 dataset evaluation; IDs và generator seeds giữa hai split không trùng.
- Tổng 36 dataset × 2 tháng = 72 snapshot dự kiến.
- 72 snapshot × 3 detector seed = 216 đơn vị detection dự kiến. Detector seeds là các lần chạy trên cùng graph, không phải dataset độc lập.

Ví dụ lịch bắt đầu bằng `dev-stable-easy-g11`; lịch evaluation kết thúc bằng `eval-dissolve-easy-g103`. Thứ tự case rồi seed theo cấu hình, không phụ thuộc thứ tự key JSON.

Đây là **lịch**, chưa phải 36 dataset hoặc 216 kết quả đã chạy. T03 không sinh dữ liệu evaluation và không chạy detector. Khóa cấu hình/evaluation thuộc PHUC-005.

## Mẫu graph thực sự chạy từ cấu hình

Đã dùng `load_benchmark_config` và dataset đầu tiên trong lịch development để gọi sampler, truyền seed/p_in/p_out/tháng từ JSON. Giữ tập user kỳ vọng độc lập của stable: A12 và K12.

| Tháng | Nodes | Cạnh | SHA-256 nội dung R.csv tương đương |
|---|---|---|---|
| 2020-01 | 24 | 76 | `58c34c2a7ba1297a7f536b8b5a55556ee5a8666ab9d65839a6a0876ba1476592` |
| 2020-02 | 24 | 53 | `4ddcba4db3dbedaf4c9b294f522e132d3b17dd690d097bad15e8ac99bd5786dd` |

Hai hash khớp lần chạy T01: chuyển tham số vào config không đổi mẫu graph mặc định. Nội dung CSV được serialize trong bộ nhớ để đối chiếu; không tạo gói graph production mới ở T03. Ví dụ API tái tạo nằm trong [hướng dẫn](../002-dynamic-benchmark/README.md).

## Kiểm thử

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_benchmark_config tests.unit.test_synthetic_truth tests.unit.test_dynamic_benchmark tests.unit.test_synthetic_io tests.unit.test_contracts tests.unit.test_truth_fixture_export tests.integration.test_truth_fixtures -v
```

**80/80 test pass, 0 skip/failure/error**. Unittest 8.139s, subprocess wall 8.766s. Đây là suite liên quan của config/sampler/truth/CSV/export/consumer, không phải toàn bộ test repo.

10 test mới trong [test_benchmark_config.py](../../../../tests/unit/test_benchmark_config.py) kiểm tra schema/defaults, read-only, JSON sai/trùng khóa/số không chuẩn, seed/probabilities/gamma/canonical, tách split/ID, dataset count độc lập số detector seeds, công thức dùng config với sampler và CLI valid/invalid từ ngoài repo. CLI cấu hình overlap trả exit code 2, không đổi input hoặc tạo output.

## Artifact và hashes

Artifact **local, bị Git ignore**, ở `artifacts/verification/phuc-002-t03-001/`:

- `verification-result.json`, `unit-integration-tests.log`: source base, command, test counts, timing, config/source hashes và kết quả sample.
- `benchmark-config-copy.json`: bản sao đúng byte cấu hình khi kiểm tra; không phải bản freeze evaluation của PHUC-005.
- `development-plan.json`, `evaluation-plan.json`: 18 record/lịch, chưa chứa graph hoặc kết quả đánh giá.
- `config-check.log`, `verify.py`: output CLI thực tế và runner local.

SHA-256 tại thời điểm chạy:

| File | SHA-256 |
|---|---|
| `configs/benchmark_week1.json` | `950737dfbc3fc895813c22e1abb64661f67a5ed11b389a9bf502189efa37edfc` |
| `src/reddit_sna/benchmarks/config.py` | `c39511b8f86eacf01975e6e5537ef9372a2b6a5297339f71b68492526fd38ba2` |
| `tests/unit/test_benchmark_config.py` | `2497a28608509476188eb486c5ba303bfefb426f3a0b32474fbf3506a5d45f36` |

Đã đối chiếu byte file config trước/sau thao tác đọc: không đổi. Thành viên khác dùng file/code đã push và lệnh/API ở [README](../002-dynamic-benchmark/README.md) để tái tạo; artifact local không tự đi theo Git.

T03 hoàn thành phần cấu hình FR01/FR04/FR05. Export graph/nodes/truth/metadata/hashes là **PHUC-002-T04** tiếp theo; freeze/evaluation đầy đủ, Leiden/AMI/tracker chưa được nghiệm thu ở task này.
