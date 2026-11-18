# Project Build Log — LLM-as-Judge Reliability Study

A record of what was built, why, and the decisions that shaped it. Stands in for the chat
transcript so the project is understandable on another machine or later.

**Author:** Emma Khare
**Purpose:** Portfolio project 2 of a planned series, for a research role (Anthropic
Education Labs). Theme across the series: *can we trust our measures of AI and learning?*

## The idea

AI labs use models to evaluate models ("LLM-as-judge"). This project asks whether such a
judge is trustworthy, using the psychometrics researchers use to validate any instrument:
**test-retest reliability** (does it agree with itself?) and **chance-corrected human
agreement** (does it agree with a person, after subtracting luck?). It closes a gap left by
project 1 (an emotion study with a pretrained model; this one drives the Claude API
directly) and adds the reliability statistics the job asks for by name.

## Key decision: build against a simulated judge

The live Claude API needs a paid key and network access the build environment lacks. So the
pipeline was built against `MockAnthropic`, a stand-in with the same `.messages.create(...)`
surface as the real client. It plugs into the same `judge_once(client=...)` seam, so going
live is a one-line change. Every result is labelled a METHOD DEMONSTRATION, not a
real-model finding — that honesty line is the point of the project, not a disclaimer bolted
on afterwards.

The mock's assumptions are named constants at the top of `mock_judge.py` (noise on clear
items, noise on borderline items, a persistent leniency rate), because a simulation whose
parameters are buried is a simulation whose results cannot be argued with.

## The merge (this version)

Two earlier versions of this study existed:

| Version | Design | Headline |
|---|---|---|
| Binary gate | 40 items, `acceptable`/`unacceptable`, one judge pass, nominal kappa | raw agreement 72.5% → **κ = 0.34**, bootstrap CI [0.00, 0.63] |
| Repeated runs | 24 items, 1-5 scores, 8 runs, ICC + quadratic kappa | ICC 0.98 clear / 0.15 borderline; majority-vote **κ = 0.98** |

They disagreed, and the disagreement was not a bug. Working through it produced the finding
this repository is now organised around:

**κ = 0.34 and κ = 0.98 cannot both describe the same judge.** 0.34 requires errors that are
nearly deterministic (a judge that says "acceptable" almost every time — its mislabels repeat
on every run, so averaging reproduces them). 0.98 requires errors that are pure noise, which
averaging removes. Both are legitimate simulations; neither generalises. The number that
matters for practice is the *split between the two kinds of error*, which neither earlier
version reported.

So the merge put both analyses on **one dataset and one judge**:

- `dataset.py` holds 40 items with 1-5 human scores and a clear/borderline flag. The binary
  label is a *view* of the score at the ≥ 4 threshold (`label_from_score`), so the binary
  analysis and the ordinal analysis cannot drift apart. The old standalone CSV was deleted
  for exactly that reason: two datasets were two sources of truth.
- `reliability.py` computes ICC(2,1), unanimity, within-item SD, nominal and
  quadratic-weighted kappa, bootstrap intervals, the majority vote, and the
  **noise-vs-bias decomposition**.
- `analysis.py` prints it all as one report, standard library only.

Deliberately dropped: the Jupyter notebook. It duplicated the narrative that now lives in
`analysis.py` and the README, and two executable copies of one analysis is how numbers start
disagreeing again. If a notebook is wanted for the portfolio page, it should be generated
from this pipeline, not maintained beside it.

## What the merged study shows (simulated judge, temperature 0.7)

| Measure | Clear | Borderline |
|---|---|---|
| ICC (self-consistency) | 0.85 | **0.10** |
| % of items unanimous across 8 runs | 29% | **0%** |
| Weighted kappa vs human, single call | 0.86 | **-0.08** |

Human agreement: single call κ = 0.67 (weighted 0.72), majority of 8 κ = 0.89. Of 6
single-call disagreements, the majority repaired 5 and left 1 standing. At temperature 0 the
judge becomes perfectly stable (ICC 1.00) and still only reaches κ = 0.94 — stability is not
validity.

**Actionable conclusion:** reliability is not one number. It depends on item difficulty, and
on whether you spent one call or several. Repetition and majority voting fix noise; they do
not fix a judge that is wrong the same way every time. Measure which one you have before
prescribing the remedy.

## To run live later

1. Key at console.anthropic.com → `.env` file: `ANTHROPIC_API_KEY=sk-ant-...` (git-ignored).
2. Pass `anthropic.Anthropic()` instead of `MockAnthropic()` (README has the command; 320
   calls for 40 items × 8 runs).

## To rebuild on another computer

```
python3 analysis.py                        # report, no install needed
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python analysis.py --charts --save-runs
```

Everything is deterministic for a given `--seed` (default 11), so the report should match this
log exactly.
