"""Interactive REPL for the AI Interview Simulator.

This module contains all the input()/print() side effects. The actual
scoring/session logic lives in session.py and scoring.py and is fully
importable/testable without touching stdin.
"""

from __future__ import annotations

from .session import Session, list_tracks, load_question_bank

BAR_WIDTH = 30


def _bar(score: float) -> str:
    filled = round(score * BAR_WIDTH)
    return "[" + ("#" * filled) + ("-" * (BAR_WIDTH - filled)) + f"] {score * 100:.0f}%"


def _print_feedback(question_number: int, question_text: str, result) -> None:
    print(f"\n--- Feedback for Q{question_number} ---")
    print(f"Q: {question_text}")
    print(f"Overall score: {_bar(result.overall_score)}")
    print(
        f"Keyword coverage: {result.keyword_result.score * 100:.0f}% "
        f"(matched {len(result.keyword_result.matched)}/"
        f"{len(result.keyword_result.matched) + len(result.keyword_result.missing)})"
    )
    print(f"STAR structure: {result.star_result.label} "
          f"({result.star_result.components_present}/4 components detected)")
    print(f"Length: {result.length_comment}")
    if result.filler_result.filler_count:
        print(f"Filler words detected: {result.filler_result.filler_count} "
              f"({', '.join(sorted(result.filler_result.fillers_found))})")
    if result.suggestions:
        print("Suggestions:")
        for s in result.suggestions:
            print(f"  - {s}")


def choose_track(tracks: list[str]) -> str:
    print("\nAvailable tracks:")
    for i, t in enumerate(tracks, start=1):
        print(f"  {i}. {t}")
    while True:
        choice = input("Pick a track (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(tracks):
            return tracks[int(choice) - 1]
        print("Invalid choice, try again.")


def choose_num_questions(max_available: int, default: int = 5) -> int:
    raw = input(f"How many questions? (1-{max_available}, default {default}): ").strip()
    if not raw:
        return min(default, max_available)
    if raw.isdigit() and 1 <= int(raw) <= max_available:
        return int(raw)
    print(f"Using default of {min(default, max_available)}.")
    return min(default, max_available)


def run() -> None:
    print("=" * 50)
    print("  AI Interview Simulator (mock, offline, no LLM)")
    print("=" * 50)

    questions = load_question_bank()
    tracks = list_tracks(questions)
    track = choose_track(tracks)

    from .session import questions_for_track
    available = len(questions_for_track(questions, track))
    num_questions = choose_num_questions(available)

    session = Session(questions, track=track, num_questions=num_questions)

    print(f"\nStarting a {len(session)}-question session on '{track}'.\n")

    for i in range(len(session)):
        q = session.get_question(i)
        print(f"\nQ{i + 1}/{len(session)}: {q.question}")
        answer = input("Your answer> ")
        result = session.record_answer(i, answer)
        _print_feedback(i + 1, q.question, result)

    summary = session.summary()
    print("\n" + "=" * 50)
    print("  Session Summary")
    print("=" * 50)
    print(f"Questions answered: {summary.num_questions}")
    print(f"Average score: {_bar(summary.average_score)}")
    if summary.weakest_question_text:
        print(f"Weakest question: \"{summary.weakest_question_text}\" "
              f"(score {summary.weakest_score * 100:.0f}%)")
    if summary.suggestions:
        print("\nTop suggestions for improvement:")
        for s in summary.suggestions:
            print(f"  - {s}")
    print()


def main() -> None:
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nSession interrupted. Goodbye!")


if __name__ == "__main__":
    main()
