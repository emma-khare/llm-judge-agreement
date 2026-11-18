# The rebuild exercise

This file is the point of the repository. Do these six steps in order, one sitting each. Do
not skip step 3.

## 1. Run it

```
python3 analysis.py
```

Look at the numbers. Before you read any further, write down what you think kappa of ~0.67
*means*. Not the definition — what it means about the judge.

## 2. Predict before you look

Open `src/judge_reliability/dataset.py`. There are 40 items, each with a human score and a
`clear` / `borderline` flag.

Write down:
- how many items you think the judge will disagree with the human on
- what you think raw agreement should be
- why raw agreement and kappa will give different answers

Then run the script and check yourself. If your raw agreement matches and your kappa intuition
doesn't, that's the lesson.

## 3. Delete the analysis and rewrite it

This is the step that actually builds the skill.

```
mv src/judge_reliability/reliability.py reliability_original.py
```

Now write `src/judge_reliability/reliability.py` from scratch. You may look at
`reliability_original.py` — but only at the *docstrings*, not the bodies. Goal, in order:
`cohens_kappa` (observed, chance, corrected), then `quadratic_weighted_kappa`, then
`bootstrap_ci`, then `icc_2_1`.

You will get it wrong. That's expected and it's the mechanism. When you are stuck for more
than 20 minutes, ask your husband one specific question ("why does dividing by (1 - pe) fix
the problem?") rather than asking him to fix it.

When you're done, compare:

```
diff src/judge_reliability/reliability.py reliability_original.py
```

The diff is your actual report card.

## 4. Change one thing and predict the effect

Pick one:
- `python3 analysis.py --temperature 0`. Predict what happens to ICC and to kappa *before*
  you run it. Why does one go to 1.00 and the other not?
- Shuffle the judge's scores across items so agreement is random. What does kappa do? (This
  is the sanity check your analysis has to survive.)
- Set every human score to 5. What happens, and why does the script print `n/a` instead of a
  number?

Write two sentences on what you found. That's a finding.

## 5. Replace the demo data

`dataset.py` items are **synthetic** — the question/response pairs and the human scores were
written to make the study runnable. They are not data.

Before this repository is public, you must either:
- put real judgments in it, or
- keep the synthetic items and label them clearly as a demo everywhere, including in the
  README title if necessary.

Publishing made-up numbers as if they were findings is the one mistake that would end your
credibility in a measurement role. You already caught yourself almost making it once, with
the data leakage. Don't make it twice.

## 6. Commit it yourself

```
git add analysis.py src/ README.md data/
git commit -m "Rewrite reliability engine from scratch"
```

Read your own diff first. If you can't explain a line in the commit, don't commit it yet.
