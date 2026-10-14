import chess

from engine.tt import TTFlag, TranspositionTable


def test_tt_store_and_probe_roundtrip() -> None:
    board = chess.Board()
    key = TranspositionTable.key_for_board(board)
    tt = TranspositionTable(max_entries=4)

    tt.store(key=key, depth=3, score=42, flag=TTFlag.EXACT, best_move=chess.Move.from_uci("e2e4"))
    entry = tt.get(key)

    assert entry is not None
    assert entry.depth == 3
    assert entry.score == 42
    assert entry.flag is TTFlag.EXACT
    assert tt.get_best_move(key) == chess.Move.from_uci("e2e4")


def test_tt_depth_preferred_replacement_for_same_key() -> None:
    board = chess.Board()
    key = TranspositionTable.key_for_board(board)
    tt = TranspositionTable(max_entries=4)

    tt.store(key=key, depth=4, score=10, flag=TTFlag.EXACT, best_move=None)
    tt.store(key=key, depth=2, score=999, flag=TTFlag.EXACT, best_move=None)

    entry = tt.get(key)
    assert entry is not None
    assert entry.depth == 4
    assert entry.score == 10


def test_tt_bounded_size_is_enforced() -> None:
    tt = TranspositionTable(max_entries=2)

    b1 = chess.Board()
    b2 = chess.Board()
    b2.push(chess.Move.from_uci("e2e4"))
    b3 = chess.Board()
    b3.push(chess.Move.from_uci("d2d4"))

    tt.store(key=TranspositionTable.key_for_board(b1), depth=1, score=1, flag=TTFlag.EXACT, best_move=None)
    tt.store(key=TranspositionTable.key_for_board(b2), depth=1, score=2, flag=TTFlag.EXACT, best_move=None)
    tt.store(key=TranspositionTable.key_for_board(b3), depth=2, score=3, flag=TTFlag.EXACT, best_move=None)

    assert len(tt) <= 2


def test_tt_flag_names_match_search_spec() -> None:
    assert TTFlag.EXACT.name == "EXACT"
    assert TTFlag.LOWERBOUND.name == "LOWERBOUND"
    assert TTFlag.UPPERBOUND.name == "UPPERBOUND"
