import unittest
from engine.references import inventory_delta


class ReferenceUpdateTests(unittest.TestCase):
    def test_renaming_and_duplicate_do_not_create_new_training_examples(self):
        def row(h,name):return dict(sha256=h,path=name,analyzable=True)
        old=dict(records=[row('a','old.mp4'),row('b','removed.mp4')])
        current=dict(records=[row('a','renamed.mp4'),row('a','copy.mp4'),row('c','new.mp4'),dict(path='broken.mp4',analyzable=False)])
        d=inventory_delta(old,current)
        self.assertEqual(d['new_hashes'],['c']);self.assertEqual(d['missing_hashes'],['b'])
        self.assertEqual(d['unchanged_unique'],1);self.assertFalse(d['auto_trained']);self.assertFalse(d['auto_approved'])


if __name__=='__main__':unittest.main()
