# Next Steps & Future Work

Deliberate extensions, kept out of scope for this build but recorded.

## 1. Run it live (highest priority)
Swap `MockAnthropic()` for `anthropic.Anthropic()` and a key. Every number in the README then
becomes a claim about a real model instead of a demonstration. Everything is already built
for it: the client is the only seam.

## 2. How much of a real judge's error is bias?
The decomposition here is the most useful thing in the repository and the least developed: it
counts single-call errors that the majority vote repairs versus errors that survive. Run it
live and report that split per model. If most errors survive, sampling more is wasted money
and the fix has to be the instrument — rubric, prompt, or threshold.

## 3. Compare models, prompts, temperatures
Reliability depends on all three. Run the same design across several of each and report
reliability as a function of them: does lower temperature buy consistency at the cost of
nuance, or does it just freeze the bias in place?

## 4. Multiple human raters
Add 2-3 independent graders. Measure inter-HUMAN reliability first — that is the ceiling. A
judge that matches humans as well as humans match each other is doing well; one that is
noisier is not. Adjudicated disagreements also give the gold set this study lacks.

## 5. How many runs to trust a verdict?
Eight is a convention, not a finding. Measure how the majority verdict stabilises with the
number of runs, per difficulty level, and convert that into a cost per trustworthy
judgment — the number a team actually needs to budget.

## 6. Confidence-aware judging
Ask the judge for its own confidence and test whether low confidence predicts the borderline
items. If it does, confidence becomes a routing signal: send the low-confidence items to a
human instead of the long tail of everything.

## 7. Threshold sensitivity
The binary gate (≥ 4 = acceptable) moves kappa through the base rate. Plot kappa against the
threshold. If a conclusion flips between ≥ 3 and ≥ 5, it was a conclusion about the threshold,
not about the judge.

## 8. Bias probes
Test whether scores shift with surface features that a rubric should ignore: response length,
formality, hedging, confident tone. The simulated judge here has exactly this flaw built in
(systematic generosity on a share of items); the live version needs to be measured for it.

## 9. Connection to the broader portfolio
This is the second study in a series on whether we can trust our measures of AI and learning.
Natural companions: an AI-fluency measure (instrument design and validity) and a
capability-vs-engagement tool. Together they make one argument: the hard problem is not
building the tool, it is trusting the measure.
