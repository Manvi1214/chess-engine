# Chess Engine

A Python chess engine with UCI support, classical search, static evaluation, and development tools.

## Features

- UCI protocol support for chess GUIs and tournament managers
- Negamax search with alpha-beta pruning
- Quiescence search and iterative deepening
- Transposition table with bound flags and depth-preferred replacement
- Move ordering with capture scoring, killer moves, history scores, and null-move pruning
- Static evaluation with material, piece-square tables, tapered scoring, and mobility
- Utility scripts for UCI smoke tests, puzzle checks, self-play, benchmarking, and PGN reports

## Requirements

- Python 3.10+
- `python-chess`
- `pytest`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Usage

Play against the engine in your browser (Web GUI):

```bash
python tools/web_gui.py --port 8000
```
Then open `http://localhost:8000` in your web browser.

Play against the engine in your terminal:

```bash
python tools/play.py --color white --depth 4
```

Run the UCI engine (for chess GUIs like Arena, Cutechess, or Banksia):

```bash
python -m engine.uci
# or
python engine.py
# macOS / Linux launcher:
./run_myengine.sh
# Windows launcher:
run_myengine.bat
```

Run the UCI smoke test:

```bash
python tools/uci_smoke.py
```

## Development

Run the test suite:

```bash
python -m pytest -q
```

Run a search benchmark:

```bash
python tools/search_benchmark.py --depth 4 --tt --tt-size 100000
```

Run the puzzle suite:

```bash
python tools/run_puzzles.py --depth 2 --show-failures
```

Generate self-play games:

```bash
python tools/selfplay.py --games 20 --white-depth 3 --black-depth 4 --white-movetime 80 --black-movetime 80 --pgnout selfplay_match.pgn
```

Create a PGN quality report:

```bash
python tools/match_report.py --pgn selfplay_match.pgn
```

## Project Layout

- `engine/`: engine implementation (search, evaluation, transposition table, UCI protocol)
- `web/`: modern browser chessboard GUI
- `tools/`: command-line and web utilities (`play.py`, `web_gui.py`, `uci_smoke.py`, `run_puzzles.py`, etc.)
- `tests/`: pytest suite
- `engine.py`: launcher entry point
- `run_myengine.sh`: macOS/Linux launcher for UCI GUIs
- `run_myengine.bat`: Windows launcher for UCI GUIs
