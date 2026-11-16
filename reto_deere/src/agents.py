"""Agente tractor. Esta versión implementa la LÍNEA BASE (sin blackboard):
cada tractor siembra solo su franja en zigzag y es reactivo con los recursos.

Percepción de la línea base (explícita para que la comparación sea justa):
- Conoce el mapa y las rocas.
- Ve si la estación a la que va está ocupada (espera a que se libere).
- Ve a los tractores ya terminados (estacionados) y los esquiva.
- NO conoce las intenciones de los demás: dos tractores pueden entrar a la misma
  celda o cruzarse, y el motor lo cuenta como colisión.
- Recarga solo cuando C5 lo exige (combustible) o cuando se queda sin semillas.
"""
import agentpy as ap
from .planner import astar


class TractorAgent(ap.Agent):
    def setup(self):
        self.tid = None          # 1..n, lo asigna el modelo
        self.order = []          # celdas de su franja en orden de zigzag
        self.ptr = 0
        self.goal = None         # None | "G" | "S"
        self.dest = None
        self.path = []           # [(acción, celda_siguiente)]
        self.path_pos = None     # celda desde la que arranca self.path

    # ---------- acceso al mundo ----------
    @property
    def world(self):
        return self.model.world

    @property
    def tractor(self):
        return self.world.tractors[self.tid - 1]

    # ---------- ganchos que la arquitectura mejorada sobrescribirá ----------
    def avoid_cells(self) -> frozenset:
        return frozenset(t.pos for t in self.world.tractors
                         if t is not self.tractor and t.mode == "terminado")

    def blocked_next(self, nxt) -> bool:
        w = self.world
        if nxt not in (w.field.gas, w.field.seed_station):
            return False
        return any(t.pos == nxt for t in w.tractors if t is not self.tractor)

    # ---------- decisión ----------
    def decide(self) -> str:
        w, tr, f = self.world, self.tractor, self.world.field
        if tr.mode == "terminado":
            return "esperar"
        if w.needs_refuel(tr):                       # C5 siempre manda
            self.goal = "G"
        elif self.goal is None and tr.seeds < 1:
            self.goal = "S"
        if self.goal:
            station = f.gas if self.goal == "G" else f.seed_station
            if tr.pos == station:
                g, self.goal = self.goal, None
                return "cargar_" + g
            return self._go(station)
        cell = self._next_cell()
        if cell is None:
            w.finish(tr)
            return "esperar"
        return "sembrar" if tr.pos == cell else self._go(cell)

    def _next_cell(self):
        M = self.world.M
        while self.ptr < len(self.order) and M[self.order[self.ptr]]:
            self.ptr += 1
        return self.order[self.ptr] if self.ptr < len(self.order) else None

    def _go(self, dest) -> str:
        w, tr = self.world, self.tractor
        c = w.p["costs"]
        if dest != self.dest or not self.path or self.path_pos != tr.pos:
            res = astar(w.field, tr.pos, tr.direction, dest, c["move"], c["turn"], self.avoid_cells())
            if res is None:
                res = astar(w.field, tr.pos, tr.direction, dest, c["move"], c["turn"])
            if res is None:
                return "esperar"
            self.dest, self.path_pos = dest, tr.pos
            self.path = list(zip(res[0], res[1]))
        if not self.path:
            return "esperar"
        act, nxt = self.path[0]
        if self.blocked_next(nxt):
            return "esperar"
        self.path.pop(0)
        self.path_pos = nxt
        return act
