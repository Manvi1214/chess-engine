from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import chess

try:
    from engine.evaluate import evaluate
    from engine.search import search_with_time_controls
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from engine.evaluate import evaluate
    from engine.search import search_with_time_controls


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"


class GameSession:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.player_color = chess.WHITE
        self.depth = 4
        self.movetime_ms = 400
        self.move_history: list[dict] = []
        self.last_engine_stats: dict | None = None

    def reset(self, player_color: chess.Color = chess.WHITE, depth: int = 4, movetime_ms: int = 400) -> None:
        self.board = chess.Board()
        self.player_color = player_color
        self.depth = depth
        self.movetime_ms = movetime_ms
        self.move_history = []
        self.last_engine_stats = None

        if self.board.turn != self.player_color:
            self.make_engine_move()

    def get_state(self) -> dict:
        legal_moves = []
        for move in self.board.legal_moves:
            legal_moves.append({
                "uci": move.uci(),
                "san": self.board.san(move),
                "from": chess.square_name(move.from_square),
                "to": chess.square_name(move.to_square),
                "promotion": chess.piece_symbol(move.promotion) if move.promotion else None,
            })

        is_mate = self.board.is_checkmate()
        is_stale = self.board.is_stalemate()
        is_insufficient = self.board.is_insufficient_material()
        is_repetition = self.board.can_claim_threefold_repetition()
        is_fifty = self.board.can_claim_fifty_moves()

        game_over = is_mate or is_stale or is_insufficient or is_repetition or is_fifty
        status_text = "Active"
        winner = None

        if is_mate:
            winner = "white" if self.board.turn == chess.BLACK else "black"
            status_text = f"Checkmate! {winner.capitalize()} wins."
        elif is_stale:
            status_text = "Draw by stalemate."
        elif is_insufficient:
            status_text = "Draw by insufficient material."
        elif is_repetition:
            status_text = "Draw by threefold repetition."
        elif is_fifty:
            status_text = "Draw by 50-move rule."
        elif self.board.is_check():
            status_text = "Check!"

        eval_cp = evaluate(self.board)

        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "player_color": "white" if self.player_color == chess.WHITE else "black",
            "is_check": self.board.is_check(),
            "game_over": game_over,
            "status_text": status_text,
            "winner": winner,
            "eval_cp": eval_cp,
            "legal_moves": legal_moves,
            "move_history": self.move_history,
            "last_engine_stats": self.last_engine_stats,
            "depth": self.depth,
            "movetime_ms": self.movetime_ms,
        }

    def make_player_move(self, move_uci: str) -> dict:
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return {"error": f"Invalid move notation '{move_uci}'"}

        if move not in self.board.legal_moves:
            return {"error": f"Illegal move '{move_uci}'"}

        san = self.board.san(move)
        self.board.push(move)
        self.move_history.append({
            "ply": len(self.board.move_stack),
            "by": "player",
            "san": san,
            "uci": move.uci(),
        })

        if not self.board.is_game_over(claim_draw=True) and self.board.turn != self.player_color:
            self.make_engine_move()

        return self.get_state()

    def make_engine_move(self) -> None:
        start_t = time.monotonic()
        result = search_with_time_controls(
            self.board,
            max_depth=self.depth,
            movetime_ms=self.movetime_ms,
        )
        elapsed = time.monotonic() - start_t

        move = result.best_move
        if move is None or move not in self.board.legal_moves:
            move = next(iter(self.board.legal_moves), None)

        if move is not None:
            san = self.board.san(move)
            self.board.push(move)
            self.last_engine_stats = {
                "best_move": move.uci(),
                "san": san,
                "score": result.score,
                "depth_reached": result.depth_reached,
                "nodes": result.nodes,
                "time_sec": round(elapsed, 3),
            }
            self.move_history.append({
                "ply": len(self.board.move_stack),
                "by": "engine",
                "san": san,
                "uci": move.uci(),
                "score": result.score,
            })

    def undo_move(self) -> dict:
        # Undo engine move and player move if possible
        if len(self.board.move_stack) >= 2:
            self.board.pop()
            self.board.pop()
            self.move_history = self.move_history[:-2]
        elif len(self.board.move_stack) == 1:
            self.board.pop()
            self.move_history = self.move_history[:-1]
        self.last_engine_stats = None
        return self.get_state()

    def get_hint(self) -> dict:
        if self.board.is_game_over(claim_draw=True):
            return {"error": "Game is already over"}
        result = search_with_time_controls(
            self.board,
            max_depth=self.depth,
            movetime_ms=self.movetime_ms,
        )
        if result.best_move:
            return {
                "hint_uci": result.best_move.uci(),
                "hint_san": self.board.san(result.best_move),
                "score": result.score,
                "depth": result.depth_reached,
            }
        return {"error": "No hint available"}


session = GameSession()


class ChessRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._send_json(session.get_state())
        elif parsed.path == "/api/hint":
            self._send_json(session.get_hint())
        elif parsed.path == "/api/status":
            self._send_json({"name": "ChessEnginePython", "ready": True})
        else:
            super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        data = json.loads(body) if body else {}

        if parsed.path == "/api/move":
            move_uci = data.get("move", "")
            res = session.make_player_move(move_uci)
            self._send_json(res)
        elif parsed.path == "/api/new":
            player_color = chess.WHITE if data.get("color", "white") == "white" else chess.BLACK
            depth = int(data.get("depth", 4))
            movetime = int(data.get("movetime", 400))
            session.reset(player_color=player_color, depth=depth, movetime_ms=movetime)
            self._send_json(session.get_state())
        elif parsed.path == "/api/undo":
            self._send_json(session.undo_move())
        else:
            self.send_error(404, "Not Found")

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        # Suppress noisy standard request logging
        pass


import socket


class DualStackThreadingServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def run_server(port: int = 8000) -> None:
    try:
        httpd = DualStackThreadingServer(("::", port), ChessRequestHandler)
    except OSError:
        # Fallback to IPv4 standard server if IPv6 is not available
        httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), ChessRequestHandler)

    print("=" * 60)
    print(f" ♚ CHESS ENGINE WEB GUI RUNNING ♚")
    print(f" URL: http://localhost:{port} (or http://127.0.0.1:{port})")
    print(" Press Ctrl+C to stop the server")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Chess Engine Web GUI server.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args()
    run_server(port=args.port)
