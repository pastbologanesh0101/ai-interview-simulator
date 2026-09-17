"""Unit tests for interview_sim.scoring.

Uses canned answer strings (no stdin) to drive the pure scoring functions.
"""

import unittest

from interview_sim.scoring import (
    detect_filler_words,
    detect_star_structure,
    keyword_coverage,
    length_feedback,
    score_answer,
    word_count,
)

CONFLICT_QUESTION = {
    "id": "beh-001",
    "track": "general behavioral",
    "type": "behavioral",
    "question": "Tell me about a time you handled a conflict with a coworker.",
    "keywords": ["situation", "task", "action", "result", "communicat*", "resolv*", "conflict", "compromise"],
}

STRONG_ANSWER = (
    "In my previous role, I faced a difficult situation where a coworker and I "
    "disagreed about the task priorities on our project. My task was to deliver "
    "the feature on time, but he wanted to focus on something else first. So I "
    "decided to set up a meeting so we could communicate openly about our "
    "concerns. I listened to his perspective, and we found a compromise that "
    "addressed both timelines. As a result, we resolved the conflict, delivered "
    "the feature on time, and our working relationship improved afterward."
)

WEAK_ANSWER = "It was fine, we just talked about it I guess."

RAMBLING_ANSWER = (
    "Um, like, things happen sometimes, you know, it's basically just stuff "
    "that occurs and, like, whatever, I don't know really, it's just kind of "
    "things going on, um, that's it I guess, like."
)


class TestKeywordCoverage(unittest.TestCase):
    def test_strong_answer_scores_higher_than_weak_answer(self):
        strong = keyword_coverage(STRONG_ANSWER, CONFLICT_QUESTION["keywords"])
        weak = keyword_coverage(WEAK_ANSWER, CONFLICT_QUESTION["keywords"])
        self.assertGreater(strong.score, weak.score)
        self.assertGreaterEqual(strong.score, 0.7)
        self.assertLessEqual(weak.score, 0.2)

    def test_wildcard_keyword_matches_variants(self):
        result = keyword_coverage("We eventually resolved the issue together.", ["resolv*"])
        self.assertIn("resolv*", result.matched)
        self.assertEqual(result.score, 1.0)

    def test_missing_keywords_are_reported(self):
        result = keyword_coverage("Nothing relevant here.", ["situation", "result"])
        self.assertEqual(set(result.missing), {"situation", "result"})
        self.assertEqual(result.score, 0.0)


class TestStarStructureDetection(unittest.TestCase):
    def test_well_structured_answer_detected(self):
        result = detect_star_structure(STRONG_ANSWER)
        self.assertIn(result.label, ("well-structured", "partial"))
        self.assertGreaterEqual(result.components_present, 3)
        self.assertTrue(result.result)

    def test_rambling_answer_detected_as_unstructured(self):
        result = detect_star_structure(RAMBLING_ANSWER)
        self.assertEqual(result.label, "rambling")
        self.assertLessEqual(result.components_present, 1)


class TestFillerWordDetection(unittest.TestCase):
    def test_filler_words_are_counted(self):
        result = detect_filler_words(RAMBLING_ANSWER)
        self.assertGreater(result.filler_count, 5)
        self.assertIn("like", result.fillers_found)
        self.assertIn("um", result.fillers_found)
        self.assertGreater(result.filler_ratio, 0.1)

    def test_clean_answer_has_no_fillers(self):
        result = detect_filler_words(STRONG_ANSWER)
        self.assertEqual(result.filler_count, 0)
        self.assertEqual(result.fillers_found, {})


class TestLengthAndEmptyAnswers(unittest.TestCase):
    def test_empty_answer_handled_gracefully(self):
        result = score_answer(CONFLICT_QUESTION, "")
        self.assertEqual(result.overall_score, 0.0)
        self.assertEqual(result.word_count, 0)
        self.assertTrue(len(result.suggestions) > 0)

    def test_very_short_answer_gets_length_warning(self):
        feedback = length_feedback("Yes, we fixed it.")
        self.assertIn("short", feedback.lower())

    def test_word_count_ignores_punctuation(self):
        self.assertEqual(word_count("Hello, world! It's fine."), 4)


class TestScoreAnswerAggregate(unittest.TestCase):
    def test_strong_answer_scores_higher_overall_than_weak_answer(self):
        strong = score_answer(CONFLICT_QUESTION, STRONG_ANSWER)
        weak = score_answer(CONFLICT_QUESTION, WEAK_ANSWER)
        self.assertGreater(strong.overall_score, weak.overall_score)

    def test_overall_score_bounded_between_zero_and_one(self):
        result = score_answer(CONFLICT_QUESTION, RAMBLING_ANSWER)
        self.assertGreaterEqual(result.overall_score, 0.0)
        self.assertLessEqual(result.overall_score, 1.0)


if __name__ == "__main__":
    unittest.main()
