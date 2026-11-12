# Talking Head Cutroom — nghiệm thu nhiều lượt

Yêu cầu gốc: `Cutroom-Full-Audited-Codex-Prompt.txt`, SHA256
`049fb1b32ec36b52e806502e7c3a0f7306f64a8dec2649705857f845f63e1fd2`.
Checkout không có Studio/spec003 riêng trước lượt này. Triển khai dùng batch
editor hiện có; `specs/003-editing-evals/spec.md` ghi hợp đồng.

## Cách dùng

Chạy `python app/app.py --data D:\Cutroom-workspace`. Import recording, script
và B-roll của từng tập. **Make first cut** hiện có đề xuất ba hook theo nguồn;
hook thiếu lời hoặc proof vẫn là pickup. Chọn cách mở dựa trên lời thật, không
đổi các từ của presenter để vừa hiệu ứng.

Trong Style, **Record editing request** lưu yêu cầu công khai trước khi người
dùng hoặc agent thao tác. Dùng các controls hiện có rồi **Finish current request**.
History lưu context, tool requests/status và digest trạng thái. Nó không tự hiểu
mọi câu sửa tự nhiên hoặc gọi một conversational LLM. Những model motion được
gọi riêng vẫn có prompt, retrieval IDs và weight receipts của chính lần inference.
API cho agent là `/api/conversations/begin`, `/api/conversations/complete`;
gửi `X-Cutroom-Turn` khi gọi tool trong lượt đang mở. Chỉ request hiện tại và
public turns đã có được đưa vào context; scorer giữ nhãn/turns tương lai riêng.

**Select style locks / transfer** chỉ khóa các trường đã chọn. Typography,
motion intensity và music gain có thể chuyển; script, source anchors, scenes,
sound cues và approval không được chuyển. Override/lock riêng ở đích được giữ
và báo trong kết quả transfer. Muốn đổi trường khóa phải unlock rõ ràng.

Exports → **Hook 0–3s** chỉ cung cấp đoạn [0.000,3.000) từ frame đầu của MP4,
tính cả title/khoảng lặng. Người xem ghi kỳ vọng trước khi nút mở body được dùng,
rồi ghi payoff. Đây là lời xác nhận thứ tự của viewer, không phải chống gian lận
khi họ chủ động mở MP4 trong app khác. Câu nói có thể kết thúc sau giây ba;
vấn đề ở giây hai có thể được giải ở giây tám. Bốn giây branding chung không đủ.

**Save feedback only** giữ pending request ID khi mất phản hồi mạng. Retry cùng
ID/payload trả lại ghi chú cũ. Gửi chủ động lần mới dùng ID mới. API `/api/feedback`
nhận `project`, `master`, `sha256`, `revision`, `request_id`, `note` có timecode
và một action: `scene`, `cue_gain`, `note`, `pickup`. Payload khác dưới cùng ID
trả HTTP409. Ledger và edit được commit cùng một workspace JSON atomic; render
orphan trước commit được giữ và retry dùng folder version tiếp theo.

Approval phải có `attestation`: run ID, SHA256 hiện hành, reviewer, decision,
full-watch/full-listen, tốc độ1×, width240–480px và coverage toàn bộ master.
Service từ chối thiếu evidence, hash cũ, review lỗi chưa giải quyết và revision
đã đổi. Sáu gate notes vẫn bắt buộc. `validate_only:true` cho test attestation
chỉ kiểm route, không ghi human sign-off, không tạo release receipt. Đây là
identity do local reviewer tự khai, không phải cơ chế xác thực danh tính.
Approval và dry validation còn hash-check source/render dependencies hiện tại;
đổi renderer hoặc nguồn không thể đi vòng bằng một attestation hợp lệ về hình dạng.

## Baseline và kết quả đã đo

Đối chiếu bảy mục của file gốc:

| Mục | Đã có / giới hạn còn lại |
|---|---|
|1 Baseline, audit |Snapshot baseline, xung đột/prompt versions và logs hiện có; điểm lịch sử được tách riêng |
|2 Editing contract |Hook export3s, source anchors, stems và kiểm timing; xem/nghe và hiểu proof trên master thật còn chờ reviewer |
|3 Ba runtime failures |Idempotency, attestation và gallery API đã kiểm; gallery không phải OS sandbox cho code tùy ý cùng tài khoản |
|4 Whole conversation |T1–T8 +3variants qua app/renderer; B hiện chỉ là excerpt, chưa đủ tập mới độc lập |
|5 Split/isolation |Connected family/conversation checks và actual-read development log; final cohort thật chưa được mở |
|6 Hill climb/release |Có freeze/budget/stop/CI gates; quality hill climb và final paired batch **NOT_RUN**, chưa đủ human metrics/families |
|7 Evidence/delivery |Code, commands, logs và preserved versions có sẵn; master **NEEDS_REVIEW**, model **INCONCLUSIVE** |

Evidence riêng trên D: `output/editing-evals/v001/`; raw media, logs, model và
private scorer files không vào Git. Baseline source được copy trước ba runtime
fix, lưu HEAD, dirty patch SHA và hashes. Điểm lịch sử8/8 cue,8/11 Studio trong
prompt không được chép thành kết quả của lượt mới.

| Bài kiểm tra | Kết quả / phạm vi |
|---|---|
| Cue controls baseline |8/8 engine assertions, log riêng |
| Baseline API |feedback/style-lock/gallery routes HTTP404 |
| Baseline replay mới |2/8 lượt đạt toàn bộ assertion của lượt;0/1 trajectory đạt |
| Challenger replay |T1–T8 và3 variants đạt các assertion cơ học; có render thật |
| Public-turn replay |request vào service trước tool; context/history sống qua restart; không có hidden grader labels |
| Full A replay |118,1s, CTA và13cutaways; B là excerpt của cùng nguồn, không phải tập unseen |
| Gallery optimizer subprocess |search/direct sealed ID bị chặn; development được đọc; actual-read digests chỉ có development |
| Chime cũ |onset âm học sớm3,1625frame khi peak được căn đúng; bài decode AAC phát hiện FAIL |
| Chime mới nguyên gốc |onset/peak cách nhau0,118125frame; kiểm decoded fixture đạt timing; audibility chưa được nghe |

Các replay dùng nguồn thật của vlog hoặc fixture được ghi rõ. Passing assertion
cơ học không chứng nhận hiểu hành động, caption/giọng đúng hoặc phong cách đẹp.
Không có test reviewer nào được ghi thành người đã duyệt video thật.

Counts:29 reference files/28 distinct hashes; số family/creator độc lập của corpus
chưa xác minh. Hai excerpt từ1.mp4 là cùng development family. Full replay có
1tập đầy đủ và1excerpt; các lần chạy lại không tạo thêm family độc lập. Final
unseen cohort và human reviews hiện chưa đủ. First-cut approval, editor minutes
và95%CI còn null. Thời gian render được đo riêng, không dùng làm phút sửa người.

## Audit các xung đột

| Owning file | Failure / sửa nhỏ nhất | Evidence |
|---|---|---|
|`app/revisions.py` (mới) |chưa có logical-feedback ledger; thêm scope/payload conflict/atomic commit |concurrent+restart và orphan-commit tests, replayT3–T4 |
|`app/qc_bridge.py`, `review_attestation.py` |tự điền full watch/listen từ form; yêu cầu attestation từ caller |thiếu/stale/gap/defect tests; dry-run không ghi approval |
|`app/evaluation_access.py` (mới) |chưa có gallery capability riêng; manifest development-only và hash-checked reads/imports |optimizer subprocess + actual read log; không đọc real final cohort |
|`app/openings.py`, motion/master-review skills |audition4s chưa cùng clock hook; đổi audition3s và thống nhất export clock |hook derivative90frames và UI chỉ hook trước câu trả lời |
|`app/workspace.py` |giới hạn12chặn13cutaways của nguồn thật; nâng32, giữ kiểm range/overlap |failed full replay được giữ; test32/33, rerender13 |
|`app/motion_render.py` |round centisecond làm lặp tư thế ởframe2/5/8; dùng floor |decoded10frame regression; đây là renderer fix, không phải model gain |
|`app/motion_specs.py`, native UI |chữ đổi nhưng thẻ không đổi geometry; thêm rect từng state và inherit |source-PTS reference frames, validator và actual-control tests |
|`app/motion_specs.py`, `motion_storyboard.py`, `motion_decode.py` |spec proof ghi `host` nhưng renderer vẫn chèn full demo; chỉ cho phép `demo` trong context/grammar/validator, từ chối spec mâu thuẫn |recipe base v005 thật bị từ chối, tuned hợp lệ; cả ba master cũ giữ nguyên SHA |
|`qc_gates.py`, sound catalog |peak lock không chứng minh onset lock; đo riêng onset1%asset-peak |decoded AAC fixture; không thay kiểm nghe bằng ngưỡng âm học |
|`app/ui/app.js` |cue audition dùnglegacy`none.wav`; chuyển sang đúng SFX stem của export |UI/API export stem route |

Prompt/skill files không tự được app load như system prompt. Codex đọc AGENTS và
skill ngoài app; conversation API trả contract/version/hashes. Motion worker
nhận SYSTEMS theo checkpoint, current source context và train-only retrieval;
`model-runs/request.json` cùng decoder/prompt/weight receipts là bằng chứng thực.
Các model cũ không bị viết lại prompt để giả tương thích. Packager có allowlist
modules mới; bản EXE cũ giữ riêng, không được gọi là đã tự nâng cấp.

## Split, hill climb và quyết định release

`editing_evals.split_check` gộp family, conversation, duplicate hashes và lineage
trước split; cross-creator mode còn gộp creator/series. A/B của cùng conversation
không tách partition. Trong personalization phải ghi cutoff và dùng tập về sau.
Gallery development chỉ chứa catalog/media/import hashes được cấp. Scorer giữ
sealed media/catalog/index/cache/trace ở workspace khác; optimizer kiểm actual
reads qua API. Đây không phải Windows ACL sandbox cho arbitrary Python dưới
cùng tài khoản; cần process/container/account isolation nếu threat model đó áp dụng.

`freeze`, `round_start`, `final_batch` giữ protocol, input/implementation/grader
hashes, hypothesis, một variable, metric, budget, rollback, validation looks và
repeat count. Tối đa3round; dừng sau2flat, critical regression hoặc hết budget.
Final batch chỉ independent scorer mở; infrastructure chỉ resume cùng trial ID.
Không dùng feedback cuối để tune rồi vẫn gọi family đó là unseen.

Quality hill climb/final test hiện **NOT_RUN** vì thiếu review/time/fresh families.
Cơ chế giới hạn đã có test; không bịa ra3round chất lượng. Chỉ tính quality từ
hash-bound whole-video reviews của cả A/B, đầy đủ QC/nghe và repair sessions.
Flag `human_evidence_verified:true` đơn lẻ không đủ. CI bootstrap theo family
chỉ chạy khi đủ pilot evidence; các mức10paired conversations/3groups là sàn
pilot của kit, không phải power calculation. Quality gate cần0critical regression,
cận dưới95%paired approval gain>0 và median correction time không tăng. Kết quả
chỉ là candidate cần quyết định; không tự bật model hoặc ký master.

## Chạy lại

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
python -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py'
python app/gallery_acceptance.py --out D:\NEW-gallery-run
python app/editing_replay.py --config D:\replay-config.json --out D:\NEW-replay
python app/editing_evals.py split-check D:\case-manifest.json
python app/editing_evals.py freeze D:\trial-config.json --out D:\NEW-trial
python app/editing_evals.py score D:\scorer-records.json --out D:\NEW-results.json
```

Replay config chỉ trỏ nguồn riêng có quyền dùng. Muốn so baseline truyền
`--app D:\frozen-baseline\app`; mỗi arm dùng out/workspace mới. Logs chứa script
và source paths nên là dữ liệu project riêng, không đưa vào training/RAG mặc định.
Các lệnh harness chạy trong checkout phát triển. Người mua EXE không cần cài
Playwright để dựng và duyệt video của họ.

Lượt này:219app tests cộng2packaging regressions,54QC tests,39reference
regressions PASS;3skills sửa đổi
qua validator. UI lost-response/state/hook test hoàn tất sau khi sửa selector của
harness; lỗi cũ được giữ, không khai cold-run PASS. Model v005 đã có ba full
exports kiểm kỹ thuật; base/tuned trùng hash, không có quality gain được chứng minh.
Chi tiết device/codec/weights và các giới hạn ở`MOTION-PLANNER-V005.vi.md`.
Lượt tiếp theo v006 đã train/reload thật và thêm control nền riêng từng dòng;
229app tests PASS, packaged UI render A/B sau sửa fade. Đây là component upgrade;
base/tuned trong case mới vẫn trùng preview, không có whole-video quality gain.
Kết quả, hash, lỗi harness được giữ và lệnh tái chạy ở`MOTION-PLANNER-V006.vi.md`.

Đối chiếu lại trực tiếp file yêu cầu ngày12/11: SHA256 vẫn khớp giá trị đầu tài
liệu. Source dev11 thêm kiểm tính nhất quán layout;224app tests PASS trong lượt
này, bao gồm grammar runtime thật.54QC và39reference tests là kết quả lượt trước,
không được tính thành lượt chạy mới. Evidence bổ sung:
`output/editing-evals/v001/layout-contract-v001/` có protocol trước sửa, baseline,
script kiểm lại recipe/master thật, results và log tests. Đây là một sửa hợp đồng
renderer, không phải một round chứng minh chất lượng model tăng.

Native animation v1 đặt ROI theo màn hình được contain toàn khung; vì vậy cảnh
có proof phải dùng `layout=demo`. Presenter PiP vẫn là control của cutaway riêng,
không được ngầm suy ra từ `host`. Context mới là version4 để không tái dùng scene
cache version3. Spec cũ mâu thuẫn bị yêu cầu regenerate/reassign khi dựng lại;
compiler không tự sửa lựa chọn đó. MP4, recipe và checkpoint cũ được giữ nguyên.
Kiểm recipe thật xác nhận demo base v005 ghi `host`, tuned ghi `demo`; renderer
cũ đã cho cùng hình. Do đó trường layout này không phải bằng chứng model thắng.

Kiểm EXE thực tế phát hiện gói dev9 thiếu deferred import`proof_assignments.py`;
render bị chặn trước khi có master. Gói lỗi được giữ. Dev10 bổ sung module và
preflight kiểm closure của các app-owned imports trước build; regression cố ý bỏ
module đó phải thất bại. Receipt của lần chạy binary nằm riêng ở
`output/editing-evals/v001/packaged-runtime.json`; source-test PASS không tự thay
cho kết quả binary. Bản EXE là internal development build, không chứng nhận
Windows sạch hoặc human editorial release.

Còn cần: raw tập B mới/script/branding riêng, reviewer xem/nghe trọn exact MP4,
câu trả lời hook/payoff và quiz không gợi đáp án, lựa chọn style, timer sửa thực
tế; capture Export/opened-file còn thiếu phải quay Recordly. Giữ READY cho master
đã ký đầy đủ; các master hiện tại vẫn NEEDS_REVIEW. Model v005 train/reload là
thử nghiệm; validation loss tăng, không chứng minh nâng chất lượng.
