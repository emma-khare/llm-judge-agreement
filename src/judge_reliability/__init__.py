"""Measuring whether an LLM judge can be trusted.

Modules:
    dataset       -- the items, the rubric, and scores turning into labels
    judge         -- one call to the judge (real Anthropic client or a stand-in)
    mock_judge    -- the simulated judge used for the offline demonstration
    reliability   -- ICC, kappa, bootstrap intervals, majority vote, run_study
    charts        -- the three figures (matplotlib, optional)
"""

from .dataset import ITEMS, RUBRIC, by_difficulty, label_from_score
from .judge import Judgement, JudgeError, judge_once
from .reliability import majority_scores, run_study

__all__ = [
    "ITEMS", "RUBRIC", "by_difficulty", "label_from_score",
    "Judgement", "JudgeError", "judge_once",
    "majority_scores", "run_study",
]
