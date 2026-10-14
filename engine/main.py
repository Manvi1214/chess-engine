from __future__ import annotations

import chess


def create_starting_board() -> chess.Board:
    """Return a fresh chess board in the standard starting position."""
    return chess.Board()


def parse_uci_move(board: chess.Board, uci_text: str) -> chess.Move | None:
    """Parse and validate a UCI move string against the board's legal moves."""
    try:
        move = chess.Move.from_uci(uci_text.strip())
    except ValueError:
        return None

    if move not in board.legal_moves:
        return None

    return move


def print_status(board: chess.Board) -> None:
    """Print board and basic game-state info for terminal play."""
    print(board)
    print()
    print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")

    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        print(f"Checkmate. {winner} wins.")
    elif board.is_stalemate():
        print("Stalemate.")
    elif board.is_check():
        print("Check.")


def run_terminal_game_loop() -> None:
    """Simple human-vs-human terminal loop using UCI move input."""
    board = create_starting_board()

    while not board.is_game_over():
        print_status(board)
        move_text = input("Enter move in UCI (or q to quit): ").strip()

        if move_text.lower() in {"q", "quit", "exit"}:
            print("Game ended by user.")
            return

        move = parse_uci_move(board, move_text)
        if move is None:
            print("Illegal or invalid move. Try again.\n")
            continue

        board.push(move)
        print()

    print_status(board)
    print(f"Game over: {board.result(claim_draw=True)}")


def main() -> None:
    run_terminal_game_loop()


if __name__ == "__main__":
    main()
