import tempfile,unittest
from pathlib import Path
from full_video_acceptance import implementation_identity


class ComparisonIdentityTests(unittest.TestCase):
    def test_renderer_and_ui_changes_have_different_comparison_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'ui').mkdir();renderer=root/'renderer.py';renderer.write_text('before')
            ui=root/'ui'/'app.js';ui.write_text('before');(root/'test_renderer.py').write_text('test only')
            original=implementation_identity(root);self.assertEqual(set(original),{'renderer.py','ui/app.js'})
            renderer.write_text('after');self.assertNotEqual(original,implementation_identity(root))
            renderer.write_text('before');ui.write_text('after');self.assertNotEqual(original,implementation_identity(root))
