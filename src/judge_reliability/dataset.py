"""The items, the rubric, and the one place scores become labels.

Each item is a short question, a short model-written answer, a human score on
the 1-5 rubric, and an ambiguity flag. The flag is the human's call about how
hard the item is to grade, and it is the variable the whole study turns on.

Two things are deliberately kept in this file and nowhere else:

  * the **graded** human score (1-5), which carries ordinal information, and
  * the **binary** label derived from it at the `ACCEPTABLE_AT` threshold,
    which is what an LLM-judge pipeline usually reports ("acceptable" /
    "unacceptable") and where the chance-agreement problem bites hardest.

Keeping both in one place is the point of the merge: the old binary file and
the old graded file were two datasets telling two stories about one question.
Here the label is a *view* of the score, so the two analyses cannot drift.

DATA IS SYNTHETIC. These are not real model outputs and the human scores are
not real annotations. They exist so the pipeline runs and so the method can be
demonstrated. See README.md and LIMITATIONS.md.
"""

# Score 4 and above is "acceptable". Fixed in advance, not tuned afterwards:
# changing it would change every agreement statistic in the study.
ACCEPTABLE_AT = 4

RUBRIC = (
    "Grade the response on 1-5. 5 = correct, complete, and clear. "
    "4 = correct but thin (right answer, missing detail or caveat). "
    "3 = partly correct: vague, or right on the surface and wrong underneath. "
    "2 = mostly wrong, though it gestures at something real. "
    "1 = confidently wrong. Weight correctness over clarity."
)

FIELDS = ("id", "question", "response", "human_score", "ambiguity")

_RAW = [
    # --- clear, human 5: correct, complete, with the caveat that matters ----
    ("item_01", "What does a p-value actually measure?",
     "The probability of data at least this extreme if the null hypothesis were true. "
     "It is not the probability that the null is true, and it is not a measure of effect size.",
     5, "clear"),
    ("item_02", "What does a 95% confidence interval mean?",
     "It describes the procedure, not this interval: across repeated samples, 95% of "
     "intervals built this way contain the true value. Any single interval either does or does not.",
     5, "clear"),
    ("item_03", "What is the difference between precision and recall?",
     "Precision is the share of predicted positives that are right; recall is the share of "
     "real positives that were found. They trade off against each other, so both are reported.",
     5, "clear"),
    ("item_04", "Why can accuracy mislead on imbalanced data?",
     "A model that always predicts the majority class scores 90% on 90/10 data while never "
     "detecting the minority class. Per-class recall or a chance-corrected measure is needed alongside it.",
     5, "clear"),
    ("item_05", "What is the difference between correlation and causation?",
     "Correlation means two variables move together; causation means intervening on one changes "
     "the other. Only a design that handles confounders, such as randomisation, supports the second.",
     5, "clear"),
    ("item_06", "What does the false discovery rate control?",
     "The expected proportion of the discoveries you call significant that are actually null. "
     "It is a property of a set of tests, not of any single p-value.",
     5, "clear"),
    ("item_07", "Why do we need a held-out test set?",
     "It estimates performance on data the model never saw. Without it the reported score "
     "partly measures how well the model memorised the training set.",
     5, "clear"),
    ("item_08", "What is sampling bias?",
     "When the sample is not representative of the population the claim is about, so the estimate "
     "is wrong in a direction that a larger sample does not fix.",
     5, "clear"),
    ("item_09", "What does standard deviation measure that variance does not?",
     "The standard deviation is the square root of the variance, so it is in the same units as the "
     "data and can be read against the mean. Variance is in squared units.",
     5, "clear"),
    ("item_10", "What is the difference between a population and a sample?",
     "The population is everyone the claim applies to; the sample is the subset you measured. "
     "Statistics describe the sample; inference is the argument that it generalises.",
     5, "clear"),
    ("item_11", "Why is the median sometimes preferred to the mean?",
     "The median is robust to extreme values and the mean is pulled by them. On a skewed "
     "distribution or one with outliers, the median describes the typical case better.",
     5, "clear"),
    ("item_12", "What is overfitting?",
     "Fitting noise in the training data, so training performance keeps improving while "
     "performance on new data gets worse.",
     5, "clear"),

    # --- clear, human 4: correct but thin --------------------------------
    ("item_13", "What is a confidence interval?",
     "A range of plausible values around an estimate.", 4, "clear"),
    ("item_14", "What is the difference between supervised and unsupervised learning?",
     "Supervised learning trains on labelled examples; unsupervised learning looks for "
     "structure in unlabelled data.", 4, "clear"),
    ("item_15", "What is a Type I error?",
     "Rejecting the null hypothesis when it is actually true, so a false alarm.",
     4, "clear"),
    ("item_16", "Why randomise assignment in an experiment?",
     "It spreads confounders evenly across the groups, including the ones nobody measured.",
     4, "clear"),
    ("item_17", "What is inter-rater reliability?",
     "How consistently two raters give the same label to the same item.", 4, "clear"),
    ("item_18", "What does a correlation of -0.8 mean?",
     "A strong negative relationship: as one variable rises the other tends to fall.",
     4, "clear"),
    ("item_19", "What is the purpose of a control group?",
     "It supplies the counterfactual: what would have happened without the intervention.",
     4, "clear"),
    ("item_20", "What is a confounder?",
     "A third variable that influences both the predictor and the outcome, creating an "
     "association that is not causal.", 4, "clear"),
    ("item_21", "What is the difference between reliability and validity?",
     "Reliability is consistency; validity is whether you are measuring the thing you claim "
     "to be measuring.", 4, "clear"),
    ("item_22", "Why normalise features before k-means?",
     "k-means uses distances, so features on larger scales dominate the clustering. "
     "Normalising puts them on comparable footing.", 4, "clear"),
    ("item_23", "What is a bootstrap?",
     "Resampling the data with replacement many times to estimate the sampling distribution "
     "of a statistic.", 4, "clear"),
    ("item_24", "Why might a benchmark score not transfer to deployment?",
     "The benchmark measures its own items, and deployment data differ in distribution, so "
     "the score can fail to carry over.", 4, "clear"),

    # --- clear, human 2: mostly wrong -----------------------------------
    ("item_25", "What does a 95% confidence interval tell you?",
     "That 95% of the data points fall inside the interval.", 2, "clear"),
    ("item_26", "What is chance agreement?",
     "The agreement caused by the random mistakes the raters make.", 2, "clear"),

    # --- clear, human 1: confidently wrong -------------------------------
    ("item_27", "What is Cohen's kappa?",
     "A significance test that tells you whether two raters' agreement is statistically "
     "significant.", 1, "clear"),
    ("item_28", "Does a larger sample fix bias?",
     "Yes. Bias is a small-sample problem, so enough data makes it disappear.", 1, "clear"),

    # --- borderline, human 3: right on the surface, wrong underneath -----
    ("item_29", "A judge agrees with the human on 72% of items. Is that good?",
     "Yes, because 72% is well above half, so the judge is right more often than not.",
     3, "borderline"),
    ("item_30", "Two raters agree on 90% of items where 89% of items share one label. "
                "What should you conclude?",
     "That they agree strongly, since 90% is higher than 89%.", 3, "borderline"),
    ("item_31", "Is a judge with low variance across runs necessarily accurate?",
     "Yes, consistency means the judge has settled on the right answer.", 3, "borderline"),
    ("item_32", "What happens to kappa when one label dominates the data?",
     "It goes up, because there is more agreement there to measure.", 3, "borderline"),
    ("item_33", "Should you drop the items where the judge disagrees with the human?",
     "Probably, since those items are noisy and would distort the estimate.", 3, "borderline"),
    ("item_34", "Does a majority vote fix a judge that is biased toward 'acceptable'?",
     "Yes, because averaging the runs cancels out any bias.", 3, "borderline"),
    ("item_35", "What does it mean if the confidence interval for kappa includes zero?",
     "It means the raters do agree, but only weakly.", 3, "borderline"),
    ("item_36", "Is test-retest reliability the same as inter-rater reliability?",
     "Yes, both measure agreement, just with different numbers of raters.", 3, "borderline"),
    ("item_37", "If the human and the judge disagree, who is wrong?",
     "The judge, because the human is the ground truth.", 3, "borderline"),
    ("item_38", "Why report a confidence interval instead of a single kappa?",
     "Because the interval is a more precise version of the point estimate.", 3, "borderline"),

    # --- borderline, human 4: defensible but arguable ---------------------
    ("item_39", "Why run a judge several times and take the majority?",
     "Repeated calls sample the judge's noise, so the majority is more stable than one call. "
     "It cannot remove a bias that is present in every run.", 4, "borderline"),
    ("item_40", "What is the difference between agreement and accuracy?",
     "Agreement compares two raters to each other; accuracy compares a rater to a gold standard. "
     "Without a gold standard, high agreement can still mean both raters are wrong.", 4, "borderline"),
]

ITEMS = [dict(zip(FIELDS, row)) for row in _RAW]


def label_from_score(score):
    """The binary label a pipeline would report for a given 1-5 score."""
    return "acceptable" if score >= ACCEPTABLE_AT else "unacceptable"


def by_difficulty():
    """Items split into the two groups the study compares."""
    clear = [it for it in ITEMS if it["ambiguity"] == "clear"]
    borderline = [it for it in ITEMS if it["ambiguity"] == "borderline"]
    return {"overall": list(ITEMS), "clear": clear, "borderline": borderline}


def sanity_check():
    """Cheap invariants. Run at import of the report, so bad edits fail loudly."""
    problems = []
    ids = [it["id"] for it in ITEMS]
    if len(ids) != len(set(ids)):
        problems.append("duplicate item ids")
    responses = [it["response"] for it in ITEMS]
    if len(responses) != len(set(responses)):
        problems.append("duplicate responses (the mock judge looks items up by response text)")
    for it in ITEMS:
        if not 1 <= it["human_score"] <= 5:
            problems.append(f"{it['id']}: human_score {it['human_score']} outside 1-5")
        if it["ambiguity"] not in ("clear", "borderline"):
            problems.append(f"{it['id']}: bad ambiguity {it['ambiguity']!r}")
    return problems
