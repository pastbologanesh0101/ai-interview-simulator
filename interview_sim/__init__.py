"""AI Interview Simulator - core package.

Pure-Python mock interview simulator: no network calls, no LLM APIs.
The scoring/session logic lives in this package and is fully importable
so it can be exercised by unit tests without touching stdin/stdout.
"""

from .scoring import (
    keyword_coverage,
    detect_star_structure,
    detect_filler_words,
    length_feedback,
    score_answer,
)
from .session import Question, SessionSummary, Session, load_question_bank

__all__ = [
    "keyword_coverage",
    "detect_star_structure",
    "detect_filler_words",
    "length_feedback",
    "score_answer",
    "Question",
    "SessionSummary",
    "Session",
    "load_question_bank",
]
