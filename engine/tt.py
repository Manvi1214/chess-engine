from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import chess


class TTFlag(Enum):
    """Bound type for a transposition-table entry."""

    EXACT = auto()
    LOWERBOUND = auto()
    UPPERBOUND = auto()
    # Backward-compatible aliases used by earlier code/tests.
    LOWER = LOWERBOUND
    UPPER = UPPERBOUND


@dataclass(frozen=True)
class TTEntry:
    """Single transposition-table entry."""

    key: int
    depth: int
    score: int
    flag: TTFlag
    best_move_uci: str | None


class TranspositionTable:
    """Bounded transposition table with depth-preferred replacement."""

    def __init__(self, max_entries: int = 500_000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self.max_entries = max_entries
        self._table: dict[int, TTEntry] = {}

    def __len__(self) -> int:
        return len(self._table)

    @staticmethod
    def key_for_board(board: chess.Board) -> int:
        # python-chess exposes a Zobrist transposition key for fast hashing.
        return board._transposition_key()

    def clear(self) -> None:
        self._table.clear()

    def get(self, key: int) -> TTEntry | None:
        return self._table.get(key)

    def get_best_move(self, key: int) -> chess.Move | None:
        entry = self._table.get(key)
        if entry is None or entry.best_move_uci is None:
            return None
        try:
            return chess.Move.from_uci(entry.best_move_uci)
        except ValueError:
            return None

    def store(
        self,
        *,
        key: int,
        depth: int,
        score: int,
        flag: TTFlag,
        best_move: chess.Move | None,
    ) -> None:
        existing = self._table.get(key)
        if existing is not None and existing.depth > depth:
            # Keep deeper information already cached for this exact key.
            return

        if len(self._table) >= self.max_entries and key not in self._table:
            self._evict_shallowest_entry()

        self._table[key] = TTEntry(
            key=key,
            depth=depth,
            score=score,
            flag=flag,
            best_move_uci=best_move.uci() if best_move is not None else None,
        )

    def _evict_shallowest_entry(self) -> None:
        # Simple depth-preferred eviction: discard one shallowest entry.
        shallowest_key = min(self._table.items(), key=lambda item: item[1].depth)[0]
        self._table.pop(shallowest_key, None)
