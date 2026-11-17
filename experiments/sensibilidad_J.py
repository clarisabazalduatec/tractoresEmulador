from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from src.model import DEFAULT_CONFIG
from src.world import load_params

SALIDA = Path('results') / 'sensibilidad'
SALIDA.mkdir(parents=True, exist_ok=True)

LAMBDAS_COLISION = [0, 1, 10, 100, 1000]

w = load_params(DEFAULT_CONFIG)['objective_weights']
pesos = {'ticks': w['lambda1'], 'distancia_total': w['lambda2'],
         'espera_total': w['lambda4'], 'combustible_total': w['lambda5'],
         'desbalance': w['lambda6']}


def j_con(df, lam3):
    return sum(p * df[c] for c, p in pesos.items()) + lam3 * df['colisiones']


datos = pd.read_csv('results/stage4/episodes.csv')
filas = []
for densidad, grupo in datos.groupby('density'):
    base = grupo[grupo.architecture == 'baseline'].set_index('seed').sort_index()
    mejor = grupo[grupo.architecture == 'improved'].set_index('seed').sort_index()
    for lam in LAMBDAS_COLISION:
        dif = j_con(base, lam) - j_con(mejor, lam)
        filas.append({'density': densidad, 'lambda3': lam,
                      'mejora_media_J': dif.mean(),
                      'pct_pares_improved_mejor': 100 * float((dif > 0).mean())})
tabla = pd.DataFrame(filas)
tabla.to_csv(SALIDA / 'sensibilidad_pesos_J.csv', index=False)
print(tabla.round(2).to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 4.5))
for densidad, g in tabla.groupby('density'):
    ax.plot(g.lambda3, g.mejora_media_J, marker='o', label=f'{densidad:.0%} obstáculos')
ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_xscale('symlog', linthresh=1)
ax.set_xlabel('Peso de colisiones (λ3)')
ax.set_ylabel('Mejora media de J (baseline - improved)')
ax.set_title('Sensibilidad de J al peso de colisiones')
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(SALIDA / 'sensibilidad_pesos_J.png', dpi=160)
plt.close(fig)