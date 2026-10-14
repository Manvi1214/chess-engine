import chess
import pytest

from engine.position_presets import get_preset_fen, list_preset_names


def test_list_preset_names_contains_expected_entries() -> None:
    names = list_preset_names()
    assert "startpos" in names
    assert "fools_mate" in names
    assert "castle_ready" in names


def test_get_preset_fen_returns_valid_fen() -> None:
    fen = get_preset_fen("fools_mate")
    board = chess.Board(fen)
    assert board.is_checkmate() is True


def test_get_preset_fen_is_case_insensitive() -> None:
    lower = get_preset_fen("mate_corner")
    mixed = get_preset_fen("MaTe_CoRnEr")
    assert lower == mixed


def test_get_preset_fen_raises_for_unknown_name() -> None:
    with pytest.raises(ValueError) as exc:
        get_preset_fen("not_a_real_preset")
    assert "Unknown preset" in str(exc.value)
