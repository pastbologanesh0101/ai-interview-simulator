"""Question bank loading and session/summary logic.

Everything here is pure and importable: no input()/print(). The CLI
REPL (interview_sim/cli.py) is a thin wrapper that drives a Session
using real stdin/stdout; tests drive the same Session with canned
answer strings.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .scoring import ScoredAnswer, score_answer

REQUIRED_QUESTION_FIELDS = ("id", "track", "type", "question", "keywords")

DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "questions.json"


@dataclass
class Question:
    id: str
    track: str
    type: str
    question: str
    keywords: list[str]

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        return cls(
            id=d["id"],
            track=d["track"],
            type=d["type"],
            question=d["question"],
            keywords=list(d["keywords"]),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "track": self.track,
            "type": self.type,
            "question": self.question,
            "keywords": list(self.keywords),
        }


class QuestionBankError(ValueError):
    """Raised when the question bank JSON is malformed or missing fields."""


def load_question_bank(path: Path | str = DEFAULT_QUESTIONS_PATH) -> list[Question]:
    """Load and validate the question bank from a JSON file.

    Raises QuestionBankError if the file isn't a JSON list of objects,
    or if any question is missing a required field or has empty keywords.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list) or not raw:
        raise QuestionBankError(f"Question bank at {path} must be a non-empty JSON list.")

    questions: list[Question] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise QuestionBankError(f"Question at index {i} is not an object.")
        missing = [field_name for field_name in REQUIRED_QUESTION_FIELDS if field_name not in item]
        if missing:
            raise QuestionBankError(f"Question at index {i} missing required field(s): {missing}.")
        if not item["keywords"]:
            raise QuestionBankError(f"Question '{item.get('id')}' has an empty keywords list.")
        if item["id"] in seen_ids:
            raise QuestionBankError(f"Duplicate question id: {item['id']}.")
        seen_ids.add(item["id"])
        questions.append(Question.from_dict(item))

    return questions


def list_tracks(questions: list[Question]) -> list[str]:
    """Return the distinct track names, in first-seen order."""
    seen: list[str] = []
    for q in questions:
        if q.track not in seen:
            seen.append(q.track)
    return seen


def questions_for_track(questions: list[Question], track: str) -> list[Question]:
    return [q for q in questions if q.track == track]


@dataclass
class SessionSummary:
    num_questions: int
    average_score: float
    weakest_question_id: str | None
    weakest_question_text: str | None
    weakest_score: float | None
    suggestions: list[str] = field(default_factory=list)


class Session:
    """Drives a sequence of questions and scores answers.

    Pure logic - no I/O. A caller (CLI or test) supplies answers via
    `record_answer` and reads results back; there is no input() here.
    """

    def __init__(self, questions: list[Question], track: str, num_questions: int = 5, seed: int | None = None):
        pool = questions_for_track(questions, track)
        if not pool:
            raise ValueError(f"No questions found for track '{track}'.")
        rng = random.Random(seed)
        chosen = pool[:] if num_questions >= len(pool) else rng.sample(pool, num_questions)
        self.track = track
        self.questions: list[Question] = chosen
        self.results: list[ScoredAnswer] = []

    def __len__(self) -> int:
        return len(self.questions)

    def get_question(self, index: int) -> Question:
        return self.questions[index]

    def record_answer(self, index: int, answer_text: str) -> ScoredAnswer:
        """Score `answer_text` against question `index` and store the result."""
        question = self.questions[index]
        result = score_answer(question.to_dict(), answer_text)
        # Keep results aligned with question order even if called out of order.
        while len(self.results) <= index:
            self.results.append(None)  # type: ignore[arg-type]
        self.results[index] = result
        return result

    def is_complete(self) -> bool:
        return len(self.results) == len(self.questions) and all(r is not None for r in self.results)

    def summary(self) -> SessionSummary:
        """Aggregate all recorded results into a SessionSummary.

        Ignores any not-yet-answered slots (None) so a summary can be
        requested mid-session too.
        """
        scored = [r for r in self.results if r is not None]
        if not scored:
            return SessionSummary(
                num_questions=len(self.questions),
                average_score=0.0,
                weakest_question_id=None,
                weakest_question_text=None,
                weakest_score=None,
                suggestions=["No answers were recorded."],
            )

        average = sum(r.overall_score for r in scored) / len(scored)
        weakest = min(scored, key=lambda r: r.overall_score)
        weakest_q = next((q for q in self.questions if q.id == weakest.question_id), None)

        suggestions: list[str] = []
        seen: set[str] = set()
        for r in scored:
            for s in r.suggestions:
                if s not in seen:
                    seen.add(s)
                    suggestions.append(s)

        return SessionSummary(
            num_questions=len(self.questions),
            average_score=average,
            weakest_question_id=weakest.question_id,
            weakest_question_text=weakest_q.question if weakest_q else None,
            weakest_score=weakest.overall_score,
            suggestions=suggestions[:8],
        )
