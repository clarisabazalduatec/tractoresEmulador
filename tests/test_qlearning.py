import pytest

from src.model import run_episode
from src.qlearning import SeedPolicy


def test_q_update_and_terminal_target():
    policy = SeedPolicy(alpha=0.5, gamma=0.9, epsilon=0)
    state, next_state = (2, 1, 1), (3, 1, 1)
    policy.values[next_state] = [100, 100]
    policy.update(state, 'reabastecer', 4, next_state, terminal=True)
    assert policy.values[state][1] == pytest.approx(2)
    assert policy.choose(state, training=False) == 'reabastecer'


def test_duration_discount_and_unseen_fallback():
    policy = SeedPolicy(alpha=1, gamma=0.5, epsilon=0)
    assert policy.choose((2, 0, 1), training=False) == 'reabastecer'
    assert policy.choose((3, 0, 1), training=False) == 'continuar'
    policy.values[(3, 0, 1)] = [8, 0]
    policy.update((2, 0, 1), 'continuar', 0, (3, 0, 1), duration=3)
    assert policy.values[(2, 0, 1)][0] == pytest.approx(1)


def test_learning_integrates_with_coordinated_episode():
    policies = [SeedPolicy(seed=i) for i in range(3)]
    _, result = run_episode('improved', 0.05, 0, q_enabled=True,
                            q_training=True, q_policies=policies)
    assert result['completo']
    assert result['colisiones'] == result['acciones_rechazadas'] == result['resiembras'] == 0
    assert all(p.values for p in policies)
