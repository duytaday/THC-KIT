import unittest
from pathlib import Path
from unittest.mock import patch
import storyboard

class StoryboardTests(unittest.TestCase):
    def propose(self,text,**kwargs):
        with patch('engine.planner.audio_windows',return_value=[[0,20]]):return storyboard.propose(text,20,Path('fixture'),**kwargs)
    def test_one_line_sentences_are_independent_and_stable(self):
        a=self.propose('Đầu tiên, chọn video. Sau đó, bấm nút xuất.');b=self.propose('Đầu tiên, chọn video. Tiếp theo, bấm nút xuất.')
        self.assertEqual(len(a['passages']),2);self.assertEqual(a['passages'][0]['id'],b['passages'][0]['id']);self.assertNotEqual(a['passages'][1]['id'],b['passages'][1]['id'])
    def test_repeated_sentence_keeps_occurrences(self):
        r=self.propose('Bấm nút xuất. Bấm nút xuất.')['passages'];self.assertEqual([p['occurrence'] for p in r],[0,1]);self.assertNotEqual(r[0]['id'],r[1]['id'])
    def test_five_repos_keep_order_and_own_missing_proof(self):
        p=self.propose('5 repo GitHub. Runway. fal. Remotion. Recordly. FFmpeg Skill.')
        self.assertEqual(p['artifacts'][0]['title'],'5 repo GitHub');self.assertEqual([a['title'] for a in p['artifacts'][1:]],['Runway','fal','Remotion','Recordly','FFmpeg Skill']);self.assertTrue(all(a['kind']=='placeholder' for a in p['artifacts'][1:]))
    def test_real_export_and_opened_result_are_separate(self):
        p=self.propose('Xuất video trong Cutroom. Bấm nút xuất.',evidence={'asset':'screen','duration':10,'result':3.8,'opened':8.1})
        self.assertEqual(p['artifacts'][0]['kind'],'result_first');self.assertNotEqual(p['artifacts'][1]['evidence']['result'],p['artifacts'][1]['evidence']['opened']);self.assertIn('PICKUP',p['artifacts'][0]['status'])
    def test_preserve_promised_count_and_do_not_invent_fal_from_fallback(self):
        p=self.propose('5 repo GitHub. Recordly có fallback.')
        intro=p['artifacts'][0];self.assertEqual(intro['title'],'5 repo GitHub');self.assertEqual(intro['missing_repo_names'],4);self.assertEqual(len(p['artifacts'][1:]),1);self.assertTrue(intro['status'].startswith('NEEDS_INPUT'))

if __name__=='__main__':unittest.main()
