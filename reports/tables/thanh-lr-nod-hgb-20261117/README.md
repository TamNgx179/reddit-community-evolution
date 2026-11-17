# LR đầy đủ, LR bỏ D và HGB trên cùng tập ca

Ngày: 17/11/2026 · Người làm: Thanh

## Cách tái tính

```
python scripts/compare_lr_nod_hgb.py --out reports/tables/thanh-lr-nod-hgb-20261117
```

- Nguồn: các bảng confusion đã lưu trong `reports/tables/midterm2-20261104` (A1 theo tháng, A2 theo lịch sử). Không fit lại mô hình.
- Mô hình: `hier_lr_dynamic` (LR đầy đủ), `A_no_dynamics_matched` (LR bỏ 9 trường D), `hier_hgb_dynamic` (HGB).
- Cùng tập ca: cửa sổ final 2018-01..09, có 1,269 mẫu. Mọi tầng đều có cùng n cho cả ba mô hình.
- Kiểm chứng: Macro-F1 và n tái tính khớp bản lưu, lệch lớn nhất 8e-17 (`audit.csv`).
- Seed 42–44 cho kết quả giống hệt nhau (`seed_spread.csv`), nên các số bên dưới là của một seed.
- Giới hạn: bảng confusion không có khóa từng ca. Vì vậy chỉ so được số lượng trong từng tầng, không chỉ ra được chính xác ca nào đổi nhãn.

## Kết quả chính

| | LR đầy đủ | LR bỏ D | HGB |
| --- | ---: | ---: | ---: |
| Macro-F1 | **0.412** | 0.364 | 0.388 |
| Tổng số lỗi | 121 | **105** | 115 |
| grow đúng / 19 | 3 | 0 | 3 |
| merge đúng / 15 | 3 | 2 | 3 |
| grow → dissolve | 14 | 17 | **12** |
| merge → dissolve | **8** | 11 | 9 |
| grow+merge → dissolve | 22 | 28 | **21** |
| dissolve bị đoán sai / 1,167 | 64 | **39** | 55 |

- Bỏ D làm Macro-F1 giảm 0.048 và làm mất toàn bộ grow (recall về 0).
- Bỏ D lại có ít lỗi hơn vì gần như đoán mọi ca là dissolve. Đổi lại, nó sai thêm 6 ca grow/merge → dissolve.
- So với HGB, LR hơn về Macro-F1. Số ca grow/merge bị đoán dissolve thì gần bằng nhau (22 so với 21).

## Ảnh hưởng của D theo lịch sử

| Tầng | n | LR | LR bỏ D | Δ D | grow+merge → dissolve (LR / bỏ D / HGB) |
| --- | ---: | ---: | ---: | ---: | --- |
| Lineage có lịch sử | 105 | 0.425 | 0.348 | +0.077 | 0 / 2 / 1 |
| Lineage thiếu lịch sử | 1,164 | 0.393 | 0.340 | +0.053 | 22 / 26 / 20 |
| Có lịch sử hoạt động thành viên | 730 | 0.414 | 0.357 | +0.057 | 9 / 15 / 8 |
| Thiếu lịch sử hoạt động thành viên | 539 | 0.200 | 0.205 | −0.005 | 13 / 13 / 13 |

- D vẫn có ích khi thiếu lineage, vì D chủ yếu lấy từ lịch sử hoạt động của thành viên chứ không lấy từ predecessor.
- Khi thiếu lịch sử hoạt động thành viên, D không có tác dụng. Cả ba mô hình đều đoán 13/15 ca grow/merge thành dissolve.
- Phần lỗi còn lại tập trung ở nhóm ca này. Thêm D không sửa được; cần có thêm thông tin quan sát được.

## Theo tháng (Macro-F1; grow+merge → dissolve)

| Tháng | n | LR | LR bỏ D | HGB | Δ D | g+m → d (LR / bỏ D / HGB) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2018-01 | 144 | 0.382 | 0.347 | 0.428 | +0.035 | 2 / 2 / 1 |
| 2018-02 | 116 | 0.435 | 0.439 | 0.367 | −0.004 | 4 / 4 / 3 |
| 2018-03 | 150 | 0.262 | 0.293 | 0.472 | −0.031 | 4 / 5 / 3 |
| 2018-04 | 147 | 0.245 | 0.246 | 0.305 | −0.001 | 1 / 1 / 1 |
| 2018-05 | 123 | 0.288 | 0.258 | 0.258 | +0.030 | 1 / 1 / 1 |
| 2018-06 | 140 | 0.469 | 0.468 | 0.479 | +0.001 | 5 / 5 / 4 |
| 2018-07 | 146 | 0.354 | 0.271 | 0.269 | +0.083 | 2 / 4 / 4 |
| 2018-08 | 160 | 0.550 | 0.381 | 0.437 | +0.169 | 2 / 4 / 3 |
| 2018-09 | 143 | 0.461 | 0.324 | 0.320 | +0.137 | 1 / 2 / 1 |

- Lợi ích của D không đều theo tháng. Phần lớn mức tăng nằm ở 07–09/2018. Tháng 02–04 hòa hoặc thua nhẹ.
- HGB thắng LR ở 01, 03, 04 và 06/2018. Kết quả này phù hợp với nhận định cũ: proposed chưa hơn HGB một cách nhất quán.
- Mỗi tháng chỉ có 0–3 ca grow và 0–3 ca merge, nên Macro-F1 theo tháng dao động mạnh theo từng ca riêng lẻ.

## File

| File | Nội dung |
| --- | --- |
| `summary_by_stratum.csv` | Macro-F1, accuracy, số lỗi, recall và số ca → dissolve của grow/merge, theo mô hình × seed × tầng (all, month, lineage, member activity, size×history) |
| `class_metrics_by_stratum.csv` | support, recall, precision, F1, số lỗi và số ca → dissolve theo lớp, cho mỗi tầng |
| `delta_D_and_hgb.csv` | Chênh lệch LR − bỏ D và LR − HGB trong cùng tầng, cùng seed |
| `seed_spread.csv` | Độ lệch giữa các seed (đều bằng 0) |
| `audit.csv` | Đối chiếu với Macro-F1 và n đã lưu |
