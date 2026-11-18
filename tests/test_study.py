"""The check this repository exists to argue for, turned on itself.

The earlier version of this project had a README quoting kappa = 0.34 while the
case study page quoted 0.98, and the code supported neither. Number drift is the
failure mode of a measurement project, so it gets a test: run the study, and
fail if the README no longer quotes what the code actually produces.

    python3 -m unittest discover -s tests -t . -v

Standard library only, so it runs anywhere the study runs, including CI.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from judge_reliability.dataset import ITEMS, label_from_score, sanity_check
from judge_reliability.mock_judge import MockAnthropic
from judge_reliability.reliability import (
    cohens_kappa,
    icc_2_1,
    majority_scores,
    quadratic_weighted_kappa,
    run_study,
)

SEED = 11
RUNS = 8
TEMPERATURE = 0.7


class DatasetTest(unittest.TestCase):
    def test_invariants_hold(self):
        self.assertEqual(sanity_check(), [])

    def test_size_and_split(self):
        self.assertEqual(len(ITEMS), 40)
        clear = [i for i in ITEMS if i["ambiguity"] == "clear"]
        self.assertEqual(len(clear), 28)

    def test_threshold_is_where_the_readme_says(self):
        self.assertEqual(label_from_score(4), "acceptable")
        self.assertEqual(label_from_score(3), "unacceptable")


class StatisticTest(unittest.TestCase):
    def test_perfect_agreement_is_one(self):
        kappa, observed, _ = cohens_kappa([("a", "a"), ("b", "b"), ("a", "a")])
        self.assertAlmostEqual(kappa, 1.0)
        self.assertAlmostEqual(observed, 1.0)

    def test_one_label_only_is_undefined_not_perfect(self):
        kappa, _, chance = cohens_kappa([("a", "a")] * 5)
        self.assertIsNone(kappa, "kappa must be None, not 1.0, when chance agreement is 1")
        self.assertEqual(chance, 1.0)

    def test_weighted_kappa_bounds(self):
        self.assertAlmostEqual(quadratic_weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)
        self.assertLess(quadratic_weighted_kappa([1, 1, 2, 2], [5, 5, 4, 4]), 0.0)

    def test_icc_needs_at_least_two_runs(self):
        self.assertIsNone(icc_2_1([[3], [4]]))

    def test_icc_is_one_when_the_runs_are_identical(self):
        self.assertAlmostEqual(icc_2_1([[1, 1], [2, 2], [3, 3]]), 1.0)

    def test_majority_takes_the_mode(self):
        self.assertEqual(majority_scores({"x": [3, 3, 4, 3], "y": [2, 3, 2, 4]})["x"], 3)
        self.assertEqual(majority_scores({"x": [3, 3, 4, 3], "y": [2, 3, 2, 4]})["y"], 2)


class ReadmeMatchesTheRunTest(unittest.TestCase):
    """If these fail, the README and the code have drifted apart. Fix the text."""

    @classmethod
    def setUpClass(cls):
        cls.result = run_study(MockAnthropic(seed=SEED), n_runs=RUNS, temperature=TEMPERATURE)
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_headline_numbers_are_quoted(self):
        r = self.result
        expected = {
            "ICC, clear items": r["test_retest"]["clear"]["icc"],
            "ICC, borderline items": r["test_retest"]["borderline"]["icc"],
            "binary kappa, single call": r["single_call"]["cohens_kappa"],
            "binary kappa, majority": r["majority_vote"]["cohens_kappa"],
            "weighted kappa, single call": r["single_call"]["quadratic_kappa"],
            "weighted kappa, majority": r["majority_vote"]["quadratic_kappa"],
        }
        for label, value in expected.items():
            with self.subTest(label=label):
                self.assertIn(
                    f"{value:.2f}", self.readme,
                    msg=f"README no longer quotes {value:.2f} for {label}; update the results table",
                )

    def test_borderline_collapse_is_quoted(self):
        value = self.result["single_call_by_difficulty"]["borderline"]["quadratic_kappa"]
        # The README writes this one with a Unicode minus sign.
        self.assertIn(f"{value:.2f}".replace("-", "\u2212"), self.readme)

    def test_claim_about_repetition_matches_the_decomposition(self):
        d = self.result["error_decomposition"]
        self.assertEqual(d["n_events_fixed"] + d["n_bias_events"], self.result["n_disagreements"])
        self.assertIn(f"repaired **{d['n_events_fixed']}**", self.readme)
        self.assertIn(f"**{d['n_bias_events']} survived**", self.readme)

    def test_determinism(self):
        again = run_study(MockAnthropic(seed=SEED), n_runs=RUNS, temperature=TEMPERATURE)
        self.assertEqual(self.result["single_call"], again["single_call"])


if __name__ == "__main__":
    unittest.main()
