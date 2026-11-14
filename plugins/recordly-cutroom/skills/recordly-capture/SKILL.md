---
name: recordly-capture
description: Use to record a real Windows software demonstration in Recordly for Talking Head Cutroom, retaining silent source footage, an editable project and a native export on D.
---

Use Recordly tools, not mouse coordinates on the HUD, for capture lifecycle.
This plugin is local Windows only. It prepares a separate companion from the
installed Recordly1.4.0 and preserves that original installation. Newer versions
or packed/unknown builds fail closed; do not silently upgrade or patch the original.

1. Read the actual spoken passage and intended proof. Prepare the target app
   through Computer Use. Never replace a real before/action/result with a reference
   excerpt, synthetic success badge, or generated output from another run.
2. Call recordly_status/open, then sources. Choose an observed exact window ID
   and title. Do not capture a private/account tab or fall back to the full desktop.
   If the source disappears or changes title, enumerate again.
3. Start with a stable request ID and beat ID; microphone/system audio/webcam are
   off. Only after CAPTURING is confirmed perform the demo through Computer Use.
   Show target before action, retain the result long enough to read, then stop.
4. Stop using the returned capture ID. Save native project and retain source/
   sidecars. Native exports use unique names. Current adapter supports static
   layout exports, not animated zoom; do not claim unsupported styling was rendered.
5. Inspect/decode the actual MP4 at phone size. Import the export into a new
   Cutroom version through the existing editor workflow. Preserve old cut and
   original narration, retime picture/captions/SFX together using source anchors.
6. Record before/after timestamps, project/export hashes and remaining pickups.
   Tools returning success or native encoder metadata do not establish readable
   proof, full listening, or READY. A reviewer without hearing leaves audio unverified.

Retry the same logical request with the same request ID after lost response.
Do not start a second capture on an unknown operation. Inspect status/native log.
Never expose tokens, enable remote access, send recordings to a cloud server,
change OS capture permissions, or delete prior media to make a test pass.


## Capture source guard (0.1.2)

The exact selected window ID/title is checked again after selection, every 300 ms
while recording, and at stop. A changed/missing window or failed source check
stops the capture, retains its source/native project, marks the take FAILED and
blocks export. Deliberate navigation that changes the window title needs a new
explicitly selected take. Never silently expand the allowed title list.

MONITORED_NO_CHANGE_OBSERVED means only that polling saw no ID/title change.
It does not prove pixel isolation, privacy, a real tutorial result or readiness.
Inspect the decoded export for unwanted tabs/windows. Legacy captures are
LEGACY_UNVERIFIED and retain their prior evidence. The 0.1.2 native Windows
recapture remains pending; deterministic tests do not replace that test.
