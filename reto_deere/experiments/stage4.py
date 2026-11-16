"""Etapa 4: experimentos pareados, intervalos de confianza y dashboard reproducible.

Ejecutar: python -m experiments.stage4 --output results/stage4
Reanalizar CSV existente: python -m experiments.stage4 --from-csv results/stage4/episodes.csv
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ARCHS = ('baseline', 'improved')
METRICS = ('ticks', 'cobertura_pct', 'distancia_total', 'combustible_total',
           'espera_total', 'colisiones', 'acciones_rechazadas', 'resiembras',
           'desbalance', 'J')
LOWER_BETTER = {'ticks', 'distancia_total', 'combustible_total', 'espera_total',
                'colisiones', 'acciones_rechazadas', 'resiembras', 'desbalance', 'J'}


def simulate(densities=(0., .05, .10), seeds=range(20)):
    from src.model import run_episode
    rows = []
    for density in densities:
        for seed in seeds:
            for arch in ARCHS:
                _, result = run_episode(arch, density, seed)
                row = {'architecture': arch, 'density': float(density), 'seed': int(seed)}
                row.update(result)
                rows.append(row)
                print(f'{arch:8s} density={density:.2f} seed={seed:02d} '
                      f'coverage={float(result["cobertura_pct"]):.1f}% '
                      f'ticks={int(result["ticks"])} complete={bool(result["completo"])}', flush=True)
    return pd.DataFrame(rows)


def _paired_ci(values):
    values = np.asarray(values, dtype=float)
    n = len(values)
    mean = float(np.mean(values))
    if n < 2:
        return mean, np.nan, np.nan, np.nan
    se = float(stats.sem(values))
    margin = float(stats.t.ppf(.975, n - 1) * se)
    p = float(stats.ttest_1samp(values, 0).pvalue) if se > 0 else (1. if mean == 0 else 0.)
    return mean, mean - margin, mean + margin, p


def analyze(df):
    df = df.copy()
    df['completo'] = df['completo'].map(lambda x: str(x).lower() in ('true', '1'))
    if df.duplicated(['density', 'seed', 'architecture']).any():
        raise ValueError('Hay escenarios duplicados (density, seed, architecture).')
    summary = df.groupby(['density', 'architecture'], as_index=False).agg(
        n=('seed', 'count'), completos=('completo', 'sum'),
        cobertura_media=('cobertura_pct', 'mean'), ticks_media=('ticks', 'mean'),
        distancia_media=('distancia_total', 'mean'), combustible_medio=('combustible_total', 'mean'),
        esperas_medias=('espera_total', 'mean'), colisiones_medias=('colisiones', 'mean'),
        J_medio=('J', 'mean'))
    summary['tasa_completitud_pct'] = 100 * summary['completos'] / summary['n']
    pairs = []
    for density, group in df.groupby('density'):
        base = group[group.architecture == 'baseline'].set_index('seed')
        improved = group[group.architecture == 'improved'].set_index('seed')
        shared = sorted(base.index.intersection(improved.index))
        if len(shared) != len(base) or len(shared) != len(improved):
            raise ValueError(f'Densidad {density}: faltan pares de semillas.')
        # Diferencia pareada de completitud en puntos porcentuales.
        completed_delta = 100 * (improved.loc[shared, 'completo'].astype(int).to_numpy() - base.loc[shared, 'completo'].astype(int).to_numpy())
        m, lo, hi, pv = _paired_ci(completed_delta)
        pairs.append({'density': density, 'metric': 'completitud_pp', 'n': len(shared),
                      'mean_improvement': m, 'ci95_low': lo, 'ci95_high': hi,
                      'p_value_exploratory': pv,
                      'baseline_complete': int(base.loc[shared, 'completo'].sum()),
                      'improved_complete': int(improved.loc[shared, 'completo'].sum())})
        for metric in METRICS:
            # Diferencia positiva significa mejora (menos coste o mayor cobertura).
            sign = 1 if metric in LOWER_BETTER else -1
            delta = sign * (base.loc[shared, metric].to_numpy(dtype=float) -
                            improved.loc[shared, metric].to_numpy(dtype=float))
            mean, lo, hi, p = _paired_ci(delta)
            pairs.append({'density': density, 'metric': metric, 'n': len(shared),
                          'mean_improvement': mean, 'ci95_low': lo, 'ci95_high': hi,
                          'p_value_exploratory': p,
                          'baseline_complete': int(base.loc[shared, 'completo'].sum()),
                          'improved_complete': int(improved.loc[shared, 'completo'].sum())})
    return summary, pd.DataFrame(pairs)


def dashboard(df, summary, pairs, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    densities = sorted(df.density.unique())
    fig = plt.figure(figsize=(16, 10), layout='constrained')
    grid = fig.add_gridspec(2, 3, height_ratios=[1, 1.15])
    colors = {'baseline': '#c77955', 'improved': '#387f92'}
    axes = [fig.add_subplot(grid[i, j]) for i in range(2) for j in range(3)]
    x = np.arange(len(densities))
    for ax, metric, title in [(axes[0], 'cobertura_pct', 'Cobertura final (%)'),
                              (axes[1], 'ticks', 'Tiempo (ticks; límite 3000)'),
                              (axes[2], 'J', 'Función objetivo J'),
                              (axes[3], 'distancia_total', 'Distancia (celdas)'),
                              (axes[4], 'combustible_total', 'Combustible consumido')]:
        for i, arch in enumerate(ARCHS):
            vals = [df[(df.density == d) & (df.architecture == arch)][metric].mean() for d in densities]
            ax.bar(x + (i-.5)*.34, vals, width=.33, color=colors[arch], label=arch)
        ax.set_title(title)
        ax.set_xticks(x, [f'{d:.0%}' for d in densities])
        ax.set_xlabel('Obstáculos')
        ax.grid(axis='y', alpha=.2)
    axes[0].legend()
    # El dashboard se reconstruye exclusivamente a partir del CSV, sin AgentPy.
    # Esto permite auditar resultados en otra computadora y evita simulaciones extra.
    ax = axes[5]
    for i, arch in enumerate(ARCHS):
        vals = [100 * df[(df.density == d) & (df.architecture == arch)]['completo'].mean()
                for d in densities]
        ax.bar(x + (i-.5)*.34, vals, width=.33, color=colors[arch], label=arch)
    ax.set_title('Simulaciones completadas (%)')
    ax.set_xticks(x, [f'{d:.0%}' for d in densities])
    ax.set_xlabel('Obstáculos')
    ax.set_ylabel('Completitud (%)')
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=.2)
    ax.legend()
    fig.suptitle('John Deere · Etapa 4 · Comparación de arquitecturas', fontsize=19, weight='bold')
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)


def plot_effects(pairs, path):
    """Efectos pareados e IC del 95 %, sin mezclar unidades entre métricas."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selected = ('cobertura_pct', 'ticks', 'distancia_total', 'combustible_total',
                'espera_total', 'J')
    densities = sorted(pairs.density.unique())
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout='constrained')
    for ax, metric in zip(axes.flat, selected):
        subset = pairs[pairs.metric == metric].sort_values('density')
        y = subset.mean_improvement.to_numpy(dtype=float)
        lo = subset.ci95_low.to_numpy(dtype=float)
        hi = subset.ci95_high.to_numpy(dtype=float)
        ax.errorbar(range(len(subset)), y, yerr=[y-lo, hi-y], fmt='o', capsize=5)
        ax.axhline(0, color='gray', linestyle='--', linewidth=1)
        ax.set_xticks(range(len(subset)), [f'{d:.0%}' for d in subset.density])
        ax.set_title(metric)
        ax.set_xlabel('Densidad de obstáculos')
        ax.set_ylabel('Mejora improved - baseline')
        ax.grid(alpha=.15)
    fig.suptitle('Diferencias pareadas con IC 95 % (positivo favorece improved)')
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)


def report(summary, pairs, path):
    lines = ['# Etapa 4 — Resultados experimentales', '',
             'Diseño pareado: mismas semillas y densidades para baseline e improved.',
             'Diferencia = mejora positiva (reducción de costes o aumento de cobertura).',
             'IC 95%: intervalo t de Student de diferencias pareadas, no ajustado por comparaciones múltiples.',
             '**Advertencia:** los ticks están censurados en 3000 si el episodio no termina;',
             'por tanto las comparaciones de tiempo y J pueden reflejar fallos de finalización,',
             'no únicamente eficiencia. Interpretar cobertura y tasa de finalización primero.', '',
             '## Resumen', '', summary.round(3).to_markdown(index=False), '',
             '## Diferencias pareadas e intervalos de confianza', '',
             pairs.round(3).to_markdown(index=False), '',
             '## Limitaciones', '',
             '- Entorno discretizado, combustible y obstáculos idealizados.',
             '- Semillas emparejadas controlan el mapa, pero las decisiones de cada arquitectura difieren.',
             '- Intervalos t descriptivos/exploratorios; no garantizan normalidad ni corrigen multiplicidad.',
             '- La comparación no demuestra rendimiento en maquinaria física.',
             '- Analizar por separado escenarios incompletos y métricas penalizadas por límite de ticks.',
             '- El dashboard CSV muestra completitud y desempeño; no reconstruye trayectorias espaciales.', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='results/stage4')
    p.add_argument('--from-csv', type=Path)
    p.add_argument('--seeds', type=int, default=20)
    p.add_argument('--skip-dashboard', action='store_true')
    args = p.parse_args(argv)
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    if args.from_csv:
        df = pd.read_csv(args.from_csv)
    else:
        df = simulate(seeds=range(args.seeds))
    df.to_csv(out/'episodes.csv', index=False)
    summary, pairs = analyze(df)
    summary.to_csv(out/'summary.csv', index=False)
    pairs.to_csv(out/'paired_ci.csv', index=False)
    report(summary, pairs, out/'REPORT.md')
    plot_effects(pairs, out/'paired_effects.png')
    if not args.skip_dashboard:
        dashboard(df, summary, pairs, out/'dashboard.png')
    print(f'Guardado en {out.resolve()} ({len(df)} episodios)')


if __name__ == '__main__':
    main()
