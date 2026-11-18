#!/usr/bin/env python3
"""Can you trust an LLM judge? Run the study and print the report.

    python3 analysis.py                 # 40 items x 8 runs, simulated judge
    python3 analysis.py --runs 12
    python3 analysis.py --temperature 0
    python3 analysis.py --save-runs     # also write data/judge_runs.csv
    python3 analysis.py --charts        # also write reports/*.png
    python3 analysis.py --json          # machine-readable result

No installation and no API key: the default client is the simulated judge in
src/judge_reliability/mock_judge.py. Passing a real `anthropic.Anthropic()` to
`run_study` is the only change needed to run it live (see README).

The report answers three questions in order:
  1. Does the judge agree with itself?      (test-retest, ICC)
  2. Does it agree with the human?          (single call vs 8-run majority)
  3. Where does it fail?                    (by difficulty, and item by item)
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from judge_reliability.dataset import ITEMS, by_difficulty, label_from_score, sanity_check
from judge_reliability.mock_judge import MockAnthropic
from judge_reliability.reliability import describe, run_study

LINE = "-" * 74


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=8, help="repeated judgments per item")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=11, help="simulated judge seed")
    parser.add_argument("--save-runs", action="store_true", help="write data/judge_runs.csv")
    parser.add_argument("--charts", action="store_true", help="write reports/*.png (needs matplotlib)")
    parser.add_argument("--json", action="store_true", help="print the result dict as JSON")
    args = parser.parse_args(argv)

    problems = sanity_check()
    if problems:
        print("dataset problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    results = run_study(MockAnthropic(seed=args.seed), n_runs=args.runs,
                        temperature=args.temperature)

    if args.json:
        print(json.dumps({k: v for k, v in results.items() if k != "scores"}, indent=2, default=str))
        return 0

    report(results)
    if args.save_runs:
        path = save_runs(results)
        print(f"\nwrote {path.relative_to(ROOT)}")
    if args.charts:
        from judge_reliability.charts import make_all
        for path in make_all(results, ROOT / "reports"):
            print(f"wrote {Path(path).relative_to(ROOT)}")
    return 0


def report(results):
    counts = {name: len(subset) for name, subset in by_difficulty().items()}
    acceptable = sum(1 for item in ITEMS if label_from_score(item["human_score"]) == "acceptable")

    print(LINE)
    print("LLM-AS-JUDGE RELIABILITY STUDY")
    print(LINE)
    print(f"  {results['n_items']} items ({counts['clear']} clear, {counts['borderline']} borderline), "
          f"{results['n_runs']} judgments each, temperature {results['temperature']}")
    print(f"  human labels: {acceptable} acceptable, {len(ITEMS) - acceptable} unacceptable "
          f"({acceptable / len(ITEMS):.0%} acceptable)")
    print("  judge: SIMULATED (method demonstration, not a finding about a real model)")

    print(f"\n1. TEST-RETEST — does the judge agree with itself?")
    print(f"   {'group':<12}{'n':>4}{'ICC':>8}{'unanimous':>12}{'mean SD':>10}{'mean range':>12}")
    for group in ("overall", "clear", "borderline"):
        d = results["test_retest"][group]
        icc = "n/a" if d["icc"] is None else f"{d['icc']:.2f}"
        print(f"   {group:<12}{d['n_items']:>4}{icc:>8}"
              f"{d['pct_items_unanimous'] * 100:>11.0f}%{d['mean_within_item_sd']:>10.2f}"
              f"{d['mean_within_item_range']:>12.1f}")

    single = results["single_call"]
    majority = results["majority_vote"]
    print(f"\n2. HUMAN AGREEMENT — does it agree with the annotator?")
    print(f"   {'':<32}{'single call':>15}{'8-run majority':>17}")
    rows = [
        ("quadratic-weighted kappa", _fmt(single["quadratic_kappa"]), _fmt(majority["quadratic_kappa"])),
        ("Cohen's kappa (binary gate)", _fmt(single["cohens_kappa"]), _fmt(majority["cohens_kappa"])),
        ("raw agreement", _pct(single["observed_agreement"]), _pct(majority["observed_agreement"])),
        ("chance agreement", _pct(single["chance_agreement"]), _pct(majority["chance_agreement"])),
        ("exact match (1-5)", _pct(single["exact_match_rate"]), _pct(majority["exact_match_rate"])),
        ("within 1 point", _pct(single["within_1_point_rate"]), _pct(majority["within_1_point_rate"])),
        ("mean signed error (judge-human)", f"{single['mean_signed_error_bias']:+.2f}",
         f"{majority['mean_signed_error_bias']:+.2f}"),
    ]
    for label, a, b in rows:
        print(f"   {label:<32}{a:>15}{b:>17}")
    print(f"   95% bootstrap CI on the single-call binary kappa: "
          f"[{single['ci_lower']:.3f}, {single['ci_upper']:.3f}]"
          if single["ci_lower"] is not None else "   (binary kappa undefined: one label only)")

    print("\n3. WHERE IT FAILS — agreement with the human, by item difficulty, single call")
    for group in ("clear", "borderline"):
        d = results["single_call_by_difficulty"][group]
        print(f"   {group:<12} n={d['n_items']:<3} weighted κ {_fmt(d['quadratic_kappa'])}   "
              f"exact {_pct(d['exact_match_rate'])}   within 1 {_pct(d['within_1_point_rate'])}   "
              f"bias {d['mean_signed_error_bias']:+.2f}")

    print(f"\n4. THE DISAGREEMENTS ON A SINGLE CALL ({results['n_disagreements']} of "
          f"{results['n_items']} items)")
    for d in results["disagreements"]:
        print(f"   {d['id']:<9}{d['ambiguity']:<11} human {d['human_score']} "
              f"({d['human_label']})  judge {d['judge_score']} ({d['judge_label']})")
    if not results["disagreements"]:
        print("   none")

    decomposition = results["error_decomposition"]
    fixed = decomposition["n_events_fixed"]
    bias = decomposition["n_bias_events"]
    print(f"\n5. WHAT REPETITION FIXES, AND WHAT IT DOESN'T")
    print(f"   Of the {results['n_disagreements']} single-call disagreements, the majority vote "
          f"repaired {fixed}")
    print(f"   (noise: the judge was capable of the right answer and the sample missed it) and "
          f"left {bias}")
    print("   standing (bias: every run made the same call, so averaging reproduces it).")
    if bias:
        print(f"   The errors that survive: {', '.join(decomposition['persistent_errors'])}")

    print(f"\n6. READING THIS HONESTLY")
    print(f"   Raw agreement is {_pct(single['observed_agreement'])}, but two raters labelling at random "
          f"from these base rates would")
    print(f"   already agree {_pct(single['chance_agreement'])} of the time, because "
          f"{acceptable / len(ITEMS):.0%} of items share the 'acceptable' label.")
    print("   After correcting for that, kappa is")
    print(f"   {_fmt(single['cohens_kappa'])} ({single['chance_corrected_band']}) on a single call and "
          f"{_fmt(majority['cohens_kappa'])} ({describe(majority['cohens_kappa'])}) on the majority "
          f"of {results['n_runs']}.")
    print(f"   On the {counts['borderline']} borderline items — the ones a human is actually needed "
          "for — the single")
    print(f"   call scores {_fmt(results['single_call_by_difficulty']['borderline']['quadratic_kappa'])} "
          f"weighted kappa while the {counts['clear']} clear items score "
          f"{_fmt(results['single_call_by_difficulty']['clear']['quadratic_kappa'])}: "
          "reliability is not one number.")
    print(f"   Test-retest says the same thing in the other currency: ICC "
          f"{_fmt(results['test_retest']['clear']['icc'])} clear versus "
          f"{_fmt(results['test_retest']['borderline']['icc'])} borderline, and "
          f"{results['test_retest']['borderline']['pct_items_unanimous'] * 100:.0f}% of borderline items")
    print("   got the same score twice in a row.")
    if single["ci_lower"] is not None and single["ci_lower"] <= 0.05:
        print("   The single-call interval's lower bound sits at or near zero: this sample cannot")
        print("   rule out chance agreement. More items narrow the interval; aggregation raises it.")
    print("   The two earlier versions of this study reported kappa = 0.34 and kappa = 0.98 for what")
    print("   looked like one claim. They were different claims: 0.34 needed errors that repeat every")
    print("   run (a lenient judge), 0.98 needed errors that vanish on repetition. Both are measured")
    print("   here, and the split in section 5 is the one number neither of them reported.")

    print("\n   What this does NOT tell you:")
    print("     - anything about a real model: the judge here is simulated")
    print("     - whether the human scores are right (there is no gold standard)")
    print("     - whether the judge is right and the human wrong on any item")
    print("     - whether the majority vote is correct, only that it is more stable")
    print("     - whether this holds at another threshold, rubric, model, or temperature")
    print(LINE)


def save_runs(results):
    path = ROOT / "data" / "judge_runs.csv"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = ["item_id", "ambiguity", "human_score"] + [
            f"run_{n + 1}" for n in range(results["n_runs"])
        ]
        writer.writerow(header)
        for item in ITEMS:
            writer.writerow(
                [item["id"], item["ambiguity"], item["human_score"]]
                + results["scores"][item["id"]]
            )
    return path


def _fmt(value):
    return "n/a" if value is None else f"{value:.2f}"


def _pct(value):
    return f"{value * 100:.0f}%"


if __name__ == "__main__":
    raise SystemExit(main())
