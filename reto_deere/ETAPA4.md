# Etapa 4 — Experimentos y análisis estadístico

## Diseño

Se comparan **baseline** e **improved** en densidades de obstáculos 0 %, 5 % y 10 %, con 20 semillas (0–19) por densidad y arquitectura: **120 episodios**. Las semillas se emparejan entre arquitecturas para comparar bajo la misma generación del entorno.

Se registran cobertura, terminación, ticks, distancia, combustible, esperas, colisiones, rechazos, resiembras, desbalance y función objetivo J. Se calculan diferencias pareadas (positivas = mejora) e intervalos t de Student al 95 %. La inferencia es exploratoria; se incluyen valores p sin corrección por pruebas múltiples.

## Ejecución

Desde la raíz del proyecto, con las dependencias de `requirements.txt` instaladas:

```bash
pytest -q
python -m experiments.stage4 --output results/stage4
```

El experimento guarda `episodes.csv` (120 filas), `summary.csv`, `paired_ci.csv`, `REPORT.md` y `dashboard.png` (dashboard estático con un mapa 2D real de la simulación).

Para recalcular tablas e intervalos sin volver a simular:

```bash
python -m experiments.stage4 --from-csv results/stage4/episodes.csv --output results/stage4
```

Para una prueba rápida (no apta para conclusiones estadísticas):

```bash
python -m experiments.stage4 --seeds 2 --output results/smoke
```

## Interpretación y cautelas

- Comparar primero cobertura y proporción de episodios completos. El límite de 3000 ticks **censura** los episodios incompletos.
- Una reducción de J no necesariamente implica éxito si hay coberturas distintas; reportar ambas.
- Los intervalos pareados reflejan variación entre semillas, no incertidumbre física de un tractor real.
- No modificar parámetros o pesos de J después de observar resultados sin declararlo como análisis exploratorio.
- El dashboard es estático; la rúbrica permite un dashboard estático bien diseñado. Se pueden añadir visualizaciones temporales en etapas posteriores.

## Mejoras de validación y visualización

- `summary.csv` incorpora `tasa_completitud_pct`.
- `paired_ci.csv` incorpora `completitud_pp` (diferencia pareada en puntos porcentuales).
- `paired_effects.png` muestra intervalos de confianza por métrica, cada una con su propia escala.
- `dashboard.png` puede regenerarse a partir de `episodes.csv` **sin ejecutar AgentPy**.
- Para reconstruir trayectorias y una animación 2D será necesario conservar telemetría espacial por tick; los CSV de métricas finales no contienen esa información.
- Si baseline no termina, no interpretar menor `J` como una victoria sin examinar cobertura y completitud.
