"""Tests for human_ceiling.py's statistics.

These need no downloaded data, so they run in CI where the CC BY-NC ChaosNLI
files are deliberately absent. The point is the same as the rest of the test
suite: if the README quotes a number, the code that produces it should be
checked independently of the run that produced it.
"""

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from human_ceiling import agreement_bands, cohens_kappa, fleiss_kappa, simulated_pairwise


class CohensKappaTest(unittest.TestCase):
    def test_perfect_agreement_is_one(self):
        kappa, observed, _ = cohens_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"])
        self.assertAlmostEqual(kappa, 1.0)
        self.assertAlmostEqual(observed, 1.0)

    def test_one_label_only_is_undefined_not_perfect(self):
        kappa, _, chance = cohens_kappa(["a"] * 6, ["a"] * 6)
        self.assertIsNone(kappa, "kappa must be None, not 1.0, when chance agreement is 1")
        self.assertAlmostEqual(chance, 1.0)

    def test_chance_level_agreement_is_zero(self):
        # rater A says a,b,c; rater B says c,b,a. They agree once in three, and
        # each label has the same 1/3 frequency in both -- so observed agreement
        # equals chance agreement exactly and kappa is 0.0, not negative.
        kappa, observed, _ = cohens_kappa(["a", "b", "c"], ["c", "b", "a"])
        self.assertAlmostEqual(observed, 1.0 / 3.0)
        self.assertAlmostEqual(kappa, 0.0, places=9)


class FleissKappaTest(unittest.TestCase):
    def test_hand_computed_example(self):
        # 2 items, 3 raters, 2 categories.
        # P_i = (2^2 + 1^2 - 3) / (3*2) = 1/3 for both items -> P_bar = 1/3
        # p_1 = p_2 = 0.5 -> P_e = 0.5
        # kappa = (1/3 - 0.5) / (1 - 0.5) = -1/3
        kappa = fleiss_kappa([[2, 1], [1, 2]], 3)
        self.assertAlmostEqual(kappa, -1.0 / 3.0, places=6)

    def test_unanimous_is_one(self):
        kappa = fleiss_kappa([[3, 0], [0, 3]], 3)
        self.assertAlmostEqual(kappa, 1.0, places=6)

    def test_wrong_rater_count_raises(self):
        with self.assertRaises(ValueError):
            fleiss_kappa([[2, 1]], 100)


class SimulatedPairwiseTest(unittest.TestCase):
    ROWS = [
        {"label_count": [100, 0, 0]},
        {"label_count": [50, 50, 0]},
        {"label_count": [34, 33, 33]},
    ]

    def test_is_deterministic_for_a_fixed_seed(self):
        first = simulated_pairwise(self.ROWS, ["e", "n", "c"], random.Random(7))
        second = simulated_pairwise(self.ROWS, ["e", "n", "c"], random.Random(7))
        self.assertEqual(first, second)

    def test_interval_brackets_the_mean(self):
        result = simulated_pairwise(self.ROWS, ["e", "n", "c"], random.Random(7))
        self.assertLessEqual(result["lo"], result["mean"])
        self.assertLessEqual(result["mean"], result["hi"])

    def test_raw_agreement_cannot_exceed_one(self):
        result = simulated_pairwise(self.ROWS, ["e", "n", "c"], random.Random(7))
        self.assertLessEqual(result["raw_mean"], 1.0)


class AgreementBandsTest(unittest.TestCase):
    def test_bands_partition_every_item(self):
        rows = [
            {"label_count": [100, 0, 0]},
            {"label_count": [90, 10, 0]},
            {"label_count": [70, 20, 10]},
            {"label_count": [45, 35, 20]},
        ]
        bands = agreement_bands(rows)
        self.assertAlmostEqual(sum(bands.values()), 1.0)
        self.assertAlmostEqual(bands["100%"], 0.25)
        self.assertAlmostEqual(bands["50-59%"], 0.25)


if __name__ == "__main__":
    unittest.main()
