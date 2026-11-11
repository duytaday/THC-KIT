import tempfile,unittest
from pathlib import Path
import editing_styles


class EditingMediaPathsTests(unittest.TestCase):
    def test_display_text_stays_text_even_if_empty_or_matching_a_local_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'Recordly').write_text('test')
            spec=dict(headline='',badge='Recordly',visual=dict(src='screens/*.png'),images=['one.jpg','two.jpg'])
            result=editing_styles.media_paths(spec,root)
            self.assertEqual(result['headline'],'')
            self.assertEqual(result['badge'],'Recordly')
            self.assertEqual(result['visual']['src'],str((root/'screens/*.png').resolve()))
            self.assertEqual(result['images'],[str((root/n).resolve()) for n in spec['images']])

    def test_remote_asset_does_not_silently_leave_the_local_adapter(self):
        with self.assertRaisesRegex(ValueError,'local media'):editing_styles.media_paths(dict(src='https://example.org/asset.png'),Path.cwd())


if __name__=='__main__':unittest.main()
