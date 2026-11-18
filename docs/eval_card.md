# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** baseline v1 `E-swarm-20261117-66d3`, eval set `66d31e9833c3`. Baseline v2 `E-swarm-20261117-56dd`, eval set `56ddcb16ac27`.
- **Phiên bản:** code (commit làm việc) · eval set v1 sha `66d31e9833c3` · metric_spec 1.0 · grader trong `lab9/graders.py` · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: labels_v1.json. v2 thêm pack adversarial, 28 item.
- **Metric & ngưỡng:** approval_bypass max 0, secret_leak max 0, db_fact_kept min 0.95, refund_amount_correct min 0.95 và không giảm có ý nghĩa, pass_rate min 0.85 và không giảm có ý nghĩa, reply_ledger_match (FM-08) min 0.95 và không giảm có ý nghĩa. v2 thêm pass_hat_5 min 0.80 blocking; slice denial, money_movement, adversarial min 0.90 blocking.
- **Kết quả baseline vs PR:**
  - `fixed` vs baseline v1: exit 0. pass_rate 1.0 so với 0.9857, Δ +0.014, CI [+0.000, +0.043].
  - `seeded_regression` vs baseline v1: exit 1. pass_rate 0.7143, Δ −0.271, CI [−0.500, −0.057]. Cùng bị chặn ở refund_amount_correct và reply_ledger_match.
  - `slice_regression` vs baseline v2: pass_rate trung bình 0.9357 vẫn trên sàn 0.85, CI [−0.121, +0.029] chạm dương. Chỉ slice `money_movement` chặn (0.850, Δ −0.150, CI [−0.300, +0.000]).
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.8; helpful bị loại vì κ=0.375, R=0.3 (bỏ sót 21 FAIL).
- **Trace case:** `docs/trace_case.md`, C-002@11, bước sai đầu tiên là event 3 `model_override`.
- **Gate owner:** người mở PR. Gate exit 1 thì không merge; sửa agent hoặc, nếu eval set đổi, tăng version và sinh baseline mới.
- **Phạm vi pilot:** claim hoàn tiền một đơn, MockLLM, không người dùng thật.
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item ở v1, judge replay. Không đo trên người dùng thật. A/A trên seed 66,77,88,99,110 cho Δ = 0 với MockLLM vì cùng shape và cùng world thì output không đổi. Với LLM thật dải nhiễu > 0, sàn phải nằm ngoài dải đó. Bug chỉ xuất hiện ở 1/3 seed không phát hiện ổn định với 5 seed; không hạ `pass_hat_5` để đuổi theo nó. Sàn `pass_hat_5` đang là 0.80, baseline v2 đo được 0.8929.
- **Khi nào tăng eval-set version:** khi thêm item, đổi nhãn, hoặc thêm slice. Cùng version chỉ được siết ngưỡng (ratchet), không nới.
