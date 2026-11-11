# Vietnamese typography and animation

The v012 repair found a real browser fallback: requested Arial weight900 used
Arial-Black for Latin glyphs and TimesNewRomanPS-BoldMT for some Vietnamese letters
in the same words. A visually plausible single screenshot missed this defect.

For future jobs:

1. Package the full regular/bold/display font files with license and SHA receipt.
   Be Vietnam Pro from Google Fonts is verified in this job. Do not rely on OS
   family names or Latin-only web subsets for Vietnamese.
2. Normalize authored text to NFC. Check the actual text against each font cmap;
   preserve spoken words and cue timing. Symbols may have deliberate separate
   fonts, but accented letters must not silently change typeface.
3. Use explicit @font-face weights and await fonts before registering/capturing
   a browser composition. Set fontsdir for libass. Check browser CDP
   CSS.getPlatformFontsForNode and FFmpeg fontselect logs in addition to pixels.
4. Recheck layout after a font change. ASS nominal80 produced41px core glyphs
   with this font while the prior face produced55px. v014 uses nominal108 and
   measures56px in the calibration cue. Measure native output and also inspect
   at360px width; protect diacritics, two-line captions and proof details.
   Approximately54px main text /38px auxiliary are guidelines for this720-wide
   job, not a guarantee derived from font size. Judge actual words and context.
5. Keep the presenter stable during tool overlays. The owned reference sequences
   show short entries followed by settled holds. Reduce travel and unnecessary
   blur before lengthening motion; preserve actual capture zoom and result holds.
6. A reference observation is distinct from an editor-approved training target.
   Store machine-reviewed frame facts in RAG with provenance; do not convert
   them into human_approved labels or claim a trained model.

Working scripts: reference-lab/audit_browser_fonts.cjs,
prepare_animation_v013.py, refine_animation_v013.py, build_motion_v013.py,
prepare_animation_v014.py. The v014 timeline, source font receipt, actual native
measurements, comparison clips and versioned masters remain in the private job.
The packaged source and license are
https://github.com/google/fonts/tree/main/ofl/bevietnampro .
