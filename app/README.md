# Talking Head Cutroom local development handoff

Headless `auto-edit`, `status`, `resume`, `revise` and `library` share this app’s workspace/renderer/QC. See [batch CLI and compact UI](../docs/HEADLESS-AUTO-EDIT.vi.md). The UI top level is Files / Library / Outputs; advanced style tools are reachable from Library.

Creator path: add a recording → **Make first cut**. Optional TXT/SRT, usable
B-roll, style reference and free-text niche stay separate. Local ASR is a first-use
download or supplied-script fallback; uncertain takes remain intact for review.
See `docs/CREATOR-QUICKSTART.vi.md` and `app/build_release.py --help` for the
versioned internal Windows candidate. The starter distribution grant remains
unresolved; this is not a public release or an editorial READY certificate.

Real-footage orchestration uses the existing `$talking-head-edit` repo skill.
Full-export benchmarking is in Exports → Benchmark full videos. See
`docs/FULL-VIDEO-BENCHMARK.vi.md` for the frozen protocol, blind review, quiz,
repair timer and approved-development-feedback export. Model rejections are
retained; a scene preview is not a programme-loudness or release approval.
See `.agents/skills/talking-head-edit/references/real-footage-workflow.md` for
the buyer invocation, three hooks, source-linked shot plan and missing-pickup case;
`references/components.md` in that skill defines twenty components with honest
implementation limits. `python app/buyer_acceptance.py --help` describes the
optional Playwright UI acceptance runner. Playwright is a test dependency only.
Render-tested layouts are Full demo and original-presenter PiP; Auto PiP avoids
observed controls/results/captions or falls back to full demo. The optional lab
imports private Kaggle generative receipts; configure `CUTROOM_KAGGLE_CLI` or put
the CLI on PATH. Core editing needs neither Kaggle nor those model libraries.

`Reference badges` is an original motion preset with a gentle slide and a static
badge when intensity is zero. It is independent of the optional generative model.
Its parameters/reference observations are frozen in the recipe. See
`docs/REFERENCE-REFRESH-RESULTS.vi.md` for actual training continuation and native
runtime tests. The generative trainer accepts `--resume-sha256` and refuses an
absent or changed parent rather than silently training from the base model.

Python3.11+ and FFmpeg/ffprobe on PATH. The built-in app uses the Python standard
library and included fonts/audio; Playwright and model libraries are test/training
dependencies only. The final QC bridge also needs the upstream ffmpeg-skill scripts
(tested3.2.3); set CUTROOM_QC_SKILL to their installed directory. No API key is
needed. Do not bundle customer recordings or the training corpus into this source
package. See THIRD_PARTY.txt and the font notices before public redistribution.

From the checkout root on this machine:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& '.\Start Talking Head Cutroom.ps1' -Python $py
```

Recordings appear in Workspace; assign each its own script. Plain text has
estimated speech timing, SRT uses supplied phrase timing. Generate intro & demos
creates editable, versioned scenes and visible passage IDs. Optional images/logo
and brand accent remain local. Product proof missing? Keep the capture placeholder.
An illustrative script without matching speech remains a storyboard/pickup.

Source recordings have search, project filters and an archive. Manage preserves
the original filename while letting you name the lesson, inspect its hash/path
and reveal it in Explorer. Add new take keeps the original and style, creates a
linked source with empty active script/events/cutaways, and retains the previous
script only as a reference for realignment. Archived sources are not queued.
Exports show the latest cut per source by default; use All versions/history to
see v001/v002 and go back to the source. Organization does not rewrite masters.

Reference roles are independent: Use for pacing, Show in video, Include in training.
Training intake records permission, creator/series/family and reviewed moments.
Do not infer discarded raw takes from a final MP4. Deliberate presenter holds and
unlabeled passages are separate. Dataset preparation displays exact blockers.

Style has independent motion, cue mute/gain/offset and music controls. Apply-to-
selected changes only touched fields. Manual cues and each recording’s script
survive reference changes. Review saved corrections retains before/after and
optional editor reason. No raw video is sent to an agent or cloud service.

The fine-tuned candidate is optional. Install a frozen model preset under the
workspace models/candidate/preset.json only after a reviewed experiment. It must
identify version, pinned model_revision, dataset_fingerprint, base_path,
adapter_path, deployment_eligible and a files map of relative paths to SHA256.
Use safetensors; hash all base/tokenizer/adapter files and the training-only
retrieval index. Retrieval entries need split=train and source_sha256. Unseen
episode hashes and held-out groups may not enter retrieval. CUTROOM_PLANNER_PYTHON
can select a separate compatible torch/transformers/peft environment. Missing or
changed checkpoints visibly fall back to built-in rules; inspect planner-receipt.
The worker uses local files only, never downloads models during a buyer export.

Render creates a new MP4 and freezes brief, delivery, editable recipe, dependencies,
cue sheet and six-gate report. It actually rerenders the frozen recipe to test
repeatability. Exports retain historical versions. Approval requires the exact
hash/current project revision plus actual human viewing/listening evidence. A
reviewer without audio leaves voice intelligibility unverified.

Tests and actual results: see docs/CUTROOM-RESULTS.vi.md. Reopening a frozen recipe
after renderer/dependency changes is intentionally rejected; create a new recipe
through the current UI. OpenBot/MausBot capability indicators are disconnected
until a real endpoint and invocation have been verified. Ordinary editing works
with those agents off.

## Optional animation-spec worker and library

`Generate intro & demos` can use native rules, base+training-only RAG or the
separate animation-spec adapter. Import a completed compact Kaggle spec ZIP;
configure `CUTROOM_ANIMATION_PYTHON`, `CUTROOM_ANIMATION_BASE` and optionally
`CUTROOM_ASR_PYTHON`/`CUTROOM_WHISPER_MODEL` before launching. No Torch dependency
is added to the core UI/runtime. The selector candidate described above is a
different task; its weights cannot act as an animation-spec adapter. Inference
failures remain errors with previous scenes preserved; no successful rules
fallback is substituted for rejected spec output.

Transcribe creates a local source-bound draft. The optional style CLI accepts a
`terminology` list from the current episode; it does not inject the five-repo
vlog's names into every Vietnamese recording. Check names/meaning against speech.

Native scene cards expose editable JSON, motion intensity, individual cues and a
lock. Save to animations creates a silent preview and reusable native template.
Adapt rebinds new words, source clocks and observed ROIs; archived reference clips
cannot supply proof for a new product run. Reference extraction keeps permission,
source ranges, crop and file hash; separate watermark and layout inspections are
required before Add as illustration. Prior crops and inspection history stay.

See `talking-head-qc/integrations/video-skill-set.md` for HyperFrames0.9.33 and
the pinned Claude editing Windows bridge. Those are optional CLI renderers;
their local previews are not automatically installed as batch presets. Claude
style previews already contain voice and burned captions: do not stack them
under a second copy of narration/captions. Keep one authoritative caption/audio
route when using a complete styled cut. Native scene specs are the tested UI
path for compositing graphics directly onto its original episode buses. Run
master QC after any assembly.

### Bộ đăng bài theo revision

Trong **Outputs**, mở **Bộ đăng bài** trên bản xuất muốn đăng. Chọn hoặc sửa
caption, chọn giây, bố cục và crop thumbnail rồi bấm **Lưu và xem thumbnail**.
ZIP gồm MP4, caption TXT UTF-8, thumbnail PNG và manifest có hash/khung hình nguồn.
Có thể tải TXT và PNG riêng. Mỗi lần lưu giữ bộ tải nhất quán với MP4 đã chọn.

Nếu muốn đưa thiết kế chữ vào đầu video, xem **Xem thiết kế bìa trong video**
rồi bấm **Đổi bìa trong video và xuất bản mới**. Bìa chiếm 12 frame đầu trên
timeline hiện có. Hàng đợi tạo revision mới, kiểm tra kỹ thuật và chờ xem/nghe
bản mới. Cảnh demo hoặc cue hình ảnh trong khoảng bìa sẽ chặn thao tác.
