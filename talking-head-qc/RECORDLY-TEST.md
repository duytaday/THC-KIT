# Recordly setup and integration verification

Tested on Windows on 2026-11-10.

Recordly 1.4.0 installed successfully at %LOCALAPPDATA%/Programs/Recordly/Recordly.exe. Installer exit code was 0. The Windows x64 installer SHA-256 matched the GitHub release asset digest.

Installer SHA-256
08f20bafb0d6cf82399b6e4d8d12f58cbf1821a1d93abdd1e944bb9727b66b20

## Actual results

- Importing the existing ShotCraft MP4 fixture succeeded with exit 0.
- Imported media SHA-256 matched the source. The fixture is H.264, 960 x 540, 2.026667 seconds.
- A duplicate import was rejected with exit 2 and preserved the existing take.
- A job path containing ../ was rejected with exit 2.
- All five packaged QC smoke cases passed with overall exit 0. READY in this test uses explicitly simulated editorial evidence.
- The importer now hashes in chunks using APIs available in Python 3.10. Runtime verification used Python 3.12.14. Python 3.10 itself was unavailable for execution.

## Capture and export remain pending

The application initially exposed capture controls. A later automation session found an empty transparent Recordly HUD with no controls. The input helper reported coordinate input geometry is unavailable. Restarting the app with a normal window and then with --disable-gpu did not restore the controls.

No live recording or Recordly-exported MP4 was produced. The import fixture above came from ShotCraft. No real Recordly master has received editorial sign-off.

## Resume verification

1. Launch Recordly interactively and verify that its Screen and Record buttons are visible. Select a small test window.
2. Record a demonstration showing both the action and its result. Stop and save the editable project with its linked media.
3. Export MP4 and import it using the command below from the repository root.
4. Map the imported clip to its required beat in a per-video brief and timeline. Assemble a fresh output/<job>/vNNN/ bundle with captions and delivery settings.
5. Run verify_edit.py, inspect and listen to the exact output, complete review.json with actual evidence, and rerun the checker. Retain NEEDS_REVIEW for unavailable evidence.

```powershell
$py = "$env:LOCALAPPDATA/talking-head-qc/venv/Scripts/python.exe"
& $py talking-head-qc/tools/import_recordly.py "C:/captures/demo.mp4" --job demo --beat proof --project "C:/captures/demo.recordly"
```

The Python path is the working setup on this machine. Use your own Python environment on another machine.
