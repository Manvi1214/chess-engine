import chess

from engine.board_utils import (
    apply_uci_moves,
    board_to_pretty_string,
    game_state_summary,
    inspect_move,
    load_board_from_fen,
    piece_count,
)


def test_load_board_from_fen_and_piece_count() -> None:
    board = load_board_from_fen(chess.STARTING_FEN)
    assert piece_count(board) == 32


def test_push_pop_roundtrip_restores_original_position() -> None:
    board = chess.Board()
    start_fen = board.fen()

    apply_uci_moves(board, ["e2e4"])
    board.pop()

    assert board.fen() == start_fen


def test_checkmate_position_is_detected() -> None:
    # White king on h1 is checkmated by black queen on g2 protected by king on g3.
    fen = "7k/8/8/8/8/6k1/6q1/7K w - - 0 1"
    board = load_board_from_fen(fen)
    summary = game_state_summary(board)

    assert summary.is_checkmate is True
    assert summary.legal_move_count == 0


def test_castling_and_en_passant_appear_when_legal() -> None:
    castling_board = load_board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    castling_uci = {move.uci() for move in castling_board.legal_moves}
    assert "e1g1" in castling_uci
    assert "e1c1" in castling_uci

    en_passant_board = load_board_from_fen("8/8/8/3pP3/8/8/8/8 w - d6 0 1")
    en_passant_uci = {move.uci() for move in en_passant_board.legal_moves}
    assert "e5d6" in en_passant_uci


def test_inspect_move_flags_promotion_and_capture() -> None:
    board = load_board_from_fen("7k/P7/8/8/8/8/8/7K w - - 0 1")
    move = chess.Move.from_uci("a7a8q")

    details = inspect_move(board, move)

    assert details.is_promotion is True
    assert details.promotion_piece == "queen"
    assert details.from_square == "a7"
    assert details.to_square == "a8"


def test_board_to_pretty_string_includes_coordinates() -> None:
    board = chess.Board()
    rendered = board_to_pretty_string(board)

    assert "8" in rendered
    assert "a b c d e f g h" in rendered
