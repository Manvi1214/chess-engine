from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path

import chess

try:
    from engine.search import find_best_move_alpha_beta
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.search import find_best_move_alpha_beta


@dataclass(frozen=True)
class PuzzleCase:
    name: str
    fen: str
    best_move_uci: str


@dataclass(frozen=True)
class PuzzleRunResult:
    total: int
    solved: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return 100.0 * self.solved / self.total


DEFAULT_PUZZLES: list[PuzzleCase] = [
    PuzzleCase(
        name="mate_in_one_white",
        fen="6k1/8/6KQ/8/8/8/8/8 w - - 0 1",
        best_move_uci="h6g7",
    ),
    PuzzleCase(
        name="free_queen_white",
        fen="q3k3/8/8/8/8/8/8/R3K3 w - - 0 1",
        best_move_uci="a1a8",
    ),
    PuzzleCase(
        name="free_queen_black",
        fen="r3k3/8/8/8/8/8/8/Q3K3 b - - 0 1",
        best_move_uci="a8a1",
    ),
]


def solve_puzzle(case: PuzzleCase, depth: int) -> str | None:
    board = chess.Board(case.fen)
    best_move = find_best_move_alpha_beta(board, depth=depth)
    if best_move is None:
        return None
    return best_move.uci()


def run_puzzle_suite(
    depth: int,
    max_cases: int | None = None,
    puzzles: list[PuzzleCase] | None = None,
) -> tuple[PuzzleRunResult, list[tuple[PuzzleCase, str | None]]]:
    if depth < 1:
        raise ValueError("depth must be >= 1")

    cases = puzzles if puzzles is not None else DEFAULT_PUZZLES
    if max_cases is not None:
        cases = cases[: max(0, max_cases)]

    solved = 0
    details: list[tuple[PuzzleCase, str | None]] = []

    for case in cases:
        move_uci = solve_puzzle(case, depth=depth)
        details.append((case, move_uci))
        if move_uci == case.best_move_uci:
            solved += 1

    return PuzzleRunResult(total=len(cases), solved=solved), details


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small tactical puzzle suite.")
    parser.add_argument("--depth", type=int, default=2, help="Search depth for puzzle solving.")
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Optional limit for number of puzzles to run.",
    )
    parser.add_argument(
        "--show-failures",
        action="store_true",
        help="Print per-puzzle mismatches.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result, details = run_puzzle_suite(depth=args.depth, max_cases=args.max_cases)

    print(f"Puzzles run: {result.total}")
    print(f"Solved: {result.solved}")
    print(f"Pass rate: {result.pass_rate:.2f}%")

    if args.show_failures:
        for case, actual in details:
            if actual != case.best_move_uci:
                print(
                    f"FAIL {case.name}: expected {case.best_move_uci}, got {actual if actual is not None else 'None'}"
                )

    return 0 if result.total == 0 or result.solved == result.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
