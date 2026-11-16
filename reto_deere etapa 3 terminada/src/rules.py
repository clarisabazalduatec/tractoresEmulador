"""Motor de reglas: transición del sistema y restricciones C1-C6.

Cada tick recibe una acción por tractor, valida, resuelve conflictos de forma
simultánea y aplica la transición. No decide qué acción conviene (eso es de los agentes).
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
import numpy as np
from .state import ACTIONS, Tractor
from .world import DIRS, Field


@dataclass
class Outcome:
    tractor: int
    action: str
    status: str        # ok | rechazada | bloqueada | inactivo
    reason: str = ""


class WorldState:
    def __init__(self, field: Field, params: dict, rng=None):
        self.field, self.p = field, params
        self.rng = rng if rng is not None else np.random.default_rng(params["sim"]["base_seed"])
        n = field.size
        self.M = np.zeros((n, n), dtype=np.int8)            # M(t): 1 = sembrada
        self.sow_count = np.zeros((n, n), dtype=np.int16)   # para medir resiembras reales
        t = params["tractors"]
        self.tractors = [
            Tractor(id=i + 1, pos=tuple(s), direction=t["initial_direction"],
                    seeds=t["seed_capacity"], fuel=t["fuel_capacity"])
            for i, s in enumerate(t["starts"])]
        self.R: dict = {}                                    # R(t): siguiente celda reservada
        self.O = {"G": None, "S": None}                      # O(t): ocupante de cada estación
        self.t = 0
        self.collisions = 0
        self.conflicts_blocked = 0
        self.rejected = 0
        self.log: list = []

    # ---------- consultas ----------
    def is_done(self) -> bool:
        return int(self.M.sum()) == len(self.field.sowable)

    def needs_refuel(self, tr: Tractor) -> bool:
        """C5: f_k < costo del camino más corto a G + margen."""
        c = self.p["costs"]
        cost = self.field.min_cost(tr.pos, tr.direction, self.field.gas, c["move"], c["turn"])
        return tr.fuel < cost + self.p["refuel"]["margin"]

    def finish(self, tr: Tractor):
        """El agente declara que ya no tiene trabajo."""
        tr.mode = "terminado"

    # ---------- validación (pura) ----------
    def _validate(self, tr: Tractor, a: str):
        f, c = self.field, self.p["costs"]
        if a not in ACTIONS:
            return False, "acción desconocida"
        if a in DIRS:
            tgt = (tr.pos[0] + DIRS[a][0], tr.pos[1] + DIRS[a][1])
            if not f.in_bounds(tgt):
                return False, "fuera del campo"
            if not f.passable(tgt):
                return False, "obstáculo"
            if tr.fuel + 1e-9 < c["move"] + (c["turn"] if a != tr.direction else 0.0):
                return False, "combustible insuficiente"
        elif a == "sembrar":
            if tr.pos not in f.sowable:
                return False, "celda no sembrable"
            if self.M[tr.pos]:
                return False, "celda ya sembrada"
            if tr.seeds < 1:
                return False, "sin semillas"
        elif a == "cargar_G" and tr.pos != f.gas:
            return False, "fuera de la estación G"
        elif a == "cargar_S" and tr.pos != f.seed_station:
            return False, "fuera de la estación S"
        return True, ""

    def _ranks(self) -> dict:
        ids = [t.id for t in self.tractors]
        order = list(self.rng.permutation(ids)) if self.p["coordination"]["random_tiebreak"] else sorted(ids)
        return {int(k): i for i, k in enumerate(order)}     # menor = mayor prioridad

    def _resolve(self, moves: dict, rank: dict) -> set:
        """C2 y C3: devuelve los tractores cuyo movimiento se bloquea."""
        pos = {t.id: t.pos for t in self.tractors}
        blocked: set = set()
        while True:
            dest = {k: (moves[k][0] if k in moves and k not in blocked else pos[k]) for k in pos}
            groups = defaultdict(list)
            for k, cell in dest.items():
                groups[cell].append(k)
            new: set = set()
            for ks in groups.values():
                if len(ks) > 1:
                    stayers = [k for k in ks if k not in moves or k in blocked]
                    movers = [k for k in ks if k in moves and k not in blocked]
                    keep = stayers[0] if stayers else min(movers, key=rank.get)
                    new.update(k for k in movers if k != keep)
            active = [k for k in moves if k not in blocked]
            for i, j in combinations(active, 2):
                if moves[i][0] == pos[j] and moves[j][0] == pos[i]:
                    new.add(max((i, j), key=rank.get))
            new -= blocked
            if not new:
                return blocked
            blocked |= new

    # ---------- transición ----------
    def step(self, actions: dict) -> dict:
        self.t += 1
        c, rank, allow = self.p["costs"], self._ranks(), self.p["coordination"]["allow_collisions"]
        out, plan, moves = {}, {}, {}
        for tr in self.tractors:
            a = actions.get(tr.id, "esperar")
            if tr.mode == "terminado":
                out[tr.id], plan[tr.id] = Outcome(tr.id, a, "inactivo"), "inactivo"
                continue
            ok, why = self._validate(tr, a)
            if not ok:
                out[tr.id], plan[tr.id] = Outcome(tr.id, a, "rechazada", why), "esperar"
                self.rejected += 1
                continue
            out[tr.id], plan[tr.id] = Outcome(tr.id, a, "ok"), a
            if a in DIRS:
                tgt = (tr.pos[0] + DIRS[a][0], tr.pos[1] + DIRS[a][1])
                moves[tr.id] = (tgt, a, c["move"] + (c["turn"] if a != tr.direction else 0.0))

        pos = {t.id: t.pos for t in self.tractors}
        if allow:
            blocked = set()
            self.collisions += sum(1 for i, j in combinations(moves, 2)
                                   if moves[i][0] == pos[j] and moves[j][0] == pos[i])
        else:
            blocked = self._resolve(moves, rank)
            self.conflicts_blocked += len(blocked)
        self.R = {k: moves[k][0] for k in moves if k not in blocked}

        moved = set()
        for tr in sorted(self.tractors, key=lambda t: rank[t.id]):
            k, p = tr.id, plan[tr.id]
            if p == "inactivo":
                continue
            if k in blocked:
                out[k] = Outcome(k, out[k].action, "bloqueada", "conflicto de celda")
                self._wait(tr)
            elif p in DIRS:
                tgt, a, cost = moves[k]
                tr.pos, tr.fuel = tgt, max(0.0, tr.fuel - cost)
                tr.fuel_spent += cost
                tr.distance += 1
                tr.turns += int(a != tr.direction)
                tr.direction, tr.mode = a, "moviéndose"
                tr.trampled += int(self.M[tgt])
                moved.add(k)
            elif p == "sembrar":
                ok, why = self._validate(tr, "sembrar")     # otro tractor pudo sembrar en este tick
                if ok:
                    self.M[tr.pos] = 1
                    self.sow_count[tr.pos] += 1
                    tr.seeds -= 1
                    tr.sown += 1
                    tr.mode = "sembrando"
                else:
                    out[k] = Outcome(k, "sembrar", "rechazada", why)
                    self.rejected += 1
                    self._wait(tr)
            elif p == "esperar":
                self._wait(tr)
            elif p == "cargar_G":
                tr.fuel, tr.mode = float(self.p["tractors"]["fuel_capacity"]), "cargando"
                tr.visits_G += 1
            elif p == "cargar_S":
                tr.seeds, tr.mode = self.p["tractors"]["seed_capacity"], "cargando"
                tr.visits_S += 1

        if allow:
            for cell, n in Counter(t.pos for t in self.tractors).items():
                if n > 1 and any(t.id in moved and t.pos == cell for t in self.tractors):
                    self.collisions += 1
        for name, cell in (("G", self.field.gas), ("S", self.field.seed_station)):
            occ = [t.id for t in self.tractors if t.pos == cell]
            self.O[name] = min(occ) if occ else None
        if self.is_done():
            for tr in self.tractors:
                tr.mode = "terminado"
        if self.p["sim"]["record_telemetry"]:
            for tr in self.tractors:
                o = out[tr.id]
                self.log.append(dict(t=self.t, tractor=tr.name, pos=tr.pos, mode=tr.mode,
                                     action=o.action, status=o.status,
                                     intent=self.R.get(tr.id)))
        return out

    def _wait(self, tr: Tractor):
        cost = min(self.p["costs"]["wait"], tr.fuel)
        tr.fuel -= cost
        tr.fuel_spent += cost
        tr.wait_ticks += 1
        tr.mode = "esperando"

    # ---------- métricas ----------
    def summary(self) -> dict:
        T = self.tractors
        d = [t.distance for t in T]
        return {
            "ticks": self.t,
            "cobertura_pct": 100.0 * float(self.M.sum()) / len(self.field.sowable),
            "resiembras": int((self.sow_count > 1).sum()),
            "colisiones": self.collisions,
            "conflictos_bloqueados": self.conflicts_blocked,
            "acciones_rechazadas": self.rejected,
            "distancia": d, "distancia_total": sum(d),
            "combustible": [round(t.fuel_spent, 2) for t in T],
            "combustible_total": round(sum(t.fuel_spent for t in T), 2),
            "espera": [t.wait_ticks for t in T], "espera_total": sum(t.wait_ticks for t in T),
            "visitas_G": [t.visits_G for t in T], "visitas_S": [t.visits_S for t in T],
            "pisadas": sum(t.trampled for t in T),
            "desbalance": max(d) - min(d),
        }


def objective(s: dict, w: dict) -> float:
    """J = λ1·T + λ2·D + λ3·colisiones + λ4·espera + λ5·combustible + λ6·Δ_balance."""
    return (w["lambda1"] * s["ticks"] + w["lambda2"] * s["distancia_total"]
            + w["lambda3"] * s["colisiones"] + w["lambda4"] * s["espera_total"]
            + w["lambda5"] * s["combustible_total"] + w["lambda6"] * s["desbalance"])
