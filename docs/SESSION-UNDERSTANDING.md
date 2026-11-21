# Session understanding

- [ ] Recordly source selection: user asked “là sao”. Explained that Screen
  selects the window to record, distinct from starting Record. Current observed
  source is Facebook, so recording has not started. CUA activation and one fresh
  recovery failed; asked only to select “FFmpeg preview · 5 repo GitHub”, without
  pressing Record. Waiting for confirmation; no mastery inferred.

- [ ] Optional SFX in reusable templates: dev20 fixes a real KeyError for valid
  specs with no SFX field. Unknown sound planning stays distinct from explicit
  empty/muted cues. The rebinding test covers both states and leaves the stored
  template unchanged. This implementation test is not human comprehension or
  episode audio approval.
  Dev21 also preserves this distinction in Controls Save. Five real UI cases
  passed on an isolated workspace, including cue removal/restoration and locked
  scene protection. On13/11 the user answered the Save question:
  “âm thanh sẽ đi theo thẻ riêng.” This expresses a per-card cue relationship;
  it does not yet distinguish spatial placement from event time, or unknown
  sound planning from explicit mute. Keep this item pending. Asked a concrete
  follow-up: a card/pop at00:05 is moved left on the picture without changing
  timeline time — what should Save do to the pop? The user selected mute.
  Explained that X/Y placement and sound mute are separate; a spatial move
  preserves the existing onset/gain. In the next open-ended case the user said
  “sẽ đẩy đoạn đầu xuống thôi”; this does not identify X/Y versus timeline time.
  Explained the intended X/Y-only operation and deferred a visual demonstration
  while answering the user's evals/harness audit request. Mastery remains pending;
  do not change product behavior to auto-mute based on this quiz response.
  Neither the UI tests nor this partial answer establishes full mastery or any
  listening approval. This reply is not confirmation of the Recordly source.

Current v008 evidence: Kaggle COMPLETE/reloaded; base/tuned full masters are
byte-identical. The full intro manual v002 changes timing only, not model weights.
Decoded frame35.500 confirms the FFmpeg proof pickup. All five masters have an
agent visual-only REVISE note, and full listening is still unverified. Buyer
quiz is prepared with zero responses; no pending learning item is marked mastered.

Latest typography follow-up: manual v003 changes font sizes only, not weights,
timing or voices. Full PCM/SRT remain identical; two3second hooks also have equal
decoded PCM and measured listening level. Agent can read sampled360px frames,
but has not established one-pass recognition or user preference. Reference host
headlines are already present; authored full-intro movement is not observed
reference motion. No new quiz answer, listening approval or mastery is inferred.
See `GOAL-RELEASE-AUDIT-2026-11-13.vi.md` for unmet full-scope requirements.

- [ ] Silent scene versus voiced master:16authored fixtures revealed that a
  silent preview could not be produced without programme loudness. The fix
  admits measured silence only for previews, with null levels and no master
  loudness attestation; real master normalization still rejects it. Explained
  the distinction during work; no human answer or mastery inferred.

- [ ] Declared input versus target leakage: dev18 recovers layout only from
  the existing canonical intent, before inspecting target labels. All18 changed
  inputs were validation; train/RAG stayed byte-identical, so no duplicate
  Kaggle run was launched. Four tuned native successes still include2manual
  compiler repairs and2content omissions. No user mastery or approval inferred.

- [ ] Validation diagnostic:8source-disjoint component inputs still give5base
  and6tuned native failures. Rules8/8 native does not establish coverage/style;
  post-hoc agent-label agreement is not independent human evidence. Explained
  this distinction in the progress update; no new user answer/mastery recorded.

- [ ] Same-video model comparison: actual v007 base/tuned exports have the same
  MP4 hash, while real training/loading succeeded. Asked whether that proves
  fine-tuning improved picture/sound or requires a new blind episode and measured
  repair work. Awaiting the user's answer; no acceptance inferred from hashes.

- [x] Source protection: asked what `protected: face [x,y,w,h]` means when placing
  a graphic, with three choices. The question follows the actual v006 failure
  that copied this rectangle into a card. The user answered: “Đây là vùng cần
  tránh đặt thẻ; không được chép nó làm khung thẻ.” This demonstrates the
  exclusion-zone concept; it does not approve any current master or model.

  Applied example: current headline uses the measured source face exclusion.
  A late-analysis regression was caught by the UI assertion before replacing
  the locked demo. Its fix preserves reviewed reference guidance; 252 tests
  establish runtime behavior only. No further human mastery or sign-off is
  inferred from that result.

- [ ] Prompt recheck 12/11 v002: distinguish a passing mechanical replay from
  independent episode quality. Current 24 targeted tests and a synthetic gallery
  process prove software contracts only. Asked the pending retry question again
  with one Send / one request ID / one click-gain change; no answer recorded yet.
  Do not count test success or this document as demonstrated human mastery.

- [ ] New model versus cached scene: a checkpoint can change while the menu still
  says Fine-tuned. A focused multiple-choice checkpoint asks which evidence proves
  the new model generated the preview, separately from whether its quality is
  better. Awaiting the user's answer; no mastery inferred from the code/tests.
  Latest concrete evidence: v006 runs can load correctly and still choose a panel
  unlike the reference, or copy the protected face rectangle into a graphic and
  be rejected. A manual panel-to-lines repair is recorded separately from raw
  model scores. These results do not answer the pending human checkpoint.

- [ ] Logical feedback retry: user initially chose two notes for a single click
  retried by the network. Explained one deliberate submission vs transport retry,
  and why a relative change must not execute twice. Mastery is not yet demonstrated;
  use the actual lost-response UI test as the next concrete teaching example.
  That UI test now passed: first response deliberately lost, same request retried,
  exactly one note remained. A follow-up asks whether the ID represents a deliberate
  user request or each arriving packet. No answer has been recorded yet.
  During the prompt recheck, asked the same distinction as a concrete open-ended
  case: one deliberate Send, retry with the same ID — how many notes/edits?
  Still pending; implementation tests do not establish the user's mastery.

- [x] Reusable production contract: the user explicitly distinguished customer
  script, industry, B-roll/footage, logo/branding, then chose full blinded review,
  QC, viewer answers and repair time before enabling a candidate. Earlier shared
  branding and storyboard/proof answers remain applicable. This is conceptual
  understanding, not a completed review of the current master.

- [x] Shared branding can remain consistent while edit style, animation and demo
  choices change. Per-recording scripts and proof remain independent.
- [x] User distinguished an illustrative-script preview from a voice-aligned
  delivery: response “story board nhé.” Missing recorded speech is a pickup.
- [x] Local recordings live on D. A C junction is not a second disposable copy;
  clean only physical scoped cache (confirmed in the earlier storage checkpoint).
- [x] A caption covering proof requires revision; unavailable playback leaves
  review pending; missing ffprobe blocks the checker (earlier explicit answers).
- [x] User chose viewer quizzes to evaluate the result. Explained that the quiz
  must bind answers/timecodes to blinded unseen-episode exports, and that repair
  time/preference/cost evidence is still needed; weight loading alone is not gain.
- [x] User answered C to the controlled-unseen-comparison checkpoint: same media,
  renderer and listening level; quiz answers, corrections, repair time and cost.
- [x] Updated real-footage skill: user answered that a `For review` badge is
  insufficient for “open the exported file”; Recordly must capture that action.
- [ ] New references: distinguish a newly observed badge/style from a render-tested
  component and from an approved episode. More files alone do not establish gain.
  A focused checkpoint is pending: where to use an attractive new badge when the
  client episode lacks actual result footage, and what delivery status follows.
- [ ] Optional skill/render integration: distinguish a rendered layout template
  from the current episode's actual action/result proof and from demonstrated
  improvement. A focused checkpoint was sent; no answer recorded yet. Do not
  mark this mastered from the installation, model logs or frame-grid inspection.
  A combined checkpoint now asks what to keep, capture and release when a new
  episode has an attractive sliding/rotating name card but lacks actual action
  results. No answer has been received; no mastery inferred from the UI smoke.
- [x] Full-video benchmark: after an initial answer that reused a trained-on test
  episode, the user identified the episode-specific inputs and then selected
  blinded complete-video comparison on new material, same source/listening level,
  all QC gates, viewer answers and actual repair time. A corrected training episode
  remains a regression example; the next unseen claim requires fresh held-out data.
  Latest explicit restatement: “So mù các bản toàn tập cùng nguồn/mức nghe,
  kiểm đủ QC, câu trả lời người xem và thời gian sửa thực tế.” This verifies the
  promotion criterion, not an actual approval or observed benchmark result.
- [x] Benchmark granularity: user explicitly requires full edited videos and
  reference-based flow criteria. Scene/spec diagnostics do not replace whole-episode
  acceptance. A future folder of 30 shorts is intake, not a claim that 30 exist now.

Current explanation: one local master plan owns source timecodes, captions,
voice, locked edits and QC. Optional HTML renderers and model workers produce
versioned proposals; they do not independently approve the customer master.
Raw-model failures, compiler repairs and unverified listening stay visible so
the buyer can understand what each success actually establishes.
The v006 component pilot now demonstrates a specific reference mismatch: one
large text panel versus backgrounds sized per line. UI/decoded evidence and equal
audio/caption hashes establish the controlled visual change, not style preference,
audibility, a successful model train or whole-episode improvement. No new mastery
is inferred from these automated results; pending questions remain pending.

Current concrete case: a supplied source and its hash/range establish an
assignment, not the truth of its result or final audibility. Legacy filename
associations remain unverified. Capture requirements now bind to the rendered
master's frozen profile; editing later workspace scenes cannot rewrite them.
This implementation evidence does not answer the pending template/proof checkpoint.

The current analyzer reports candidates. Training intake cannot turn an unlabeled
interval into a deliberate presenter hold. Inference features and final-editor
targets are separate; duplicate/creator/series/excerpt groups stay together.
The user permits agent-reviewed experiments. Those labels remain experimental,
and a reviewer without audio cannot certify voice clarity.

Applied hillclimb example13/11: a persisted paired mechanical replay completed
T1–T8/three variants in both arms, score1.0→1.0(flat), with zero real human
reviews. Stable-ID retry did not create new exports. Explained that operational
runner success is not model/style improvement; no new mastery or sign-off is
inferred. Full held-out video quality and the pending SFX distinction remain open.


Recordly plugin checkpoint13/11: capture/export smoke used a controlled local fixture,
not a real client demo. Thirteen tests, real native capture and exports establish
operation, not editorial approval. Explained same request ID means network retry
and must reuse the original result; a deliberate new take uses a new ID. The user restated: “1 lượt quay và cần đổi lại request id.”
This verifies one logical request versus a deliberate new take.
- [x] Distinguish a retry with the same Recordly request ID from a new take with a new ID.
- [ ] Distinguish this silent fixture test from actual action/result proof and
  whole-master listening/QC. No mastery inferred from plugin installation.

Latest audio instruction: “giọng nói quan trọng nên phải giữ xuyên suốt và thêm sound effect giúp tôn giọng nói hơn nữa nhé.” This overrides the earlier ambiguous music/SFX-only request. Keep the recorded narration in the episode, lower the bed from its detector, and retain independent cue controls. It is a direction, not an assertion that anyone has heard or approved the new export.

- [x] Atomic revision conflict: user explained revision 8 must survive a stale revision 7 save; never relabel the stale draft as revision 8. Correct three-way merge requires base/current/local, stable scene IDs, delete-vs-edit handling and another atomic CAS after merging. Referenced projects.py/studio.py are not files in this inspected checkout; implementation here is Workspace/Handler.
- [ ] Explain the boundary between a preserved local browser draft and implemented automatic three-way merge. Draft review/download is implemented; automatic merging is not yet claimed.
- [ ] Next-sprint capability boundary: a circular presenter preview must match the actual exported mask, preserve one voice route and keep result/captions visible. Human mastery and actual export acceptance remain pending.

- [x] Spatial presenter edit: user explicitly selected keeping words, captions, timing and SFX gain/mute unchanged, then inspecting that the new crop does not cover text/results. This resolves the earlier position-versus-sound confusion; actual master listening remains a separate pending review.


14/11 follow-through: the user again stated that a crop/position-only revision
keeps words, captions, timing and SFX gain/mute, and checks new obstruction.
Verified as understanding; matching exported stem/caption hashes are separate
mechanical evidence. A sampled fixture export exposed an unwanted window;
source-ID/title monitoring is now tested but cannot establish pixel isolation.
- [ ] Explain why no observed ID/title change and passing mechanical tests do
  not establish readable real software proof or whole-master listening.


14/11 model request audit: the old synthetic C4 combined a changed label with a
hold-only instruction. Split into timing-only and label-only development probes,
preserving the old rejection. New authored train-only examples are experimental;
no mastery, hearing approval or model quality improvement inferred from them.
- [ ] Explain why a corrected probe and lower training loss do not establish
  improved full-video editing on an independent episode.


15/11 source binding/capture follow-through: user explicitly resumed Computer
Use for the real FFmpeg demo. Answer “chưa cần có human check” is ambiguous;
do not infer final viewing/listening approval or mark the pending source-guard
checkpoint mastered. Original final human review requirement remains in force.
Observed a concrete phone-size defect: nested preview captions conflict with
current narration. Retained that export, recorded a clean-caption preview from
the same real footage and kept one outer caption/voice route. Technical pass,
compiler equivalence and unchanged stems are separate from actual hearing.
- [ ] Explain why source-bound compiler correctness does not establish a
  trained planner's layout/motion quality or full-video style fidelity.


18/11 THC-KIT stock/planner acceptance:
- [x] User correctly restated that 1,000 decoded files establish acquisition only; a usable library additionally needs deduplication, provenance, categories, measured windows and retrieval/insertion.
- [x] User distinguished SFT context→approved final EditPlan from real A/B preference labels; two unbound MP4s and agent autopicks do not establish human preference.
- [x] User identified script/timestamps/style/candidate pool, asset source/timeline clocks, crop/layout/cues, feedback and episode/family/revision traceability as supervision.
- [x] User specified independent episode evaluation and keeping derivatives/source families together, with sealed final excluded from training/RAG/optimization.
- [x] User explicitly retained B1 after anchor regression, distinguished technical train/load from customer acceptance, and required expected/actual trace through source/output clocks, rerunning failed cases, independent development episodes, decoded render/caption/SFX review, measurable benefit and versioned promotion/rollback. Final stays sealed. Demonstrated in the 18/11 follow-up answer.

## Sprint hill climbing ngày 21/11/2026

- [x] Đã xác nhận trước đây rằng cải thiện trên bộ dev cần so mù tập mới, cùng nguồn và mức nghe, với QC, câu trả lời người xem và thời gian sửa thật.
- [ ] Giải thích vì sao một ZIP có ba file đúng hash vẫn có thể gắn sai revision, và vì sao API đối chiếu revision với export đã chọn.
- [ ] Mô tả khác biệt giữa đổi thumbnail cho cùng MP4, đổi bìa bên trong video và resume batch. Nêu bằng chứng dùng để biết lần nào sinh encode mới.
- [ ] Nêu lý do tập thiếu capture Save giữ draft và yêu cầu quay bổ sung, dù batch có thể hoàn thành.

Đã gửi câu hỏi kiểm tra về manifest. Ghi nhận hiểu biết sau khi có câu trả lời.
