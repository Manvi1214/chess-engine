from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import chess
import chess.pgn

try:
    from engine.search import search_with_time_controls
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.search import search_with_time_controls


@dataclass(frozen=True)
class EngineConfig:
    name: str
    max_depth: int
    movetime_ms: int


@dataclass(frozen=True)
class MatchScore:
    white_wins: int
    black_wins: int
    draws: int


def play_single_game(
    white: EngineConfig,
    black: EngineConfig,
    game_index: int,
    max_plies: int = 300,
) -> chess.pgn.Game:
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Selfplay"
    game.headers["Round"] = str(game_index)
    game.headers["White"] = white.name
    game.headers["Black"] = black.name
    game.headers["TimeControl"] = f"{white.movetime_ms / 1000:.3f}+0"

    node = game

    for _ply in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        cfg = white if board.turn == chess.WHITE else black
        result = search_with_time_controls(
            board,
            max_depth=cfg.max_depth,
            movetime_ms=cfg.movetime_ms,
        )
        move = result.best_move

        if move is None or move not in board.legal_moves:
            game.headers["Termination"] = "illegal move"
            game.headers["Result"] = "0-1" if board.turn == chess.WHITE else "1-0"
            return game

        board.push(move)
        node = node.add_variation(move)

    if board.is_game_over(claim_draw=True):
        game.headers["Result"] = board.result(claim_draw=True)
        game.headers["Termination"] = "game over"
    else:
        game.headers["Result"] = "1/2-1/2"
        game.headers["Termination"] = "max plies reached"

    return game


def run_match(
    games: int,
    white: EngineConfig,
    black: EngineConfig,
    pgn_path: str | None,
    max_plies: int,
) -> MatchScore:
    white_wins = 0
    black_wins = 0
    draws = 0

    out_handle = None
    if pgn_path:
        path = Path(pgn_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        out_handle = path.open("w", encoding="utf-8")

    try:
        for index in range(1, games + 1):
            game = play_single_game(white=white, black=black, game_index=index, max_plies=max_plies)
            result = game.headers.get("Result", "*")

            if result == "1-0":
                white_wins += 1
            elif result == "0-1":
                black_wins += 1
            else:
                draws += 1

            if out_handle is not None:
                print(game, file=out_handle, end="\n\n")

            print(
                f"Game {index}/{games}: {result}"
                f" ({game.headers.get('White')} vs {game.headers.get('Black')})"
            )
    finally:
        if out_handle is not None:
            out_handle.close()

    return MatchScore(white_wins=white_wins, black_wins=black_wins, draws=draws)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local self-play between two engine settings.")
    parser.add_argument("--games", type=int, default=20, help="Number of games to play.")
    parser.add_argument("--white-name", type=str, default="Engine_vN")
    parser.add_argument("--black-name", type=str, default="Engine_vN1")
    parser.add_argument("--white-depth", type=int, default=3)
    parser.add_argument("--black-depth", type=int, default=3)
    parser.add_argument("--white-movetime", type=int, default=100)
    parser.add_argument("--black-movetime", type=int, default=100)
    parser.add_argument("--max-plies", type=int, default=300)
    parser.add_argument("--pgnout", type=str, default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.games < 1:
        raise ValueError("--games must be >= 1")

    white = EngineConfig(
        name=args.white_name,
        max_depth=max(1, args.white_depth),
        movetime_ms=max(1, args.white_movetime),
    )
    black = EngineConfig(
        name=args.black_name,
        max_depth=max(1, args.black_depth),
        movetime_ms=max(1, args.black_movetime),
    )

    score = run_match(
        games=args.games,
        white=white,
        black=black,
        pgn_path=args.pgnout or None,
        max_plies=max(10, args.max_plies),
    )

    total = score.white_wins + score.black_wins + score.draws
    print("")
    print("Final score")
    print(f"  White wins: {score.white_wins}")
    print(f"  Black wins: {score.black_wins}")
    print(f"  Draws: {score.draws}")
    print(f"  Games: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
