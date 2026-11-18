# Can you trust an LLM judge?

A measurement study of inter-rater agreement between a human annotator and
an LLM judge, using Cohen's kappa instead of raw agreement.

> **Status: demo data.** `data/sample_judgments.csv` is synthetic, generated
> to make the script runnable. The numbers below are therefore an
> illustration of the method, not a finding about any real model. See
> [Data](#data) before citing anything here.

## The question

Teams increasingly use one LLM to grade another's output. The usual evidence
offered is a percentage: *"the judge agreed with humans 72% of the time."*

That number is close to meaningless on its own. If 70% of your examples share
one label, two raters who never think and always emit that label will agree
70% of the time. Raw agreement rewards lopsided data.

This repository asks a narrower, answerable question: **once you subtract the
agreement you'd expect by chance, is anything left?**

## Method

- 40 items, binary labels (`acceptable` / `unacceptable`)
- Two raters: a human annotator and an LLM judge
- **Cohen's kappa** as the agreement statistic: `(po - pe) / (1 - pe)`
- **Bootstrap confidence interval** (2,000 resamples, fixed seed) because a
  point estimate on 40 items is not an estimate, it's a rumour
- Pure standard library — no dependencies, so every line is readable

## Results (demo data)

| Quantity | Value |
|---|---|
| Items compared | 40 |
| Raw agreement | 72.5% |
| Chance agreement | 58.2% |
| **Cohen's kappa** | **0.341** (fair) |
| 95% bootstrap CI | ~[0.00, 0.63] |

**Reading this honestly:** raw agreement of 72.5% sounds like a working
judge. Nearly 58 of those points were free, because the labels are lopsided.
After correction, kappa is 0.341 — "fair" at best. And the confidence
interval's lower bound sits at essentially zero, which means this sample
**cannot rule out that the judge agrees with humans only by chance.**

The disagreeing items are also not evenly distributed: the judge errs far more
often on the minority class. A summary statistic hides that; the confusion
pattern is where the useful information lives.

## Limitations

This is a small, single-annotator, binary, single-domain study on synthetic
data. It cannot tell you:

- whether the human labels are correct — there is no gold standard here
- whether the judge is right and the human wrong on any given item
- whether either rater is stable across a second pass (no intra-rater check)
- whether the taxonomy itself is the right one to be measuring against

A real version of this study needs an adjudicated gold set, at least two
independent human annotators, a measure of each human's self-agreement, and
a sample large enough to narrow the interval.

## Reproduce

```
python3 analysis.py
```

No installation required. Standard library only.

## Data

`data/sample_judgments.csv` is **synthetic** (`item_id,human_label,judge_label`).
It was generated with a fixed seed so the script runs out of the box.
Replacing it with real judgments is step 5 of [REBUILD.md](REBUILD.md).

## Why this exists

I work in research on conversational AI, where the recurring failure I see is
not bad statistics — it is a confident number with no account of what it
measures. This is the smallest complete version of the check I think every
LLM-as-judge pipeline should have to pass.
