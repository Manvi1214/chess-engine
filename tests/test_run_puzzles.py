from tools.run_puzzles import DEFAULT_PUZZLES, PuzzleCase, run_puzzle_suite, solve_puzzle


def test_run_puzzle_suite_executes_and_reports_counts() -> None:
    result, details = run_puzzle_suite(depth=2)

    assert result.total == len(DEFAULT_PUZZLES)
    assert len(details) == result.total
    assert 0 <= result.solved <= result.total


def test_known_mate_in_one_is_solved() -> None:
    case = PuzzleCase(
        name="mate_in_one_white",
        fen="6k1/8/6KQ/8/8/8/8/8 w - - 0 1",
        best_move_uci="h6g7",
    )

    move_uci = solve_puzzle(case, depth=1)
    assert move_uci == "h6g7"


def test_run_puzzle_suite_respects_max_cases() -> None:
    result, details = run_puzzle_suite(depth=2, max_cases=2)

    assert result.total == 2
    assert len(details) == 2
