# Source-bound demo focus

The focused demo CLI rebuilds a small software demonstration from its original recording. It makes the control readable before the real action and holds the actual result. The base master supplies the voice and existing captions. A catalogue entry or a moving cursor alone does not prove that the result is present.

This is a source-checkout CLI for 1–30 second, 720×1280, 30fps clips. It is separate from the batch UI and is not yet included in the Windows installer. Python 3.11+, FFmpeg/FFprobe and the repository QC tools are required. The pinned Motion curves additionally require Node.js; `native_smoothstep` uses Python only.

## Prepare an episode instance

1. Copy `examples/demo-focus/recipe.template.json` outside the checkout. Replace every placeholder with the current episode's absolute file path and observed SHA256. The template deliberately fails until bound to real media. The sample crop sizes are examples, not detected targets.
2. Inspect the original recording, installed capture-app version and native project, if available. Record existing zoom, crop, cursor, click sound, webcam and audio ownership. Do not infer telemetry or an automation API from the app name. If the source already has animated camera movement, inspect and resolve that ownership before adding another camera controller.
3. Find context, control, real contact and visible result in the recording. Record source PTS seconds, target and result rectangles, and their output frame positions. VFR source timestamps remain seconds; the output clock is fixed at 30fps. A cursor event identifies an action candidate; decoded pixels establish the visible result.
4. Bind the context crop and its contained focus crop. Choose a viewport above y=930 so the base caption zone stays intact. Exclude unrelated browser tabs and tooltips by cropping. Settle before the action, then use a separate static result shot with enough reading time. Inspect legibility at phone size.
5. If demonstrating a zoom with a frozen frame, set `freeze: true` and visibly label it as an illustration in the optional ASS overlay. A freeze is not a new recorded action. Missing actions or results remain NEEDS_PICKUP; editing can continue with a clearly labelled alternative treatment.

Every source interval, geometry value and landmark needs rebinding for a new episode. Keep original media and old masters. The renderer refuses an existing output filename.

## Render and inspect

Run from the repository root; replace the example instance/output paths:

```sh
python app/demo_focus.py /absolute/path/episode-recipe.json --out /absolute/path/B.mp4
python app/demo_focus.py /absolute/path/episode-recipe.json --out /absolute/path/B-motion-off.mp4 --motion-off
```

`--motion-off` freezes the camera at its context crop. It does not remove existing movement baked into the recording. Compare decoded target-region pixels between both exports, then view both at normal speed. Hash differences alone do not establish visible camera movement.

The CLI copies only the base master's audio stream, adds no click or avatar and preserves the caption area below y=930 during demo shots. It clears the upper demo area during each shot and clears the top 200px during the first 2.933 seconds. Use it only with a compatible base layout. Additional heading text needs an explicitly hash-bound `overlay_ass` file and `overlay_sha256`; otherwise no new heading is created. Caption and face safety beyond this fixed layout requires separate review.

The trace is `main` → `validate` → `curve` → `render` in `app/demo_focus.py`. Each shot's `move` selects actual sampled values through `motion_bridge.samples` or native smoothstep. Those samples form the saved zoompan filter expression. The `.filters.txt` and `.receipt.json` next to the MP4 retain geometry, samples, source hashes, recipe hash, renderer hash and exact output hash. They make the route inspectable; decoded frames are the output evidence.

## Independent rendered-pixel evaluations

Copy `examples/demo-focus/eval.template.json` outside the checkout. Select the result landmark from the original recording independently of the renderer. Bind its source PTS/ROI and its expected output frame/ROI. Obtain `baseline_pcm_sha256` from `demo_evals.pcm_hash` on the A clip before evaluating B. The baseline is decoded 48kHz mono PCM; it is not a listening approval or a full stereo-equivalence claim.

```sh
python app/demo_evals.py /absolute/path/B.mp4 /absolute/path/eval.json --mutants /absolute/path/new-eval-folder
```

Use a new mutants directory. This gate expects 30fps output and one known, visually stable result landmark. It searches a bounded ±6-frame window by default, permits one frame of onset tolerance and compares the held landmark ten frames later. Threshold 0.75 is a starting value; validate it against the episode's clean and negative controls, not by lowering it until a broken export passes.

The command requires the clean render to pass, a covered result label to fail and a picture-only delay to be detected at exactly three frames while its audio identity still passes. It saves all correlations, frame offsets and output identities in `eval-results.json`. This is source correspondence, not OCR semantics, a general quality score or proof that an action caused a result. Review the actual action, result hold and transitions separately.

The initial real-footage verification passed these three cases and the full regression suite: 355 cases, 342 passed, 13 skipped. Unsupported optional runtime checks remain skipped. The reviewed 25-second export had 750 frames; result onset was frame 286 and the delayed control was frame 289. Private media, episode hashes, machine paths and private recipes are intentionally outside this repository.

## Readiness and distribution

Save reusable treatment rules separately from an episode instance. Runtime presence is not READY_TO_RENDER: that state needs a real smoke render for the template and project runtime. READY_FOR_SCENE needs current footage, interval, aspect, revision, rights and rendered scene evidence. Changes invalidate the affected evidence. Every exported master still enters NEEDS_REVIEW, with listening UNVERIFIED until its own listening review is recorded.

These source changes do not publish recordings, reference footage, trained adapters or a new binary installer. Preserve upstream notices. Public repository visibility does not resolve the existing starter-runtime distribution grant or assign a new blanket license.
