"""Tractor con decisiones coordinadas por blackboard."""
from .agents import TractorAgent
from .planner import astar


class ImprovedTractor(TractorAgent):
    def setup(self):
        super().setup()
        self.stalled = 0
        self.last_pos = None
        self.station_departure = False
        self.q_pending = None
        self.q_decided_seeds = None

    def _q_observe(self, terminal=False):
        if self.q_pending is None or not self.model.p.get('q_training', False):
            return
        state, action, tick, fuel, sown = self.q_pending
        tr = self.tractor
        duration = self.world.t - tick
        reward = 5 * (tr.sown - sown) - 0.1 * duration - 0.05 * (tr.fuel_spent - fuel)
        self.model.q_policies[self.tid - 1].update(state, action, reward, self._q_state(), terminal, duration)
        self.q_pending = None

    def _q_state(self):
        tr, f = self.tractor, self.world.field
        c = self.world.p['costs']
        distance = f.min_cost(tr.pos, tr.direction, f.seed_station, c['move'], c['turn'])
        pending = sum(owner == self.tid for owner in self.model.blackboard.claims.values())
        return self.model.q_policies[self.tid - 1].state(tr.seeds, distance, pending)

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
        elif (self.goal is None and not self.model.p.get('q_enabled', False)
              and tr.seeds <= self.model.cfg['dispatch']['seed_threshold']):
            self.goal = 'S'
        if self.goal:
            station = f.gas if self.goal == 'G' else f.seed_station
            if tr.pos == station:
                g, self.goal = self.goal, None
                self.q_decided_seeds = None
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
        pending = sum(owner == self.tid for owner in self.model.blackboard.claims.values())
        if (self.model.p.get('q_enabled', False) and tr.seeds <= 5
                and pending > tr.seeds
                and (tr.seeds == 0 or tr.seeds != self.q_decided_seeds)):
            self._q_observe()
            state = self._q_state()
            action = ('reabastecer' if tr.seeds < 1 else
                      self.model.q_policies[self.tid - 1].choose(state, self.model.p.get('q_training', False)))
            self.q_decided_seeds = tr.seeds
            if self.model.p.get('q_training', False):
                self.q_pending = (state, action, w.t, tr.fuel_spent, tr.sown)
            if action == 'reabastecer':
                self.goal = 'S'
                return self._navigate(f.seed_station)
        if tr.seeds > 5:
            self.q_decided_seeds = None
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
