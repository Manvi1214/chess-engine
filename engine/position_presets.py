from __future__ import annotations

import chess

POSITION_PRESETS: dict[str, str] = {
    "startpos": chess.STARTING_FEN,
    "fools_mate": "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
    "mate_corner": "7k/8/8/8/8/6k1/6q1/7K w - - 0 1",
    "stalemate_corner": "7k/8/8/8/8/8/5qk1/7K w - - 0 1",
    "castle_ready": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "en_passant_ready": "8/8/8/3pP3/8/8/8/8 w - d6 0 1",
}


def list_preset_names() -> list[str]:
    """Return preset names in a stable display order."""
    return sorted(POSITION_PRESETS.keys())


def get_preset_fen(name: str) -> str:
    """Resolve a named board preset to its FEN string."""
    key = name.strip().lower()
    if key not in POSITION_PRESETS:
        available = ", ".join(list_preset_names())
        raise ValueError(f"Unknown preset '{name}'. Available presets: {available}")
    return POSITION_PRESETS[key]
