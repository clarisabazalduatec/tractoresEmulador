# Dashboard de experimentos

El dashboard interactivo está en `notebooks/dashboard_experimentos.ipynb`. Desde la raíz del repositorio, instala las dependencias y abre el notebook:

```powershell
python -m pip install -r requirements.txt
jupyter lab notebooks/dashboard_experimentos.ipynb
```

En Jupyter, ejecuta las celdas de arriba hacia abajo. Las gráficas y tablas se construyen desde los CSV disponibles; no se inicia ninguna simulación hasta pulsar el botón de regeneración de telemetría.

## Etapas que presenta

1. **Baseline + A\*:** trabajo por franjas y decisiones individuales.
2. **Improved + A\* + Blackboard:** asignación coordinada de tareas y prevención de conflictos.
3. **Improved + A\* + Blackboard + Q-learning:** usa Q-learning para decidir el reabastecimiento de semillas. La selección de celdas de trabajo y el combustible siguen fuera de la política aprendida.

OpenClaw y MCP son posibilidades futuras, no componentes implementados.

## Archivos de resultados

| Archivo | Uso |
|---|---|
| `results/stage4/episodes.csv` | Fuente principal para baseline e improved; una fila por arquitectura, densidad y semilla. Incluye las métricas finales y la bandera `completo`. |
| `results/qlearning*/episodes.csv` | Fuente opcional por experimento Q-learning. Debe incluir `phase` (`train`/`eval`), `architecture`, `density`, `seed` y las métricas. Cada carpeta se analiza separada. |
| `results/qlearning*/policies.json` | Política aprendida que permite intentar regenerar la telemetría de la evaluación Q de esa carpeta. No contiene por sí sola un manifiesto suficiente de parámetros. |
| `docs/evaluations/qlearning_random_starts/episodes.csv` | Evaluación versionada de la política de demostración con posiciones iniciales aleatorias; utiliza `config/qlearning_demo_policies.json` para reproducir episodios. |
| `results/visualizaciones/*.png` | Figuras complementarias ya generadas. El notebook puede regenerar cobertura y trayectorias de un episodio seleccionado en memoria. |

El dashboard recalcula los resúmenes desde `episodes.csv`; `summary.csv`, `paired_ci.csv`, `summary.json` y los PNG son productos derivados, no fuentes necesarias para sus tablas principales.

### Regenerar resultados

Para volver a ejecutar el diseño baseline/improved (120 episodios por defecto, 20 semillas por densidad):

```powershell
python -m experiments.stage4 --output results/stage4
```

Para rehacer solo tablas e imágenes a partir del CSV existente:

```powershell
python -m experiments.stage4 --from-csv results/stage4/episodes.csv --output results/stage4
```

La evaluación de Q-learning se ejecuta con `python -m experiments.evaluate_qlearning --help` para revisar los argumentos disponibles antes de correrla. La fase de entrenamiento actualiza la política; la fase de evaluación usa episodios separados y debe conservarse como `phase=eval`. No interpretes métricas de entrenamiento como evaluación.

Para ver cómo se genera la telemetría de cobertura y posiciones, el flujo original está en `experiments/visualizaciones.py` y `experiments/secuencia_estados.py`. Ambos vuelven a ejecutar episodios; los CSV de etapa 4 no contienen trayectorias por tick.

## Comparaciones y límites

- La comparación baseline/improved empareja por densidad y semilla dentro de `results/stage4/episodes.csv`. La configuración en uso define 15 × 15, tres tractores, posiciones iniciales de `config/params.yaml` y un límite de 3000 ticks. El CSV no guarda una huella de configuración; el notebook presenta el contexto del YAML disponible y avisa de esta limitación.
- Un episodio con `completo=false` llegó al límite de ticks sin cubrir todas las celdas. Sus ticks están censurados en ese tope. El dashboard lo identifica y no mezcla silenciosamente sus métricas terminales con las de episodios completos.
- Q-learning se compara con improved solo dentro del mismo CSV, fase `eval`, densidad y semilla. No se combinan distintas carpetas Q ni se mezclan con etapa 4. El archivo de evaluación actual registra la fase, densidad, semilla y métricas, pero no un manifiesto con modo de posiciones iniciales, parámetros completos de entrenamiento o huella de configuración. Por eso esos resultados se muestran como exploratorios y no se atribuye una mejora general a Q-learning.
- La tabla admite columnas opcionales `start_mode` (también `initial_positions_mode`), `start_seed` (también `initial_positions_seed`), `scenario_id`, las posiciones iniciales serializadas y `config_hash`. Si aparecen, el dashboard filtra y empareja también por esas claves; si no, deja explícito que el modo de inicio no está declarado y no permite inferirlo por la semilla del mapa.
- Los efectos pareados son descriptivos. Los ticks de episodios truncados alcanzan el límite; distancia, combustible y esperas se interpretan entre episodios completados en la tabla de pares, con los tamaños de muestra visibles.
- Los artefactos bajo `results/` están excluidos por `.gitignore`. Para compartir el análisis, copia la carpeta de resultados necesaria junto con el repositorio, o adjunta los CSV y la política correspondiente. Conserva carpetas Q separadas y el mismo `episodes.csv` que produjo cada resumen; no renombres ni combines cohortes distintas.

