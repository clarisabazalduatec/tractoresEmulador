"""Campo, obstáculos, estaciones y rutas de costo mínimo. Coordenadas = (fila, columna)."""
from __future__ import annotations
import heapq
from functools import lru_cache
from collections import deque
import numpy as np
import yaml

DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1)}


def validate_params(p: dict) -> None:
    f, t, c = p["field"], p["tractors"], p["costs"]
    n = f["size"]
    if not isinstance(n, int) or n < 2:
        raise ValueError("field.size debe ser entero >= 2")
    if not 0.0 <= f["obstacle_density"] < 0.5:
        raise ValueError("obstacle_density debe estar en [0, 0.5)")
    stations = [tuple(f["gas_station"]), tuple(f["seed_station"])]
    starts = [tuple(s) for s in t["starts"]]
    for cell in stations + starts:
        if not (0 <= cell[0] < n and 0 <= cell[1] < n):
            raise ValueError(f"celda fuera del campo: {cell}")
    if len(set(stations + starts)) != len(stations) + len(starts):
        raise ValueError("estaciones y posiciones iniciales deben ser distintas")
    if len(starts) != t["count"]:
        raise ValueError("tractors.count debe coincidir con len(starts)")
    if t["initial_direction"] not in DIRS:
        raise ValueError("initial_direction debe ser N, S, E u O")
    if t["seed_capacity"] <= 0 or t["fuel_capacity"] <= 0:
        raise ValueError("capacidades deben ser positivas")
    if min(c.values()) < 0:
        raise ValueError("los costos no pueden ser negativos")


def load_params(path) -> dict:
    with open(path, encoding="utf-8") as fh:
        p = yaml.safe_load(fh)
    validate_params(p)
    return p


class Field:
    def __init__(self, size, gas, seed_station, obstacles=()):
        self.size = size
        self.gas = tuple(gas)
        self.seed_station = tuple(seed_station)
        self.obstacles = frozenset(tuple(o) for o in obstacles)
        for s in (self.gas, self.seed_station):
            if not self.in_bounds(s) or s in self.obstacles:
                raise ValueError(f"estación inválida: {s}")
        stations = {self.gas, self.seed_station}
        self.sowable = frozenset(
            (r, c) for r in range(size) for c in range(size)
            if (r, c) not in self.obstacles and (r, c) not in stations)

    def in_bounds(self, cell):
        return 0 <= cell[0] < self.size and 0 <= cell[1] < self.size

    def passable(self, cell):
        return self.in_bounds(cell) and cell not in self.obstacles

    def neighbors(self, cell):
        for d, (dr, dc) in DIRS.items():
            nxt = (cell[0] + dr, cell[1] + dc)
            if self.passable(nxt):
                yield d, nxt

    def bfs_dist(self, src) -> dict:
        dist, q = {src: 0}, deque([src])
        while q:
            cur = q.popleft()
            for _, nxt in self.neighbors(cur):
                if nxt not in dist:
                    dist[nxt] = dist[cur] + 1
                    q.append(nxt)
        return dist

    def is_connected(self) -> bool:
        free = [(r, c) for r in range(self.size) for c in range(self.size)
                if (r, c) not in self.obstacles]
        return len(self.bfs_dist(free[0])) == len(free)

    @lru_cache(maxsize=12000)
    def min_cost(self, src, direction, dst, move=1.0, turn=0.5) -> float:
        """Dijkstra sobre (celda, dirección): costo mínimo incluyendo vueltas."""
        heap, best = [(0.0, src, direction)], {(src, direction): 0.0}
        while heap:
            cost, cell, d = heapq.heappop(heap)
            if cell == dst:
                return cost
            if cost > best.get((cell, d), float("inf")):
                continue
            for nd, nxt in self.neighbors(cell):
                nc = cost + move + (turn if nd != d else 0.0)
                if nc < best.get((nxt, nd), float("inf")):
                    best[(nxt, nd)] = nc
                    heapq.heappush(heap, (nc, nxt, nd))
        return float("inf")


def generate_obstacles(size, density, rng, protected, gas, seed_station, max_attempts=500):
    """Rocas aleatorias (con semilla) que nunca tocan inicios ni estaciones y
    dejan el campo conectado; si no, se regenera."""
    n_obs = int(round(density * size * size))
    if n_obs == 0:
        return frozenset()
    blocked = {tuple(c) for c in protected} | {tuple(gas), tuple(seed_station)}
    candidates = [(r, c) for r in range(size) for c in range(size) if (r, c) not in blocked]
    for _ in range(max_attempts):
        idx = rng.choice(len(candidates), size=n_obs, replace=False)
        obs = frozenset(candidates[i] for i in idx)
        if Field(size, gas, seed_station, obs).is_connected():
            return obs
    raise RuntimeError("no se pudo generar un mapa conectado; baja la densidad")


def build_field(params: dict, rng=None, obstacles=None) -> Field:
    f = params["field"]
    if obstacles is None:
        rng = rng if rng is not None else np.random.default_rng(params["sim"]["base_seed"])
        obstacles = generate_obstacles(f["size"], f["obstacle_density"], rng,
                                       params["tractors"]["starts"],
                                       f["gas_station"], f["seed_station"])
    return Field(f["size"], f["gas_station"], f["seed_station"], obstacles)
