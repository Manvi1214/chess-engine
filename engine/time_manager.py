from __future__ import annotations

import chess


def allocate_time_seconds(
    board: chess.Board,
    wtime_ms: int | None,
    btime_ms: int | None,
    winc_ms: int = 0,
    binc_ms: int = 0,
    fallback_ms: int = 2000,
) -> float:
    """Return a simple per-move search budget in seconds.

    Strategy:
    - If side-to-move clock is unknown, use fallback.
    - Spend roughly 1/25 of remaining time plus half increment.
    - Keep at least 50ms and never exceed half of remaining clock.
    """
    if board.turn == chess.WHITE:
        remaining_ms = wtime_ms
        increment_ms = winc_ms
    else:
        remaining_ms = btime_ms
        increment_ms = binc_ms

    if remaining_ms is None:
        return max(0.05, fallback_ms / 1000.0)

    safe_remaining = max(50, remaining_ms - 50)
    target = safe_remaining // 25 + increment_ms // 2
    capped = min(target, safe_remaining // 2)
    budget_ms = max(50, capped)

    return budget_ms / 1000.0
