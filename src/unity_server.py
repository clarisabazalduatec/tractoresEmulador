"""HTTP adapter for visualizing the live AgentPy simulation in Unity.

This module only serializes the existing model and advances it one tick on
request. Decisions, coordination, navigation, and world rules remain in the
model classes.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from urllib.parse import urlparse

from .model import FarmModel


class SimulationSession:
    """Own one reproducible model instance and expose stable JSON snapshots."""

    def __init__(
        self,
        architecture: str = "improved",
        density: float = 0.10,
        seed: int = 0,
        max_ticks: int = 3000,
        q_policies_path: str | Path | None = None,
    ) -> None:
        params: dict[str, Any] = {
            "architecture": architecture,
            "obstacle_density": density,
            "seed": seed,
        }
        if q_policies_path is not None:
            try:
                from .qlearning import load_policies
            except ModuleNotFoundError as exc:
                if exc.name == "src.qlearning":
                    raise RuntimeError("Q-learning aún no está disponible en esta versión del modelo") from exc
                raise

            params["q_enabled"] = True
            params["q_policies"] = load_policies(q_policies_path)

        self.model = FarmModel(params)
        self.model.sim_setup(steps=max_ticks, seed=seed)
        self.scenario = {
            "architecture": architecture,
            "obstacle_density": density,
            "seed": seed,
            "q_learning": q_policies_path is not None,
        }
        self._lock = threading.RLock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            world = self.model.world
            field = world.field
            sowable_count = len(field.sowable)
            planted = [
                {"row": int(row), "col": int(col)}
                for row, col in zip(*world.M.nonzero())
            ]
            coverage = 100.0 * len(planted) / sowable_count if sowable_count else 100.0
            complete = world.is_done()
            finished = complete or world.t >= self.model.cfg["sim"]["max_ticks"] or not self.model.running
            return {
                "schema_version": 1,
                "scenario": dict(self.scenario),
                "tick": int(world.t),
                "complete": bool(complete),
                "finished": bool(finished),
                "field": {
                    "rows": int(field.size),
                    "columns": int(field.size),
                    "coordinate_order": ["row", "col"],
                    "obstacles": [
                        {"row": int(row), "col": int(col)}
                        for row, col in sorted(field.obstacles)
                    ],
                    "stations": {
                        "gas": {"row": int(field.gas[0]), "col": int(field.gas[1])},
                        "seeds": {
                            "row": int(field.seed_station[0]),
                            "col": int(field.seed_station[1]),
                        },
                    },
                    "sowable_count": int(sowable_count),
                },
                "planted": planted,
                "tractors": [
                    {
                        "id": int(tractor.id),
                        "row": int(tractor.pos[0]),
                        "col": int(tractor.pos[1]),
                        "direction": tractor.direction,
                        "seeds": float(tractor.seeds),
                        "fuel": float(tractor.fuel),
                        "mode": tractor.mode,
                    }
                    for tractor in world.tractors
                ],
                "metrics": {
                    "coverage_pct": float(coverage),
                    "collisions": int(world.collisions),
                    "rejected_actions": int(world.rejected),
                },
            }

    def step(self) -> dict[str, Any]:
        """Advance exactly one AgentPy tick, then return the resulting state."""
        with self._lock:
            world = self.model.world
            if self.model.running and not world.is_done():
                self.model.sim_step()
            return self.snapshot()


def make_handler(session: SimulationSession):
    class UnityRequestHandler(BaseHTTPRequestHandler):
        def _respond(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            route = urlparse(self.path).path
            if route == "/health":
                self._respond(200, {"status": "ok", "schema_version": 1})
            elif route == "/state":
                self._respond(200, session.snapshot())
            else:
                self._respond(404, {"error": "ruta no encontrada"})

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            route = urlparse(self.path).path
            if route != "/step":
                self._respond(404, {"error": "ruta no encontrada"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length:
                    self.rfile.read(content_length)
                self._respond(200, session.step())
            except Exception as exc:  # keep protocol errors visible to Unity
                self._respond(500, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[unity-http] {self.address_string()} - {format % args}")

    return UnityRequestHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Sirve snapshots del modelo multiagente a Unity.")
    parser.add_argument("--architecture", choices=("baseline", "improved"), default="improved")
    parser.add_argument("--density", type=float, default=0.10, help="densidad de obstáculos [0, 0.5)")
    parser.add_argument("--seed", type=int, default=0, help="semilla reproducible del escenario")
    parser.add_argument("--max-ticks", type=int, default=3000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--q-policies",
        type=Path,
        help="JSON de políticas entrenadas; activa evaluación Q-learning sin explorar",
    )
    args = parser.parse_args()

    session = SimulationSession(
        architecture=args.architecture,
        density=args.density,
        seed=args.seed,
        max_ticks=args.max_ticks,
        q_policies_path=args.q_policies,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(session))
    print(
        f"Unity bridge en http://{args.host}:{args.port} | "
        f"arquitectura={args.architecture}, densidad={args.density:.0%}, seed={args.seed}; "
        "GET /state no avanza; POST /step avanza un tick. Ctrl+C para detener."
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
