# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261117-66d3` |
| Triệu chứng | Lab 8 fail `status resolved != denied`. Reply nói đã hoàn 20.000đ; ledger ghi 20000; nhãn là refund 0, status denied |
| Bước sai đầu tiên | Event 3, kind `model_override`, payload `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event 1 handoff và event 2 `lookup_order` vẫn đọc DB (delay thật là 2 ngày, đơn delivered). Chưa có quyết định tiền trước event 3 |
| FM | FM-03 ticket_trust |
| Regression test | `DbFactKept` fail khi có event `model_override`; `RefundAmountCorrect` fail vì ledger 20000 khác nhãn 0. Trên `fixed` cùng claim@seed không có override và status denied |

`fixed` C-002@11 là đối chứng: không ghi `model_override`, không hoàn tiền.
