---
name: cutroom-motion
description: Plan and revise original Cutroom intro and demonstration artifacts from a recording, script and real proof assets through the local editor.
---

Launch `python app/app.py --data D:\Cutroom-workspace`. In Script choose
Generate intro & demos. Review the exact source passage, occurrence, timing basis,
evidence asset and pickup status before inserting each scene. Software actions
need observed control/contact/result/opened-file times from that recording.
Keep narration on the episode bus; a script alone is not proof it was spoken.

Use individual Edit/Regenerate actions. Preserve other scenes, manual overrides,
previous exports and each recording’s script. A deleted anchor requires reassignment.
Missing product proof remains a capture placeholder; an original diagram must be
labeled as an illustration. Export scene JSON and timeline with the preview.
For a frozen episode recipe: `python app/cli.py render render-project.json --out NEW-VERSION`.
Changed dependencies require a new recipe through the UI, never bypass a stale hash.
