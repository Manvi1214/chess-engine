from __future__ import annotations

import chess

PIECE_VALUES: dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

GAME_STAGE_INC: dict[chess.PieceType, int] = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
    chess.KING: 0,
}

MAX_STAGE = 24
MOBILITY_WEIGHT = 2

# Piece-square tables indexed by python-chess square index (a1..h8).
# Values are from White's perspective; Black uses mirrored squares.
PSQT_MG: dict[chess.PieceType, tuple[int, ...]] = {
    chess.PAWN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        0, 5, 5, -5, -5, 5, 5, 0,
        0, 10, 10, 15, 15, 10, 10, 0,
        5, 10, 10, 20, 20, 10, 10, 5,
        10, 15, 15, 25, 25, 15, 15, 10,
        15, 20, 20, 30, 30, 20, 20, 15,
        0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.KNIGHT: (
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50,
    ),
    chess.BISHOP: (
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ),
    chess.ROOK: (
        0, 0, 5, 10, 10, 5, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.QUEEN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ),
    chess.KING: (
        20, 25, 10, 0, 0, 10, 25, 20,
        10, 10, -5, -10, -10, -5, 10, 10,
        -10, -15, -20, -25, -25, -20, -15, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -35, -40, -45, -45, -40, -35, -30,
        -35, -40, -45, -50, -50, -45, -40, -35,
        -35, -40, -45, -50, -50, -45, -40, -35,
        -35, -40, -45, -50, -50, -45, -40, -35,
    ),
}

PSQT_EG: dict[chess.PieceType, tuple[int, ...]] = {
    chess.PAWN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, -10, -10, 10, 10, 5,
        5, 10, 15, 20, 20, 15, 10, 5,
        10, 15, 20, 25, 25, 20, 15, 10,
        15, 20, 25, 30, 30, 25, 20, 15,
        20, 25, 30, 35, 35, 30, 25, 20,
        40, 40, 40, 40, 40, 40, 40, 40,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.KNIGHT: (
        -45, -35, -25, -25, -25, -25, -35, -45,
        -30, -10, 0, 0, 0, 0, -10, -30,
        -20, 0, 10, 12, 12, 10, 0, -20,
        -15, 5, 12, 18, 18, 12, 5, -15,
        -15, 5, 12, 18, 18, 12, 5, -15,
        -20, 0, 10, 12, 12, 10, 0, -20,
        -30, -10, 0, 0, 0, 0, -10, -30,
        -45, -35, -25, -25, -25, -25, -35, -45,
    ),
    chess.BISHOP: (
        -15, -8, -8, -8, -8, -8, -8, -15,
        -8, 0, 0, 0, 0, 0, 0, -8,
        -8, 0, 6, 10, 10, 6, 0, -8,
        -8, 6, 8, 10, 10, 8, 6, -8,
        -8, 2, 10, 10, 10, 10, 2, -8,
        -8, 10, 10, 10, 10, 10, 10, -8,
        -8, 6, 0, 0, 0, 0, 6, -8,
        -15, -8, -8, -8, -8, -8, -8, -15,
    ),
    chess.ROOK: (
        0, 0, 5, 10, 10, 5, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.QUEEN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ),
    chess.KING: (
        -35, -20, -10, -5, -5, -10, -20, -35,
        -20, -5, 0, 5, 5, 0, -5, -20,
        -10, 0, 10, 15, 15, 10, 0, -10,
        -5, 5, 15, 20, 20, 15, 5, -5,
        -5, 5, 15, 20, 20, 15, 5, -5,
        -10, 0, 10, 15, 15, 10, 0, -10,
        -20, -5, 0, 5, 5, 0, -5, -20,
        -35, -20, -10, -5, -5, -10, -20, -35,
    ),
}


def evaluate_material(board: chess.Board) -> int:
    """Return pure material score in centipawns from White's perspective."""
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        score += value * (white_count - black_count)
    return score


def evaluate_psqt_components(board: chess.Board) -> tuple[int, int]:
    """Return middlegame and endgame PSQT components from White's perspective."""
    mg_score = 0
    eg_score = 0

    for piece_type in PSQT_MG:
        mg_table = PSQT_MG[piece_type]
        eg_table = PSQT_EG[piece_type]

        for square in board.pieces(piece_type, chess.WHITE):
            mg_score += mg_table[square]
            eg_score += eg_table[square]
        for square in board.pieces(piece_type, chess.BLACK):
            mirrored = chess.square_mirror(square)
            mg_score -= mg_table[mirrored]
            eg_score -= eg_table[mirrored]

    return mg_score, eg_score


def calculate_game_stage(board: chess.Board) -> int:
    """Return a game-stage value in [0, MAX_STAGE], where MAX_STAGE is opening-like."""
    stage = 0
    for piece_type, inc in GAME_STAGE_INC.items():
        if inc == 0:
            continue
        stage += inc * (
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
        )
    return min(stage, MAX_STAGE)


def evaluate_psqt(board: chess.Board) -> int:
    """Return tapered PSQT score in centipawns from White's perspective."""
    mg_score, eg_score = evaluate_psqt_components(board)
    stage = calculate_game_stage(board)
    return (mg_score * stage + eg_score * (MAX_STAGE - stage)) // MAX_STAGE


def _legal_moves_for_color(board: chess.Board, color: chess.Color) -> int:
    temp = board.copy(stack=False)
    temp.turn = color
    return temp.legal_moves.count()


def evaluate_mobility(board: chess.Board) -> int:
    """Return lightweight mobility term (White legal moves - Black legal moves)."""
    white_moves = _legal_moves_for_color(board, chess.WHITE)
    black_moves = _legal_moves_for_color(board, chess.BLACK)
    return MOBILITY_WEIGHT * (white_moves - black_moves)


def evaluate(board: chess.Board) -> int:
    """Return static evaluation in centipawns from White's perspective."""
    return evaluate_material(board) + evaluate_psqt(board) + evaluate_mobility(board)
