"""Entrena y guarda una tabla por tractor: python -m experiments.train_qlearning."""
import argparse
import json
from pathlib import Path

from src.model import run_episode
from src.qlearning import SeedPolicy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=int, default=30)
    parser.add_argument('--density', type=float, default=0.05)
    parser.add_argument('--output', type=Path, default=Path('results/qlearning/policies.json'))
    args = parser.parse_args()
    if args.episodes < 1:
        parser.error('--episodes debe ser positivo')
    policies = [SeedPolicy(seed=i) for i in range(3)]
    for seed in range(args.episodes):
        _, result = run_episode('improved', args.density, seed, q_enabled=True,
                                q_training=True, q_policies=policies)
        print(f"episodio {seed + 1}: ticks={result['ticks']}, completo={result['completo']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([{'values': [[list(k), v] for k, v in p.values.items()]}
                                       for p in policies], indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
