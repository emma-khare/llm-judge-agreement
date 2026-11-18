"""One judgment: send (question, response, rubric) to the judge, get back a score.

This module is the seam between the study and a real model. It knows how to
talk to the Anthropic Messages API and how to parse a score out of the reply;
it knows nothing about reliability statistics. `MockAnthropic` in
`mock_judge.py` implements the same `.messages.create(...)` surface, so

    judge_once(..., client=anthropic.Anthropic())
    judge_once(..., client=MockAnthropic())

are interchangeable and the rest of the pipeline cannot tell them apart. That
one line is the difference between a method demonstration and a live study.
"""

import json
import os
import re
from dataclasses import dataclass

DEFAULT_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-5")

PROMPT = """You are grading a short answer against a rubric.

RUBRIC
{rubric}

QUESTION
{question}

RESPONSE TO GRADE
{response}

Reply with JSON only, no prose and no code fences:
{{"score": <integer 1-5>, "reason": "<one sentence>"}}"""


class JudgeError(RuntimeError):
    """The judge's reply could not be read as a score."""


@dataclass(frozen=True)
class Judgement:
    score: int
    reason: str


def build_prompt(question, response, rubric):
    return PROMPT.format(rubric=rubric, question=question, response=response)


def parse_reply(text):
    """Pull {"score": n, "reason": ...} out of a model reply.

    Models wrap JSON in prose or fences often enough that a bare json.loads is
    not enough. This tries the whole string, then the first {...} block, then a
    last-resort "score: n" match, and rejects anything outside 1-5 rather than
    silently clipping it.
    """
    candidates = [text]
    block = re.search(r"\{.*\}", text, re.DOTALL)
    if block:
        candidates.append(block.group(0))

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(payload, dict) and "score" in payload:
            return _as_judgement(payload)

    loose = re.search(r'"?score"?\s*[:=]\s*([1-5])\b', text)
    if loose:
        return Judgement(score=int(loose.group(1)), reason=text.strip()[:200])

    raise JudgeError(f"no score in reply: {text[:200]!r}")


def _as_judgement(payload):
    try:
        score = int(payload["score"])
    except (TypeError, ValueError):
        raise JudgeError(f"score is not an integer: {payload.get('score')!r}")
    if not 1 <= score <= 5:
        raise JudgeError(f"score {score} outside 1-5")
    return Judgement(score=score, reason=str(payload.get("reason", "")).strip())


def judge_once(question, response, rubric, client, temperature=0.7, model=None):
    """Ask the judge for one score. `client` is anthropic.Anthropic() or a stand-in."""
    reply = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=200,
        temperature=temperature,
        messages=[{"role": "user", "content": build_prompt(question, response, rubric)}],
    )
    return parse_reply(reply.content[0].text)
