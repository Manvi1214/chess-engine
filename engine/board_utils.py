from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class MoveDetails:
    """Structured move metadata for debugging and testing."""

    uci: str
    from_square: str
    to_square: str
    is_capture: bool
    is_promotion: bool
    promotion_piece: str | None
    is_castling: bool
    is_en_passant: bool
    gives_check: bool


@dataclass(frozen=True)
class GameStateSummary:
    """Snapshot of position status in a test-friendly shape."""

    turn: str
    legal_move_count: int
    is_check: bool
    is_checkmate: bool
    is_stalemate: bool
    is_insufficient_material: bool
    is_fifty_moves: bool
    is_repetition: bool


def load_board_from_fen(fen: str) -> chess.Board:
    """Create a board from a FEN string with explicit validation error context."""
    try:
        return chess.Board(fen)
    except ValueError as exc:
        raise ValueError(f"Invalid FEN: {fen}") from exc


def board_to_pretty_string(board: chess.Board) -> str:
    """Return a board string with rank/file labels for terminal display."""
    rows = str(board).splitlines()
    labeled_rows = [f"{8 - idx} {row}" for idx, row in enumerate(rows)]
    return "\n".join(labeled_rows + ["  a b c d e f g h"])


def piece_count(board: chess.Board) -> int:
    """Return total number of pieces on board."""
    return len(board.piece_map())


def apply_uci_moves(board: chess.Board, uci_moves: list[str]) -> chess.Board:
    """Apply a sequence of UCI moves to an existing board, validating legality."""
    for uci_text in uci_moves:
        move = chess.Move.from_uci(uci_text)
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move '{uci_text}' for position: {board.fen()}")
        board.push(move)
    return board


def inspect_move(board: chess.Board, move: chess.Move) -> MoveDetails:
    """Extract human-readable flags and square information for a move."""
    from_square = chess.square_name(move.from_square)
    to_square = chess.square_name(move.to_square)

    is_legal = move in board.legal_moves
    gives_check = False
    if is_legal:
        board.push(move)
        gives_check = board.is_check()
        board.pop()

    promotion_piece = chess.piece_name(move.promotion) if move.promotion else None

    return MoveDetails(
        uci=move.uci(),
        from_square=from_square,
        to_square=to_square,
        is_capture=board.is_capture(move),
        is_promotion=move.promotion is not None,
        promotion_piece=promotion_piece,
        is_castling=board.is_castling(move),
        is_en_passant=board.is_en_passant(move),
        gives_check=gives_check,
    )


def game_state_summary(board: chess.Board) -> GameStateSummary:
    """Return a compact state report for the current board."""
    return GameStateSummary(
        turn="white" if board.turn == chess.WHITE else "black",
        legal_move_count=board.legal_moves.count(),
        is_check=board.is_check(),
        is_checkmate=board.is_checkmate(),
        is_stalemate=board.is_stalemate(),
        is_insufficient_material=board.is_insufficient_material(),
        is_fifty_moves=board.is_fifty_moves(),
        is_repetition=board.is_repetition(),
    )
