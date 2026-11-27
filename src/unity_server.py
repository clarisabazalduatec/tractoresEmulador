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
        start_mode: str = "fixed",
        q_learning: bool | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self.max_ticks = int(max_ticks)
        self.q_policies_path = Path(q_policies_path) if q_policies_path is not None else None
        self.architecture = architecture
        self.density = float(density)
        self.seed = int(seed)
        self.start_mode = start_mode
        self.q_learning = (self.q_policies_path is not None if q_learning is None
                           else q_learning)
        self.model, self.scenario = self._build_episode(
            self.architecture, self.density, self.seed, self.start_mode, self.q_learning
        )

    def _build_episode(self, architecture: str, density: float, seed: int,
                       start_mode: str, q_learning: bool):
        params: dict[str, Any] = {
            "architecture": architecture,
            "obstacle_density": density,
            "seed": seed,
            "start_mode": start_mode,
        }
        if q_learning:
            if self.q_policies_path is None:
                raise ValueError("Q-learning requiere --q-policies con una política entrenada")
            try:
                from .qlearning import load_policies
            except ModuleNotFoundError as exc:
                if exc.name == "src.qlearning":
                    raise RuntimeError("Q-learning aún no está disponible en esta versión del modelo") from exc
                raise
            params["q_enabled"] = True
            params["q_policies"] = load_policies(self.q_policies_path)

        model = FarmModel(params)
        model.sim_setup(steps=self.max_ticks, seed=seed)
        scenario = {
            "architecture": architecture,
            "density": density,
            "obstacle_density": density,
            "seed": seed,
            "start_mode": start_mode,
            "initial_positions": start_mode,
            "q_learning": q_learning,
            "max_ticks": self.max_ticks,
        }
        return model, scenario

    def reset(self, *, density: float | None = None, seed: int | None = None,
              start_mode: str | None = None, q_learning: bool | None = None,
              architecture: str | None = None) -> dict[str, Any]:
        """Replace the episode and return its actual tick-zero snapshot."""
        with self._lock:
            next_architecture = self.architecture if architecture is None else architecture
            next_density = self.density if density is None else density
            next_seed = self.seed if seed is None else seed
            next_start_mode = self.start_mode if start_mode is None else start_mode
            next_q_learning = self.q_learning if q_learning is None else q_learning
            if isinstance(next_density, bool) or not isinstance(next_density, (int, float)):
                raise ValueError("density debe ser numérica")
            if isinstance(next_seed, bool) or not isinstance(next_seed, int):
                raise ValueError("seed debe ser un entero")
            if not isinstance(next_q_learning, bool):
                raise ValueError("q_learning debe ser booleano")
            if next_start_mode not in ("fixed", "random"):
                raise ValueError("start_mode debe ser 'fixed' o 'random'")

            next_density = float(next_density)
            model, scenario = self._build_episode(
                next_architecture, next_density, next_seed,
                next_start_mode, next_q_learning,
            )
            self.architecture = next_architecture
            self.density = next_density
            self.seed = next_seed
            self.start_mode = next_start_mode
            self.q_learning = next_q_learning
            self.model, self.scenario = model, scenario
            return self._snapshot_unlocked()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> dict[str, Any]:
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
            return self._snapshot_unlocked()


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
            if route not in ("/step", "/reset"):
                self._respond(404, {"error": "ruta no encontrada"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(content_length) if content_length else b""
                if route == "/step":
                    self._respond(200, session.step())
                    return
                payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
                if not isinstance(payload, dict):
                    raise ValueError("el cuerpo de /reset debe ser un objeto JSON")
                snapshot = session.reset(
                    density=payload.get("density", payload.get("obstacle_density")),
                    seed=payload.get("seed"),
                    start_mode=payload.get("start_mode", payload.get("initial_positions")),
                    q_learning=payload.get("q_learning"),
                    architecture=payload.get("architecture"),
                )
                self._respond(200, snapshot)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
                self._respond(400, {"error": str(exc)})
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
    parser.add_argument("--start-mode", choices=("fixed", "random"), default="fixed",
                        help="posiciones iniciales fijas o aleatorias")
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
        start_mode=args.start_mode,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(session))
    print(
        f"Unity bridge en http://{args.host}:{args.port} | "
        f"arquitectura={args.architecture}, densidad={args.density:.0%}, seed={args.seed}, "
        f"inicio={args.start_mode}; GET /state no avanza; POST /step avanza un tick; "
        "POST /reset inicia un episodio. Ctrl+C para detener."
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
