from pathlib import Path

from tools.match_report import build_report


def test_match_report_counts_illegal_terminations(tmp_path: Path) -> None:
    pgn_text = """
[Event "?"]
[White "MyEngine"]
[Black "Stockfish"]
[Result "0-1"]
[Termination "White makes an illegal move: h8g8"]

1. e4 e5 0-1

[Event "?"]
[White "Stockfish"]
[Black "MyEngine"]
[Result "1-0"]
[Termination "Black makes an illegal move: g5h7"]

1. d4 d5 1-0

[Event "?"]
[White "MyEngine"]
[Black "Stockfish"]
[Result "1/2-1/2"]
[Termination "Draw by 3-fold repetition"]

1. c4 c5 1/2-1/2
""".strip()

    pgn_path = tmp_path / "sample.pgn"
    pgn_path.write_text(pgn_text, encoding="utf-8")

    report = build_report(pgn_path)

    assert report.total_games == 3
    assert report.white_wins == 1
    assert report.black_wins == 1
    assert report.draws == 1

    assert report.illegal_terminations == 2
    assert report.illegal_by_color.get("white") == 1
    assert report.illegal_by_color.get("black") == 1

    assert report.illegal_losses_by_player.get("MyEngine") == 2
    assert report.illegal_rate_percent > 60.0
