"""What do humans actually agree at? The ceiling the judge is measured against.

The judge study reports Cohen's kappa = 0.67 between a single judge call and one
human annotator (0.89 after majority-voting eight calls) on 40 synthetic items.
Those numbers have no reference point. How well do *humans* agree with each
other on items of this kind? If two people only reach 0.30, then a judge at 0.67
is not merely "fair" -- it is agreeing with one annotator more than the
annotators agree with each other, which should raise a question rather than
settle one.

This script measures the ceiling on real data: ChaosNLI (Nie et al., 2020)
collected 100 human annotations for each of 4,645 items drawn from the
development sets of SNLI, MultiNLI and alphaNLI.

Two estimates per dataset, computed independently so they check each other:

  1. SIMULATED PAIRWISE
     ChaosNLI ships per-item counts, not per-rater identities, so two
     independent annotators are drawn per item from that item's observed label
     distribution and Cohen's kappa is computed across items. Resampled B times
     for an interval.

  2. FLEISS' KAPPA
     Chance-corrected agreement across all 100 annotators at once.

They land within 0.01 of each other on every dataset, which is the evidence
that both are implemented correctly.

A NOTE ON WHAT THIS DATA CANNOT DO
  ChaosNLI also ships `old_labels`, the 5 original annotator labels for SNLI
  and MultiNLI items. It is tempting to compute the 10 pairwise rater-pair
  kappas from it for a stricter estimate. Do not: the ordering of `old_labels`
  is not stable across items, so "rater 3 on item 1" and "rater 3 on item 2"
  are different people. Computed that way every pair comes out near 0.03 --
  chance -- on both datasets, while the count-based estimate gives 0.45 and
  0.29. The pairing destroys the signal, so this script does not report it.
  Per-rater kappa needs data with persistent rater IDs, which this release
  does not include.

Standard library only, same as the rest of the repository.

Data:    data/chaosnli/chaosNLI_{snli,mnli_m,alphanli}.jsonl
Fetch:   python3 download_chaosnli.py
Source:  https://huggingface.co/datasets/earino/chaosnli
         revision eb7cc18dbfa0f161d93a2b22c7856ca0faafcf2b
License: CC BY-NC 4.0 -- non-commercial use only. Cite Nie et al. (2020).

Run:     python3 human_ceiling.py
"""

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "chaosnli"
N_BOOTSTRAP = 2000
SEED = 7

DATASETS = [
    ("SNLI", "chaosNLI_snli.jsonl", ["e", "n", "c"]),
    ("MultiNLI", "chaosNLI_mnli_m.jsonl", ["e", "n", "c"]),
    ("alphaNLI", "chaosNLI_alphanli.jsonl", ["1", "2"]),
]

# Headline numbers from analysis.py, for the comparison panel.
JUDGE_SINGLE_CALL = 0.67
JUDGE_MAJORITY = 0.89


def load(name):
    path = DATA_DIR / name
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}.\n"
            "Run: python3 download_chaosnli.py"
        )
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def cohens_kappa(a, b):
    """Cohen's kappa for two aligned label sequences.

    Returns (kappa, observed, chance), or (None, ...) when chance agreement is
    1.0 and kappa is undefined.
    """
    n = len(a)
    if n == 0:
        return None, None, None
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    chance = 0.0
    for lab in set(a) | set(b):
        chance += (a.count(lab) / n) * (b.count(lab) / n)
    if chance >= 1.0:
        return None, observed, chance
    return (observed - chance) / (1.0 - chance), observed, chance


def fleiss_kappa(count_rows, n_raters):
    """Fleiss' kappa from per-item category counts."""
    n_items = len(count_rows)
    if n_items == 0:
        return None
    p_items = []
    for row in count_rows:
        total = sum(row)
        if total != n_raters:
            raise ValueError("item has %d annotations, expected %d" % (total, n_raters))
        sq = sum(c * c for c in row)
        p_items.append((sq - n_raters) / (n_raters * (n_raters - 1)))
    p_bar = sum(p_items) / n_items
    n_categories = len(count_rows[0])
    p_j = [
        sum(row[j] for row in count_rows) / (n_items * n_raters)
        for j in range(n_categories)
    ]
    p_e = sum(p * p for p in p_j)
    if p_e >= 1.0:
        return None
    return (p_bar - p_e) / (1.0 - p_e)


def simulated_pairwise(rows, labels, rng):
    """Draw two independent annotators per item, compute kappa, resample."""
    kappas, raws = [], []
    for _ in range(N_BOOTSTRAP):
        a, b = [], []
        for row in rows:
            picked = rng.choices(labels, weights=row["label_count"], k=2)
            a.append(picked[0])
            b.append(picked[1])
        kappa, observed, _ = cohens_kappa(a, b)
        if kappa is not None:
            kappas.append(kappa)
            raws.append(observed)
    kappas.sort()
    raws.sort()
    return {
        "mean": sum(kappas) / len(kappas),
        "lo": kappas[int(0.025 * len(kappas))],
        "hi": kappas[int(0.975 * len(kappas)) - 1],
        "raw_mean": sum(raws) / len(raws),
    }


def agreement_bands(rows):
    """How dominant is the majority label, item by item."""
    bands = {"100%": 0, "80-99%": 0, "60-79%": 0, "50-59%": 0}
    for row in rows:
        top = max(row["label_count"]) / sum(row["label_count"])
        if top == 1.0:
            bands["100%"] += 1
        elif top >= 0.80:
            bands["80-99%"] += 1
        elif top >= 0.60:
            bands["60-79%"] += 1
        else:
            bands["50-59%"] += 1
    return {k: v / len(rows) for k, v in bands.items()}


def main():
    rng = random.Random(SEED)
    print("Human inter-annotator agreement on ChaosNLI")
    print("Nie et al. (2020) -- 100 annotations/item, CC BY-NC 4.0")
    print()

    results = []
    for display, filename, labels in DATASETS:
        rows = load(filename)
        fleiss = fleiss_kappa([row["label_count"] for row in rows], 100)
        sim = simulated_pairwise(rows, labels, rng)
        bands = agreement_bands(rows)
        results.append((display, len(rows), fleiss, sim, bands))

        print("--- %s (%s items x 100 annotators)" % (display, format(len(rows), ",")))
        print("    Two random annotators, Cohen's kappa: %.3f  "
              "95%% CI [%.3f, %.3f]" % (sim["mean"], sim["lo"], sim["hi"]))
        print("    Fleiss' kappa (all 100 raters):       %s"
              % ("n/a" if fleiss is None else "%.3f" % fleiss))
        print("    Their raw agreement:                  %.1f%%" % (sim["raw_mean"] * 100))
        print("    Majority-label dominance:             "
              + ", ".join("%s %.0f%%" % (k, v * 100) for k, v in bands.items()))
        print()

    print("--- Against the judge")
    print("    Single judge call vs one human:        %.3f" % JUDGE_SINGLE_CALL)
    print("    Eight calls, majority vote:            %.3f" % JUDGE_MAJORITY)
    print()
    for display, _, _, sim, _ in results:
        print("    Two humans on %-9s %8.3f   ->  single call is %.2f above, "
              "majority vote %.2f above"
              % (display, sim["mean"],
                 JUDGE_SINGLE_CALL - sim["mean"], JUDGE_MAJORITY - sim["mean"]))
    print()
    print("Read this carefully. The judge items are synthetic and these items are")
    print("real, so this is not a head-to-head comparison -- it establishes the")
    print("scale of the target, not the judge's score.")
    print()
    print("What it does establish: a judge can agree with ONE annotator better than")
    print("two annotators agree with each other, and still be wrong, because a")
    print("single-annotator comparison has no way to separate shared error from")
    print("shared judgment. Agreement above the human ceiling is a warning sign,")
    print("not a trophy. The honest design puts the judge against an adjudicated")
    print("gold set and reports the inter-human ceiling on the same items.")


if __name__ == "__main__":
    main()
