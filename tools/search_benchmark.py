from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chess

try:
    from engine.search import compare_alpha_beta_with_without_tt, compare_search_nodes
    from engine.tt import TranspositionTable
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.search import compare_alpha_beta_with_without_tt, compare_search_nodes
    from engine.tt import TranspositionTable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare plain negamax and alpha-beta node counts.")
    parser.add_argument("--depth", type=int, default=3, help="Search depth (>=1).")
    parser.add_argument(
        "--fen",
        type=str,
        default=chess.STARTING_FEN,
        help="FEN position to benchmark (default: starting position).",
    )
    parser.add_argument(
        "--tt",
        action="store_true",
        help="Also compare alpha-beta with and without transposition table.",
    )
    parser.add_argument(
        "--tt-size",
        type=int,
        default=100_000,
        help="TT max entries when --tt is used.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.depth < 1:
        raise ValueError("--depth must be >= 1")

    board = chess.Board(args.fen)
    plain, alpha_beta = compare_search_nodes(board, args.depth)

    reduction = 0.0
    if plain.nodes > 0:
        reduction = 100.0 * (plain.nodes - alpha_beta.nodes) / plain.nodes

    print(f"Depth: {args.depth}")
    print(f"FEN: {board.fen()}")
    print("")
    print("Plain negamax:")
    print(f"  best move: {plain.best_move}")
    print(f"  score: {plain.score}")
    print(f"  nodes: {plain.nodes}")
    print("")
    print("Alpha-beta:")
    print(f"  best move: {alpha_beta.best_move}")
    print(f"  score: {alpha_beta.score}")
    print(f"  nodes: {alpha_beta.nodes}")
    print("")
    print(f"Node reduction: {reduction:.2f}%")

    if args.tt:
        tt = TranspositionTable(max_entries=args.tt_size)
        ab_no_tt, ab_with_tt = compare_alpha_beta_with_without_tt(board, args.depth, tt=tt)
        tt_reduction = 0.0
        if ab_no_tt.nodes > 0:
            tt_reduction = 100.0 * (ab_no_tt.nodes - ab_with_tt.nodes) / ab_no_tt.nodes

        print("")
        print("Alpha-beta without TT:")
        print(f"  best move: {ab_no_tt.best_move}")
        print(f"  score: {ab_no_tt.score}")
        print(f"  nodes: {ab_no_tt.nodes}")
        print("")
        print("Alpha-beta with TT:")
        print(f"  best move: {ab_with_tt.best_move}")
        print(f"  score: {ab_with_tt.score}")
        print(f"  nodes: {ab_with_tt.nodes}")
        print(f"  tt hits: {ab_with_tt.tt_hits}")
        print("")
        print(f"TT node reduction: {tt_reduction:.2f}%")


if __name__ == "__main__":
    main()
