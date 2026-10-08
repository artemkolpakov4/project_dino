import random
import unittest

import fights


class FightRulesTest(unittest.TestCase):
    def test_razbeg_bust_over_ten_scores_zero(self):
        self.assertEqual(fights.razbeg_score([6, 5]), 0)

    def test_razbeg_sum_up_to_ten_counts(self):
        self.assertEqual(fights.razbeg_score([4, 3, 2]), 9)

    def test_oblomki_damage_is_opponent_spikes_minus_own_plates(self):
        self.assertEqual(fights.oblomki_damage(own_plates=2, opponent_spikes=5), 3)

    def test_oblomki_damage_never_negative(self):
        self.assertEqual(fights.oblomki_damage(own_plates=6, opponent_spikes=2), 0)

    def test_more_less_against_three_has_dominant_guess(self):
        # Правило «больше трёх или меньше»: тройка перебрасывается,
        # и «больше» всегда верно в 3 случаях из 5.
        self.assertAlmostEqual(fights.more_less_best_guess_rate(), 0.6)


class FightBalanceTest(unittest.TestCase):
    N = 4000

    def test_every_fight_is_fair_without_bonus(self):
        for name in fights.FIGHTS:
            rate = fights.win_rate(name, k=0, n=self.N, rng=random.Random(7))
            self.assertTrue(0.44 <= rate <= 0.56, (name, rate))

    def test_bonus_helps_in_every_fight(self):
        for name in fights.FIGHTS:
            base = fights.win_rate(name, k=0, n=self.N, rng=random.Random(11))
            boosted = fights.win_rate(name, k=2, n=self.N, rng=random.Random(11))
            self.assertGreater(boosted, base + 0.03, (name, base, boosted))

    def test_there_are_twelve_fights_three_per_stat(self):
        by_stat = {}
        for meta in fights.FIGHTS.values():
            by_stat.setdefault(meta["stat"], []).append(meta["format"])
        self.assertEqual(sorted(by_stat), ["броня", "сила", "скорость", "хитрость"])
        for formats in by_stat.values():
            self.assertEqual(sorted(formats), ["кубики", "реакция", "решение"])



class CalibratedBonusTest(unittest.TestCase):
    def test_calibrated_bonuses_reach_about_seventy_at_max_advantage(self):
        for name, params in fights.CALIBRATED.items():
            rate = fights.win_rate(name, k=5, n=6000, rng=random.Random(21), **params)
            self.assertTrue(0.60 <= rate <= 0.72, (name, rate))

    def test_calibrated_covers_all_twelve_fights(self):
        self.assertEqual(sorted(fights.CALIBRATED), sorted(fights.FIGHTS))


if __name__ == "__main__":
    unittest.main()
