import unittest
from qc_gates import mix_alignment


class CorrelationEvidenceTests(unittest.TestCase):
    def test_periodic_voice_chime_competition_is_not_a_confirmed_shift(self):
        result=mix_alignment([(.70032,-1.035),(.67013,-.69),(.61,0)],1)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertTrue(result['ambiguous'])

    def test_unique_four_frame_routing_error_still_fails(self):
        self.assertEqual(mix_alignment([(.99,4),(.2,0),(.15,-2)],1)['status'],'FAIL')

    def test_unique_on_time_match_passes_but_weak_match_does_not(self):
        self.assertEqual(mix_alignment([(.99,0),(.2,3)],1)['status'],'PASS')
        self.assertEqual(mix_alignment([(.4,0),(.2,3)],1)['status'],'UNVERIFIED')

    def test_ambiguous_best_inside_is_not_a_false_pass(self):
        self.assertEqual(mix_alignment([(.99,0),(.98,3)],1)['status'],'UNVERIFIED')


if __name__=='__main__':unittest.main()
