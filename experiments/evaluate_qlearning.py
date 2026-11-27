"""Entrenamiento y comparación pareada reproducibles de la política de semillas."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, median

from src.model import run_episode
from src.qlearning import SeedPolicy, load_policies


def _policy_payload(policies):
    return [{'values': [[list(k), v] for k, v in policy.values.items()]}
            for policy in policies]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-per-density', type=int, default=40)
    parser.add_argument('--eval-per-density', type=int, default=20)
    parser.add_argument('--eval-start-seed', type=int, default=10000)
    parser.add_argument('--policy', type=Path, help='Evaluar tablas existentes sin entrenar')
    parser.add_argument('--start-mode', choices=('fixed', 'random'), default='fixed')
    parser.add_argument('--output', type=Path, default=Path('results/qlearning_experiment'))
    args = parser.parse_args()
    if args.train_per_density < 1 or args.eval_per_density < 1:
        parser.error('Las cantidades de episodios deben ser positivas')
    if args.eval_start_seed < args.train_per_density:
        parser.error('Las semillas de evaluación deben ser distintas a las de entrenamiento')
    if args.start_mode == 'random' and not args.policy:
        parser.error('La evaluación con inicios aleatorios requiere --policy para no entrenar tablas nuevas')

    if args.output.exists() and any(args.output.iterdir()):
        parser.error(f'El directorio de salida no está vacío: {args.output}; elige una ruta nueva')
    args.output.mkdir(parents=True, exist_ok=True)
    densities = (0.0, 0.05, 0.10)
    policies = load_policies(args.policy) if args.policy else [SeedPolicy(seed=i) for i in range(3)]
    fields = [
        'phase', 'architecture', 'density', 'seed', 'start_mode', 'initial_positions',
        'obstacle_sha256', 'ticks', 'max_ticks', 'hit_tick_limit', 'completo',
        'cobertura_pct', 'distancia_total', 'combustible_total', 'espera_total',
        'colisiones', 'acciones_rechazadas', 'resiembras', 'visitas_G', 'visitas_S',
    ]
    metric_fields = (
        'ticks', 'completo', 'cobertura_pct', 'distancia_total', 'combustible_total',
        'espera_total', 'colisiones', 'acciones_rechazadas', 'resiembras',
    )
    with (args.output / 'episodes.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        def episode(phase, label, density, seed, **kwargs):
            model, result = run_episode(
                'improved', density, seed, start_mode=args.start_mode, **kwargs
            )
            starts = [[int(row), int(col)] for row, col in model.start_positions]
            obstacles = sorted([int(r), int(c)] for r, c in model.world.field.obstacles)
            max_ticks = int(model.cfg['sim']['max_ticks'])
            complete = bool(result['completo'])
            row = {
                'phase': phase,
                'architecture': label,
                'density': density,
                'seed': seed,
                'start_mode': model.start_mode,
                'initial_positions': json.dumps(starts, separators=(',', ':')),
                'obstacle_sha256': hashlib.sha256(
                    json.dumps(obstacles, separators=(',', ':')).encode('utf-8')
                ).hexdigest(),
                'max_ticks': max_ticks,
                'hit_tick_limit': bool(not complete and model.world.t >= max_ticks),
            }
            row.update({key: result[key] for key in metric_fields})
            row['completo'] = complete
            row['visitas_G'] = sum(t.visits_G for t in model.world.tractors)
            row['visitas_S'] = sum(t.visits_S for t in model.world.tractors)
            writer.writerow(row)
            handle.flush()
            print(
                f"{phase} {label} d={density} seed={seed} mode={args.start_mode} "
                f"ticks={row['ticks']} complete={row['completo']} "
                f"tick_limit={row['hit_tick_limit']}",
                flush=True,
            )
            return row

        if not args.policy:
            for seed in range(args.train_per_density):
                for density in densities:
                    episode('train', 'q_learning', density, seed, q_enabled=True,
                            q_training=True, q_policies=policies)
            generated_policy = args.output / 'policies.json'
            generated_policy.write_text(
                json.dumps(_policy_payload(policies), indent=2), encoding='utf-8'
            )
            policies = load_policies(generated_policy)
            policy_path = generated_policy
        else:
            policy_path = args.policy

        policy_file_digest_before = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        policy_tables_before = copy.deepcopy([policy.values for policy in policies])
        pairs = []
        for density in densities:
            for seed in range(args.eval_start_seed, args.eval_start_seed + args.eval_per_density):
                improved = episode('eval', 'improved_no_q', density, seed)
                learned = episode('eval', 'q_learning', density, seed,
                                  q_enabled=True, q_training=False,
                                  q_policies=policies)
                if (improved['obstacle_sha256'] != learned['obstacle_sha256']
                        or improved['initial_positions'] != learned['initial_positions']):
                    raise RuntimeError('El par Q/improved no comparte mapa e inicios')
                pairs.append((improved, learned))
        if policy_tables_before != [policy.values for policy in policies]:
            raise RuntimeError('La política cambió durante la evaluación sin aprendizaje')

    policy_digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    if policy_digest != policy_file_digest_before:
        raise RuntimeError('El archivo de política cambió durante la evaluación')
    summary = {
        'metadata': {
            'start_mode': args.start_mode,
            'policy': str(policy_path),
            'policy_sha256': policy_digest,
            'q_learning_training_during_evaluation': False,
            'tick_limit': pairs[0][0]['max_ticks'],
            'densities': list(densities),
            'eval_seeds': list(range(args.eval_start_seed,
                                     args.eval_start_seed + args.eval_per_density)),
            'paired_map_and_initial_positions': True,
            'censoring_note': (
                'Ticks-to-completion only uses pairs where both episodes complete. '
                'Other totals from tick-limited episodes are cumulative only through the limit.'
            ),
        },
    }
    descriptive_metrics = (
        'cobertura_pct', 'distancia_total', 'combustible_total', 'espera_total',
        'colisiones', 'acciones_rechazadas', 'resiembras', 'visitas_S',
    )
    for density in densities:
        subset = [(a, b) for a, b in pairs if a['density'] == density]
        complete_pairs = [(a, b) for a, b in subset if a['completo'] and b['completo']]
        metrics_summary = {}
        for metric in descriptive_metrics:
            metrics_summary[metric] = {
                'n_pairs': len(subset),
                'improved_no_q_mean_until_completion_or_limit': mean(a[metric] for a, _ in subset),
                'q_learning_mean_until_completion_or_limit': mean(b[metric] for _, b in subset),
                'paired_difference_q_minus_improved': mean(
                    b[metric] - a[metric] for a, b in subset
                ),
                'median_difference': median(b[metric] - a[metric] for a, b in subset),
            }
        summary[str(density)] = {
            'pairs': len(subset),
            'completed_improved_no_q': sum(a['completo'] for a, _ in subset),
            'completed_q_learning': sum(b['completo'] for _, b in subset),
            'hit_tick_limit_improved_no_q': sum(a['hit_tick_limit'] for a, _ in subset),
            'hit_tick_limit_q_learning': sum(b['hit_tick_limit'] for _, b in subset),
            'ticks_when_both_complete': {
                'n_pairs': len(complete_pairs),
                'improved_no_q_mean': mean(a['ticks'] for a, _ in complete_pairs)
                if complete_pairs else None,
                'q_learning_mean': mean(b['ticks'] for _, b in complete_pairs)
                if complete_pairs else None,
                'paired_difference_q_minus_improved': mean(
                    b['ticks'] - a['ticks'] for a, b in complete_pairs
                ) if complete_pairs else None,
                'median_difference': median(
                    b['ticks'] - a['ticks'] for a, b in complete_pairs
                ) if complete_pairs else None,
            },
            'metrics_until_completion_or_limit': metrics_summary,
        }
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Experimento finalizado.', flush=True)


if __name__ == '__main__':
    main()
