import chess

from engine.main import create_starting_board, parse_uci_move


def test_create_starting_board_has_20_legal_moves() -> None:
    board = create_starting_board()
    assert board.fen().startswith("rnbqkbnr/pppppppp/")
    assert board.legal_moves.count() == 20


def test_parse_uci_move_accepts_legal_and_rejects_illegal() -> None:
    board = chess.Board()
    assert parse_uci_move(board, "e2e4") == chess.Move.from_uci("e2e4")
    assert parse_uci_move(board, "e2e5") is None


def test_parse_uci_move_rejects_invalid_text_inputs() -> None:
    board = chess.Board()
    assert parse_uci_move(board, "") is None
    assert parse_uci_move(board, "hello") is None
    assert parse_uci_move(board, "e9e4") is None


def test_push_pop_restores_exact_state() -> None:
    board = chess.Board()
    initial_fen = board.fen()
    initial_stack_len = len(board.move_stack)

    move = parse_uci_move(board, "e2e4")
    assert move is not None

    board.push(move)
    board.pop()

    assert board.fen() == initial_fen
    assert len(board.move_stack) == initial_stack_len
