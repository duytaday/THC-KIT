---
name: thc-hill-climb
description: Run and interpret THC-KIT baseline versus challenger experiments for one editing prompt, rule, or component-selection change. Use when a measurable Cutroom failure has a reproducible development case and the goal is to decide whether to retain the baseline or advance a candidate for independent review.
---

# THC hill climbing

1. Locate the THC-KIT checkout. Read `specs/003-editing-evals/spec.md`, then confirm options from `python app/hillclimb.py --help` and `python app/editing_evals.py --help`. Reuse the existing runner and QC, and select the checkout's supported invocation for your environment.
2. Start from one observed failure and name the changed decision. Record an adverse case, a control that already passes, the primary metric and critical gates. Choose one candidate change per round. Include a focused diff and verify it changes only the declared factor. A grader change begins a separate calibration campaign with a new baseline.
3. Use authorized development recordings or fixtures. Assign all takes, turns, branches, captions and derivatives of a recording family to the same partition. Give the optimizer development inputs only. Keep validation budget, sealed cases, gold outputs and future turns with the independent evaluator. A role flag inside the app is not an OS isolation boundary.
4. Before dispatch, freeze the model and options when used, prompt and grader hashes, asset and script digests, renderer versions, preset locks and budget. Use a stable request ID and separate outputs for both arms. If a run is interrupted, inspect the same round and reuse verified completed evidence; use the runner's supported recovery for an incomplete dispatch.
5. Compare matched cases. A critical regression vetoes promotion even when the aggregate improves. Report per-case failures, cost and wall time. Stop on the configured budget, critical regression or the runner's plateau rule. Keep the baseline if benefit is unresolved. Tiny or synthetic-only differences are inconclusive for editorial quality.
6. Advance an eligible candidate to an independent evaluation; keep graders fixed for scored comparisons. Report mechanical playback/render checks separately from editor-scored hooks, truthful demonstration, caption readability and audio. A real master remains `NEEDS_REVIEW` until a creator watches and listens to that exact MP4 at 1×.

For a reproducible handoff, return the hypothesis, changed path and diff, command, trial/round ID, frozen input and grader hashes, per-arm report, decision and remaining evidence. Example: if a tighter prompt scores equally on fixtures yet the new crop hides the actual Save result on a matched case, report the regression and retain the baseline.

## Windows and the sprint harness

From the checkout root on D, dot-source `talking-head-qc/tools/use_d_storage.ps1`
and use `$env:THC_PYTHON`. Configure the local QC skill and use a new D output
folder. The trace and reports belong outside Git.

The controller uses `freeze CONFIG --out TRIAL_DIR`, `start TRIAL_JSON --id ID
--hypothesis TEXT --variable TEXT`, `run TRIAL_JSON --id ID --cost N`, then
`status TRIAL_JSON`. Read command help before using the flags. The default
profile replays the eight editing turns. Set `profile: "sprint"` in the replay
config to run batch resume, bound and missing demo, thumbnail, cover and cached
bundle checks. Use the [sprint guide](../../../docs/SPRINT-HARNESS.vi.md) for
the fixture contract. The sprint controller checks the declared changed path
against both source trees. It does not infer how many decisions changed inside
that file, so review the actual diff before starting.

If an arm is already dispatched, inspect its process and saved receipt. The
controller adopts a completed matching receipt. An incomplete arm stays
incomplete. Preserve it for diagnosis before opening a fresh campaign.
