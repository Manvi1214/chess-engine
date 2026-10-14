import chess

from tools.play import format_score, parse_player_move, render_board


def test_render_board_contains_starting_rank_and_pieces() -> None:
    board = chess.Board()
    rendered = render_board(board, unicode_pieces=True)
    assert "8 |" in rendered
    assert "1 |" in rendered
    assert "a   b   c   d   e   f   g   h" in rendered


def test_parse_player_move_uci_and_san() -> None:
    board = chess.Board()
    # Test UCI
    move_uci = parse_player_move(board, "e2e4")
    assert move_uci == chess.Move.from_uci("e2e4")

    # Test SAN
    move_san = parse_player_move(board, "e4")
    assert move_san == chess.Move.from_uci("e2e4")

    # Test illegal
    assert parse_player_move(board, "e5") is None
    assert parse_player_move(board, "invalid") is None


def test_format_score() -> None:
    assert format_score(0, chess.WHITE) == "0.00"
    assert format_score(150, chess.WHITE) == "+1.50"
    assert format_score(-50, chess.WHITE) == "-0.50"
    assert format_score(100_000, chess.WHITE) == "+M1"
