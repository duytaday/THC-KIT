# Independent reviewer task — submit in the actual configured reviewer runtime

This file does not connect an app. Do not claim to be MausBot merely by reading it.
Record actual reviewer_id/runtime and the request file supplied by the operator.

1. Use a dedicated working folder for findings. Allow read access to request bundle and evidence; no editor/master replacement tools. Configure this isolation in the actual app/OS. A JSON policy or read-only file attribute is not an OS security boundary.
2. Run `qc_exchange.py validate-request <request.json>` in the installed local Python. Verify every hash before inspecting. The request names the exact file; do not pick a similarly named final from another task.
3. Run the kit technical checker, then view and listen to the exact master at normal speed. State actual watched_ranges/listened_ranges in milliseconds. A screenshot-only runtime leaves listening empty. Check opening/payoff, qualifiers, breaths/cuts, true feature proof, mobile layout, accents/names/numbers and CTA.
4. Report schema_version1, job_id, request_hash, master_sha256, brief_hash, data_class, reviewer_id, runtime, watched_ranges, listened_ranges, issues[], verdict. Each issue needs id, issue_timecode_ms, severity, evidence and requested_change. Return REVISE for confirmed defects, NEEDS_REVIEW for missing evidence, BLOCKED for essential missing tools. Use the inbox request IDs exactly.
5. Write a new findings file, then call `qc_exchange.py receive <request> <findings> <shared-folder>`. Imported reports cannot grant final release; complete the kit human review form on the same bundle. Do not self-attest a final human's name.
6. Maximum two automatic fixes for the same issue: the editor reserves each attempt with reserve_repair before rendering a fresh version. Preserve old reports and cuts. After two failures, hand the concrete issue to the operator.

Live integration requires a result produced by this actual bot runtime. A local fixture worker or Codex subagent is separately labeled and cannot prove live OpenBot/MausBot connectivity.
