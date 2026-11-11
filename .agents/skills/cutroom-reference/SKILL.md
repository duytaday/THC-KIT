---
name: cutroom-reference
description: Analyze local talking-head reference videos for Cutroom pacing evidence and training readiness; distinguish style, visible proof and model-training uses.
---

Use the existing Cutroom engine from the repository root:
`python app/cli.py analyze REFERENCE.mp4 --out NEW-profile.json`.
Add `--full` for whole-reference shot candidates. Save source hashes and exact
sample timecodes. A shot detector does not establish button contact, deliberate
presenter holds, title settlement, isolated sounds or reasons for discarded takes.
Keep uncertain observations marked as candidates; audio attribution needs listening.

For a corpus use `python app/learning_inventory.py DIRECTORY --out NEW-RUN`.
Training selection is separate from immediate style use and visible insertion.
Record permission and source groups before a split; keep held-out footage,
transcripts, labels and corrections out of both training and retrieval.
Report actual accessible/distinct/eligible/labeled counts. Do not call a rules
profile fine-tuned. Unknown source groups or missing reviewed inputs block training,
not the ordinary local editing workflow.
