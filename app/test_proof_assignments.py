import copy,tempfile,unittest
from pathlib import Path
import proof_assignments as proof


class ProofAssignmentTests(unittest.TestCase):
    def test_filename_and_substring_are_not_a_subject_assignment(self):
        q=dict(source_name='Recordly-success.mp4',demonstrates='Other Recordly tutorial')
        self.assertEqual(proof.candidates([q],'Recordly'),[])
        q['demonstrates']=' recordly ';self.assertEqual(proof.candidates([q],'Recordly'),[q])

    def test_known_illustration_cannot_acquire_product_proof_from_a_label(self):
        with self.assertRaisesRegex(ValueError,'illustration'):
            proof.assignment(dict(demonstrates='Recordly'),dict(data_class='reference_excerpt'))
        q=dict(demonstrates='Recordly',artifact_kind='generated_video')
        self.assertEqual(proof.candidates([q],'Recordly'),[])

    def test_claim_requires_subject_and_plain_bounded_text(self):
        for row in (dict(visual_claim='Show success'),dict(demonstrates=7),dict(demonstrates='a\nb'),dict(visual_claim='a'*401)):
            with self.subTest(row=row),self.assertRaises(ValueError):proof.assignment(row,{})

    def test_supplied_source_stays_unverified_and_does_not_invent_contact(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source';path.write_bytes(b'unit bytes, not footage')
            q=dict(demonstrates='Xuất hóa đơn',file=str(path),source_start=3,start=5,end=7,visual_claim='Đọc số hóa đơn')
            original=copy.deepcopy(q);r=proof.followups([dict(subject='Xuất hóa đơn',claim='Read invoice')],[q])[0]
            self.assertEqual(r['status'],'PROVIDED_UNVERIFIED');self.assertFalse(r['editorial_verified'])
            self.assertEqual(r['sources'][0]['source_range'],[3,5]);self.assertEqual(r['sources'][0]['observed_anchors'],{})
            self.assertEqual(q,original)

    def test_missing_subject_is_separate_from_supplied_but_unreviewed(self):
        r=proof.followups([dict(subject='Runway',claim='Show input')],[])[0]
        self.assertEqual(r['status'],'UNASSIGNED');self.assertEqual(r['sources'],[])

    def test_old_profile_is_not_upgraded_to_an_explicit_assignment(self):
        r=proof.frozen_followups(dict(demonstrations=[dict(repo_name='Recordly',source_asset='Recordly.mp4')]))[0]
        self.assertEqual(r['status'],'LEGACY_UNVERIFIED');self.assertFalse(r['editorial_verified'])

    def test_legacy_explicit_absence_is_not_discarded_as_unknown(self):
        r=proof.frozen_followups(dict(demonstrations=[dict(repo_name='Runway',source_asset='',source_sha256='0'*64)]))[0]
        self.assertEqual(r['status'],'UNASSIGNED')
