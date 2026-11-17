"""Diagnóstico reproducible de estancamientos; usa AgentPy real."""
import argparse
from collections import Counter
from src.model import run_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--density', type=float, default=0.10)
    parser.add_argument('--seed', type=int, default=4)
    args = parser.parse_args()
    model, result = run_episode('improved', args.density, args.seed)
    w = model.world
    print('RESULTADO:', result)
    print('TRACTORES:')
    for a in model.agents:
        t = a.tractor
        print(t.name, 'pos=', t.pos, 'fuel=', round(t.fuel, 2), 'seeds=', t.seeds,
              'goal=', a.goal, 'stalled=', a.stalled, 'mode=', t.mode,
              'target=', model.blackboard.target(a.tid))
    pending = model.blackboard.pending()
    print('PENDIENTES:', len(pending), sorted(pending))
    print('PROPIETARIOS:', Counter(model.blackboard.claims.get(c) for c in pending))
    print('ULTIMAS ACCIONES:')
    for item in w.log[-30:]:
        print(item)
    print('NOTA: las acciones rechazadas no registran motivo en la telemetría original.')

if __name__ == '__main__':
    main()
