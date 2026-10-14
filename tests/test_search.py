import chess
from engine.evaluate import evaluate

from engine.search import (
    _ordered_legal_moves,
    compare_alpha_beta_with_without_tt,
    compare_search_nodes,
    find_best_move,
    find_best_move_alpha_beta,
    find_best_move_alpha_beta_with_stats,
    find_best_move_with_stats,
    iterative_deepening_search,
    negamax,
    negamax_alpha_beta,
    quiescence,
    search_with_time_controls,
)
from engine.tt import TranspositionTable


def test_mate_in_one_is_found() -> None:
    board = chess.Board("6k1/8/6KQ/8/8/8/8/8 w - - 0 1")
    best_move = find_best_move(board, depth=1)

    assert best_move is not None
    assert best_move.uci() == "h6g7"


def test_free_piece_capture_is_preferred() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    best_move = find_best_move(board, depth=1)

    assert best_move is not None
    assert best_move.uci() == "a1a8"


def test_negamax_depth_zero_returns_int_score() -> None:
    board = chess.Board()
    score = negamax(board, depth=0)

    assert isinstance(score, int)


def test_alpha_beta_matches_plain_negamax_best_move_same_depth() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")

    best_plain = find_best_move(board, depth=2)
    best_ab = find_best_move_alpha_beta(board, depth=2)

    assert best_plain is not None
    assert best_ab is not None
    assert best_ab == best_plain


def test_ordered_legal_moves_places_captures_first() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    ordered = _ordered_legal_moves(board)

    assert ordered
    assert ordered[0].uci() == "a1a8"


def test_stats_wrappers_match_best_move_functions() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")

    plain_best = find_best_move(board, depth=2)
    plain_stats = find_best_move_with_stats(board, depth=2)
    ab_best = find_best_move_alpha_beta(board, depth=2)
    ab_stats = find_best_move_alpha_beta_with_stats(board, depth=2)

    assert plain_best == plain_stats.best_move
    assert ab_best == ab_stats.best_move
    assert plain_stats.nodes > 0
    assert ab_stats.nodes > 0


def test_alpha_beta_visits_no_more_nodes_than_plain_negamax() -> None:
    board = chess.Board()
    plain, alpha_beta = compare_search_nodes(board, depth=3)

    assert plain.best_move is not None
    assert alpha_beta.best_move is not None
    assert alpha_beta.nodes <= plain.nodes


def test_quiescence_improves_leaf_score_when_capture_is_available() -> None:
    # White is materially down, but can capture a free queen on a8.
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    stand_pat = evaluate(board)
    q_score = quiescence(board, alpha=-10**9, beta=10**9)

    assert stand_pat < 0
    assert q_score > stand_pat


def test_alpha_beta_depth_zero_uses_quiescence() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    ab_leaf_score = negamax_alpha_beta(board, depth=0, alpha=-10**9, beta=10**9)

    # Depth-0 alpha-beta should still see tactical capture sequence via quiescence.
    assert ab_leaf_score > 0


def test_iterative_deepening_matches_fixed_depth_when_budget_is_large() -> None:
    board = chess.Board("q3k3/8/8/8/8/8/8/R3K3 w - - 0 1")

    fixed = find_best_move_alpha_beta(board, depth=2)
    result = iterative_deepening_search(board, max_depth=2, time_budget_sec=2.0)

    assert fixed is not None
    assert result.best_move == fixed
    assert result.depth_reached == 2
    assert result.nodes > 0


def test_iterative_deepening_handles_tight_time_budget() -> None:
    board = chess.Board()
    result = iterative_deepening_search(board, max_depth=5, time_budget_sec=0.000001)

    assert result.best_move is not None
    assert result.depth_reached <= 5
    assert result.time_spent_sec >= 0


def test_search_with_time_controls_uses_movetime() -> None:
    board = chess.Board()
    result = search_with_time_controls(board, max_depth=3, movetime_ms=50)

    assert result.best_move is not None
    assert result.depth_reached >= 1


def test_search_with_time_controls_uses_side_clock_when_no_movetime() -> None:
    board = chess.Board()
    result = search_with_time_controls(
        board,
        max_depth=3,
        wtime_ms=2000,
        btime_ms=2000,
        winc_ms=100,
        binc_ms=100,
    )

    assert result.best_move is not None
    assert result.depth_reached >= 1


def test_search_with_time_controls_does_not_mutate_input_board() -> None:
    board = chess.Board()
    original_fen = board.fen()

    _ = search_with_time_controls(board, max_depth=6, movetime_ms=20)

    assert board.fen() == original_fen


def test_tt_produces_hits_in_repeated_searches() -> None:
    board = chess.Board()
    tt = TranspositionTable(max_entries=100_000)

    _ = find_best_move_alpha_beta_with_stats(board, depth=3, tt=tt)
    second = find_best_move_alpha_beta_with_stats(board, depth=3, tt=tt)

    assert second.tt_hits > 0


def test_alpha_beta_with_tt_visits_fewer_nodes_than_without_tt() -> None:
    board = chess.Board()
    tt = TranspositionTable(max_entries=100_000)

    without_tt, with_tt = compare_alpha_beta_with_without_tt(board, depth=4, tt=tt)

    assert without_tt.best_move is not None
    assert with_tt.best_move is not None
    assert without_tt.score == with_tt.score
    assert with_tt.nodes < without_tt.nodes


def test_tt_search_is_stable_over_many_repeated_calls() -> None:
    board = chess.Board()
    tt = TranspositionTable(max_entries=200_000)

    for _ in range(200):
        stats = find_best_move_alpha_beta_with_stats(board, depth=3, tt=tt)
        assert stats.best_move is not None
        assert stats.nodes > 0

    assert len(tt) <= tt.max_entries
