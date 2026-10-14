from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import chess

try:
    from engine.board_utils import board_to_pretty_string
    from engine.evaluate import evaluate
    from engine.search import search_with_time_controls
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.board_utils import board_to_pretty_string
    from engine.evaluate import evaluate
    from engine.search import search_with_time_controls


UNICODE_PIECES = {
    "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙",
    "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
    ".": "·",
}


def render_board(board: chess.Board, unicode_pieces: bool = True, perspective: chess.Color = chess.WHITE) -> str:
    """Format the board with rank and file coordinates for terminal display."""
    lines = []
    ranks = range(7, -1, -1) if perspective == chess.WHITE else range(8)
    files = range(8) if perspective == chess.WHITE else range(7, -1, -1)

    lines.append("    a   b   c   d   e   f   g   h" if perspective == chess.WHITE else "    h   g   f   e   d   c   b   a")
    lines.append("  +---+---+---+---+---+---+---+---+")

    for rank in ranks:
        row_cells = []
        for file in files:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            symbol = piece.symbol() if piece else "."
            cell = UNICODE_PIECES.get(symbol, symbol) if unicode_pieces else symbol
            row_cells.append(f" {cell} ")
        row_str = "|".join(row_cells)
        lines.append(f"{rank + 1} |{row_str}| {rank + 1}")
        lines.append("  +---+---+---+---+---+---+---+---+")

    lines.append("    a   b   c   d   e   f   g   h" if perspective == chess.WHITE else "    h   g   f   e   d   c   b   a")
    return "\n".join(lines)


def parse_player_move(board: chess.Board, user_input: str) -> chess.Move | None:
    """Parse UCI (e2e4) or SAN (e4, Nf3, O-O) move input."""
    raw = user_input.strip()
    if not raw:
        return None

    # Try UCI first
    try:
        move = chess.Move.from_uci(raw)
        if move in board.legal_moves:
            return move
    except ValueError:
        pass

    # Try SAN next
    try:
        move = board.parse_san(raw)
        if move in board.legal_moves:
            return move
    except ValueError:
        pass

    return None


def format_score(score: int, turn: chess.Color) -> str:
    """Format centipawn score from White's perspective."""
    # Convert mate scores
    if abs(score) >= 90_000:
        plies_to_mate = max(1, 100_000 - abs(score))
        moves_to_mate = (plies_to_mate + 1) // 2
        sign = "+" if score > 0 else "-"
        return f"{sign}M{moves_to_mate}"
    pawns = score / 100.0
    sign = "+" if pawns > 0 else ""
    return f"{sign}{pawns:.2f}"


def run_interactive_game(
    player_color: chess.Color = chess.WHITE,
    depth: int = 4,
    movetime_ms: int = 500,
    use_unicode: bool = True,
) -> None:
    board = chess.Board()
    color_name = "White" if player_color == chess.WHITE else "Black"
    engine_color_name = "Black" if player_color == chess.WHITE else "White"

    print("=" * 50)
    print(" ♚  CHESS ENGINE - INTERACTIVE GAME  ♚")
    print("=" * 50)
    print(f"You are playing as {color_name}.")
    print(f"Engine is playing as {engine_color_name} (depth={depth}, movetime={movetime_ms}ms).")
    print("Type moves in UCI ('e2e4') or SAN ('e4', 'Nf3', 'O-O').")
    print("Commands: 'undo', 'moves', 'eval', 'fen', 'quit'\n")

    while not board.is_game_over(claim_draw=True):
        print(render_board(board, unicode_pieces=use_unicode, perspective=player_color))
        print()

        eval_val = evaluate(board)
        eval_str = format_score(eval_val, chess.WHITE)
        print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'} | Eval: {eval_str} | Move: {board.fullmove_number}")

        if board.is_check():
            print("⚠️  CHECK!")

        if board.turn == player_color:
            # Human move
            while True:
                user_input = input("\nYour move > ").strip()
                cmd = user_input.lower()

                if cmd in {"q", "quit", "exit"}:
                    print("\nGame aborted by player.")
                    return
                elif cmd in {"u", "undo"}:
                    if len(board.move_stack) >= 2:
                        board.pop()
                        board.pop()
                        print("\nUndid last full move.")
                        break
                    elif len(board.move_stack) == 1:
                        board.pop()
                        print("\nUndid last move.")
                        break
                    else:
                        print("No moves to undo.")
                        continue
                elif cmd in {"m", "moves"}:
                    legal = [board.san(m) for m in board.legal_moves]
                    print("Legal moves: " + ", ".join(legal))
                    continue
                elif cmd == "eval":
                    print(f"Current position eval: {format_score(evaluate(board), chess.WHITE)}")
                    continue
                elif cmd == "fen":
                    print(f"FEN: {board.fen()}")
                    continue

                move = parse_player_move(board, user_input)
                if move is None:
                    print(f"Invalid or illegal move '{user_input}'. Type 'moves' for legal moves.")
                    continue

                san_move = board.san(move)
                board.push(move)
                print(f"You played: {san_move} ({move.uci()})\n")
                break
        else:
            # Engine move
            print("\nEngine is thinking...")
            start_t = time.monotonic()
            result = search_with_time_controls(
                board,
                max_depth=depth,
                movetime_ms=movetime_ms,
            )
            elapsed = time.monotonic() - start_t
            move = result.best_move

            if move is None or move not in board.legal_moves:
                move = next(iter(board.legal_moves))

            san_move = board.san(move)
            board.push(move)

            score_str = format_score(result.score, board.turn)
            print(f"Engine played: {san_move} ({move.uci()})")
            print(f"  [depth={result.depth_reached}, score={score_str}, nodes={result.nodes}, time={elapsed:.2f}s]\n")

    # Game Over
    print("\n" + "=" * 50)
    print("GAME OVER")
    print("=" * 50)
    print(render_board(board, unicode_pieces=use_unicode, perspective=player_color))
    print()

    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        print(f"Checkmate! {winner} wins! 🏆")
    elif board.is_stalemate():
        print("Draw by stalemate.")
    elif board.is_insufficient_material():
        print("Draw by insufficient material.")
    elif board.can_claim_threefold_repetition():
        print("Draw by threefold repetition.")
    elif board.can_claim_fifty_moves():
        print("Draw by 50-move rule.")
    else:
        print(f"Game drawn: {board.result(claim_draw=True)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play chess against the engine in your terminal.")
    parser.add_argument(
        "--color",
        choices=["white", "black"],
        default="white",
        help="Player color (default: white)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=4,
        help="Engine search depth (default: 4)",
    )
    parser.add_argument(
        "--movetime",
        type=int,
        default=500,
        help="Engine move time budget in milliseconds (default: 500)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use ASCII piece letters instead of Unicode symbols",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    player_color = chess.WHITE if args.color == "white" else chess.BLACK
    run_interactive_game(
        player_color=player_color,
        depth=args.depth,
        movetime_ms=args.movetime,
        use_unicode=not args.ascii,
    )


if __name__ == "__main__":
    main()
