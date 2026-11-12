---
name: cutroom-motion
description: Plan and revise original Cutroom intro and demonstration artifacts from a recording, script and real proof assets through the local editor.
---

Launch `python app/app.py --data D:\Cutroom-workspace`. In Script choose
Generate intro & demos. Review the exact source passage, occurrence, timing basis,
evidence asset and pickup status before inserting each scene. Software actions
need observed control/contact/result/opened-file times from that recording.
Keep narration on the episode bus; a script alone is not proof it was spoken.

Use Studio's export clock for hooks: **[0.000, 3.000)** from the first presented
frame of the exported MP4, including titles and silence. Propose three hooks and
render one. Ask what the viewer expects after only that interval, save the answer
before showing the body, then timestamp its payoff. A problem shown at second two
may resolve at second eight; the spoken sentence need not finish by second three.
For persisted revision requests and style transfer, follow
`docs/EDITING-EVALS.vi.md`; repeat the same request ID on transport retries.

Use individual Edit/Regenerate actions. Preserve other scenes, manual overrides,
previous exports and each recording’s script. A deleted anchor requires reassignment.
For a reference with backgrounds hugging individual text lines, use native
`box_style: lines` / Text background in the scene editor. Keep `panel` for one
enclosing card. Do not invent an entrance for a label already visible in the
source interval. Preserve source timing/words and inspect the decoded phone-size
frames; matching this component does not establish full-episode style fidelity.
Missing product proof remains a capture placeholder; an original diagram must be
labeled as an illustration. Export scene JSON and timeline with the preview.
For a frozen episode recipe: `python app/cli.py render render-project.json --out NEW-VERSION`.
Changed dependencies require a new recipe through the UI, never bypass a stale hash.
