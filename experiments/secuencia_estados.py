from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.model import FarmModel

SALIDA = Path('results') / 'visualizaciones'
SALIDA.mkdir(parents=True, exist_ok=True)

ARQUITECTURA = 'improved'
DENSIDAD = 0.10
SEMILLA = 0


class ModeloConSnapshots(FarmModel):
    def setup(self):
        self.snapshots = []
        super().setup()

    def update(self):
        super().update()
        w = self.world
        self.snapshots.append((w.t, w.M.copy(), [t.pos for t in w.tractors]))


modelo = ModeloConSnapshots({'architecture': ARQUITECTURA,'obstacle_density': DENSIDAD,'seed': SEMILLA})
modelo.run(display=False)
w = modelo.world
snaps = modelo.snapshots
if snaps[-1][0] != w.t:
    snaps.append((w.t, w.M.copy(), [t.pos for t in w.tractors]))

total = len(snaps)
indices = [0, total // 3, 2 * total // 3, total - 1]

campo = w.field
n = campo.size
colores = ListedColormap(['#fff3cd', '#78b77b', '#545454', '#4c82d6', '#e5a44b'])
colores_tractor = ['#d62728', '#9467bd', '#17becf']

fig, ejes = plt.subplots(1, 4, figsize=(18, 5.5))
for ax, i in zip(ejes, indices):
    tick, M, posiciones = snaps[i]
    mapa = np.zeros((n, n), dtype=int)
    for r, c in campo.sowable:
        mapa[r, c] = 1 if M[r, c] else 0
        
    for r, c in campo.obstacles:
        mapa[r, c] = 2
    mapa[campo.gas] = 3
    mapa[campo.seed_station] = 4
    ax.imshow(mapa, cmap=colores, vmin=-0.5, vmax=4.5, interpolation='nearest')

    for k in range(len(w.tractors)):
        ruta = np.array([s[2][k] for s in snaps[:i + 1]])
        ax.plot(ruta[:, 1], ruta[:, 0], color=colores_tractor[k], linewidth=1, alpha=0.6)
        r, c = posiciones[k]
        ax.scatter(c, r, s=110, marker='s', color=colores_tractor[k],edgecolor='black', zorder=3)

    cobertura = 100 * float(M.sum()) / len(campo.sowable)
    ax.set_title(f'Tick {tick} · cobertura {cobertura:.1f}%')
    ax.set_xticks(range(0, n, 2))
    ax.set_yticks(range(0, n, 2))
    ax.set_xlabel('Columna')
ejes[0].set_ylabel('Fila')

etiquetas = ['Sin sembrar', 'Sembrada', 'Obstáculo', 'Gasolinera G', 'Semillas S']
manijas = [Patch(color=colores(i), label=e) for i, e in enumerate(etiquetas)]
manijas += [Line2D([0], [0], marker='s', color='w', markerfacecolor=colores_tractor[k], markeredgecolor='black', markersize=9, label=f'Tractor T{k + 1}') for k in range(len(w.tractors))]
fig.legend(handles=manijas, loc='lower center', ncol=8, fontsize=9)

fig.suptitle(f'Secuencia de estados: {ARQUITECTURA}, {DENSIDAD:.0%} obstáculos, semilla {SEMILLA}')
fig.tight_layout(rect=(0, 0.07, 1, 0.95))

fig.savefig(SALIDA / 'secuencia_estados.png', dpi=160, bbox_inches='tight')
plt.close(fig)
print('Guardado en', (SALIDA / 'secuencia_estados.png').resolve())