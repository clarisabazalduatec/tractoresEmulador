"""Política tabular para decidir el reabastecimiento de semillas."""
import random
import json
from pathlib import Path


class SeedPolicy:
    ACTIONS = ('continuar', 'reabastecer')

    def __init__(self, alpha=0.2, gamma=0.9, epsilon=0.1, seed=0):
        if not all(0 <= x <= 1 for x in (alpha, gamma, epsilon)):
            raise ValueError('alpha, gamma y epsilon deben estar entre 0 y 1')
        self.alpha, self.gamma, self.epsilon = alpha, gamma, epsilon
        self.rng = random.Random(seed)
        self.values = {}

    @staticmethod
    def state(seeds, distance, pending):
        return (min(int(seeds), 10), min(int(distance // 5), 4), min(int(pending // 10), 4))

    def choose(self, state, training):
        if training and self.rng.random() < self.epsilon:
            return self.rng.choice(self.ACTIONS)
        values = self.values.get(state)
        if values is None:
            return 'reabastecer' if state[0] <= 2 else 'continuar'
        return self.ACTIONS[max(range(2), key=lambda i: values[i])]

    def update(self, state, action, reward, next_state, terminal=False, duration=1):
        values = self.values.setdefault(state, [0.0, 0.0])
        i = self.ACTIONS.index(action)
        future = 0.0 if terminal else max(self.values.get(next_state, [0.0, 0.0]))
        values[i] += self.alpha * (reward + self.gamma ** max(1, duration) * future - values[i])


def load_policies(path):
    """Carga las tablas entrenadas para evaluar sin exploración ni actualización."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    policies = []
    for item in data:
        policy = SeedPolicy(epsilon=0)
        policy.values = {tuple(state): list(values) for state, values in item['values']}
        policies.append(policy)
    return policies
