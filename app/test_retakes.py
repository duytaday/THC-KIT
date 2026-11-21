import unittest

import retakes


def fixture(texts, starts=(1,4), **plan):
    beats, words = [], []
    for i, (text, start) in enumerate(zip(texts, starts)):
        parts=text.split()
        end=start+len(parts)*.23
        beats.append(dict(id=str(i),source_start=start,source_end=end,quote=text))
        words.extend(dict(text=w,start=start+n*.23,end=start+(n+1)*.23,probability=.98)
                     for n,w in enumerate(parts))
    return dict(keep=[[0,9]],**plan),beats,words


class RetakeTests(unittest.TestCase):
    def evaluate(self, texts, **kwargs):
        return retakes.proposal_options(*fixture(texts, **kwargs),'synthetic',9)

    def test_exact_vietnamese_english_pair_keeps_manual_choice(self):
        proposals=self.evaluate(['Bấm nút Save lần nữa.']*2)
        self.assertEqual(len(proposals),1)
        self.assertEqual(len(proposals[0]['choices']),2)
        self.assertEqual(proposals[0]['choices'][0]['drop_take']['word_ids'],list(range(5)))
        self.assertAlmostEqual(proposals[0]['choices'][0]['master_cut'][0],.9)

    def test_negation_number_and_diacritic_are_not_duplicates(self):
        for texts in (['Bạn cần chọn nút Save.','Bạn không cần chọn nút Save.'],
                      ['Chọn đúng 2 repo nhé.','Chọn đúng 3 repo nhé.'],
                      ['Bạn hãy tiếp tục bán.','Bạn hãy tiếp tục bàn.']):
            with self.subTest(texts=texts):
                self.assertEqual(self.evaluate(texts),[])

    def test_close_emphasis_and_incomplete_sentence_have_no_cut(self):
        self.assertEqual(self.evaluate(['Bấm nút Save lần nữa.']*2,starts=(1,2.20)),[])
        self.assertEqual(self.evaluate(['Bấm nút Save lần nữa']*2),[])

    def test_demo_and_sfx_protect_their_overlapping_takes(self):
        self.assertEqual(self.evaluate(['Bấm nút Save lần nữa.']*2,
            proof=[dict(start=.9,end=2.5)],
            events=[dict(id='click',kind='contact',hold_frames=15,anchor=dict(source_pts=4.2),
                         sound=dict(id='click',offset_frames=0))]),[])

    def test_missing_word_timing_requires_manual_edit(self):
        plan,beats,_=fixture(['Bấm nút Save lần nữa.']*2)
        self.assertEqual(retakes.proposal_options(plan,beats,[],'synthetic',9),[])
