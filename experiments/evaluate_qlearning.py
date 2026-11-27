"""Entrenamiento y comparación pareada reproducibles de la política de semillas."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

from src.model import run_episode
from src.qlearning import SeedPolicy, load_policies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-per-density', type=int, default=40)
    parser.add_argument('--eval-per-density', type=int, default=20)
    parser.add_argument('--eval-start-seed', type=int, default=10000)
    parser.add_argument('--policy', type=Path, help='Evaluar tablas existentes sin entrenar')
    parser.add_argument('--output', type=Path, default=Path('results/qlearning_experiment'))
    args = parser.parse_args()
    if args.train_per_density < 1 or args.eval_per_density < 1:
        parser.error('Las cantidades de episodios deben ser positivas')
    if args.eval_start_seed < args.train_per_density:
        parser.error('Las semillas de evaluación deben ser distintas a las de entrenamiento')
    args.output.mkdir(parents=True, exist_ok=True)
    densities = (0.0, 0.05, 0.10)
    policies = load_policies(args.policy) if args.policy else [SeedPolicy(seed=i) for i in range(3)]
    fields = ['phase', 'architecture', 'density', 'seed', 'ticks', 'completo',
              'cobertura_pct', 'distancia_total', 'combustible_total', 'espera_total',
              'colisiones', 'acciones_rechazadas', 'resiembras', 'visitas_G', 'visitas_S']
    with (args.output / 'episodes.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        def episode(phase, label, density, seed, **kwargs):
            model, result = run_episode('improved', density, seed, **kwargs)
            row = dict(phase=phase, architecture=label, density=density, seed=seed)
            row.update({k: result[k] for k in fields[4:-2]})
            row['visitas_G'] = sum(t.visits_G for t in model.world.tractors)
            row['visitas_S'] = sum(t.visits_S for t in model.world.tractors)
            writer.writerow(row)
            handle.flush()
            print(f"{phase} {label} d={density} seed={seed} ticks={row['ticks']} completo={row['completo']}", flush=True)
            return row

        if not args.policy:
            for seed in range(args.train_per_density):
                for density in densities:
                    episode('train', 'q_learning', density, seed, q_enabled=True,
                            q_training=True, q_policies=policies)
        policy_path = args.output / 'policies.json'
        policy_path.write_text(json.dumps([{'values': [[list(k), v] for k, v in p.values.items()]}
                                           for p in policies], indent=2), encoding='utf-8')
        policies = load_policies(policy_path)
        pairs = []
        for density in densities:
            for seed in range(args.eval_start_seed, args.eval_start_seed + args.eval_per_density):
                base = episode('eval', 'improved', density, seed)
                learned = episode('eval', 'q_learning', density, seed,
                                  q_enabled=True, q_policies=policies)
                pairs.append((base, learned))

    summary = {}
    metrics = ('ticks', 'cobertura_pct', 'distancia_total', 'combustible_total',
               'espera_total', 'colisiones', 'acciones_rechazadas', 'resiembras', 'visitas_S')
    for density in densities:
        subset = [(a, b) for a, b in pairs if a['density'] == density]
        summary[str(density)] = {
            'pairs': len(subset),
            'completed_baseline': sum(a['completo'] for a, _ in subset),
            'completed_q': sum(b['completo'] for _, b in subset),
            'means': {m: {'improved': mean(a[m] for a, _ in subset),
                          'q_learning': mean(b[m] for _, b in subset),
                          'paired_difference_q_minus_improved': mean(b[m] - a[m] for a, b in subset),
                          'median_difference': median(b[m] - a[m] for a, b in subset)} for m in metrics},
        }
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Experimento finalizado.', flush=True)


if __name__ == '__main__':
    main()
