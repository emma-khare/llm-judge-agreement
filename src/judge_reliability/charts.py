"""The three figures in reports/.

    python3 analysis.py --charts

matplotlib is imported here and nowhere else, so the study itself runs on a
bare Python install. Every figure is drawn from the same `run_study` result the
report prints, so a chart cannot disagree with a number in the text.
"""

import matplotlib
matplotlib.use("Agg")  # no display needed; savefig only

import matplotlib.pyplot as plt
from pathlib import Path

CLEAR = "#2f6f9f"
BORDER = "#b5532b"
INK = "#222222"


def make_all(results, outdir="reports"):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    written = [
        _reliability_by_difficulty(results, out / "reliability_by_difficulty.png"),
        _score_spread(results, out / "score_spread.png"),
        _human_vs_judge(results, out / "human_vs_judge.png"),
    ]
    return written


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK)
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)


def _reliability_by_difficulty(results, path):
    retest = results["test_retest"]
    groups = ["clear", "borderline"]
    labels = ["Clear items", "Borderline items"]
    icc = [retest[g]["icc"] or 0.0 for g in groups]
    unanimous = [retest[g]["pct_items_unanimous"] * 100 for g in groups]

    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=200)
    bars = ax.bar(labels, icc, color=[CLEAR, BORDER], width=0.55)
    for bar, value, share in zip(bars, icc, unanimous):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.03,
                f"ICC {value:.2f}\n{share:.0f}% unanimous",
                ha="center", va="bottom", fontsize=10, color=INK)

    ax.set_ylim(0, 1.15)
    ax.set_ylabel("ICC(2,1) — agreement with itself")
    ax.set_title("A judge is reliable on clear items and nearly random on hard ones",
                 fontsize=11, color=INK, pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _score_spread(results, path):
    scores = results["scores"]
    ambiguity = results["ambiguity"]
    ids = list(scores)
    ids.sort(key=lambda i: (ambiguity[i] != "clear", -_spread(scores[i]), i))

    fig, ax = plt.subplots(figsize=(8.0, 4.2), dpi=200)
    for x, item_id in enumerate(ids):
        runs = scores[item_id]
        colour = CLEAR if ambiguity[item_id] == "clear" else BORDER
        ax.plot([x, x], [min(runs), max(runs)], color=colour, linewidth=1.6, alpha=0.9)
        ax.scatter([x] * len(runs), runs, s=16, color=colour, alpha=0.75, zorder=3)
        ax.scatter([x], [results["human_scores"][item_id]], marker="_", s=140,
                   color=INK, linewidths=1.4, zorder=4)

    ax.set_xlim(-1, len(ids))
    ax.set_ylim(0.5, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_xlabel(f"{len(ids)} items, sorted by difficulty (clear → borderline)")
    ax.set_ylabel("Score across 8 runs")
    ax.set_title("Each item's 8 repeated judgments — black tick is the human score",
                 fontsize=11, color=INK, pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _human_vs_judge(results, path):
    human = results["human_scores"]
    single = results["single_call"]
    majority = results["majority_vote"]

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4), dpi=200, sharey=True)
    panels = [
        ("Single call", results["single_call_scores"], single["quadratic_kappa"]),
        ("Majority of 8 runs", results["majority_scores"], majority["quadratic_kappa"]),
    ]
    for ax, (title, judged, kappa) in zip(axes, panels):
        xs = [human[i] for i in judged]
        ys = [judged[i] for i in judged]
        ax.plot([0.5, 5.5], [0.5, 5.5], color="#999999", linewidth=1, linestyle="--")
        ax.scatter(xs, ys, s=34, color=CLEAR, alpha=0.75, edgecolor="white", linewidth=0.6)
        ax.set_xlim(0.5, 5.5)
        ax.set_ylim(0.5, 5.5)
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_xlabel("Human score")
        ax.set_title(f"{title}  ·  weighted κ {kappa:.2f}" if kappa is not None else title,
                     fontsize=10, color=INK)
        _style(ax)

    axes[0].set_ylabel("Judge score")
    fig.suptitle("Majority voting repairs the noise; what it leaves behind is bias",
                 fontsize=11, color=INK, y=1.02)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _spread(runs):
    return max(runs) - min(runs)
