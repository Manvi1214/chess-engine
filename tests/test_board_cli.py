import chess

from tools.board_cli import build_board, render_report


def test_build_board_from_startpos_and_moves() -> None:
    board = build_board(startpos=True, fen=None, preset=None, moves=["e2e4", "e7e5"])

    assert board.piece_at(chess.E4) is not None
    assert board.piece_at(chess.E5) is not None
    assert board.turn == chess.WHITE


def test_build_board_rejects_startpos_and_fen_together() -> None:
    try:
        build_board(startpos=True, fen=chess.STARTING_FEN, preset=None, moves=[])
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "only one of --startpos, --fen, or --preset" in str(exc)


def test_build_board_from_named_preset() -> None:
    board = build_board(startpos=False, fen=None, preset="castle_ready", moves=[])
    legal = {move.uci() for move in board.legal_moves}
    assert "e1g1" in legal
    assert "e1c1" in legal


def test_render_report_includes_core_fields() -> None:
    board = chess.Board()
    output = render_report(board, show_legal=False, max_legal=20)

    assert "FEN:" in output
    assert "Legal moves: 20" in output
    assert "Turn: white" in output


def test_render_report_shows_legal_move_list_when_requested() -> None:
    board = chess.Board()
    output = render_report(board, show_legal=True, max_legal=3)

    assert "Sample legal moves:" in output
    assert output.count("- ") >= 3
