# Constraints & Limitations

Every constraint and scope boundary, named. A measurement study is only credible if it is
honest about what it cannot conclude.

## What this project claims

> A working pipeline for measuring an LLM judge's reliability (test-retest ICC) and its
> chance-corrected agreement with a human (Cohen's and quadratic-weighted kappa, bootstrap
> intervals), plus a decomposition of disagreement into noise that repetition fixes and bias
> that it does not — and, on a **simulated** judge, the demonstration that reliability
> collapses on ambiguous items while a majority vote repairs the noise part only.

## What it does NOT claim

Anything about a specific real model's reliability, or that the numbers here would reproduce
with another rubric, threshold, model, or temperature. That needs a live run.

---

| # | Constraint | What it is | Why it matters | How to address it |
|---|-----------|-----------|----------------|-------------------|
| 1 | **Simulated judge** | The results come from `mock_judge.py`, not the live API (no key, no network in the build). | The numbers demonstrate the METHOD and the pipeline's behaviour, not a real model's reliability. | One-line client swap to `anthropic.Anthropic()` plus a key turns it into a live study. |
| 2 | **The simulation's constants are design choices** | `CLEAR_NOISE`, `PERSISTENT_LENIENCY_RATE`, `BORDERLINE_OFFSETS` were chosen to exercise the pipeline, not estimated from data. | The specific values of every statistic follow from them. Changing them changes the result. | Treat them as assumptions, stated in one file and in the README; a live run replaces them with observation. |
| 3 | **Synthetic items** | 40 question/response pairs and their human scores were written for this repository. | They are not a sample of anything; item difficulty was assigned, not measured. | Replace `dataset.py` with real collected judgments before quoting any number publicly. |
| 4 | **Small n (40 items)** | The bootstrap interval on the single-call kappa is [0.39, 0.89]. | An interval that wide cannot distinguish a fair judge from a good one. | Scale to hundreds of items across topics and difficulty levels; the interval narrows as √n. |
| 5 | **Single human rater, no gold standard** | "Human agreement" is agreement with one annotator. | Humans disagree too; without a gold set, high agreement can mean two raters share a mistake. | 2-3 independent raters; measure inter-HUMAN reliability first — that is the ceiling — and adjudicate disagreements into a gold set. |
| 6 | **One rubric, prompt, model, temperature, threshold** | All five were fixed, and the threshold (≥ 4 = acceptable) is a choice. | kappa depends on base rates, so the threshold alone can move it several points. | Vary each systematically; report reliability as a function of them. |
| 7 | **Majority voting fixes variance, not bias** | The decomposition here repaired 5 of 6 errors and left 1. | The widespread advice to "just sample a few times and take the majority" silently assumes the errors are noise. | Measure the surviving errors, as this repo does; fix bias with rubric, prompt, or threshold changes and re-measure. |
| 8 | **Snapshot in time** | Models are updated regularly. | A reliability result is dated the moment the model changes. | Re-run periodically and version-stamp every result with model, date, and settings. |
| 9 | **Ambiguity flag is subjective** | Clear vs. borderline is one person's call, made when the items were written. | The headline split rests on that judgment, and the borderline group is only 12 items. | Have multiple raters assign the flag; their disagreement becomes an objective ambiguity measure. |
| 10 | **Independence assumption** | The bootstrap resamples items as if exchangeable, and ICC assumes a two-way random design. | If items are clustered (same topic, same author), the interval is too narrow and ICC's assumptions are violated. | Cluster-aware resampling or a mixed model with topic as a random effect. |
| 11 | **One aggregation rule** | Majority vote with ties broken toward the item mean. | Other rules (mean, median, confidence-weighted) would give different numbers. | Compare rules on the same runs; the pipeline keeps the full score matrix so this is free. |

---

## The broader point

If an organization uses an LLM to grade, score, or filter at scale, the reliability of that
judge silently determines the quality of every downstream decision. An unreliable judge on
ambiguous cases — exactly where human oversight is most needed — will make confident,
inconsistent calls. And a *reliable* judge can still be wrong in the same direction every
time: at temperature 0 this simulated judge is perfectly stable (ICC 1.00) and still only
0.94 kappa, because its generosity is systematic.

Measuring both, and knowing which part of the error repetition can fix, is a prerequisite for
using LLM-as-judge responsibly.

*See [NEXT_STEPS.md](NEXT_STEPS.md) for concrete extensions.*
