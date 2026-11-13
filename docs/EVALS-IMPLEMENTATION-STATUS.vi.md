# Evals, prompt audit, hillclimb và harness — 13/11/2026

Update13/11: đã thêm persisted one-round runner gọi harness thật, stable IDs,
receipt/hash checks và budget stop. 271 tests và một paired development replay
đạt; mechanical score flat1,0→1,0. Chưa có autonomous candidate proposer hoặc
quality gain trên tập mới. Xem [Hillclimb runner](HILLCLIMB-RUNNER.vi.md).
Các mô tả thiếu runner bên dưới là trạng thái trước update này.

Đã kiểm source hiện hành và chạy lại kiểm tra tập trung. Không gọi cơ chế đã
viết thành một vòng tối ưu chất lượng đã chạy thành công.

| Phần | Đã triển khai | Còn thiếu / phạm vi |
|---|---|---|
| Evals design | `specs/003-editing-evals/spec.md`;conversation T1–T8,3variants;group split,critical trajectory gates,hash-bound human quality scoring | Tập B độc lập,viewer answers và phút sửa thật chưa có |
| Prompt audit | Đọc prompt gốc SHA049fb1b3…;trace contract/context/prompt/retrieval/model/renderer;conflicts và owning-file fixes tại `EDITING-EVALS.vi.md` | Đây là source/runtime audit do agent thực hiện,không phải automated prompt-conflict scanner chạy mỗi lần đổi file |
| Harness | `editing_replay.py` dùng app/API/renderer thật;`gallery_acceptance.py` gọi optimizer subprocess;full-video và UI harness riêng | Replay T1–T8 đầy đủ là log lịch sử dev9;không gọi là đã chạy lại whole-conversation hôm nay |
| Hillclimb | `editing_evals.freeze`, `round_start`, `final_batch`, `summarize`;budget,max3round,dừng2flat/regression;family CI và giữ baseline khi thiếu evidence | Chưa có integrated optimizer runner hoặc CLI start/finish-round;CLI hiện chỉ split-check/freeze/score. Quality hillclimb và paired final test **NOT_RUN** |

Kiểm mới trong lượt này:

- 10 tests `test_editing_*.py`: PASS.
- 14 tests `test_revisions.py`: PASS.
- Gallery probe mới: development search/direct đọc được;sealed search rỗng,
  direct known sealed ID trả403;actual-read digest chỉ thuộc development.
  Dùng marker tổng hợp,không chạm real final cohort. Đây là API boundary,
  không phải OS sandbox chống arbitrary code cùng Windows account.
- Prompt gốc vẫn SHA256
  `049fb1b32ec36b52e806502e7c3a0f7306f64a8dec2649705857f845f63e1fd2`.

Log lịch sử đã đọc lại: baseline2/8turn;challenger8/8turn và3variants;public-turn
replay8/8turn. Đây là **mechanical development replay**, human reviews0, không
phải chất lượng video hoặc generalization. B của replay là excerpt cùng nguồn.

Evidence riêng: `output/editing-evals/status-recheck-20261113-v001/` gồm test logs,
gallery process/read logs và `status.json` ghi hash source và phạm vi kết quả.
Không có thay đổi thuật toán evals trong lượt kiểm trạng thái này.

Commit triển khai gốc: `8da912a`; parent `ad9a7f7`. Snapshot baseline lúc đó có
dirty changes, nên Git parent không đồng nghĩa toàn bộ frozen baseline thực tế.
Tracking patch theo frozen baseline phải dùng `baseline-source` và kiểm
`baseline-files.json`;Git commit diff là một view riêng.
