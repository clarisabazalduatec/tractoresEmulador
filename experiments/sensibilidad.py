from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt

from src.model import DEFAULT_CONFIG, run_episode

SALIDA = Path('results') / 'sensibilidad'
SALIDA.mkdir(parents=True, exist_ok=True)

DENSIDAD = 0.10
SEMILLAS = range(10)
COLORES = {'baseline': '#c77955', 'improved': '#387f92'}
BARRIDOS = [
    ('tractors', 'fuel_capacity', [60.0, 80.0, 100.0, 120.0], ('baseline', 'improved'), 'Capacidad de combustible'),
    ('dispatch', 'seed_threshold', [0, 2, 5, 10], ('improved',), 'Umbral de semillas para ir a S'),
]


def correr(seccion, clave, valores, arquitecturas):
    ruta = SALIDA / 'config_temporal.yaml'
    filas = []
    for valor in valores:
        cfg = yaml.safe_load(Path(DEFAULT_CONFIG).read_text(encoding='utf-8'))
        cfg[seccion][clave] = valor
        ruta.write_text(yaml.safe_dump(cfg), encoding='utf-8')
        for arq in arquitecturas:
            for semilla in SEMILLAS:
                _, r = run_episode(arq, DENSIDAD, semilla, config_path=str(ruta))
                filas.append({'parametro': clave, 'valor': valor, 'arquitectura': arq,
                              'seed': semilla, 'completo': float(bool(r['completo'])),
                              'ticks': r['ticks'],
                              'combustible_total': r['combustible_total'],
                              'J': r['J']})
                print(f'{clave}={valor} {arq:8s} seed={semilla:02d} '
                      f'ticks={int(r["ticks"])} completo={bool(r["completo"])}', flush=True)
    return filas


def graficar(df, clave, etiqueta, archivo):
    sub = df[df.parametro == clave]
    fig, ejes = plt.subplots(1, 3, figsize=(14, 4))
    for arq, color in COLORES.items():
        g = sub[sub.arquitectura == arq]
        if g.empty:
            continue
        r = g.groupby('valor').agg(t=('ticks', 'mean'), t_sd=('ticks', 'std'), c=('combustible_total', 'mean'), c_sd=('combustible_total', 'std'), comp=('completo', 'mean'))
        ejes[0].errorbar(r.index, r.t, yerr=r.t_sd, marker='o', capsize=3, color=color, label=arq)
        ejes[1].errorbar(r.index, r.c, yerr=r.c_sd, marker='o', capsize=3, color=color, label=arq)
        ejes[2].plot(r.index, 100 * r.comp, marker='o', color=color, label=arq)

    ejes[0].set_ylabel('Ticks (media ± desv. est.)')
    ejes[1].set_ylabel('Combustible consumido (media ± desv. est.)')
    ejes[2].set_ylabel('Episodios completados (%)')
    ejes[2].set_ylim(0, 105)

    for ax in ejes:
        ax.set_xlabel(etiqueta)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle(f'Sensibilidad: {etiqueta} ({DENSIDAD:.0%} obstáculos, {len(SEMILLAS)} semillas)')
    fig.tight_layout()
    fig.savefig(archivo, dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    filas = []
    for seccion, clave, valores, arqs, _ in BARRIDOS:
        filas += correr(seccion, clave, valores, arqs)
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / 'sensibilidad.csv', index=False)
    for _, clave, _, _, etiqueta in BARRIDOS:
        graficar(df, clave, etiqueta, SALIDA / f'sensibilidad_{clave}.png')
    print('Guardado en', SALIDA.resolve())


if __name__ == '__main__':
    main()