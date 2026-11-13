# Runner cho các vòng development có giới hạn

Triển khai trong `app/hillclimb.py`, dùng `editing_evals` làm nguồn protocol và
`editing_replay` làm harness app/API/renderer thật. Không tạo Studio mới, không
thay prompt/model/render settings của khách. Đây là runner cho candidate được
khai báo trước, chưa phải bộ tự sinh candidate hoặc quality optimizer.

## Thay đổi có bằng chứng

Trước: `round_start` chỉ sửa dict trong bộ nhớ, CLI chỉ có split-check/freeze/score;
không có vòng persisted gọi harness và ghép receipt. Sau: freeze/start/run/finish/
status ghi journal atomic, dùng OS file lock, stable request ID và snapshot cho
từng arm. Cùng ID/cùng yêu cầu trả round cũ; đổi nội dung dưới ID cũ bị từ chối.

Mỗi cặp dùng cùng config/source/grader; baseline giữ nguyên trong campaign,
candidate được snapshot khi bắt đầu vòng. Config, controller, grader và nguồn
được hash; input/script/proof phải nằm trong development allowlist trước khi chạy.
Runner không mở sealed scoring. Không nhận cờ `passed=true` thay receipt: chỉ
score report terminal có đủ T1–T8, ba variants, input snapshot và grader khớp.

Retry nhận lại output hoàn tất mà không render lại. Nếu đã dispatch nhưng chỉ
có output thiếu/không rõ trạng thái, runner dừng để kiểm process/output cũ;
không suy từ lock/status file rằng process còn sống, không tự restart. Chưa có
khôi phục tự động giữa các tool của một replay bị chết trước terminal receipt.

Giới hạn ba vòng, hai flat hoặc critical regression do protocol hiện có quản lý.
Critical regression được kiểm từng turn/variant, kể cả khi overall score cùng0.
Ngân sách được kiểm trước dispatch arm tiếp theo theo thời gian replay hoàn tất;
không tuyên bố đây là hard timeout để kill một render đang chạy. Cost là số caller
báo theo đơn vị/phạm vi đã khai, không phải billing telemetry tự đo. Render wait
không được gọi là phút editor sửa.

## Lượt chạy thật ngày13/11/2026

- **271 app tests PASS** trên bản source thử;13case mới chạy lại trên checkout chính PASS. Các case mới về idempotency, disk reload, OS lock,
  incomplete/grader/input mismatch, adoption sau interruption và budget stop.
- Một cặp baseline/challenger qua app/API/FFmpeg thật, dùng authorized excerpts
  của tập5repo đã dùng. Mỗi arm T1–T8 và ba variants PASS, ba exports/arm.
- Wall time replay: baseline45,984s;challenger45,938s. Không phải thời gian sửa người.
- Cùng ID chạy lại: journal và hash sáu exports không đổi, không render thêm.
- Mechanical trajectory score **1,0→1,0, flat**, không critical regression.
  Human reviews0,quality promotion false,first-pass/repair-time chưa đo.

Đây là kiểm runner trên development, không phải tập B độc lập, chất lượng model
hoặc ký master. V008 không train thêm/không được promote. Các master thật vẫn
cần capture FFmpeg còn thiếu và reviewer có khả năng nghe/xem1×.

## Chạy

Config campaign JSON cần `scope:development`, `baseline` và `challenger` là thư
mục app, `replay_config` là file config của editing_replay, `grader`, `cost_unit`,
`budget:{max_cost,max_wall_seconds}`, `cases` có development hashes của tất cả
nguồn/script/proof. Giữ dữ liệu và logs riêng trên D, không đưa vào RAG tự động.

```powershell
python app/hillclimb.py freeze D:/campaign-config.json --out D:/campaign-001
python app/hillclimb.py start D:/campaign-001/trial.json --id round-001 --hypothesis "One change improves the declared metric" --variable "One declared change"
python app/hillclimb.py run D:/campaign-001/trial.json --id round-001 --cost 0
python app/hillclimb.py status D:/campaign-001/trial.json
# finish dùng để adopt đủ hai terminal receipts đã có; không tạo replay mới.
python app/hillclimb.py finish D:/campaign-001/trial.json --id round-001 --cost 0
```

`--cost 0` chỉ đúng nếu phạm vi cost đã khai thực sự bằng0 (ví dụ external API
USD của replay local không gọi provider); không dùng làm tổng chi phí sản xuất.
Khi có human quality evidence trên fresh held-out families, dùng scorer riêng
`editing_evals.py score`; runner cơ học không thay các điều kiện quality gate.

Private evidence trên D trong `hillclimb-audit-v001`: source identities, patch,
271-test log, `campaign-v001/trial.json`, từng arm's frozen-inputs/tool traces/
results và `integration-result.json`. Không commit raw media hoặc private traces.

## Audit boundary và counterexamples

Skill Cutroom Prompt Audit được dùng cho tool contract/harness, không đổi model
prompt hoặc provider API; không khảo sát global settings, credentials, endpoint
secrets, private transcripts ngoài input development được cấp hoặc sealed gold.
Editing agent, local application và independent quality scorer là ba vai trò.

Finding demonstrated1 (`editing_evals.py:61,144` trước sửa; `hillclimb.py:52,77,134` sau sửa): không có persisted execution path. Control: cùng request
ID sau restart vẫn một vòng;adverse: ID cũ với yêu cầu khác phải conflict.
Finding demonstrated2 (`editing_replay.py:74,83`; `hillclimb.py:98,112`): partial/frozen-input mismatch không đủ để grade. Control:
đúng terminal receipts được score;adverse: partial output/grader đổi phải từ chối.
Before/after chỉ áp dụng các kiểm đã chạy nêu trên; không suy ra model gain,
cache hit, normal-speed listening hoặc mức style tương đương reference.
