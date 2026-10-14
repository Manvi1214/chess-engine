from __future__ import annotations

from dataclasses import dataclass
import time

import chess

from engine.evaluate import PIECE_VALUES, evaluate
from engine.time_manager import allocate_time_seconds
from engine.tt import TTFlag, TTEntry, TranspositionTable

INF = 10**9
MATE_SCORE = 100_000
DRAW_SCORE = 0
NULL_MOVE_REDUCTION = 2


@dataclass(frozen=True)
class SearchRunStats:
    """Search output and visited node count for a fixed-depth run."""

    best_move: chess.Move | None
    score: int
    nodes: int
    tt_hits: int = 0


@dataclass(frozen=True)
class IterativeDeepeningResult:
    """Outcome for iterative deepening under a time budget."""

    best_move: chess.Move | None
    score: int
    depth_reached: int
    nodes: int
    timed_out: bool
    time_spent_sec: float


class SearchTimeout(Exception):
    """Raised when search exceeds its deadline."""


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise SearchTimeout


def _evaluate_for_side_to_move(board: chess.Board) -> int:
    """Convert white-perspective eval to side-to-move perspective."""
    white_pov = evaluate(board)
    return white_pov if board.turn == chess.WHITE else -white_pov


def _terminal_score(board: chess.Board, ply: int) -> int:
    """Return a terminal node score from side-to-move perspective."""
    if board.is_checkmate():
        # Side to move is checkmated, so this is losing.
        return -MATE_SCORE + ply

    if board.is_game_over(claim_draw=True):
        return DRAW_SCORE

    return _evaluate_for_side_to_move(board)


def _ordered_legal_moves(
    board: chess.Board,
    preferred_move: chess.Move | None = None,
    ply: int = 0,
    killer_moves: dict[int, list[chess.Move]] | None = None,
    history_scores: dict[chess.Move, int] | None = None,
) -> list[chess.Move]:
    """Return legal moves ordered by TT/captures/killers/history, then lexicographic."""
    legal_moves = list(board.legal_moves)

    def score(move: chess.Move) -> int:
        if preferred_move is not None and move == preferred_move:
            return 10_000_000

        if board.is_capture(move):
            return 5_000_000 + _mvv_lva_score(board, move)

        killer_bucket = killer_moves.get(ply, []) if killer_moves is not None else []
        if any(move == killer for killer in killer_bucket):
            return 4_000_000

        if history_scores is not None:
            return history_scores.get(move, 0)

        return 0

    return sorted(
        legal_moves,
        key=lambda move: (-score(move), move.uci()),
    )


def _record_killer_move(killer_moves: dict[int, list[chess.Move]], ply: int, move: chess.Move) -> None:
    bucket = killer_moves.setdefault(ply, [])
    if any(move == killer for killer in bucket):
        return
    bucket.insert(0, move)
    if len(bucket) > 2:
        bucket.pop()


def _has_non_pawn_material(board: chess.Board, color: chess.Color) -> bool:
    for piece in board.piece_map().values():
        if piece.color == color and piece.piece_type not in (chess.KING, chess.PAWN):
            return True
    return False


def _mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    """Return MVV-LVA score (higher is better for ordering captures)."""
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    victim_value = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
    attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
    return victim_value * 10 - attacker_value


def _ordered_capture_moves(board: chess.Board) -> list[chess.Move]:
    """Return legal captures ordered by MVV-LVA."""
    captures = [move for move in board.legal_moves if board.is_capture(move)]
    return sorted(captures, key=lambda move: (-_mvv_lva_score(board, move), move.uci()))


def _probe_tt_and_adjust_bounds(
    entry: TTEntry | None,
    depth: int,
    alpha: int,
    beta: int,
    counter: dict[str, int] | None = None,
) -> tuple[int, int, int | None]:
    """Apply TT bound information. Returns (alpha, beta, exact_score_or_none)."""
    if entry is None or entry.depth < depth:
        return alpha, beta, None

    if counter is not None:
        counter["tt_hits"] += 1

    if entry.flag is TTFlag.EXACT:
        return alpha, beta, entry.score
    if entry.flag is TTFlag.LOWERBOUND:
        alpha = max(alpha, entry.score)
    elif entry.flag is TTFlag.UPPERBOUND:
        beta = min(beta, entry.score)

    if alpha >= beta:
        return alpha, beta, entry.score

    return alpha, beta, None


def quiescence(
    board: chess.Board,
    alpha: int,
    beta: int,
    ply: int = 0,
    deadline: float | None = None,
) -> int:
    """Capture-only quiescence search with stand-pat evaluation."""
    _check_deadline(deadline)

    if board.is_checkmate():
        return -MATE_SCORE + ply

    if board.is_game_over(claim_draw=True):
        return DRAW_SCORE

    stand_pat = _evaluate_for_side_to_move(board)
    if stand_pat >= beta:
        return beta

    if stand_pat > alpha:
        alpha = stand_pat

    for move in _ordered_capture_moves(board):
        board.push(move)
        try:
            score = -quiescence(board, -beta, -alpha, ply + 1, deadline)
        finally:
            board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax(board: chess.Board, depth: int, ply: int = 0) -> int:
    """Baseline negamax search without alpha-beta pruning."""
    if depth < 0:
        raise ValueError("depth must be >= 0")

    if depth == 0 or board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    best_score = -INF

    for move in board.legal_moves:
        board.push(move)
        try:
            score = -negamax(board, depth - 1, ply + 1)
        finally:
            board.pop()

        if score > best_score:
            best_score = score

    return best_score


def _negamax_counted(
    board: chess.Board,
    depth: int,
    ply: int,
    node_counter: dict[str, int],
) -> int:
    node_counter["nodes"] += 1

    if depth == 0 or board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    best_score = -INF
    for move in board.legal_moves:
        board.push(move)
        try:
            score = -_negamax_counted(board, depth - 1, ply + 1, node_counter)
        finally:
            board.pop()
        if score > best_score:
            best_score = score

    return best_score


def _quiescence_counted(
    board: chess.Board,
    alpha: int,
    beta: int,
    ply: int,
    node_counter: dict[str, int],
    deadline: float | None = None,
) -> int:
    node_counter["nodes"] += 1
    _check_deadline(deadline)

    if board.is_checkmate():
        return -MATE_SCORE + ply

    if board.is_game_over(claim_draw=True):
        return DRAW_SCORE

    stand_pat = _evaluate_for_side_to_move(board)
    if stand_pat >= beta:
        return beta

    if stand_pat > alpha:
        alpha = stand_pat

    for move in _ordered_capture_moves(board):
        board.push(move)
        try:
            score = -_quiescence_counted(board, -beta, -alpha, ply + 1, node_counter, deadline)
        finally:
            board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax_alpha_beta(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int = 0,
    deadline: float | None = None,
    tt: TranspositionTable | None = None,
    killer_moves: dict[int, list[chess.Move]] | None = None,
    history_scores: dict[chess.Move, int] | None = None,
) -> int:
    """Negamax search with alpha-beta pruning."""
    if depth < 0:
        raise ValueError("depth must be >= 0")

    _check_deadline(deadline)

    if board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    if depth == 0:
        return quiescence(board, alpha, beta, ply, deadline)

    key = TranspositionTable.key_for_board(board)
    tt_entry = tt.get(key) if tt is not None else None
    alpha_orig = alpha
    beta_orig = beta

    alpha, beta, exact = _probe_tt_and_adjust_bounds(tt_entry, depth, alpha, beta)
    if exact is not None:
        return exact

    if (
        depth >= 3
        and not board.is_check()
        and _has_non_pawn_material(board, board.turn)
    ):
        board.push(chess.Move.null())
        try:
            null_score = -negamax_alpha_beta(
                board,
                depth - 1 - NULL_MOVE_REDUCTION,
                -beta,
                -beta + 1,
                ply + 1,
                deadline,
                tt,
                killer_moves,
                history_scores,
            )
        finally:
            board.pop()
        if null_score >= beta:
            return beta

    best_score = -INF
    best_move: chess.Move | None = None
    preferred = tt.get_best_move(key) if tt is not None else None

    for move in _ordered_legal_moves(board, preferred, ply, killer_moves, history_scores):
        board.push(move)
        try:
            score = -negamax_alpha_beta(
                board,
                depth - 1,
                -beta,
                -alpha,
                ply + 1,
                deadline,
                tt,
                killer_moves,
                history_scores,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            if not board.is_capture(move):
                if killer_moves is not None:
                    _record_killer_move(killer_moves, ply, move)
                if history_scores is not None:
                    history_scores[move] = history_scores.get(move, 0) + depth * depth
            break

    if tt is not None:
        flag = TTFlag.EXACT
        if best_score <= alpha_orig:
            flag = TTFlag.UPPERBOUND
        elif best_score >= beta_orig:
            flag = TTFlag.LOWERBOUND

        tt.store(
            key=key,
            depth=depth,
            score=best_score,
            flag=flag,
            best_move=best_move,
        )

    return best_score


def _negamax_alpha_beta_counted(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    node_counter: dict[str, int],
    deadline: float | None = None,
    tt: TranspositionTable | None = None,
    killer_moves: dict[int, list[chess.Move]] | None = None,
    history_scores: dict[chess.Move, int] | None = None,
) -> int:
    node_counter["nodes"] += 1
    _check_deadline(deadline)

    if board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    if depth == 0:
        return _quiescence_counted(board, alpha, beta, ply, node_counter, deadline)

    key = TranspositionTable.key_for_board(board)
    tt_entry = tt.get(key) if tt is not None else None
    alpha_orig = alpha
    beta_orig = beta

    alpha, beta, exact = _probe_tt_and_adjust_bounds(tt_entry, depth, alpha, beta, node_counter)
    if exact is not None:
        return exact

    if (
        depth >= 3
        and not board.is_check()
        and _has_non_pawn_material(board, board.turn)
    ):
        board.push(chess.Move.null())
        try:
            null_score = -_negamax_alpha_beta_counted(
                board,
                depth - 1 - NULL_MOVE_REDUCTION,
                -beta,
                -beta + 1,
                ply + 1,
                node_counter,
                deadline,
                tt,
                killer_moves,
                history_scores,
            )
        finally:
            board.pop()
        if null_score >= beta:
            return beta

    best_score = -INF
    best_move: chess.Move | None = None
    preferred = tt.get_best_move(key) if tt is not None else None

    for move in _ordered_legal_moves(board, preferred, ply, killer_moves, history_scores):
        board.push(move)
        try:
            score = -_negamax_alpha_beta_counted(
                board,
                depth - 1,
                -beta,
                -alpha,
                ply + 1,
                node_counter,
                deadline,
                tt,
                killer_moves,
                history_scores,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            if not board.is_capture(move):
                if killer_moves is not None:
                    _record_killer_move(killer_moves, ply, move)
                if history_scores is not None:
                    history_scores[move] = history_scores.get(move, 0) + depth * depth
            break

    if tt is not None:
        flag = TTFlag.EXACT
        if best_score <= alpha_orig:
            flag = TTFlag.UPPERBOUND
        elif best_score >= beta_orig:
            flag = TTFlag.LOWERBOUND

        tt.store(
            key=key,
            depth=depth,
            score=best_score,
            flag=flag,
            best_move=best_move,
        )

    return best_score


def find_best_move(board: chess.Board, depth: int) -> chess.Move | None:
    """Return best move found by baseline negamax at fixed depth."""
    if depth < 1:
        raise ValueError("depth must be >= 1")

    best_move: chess.Move | None = None
    best_score = -INF

    for move in board.legal_moves:
        board.push(move)
        try:
            score = -negamax(board, depth - 1, ply=1)
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

    return best_move


def find_best_move_alpha_beta(
    board: chess.Board,
    depth: int,
    deadline: float | None = None,
    tt: TranspositionTable | None = None,
) -> chess.Move | None:
    """Return best move found by alpha-beta negamax at fixed depth."""
    if depth < 1:
        raise ValueError("depth must be >= 1")

    best_move: chess.Move | None = None
    best_score = -INF
    alpha = -INF
    beta = INF
    killer_moves: dict[int, list[chess.Move]] = {}
    history_scores: dict[chess.Move, int] = {}

    key = TranspositionTable.key_for_board(board)
    preferred = tt.get_best_move(key) if tt is not None else None

    for move in _ordered_legal_moves(board, preferred, 0, killer_moves, history_scores):
        _check_deadline(deadline)
        board.push(move)
        try:
            score = -negamax_alpha_beta(
                board,
                depth - 1,
                -beta,
                -alpha,
                ply=1,
                deadline=deadline,
                tt=tt,
                killer_moves=killer_moves,
                history_scores=history_scores,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

    return best_move


def find_best_move_with_stats(board: chess.Board, depth: int) -> SearchRunStats:
    """Run baseline negamax and return best move, score, and visited nodes."""
    if depth < 1:
        raise ValueError("depth must be >= 1")

    best_move: chess.Move | None = None
    best_score = -INF
    counter = {"nodes": 0}

    for move in board.legal_moves:
        board.push(move)
        try:
            score = -_negamax_counted(board, depth - 1, 1, counter)
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

    return SearchRunStats(best_move=best_move, score=best_score, nodes=counter["nodes"])


def find_best_move_alpha_beta_with_stats(
    board: chess.Board,
    depth: int,
    deadline: float | None = None,
    tt: TranspositionTable | None = None,
) -> SearchRunStats:
    """Run alpha-beta negamax and return best move, score, and visited nodes."""
    if depth < 1:
        raise ValueError("depth must be >= 1")

    best_move: chess.Move | None = None
    best_score = -INF
    alpha = -INF
    beta = INF
    counter = {"nodes": 0, "tt_hits": 0}
    killer_moves: dict[int, list[chess.Move]] = {}
    history_scores: dict[chess.Move, int] = {}

    key = TranspositionTable.key_for_board(board)
    preferred = tt.get_best_move(key) if tt is not None else None

    for move in _ordered_legal_moves(board, preferred, 0, killer_moves, history_scores):
        _check_deadline(deadline)
        board.push(move)
        try:
            score = -_negamax_alpha_beta_counted(
                board,
                depth - 1,
                -beta,
                -alpha,
                1,
                counter,
                deadline,
                tt,
                killer_moves,
                history_scores,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

    return SearchRunStats(
        best_move=best_move,
        score=best_score,
        nodes=counter["nodes"],
        tt_hits=counter["tt_hits"],
    )


def compare_search_nodes(board: chess.Board, depth: int) -> tuple[SearchRunStats, SearchRunStats]:
    """Return (plain_negamax_stats, alpha_beta_stats) at the same depth."""
    plain = find_best_move_with_stats(board, depth)
    alpha_beta = find_best_move_alpha_beta_with_stats(board, depth)
    return plain, alpha_beta


def compare_alpha_beta_with_without_tt(
    board: chess.Board,
    depth: int,
    tt: TranspositionTable | None = None,
) -> tuple[SearchRunStats, SearchRunStats]:
    """Return (alpha-beta no TT, alpha-beta with TT) for same position/depth."""
    without_tt = find_best_move_alpha_beta_with_stats(board, depth, tt=None)
    with_tt = find_best_move_alpha_beta_with_stats(
        board,
        depth,
        tt=tt if tt is not None else TranspositionTable(),
    )
    return without_tt, with_tt


def iterative_deepening_search(
    board: chess.Board,
    max_depth: int,
    time_budget_sec: float,
    tt: TranspositionTable | None = None,
) -> IterativeDeepeningResult:
    """Iterative deepening over alpha-beta+quiescence within a time budget."""
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    if time_budget_sec <= 0:
        raise ValueError("time_budget_sec must be > 0")

    start = time.monotonic()
    deadline = start + time_budget_sec

    best_move: chess.Move | None = None
    best_score = -INF
    depth_reached = 0
    total_nodes = 0
    timed_out = False

    for depth in range(1, max_depth + 1):
        try:
            stats = find_best_move_alpha_beta_with_stats(
                board,
                depth,
                deadline=deadline,
                tt=tt,
            )
        except SearchTimeout:
            timed_out = True
            break

        total_nodes += stats.nodes
        if stats.best_move is not None:
            best_move = stats.best_move
            best_score = stats.score
            depth_reached = depth

    if best_move is None:
        best_move = next(iter(board.legal_moves), None)
        best_score = 0

    elapsed = time.monotonic() - start
    if elapsed >= time_budget_sec and depth_reached < max_depth:
        timed_out = True

    return IterativeDeepeningResult(
        best_move=best_move,
        score=best_score,
        depth_reached=depth_reached,
        nodes=total_nodes,
        timed_out=timed_out,
        time_spent_sec=elapsed,
    )


def search_with_time_controls(
    board: chess.Board,
    max_depth: int,
    movetime_ms: int | None = None,
    wtime_ms: int | None = None,
    btime_ms: int | None = None,
    winc_ms: int = 0,
    binc_ms: int = 0,
    fallback_ms: int = 2000,
    tt: TranspositionTable | None = None,
) -> IterativeDeepeningResult:
    """Run iterative deepening using either movetime or simple clock allocation."""
    if movetime_ms is not None:
        if movetime_ms <= 0:
            raise ValueError("movetime_ms must be > 0")
        budget_sec = movetime_ms / 1000.0
    else:
        budget_sec = allocate_time_seconds(
            board=board,
            wtime_ms=wtime_ms,
            btime_ms=btime_ms,
            winc_ms=winc_ms,
            binc_ms=binc_ms,
            fallback_ms=fallback_ms,
        )

    return iterative_deepening_search(
        board=board,
        max_depth=max_depth,
        time_budget_sec=budget_sec,
        tt=tt,
    )
