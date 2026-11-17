"""Tractor con decisiones coordinadas por blackboard."""
from .agents import TractorAgent
from .planner import astar


class ImprovedTractor(TractorAgent):
    def setup(self):
        super().setup()
        self.stalled = 0
        self.last_pos = None
        self.station_departure = False

    def decide(self):
        w, tr, f = self.world, self.tractor, self.world.field
        if tr.mode == 'terminado':
            return 'esperar'
        self.stalled = self.stalled + 1 if tr.pos == self.last_pos else 0
        self.last_pos = tr.pos
        # En G no se vuelve a pedir gasolina después de cargar: salir de la
        # estación tiene prioridad sobre cualquier objetivo de siembra.
        if tr.pos == f.gas and self.goal != 'G':
            departure = self.model.blackboard.station_exit(self.tid)
            if departure is not None:
                return departure
        if self.goal != 'G' and (w.needs_refuel(tr) or
                tr.fuel <= f.min_cost(tr.pos, tr.direction, f.gas,
                    w.p['costs']['move'], w.p['costs']['turn']) + 12.0):
            self.goal = 'G'
        elif self.goal is None and tr.seeds <= self.model.cfg['dispatch']['seed_threshold']:
            self.goal = 'S'
        if self.goal:
            station = f.gas if self.goal == 'G' else f.seed_station
            if tr.pos == station:
                g, self.goal = self.goal, None
                return 'cargar_' + g
            return self._navigate(station)
        target = self.model.blackboard.target(self.tid)
        if target is None:
            # Retirarse a una plaza fija, lejos de las estaciones, antes de terminar.
            parking = tuple(self.model.cfg['tractors']['starts'][self.tid - 1])
            if tr.pos == parking:
                w.finish(tr)
                return 'esperar'
            return self._navigate(parking)
        if tr.pos == target:
            return 'sembrar'
        return self._navigate(target)

    def _navigate(self, dest):
        w, tr = self.world, self.tractor
        c = w.p['costs']
        occupied = {t.pos for t in w.tractors if t.id != self.tid}
        route = astar(w.field, tr.pos, tr.direction, dest, c['move'], c['turn'], occupied)
        if route is None:
            # Dejar que el blackboard coordine un paso ocupado, sin bloquear
            # permanentemente la ruta por considerar al otro tractor una roca.
            route = astar(w.field, tr.pos, tr.direction, dest, c['move'], c['turn'])
        if route is None or not route[0]:
            return 'esperar'
        return route[0][0]
