# Additional video skills: pinned local integration

`$talking-head-edit` remains the master workflow: source voice, brief, timeline,
versioned exports and six-gate QC. These additions supply optional capabilities.

| Source | Integrated role | Actual boundary |
|---|---|---|
| `zhuyansen/awesome-claude-video-skills` @ `84d86811a655d7eba91115e669c97fcd4e068d55` | `claude-video-catalog`: local search across469 catalog entries | Discovery metadata, not469 installed/tested engines. Upstream security labels are not kit audit results. List license CC0; each project has its own license. |
| `heygen-com/hyperframes` @ `v0.9.33` | Installed `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`; new HTML renderer bridge | Local Node22+/FFmpeg; separate from the older0.8.52 talking-head-editor bridge. Paid reverse/avatar/style-template workflows are not enabled. |
| `artemnovitckii/claude-editing-skills` @ `beff6b868a8c1bdfad8661bd8a298497e75568a3` | Eleven skill instructions + pinned shared upstream checkout; six-workflow Windows bridge | Split-screen rendered on real user footage. Other workflows/cutouts/photographic media overrides need their own runtime/visual tests; installation does not certify them. Code MIT, sample-media rights separate. |

Installed under `D:/.codex/skills` on this machine. `UPSTREAM-SKILL.md` preserves
each original instruction; `INSTALLATION.json` records its source and adapter.
Use `configure_video_skills.py` after installing those pinned skill paths. It
adds the kit's Windows/local-ASR/full-Vietnamese-font/real-voice/QC overrides;
do not run the upstream Unix setup or Groq transcription for these local jobs.
Global skills become available on the next chat turn.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py='python' # Select the working Python interpreter for this machine.
& $py .agents/skills/claude-video-catalog/scripts/catalog.py 'talking head' --limit 10
# One-time pinned CLI setup; caches stay on D in this installation:
npx --yes hyperframes@0.9.33 --version
npx --yes hyperframes@0.8.52 --version

# New, editable HTML scene. Copy examples/hyperframes-intro to a new job,
# supply local GSAP, a full Vietnamese font and the user's community logo.
npx --yes hyperframes@0.9.33 check PATH_TO_PROJECT --json
& $py app/hyperframes_bridge.py PATH_TO_PROJECT --out NEW_VERSION/intro.mp4

# Optional six-workflow style bridge. All media paths belong to the current job.
$env:CUTROOM_GSAP_FILE='PATH_TO_LOCAL_PINNED_GSAP_JS'
$env:CUTROOM_ASR_PYTHON='PATH_TO_FASTER_WHISPER_PYTHON'
$env:CUTROOM_WHISPER_MODEL='PATH_TO_LOCAL_MULTILINGUAL_MODEL_SNAPSHOT'
& $py -X utf8 app/editing_styles.py split-screen spec.json --upstream PATH_TO_PINNED_EDITING_REPO --out NEW_VERSION_FOLDER
```

The style bridge reuses actual upstream build code. It adapts Windows execution,
local word timings, phrase-end/frame count, a full Vietnamese font, optional brand
accent and explicitly supported caption corrections. Corrections retain original
word times and need user/source evidence. It does not synthesize voice or turn a
drawn cursor into real click proof. Its original six workflows use compatible
HyperFrames0.8.52; five photographic templates retain their upstream builder and
require explicit paired media/cutout overrides where applicable.

These complete style previews contain their own burned captions and source
voice. They are optional CLI outputs, not eleven newly selectable batch presets.
Do not import one as a cutaway under duplicate narration/captions. Use a single
caption/audio authority for a complete styled cut, or the native-spec UI path
for graphics composited directly on the original master buses.

The example HTML is original code using five repo names; it is a scene template,
not a fixed five-repo workflow for other customers. The user's logo and footage
are supplied at runtime and not bundled here. Retain each external dependency's
license when distributing its code/assets.

## Actual checks so far

- Catalog search executed; skill validator passed.
- HyperFrames0.9.33: local preview HTTP200, Chrome hardware WebGL on NVIDIA,
  five-second render,150frames,1080×1920, encoded h264_nvenc; full decode passed.
  Silent intermediate animation; normal-speed master review remains separate.
- Claude editing split-screen:5.666667s,170frames,1080×1920,h264_nvenc, real voice,
  faster-whisper large-v3-turbo CUDA. Keptv002 with confirmed CTI/target-framing
  defects;v003 corrects CTA from the user's explicit answer and shows Releases;
  v004 also finishes audio at−16.01LUFS/−1.9dBTP.
  It is a layout pilot using a static screenshot, not the final click/result demo.
- Trial-reels rendered all three files from identical real media/audio,170frames
  each at−16.01LUFS/−1.9dBTP. Kept faulty pilotv001 and corrected title/header
  input inv002; no model-quality or viewer-preference conclusion is inferred.
- Full listening remains unverified; no final customer READY claim.

See `docs/ARCHITECTURE-RESEARCH.vi.md` for why the kit keeps one local application,
one source-linked master plan and optional renderer/model workers.
