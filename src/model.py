"""Modelo AgentPy: campo + 3 tractores. Parámetros del modelo (self.p):
    architecture     'baseline' | 'improved'
    obstacle_density fracción de rocas (sobrescribe el YAML)
    seed             semilla (AgentPy la usa para self.nprandom)
    config_path      ruta del YAML (opcional)
"""
from pathlib import Path
import copy
import agentpy as ap
from .agents import TractorAgent
from .improved import ImprovedTractor
from .blackboard import Blackboard
from .planner import strips, zigzag_order
from .rules import WorldState, objective
from .world import build_field, load_params, validate_params

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "params.yaml"
AGENT_CLASSES = {"baseline": TractorAgent, "improved": ImprovedTractor}          # 'improved' llega en la etapa 3


class FarmModel(ap.Model):
    def setup(self):
        arch = self.p.get("architecture", "baseline")
        if arch not in AGENT_CLASSES:
            raise NotImplementedError(f"arquitectura '{arch}' aún no implementada")
        cfg = copy.deepcopy(load_params(self.p.get("config_path", DEFAULT_CONFIG)))
        cfg["coordination"].update(cfg["architectures"][arch])
        if "obstacle_density" in self.p:
            cfg["field"]["obstacle_density"] = float(self.p["obstacle_density"])
        validate_params(cfg)
        self.cfg, self.arch = cfg, arch
        field = build_field(cfg, rng=self.nprandom)
        self.world = WorldState(field, cfg, rng=self.nprandom)
        n = cfg["tractors"]["count"]
        self.agents = ap.AgentList(self, n, AGENT_CLASSES[arch])
        for i, (agent, cols) in enumerate(zip(self.agents, strips(field.size, n)), start=1):
            agent.tid = i
            agent.order = zigzag_order(cols, field)
        if arch == "improved":
            self.blackboard = Blackboard(self)
            self.blackboard.auction()

    def step(self):
        actions = {a.tid: a.decide() for a in self.agents}
        if self.arch == "improved":
            from .planner import step_cell
            from .world import DIRS
            intents = {tid: (action, step_cell(self.world.tractors[tid-1].pos, action) if action in DIRS else None) for tid, action in actions.items()}
            actions = self.blackboard.plan_moves(intents)
        self.world.step(actions)
        if self.arch == "improved":
            self.blackboard.auction()
        if self.world.is_done() or self.world.t >= self.cfg["sim"]["max_ticks"]:
            self.stop()

    def update(self):
        w = self.world
        self.record("cobertura", 100.0 * float(w.M.sum()) / len(w.field.sowable))
        self.record("colisiones", w.collisions)

    def end(self):
        w, s = self.world, self.world.summary()
        for k, v in s.items():
            if isinstance(v, list):
                for i, x in enumerate(v, start=1):
                    self.report(f"{k}_T{i}", x)
            else:
                self.report(k, v)
        self.report("J", objective(s, self.cfg["objective_weights"]))
        self.report("completo", bool(w.is_done()))
        self.report("celdas_sembrables", len(w.field.sowable))
        self.report("obstaculos", len(w.field.obstacles))
        if self.arch == "improved":
            self.report("subastas", self.blackboard.auctions)


def run_episode(architecture="baseline", density=0.0, seed=0, **extra):
    """Corre una simulación y devuelve (modelo, reporters como dict)."""
    m = FarmModel({"architecture": architecture, "obstacle_density": density, "seed": seed, **extra})
    res = m.run(display=False)
    return m, res.reporters.iloc[0].to_dict()
