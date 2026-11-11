import unittest
from engine.layouts import resolve, options, intersects


class LayoutTests(unittest.TestCase):
    def test_button_corner_moves_without_mutating_override(self):
        q={'layout':'presenter_pip','pip_corner':'auto','pip_width':.25}
        protected=[[650,1300,430,620],[60,1420,960,160]]
        r=resolve(q,protected)
        self.assertEqual(r['resolved'],'presenter_pip')
        self.assertFalse(any(intersects(r['rect'],p) for p in protected))
        self.assertEqual(q['pip_corner'],'auto')

    def test_full_data_table_falls_back(self):
        r=resolve({'layout':'presenter_pip'},[[0,0,1080,1920]])
        self.assertEqual(r['resolved'],'full_demo')
        self.assertEqual(r['requested'],'presenter_pip')

    def test_manual_conflict_is_not_silently_overwritten(self):
        with self.assertRaisesRegex(ValueError,'covers protected'):
            resolve({'layout':'presenter_pip','pip_corner':'bottom_left'},[[0,0,1080,1920]])

    def test_bad_size_and_unrendered_layout_rejected(self):
        for size in (True,float('nan'),.17,.37):
            with self.assertRaises(ValueError):options({'pip_width':size})
        with self.assertRaises(ValueError):options({'layout':'presenter_split'})


if __name__=='__main__':unittest.main()
