"""Does the LLM judge agree with the human? And is that agreement real?

One question, one number: when an LLM judge and a human annotator label the
same examples, how often do they agree -- and how much of that is just luck?

Raw agreement ("they agreed 78% of the time") is a trap. If 90% of your
examples are 'acceptable', two raters who always say 'acceptable' agree 90%
of the time while measuring nothing. Cohen's kappa corrects for that by
subtracting the agreement you would expect from chance alone.

Input:  data/sample_judgments.csv   (columns: item_id, human_label, judge_label)
Output: a printed report

Run:    python3 analysis.py

No dependencies. Standard library only, on purpose, so every line can be read.
"""

import csv
import random

DATA_PATH = "data/sample_judgments.csv"
N_BOOTSTRAP = 2000
SEED = 7  # fixed so the confidence interval is reproducible


def load_rows(path):
    """Read the CSV into a list of (item_id, human_label, judge_label) tuples."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                (record["item_id"], record["human_label"], record["judge_label"])
            )
    return rows


def cohens_kappa(rows):
    """Return (kappa, observed_agreement, chance_agreement).

    kappa = (po - pe) / (1 - pe)

      po = how often the two raters actually agreed
      pe = how often they would agree if both labeled at random, using
           their own label frequencies as the odds

    Returns kappa=None when chance agreement is 1.0 (everyone used one
    label), because the denominator would be zero and kappa is undefined.
    """
    n = len(rows)
    labels = {h for _, h, _ in rows} | {j for _, _, j in rows}

    observed = sum(1 for _, h, j in rows if h == j) / n

    chance = 0.0
    for label in labels:
        human_rate = sum(1 for _, h, _ in rows if h == label) / n
        judge_rate = sum(1 for _, _, j in rows if j == label) / n
        chance += human_rate * judge_rate

    if chance == 1.0:
        return None, observed, chance

    return (observed - chance) / (1.0 - chance), observed, chance


def bootstrap_ci(rows, n_boot=N_BOOTSTRAP, seed=SEED):
    """Resample the data 2000 times to get a 95% interval around kappa.

    A single kappa on 40 items is a noisy estimate. Resampling with
    replacement simulates 'what if I had drawn a slightly different sample
    of items?' and reports where 95% of those estimates landed. If that
    interval straddles zero, you cannot claim the judge agrees with humans
    at all.
    """
    rng = random.Random(seed)
    estimates = []

    for _ in range(n_boot):
        resample = [rows[rng.randrange(len(rows))] for _ in rows]
        kappa, _, _ = cohens_kappa(resample)
        if kappa is not None:
            estimates.append(kappa)

    estimates.sort()
    lower = estimates[int(0.025 * len(estimates))]
    upper = estimates[int(0.975 * len(estimates))]
    return lower, upper


def describe(kappa):
    """Plain-language band for a kappa value (Landis & Koch, 1977)."""
    if kappa < 0.0:
        return "worse than chance"
    if kappa < 0.21:
        return "slight"
    if kappa < 0.41:
        return "fair"
    if kappa < 0.61:
        return "moderate"
    if kappa < 0.81:
        return "substantial"
    return "almost perfect"


def main():
    rows = load_rows(DATA_PATH)
    kappa, observed, chance = cohens_kappa(rows)
    lower, upper = bootstrap_ci(rows)

    print(f"items compared        {len(rows)}")
    print(f"raw agreement         {observed:.1%}")
    print(f"chance agreement      {chance:.1%}")
    print(f"Cohen's kappa         {kappa:.3f}  ({describe(kappa)})")
    print(f"95% bootstrap CI      [{lower:.3f}, {upper:.3f}]")

    if lower <= 0.05:
        print("\n-> The lower bound sits at or near zero. This sample cannot")
        print("   rule out that the judge agrees with humans only by chance.")
        print("   To narrow that interval you need more items, not a better metric.")

    disagreements = [(i, h, j) for i, h, j in rows if h != j]
    print(f"\ndisagreements         {len(disagreements)}")
    for item_id, human, judge in disagreements[:5]:
        print(f"  {item_id}: human={human!r} judge={judge!r}")

    print("\nWhat this does NOT tell you:")
    print("  - whether the human labels are correct (no gold standard here)")
    print("  - whether the judge is right and the human is wrong")
    print("  - whether either rater is stable across a second pass")
    print("  - whether the taxonomy is the right one to begin with")


if __name__ == "__main__":
    main()
