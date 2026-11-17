"""Pizarrón: propiedad de tareas, planificación de movimientos y cesión de paso."""
from .planner import astar, step_cell
from .world import DIRS


class Blackboard:
    def __init__(self, model):
        self.model = model
        self.claims = {}
        self.reservations = {}
        self.station_queue = {'G': [], 'S': []}
        self.auctions = 0
        self.yields = 0

    def pending(self):
        w = self.model.world
        return set(w.field.sowable) - {tuple(x) for x in zip(*w.M.nonzero())}

    def auction(self):
        """Asignación estable por franja; un tractor libre puede recibir trabajo pendiente."""
        w = self.model.world
        remaining = self.pending()
        self.claims = {c: owner for c, owner in self.claims.items() if c in remaining}
        if not self.claims and remaining:
            for a in self.model.agents:
                for cell in a.order:
                    if cell in remaining:
                        self.claims[cell] = a.tid
                        self.auctions += 1
        # Solo reasignar cuando un tractor realmente agotó su trabajo.
        idle = [a for a in self.model.agents if not any(v == a.tid for v in self.claims.values())]
        for a in idle:
            donors = [(sum(v == b.tid for v in self.claims.values()), b)
                      for b in self.model.agents if b.tid != a.tid]
            if not donors:
                continue
            count, donor = max(donors, key=lambda x: x[0])
            if count < 12:
                continue
            candidates = [c for c, owner in self.claims.items() if owner == donor.tid]
            costs = w.p['costs']
            bids = []
            for cell in candidates:
                route = astar(w.field, a.tractor.pos, a.tractor.direction, cell,
                              costs['move'], costs['turn'])
                if route:
                    bids.append((route[2], cell))
            if bids:
                for _, cell in sorted(bids)[:max(1, count // 4)]:
                    self.claims[cell] = a.tid
                    self.auctions += 1

    def target(self, tid):
        w = self.model.world
        tr = w.tractors[tid - 1]
        choices = [c for c, owner in self.claims.items() if owner == tid and not w.M[c]]
        if not choices:
            return None
        costs = w.p['costs']
        def score(cell):
            route = astar(w.field, tr.pos, tr.direction, cell, costs['move'], costs['turn'])
            return route[2] if route else float('inf')
        return min(choices, key=lambda c: (score(c), c))

    def release(self, tid):
        for c in [c for c, owner in self.claims.items() if owner == tid]:
            del self.claims[c]

    def station_exit(self, tid):
        """Desocupa G de inmediato tras recargar, sin entrar en otra posición ocupada.

        Elige un vecino que permita volver a G y que no sea otra estación.
        El coste de combustible de la maniobra es comprobado de nuevo en plan_moves.
        """
        w = self.model.world
        tr = w.tractors[tid - 1]
        occupied = {t.pos for t in w.tractors if t.id != tid}
        c = w.p['costs']
        options = []
        for direction, nxt in w.field.neighbors(tr.pos):
            if nxt in occupied or nxt == w.field.seed_station:
                continue
            cost = c['move'] + (c['turn'] if direction != tr.direction else 0)
            if tr.fuel < cost + w.field.min_cost(nxt, direction, w.field.gas,
                                                   c['move'], c['turn']) + 2:
                continue
            # Preferir alejarse de la cola de G y no bloquear sus accesos.
            clearance = sum(abs(nxt[0]-t.pos[0])+abs(nxt[1]-t.pos[1])
                            for t in w.tractors if t.id != tid and t.mode != 'terminado')
            options.append((-clearance, cost, nxt, direction))
        return min(options)[3] if options else None

    def plan_moves(self, intents):
        """Reserva simultánea. Un bloqueo circular se rompe haciendo ceder al ocupante.

        Solo se autorizan movimientos que el motor puede ejecutar sin conflictos;
        las maniobras de cesión se hacen sobre celdas libres y nunca intercambian posiciones.
        """
        w = self.model.world
        tractors = {t.id: t for t in w.tractors}
        occupied = {t.pos: t.id for t in w.tractors}
        actions = {tid: action for tid, (action, _) in intents.items()}
        destinations = {tid: cell for tid, (action, cell) in intents.items()
                        if action in DIRS and cell is not None}
        # Seguridad de combustible: nunca aceptar un movimiento de trabajo que
        # deje al tractor sin ruta energética de regreso a G. Para viajes a G
        # se permite reducir la reserva, pero nunca gastar más que lo disponible.
        costs = w.p['costs']
        for tid, dest in list(destinations.items()):
            tr = tractors[tid]
            direction = actions[tid]
            step_cost = costs['move'] + (costs['turn'] if direction != tr.direction else 0.0)
            remaining = tr.fuel - step_cost
            if remaining < -1e-8:
                actions[tid] = 'esperar'
                continue
            distance_to_g = w.field.min_cost(dest, direction, w.field.gas,
                                             costs['move'], costs['turn'])
            # Si no va hacia G, debe poder volver con margen de espera.
            agent = self.model.agents[tid - 1]
            margin = 0.0 if agent.goal == 'G' else w.p['refuel']['margin'] + 2.0
            if remaining + 1e-8 < distance_to_g + margin:
                actions[tid] = 'esperar'
                agent.goal = 'G'
        destinations = {tid: cell for tid, cell in destinations.items() if actions[tid] in DIRS}
        # No permitir que un tractor que NO está reabasteciéndose entre en G
        # cuando otro tractor necesita la estación. Evita ocupar el recurso
        # compartido como simple atajo de navegación.
        approaching = [tid for tid, a in enumerate(self.model.agents, 1)
                       if a.goal == 'G' and tractors[tid].pos != w.field.gas]
        if approaching:
            for tid, dest in list(destinations.items()):
                if dest == w.field.gas and tid not in approaching:
                    actions[tid] = 'esperar'
            destinations = {tid: cell for tid, cell in destinations.items()
                            if actions[tid] in DIRS}
        # Evitar objetivos duplicados y ciclos de intercambio.
        for tid in sorted(destinations):
            cell = destinations[tid]
            rivals = [k for k, v in destinations.items() if v == cell and k < tid]
            if rivals:
                actions[tid] = 'esperar'
        # La maniobra solo se aplica si el tractor que ocupa el paso no puede salir.
        # Una celda libre contigua permite desplazarlo sin cruzarse de frente.
        for tid in sorted(destinations):
            if actions[tid] not in DIRS:
                continue
            cell = destinations[tid]
            blocker = occupied.get(cell)
            if blocker is None or blocker == tid:
                continue
            other_dest = destinations.get(blocker) if actions.get(blocker) in DIRS else None
            if other_dest is not None and other_dest != tractors[tid].pos:
                continue  # movimiento de seguimiento válido
            actions[tid] = 'esperar'
            if actions.get(blocker) not in ('esperar',) and other_dest is not None:
                continue
            if tractors[blocker].mode == 'terminado':
                continue
            reserved = {destinations[k] for k in destinations if actions.get(k) in DIRS}
            for direction, nxt in w.field.neighbors(tractors[blocker].pos):
                if nxt in occupied or nxt in reserved:
                    continue
                cost = w.p['costs']['move'] + (w.p['costs']['turn'] if direction != tractors[blocker].direction else 0)
                if tractors[blocker].fuel < cost + w.field.min_cost(nxt, direction, w.field.gas,
                        w.p['costs']['move'], w.p['costs']['turn']):
                    continue
                actions[blocker] = direction
                self.yields += 1
                break
        # Intercambio frontal: el tractor con menos urgencia cede lateralmente.
        # La prioridad es alcanzar G con combustible suficiente.
        for tid in sorted(destinations):
            if actions.get(tid) not in DIRS:
                continue
            owner = occupied.get(step_cell(tractors[tid].pos, actions[tid]))
            if owner is None or owner == tid or actions.get(owner) not in DIRS:
                continue
            if step_cell(tractors[owner].pos, actions[owner]) != tractors[tid].pos:
                continue
            urgent = lambda k: (self.model.agents[k-1].goal == 'G', -tractors[k].fuel)
            yielder = min((tid, owner), key=urgent)
            if tractors[yielder].mode == 'terminado':
                continue
            reserved = {step_cell(tractors[k].pos, a) for k, a in actions.items()
                        if a in DIRS and k not in (tid, owner)}
            for direction, nxt in w.field.neighbors(tractors[yielder].pos):
                if nxt in occupied or nxt in reserved:
                    continue
                cost = w.p['costs']['move'] + (w.p['costs']['turn'] if direction != tractors[yielder].direction else 0)
                if tractors[yielder].fuel < cost + 1:
                    continue
                actions[yielder] = direction
                self.yields += 1
                break
        # Resolver dependencias hasta punto fijo (incluidos swaps y cadenas detenidas).
        while True:
            moving = {tid: step_cell(tractors[tid].pos, a)
                      for tid, a in actions.items() if a in DIRS and tractors[tid].mode != 'terminado'}
            blocked = set()
            for tid, dest in moving.items():
                owner = occupied.get(dest)
                if owner is not None and owner not in moving:
                    blocked.add(tid)
                elif owner is not None and moving.get(owner) == tractors[tid].pos:
                    blocked.add(max(tid, owner))
            for tid, dest in moving.items():
                if any(k < tid and v == dest for k, v in moving.items()):
                    blocked.add(tid)
            if not blocked:
                break
            for tid in blocked:
                actions[tid] = 'esperar'
        self.reservations = {tid: step_cell(tractors[tid].pos, a)
                             for tid, a in actions.items() if a in DIRS}
        return actions
