from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
from typing import TextIO

import chess.pgn


@dataclass(frozen=True)
class MatchQualityReport:
    total_games: int
    white_wins: int
    black_wins: int
    draws: int
    illegal_terminations: int
    illegal_by_color: dict[str, int]
    illegal_losses_by_player: dict[str, int]

    @property
    def illegal_rate_percent(self) -> float:
        if self.total_games == 0:
            return 0.0
        return 100.0 * self.illegal_terminations / self.total_games


def _iter_games(pgn_path: Path):
    with pgn_path.open("r", encoding="utf-8", errors="replace") as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            yield game


_ILLEGAL_RE = re.compile(r"\b(white|black)\s+makes\s+an\s+illegal\s+move", re.IGNORECASE)


def _extract_illegal_mover_color(game: chess.pgn.Game) -> str | None:
    termination = (game.headers.get("Termination", "") or "").strip()
    match = _ILLEGAL_RE.search(termination)
    if match is not None:
        return match.group(1).lower()

    node = game
    while node.variations:
        node = node.variations[0]

    comment = node.comment or ""
    match = _ILLEGAL_RE.search(comment)
    if match is not None:
        return match.group(1).lower()

    return None


def build_report(pgn_path: Path) -> MatchQualityReport:
    white_wins = 0
    black_wins = 0
    draws = 0

    illegal_terminations = 0
    illegal_by_color: Counter[str] = Counter()
    illegal_losses_by_player: Counter[str] = Counter()

    total_games = 0

    for game in _iter_games(pgn_path):
        total_games += 1

        result = (game.headers.get("Result", "*") or "*").strip()
        if result == "1-0":
            white_wins += 1
        elif result == "0-1":
            black_wins += 1
        elif result == "1/2-1/2":
            draws += 1

        mover_color = _extract_illegal_mover_color(game)
        if mover_color is None:
            continue

        illegal_terminations += 1

        if mover_color == "white":
            illegal_by_color["white"] += 1
            white_name = game.headers.get("White", "White")
            illegal_losses_by_player[white_name] += 1
        elif mover_color == "black":
            illegal_by_color["black"] += 1
            black_name = game.headers.get("Black", "Black")
            illegal_losses_by_player[black_name] += 1
        else:
            illegal_by_color["unknown"] += 1

    return MatchQualityReport(
        total_games=total_games,
        white_wins=white_wins,
        black_wins=black_wins,
        draws=draws,
        illegal_terminations=illegal_terminations,
        illegal_by_color=dict(illegal_by_color),
        illegal_losses_by_player=dict(illegal_losses_by_player),
    )


def _print_report(report: MatchQualityReport, stream: TextIO) -> None:
    stream.write("Match Quality Report\n")
    stream.write("====================\n")
    stream.write(f"Games: {report.total_games}\n")
    stream.write(
        f"Score (White/Black/Draw): {report.white_wins}/{report.black_wins}/{report.draws}\n"
    )
    stream.write(
        f"Illegal terminations: {report.illegal_terminations} ({report.illegal_rate_percent:.2f}%)\n"
    )

    white_illegal = report.illegal_by_color.get("white", 0)
    black_illegal = report.illegal_by_color.get("black", 0)
    unknown_illegal = report.illegal_by_color.get("unknown", 0)
    stream.write(
        f"Illegal by mover color: white={white_illegal}, black={black_illegal}, unknown={unknown_illegal}\n"
    )

    if report.illegal_losses_by_player:
        stream.write("Illegal losses by player:\n")
        for name, count in sorted(
            report.illegal_losses_by_player.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            stream.write(f"  {name}: {count}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a match quality report from a PGN (including illegal-move statistics)."
    )
    parser.add_argument("--pgn", required=True, help="Path to PGN file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pgn_path = Path(args.pgn)
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN not found: {pgn_path}")

    report = build_report(pgn_path)
    _print_report(report, stream=__import__("sys").stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
