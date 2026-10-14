from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a basic UCI compliance smoke sequence.")
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python executable to use (default: current interpreter).",
    )
    parser.add_argument(
        "--engine-module",
        type=str,
        default="engine.uci",
        help="Engine module path for python -m <module>.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="Overall timeout for the smoke run in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    commands = "\n".join(
        [
            "uci",
            "isready",
            "ucinewgame",
            "position startpos moves e2e4 e7e5",
            "go movetime 100",
            "stop",
            "isready",
            "quit",
            "",
        ]
    )

    try:
        completed = subprocess.run(
            [args.python, "-m", args.engine_module],
            input=commands,
            text=True,
            capture_output=True,
            cwd=str(root),
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: engine process timed out")
        return 1

    if completed.returncode != 0:
        print(f"FAIL: engine exited with code {completed.returncode}")
        if completed.stderr.strip():
            print("stderr:")
            print(completed.stderr.strip())
        return 1

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]

    required_checks = {
        "uciok": any(line == "uciok" for line in lines),
        "readyok": any(line == "readyok" for line in lines),
        "bestmove": any(line.startswith("bestmove ") for line in lines),
        "info": any(line.startswith("info depth ") for line in lines),
    }

    missing = [name for name, ok in required_checks.items() if not ok]
    if missing:
        print(f"FAIL: missing expected responses: {', '.join(missing)}")
        print("stdout:")
        print(completed.stdout)
        return 1

    print("PASS: UCI smoke sequence completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
