import time

import chess
import engine.uci as uci_module

from engine.uci import UCIEngine


def _bestmove_from_output(lines: list[str]) -> str | None:
    for line in reversed(lines):
        if line.startswith("bestmove "):
            return line.split()[1]
    return None


def test_uci_handshake_and_ready() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("uci")
    engine.handle_command("isready")

    assert "uciok" in out
    assert "readyok" in out
    assert any(line.startswith("id name") for line in out)


def test_setoption_hash_reconfigures_tt() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    old_entries = engine.tt.max_entries
    engine.handle_command("setoption name Hash value 32")

    assert engine.hash_mb == 32
    assert engine.tt.max_entries != old_entries


def test_position_startpos_and_moves_are_applied() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("position startpos moves e2e4 e7e5")

    assert engine.board.piece_at(chess.E4) is not None
    assert engine.board.piece_at(chess.E5) is not None
    assert engine.board.turn == chess.WHITE


def test_position_fen_and_moves_are_applied() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    fen = "7k/8/8/8/8/8/8/K6Q w - - 0 1"
    engine.handle_command(f"position fen {fen} moves h1h8")

    assert engine.board.piece_at(chess.H8) is not None


def test_go_movetime_returns_legal_bestmove() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("position startpos")
    start_board = engine.board.copy(stack=False)
    engine.handle_command("go movetime 50")
    assert engine.wait_for_search(timeout=3.0)

    bestmove_text = _bestmove_from_output(out)
    assert bestmove_text is not None
    move = chess.Move.from_uci(bestmove_text)
    assert move in start_board.legal_moves


def test_go_depth_returns_legal_bestmove() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("position startpos")
    start_board = engine.board.copy(stack=False)
    engine.handle_command("go depth 2")
    assert engine.wait_for_search(timeout=3.0)

    assert any(line.startswith("info depth 2") for line in out)
    bestmove_text = _bestmove_from_output(out)
    assert bestmove_text is not None
    move = chess.Move.from_uci(bestmove_text)
    assert move in start_board.legal_moves


def test_go_infinite_can_be_stopped_cleanly() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("position startpos")
    engine.handle_command("go infinite")
    time.sleep(0.05)
    engine.handle_command("stop")

    assert engine.wait_for_search(timeout=3.0)
    assert _bestmove_from_output(out) is not None


def test_go_infinite_emits_periodic_info_lines() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("position startpos")
    engine.handle_command("go infinite")
    time.sleep(0.35)
    engine.handle_command("stop")
    assert engine.wait_for_search(timeout=3.0)

    info_lines = [line for line in out if line.startswith("info depth ")]
    assert len(info_lines) >= 1
    assert _bestmove_from_output(out) is not None


def test_setoption_logfile_writes_debug_log(tmp_path) -> None:
    out: list[str] = []
    log_path = tmp_path / "uci.log"
    engine = UCIEngine(output_func=out.append)

    engine.handle_command(f"setoption name LogFile value {log_path}")
    engine.handle_command("isready")
    engine.handle_command("quit")

    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "<= isready" in text
    assert "engine quitting" in text


def test_quit_stops_engine() -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    engine.handle_command("quit")
    assert engine.running is False


def test_canceled_search_does_not_emit_stale_bestmove(monkeypatch) -> None:
    out: list[str] = []
    engine = UCIEngine(output_func=out.append)

    # Build a concrete fake result without importing internal search module symbols.
    class _FakeResult:
        def __init__(self, board: chess.Board) -> None:
            self.best_move = next(iter(board.legal_moves), None)
            self.score = 0
            self.depth_reached = 1
            self.nodes = 1
            self.time_spent_sec = 0.05

    def _fake_search_with_time_controls(board: chess.Board, **_kwargs):
        time.sleep(0.05)
        return _FakeResult(board)

    monkeypatch.setattr(uci_module, "search_with_time_controls", _fake_search_with_time_controls)

    engine.handle_command("position startpos")
    engine.handle_command("go movetime 100")
    engine.handle_command("position startpos moves e2e4")
    engine.handle_command("go movetime 100")

    assert engine.wait_for_search(timeout=3.0)
    time.sleep(0.08)

    bestmove_lines = [line for line in out if line.startswith("bestmove ")]
    assert len(bestmove_lines) == 1
