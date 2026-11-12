# Motion planner v005 — kết quả thật

Đây là LoRA cho **JSON animation specifications** của Qwen2.5-1.5B-Instruct,
không phải model diffusion tạo pixel B-roll/footage. Renderer native dựng từ
spec có thể sửa. Candidate vẫn `production_eligible:false`; default editor dùng
built-in rules. Những clip/reference chưa được xem đủ không tự vào library usable.

Corpus29MP4/28hash; không có hash mới so với v004. Đã kiểm source-PTS liên tiếp
và sửa7intro labels để giữ thay đổi text **và kích thước thẻ**, không coi headline
tĩnh là toàn bộ animation. Mốc replacement đầu: source4=2,500s;6=3,066667s;
12=2,866667s;14=2,733333s;20=3,400s;21=3,666667s;22=4,900s. Source6 nới thẻ,
không phải mọi replacement đều thu nhỏ. Các nhãn là agent experimental, audio
chưa kiểm; một panel là projection đơn giản, không tái tạo toàn bộ emoji/line strips.
Source4/10 tương tự được ghi riêng, không nhân đôi thành mẫu độc lập mới.

Dataset fingerprint:
`211cf1bd2edf51dd8fe80d62e2c2517b28b53a909065dce19b6b51d5edf5c0e5`.
33train/33validation/10test;25labelled source IDs; independent family/creator
count chưa xác minh, human gold0. Train có8changing scenes/9replacement rectangles
và9moving entrances. Một changing scene là fixture nguyên gốc, không phải gold
reference. Train-only RAG; source hiện tại được xem là development/regression,
không có tuyên bố unseen từ split tên “test”. Prompt7/retrieval3, max2711/3072tokens.

Kaggle private kernel `duytruyenthong/talking-head-spec-training-211cf1bd2edf`
đã COMPLETE:96optimizer steps thật,33unique training IDs đã áp dụng,
106,8966s train trên`cuda:0`/TeslaT4; máy có2T4, không khai data parallel.
Peak8.317.892.096bytes; LoRA weight-update L2=3,428420. Fresh pinned base, không
resume adapter v004. Validation loss **0,832789 →0,895883, xấu hơn**.
Unconstrained held-out generation: cả base và tuned đều0/4schema pass. Không
biến constrained-decoder/compiler success thành raw-model improvement.

Adapter SHA256:
`5f52682777caad29ce6fbf9b0b92c1ca6f84b1c0536bf01f6f9221e199a96898`.
Đã import qua UI và inference bằng fresh worker local`cuda:0`. Base arm nạp base
weights với adapter inactive; tuned arm bật đúng adapter. Request, stdout/stderr,
prompt/decoder/retrieval và weight hashes được giữ ở`model-runs` trong workspace005.

Ba full masters qua UI đều118,1s/3543frames/1080×1920/30, full AV decode PASS,
AAC48k và`h264_nvenc` trênRTX3070Ti Laptop8GB/driver572.42. Smoke5s có demo đạt
150frames/NVENC trước full render. ASR lần này thực tếCUDA/float16.

| Arm / export ID | SHA256 | LUFS-I / dBTP |
|---|---|---|
|rules ·3cf8d5bad06343cfa815f30347650182|a1da676e29a8ff5ac0ffaf3c5cdbefb4602731941bfd992455610e0d5b87c279|−16,08/−1,68|
|base+RAG ·88a091b69f9645f1bcbd16007f5f9828|f19440acd65826eb8025ce8d664beb333382e7c6ea55209d1932705f097b5eba|−16,08/−1,65|
|tuned+same RAG ·bf21c70c7db64585b9040d6f4c6df76a|f19440acd65826eb8025ce8d664beb333382e7c6ea55209d1932705f097b5eba|−16,08/−1,65|

**Base và tuned cho cùng MP4 từng byte trên case này**, dù raw outputs khác.
Không dùng revision cache (`reused:false`). Intro của cả hai cần cùng sửa budget
hold1frame; base còn false missing-input note về Recordly, tuned không có note đó.
Đây không phải bằng chứng tuned dựng đẹp hơn hoặc đạt reference. Voice WAV và
SRT giống hash trên cả3arm; comparison controls đủ và matched loudness đạt.

Benchmark local: port59511,
`/benchmarks/5fd98e3d14914f418a19274e3d6005ae/index.html`.
Giữ mọi model/cut cũ. Lần poll UI timeout đã được kiểm lại bằng workspace/job/
exact export/hash/dependencies; nhận lại rules export đã xong, không render lại.
Logs riêng:`output/reference-training/reference-spec-v005/actual-results-v001.json`.

Native UI đã thử replacement rect, giữ anchors/model provenance, style locks,
public request trước tools và lost-response feedback retry. Fixture5s có title
cards nguyên gốc +tone, không phải giọng presenter/proof phần mềm. Sau lỗi selector
của harness đã tiếp tục trên đúng export150frames; không gọi là cold run liền mạch.
Ba frame phone-size đã xem:0,5/1,5/2,5s, dấu Việt và cả title cuối còn đủ,2dòng.
Đây là kiểm selected frames, không phải xem/nghe toàn master1×.

Kết luận: **INCONCLUSIVE cho quality promotion**, master **NEEDS_REVIEW**.
Chưa có reviewer nghe thật, style winner, first-cut approval, editor time hoặc
fresh complete episode B. Không admit clip vào usable library hoặc bật production
model dựa trên train/load/schema logs. Workflow nhiều lượt và lệnh chạy lại ở
`EDITING-EVALS.vi.md`.
## Kiểm bổ sung hợp đồng layout — dev11

Đối chiếu recipe thật sau lượt dựng: demo base ghi `host`, demo tuned ghi `demo`,
nhưng native renderer luôn dùng full screen proof. Đây là khác biệt JSON bị bỏ
qua, không phải thay đổi nhìn thấy được. Dev11 bắt buộc proof dùng `demo` ở cả
context mới, constrained decoder và validator; spec mâu thuẫn bị từ chối, không
được compiler tự đổi. Context version4 tránh dùng lại cache cũ. Presenter PiP
tiếp tục dùng control cutaway riêng với geometry được kiểm tra.

Diagnostic chạy trên toàn bộ plan thật: base cũ bị từ chối đúng lỗi; tuned hợp
lệ. SHA256 của cả ba MP4 và hai recipe không đổi.224app tests PASS, gồm3test mới.
Không train lại, không sửa checkpoint/prompt huấn luyện cũ, không chấm lại final
cohort. Kết luận chất lượng vẫn **INCONCLUSIVE**; nghe master vẫn **UNVERIFIED**.
Evidence: `output/editing-evals/v001/layout-contract-v001/`.
