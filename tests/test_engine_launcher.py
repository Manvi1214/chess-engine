from __future__ import annotations

import importlib.util
from pathlib import Path


def test_engine_py_launcher_exists_and_importable() -> None:
    launcher_path = Path(__file__).resolve().parents[1] / "engine.py"
    assert launcher_path.exists()

    spec = importlib.util.spec_from_file_location("engine_launcher", launcher_path)
    assert spec is not None
    assert spec.loader is not None
