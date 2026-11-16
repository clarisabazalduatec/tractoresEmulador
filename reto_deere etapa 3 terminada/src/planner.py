"""Planeación de rutas (BFS y A* con costo de vueltas) y barrido en zigzag por franja.

Complejidad: BFS O(V+E) = O(V) con V = n² celdas (ignora vueltas). A* trabaja sobre
estados (celda, dirección): 4V estados, O(E log V) en el peor caso; con la heurística
Manhattan expande muchos menos nodos. La heurística es consistente porque cada paso
cuesta >= `move`, así que el primer pop de la meta es óptimo.
"""
from __future__ import annotations
import heapq
import itertools
from collections import deque
import numpy as np
from .world import DIRS, Field


def astar(field: Field, start, direction, goal, move=1.0, turn=0.5, avoid=frozenset()):
    """Devuelve (acciones, celdas, costo) o None si no hay ruta. `avoid` = celdas vetadas."""
    if start == goal:
        return [], [], 0.0
    h = lambda c: move * (abs(c[0] - goal[0]) + abs(c[1] - goal[1]))
    tie = itertools.count()
    heap = [(h(start), 0.0, next(tie), start, direction)]
    best, parent = {(start, direction): 0.0}, {}
    while heap:
        _, g, _, cell, d = heapq.heappop(heap)
        if g > best.get((cell, d), float("inf")):
            continue
        if cell == goal:
            acts, cells, key = [], [], (cell, d)
            while key in parent:
                acts.append(key[1])
                cells.append(key[0])
                key = parent[key]
            return acts[::-1], cells[::-1], g
        for nd, nxt in field.neighbors(cell):
            if nxt in avoid:
                continue
            ng = g + move + (turn if nd != d else 0.0)
            if ng < best.get((nxt, nd), float("inf")):
                best[(nxt, nd)] = ng
                parent[(nxt, nd)] = (cell, d)
                heapq.heappush(heap, (ng + h(nxt), ng, next(tie), nxt, nd))
    return None


def bfs_path(field: Field, start, goal, avoid=frozenset()):
    """Ruta con el menor número de pasos (no considera vueltas). Línea de comparación para A*."""
    if start == goal:
        return []
    prev, q = {start: None}, deque([start])
    while q:
        cur = q.popleft()
        for d, nxt in field.neighbors(cur):
            if nxt in prev or nxt in avoid:
                continue
            prev[nxt] = (cur, d)
            if nxt == goal:
                acts = []
                while prev[nxt]:
                    nxt, a = prev[nxt][0], prev[nxt][1]
                    acts.append(a)
                return acts[::-1]
            q.append(nxt)
    return None


def path_cost(actions, direction, move=1.0, turn=0.5) -> float:
    cost = 0.0
    for a in actions:
        cost += move + (turn if a != direction else 0.0)
        direction = a
    return cost


def step_cell(cell, action):
    return (cell[0] + DIRS[action][0], cell[1] + DIRS[action][1])


def strips(size: int, n: int) -> list:
    """Franjas de columnas contiguas (15 columnas, 3 tractores -> 5 columnas cada uno)."""
    return [[int(c) for c in cols] for cols in np.array_split(np.arange(size), n)]


def zigzag_order(columns, field: Field, first_down=True) -> list:
    """Barrido en zigzag por columnas: baja una columna, sube la siguiente, etc.
    Menos vueltas que barrer por filas (2 por cambio de columna). Omite rocas y estaciones."""
    order, down = [], first_down
    for c in columns:
        rows = range(field.size) if down else range(field.size - 1, -1, -1)
        order += [(r, c) for r in rows if (r, c) in field.sowable]
        down = not down
    return order
