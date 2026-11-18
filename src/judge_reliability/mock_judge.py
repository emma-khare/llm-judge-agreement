"""A simulated judge, with the same surface as anthropic.Anthropic().

Why a simulation: the live API needs a paid key and network access, and the
study has to be runnable by anyone reading the repository. So this stand-in
imitates the three behaviours of an LLM judge that are documented in the
literature and visible in practice:

  1. It is **stable on clear items.** Given an answer that is obviously good or
     obviously wrong, repeated calls mostly return the same score.
  2. It is **unstable on borderline items.** Given an answer that is partly
     right, repeated calls scatter across neighbouring scores.
  3. It is **a bit lenient at the threshold**, for two different reasons, and
     separating them is the point of the study:
       - *threshold* leniency: with symmetric noise, an item scored 3 can drift
         up into "acceptable" but drifting down leaves it "unacceptable", so
         the label error is one-directional even with zero score bias;
       - *persistent* leniency: on a share of items the judge is systematically
         generous, answering a confident-sounding response with a higher score
         every time. This is a bias, not noise, and repeating the call will not
         move it — only a different rubric, prompt, or threshold will.

Nothing here is a claim about a real model. The distributions below are chosen
so the pipeline has something to measure, and are named constants so it is
obvious they are design choices rather than findings.

Determinism: one `random.Random(seed)` drives every call, so a study run is
reproducible exactly. Change the seed to get a different judge with the same
habits.
"""

import json
import random

from .dataset import ITEMS

# Probability that a clear item gets anything other than its human score, at
# the default temperature. Split evenly between +1 and -1.
CLEAR_NOISE = 0.22

# Share of items on which the judge is systematically generous (+1 every run,
# before noise). This is the part of the disagreement that repetition cannot
# remove, and the report measures it as such.
PERSISTENT_LENIENCY_RATE = 0.30

# Score offsets for a borderline item and their probabilities, at the default
# temperature. Symmetric by design: the mean error is zero, so any apparent
# leniency in the labels comes from the >= 4 threshold, not from bias.
BORDERLINE_OFFSETS = ((-2, 0.10), (-1, 0.22), (0, 0.30), (1, 0.26), (2, 0.12))

REFERENCE_TEMPERATURE = 0.7


class _Block:
    def __init__(self, text):
        self.text = text


class _Message:
    """Just enough of an Anthropic Message for `judge_once` to read."""

    def __init__(self, text):
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"


class MockAnthropic:
    """Drop-in stand-in for `anthropic.Anthropic()`.

    Only `.messages.create(...)` is implemented, because that is the only call
    the pipeline makes.
    """

    def __init__(self, seed=11):
        self.messages = _MockMessages(seed)


class _MockMessages:
    def __init__(self, seed):
        self._rng = random.Random(seed)
        # Longest first, so a response that contains another one cannot match wrongly.
        self._by_response = sorted(
            ((it["response"], it) for it in ITEMS), key=lambda pair: -len(pair[0])
        )
        # Fixed for the lifetime of this judge, drawn once before any grading, so
        # the same items are the generous ones in every run. That is what makes it
        # a bias rather than noise.
        self._leniency = {
            item["id"]: 1
            for item in ITEMS
            if self._rng.random() < PERSISTENT_LENIENCY_RATE
        }

    def create(self, *, model="mock", max_tokens=200, temperature=0.7, messages=None,
               system=None, **_ignored):
        if not messages:
            raise ValueError("MockAnthropic needs a messages list")
        prompt = messages[-1]["content"]
        item = self._lookup(prompt)
        score = self._sample(item, temperature)
        return _Message(json.dumps({"score": score, "reason": _reason(item, score)}))

    def _lookup(self, prompt):
        for response, item in self._by_response:
            if response in prompt:
                return item
        raise KeyError("MockAnthropic was asked to grade a response it does not know. "
                       "Add the item to dataset.py, or pass a real client.")

    def _sample(self, item, temperature):
        # The score this judge would settle on if asked forever: the human score,
        # plus its persistent generosity on the items it likes.
        base = item["human_score"] + self._leniency.get(item["id"], 0)
        heat = _heat(temperature)
        if heat == 0.0:
            return _clip(base)

        if item["ambiguity"] == "clear":
            if self._rng.random() > CLEAR_NOISE * heat:
                return _clip(base)
            return _clip(base + self._rng.choice((-1, 1)))

        offset = _weighted_choice(self._rng, BORDERLINE_OFFSETS, heat)
        return _clip(base + offset)


def _heat(temperature):
    """Map temperature to 0..1 of the designed noise. 0 -> deterministic."""
    if temperature <= 0:
        return 0.0
    return min(1.0, temperature / REFERENCE_TEMPERATURE)


def _weighted_choice(rng, table, heat):
    """Pick an offset, blending toward 0 as heat falls below 1.

    At heat = 1 the designed distribution is used as-is. Lower temperatures
    move probability mass to 0, which is what a cooler model does.
    """
    if rng.random() > heat:
        return 0
    cumulative = []
    total = 0.0
    for offset, weight in table:
        total += weight
        cumulative.append((offset, total))
    draw = rng.random() * total
    for offset, edge in cumulative:
        if draw <= edge:
            return offset
    return 0


def _clip(score):
    return max(1, min(5, score))


def _reason(item, score):
    """A short rationale, in the voice a judge would use."""
    gap = score - item["human_score"]
    if item["ambiguity"] == "clear":
        if gap == 0:
            return "Clear and correct; nothing important missing."
        return "Somewhat off: the answer misses or blurs the key point."
    if gap == 0:
        return "Partly right, but the caveat that decides it is missing."
    if gap > 0:
        return "Reads plausibly, so I gave it the benefit of the doubt."
    return "Vague enough that I scored it down."
