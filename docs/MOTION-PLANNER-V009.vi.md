# V009 — train thật, chưa đạt để bật cho khách

Ngày 15/11/2026: lượt Kaggle private version 1 đã COMPLETE, checkpoint đã được
kiểm hash, nhập qua UI Cutroom và nạp bằng hai worker CUDA mới. Kết quả chưa đạt
để promote model hoặc đưa clip vào library usable. Không chạy thêm steps/rerun
sau khi xem điểm của experiment này.

## Một thay đổi dữ liệu có giới hạn

Giả thuyết: 8 fixture gốc dạy phân biệt nguyên câu nói với nhãn hiển thị được
khai báo giúp model giữ đúng inventory. 4 intro + 4 cảnh giải thích, 4 static +
4 slide nhẹ. Nền trắng theo từng dòng tham khảo train source a10c694f… tại
00:01.000–00:01.033; slide timing do project gốc của fixture khai, không suy
từ frame tham chiếu. Không có giọng giả, màn hình thành công giả hay human gold.

Corpus reference vẫn 29 MP4 / 28 hash; 8 fixture không phải 8 reference/creator
mới. Train 56, development-validation 33, regression 10. Validation/regression
file giữ nguyên byte so v008; toàn bộ house fixtures ở một group train-only.
Không đưa bản sửa 5-repo hoặc future corrections vào train/RAG. Đã xem contact
sheets của 8 fixture và kiểm riêng frame settled 00:02.500 của mẫu moving;
chưa xác nhận reading/motion preference ở 1×. Không admit preview STORYBOARD.

Preflight tokenizer pinned: tối đa 3066/3072 token, không truncate. Giữ prompt 9,
retrieval 3, base/optimizer/lr và 64 steps như v008; thay đổi thử nghiệm là dữ liệu.
Dataset và code upload private, không raw media. Kernel:
[talking-head-spec-training-a0891e8b891b](https://www.kaggle.com/code/duytruyenthong/talking-head-spec-training-a0891e8b891b).

## Bằng chứng train và reload

- Dataset SHA: `a0891e8b891b7ea359ce0136869e6b4c49e90370e2865b1ec5f616a5ac750cdb`.
- Adapter SHA: `588fffe00cb27b9b576162200d5bf287e8991a0261dc3dfe9ccc8be314dd86ac`.
- 64 optimizer steps thực, 46 unique rows; cả 8 mẫu mới được áp dụng.
- Train trên **Tesla T4, cuda:0**, một GPU được dùng trong môi trường có hai T4.
- Optimizer wall 86.601 giây; weight-update L2 2.414216.
- Validation loss 0.833025 → 0.805809.
- Peak GPU 8,677,189,120 bytes. Đây không phải tổng wall của queue/job.

UI import dùng workspace riêng của v009, kiểm candidate hash qua reload;
jobs, locked scenes, workspace và candidate v008 giữ nguyên. Candidate vẫn
production_eligible=false. App local đã chạy bằng EXE internal v003 với path
base/runtime đúng trên D. Import metadata không thay việc xác minh load weights:
hai worker mới thật sự nạp đúng hash; base arm disable adapter, tuned arm enable.
GPU local: RTX 3070 Ti Laptop, 8192 MiB, driver 572.42; thiết bị thực cuda:0.

## Kết quả giữ nguyên, không thay bằng rules

Kaggle raw regression (các input đã dùng trước, không phải episode B):
base intro 0/2 + demo 0/2; tuned intro 0/2 + demo 1/2. Loss giảm không biến thành
điểm dựng phim. Regression đã được đọc vẫn là regression/development.

Local diagnostic giữ sáu input đã freeze: 2 intro + 2 demo từ development cũ,
R1 timing-only và R2 label-only synthetic. Vì hai probe sau là intro, tổng cột
intro là 4; không gọi bốn input đó là bốn episode độc lập. Mỗi arm model có đúng
6 generations, một fresh worker; cùng messages và RAG từng byte, unconstrained
decoder. Compiler repairs đếm riêng. Không phát sinh thêm lượt sau khi xem lỗi.

| Arm | Intro native /4 | Intro raw /4 | Demo native /2 | Demo raw /2 | Đủ tất cả declared texts /6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| rules | 4 | N/A | 2 | N/A | 4 |
| base_rag | 0 | 0 | 0 | 0 | 0 |
| fine_tuned | 0 | 0 | 1 | 1 | 0 |

Native pass không đồng nghĩa đủ nội dung. Cảnh tuned duy nhất qua schema vẫn
bỏ mất một nhãn trạng thái được khai. Hai synthetic probes R1/R2 đều không đạt.
Các lỗi còn gồm JSON sai, dùng text ngoài inventory, nhầm local entrance clock
vượt 60 frame và che protected captions. Không gỡ validator hoặc render một
cảnh thiếu chữ để gọi là clip đạt. Cả hai model batches bị policy từ chối, các
scene cũ được giữ. Quyết định: **v009 không được promote**; chưa chứng minh
cải thiện style hay chất lượng toàn tập.

Đủ-all-texts ở đây là diagnostic coverage, không phải quy tắc mọi inventory đều
bắt buộc hiện đồng thời. Acceptance phải xác định text/state nào thật sự cần
trong từng brief. Inventory giới hạn chữ được phép; nó không tự đảm bảo đủ beat.

## Audit request và capture workflow

C4 cũ vừa đổi nhãn vừa yêu cầu giữ lâu hơn. Đã tách R1/R2 mà không xóa kết quả lỗi
cũ: timing-only giữ quote/text/anchors; label-only giữ quote/anchors/duration.
Sáu test request-observability đạt, tokenizer thật kiểm repeat/invalidation và
restart đạt. Không gọi prefix ổn định là KV cache hit.

Recordly source 0.1.3 cho phép GitHub→Releases đúng mục đích: `allowed_titles`
frozen, tối đa 5 tên chính xác, đã được quan sát trên cùng window ID trong 5 phút.
Tên lạ, sai window hoặc observation cũ bị chặn; Sources trong lúc quay không
mở rộng danh sách. 23 plugin tests đạt; chưa quay native vì desktop bị dừng bằng
Esc và chưa có chỉ thị tiếp tục. Installed plugin 0.1.1 được giữ.

Application suite: 312 test, 299 pass, 13 optional skip. Đó là phần mềm, không là
chứng nhận video/model. Đường chạy và audit chi tiết ở
[MODEL-REQUEST-REVISION-AUDIT.vi.md](MODEL-REQUEST-REVISION-AUDIT.vi.md).

## Còn thiếu để đạt mục tiêu đầy đủ

- Model vẫn chưa đảm bảo text/state, local motion clock và vùng captions. Cần
  kiểm lại ranh giới quyết định model so với binding nguồn/renderer; không tiếp
  tục tăng step hoặc nhân fixture giống nhau chỉ vì loss giảm.
- Demo FFmpeg của exact master 00:34.733–00:37.333 vẫn cần quay thao tác thật;
  không dùng fixture làm minh chứng. Giữ bản cũ và trạng thái REVISE.
- Cần raw episode B độc lập và so mù toàn tập rules/base+same RAG/tuned+same RAG,
  có người nghe, QC đủ và phút sửa thực. First-pass acceptance và phút sửa/phút
  thành phẩm vẫn null, không phải 0. Full-master listening UNVERIFIED.
- Không có clip v009 nào được đưa vào usable library; không có READY hay mặc
  định model mới cho khách. Không có ASR hoặc master-render mới ở lượt này.

Artifacts private trên D: `output/reference-training/reference-spec-v009/`
gồm protocol, editable fixtures, source-timecoded inspections, immutable dataset,
tokenizer preflight, Kaggle logs/package, UI import, request receipts và mọi raw
prediction. Evidence JSON trong repo chỉ chứa metrics/hash đã lọc, không media,
private prompts hoặc API keys. Mọi checkpoint/cut trước được giữ.
