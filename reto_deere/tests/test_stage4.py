import pandas as pd
import pytest
from experiments.stage4 import analyze, _paired_ci


def test_ci_constante():
    mean, low, high, p = _paired_ci([2., 2., 2.])
    assert mean == low == high == 2
    assert p == 0


def test_diferencias_pareadas_signo():
    rows = []
    for seed in range(3):
        for arch, ticks, coverage in [('baseline', 100, 90), ('improved', 80, 100)]:
            row = dict(density=.05, seed=seed, architecture=arch, completo=arch == 'improved')
            row.update({key: 10 for key in ('distancia_total', 'combustible_total',
                         'espera_total', 'colisiones', 'acciones_rechazadas',
                         'resiembras', 'desbalance', 'J')})
            row.update(ticks=ticks, cobertura_pct=coverage)
            rows.append(row)
    summary, paired = analyze(pd.DataFrame(rows))
    assert paired.set_index('metric').loc['ticks', 'mean_improvement'] == 20
    assert paired.set_index('metric').loc['cobertura_pct', 'mean_improvement'] == 10
    assert summary['n'].tolist() == [3, 3]


def test_pares_incompletos_rechazados():
    rows = []
    for arch, seed in [('baseline', 0), ('improved', 1)]:
        row = {'architecture': arch, 'density': .05, 'seed': seed, 'completo': True}
        row.update({k: 1 for k in ('ticks', 'cobertura_pct', 'distancia_total',
                    'combustible_total', 'espera_total', 'colisiones',
                    'acciones_rechazadas', 'resiembras', 'desbalance', 'J')})
        rows.append(row)
    with pytest.raises(ValueError, match='faltan pares'):
        analyze(pd.DataFrame(rows))


def test_completitud_pareada():
    rows = []
    for seed in range(4):
        for arch in ('baseline', 'improved'):
            row = dict(density=.1, seed=seed, architecture=arch,
                       completo=(arch == 'improved'))
            row.update({k: 1 for k in ('ticks', 'cobertura_pct', 'distancia_total',
                       'combustible_total', 'espera_total', 'colisiones',
                       'acciones_rechazadas', 'resiembras', 'desbalance', 'J')})
            rows.append(row)
    summary, pairs = analyze(pd.DataFrame(rows))
    effect = pairs[pairs.metric == 'completitud_pp'].iloc[0]
    assert effect.mean_improvement == 100
    assert effect.ci95_low == effect.ci95_high == 100
    assert summary.set_index('architecture').loc['improved', 'tasa_completitud_pct'] == 100


def test_dashboard_desde_csv_sin_agentpy(tmp_path):
    from experiments.stage4 import dashboard, plot_effects
    rows = []
    for seed in range(3):
        for arch in ('baseline', 'improved'):
            row = dict(density=.05, seed=seed, architecture=arch, completo=True)
            row.update({k: 10 for k in ('ticks', 'cobertura_pct', 'distancia_total',
                       'combustible_total', 'espera_total', 'colisiones',
                       'acciones_rechazadas', 'resiembras', 'desbalance', 'J')})
            rows.append(row)
    df = pd.DataFrame(rows)
    summary, pairs = analyze(df)
    dashboard(df, summary, pairs, tmp_path/'dashboard.png')
    plot_effects(pairs, tmp_path/'paired_effects.png')
    assert (tmp_path/'dashboard.png').stat().st_size > 1000
    assert (tmp_path/'paired_effects.png').stat().st_size > 1000
