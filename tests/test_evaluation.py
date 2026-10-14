import chess

from engine.evaluate import (
    MAX_STAGE,
    calculate_game_stage,
    evaluate,
    evaluate_material,
    evaluate_mobility,
)


def test_start_position_is_equal_material() -> None:
    board = chess.Board()
    assert evaluate(board) == 0
    assert evaluate_material(board) == 0


def test_white_extra_queen_is_large_positive() -> None:
    # White has king+queen vs black king.
    board = chess.Board("7k/8/8/8/8/8/8/K6Q w - - 0 1")
    assert evaluate_material(board) == 900
    assert evaluate(board) >= 850


def test_black_extra_rook_is_negative() -> None:
    # White king vs black king+rook.
    board = chess.Board("7k/8/8/8/8/8/8/K6r w - - 0 1")
    assert evaluate_material(board) == -500
    assert evaluate(board) <= -450


def test_color_flipped_position_negates_score() -> None:
    white_up_pawn = chess.Board("7k/8/8/8/8/8/P7/K7 w - - 0 1")
    black_up_pawn = chess.Board("k7/p7/8/8/8/8/8/7K w - - 0 1")

    assert evaluate_material(white_up_pawn) == 100
    assert evaluate_material(black_up_pawn) == -100
    assert evaluate(white_up_pawn) > 0
    assert evaluate(black_up_pawn) < 0


def test_knight_center_scores_better_than_corner_for_white() -> None:
    center = chess.Board("7k/8/8/8/4N3/8/8/7K w - - 0 1")
    corner = chess.Board("7k/8/8/8/8/8/8/N6K w - - 0 1")

    assert evaluate_material(center) == evaluate_material(corner)
    assert evaluate(center) > evaluate(corner)


def test_knight_center_scores_worse_for_white_when_black_has_it() -> None:
    black_center = chess.Board("7k/8/8/4n3/8/8/8/7K w - - 0 1")
    black_corner = chess.Board("n6k/8/8/8/8/8/8/7K w - - 0 1")

    assert evaluate_material(black_center) == evaluate_material(black_corner)
    assert evaluate(black_center) < evaluate(black_corner)


def test_game_stage_is_high_in_opening_and_low_in_king_endgame() -> None:
    opening = chess.Board()
    king_only = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")

    assert calculate_game_stage(opening) == MAX_STAGE
    assert calculate_game_stage(king_only) == 0


def test_endgame_rewards_king_centralization() -> None:
    center_king = chess.Board("7k/8/8/8/4K3/8/8/8 w - - 0 1")
    corner_king = chess.Board("7k/8/8/8/8/8/8/4K3 w - - 0 1")

    assert evaluate_material(center_king) == evaluate_material(corner_king)
    assert evaluate(center_king) > evaluate(corner_king)


def test_mobility_prefers_more_legal_moves() -> None:
    # Same material: both sides have king+queen.
    # White queen on d4 has broader mobility than queen on a1.
    active = chess.Board("7k/8/8/8/3Q4/8/8/K7 w - - 0 1")
    passive = chess.Board("7k/8/8/8/8/8/8/KQ6 w - - 0 1")

    assert evaluate_material(active) == evaluate_material(passive)
    assert evaluate_mobility(active) > evaluate_mobility(passive)
