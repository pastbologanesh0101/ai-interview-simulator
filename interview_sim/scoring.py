"""Pure heuristic scoring functions for interview answers.

No LLM calls, no network access - everything here is deterministic
string/regex analysis over the candidate's typed answer. Keeping these
functions free of any input()/print() side effects makes them easy to
unit test with canned strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-zA-Z']+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, punctuation stripped."""
    if not text:
        return []
    return _WORD_RE.findall(text.lower())


def word_count(text: str) -> int:
    return len(tokenize(text))


# ---------------------------------------------------------------------------
# Keyword coverage
# ---------------------------------------------------------------------------

def _keyword_pattern(keyword: str) -> re.Pattern:
    """Build a regex for one keyword.

    A trailing '*' means prefix match (simple stemming), e.g. "resolv*"
    matches "resolve", "resolved", "resolving". Keywords containing a
    space are matched as a literal phrase.
    """
    kw = keyword.strip().lower()
    if kw.endswith("*"):
        stem = re.escape(kw[:-1])
        return re.compile(r"\b" + stem + r"\w*", re.IGNORECASE)
    if " " in kw or "-" in kw or "/" in kw:
        return re.compile(re.escape(kw), re.IGNORECASE)
    return re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)


@dataclass
class KeywordCoverageResult:
    score: float
    matched: list[str]
    missing: list[str]


def keyword_coverage(answer: str, keywords: Iterable[str]) -> KeywordCoverageResult:
    """Score how many expected keywords/concepts appear in the answer.

    Returns a KeywordCoverageResult with the fractional score (0.0-1.0),
    and lists of matched / missing keywords (original spelling kept for
    display, matching is case-insensitive with '*' prefix support).
    """
    keywords = list(keywords)
    answer = answer or ""
    matched: list[str] = []
    missing: list[str] = []
    for kw in keywords:
        pattern = _keyword_pattern(kw)
        if pattern.search(answer):
            matched.append(kw)
        else:
            missing.append(kw)
    score = len(matched) / len(keywords) if keywords else 0.0
    return KeywordCoverageResult(score=score, matched=matched, missing=missing)


# ---------------------------------------------------------------------------
# STAR structure detection
# ---------------------------------------------------------------------------

_SITUATION_MARKERS = [
    "situation", "when i", "while i", "during", "at my", "at a previous",
    "context", "background", "faced", "there was a time", "one time",
    "in my previous", "my team", "we had", "needed to",
]
_TASK_MARKERS = [
    "task", "my goal", "my job was", "i was responsible", "responsible for",
    "needed to", "had to", "the challenge", "objective", "was asked to",
]
_ACTION_MARKERS = [
    "i decided", "i implemented", "so i", "then i", "i started", "i created",
    "i built", "i organized", "i led", "i reached out", "i talked to",
    "i took", "i worked", "i set up", "i proposed", "i analyzed",
    "i wrote", "i designed", "i communicated", "first, i", "next, i",
]
_RESULT_MARKERS = [
    "as a result", "resulted in", "ultimately", "in the end", "the outcome",
    "outcome was", "we were able to", "successfully", "improved", "increased",
    "decreased", "reduced", "learned", "i learned", "this led to", "finally",
    "in the end,", "consequently",
]

_PAST_TENSE_RE = re.compile(
    r"\b(\w+ed|was|were|did|had|went|led|built|made|took|felt|said|met|"
    r"got|gave|found|told|kept|left|thought|wrote|ran|began|came)\b",
    re.IGNORECASE,
)


def _count_markers(text_lower: str, markers: list[str]) -> int:
    return sum(1 for m in markers if m in text_lower)


@dataclass
class StarStructureResult:
    situation: bool
    task: bool
    action: bool
    result: bool
    past_tense_narrative: bool
    components_present: int
    label: str


def detect_star_structure(answer: str) -> StarStructureResult:
    """Heuristically detect Situation/Task/Action/Result structure.

    This is intentionally simple: it looks for lexical markers typical of
    each STAR component plus a past-tense narrative signal, rather than
    doing any real NLP/parsing.
    """
    answer = answer or ""
    text_lower = answer.lower()

    situation = _count_markers(text_lower, _SITUATION_MARKERS) > 0
    task = _count_markers(text_lower, _TASK_MARKERS) > 0
    action = _count_markers(text_lower, _ACTION_MARKERS) > 0
    result = _count_markers(text_lower, _RESULT_MARKERS) > 0

    past_tense_hits = len(_PAST_TENSE_RE.findall(answer))
    past_tense_narrative = past_tense_hits >= 3

    components_present = sum([situation, task, action, result])

    if components_present >= 3 and result:
        label = "well-structured"
    elif components_present >= 2:
        label = "partial"
    else:
        label = "rambling"

    return StarStructureResult(
        situation=situation,
        task=task,
        action=action,
        result=result,
        past_tense_narrative=past_tense_narrative,
        components_present=components_present,
        label=label,
    )


# ---------------------------------------------------------------------------
# Filler word / length feedback
# ---------------------------------------------------------------------------

FILLER_WORDS = [
    "um", "uh", "umm", "uhh", "like", "basically", "actually", "literally",
    "sort of", "kind of", "you know", "i mean", "so yeah", "just", "stuff",
    "things", "whatever", "honestly",
]


@dataclass
class FillerWordResult:
    filler_count: int
    filler_ratio: float
    fillers_found: dict[str, int]


def detect_filler_words(answer: str) -> FillerWordResult:
    """Count filler words/phrases and their ratio to total word count."""
    answer = answer or ""
    text_lower = answer.lower()
    total_words = max(word_count(answer), 1)

    fillers_found: dict[str, int] = {}
    total_fillers = 0
    for filler in FILLER_WORDS:
        if " " in filler:
            count = text_lower.count(filler)
        else:
            count = len(re.findall(r"\b" + re.escape(filler) + r"\b", text_lower))
        if count:
            fillers_found[filler] = count
            total_fillers += count

    ratio = total_fillers / total_words
    return FillerWordResult(filler_count=total_fillers, filler_ratio=ratio, fillers_found=fillers_found)


def length_feedback(answer: str, min_words: int = 20, max_words: int = 200) -> str:
    """Return a short human-readable comment on answer length."""
    n = word_count(answer)
    if n == 0:
        return "No answer given - try to always provide at least a brief response."
    if n < min_words:
        return f"Your answer was quite short ({n} words). Try to add more concrete detail."
    if n > max_words:
        return f"Your answer was long ({n} words). Consider being more concise and focused."
    return f"Your answer length ({n} words) is in a reasonable range."


# ---------------------------------------------------------------------------
# Aggregate scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoredAnswer:
    question_id: str
    answer: str
    keyword_result: KeywordCoverageResult
    star_result: StarStructureResult
    filler_result: FillerWordResult
    length_comment: str
    word_count: int
    overall_score: float
    suggestions: list[str] = field(default_factory=list)


def score_answer(question: dict, answer: str) -> ScoredAnswer:
    """Score a single answer against a question dict.

    `question` must have at least "id" and "keywords". Combines keyword
    coverage, STAR structure, and filler-word/length penalties into one
    overall_score in [0.0, 1.0], plus a list of actionable suggestions.
    """
    answer = answer or ""
    keywords = question.get("keywords", [])

    kw_result = keyword_coverage(answer, keywords)
    star_result = detect_star_structure(answer)
    filler_result = detect_filler_words(answer)
    length_comment = length_feedback(answer)
    wc = word_count(answer)

    # Weighted blend: keyword coverage matters most, STAR structure next,
    # then a filler-word penalty is subtracted.
    star_score = star_result.components_present / 4.0
    filler_penalty = min(filler_result.filler_ratio * 2.0, 0.3)

    overall = (0.6 * kw_result.score) + (0.4 * star_score) - filler_penalty
    overall = max(0.0, min(1.0, overall))

    if wc == 0:
        overall = 0.0

    suggestions: list[str] = []
    if kw_result.missing:
        shown = ", ".join(kw_result.missing[:5])
        suggestions.append(f"Try to mention concepts like: {shown}.")
    if star_result.label == "rambling":
        suggestions.append(
            "Structure your answer with a clear Situation, Task, Action, and Result."
        )
    elif star_result.label == "partial":
        missing_parts = [
            name for name, present in (
                ("situation", star_result.situation),
                ("task", star_result.task),
                ("action", star_result.action),
                ("result", star_result.result),
            ) if not present
        ]
        if missing_parts:
            suggestions.append("Add more about the: " + ", ".join(missing_parts) + ".")
    if filler_result.filler_count > 0:
        suggestions.append(
            f"Reduce filler words (found {filler_result.filler_count}: "
            f"{', '.join(sorted(filler_result.fillers_found))})."
        )
    if wc == 0:
        suggestions.append("Give an actual answer before moving on.")
    elif wc < 20:
        suggestions.append("Expand your answer with more concrete detail.")

    return ScoredAnswer(
        question_id=question.get("id", ""),
        answer=answer,
        keyword_result=kw_result,
        star_result=star_result,
        filler_result=filler_result,
        length_comment=length_comment,
        word_count=wc,
        overall_score=overall,
        suggestions=suggestions,
    )
