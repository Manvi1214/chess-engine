import chess

from engine.time_manager import allocate_time_seconds


def test_allocate_time_uses_fallback_when_clock_unknown() -> None:
    board = chess.Board()
    budget = allocate_time_seconds(board, wtime_ms=None, btime_ms=None, fallback_ms=1500)

    assert 1.4 <= budget <= 1.6


def test_allocate_time_respects_side_to_move_clock() -> None:
    board = chess.Board()
    white_budget = allocate_time_seconds(board, wtime_ms=10000, btime_ms=1000)

    board.turn = chess.BLACK
    black_budget = allocate_time_seconds(board, wtime_ms=10000, btime_ms=1000)

    assert white_budget > black_budget


def test_allocate_time_has_minimum_floor() -> None:
    board = chess.Board()
    budget = allocate_time_seconds(board, wtime_ms=10, btime_ms=10)

    assert budget >= 0.05
