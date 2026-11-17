import numpy as np
import pytest
from src.planner import astar, bfs_path, path_cost, step_cell, strips, zigzag_order
from src.world import Field, generate_obstacles

G, S = (14, 4), (14, 10)
STARTS = [(0, 0), (0, 5), (0, 10)]


def rand_field(seed, density=0.10):
    obs = generate_obstacles(15, density, np.random.default_rng(seed), STARTS, G, S)
    return Field(15, G, S, obs)


def walk(field, start, actions):
    cell = start
    for a in actions:
        cell = step_cell(cell, a)
        assert field.passable(cell)
    return cell


@pytest.mark.parametrize("seed", range(5))
def test_astar_optimo_igual_a_dijkstra_y_ruta_valida(seed):
    f, rng = rand_field(seed), np.random.default_rng(100 + seed)
    free = [(r, c) for r in range(15) for c in range(15) if (r, c) not in f.obstacles]
    for _ in range(12):
        a, b = free[rng.integers(len(free))], free[rng.integers(len(free))]
        d = "NSEO"[rng.integers(4)]
        acts, cells, cost = astar(f, a, d, b)
        assert walk(f, a, acts) == b
        assert cost == pytest.approx(f.min_cost(a, d, b))
        assert cost == pytest.approx(path_cost(acts, d))
        bfs = bfs_path(f, a, b)
        assert len(bfs) <= len(acts) and cost <= path_cost(bfs, d) + 1e-9


def test_costos_con_vueltas():
    f = Field(15, G, S)
    assert astar(f, (0, 0), "E", (0, 4))[2] == 4.0       # recto
    assert astar(f, (0, 0), "S", (0, 4))[2] == 4.5       # una vuelta inicial
    assert astar(f, (0, 0), "S", (3, 3))[2] == 6.5       # una sola vuelta (en L)


def test_sin_ruta_y_avoid():
    f = Field(15, G, S, {(4, 5), (6, 5), (5, 4), (5, 6)})  # (5,5) encerrada
    assert astar(f, (0, 0), "S", (5, 5)) is None and bfs_path(f, (0, 0), (5, 5)) is None
    g = Field(15, G, S)
    acts, cells, _ = astar(g, (0, 0), "E", (0, 3), avoid=frozenset({(0, 1)}))
    assert (0, 1) not in cells and walk(g, (0, 0), acts) == (0, 3)


def test_franjas_y_zigzag_sin_obstaculos():
    f = Field(15, G, S)
    cols = strips(15, 3)
    assert cols == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14]]
    orders = [zigzag_order(c, f) for c in cols]
    assert [len(o) for o in orders] == [74, 75, 74]
    allc = [c for o in orders for c in o]
    assert len(allc) == len(set(allc)) == 223 and set(allc) == set(f.sowable)
    for o in orders:
        assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 2 for a, b in zip(o, o[1:]))
    assert orders[0][:2] == [(0, 0), (1, 0)] and orders[0][15] == (14, 1)   # baja y luego sube


@pytest.mark.parametrize("seed", range(5))
def test_zigzag_cubre_todo_con_obstaculos(seed):
    f = rand_field(seed)
    allc = [c for cols in strips(15, 3) for c in zigzag_order(cols, f)]
    assert len(allc) == len(set(allc)) and set(allc) == set(f.sowable)
