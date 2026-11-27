# John Deere — Simulación multiagente de siembra autónoma

Proyecto académico de simulación de **tres tractores autónomos** en un campo discretizado, desarrollado en Python con **AgentPy**. Compara una arquitectura **baseline** (trabajo por franjas, sin Blackboard) con una arquitectura **improved** (asignación dinámica de tareas y coordinación centralizada mediante Blackboard).

## Objetivo

Sembrar todas las celdas válidas de un campo de **15 × 15**, evitando rocas, colisiones y resiembras, con combustible y semillas limitados. Los tractores pueden reabastecerse en la gasolinera **G** `(14, 4)` y la estación de semillas **S** `(14, 10)`.

## Arquitecturas

| Baseline | Improved |
|---|---|
| Franjas de trabajo fijas | Franjas iniciales y redistribución de tareas |
| Navegación A* | Navegación A* considerando ocupación dinámica |
| Decisiones individuales | Coordinación mediante Blackboard |
| Conflictos resueltos por reglas del mundo | Prevención de conflictos, reservas y cesión de paso |
| Reabastecimiento reactivo | Reservas de combustible y liberación de la gasolinera |

El planificador **A\*** tiene en cuenta distancia y cambios de orientación. El motor de reglas valida las acciones, actualiza recursos y contabiliza métricas. El Blackboard coordina los movimientos propuestos por los tractores, pero **WorldState** determina su ejecución efectiva.

## Requisitos

- Python 3 compatible con las dependencias del proyecto.
- `pip` y `venv`.
- Dependencias indicadas en `requirements.txt`.
- `tabulate` para generar `REPORT.md` con `pandas.DataFrame.to_markdown()`; se instala junto con las demás dependencias.

### Instalación

Desde la **raíz del repositorio**:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Windows (PowerShell), activar con `.venv\Scripts\Activate.ps1`.

> En Arch Linux, usar un entorno virtual evita el error `externally-managed-environment` de instalaciones globales con pip.

## Ejecutar el proyecto

### Pruebas automatizadas

```bash
python -m pytest -q
```

### Simulación rápida

```bash
python -m experiments.quick_run
```

### Validación de la etapa 3

```bash
python -m experiments.validate_stage3
```

Ejecuta **60 escenarios de la arquitectura improved**: tres densidades de obstáculos (0 %, 5 %, 10 %) y semillas 0–19. Verifica cobertura, finalización y acciones rechazadas.

### Experimento de la etapa 4

```bash
python -m experiments.stage4 --output results/stage4
```

Ejecuta **120 episodios** (dos arquitecturas × tres densidades × 20 semillas emparejadas) y genera:

| Archivo | Contenido |
|---|---|
| `episodes.csv` | Métricas por episodio |
| `summary.csv` | Resumen por arquitectura y densidad |
| `paired_ci.csv` | Diferencias pareadas e intervalos de confianza del 95 % |
| `dashboard.png` | Comparación de cobertura, tiempo, distancia, combustible, J y completitud |
| `paired_effects.png` | Efectos pareados e intervalos por métrica |
| `REPORT.md` | Informe estadístico generado automáticamente |

**Reanalizar resultados sin volver a simular:**

```bash
python -m experiments.stage4 \
  --from-csv results/stage4/episodes.csv \
  --output results/stage4
```

**Prueba experimental corta** (no usar para conclusiones):

```bash
python -m experiments.stage4 --seeds 2 --output results/smoke
```

### Dashboard en Jupyter

Abre `notebooks/dashboard_experimentos.ipynb` desde la raíz del repositorio o ejecuta:

```bash
jupyter lab notebooks/dashboard_experimentos.ipynb
```

Por defecto, el notebook usa los CSV existentes, reconstruye las gráficas sin volver a correr las simulaciones y muestra las visualizaciones guardadas en `results/`. Activa `REBUILD_STAGE4_FROM_CSV` para recalcular las tablas y el informe; activa `RUN_FULL_STAGE4_SIMULATION` para correr los 120 episodios desde cero. También puedes regenerar las visualizaciones complementarias, ejecutar `quick_run`, validar la etapa 3 o correr el diagnóstico desde la celda de configuración.

El script `experiments.visualizaciones` genera gráficos de evolución temporal, mapa del campo y distribución de ticks:

```bash
python -m experiments.visualizaciones
```

## Resultados experimentales (etapa 4)

Se ejecutaron 120 episodios (2 arquitecturas × 3 densidades × 20 semillas). Los resultados provienen de results/stage4/episodes.csv.

| Obstáculos | Baseline: completados | Improved: completados | Ticks promedio baseline | Ticks promedio improved |
|---|---:|---:|---:|---:|
| 0 % | 20/20 | 20/20 | 331.00 | 254.00 |
| 5 % | 19/20 | 20/20 | 435.75 | 265.55 |
| 10 % | 20/20 | 20/20 | 296.85 | 269.80 |

- **Improved completó 60/60** episodios; baseline, **59/60**.
- Improved registró **cero colisiones** en los escenarios evaluados; baseline registró colisiones.
- Improved redujo la distancia recorrida media en las tres densidades.
- La ejecución incompleta de baseline (5 %, semilla 16) alcanzó el límite de **3000 ticks** y afecta los promedios; por tanto, la comparación de tiempo al 5 % debe interpretarse con cautela.
- La función objetivo **J** penaliza cada colisión con un peso elevado (1000); una diferencia grande en J no equivale a la misma reducción porcentual en tiempo o combustible.
- Los intervalos de confianza son **exploratorios**, basados en diferencias pareadas y sin corrección por comparaciones múltiples.

Consulta el reporte final del proyecto para la explicación metodológica, la interpretación de las métricas y las limitaciones.

### Visualizaciones adicionales

visualizaciones.py y sensibilidad_J.py requieren haber generado antes results/stage4/episodes.csv; secuencia_estados.py y sensibilidad.py simulan por su cuenta. 

```bash
python -m experiments.visualizaciones
python -m experiments.secuencia_estados
python -m experiments.sensibilidad
python -m experiments.sensibilidad_J
```

| Script | Qué hace | Salida |
|---|---|---|
| `visualizaciones.py` | Evolución temporal de la cobertura (baseline vs improved), mapa 2D final y distribución de ticks | `results/visualizaciones/` |
| `secuencia_estados.py` | Simula un episodio (improved, 10 %, semilla 0) y dibuja el mapa en 4 momentos con las trayectorias de los tractores | `results/visualizaciones/secuencia_estados.png` |
| `sensibilidad.py` | Simula 120 episodios variando la capacidad de combustible (ambas arquitecturas) y el umbral de semillas (improved) al 10 % de obstáculos | `results/sensibilidad/` |
| `sensibilidad_J.py` | Recalcula J con distintos pesos de colisiones usando `episodes.csv`, sin simular de nuevo | `results/sensibilidad/sensibilidad_pesos_J.csv` y `.png` |

## Estructura del repositorio

```text

.
├── config/
│   └── params.yaml            # Campo, tractores, costes y pesos
├── src/
│   ├── agents.py              # Arquitectura baseline
│   ├── improved.py            # Decisiones de la arquitectura improved
│   ├── blackboard.py          # Coordinación y asignación de tareas
│   ├── planner.py             # Rutas A* y utilidades de búsqueda
│   ├── world.py               # Campo y obstáculos
│   ├── state.py               # Estado de los tractores
│   ├── rules.py               # Reglas y métricas
│   └── model.py               # Modelo AgentPy
├── experiments/
│   ├── quick_run.py
│   ├── validate_stage3.py
│   ├── diagnose_deadlock.py
│   ├── stage4.py
│   ├── visualizaciones.py
│   ├── secuencia_estados.py
│   ├── sensibilidad.py
│   └── sensibilidad_J.py
├── tests/                     # Pruebas unitarias e integración
├── results/                   # Salidas generadas (CSV y figuras)
├── requirements.txt
└── pytest.ini
```

## Métricas

Se miden cobertura, episodios completados, ticks, distancia, combustible, esperas, colisiones, acciones rechazadas, resiembras, desbalance y la función objetivo:

\[
J = T + 0.5D + 1000C + 0.5W + 0.2E + \Delta
\]

Donde `T` son ticks, `D` distancia, `C` colisiones, `W` esperas, `E` combustible y `Δ` desbalance. **Menor J es mejor**, siempre interpretándolo junto con la cobertura y la finalización.

## Reproducibilidad y limitaciones

- Comparar las arquitecturas con las **mismas semillas** y densidades.
- No cambiar los parámetros entre ejecuciones que se pretendan comparar directamente.
- El límite de 3000 ticks **censura** los tiempos de episodios incompletos.
- El modelo es discreto e idealizado; sus resultados **no prueban desempeño en maquinaria real**.
- Los CSV de métricas finales no permiten reconstruir trayectorias por tick. Para ver la evolución temporal y las trayectorias se vuelve a simular un episodio concreto con `visualizaciones.py` y `secuencia_estados.py`, sin modificar las reglas del modelo.
- Los barridos de sensibilidad usan 10 semillas y un solo nivel de obstáculos (10 %); sus resultados son exploratorios y no sustituyen el experimento principal de 20 semillas.

### Sensibilidad

- Capacidad de combustible: Con 60 unidades, improved se bloquea (3/10 completados) mientras que baseline sigue operando (341 ticks). Con 100 y 120, improved completa todo pero pierde su ventaja en velocidad frente a baseline (315 vs. 261 y 305 vs. 240 ticks) debido al costo de coordinación. Su superioridad temporal depende estrictamente de las 80 unidades actuales.

- Umbral de semillas: Todas completan el 100 %. Un umbral de 5 da el mejor tiempo medio (improved en 258 ticks vs. 277 actuales), aunque con desviaciones de 25–30 ticks la diferencia no es concluyente. Subirlo a 10 sí empeora el rendimiento (326 ticks) por visitas excesivas a S.

- Peso de colisiones en J: Improved supera a baseline desde $\lambda_3 = 0$ en todas las densidades. No obstante, con 10 % de obstáculos y pesos bajos ($\lambda_3 \le 1$), solo gana en el 75 %–80 % de los pares, alcanzando el 100 % de efectividad a partir de $\lambda_3 \ge 100$.

## Documentación

Los archivos `ETAPA4.md`, `ETAPA3_VALIDACION.md`, `ETAPA3_NOTAS.md` y los documentos de diagnóstico/corrección describen decisiones y validaciones de desarrollo. El reporte académico final puede conservarse en `docs/`.

## Contexto

Proyecto académico del reto John Deere para la materia de sistemas multiagente. Consultar el reporte final para integrantes, docente y referencias institucionales.

## Demostración de tractores entrenados en Unity

Para iniciar el escenario reproducible de Unity con las tablas entrenadas incluidas, ejecuta `run_unity_demo.bat` en Windows y después pulsa Play en `Assets/Scenes/SampleScene.unity` del proyecto Unity. El lanzador prepara las dependencias del servidor en el primer uso. Los pasos, el formato de comunicación y el comando manual están en [UNITY_INTEGRATION.md](UNITY_INTEGRATION.md).

En la pantalla de configuración de Unity se puede seleccionar la densidad, semilla, arquitectura, Q-learning y posiciones iniciales fijas o aleatorias. Para evaluaciones Q-learning con inicios aleatorios y los resultados de referencia, consulta [docs/EVALUACION_QLEARNING_INICIOS_ALEATORIOS.md](docs/EVALUACION_QLEARNING_INICIOS_ALEATORIOS.md).
