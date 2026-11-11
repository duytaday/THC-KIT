# Agent-reviewed selector pilot

The user explicitly selected “Agent duyệt nhãn thử nghiệm” on2026-11-11.
This authorizes experimental agent labels; it is not human approval of their
contents or of a delivered video. The original57drafts remain unchanged.

The reviewed private dataset has57decisions from19source families. The reviewer
looked at513ordered source frames,19grouped strips and5native ambiguity checks,
with ASR sentence context. Audio was not heard. Thirteen proposed choices changed;
seven are REVIEW because the visible evidence does not substantiate the claim.
Labels distinguish visible screens from verified product outcomes.

The dataset uses data_class=agent_reviewed_experiment, human_approved=false,
agent_reviewed=true, visual_sequence_reviewed=true and
transcript_verified_by_hearing=false. Training requires an explicit experimental
entry point plus the authorization record. The default production gate still
requires human-reviewed labels. Neither route grants final video approval.

Pilot: Qwen/Qwen2.5-1.5B-Instruct pinned revision
989aa7980e4cf806f80c7fef2b1adb7bc71aa306;4bitNF4/LoRAr8q/v; seed3407;
40optimizer steps, gradient accumulation4, batch1. Split is locked by source
family:13train/2validation/4test families,39/6/12decisions. Creator identity is
unknown, so this is an episode/family holdout, not an unseen-creator evaluation.
The v014/current Vietnamese vlog is not part of training. References are English;
Vietnamese transfer and human preference have not been demonstrated.

Private Kaggle dataset and kernel are verified as private from server metadata.
Only reviewed text, source IDs/hashes/time ranges, configs and training code are
uploaded; raw video/audio stay local. Upload the explicit upload/whitelist folder,
not the dataset/working folder that Python can populate with __pycache__.
No paid model API is called. Kaggle GPU quota is separate from API spending.

Before upload, check current source bytes/rights, review provenance, split leakage,
the pinned tokenizer, every prompt+answer length and the package file hashes.
The largest pilot sequence is729tokens; no truncation. All planner shortlists
exclude validation/test reference families. Rules, base and adapter receive the
same cue/shortlist. Validation precedes the locked final test. Dataset metrics
measure agreement with agent labels, not human edit acceptance or retention.

Run prepare_agent_experiment.py once for a new numbered pilot directory, then
audit_training_tokens.py with the isolated tokenizer environment. Use Kaggle CLI
datasets create/version without --public and kernels push with is_private=true.
Record server metadata, immutable data/code hashes and each run version. A failed
runtime may be repaired using the same locked labels/split; do not tune on a
completed test result. Keep failed run logs and artifacts.

Fetch the actual provenance.json, benchmark.json, predictions.json and adapter.
Report actual_steps, losses, GPU, checkpoint hashes and test denominators only
from those files. RUNNING and a Python schema pass do not establish training.
An interrupted run may have checkpoint steps even if final evaluation failed;
report the two stages separately.

deployment_eligible=false and adapter_selected=false remain mandatory for this
pilot, even if it beats base on agent labels. Preserve rules/RAG as the delivery
default. Loading the adapter for an explicit offline test is separate from
enabling it in the kit. Human blind review, repair time, acceptance and a new
episode are required before promotion. Rollback keeps the base route and opens
the original timelines/media without the adapter.

Actual private files live under output/5-repo-ai/reference-lab, ignored by Git.
The paired video request10–20seconds is authored as versioned motion code from
real vlog material and passes the normal rendered-master QC independently of
the model experiment.

## Observed result and methodological defect

The actual pilot completed40steps onTeslaT4 and saved a verified adapter.
Independent audit found three context flags were derived from the chosen label
in the frozen label-builder, then included in the model/rules input. The raw
test report is not a valid independent quality benchmark. Preserve the frozen
run and do not rerun its test to tune the result. Adapter remainsOFF.
Future experimental export omits these fields, and the validator rejects them
unless their annotation provenance is independent of the chosen label. New
quality evaluation requires a fresh, preregistered holdout and raw generations.
See the private pilot TRAINING-RESULT.md and independent-experiment-review.md.
