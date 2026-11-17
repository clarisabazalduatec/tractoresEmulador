"""Tres visualizaciones para el proyecto John Deere.
Ejecutar desde la raiz del repositorio: py -m experiments.visualizaciones
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from src.model import FarmModel

SALIDA = Path('results') / 'visualizaciones'
SALIDA.mkdir(parents=True, exist_ok=True)


class ModeloConHistorial(FarmModel):
    """Guarda cobertura por tick sin cambiar las reglas del modelo."""

    def setup(self):
        self.historial_cobertura = []
        super().setup()

    def update(self):
        super().update()
        mundo = self.world
        cobertura = 100 * float(mundo.M.sum()) / len(mundo.field.sowable)
        self.historial_cobertura.append(cobertura)


# 1. Evolucion temporal: misma densidad/semilla para comparar arquitecturas.
plt.figure(figsize=(9, 5))
modelo_mapa = None
for arquitectura in ('baseline', 'improved'):
    modelo = ModeloConHistorial({
        'architecture': arquitectura,
        'obstacle_density': 0.10,
        'seed': 0,
    })
    modelo.run(display=False)
    plt.plot(range(1, len(modelo.historial_cobertura) + 1),
             modelo.historial_cobertura, label=arquitectura)
    if arquitectura == 'improved':
        modelo_mapa = modelo
plt.title('Evolución de cobertura (10% obstáculos, semilla 0)')
plt.xlabel('Tick (paso de simulación)')
plt.ylabel('Cobertura sembrada (%)')
plt.ylim(0, 105)
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(SALIDA / 'evolucion_temporal.png', dpi=160)
plt.close()


# 2. Mapa 2D del estado final real.
mundo = modelo_mapa.world
campo = mundo.field
n = campo.size
# 0: sin sembrar, 1: sembrada, 2: obstáculo, 3: gas, 4: semillas
mapa = np.zeros((n, n), dtype=int)
for r, c in campo.sowable:
    mapa[r, c] = 1 if mundo.M[r, c] else 0
for r, c in campo.obstacles:
    mapa[r, c] = 2
mapa[campo.gas] = 3
mapa[campo.seed_station] = 4
colores = ListedColormap(['#fff3cd', '#78b77b', '#545454', '#4c82d6', '#e5a44b'])
fig, ax = plt.subplots(figsize=(8, 7))
ax.imshow(mapa, cmap=colores, vmin=-0.5, vmax=4.5, interpolation='nearest')
for tractor in mundo.tractors:
    r, c = tractor.pos
    ax.text(c, r, f'T{tractor.id}', ha='center', va='center',
            fontweight='bold', color='black', fontsize=9,
            bbox=dict(facecolor='white', edgecolor='black', alpha=.9, pad=2))
ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticks(np.arange(-.5, n, 1), minor=True)
ax.set_yticks(np.arange(-.5, n, 1), minor=True)
ax.grid(which='minor', color='white', linewidth=1)
ax.tick_params(which='minor', bottom=False, left=False)
ax.set_xlabel('Columna')
ax.set_ylabel('Fila')
ax.set_title('Mapa final: improved, 10% obstáculos, semilla 0')
ax.legend(handles=[Patch(color=colores(i), label=etiqueta) for i, etiqueta in
                   enumerate(['Sin sembrar', 'Sembrada', 'Obstáculo', 'Gas G', 'Semillas S'])],
          loc='upper center', bbox_to_anchor=(.5, -.08), ncol=3, fontsize=9)
fig.tight_layout()
fig.savefig(SALIDA / 'mapa_color.png', dpi=160, bbox_inches='tight')
plt.close(fig)


# 3. Distribución de ticks de los 120 episodios que ya existen.
archivo_csv = Path('results/stage4/episodes.csv')
if not archivo_csv.exists():
    raise FileNotFoundError('No existe results/stage4/episodes.csv')
datos = pd.read_csv(archivo_csv)
fig, ejes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for ax, (densidad, grupo) in zip(ejes, datos.groupby('density')):
    base = grupo.loc[grupo['architecture'] == 'baseline', 'ticks']
    mejora = grupo.loc[grupo['architecture'] == 'improved', 'ticks']
    ax.boxplot([base, mejora], tick_labels=['Baseline', 'Improved'])
    ax.set_title(f'Obstáculos: {densidad:.0%}')
    ax.grid(axis='y', alpha=0.3)
ejes[0].set_ylabel('Ticks por episodio (máximo 3000)')
fig.suptitle('Distribución de tiempo por arquitectura y densidad')
fig.tight_layout()
fig.savefig(SALIDA / 'distribuciones.png', dpi=160)
plt.close(fig)
print('Listo. Gráficas guardadas en:', SALIDA.resolve())
print('Nota: una corrida baseline de 5% no terminó y llegó al límite de 3000 ticks.')
