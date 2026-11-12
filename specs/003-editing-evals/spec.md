# Editing conversation evaluation v1

The authoritative user requirements are the supplied
`Cutroom-Full-Audited-Codex-Prompt.txt` (SHA256
`049fb1b32ec36b52e806502e7c3a0f7306f64a8dec2649705857f845f63e1fd2`).
This feature runs in the existing local batch editor; no second Studio service.

- Persist public requests before their tool actions; retain exact context and
  implementation hashes. No future requests or grader targets enter that context.
- Deduplicate logical feedback by project/master/request ID, including concurrent
  and post-restart retries; a changed payload conflicts. Preserve render tokens.
- Validate identified, explicit current-run/current-digest complete 1x watch/listen
  coverage at the service boundary. Test validation never signs a real master.
- Transfer only selected style fields; preserve episode speech/proof and overrides.
- Review [0,3) on the exported clock before revealing the body; retain expectation
  and payoff observations separately from release approval.
- Isolate optimizer media/catalog/imports from a sealed scorer. Prove API search
  and known-ID denial with synthetic markers and actual read logs. This application
  boundary is not an OS sandbox for arbitrary code running as the same user.
- Replay T1–T8 and the superseded/missing-result/long-caption variants through real
  tools/rendering, keeping the baseline and failed runs. A failed critical turn
  fails the whole trajectory.
- Split connected recordings/conversations/derivatives before cutting. Apply the
  bounded-round and one-final-batch protocol; keep absent human metrics null.

Implementation, commands, evidence and limits: `docs/EDITING-EVALS.vi.md`.
Human quality and release remain INCONCLUSIVE/NEEDS_REVIEW when evidence is absent.
