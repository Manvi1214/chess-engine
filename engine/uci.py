from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import time
from typing import Callable

import chess

from engine.search import (
    find_best_move_alpha_beta_with_stats,
    search_with_time_controls,
)
from engine.tt import TranspositionTable


@dataclass(frozen=True)
class GoParams:
    movetime_ms: int | None = None
    wtime_ms: int | None = None
    btime_ms: int | None = None
    winc_ms: int = 0
    binc_ms: int = 0
    depth: int = 64
    depth_limited: bool = False
    infinite: bool = False


class UCIEngine:
    def __init__(
        self,
        output_func: Callable[[str], None] | None = None,
        log_file_path: str | None = None,
    ) -> None:
        self.board = chess.Board()
        self.running = True
        self.hash_mb = 64
        self.tt = TranspositionTable(max_entries=self._hash_mb_to_entries(self.hash_mb))

        self._output_func = output_func if output_func is not None else self._stdout_output
        self._search_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._search_state_lock = threading.Lock()
        self._active_search_token = 0
        self._log_lock = threading.Lock()
        self._log_file_path = Path(log_file_path) if log_file_path else None

    def _next_search_token(self) -> int:
        with self._search_state_lock:
            self._active_search_token += 1
            return self._active_search_token

    def _current_search_token(self) -> int:
        with self._search_state_lock:
            return self._active_search_token

    def _is_search_token_active(self, token: int) -> bool:
        return token == self._current_search_token()

    @staticmethod
    def _hash_mb_to_entries(hash_mb: int) -> int:
        # Rough estimate: around 64 bytes per entry in Python object overhead context.
        return max(1, (hash_mb * 1024 * 1024) // 64)

    @staticmethod
    def _stdout_output(line: str) -> None:
        sys.stdout.write(f"{line}\n")
        sys.stdout.flush()

    def _emit(self, line: str) -> None:
        self._output_func(line)

    def _log(self, message: str) -> None:
        if self._log_file_path is None:
            return

        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        line = f"{timestamp} {message}\n"
        with self._log_lock:
            self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_file_path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def stop_search(self, wait: bool = True, cancel_output: bool = False) -> None:
        if cancel_output:
            # Invalidate any in-flight worker output from a search we are abandoning.
            self._next_search_token()

        self._stop_event.set()
        thread = self._search_thread
        if wait and thread is not None and thread.is_alive():
            thread.join()
        if thread is not None and not thread.is_alive():
            self._search_thread = None

    def wait_for_search(self, timeout: float = 2.0) -> bool:
        thread = self._search_thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        done = not thread.is_alive()
        if done:
            self._search_thread = None
        return done

    def _parse_setoption(self, tokens: list[str]) -> None:
        lower_tokens = [token.lower() for token in tokens]
        if "name" not in lower_tokens:
            return

        name_idx = lower_tokens.index("name") + 1
        value_idx = lower_tokens.index("value") if "value" in lower_tokens else len(tokens)
        name = " ".join(tokens[name_idx:value_idx]).strip().lower()
        value_text = " ".join(tokens[value_idx + 1 :]).strip() if value_idx < len(tokens) else ""

        if name == "logfile":
            if value_text:
                self._log_file_path = Path(value_text)
                self._log("log file enabled")
            return

        if name != "hash":
            return

        try:
            hash_mb = int(value_text)
        except ValueError:
            return

        if hash_mb < 1:
            return

        self.hash_mb = hash_mb
        self.tt = TranspositionTable(max_entries=self._hash_mb_to_entries(hash_mb))
        self._log(f"set hash to {hash_mb} MB")

    def _parse_go(self, tokens: list[str]) -> GoParams:
        params: dict[str, int | bool | None] = {
            "movetime_ms": None,
            "wtime_ms": None,
            "btime_ms": None,
            "winc_ms": 0,
            "binc_ms": 0,
            "depth": 64,
            "depth_limited": False,
            "infinite": False,
        }

        i = 0
        while i < len(tokens):
            token = tokens[i].lower()
            if token == "infinite":
                params["infinite"] = True
                i += 1
                continue

            if token in {"movetime", "wtime", "btime", "winc", "binc", "depth"} and i + 1 < len(tokens):
                try:
                    value = int(tokens[i + 1])
                except ValueError:
                    i += 2
                    continue

                if token == "movetime":
                    params["movetime_ms"] = value
                elif token == "wtime":
                    params["wtime_ms"] = value
                elif token == "btime":
                    params["btime_ms"] = value
                elif token == "winc":
                    params["winc_ms"] = value
                elif token == "binc":
                    params["binc_ms"] = value
                elif token == "depth":
                    params["depth"] = max(1, value)
                    params["depth_limited"] = True
                i += 2
                continue

            i += 1

        return GoParams(
            movetime_ms=params["movetime_ms"],
            wtime_ms=params["wtime_ms"],
            btime_ms=params["btime_ms"],
            winc_ms=int(params["winc_ms"]),
            binc_ms=int(params["binc_ms"]),
            depth=int(params["depth"]),
            depth_limited=bool(params["depth_limited"]),
            infinite=bool(params["infinite"]),
        )

    def _apply_position(self, tokens: list[str]) -> None:
        if not tokens:
            return

        if tokens[0].lower() == "startpos":
            board = chess.Board()
            move_tokens = []
            if len(tokens) > 1 and tokens[1].lower() == "moves":
                move_tokens = tokens[2:]
        elif tokens[0].lower() == "fen":
            moves_index = next((i for i, t in enumerate(tokens) if t.lower() == "moves"), len(tokens))
            fen_text = " ".join(tokens[1:moves_index])
            try:
                board = chess.Board(fen_text)
            except ValueError:
                return
            move_tokens = tokens[moves_index + 1 :] if moves_index < len(tokens) else []
        else:
            return

        for move_uci in move_tokens:
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                return
            if move not in board.legal_moves:
                return
            board.push(move)

        self.board = board

    def _emit_info(self, depth: int, score: int, nodes: int, elapsed_sec: float) -> None:
        ms = max(1, int(elapsed_sec * 1000.0))
        nps = int(nodes / max(elapsed_sec, 1e-6))
        self._emit(f"info depth {depth} score cp {score} nodes {nodes} time {ms} nps {nps}")

    def _search_worker(self, board: chess.Board, params: GoParams, token: int) -> None:
        try:
            if params.infinite:
                start = time.monotonic()
                best_move: chess.Move | None = None
                best_score = 0
                depth = 1
                while not self._stop_event.is_set():
                    # Use short chunks so stop stays responsive and info lines update frequently.
                    result = search_with_time_controls(
                        board,
                        max_depth=depth,
                        movetime_ms=200,
                        tt=self.tt,
                    )
                    if result.best_move is not None:
                        best_move = result.best_move
                        best_score = result.score
                    if not self._is_search_token_active(token):
                        return
                    self._emit_info(
                        depth=depth,
                        score=best_score,
                        nodes=result.nodes,
                        elapsed_sec=max(1e-6, time.monotonic() - start),
                    )
                    depth += 1

                if not self._is_search_token_active(token):
                    return
                self._emit(f"bestmove {best_move.uci() if best_move is not None else '0000'}")
                return

            if (
                params.depth_limited
                and params.movetime_ms is None
                and params.wtime_ms is None
                and params.btime_ms is None
            ):
                start = time.monotonic()
                stats = find_best_move_alpha_beta_with_stats(board, depth=params.depth, tt=self.tt)
                elapsed = max(1e-6, time.monotonic() - start)
                self._emit_info(
                    depth=params.depth,
                    score=stats.score,
                    nodes=stats.nodes,
                    elapsed_sec=elapsed,
                )
                if not self._is_search_token_active(token):
                    return
                self._emit(f"bestmove {stats.best_move.uci() if stats.best_move is not None else '0000'}")
                return

            result = search_with_time_controls(
                board,
                max_depth=params.depth,
                movetime_ms=params.movetime_ms,
                wtime_ms=params.wtime_ms,
                btime_ms=params.btime_ms,
                winc_ms=params.winc_ms,
                binc_ms=params.binc_ms,
                tt=self.tt,
            )
            self._emit_info(
                depth=result.depth_reached,
                score=result.score,
                nodes=result.nodes,
                elapsed_sec=max(1e-6, result.time_spent_sec),
            )
            if not self._is_search_token_active(token):
                return
            self._emit(f"bestmove {result.best_move.uci() if result.best_move is not None else '0000'}")
        finally:
            if self._is_search_token_active(token):
                self._search_thread = None

    def _start_search(self, params: GoParams) -> None:
        self.stop_search(wait=True, cancel_output=True)
        self._stop_event.clear()
        self._log(f"go command: {params}")

        board_copy = self.board.copy(stack=False)
        token = self._next_search_token()
        worker = threading.Thread(target=self._search_worker, args=(board_copy, params, token), daemon=True)
        self._search_thread = worker
        worker.start()

    def handle_command(self, line: str) -> None:
        text = line.strip()
        if not text:
            return
        self._log(f"<= {text}")

        parts = text.split()
        cmd = parts[0].lower()

        if cmd == "uci":
            self._emit("id name ChessEnginePython")
            self._emit("id author onlys")
            self._emit("option name Hash type spin default 64 min 1 max 2048")
            self._emit("option name LogFile type string default")
            self._emit("uciok")
            return

        if cmd == "isready":
            self._emit("readyok")
            return

        if cmd == "setoption":
            self._parse_setoption(parts[1:])
            return

        if cmd == "ucinewgame":
            self.stop_search(wait=True, cancel_output=True)
            self.board = chess.Board()
            self.tt.clear()
            return

        if cmd == "position":
            self.stop_search(wait=True, cancel_output=True)
            self._apply_position(parts[1:])
            return

        if cmd == "go":
            params = self._parse_go(parts[1:])
            self._start_search(params)
            return

        if cmd == "stop":
            self.stop_search(wait=True)
            return

        if cmd == "quit":
            self.stop_search(wait=True, cancel_output=True)
            self.running = False
            self._log("engine quitting")
            return

    def run_loop(self) -> None:
        while self.running:
            line = sys.stdin.readline()
            if not line:
                break
            self.handle_command(line)


def main() -> None:
    UCIEngine().run_loop()


if __name__ == "__main__":
    main()
