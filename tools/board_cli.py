from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chess

try:
    from engine.board_utils import (
        apply_uci_moves,
        board_to_pretty_string,
        game_state_summary,
        inspect_move,
        load_board_from_fen,
    )
    from engine.position_presets import get_preset_fen, list_preset_names
except ModuleNotFoundError:
    # Allows direct execution: python tools/board_cli.py
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.board_utils import (
        apply_uci_moves,
        board_to_pretty_string,
        game_state_summary,
        inspect_move,
        load_board_from_fen,
    )
    from engine.position_presets import get_preset_fen, list_preset_names


def build_board(
    startpos: bool,
    fen: str | None,
    preset: str | None,
    moves: list[str],
) -> chess.Board:
    """Build a board from startpos/FEN/preset and apply optional UCI moves."""
    selected_sources = sum([1 if startpos else 0, 1 if fen else 0, 1 if preset else 0])
    if selected_sources > 1:
        raise ValueError("Use only one of --startpos, --fen, or --preset.")

    if preset:
        board = load_board_from_fen(get_preset_fen(preset))
    elif fen:
        board = load_board_from_fen(fen)
    else:
        board = chess.Board()

    apply_uci_moves(board, moves)
    return board


def render_report(board: chess.Board, show_legal: bool, max_legal: int) -> str:
    """Render a board analysis report for terminal use."""
    summary = game_state_summary(board)

    lines = [
        "Board:",
        board_to_pretty_string(board),
        "",
        f"FEN: {board.fen()}",
        f"Turn: {summary.turn}",
        f"Legal moves: {summary.legal_move_count}",
        f"Check: {summary.is_check}",
        f"Checkmate: {summary.is_checkmate}",
        f"Stalemate: {summary.is_stalemate}",
        f"Insufficient material: {summary.is_insufficient_material}",
        f"Fifty-move rule claim available: {summary.is_fifty_moves}",
        f"Threefold repetition claim available: {summary.is_repetition}",
    ]

    if show_legal:
        lines.append("")
        lines.append("Sample legal moves:")
        for idx, move in enumerate(board.legal_moves):
            if idx >= max_legal:
                break
            details = inspect_move(board, move)
            flags = []
            if details.is_capture:
                flags.append("capture")
            if details.is_castling:
                flags.append("castle")
            if details.is_en_passant:
                flags.append("en-passant")
            if details.is_promotion:
                flags.append(f"promote={details.promotion_piece}")
            if details.gives_check:
                flags.append("check")

            flag_text = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- {details.uci}: {details.from_square}->{details.to_square}{flag_text}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a chess board position from terminal.")
    parser.add_argument(
        "--startpos",
        action="store_true",
        help="Start from standard initial position (default if --fen not supplied).",
    )
    parser.add_argument("--fen", type=str, default=None, help="Load board from a FEN string.")
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help="Load a named preset position (see --list-presets).",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print available preset names and exit.",
    )
    parser.add_argument(
        "--moves",
        nargs="*",
        default=[],
        help="Optional UCI moves to apply on top of start position/FEN.",
    )
    parser.add_argument(
        "--show-legal",
        action="store_true",
        help="Print a sample of legal moves with flags.",
    )
    parser.add_argument(
        "--max-legal",
        type=int,
        default=20,
        help="Maximum legal moves to print when --show-legal is set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.max_legal < 1:
        raise ValueError("--max-legal must be >= 1")

    if args.list_presets:
        print("Available presets:")
        for name in list_preset_names():
            print(f"- {name}")
        return

    board = build_board(
        startpos=args.startpos,
        fen=args.fen,
        preset=args.preset,
        moves=args.moves,
    )
    print(render_report(board, show_legal=args.show_legal, max_legal=args.max_legal))


if __name__ == "__main__":
    main()
