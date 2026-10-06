import random
import statistics
import unittest

import match


class MatchTest(unittest.TestCase):
    def test_match_always_ends_by_gate_or_collapse(self):
        for seed in range(40):
            result = match.play(4, random.Random(seed))
            self.assertIn(result.reason, ("ворота", "обвал"), seed)
            self.assertLessEqual(result.rounds, 30, seed)

    def test_quiet_turn_fits_design_range(self):
        rng = random.Random(3)
        times = [match.turn_seconds(rng, waiting=3, steps=2, new_room=True, fight=False, shop=False)
                 for _ in range(2000)]
        self.assertTrue(30 <= statistics.mean(times) <= 50, statistics.mean(times))

    def test_fight_adds_about_thirty_seconds(self):
        rng = random.Random(4)
        quiet = statistics.mean(match.turn_seconds(rng, 3, 2, True, False, False) for _ in range(2000))
        fight = statistics.mean(match.turn_seconds(rng, 3, 2, True, True, False) for _ in range(2000))
        self.assertTrue(25 <= fight - quiet <= 35, fight - quiet)

    def test_two_players_play_shorter_than_four(self):
        two = statistics.mean(match.play(2, random.Random(s)).minutes for s in range(60))
        four = statistics.mean(match.play(4, random.Random(s)).minutes for s in range(60))
        self.assertLess(two, four)


if __name__ == "__main__":
    unittest.main()
