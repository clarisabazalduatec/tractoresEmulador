"""Pruebas de integración de la etapa 3 (requieren AgentPy instalado)."""
import pytest
from src.model import run_episode

@pytest.mark.parametrize('density', [0.0, 0.05, 0.10])
def test_improved_safety(density):
    model, result = run_episode('improved', density, 8)
    assert result['colisiones'] == 0
    assert result['resiembras'] == 0
    assert result['acciones_rechazadas'] == 0
    assert len(set(t.pos for t in model.world.tractors)) == 3

@pytest.mark.parametrize('seed', [1, 8, 42])
def test_improved_coverage(seed):
    _, result = run_episode('improved', 0.05, seed)
    assert result['completo'], f"bloqueo: seed={seed}, cobertura={result['cobertura_pct']}"


def test_improved_regression_seed_4_density_10():
    _, result = run_episode('improved', 0.10, 4)
    assert result['completo'], result
    assert result['cobertura_pct'] == 100
    assert result['colisiones'] == 0
    assert result['resiembras'] == 0
    assert result['acciones_rechazadas'] == 0

@pytest.mark.parametrize('density,seed', [(0.05,16), (0.10,4), (0.10,6), (0.10,12)])
def test_regresion_reserva_combustible(density, seed):
    _, result = run_episode('improved', density, seed)
    assert result['completo'], result
    assert result['colisiones'] == 0
    assert result['resiembras'] == 0
    assert result['acciones_rechazadas'] == 0

@pytest.mark.parametrize('density,seed', [(0.05,3), (0.05,16), (0.10,10)])
def test_regresion_bloqueo_estacion(density, seed):
    _, result = run_episode('improved', density, seed)
    assert result['completo'], result
    assert result['acciones_rechazadas'] == 0
    assert result['colisiones'] == 0
    assert result['resiembras'] == 0
