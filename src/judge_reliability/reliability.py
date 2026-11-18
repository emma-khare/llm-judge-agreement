"""The measurement engine: does the judge agree with itself, and with the human?

Two questions, and they are different questions:

  **Test-retest** — grade the same item eight times. If the eight scores agree,
  the judge is *reliable*. Measured with ICC(2,1) (absolute agreement, single
  rater), the share of items that came back unanimous, and the within-item
  standard deviation. Run on the whole set and then split by difficulty,
  because the interesting claim is that reliability is not one number.

  **Human agreement** — compare the judge's score to the annotator's. Two
  versions, and the gap between them is the point of this repository:
  the *single call* (what a pipeline actually does) and the *majority vote*
  across runs (what the earlier version of this project reported). Measured
  with quadratic weighted kappa on the 1-5 scores, Cohen's kappa on the binary
  labels at the >= 4 gate (with a bootstrap interval), plus raw and chance
  agreement, exact match, within-one-point match, and signed bias.

Everything here is plain Python: no numpy, no scikit-learn. ICC and weighted
kappa are a dozen lines each, and writing them out is the difference between
reporting a number and being able to defend it.
"""

import random
from collections import Counter
from statistics import mean

from .dataset import ITEMS, RUBRIC, by_difficulty, label_from_score
from .judge import judge_once

DEFAULT_RUNS = 8
DEFAULT_TEMPERATURE = 0.7
N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 7


# --------------------------------------------------------------------------
# collecting the scores
# --------------------------------------------------------------------------

def collect_scores(client, n_runs=DEFAULT_RUNS, temperature=DEFAULT_TEMPERATURE, items=None):
    """Grade every item `n_runs` times. Returns {item_id: [score, ...]}."""
    items = list(items if items is not None else ITEMS)
    scores = {item["id"]: [] for item in items}
    for _ in range(n_runs):
        for item in items:
            judgement = judge_once(
                item["question"], item["response"], RUBRIC,
                client=client, temperature=temperature,
            )
            scores[item["id"]].append(judgement.score)
    return scores


# --------------------------------------------------------------------------
# test-retest: does the judge agree with itself?
# --------------------------------------------------------------------------

def icc_2_1(rows):
    """ICC(2,1): two-way random effects, absolute agreement, single rater.

    `rows` is a list of score lists (items x runs). The statistic is

        (MSR - MSE) / (MSR + (k-1)MSE + k(MSC - MSE)/n)

    where MSR is between-item variance, MSC between-run variance (does the judge
    drift warmer or colder as the session goes on?) and MSE is the residual.
    The intuition: how much of the spread is *real difference between items*
    versus *noise in the same item*. 1.0 means the item effect dominates
    completely; 0 means the runs disagree as much as the items differ.

    Returns None when it is undefined (fewer than 2 items or 2 runs, or a
    degenerate table where every entry is identical).
    """
    n = len(rows)
    if n < 2:
        return None
    k = len(rows[0])
    if k < 2:
        return None

    grand = mean([mean(row) for row in rows])
    item_means = [mean(row) for row in rows]
    run_means = [mean([rows[i][j] for i in range(n)]) for j in range(k)]

    ss_items = k * sum((m - grand) ** 2 for m in item_means)
    ss_runs = n * sum((m - grand) ** 2 for m in run_means)
    ss_error = sum(
        (rows[i][j] - item_means[i] - run_means[j] + grand) ** 2
        for i in range(n) for j in range(k)
    )

    ms_items = ss_items / (n - 1)
    ms_runs = ss_runs / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denominator = ms_items + (k - 1) * ms_error + k * (ms_runs - ms_error) / n
    if denominator == 0:
        return None
    return (ms_items - ms_error) / denominator


def test_retest(scores, items, n_runs=None):
    """Reliability of the judge with itself, per difficulty group."""
    out = {}
    for group, subset in by_difficulty().items():
        if items is not None:
            keep = {item["id"] for item in items}
            subset = [item for item in subset if item["id"] in keep]
        if not subset:
            continue
        rows = [scores[item["id"]] for item in subset]
        runs = n_runs or len(rows[0])
        spreads = [max(row) - min(row) for row in rows]
        out[group] = {
            "n_items": len(subset),
            "n_runs": runs,
            "icc": icc_2_1(rows),
            "pct_items_unanimous": sum(1 for row in rows if len(set(row)) == 1) / len(rows),
            "mean_within_item_sd": mean([_sd(row) for row in rows]),
            "mean_within_item_range": mean(spreads),
        }
    return out


def _sd(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return (sum((v - m) ** 2 for v in values) / (len(values) - 1)) ** 0.5


# --------------------------------------------------------------------------
# agreement: does the judge agree with the human?
# --------------------------------------------------------------------------

def cohens_kappa(pairs):
    """Nominal Cohen's kappa on (human_label, judge_label) pairs.

    kappa = (po - pe) / (1 - pe)

      po = how often the two raters actually agreed
      pe = how often they would agree labelling at random, using their own
           label frequencies as the odds

    Returns kappa=None when pe == 1.0 (everyone used one label): the
    denominator is zero and kappa is undefined, not perfect.
    """
    n = len(pairs)
    labels = {h for h, _ in pairs} | {j for _, j in pairs}
    observed = sum(1 for h, j in pairs if h == j) / n

    chance = 0.0
    for label in labels:
        human_rate = sum(1 for h, _ in pairs if h == label) / n
        judge_rate = sum(1 for _, j in pairs if j == label) / n
        chance += human_rate * judge_rate

    if chance == 1.0:
        return None, observed, chance
    return (observed - chance) / (1.0 - chance), observed, chance


def quadratic_weighted_kappa(human_scores, judge_scores, low=1, high=5):
    """Quadratic weighted kappa for ordinal 1-5 scores.

    Plain kappa treats 4-vs-5 as just as wrong as 4-vs-1. On an ordinal scale
    that is false: a near miss should cost less. Quadratic weights

        w(i, j) = (i - j)^2 / (high - low)^2

    do that, and the correction for chance is the same idea as Cohen's kappa.
    Returns None if chance agreement is 1 (everyone used one score).
    """
    span = (high - low) ** 2
    n = len(human_scores)
    if n == 0:
        return None

    observed = 0.0
    for h, j in zip(human_scores, judge_scores):
        observed += ((h - j) ** 2) / span
    observed = 1.0 - observed / n  # weighted agreement, 1 = perfect

    human_hist = Counter(human_scores)
    judge_hist = Counter(judge_scores)
    chance = 0.0
    for a in range(low, high + 1):
        for b in range(low, high + 1):
            weight = 1.0 - ((a - b) ** 2) / span
            chance += (human_hist[a] / n) * (judge_hist[b] / n) * weight

    if chance == 1.0:
        return None
    return (observed - chance) / (1.0 - chance)


def bootstrap_ci(pairs, n_boot=N_BOOTSTRAP, seed=BOOTSTRAP_SEED):
    """95% percentile interval for the binary kappa, by resampling items.

    A kappa on 40 items is a noisy estimate. Resampling with replacement
    simulates "what if I had drawn a slightly different set of items?" and
    reports where 95% of those estimates landed. If that interval includes
    zero, the sample cannot rule out chance agreement.
    """
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_boot):
        resample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        kappa, _, _ = cohens_kappa(resample)
        if kappa is not None:
            estimates.append(kappa)
    if not estimates:
        return None, None
    estimates.sort()
    lower = estimates[int(0.025 * len(estimates))]
    upper = estimates[int(0.975 * len(estimates))]
    return lower, upper


def describe(kappa):
    """Plain-language band for a kappa (Landis & Koch, 1977)."""
    if kappa is None:
        return "undefined"
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


def agreement(items, judged_scores, with_ci=True):
    """Every agreement statistic for one set of judge scores.

    `judged_scores` is {item_id: score}. Returns a dict of plain numbers.
    """
    human = [item["human_score"] for item in items]
    judge = [judged_scores[item["id"]] for item in items]
    pairs = [(label_from_score(h), label_from_score(j)) for h, j in zip(human, judge)]

    kappa, observed, chance = cohens_kappa(pairs)
    lower, upper = bootstrap_ci(pairs) if with_ci else (None, None)
    errors = [j - h for h, j in zip(human, judge)]

    return {
        "n_items": len(items),
        "quadratic_kappa": quadratic_weighted_kappa(human, judge),
        "cohens_kappa": kappa,
        "chance_corrected_band": describe(kappa),
        "observed_agreement": observed,
        "chance_agreement": chance,
        "ci_lower": lower,
        "ci_upper": upper,
        "exact_match_rate": sum(1 for e in errors if e == 0) / len(errors),
        "within_1_point_rate": sum(1 for e in errors if abs(e) <= 1) / len(errors),
        "mean_signed_error_bias": mean(errors),
        "mean_abs_error": mean([abs(e) for e in errors]),
    }


def majority_scores(scores):
    """The modal score per item across runs; ties broken toward the item mean.

    This is the aggregation the study recommends: repeat the call, take the
    mode. Ties cannot decide, so a tie goes to the score nearest the mean of
    that item's runs, which is at least not arbitrary.
    """
    out = {}
    for item_id, runs in scores.items():
        counts = Counter(runs)
        top = max(counts.values())
        tied = [score for score, count in counts.items() if count == top]
        if len(tied) == 1:
            out[item_id] = tied[0]
        else:
            centre = mean(runs)
            out[item_id] = min(tied, key=lambda s: (abs(s - centre), s))
    return out


# --------------------------------------------------------------------------
# the whole study
# --------------------------------------------------------------------------

def run_study(client, n_runs=DEFAULT_RUNS, temperature=DEFAULT_TEMPERATURE, items=None):
    """Run both halves of the study and return one flat result dict."""
    items = list(items if items is not None else ITEMS)
    scores = collect_scores(client, n_runs=n_runs, temperature=temperature, items=items)

    single = {item_id: runs[0] for item_id, runs in scores.items()}
    majority = majority_scores(scores)

    groups = {
        "overall": items,
        "clear": [i for i in items if i["ambiguity"] == "clear"],
        "borderline": [i for i in items if i["ambiguity"] == "borderline"],
    }

    disagreements = [
        {
            "id": item["id"],
            "ambiguity": item["ambiguity"],
            "human_score": item["human_score"],
            "judge_score": single[item["id"]],
            "human_label": label_from_score(item["human_score"]),
            "judge_label": label_from_score(single[item["id"]]),
        }
        for item in items
        if label_from_score(item["human_score"]) != label_from_score(single[item["id"]])
    ]

    # Which single-call errors survive aggregation? A disagreement that the
    # majority vote removes was *noise*; one that survives is *bias*, and no
    # number of repeated calls will fix it.
    noise_fixed = []
    persistent = []
    for item in items:
        human_label = label_from_score(item["human_score"])
        if label_from_score(single[item["id"]]) != human_label:
            if label_from_score(majority[item["id"]]) == human_label:
                noise_fixed.append(item["id"])
            else:
                persistent.append(item["id"])

    return {
        "n_items": len(items),
        "n_runs": n_runs,
        "temperature": temperature,
        "error_decomposition": {
            "noise_errors_fixed_by_majority": noise_fixed,
            "persistent_errors": persistent,
            "n_events_fixed": len(noise_fixed),
            "n_bias_events": len(persistent),
        },
        "test_retest": test_retest(scores, items, n_runs=n_runs),
        "single_call": agreement(items, single),
        "majority_vote": agreement(items, majority),
        "single_call_by_difficulty": {
            group: agreement(subset, {item["id"]: single[item["id"]] for item in subset},
                             with_ci=False)
            for group, subset in groups.items() if group != "overall"
        },
        "disagreements": disagreements,
        "n_disagreements": len(disagreements),
        "scores": scores,
        "single_call_scores": single,
        "majority_scores": majority,
        "human_scores": {item["id"]: item["human_score"] for item in items},
        "ambiguity": {item["id"]: item["ambiguity"] for item in items},
    }
