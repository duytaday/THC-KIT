import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import qc_bridge

class PromiseTests(unittest.TestCase):
    def test_only_explicit_subjects_bind_promised_repository_proof(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);source=folder/'source.fixture';source.write_bytes(b'unit fixture, not video')
            clip=dict(file=str(source),source_start=0,start=0,end=1,source_name='Recordly.mp4')
            settings=dict(script='5 repo GitHub. Recordly.',insert_sound='none');plan=dict(proof=[clip],events=[],music={'mode':'off'})
            def run():
                with patch.object(qc_bridge,'prepare',return_value={'gates':{'B':{}}}):qc_bridge.prepare_export(folder,dict(path=str(source),duration=2),settings,plan)
                return json.loads((folder/'acceptance-profile.json').read_text(encoding='utf-8'))
            before=run();self.assertEqual(next(r for r in before['proof_followups'] if r['subject']=='Recordly')['status'],'UNASSIGNED')
            clip.update(demonstrates='Recordly',visual_claim='Read the release title');after=run()
            r=next(r for r in after['proof_followups'] if r['subject']=='Recordly');self.assertEqual(r['status'],'PROVIDED_UNVERIFIED');self.assertFalse(r['editorial_verified'])

    def test_five_repo_brief_does_not_substitute_repo_names_from_another_episode(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);source=folder/'source.fixture';source.write_bytes(b'unit fixture, not video')
            with patch.object(qc_bridge,'prepare',return_value={'gates':{'B':{}}}):
                qc_bridge.prepare_export(folder,dict(path=str(source),duration=2),dict(script='5 repo GitHub. Recordly. Remotion.',insert_sound='none'),dict(proof=[],events=[],music={'mode':'off'}))
            profile=json.loads((folder/'acceptance-profile.json').read_text(encoding='utf-8'));names=[p['repo_name'] for p in profile['demonstrations']]
            self.assertEqual(names[:2],['Recordly','Remotion']);self.assertEqual(len(names),5);self.assertTrue(all(n.startswith('UNASSIGNED') for n in names[2:]));self.assertNotIn('Runway',names)

if __name__=='__main__':unittest.main()
