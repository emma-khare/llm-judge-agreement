# The rebuild exercise

This file is the point of the repository. Do these six steps in order,
one sitting each. Do not skip step 3.

## 1. Run it

```
python3 analysis.py
```

Look at the number it prints. Before you read any further, write down
what you think kappa of ~0.5 *means*. Not the definition — what it means
about the judge.

## 2. Predict before you look

Open `data/sample_judgments.csv`. There are 40 items. Count the
disagreements by eye (or with a spreadsheet).

Write down:
- how many items the two raters disagreed on
- what you think raw agreement should be
- why raw agreement and kappa will give different answers

Then run the script again and check yourself. If your raw agreement
matches and your kappa intuition doesn't, that's the lesson.

## 3. Delete the analysis and rewrite it

This is the step that actually builds the skill.

```
mv analysis.py analysis_original.py
```

Now write `analysis.py` from scratch. You may look at
`analysis_original.py` — but only at the *docstrings*, not the bodies.
Goal: load the CSV, compute observed agreement, compute chance
agreement, compute kappa, print all three.

You will get it wrong. That's expected and it's the mechanism. When you
are stuck for more than 20 minutes, ask your husband one specific
question ("why does dividing by (1 - pe) fix the problem?") rather than
asking him to fix it.

When you're done, compare:

```
diff analysis.py analysis_original.py
```

The diff is your actual report card.

## 4. Change one thing and predict the effect

Pick one:
- Shuffle the judge labels so agreement is random. What does kappa do?
  (This is the sanity check your analysis has to survive.)
- Make every item "acceptable". What happens, and why does the script
  print `None` instead of a number?
- Drop the 8 hardest items. Does kappa go up? Should you be allowed to
  drop them?

Write two sentences on what you found. That's a finding.

## 5. Replace the demo data

`data/sample_judgments.csv` is **synthetic** — I generated it. It exists
so the script runs. It is not data.

Before this repository is public, you must either:
- put real judgments in it, or
- keep the synthetic file and label it clearly as a demo everywhere,
  including in the README title if necessary.

Publishing made-up numbers as if they were findings is the one mistake
that would end your credibility in a measurement role. You already
caught yourself almost making it once, with the data leakage. Don't
make it twice.

## 6. Commit it yourself

```
git add analysis.py README.md data/
git commit -m "Rewrite kappa analysis from scratch"
```

Read your own diff first. If you can't explain a line in the commit,
don't commit it yet.
