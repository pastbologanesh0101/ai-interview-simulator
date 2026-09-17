"""Unit tests for interview_sim.session: question bank loading and Session.

The Session class is driven with canned answer strings, never real
stdin, so these tests exercise exactly what the CLI would do without
any input() calls.
"""

import json
import tempfile
import unittest
from pathlib import Path

from interview_sim.session import (
    DEFAULT_QUESTIONS_PATH,
    Question,
    QuestionBankError,
    Session,
    list_tracks,
    load_question_bank,
    questions_for_track,
)

SAMPLE_QUESTIONS = [
    {
        "id": "q1",
        "track": "test-track",
        "type": "behavioral",
        "question": "Describe a challenge you overcame.",
        "keywords": ["challenge", "action", "result"],
    },
    {
        "id": "q2",
        "track": "test-track",
        "type": "behavioral",
        "question": "Describe a time you led a team.",
        "keywords": ["lead*", "team", "result"],
    },
]


class TestQuestionBankLoading(unittest.TestCase):
    def test_default_bank_loads_and_has_no_missing_fields(self):
        questions = load_question_bank(DEFAULT_QUESTIONS_PATH)
        self.assertGreaterEqual(len(questions), 40)
        for q in questions:
            self.assertTrue(q.id)
            self.assertTrue(q.track)
            self.assertTrue(q.type)
            self.assertTrue(q.question)
            self.assertTrue(q.keywords)

    def test_default_bank_covers_multiple_tracks(self):
        questions = load_question_bank(DEFAULT_QUESTIONS_PATH)
        tracks = list_tracks(questions)
        self.assertIn("general behavioral", tracks)
        self.assertIn("software engineering", tracks)

    def test_missing_required_field_raises_error(self):
        bad = [{"id": "x", "track": "t", "type": "behavioral", "question": "Q?"}]  # no keywords
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(bad, f)
            path = f.name
        try:
            with self.assertRaises(QuestionBankError):
                load_question_bank(path)
        finally:
            Path(path).unlink()

    def test_empty_keywords_raises_error(self):
        bad = [{"id": "x", "track": "t", "type": "behavioral", "question": "Q?", "keywords": []}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(bad, f)
            path = f.name
        try:
            with self.assertRaises(QuestionBankError):
                load_question_bank(path)
        finally:
            Path(path).unlink()


class TestSessionAndSummary(unittest.TestCase):
    def setUp(self):
        self.questions = [Question.from_dict(d) for d in SAMPLE_QUESTIONS]

    def test_session_selects_correct_track_and_count(self):
        session = Session(self.questions, track="test-track", num_questions=2, seed=1)
        self.assertEqual(len(session), 2)
        self.assertTrue(all(q.track == "test-track" for q in session.questions))

    def test_session_raises_for_unknown_track(self):
        with self.assertRaises(ValueError):
            Session(self.questions, track="nonexistent-track", num_questions=1)

    def test_summary_averages_recorded_scores(self):
        session = Session(self.questions, track="test-track", num_questions=2, seed=1)
        session.record_answer(0, "I faced a challenge and took action, and the result was great.")
        session.record_answer(1, "")  # empty answer scores 0.0
        summary = session.summary()
        scores = [r.overall_score for r in session.results if r is not None]
        expected_avg = sum(scores) / len(scores)
        self.assertAlmostEqual(summary.average_score, expected_avg)
        self.assertEqual(summary.num_questions, 2)

    def test_summary_identifies_weakest_question(self):
        session = Session(self.questions, track="test-track", num_questions=2, seed=1)
        strong = "I led the team through the challenge with clear action and a strong result."
        session.record_answer(0, strong)
        session.record_answer(1, "")
        summary = session.summary()
        weak_result = min(session.results, key=lambda r: r.overall_score)
        self.assertEqual(summary.weakest_question_id, weak_result.question_id)
        self.assertEqual(summary.weakest_score, weak_result.overall_score)

    def test_summary_with_no_answers_is_graceful(self):
        session = Session(self.questions, track="test-track", num_questions=2, seed=1)
        summary = session.summary()
        self.assertEqual(summary.average_score, 0.0)
        self.assertIsNone(summary.weakest_question_id)

    def test_questions_for_track_filters_correctly(self):
        filtered = questions_for_track(self.questions, "test-track")
        self.assertEqual(len(filtered), 2)
        self.assertEqual(questions_for_track(self.questions, "nope"), [])


if __name__ == "__main__":
    unittest.main()
