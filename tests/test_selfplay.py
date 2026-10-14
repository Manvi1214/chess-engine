from tools.selfplay import EngineConfig, play_single_game


def test_selfplay_game_produces_valid_result() -> None:
    white = EngineConfig(name="Engine_vN", max_depth=2, movetime_ms=20)
    black = EngineConfig(name="Engine_vN1", max_depth=2, movetime_ms=20)

    game = play_single_game(white=white, black=black, game_index=1, max_plies=60)
    result = game.headers.get("Result")

    assert result in {"1-0", "0-1", "1/2-1/2", "*"}
