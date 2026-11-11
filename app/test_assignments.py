import unittest
from assignments import match_scripts

class ScriptAssignments(unittest.TestCase):
    def test_duplicate_script_stems_are_never_assigned_by_order(self):
        a={'a':{'name':'Bài học.mp4'}}
        assigned,pending=match_scripts({},a,['a'],[{'name':'Bài học.txt','text':'first'},{'name':'Bài học.srt','text':'second'}])
        self.assertEqual(assigned,[]);self.assertEqual(len(pending),2)
    def test_unicode_normalization_preserves_accents(self):
        import unicodedata
        a={'a':{'name':'Bài học.mp4'}}
        assigned,pending=match_scripts({},a,['a'],[{'name':unicodedata.normalize('NFD','Bài học.txt'),'text':'one'}])
        self.assertEqual(assigned[0][0],'a');self.assertFalse(pending)
    def test_duplicate_recording_names_need_manual_assignment(self):
        a={k:{'name':'Lesson.mp4'} for k in ['a','b']}
        assigned,pending=match_scripts({},a,['a','b'],[{'name':'Lesson.txt','text':'one'}])
        self.assertFalse(assigned);self.assertEqual(pending[0]['candidates'],['a','b'])
    def test_only_unambiguous_items_are_assigned(self):
        a={str(i):{'name':f'Lesson{i}.mp4'} for i in range(10)}
        files=[{'name':f'Lesson{i}.txt','text':str(i)} for i in range(8)]+[{'name':'Lesson8.txt','text':'one'},{'name':'Lesson8.srt','text':'two'}]
        assigned,pending=match_scripts({},a,list(a),files)
        self.assertEqual(len(assigned),8);self.assertEqual(len(pending),2)

if __name__=='__main__':unittest.main()
