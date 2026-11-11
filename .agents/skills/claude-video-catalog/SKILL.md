---
name: claude-video-catalog
description: Search the pinned awesome-claude-video-skills catalog when choosing an additional video tool or skill, or when the user explicitly asks about that catalog. Route known tasks to the existing Talking Head Cutroom tools first.
---

Run `python scripts/catalog.py QUERY` from this skill directory. The local snapshot
contains discovery metadata, not installed engines or verified capabilities.
`--kind editing`, `--kind motion` and `--limit 10` narrow the search.

For existing real-footage jobs use talking-head-edit, its local FFmpeg renderer,
Recordly captures and exact-master QC. HyperFrames adds editable HTML motion;
claude-editing-skills adds optional style workflows through the Windows bridge.
Reuse an installed capability when it fits. A catalog entry is not a reason to
install another renderer, upload footage or enable an avatar/cloud provider.

Before adding a new upstream tool, inspect its current SKILL.md, dependencies,
license and Windows/local suitability; pin its commit, install only the needed
skill and perform a real smoke render. The catalog's security_grade is its
maintainer's label, not this kit's audit. Missing credentials/features are not
successful integration. Keep user footage, reference clips and model weights out
of the distributable skill. Follow the active kit's QC, source clocks and locks.
