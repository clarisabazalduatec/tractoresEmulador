# Etapa 4 — Resultados experimentales

Diseño pareado: mismas semillas y densidades para baseline e improved.
Diferencia = mejora positiva (reducción de costes o aumento de cobertura).
IC 95%: intervalo t de Student de diferencias pareadas, no ajustado por comparaciones múltiples.
**Advertencia:** los ticks están censurados en 3000 si el episodio no termina;
por tanto las comparaciones de tiempo y J pueden reflejar fallos de finalización,
no únicamente eficiencia. Interpretar cobertura y tasa de finalización primero.

## Resumen

|   density | architecture   |   n |   completos |   cobertura_media |   ticks_media |   distancia_media |   combustible_medio |   esperas_medias |   colisiones_medias |   J_medio |   tasa_completitud_pct |
|----------:|:---------------|----:|------------:|------------------:|--------------:|------------------:|--------------------:|-----------------:|--------------------:|----------:|-----------------------:|
|      0    | baseline       |  20 |          20 |           100     |        331    |            611    |             644     |             5    |               18    | 18843.8   |                    100 |
|      0    | improved       |  20 |          20 |           100     |        254    |            490    |             537.1   |            11    |                0    |   617.92  |                    100 |
|      0.05 | baseline       |  20 |          19 |            99.953 |        435.75 |            569.8  |             625.4   |           140.2  |               11.35 | 12324.9   |                     95 |
|      0.05 | improved       |  20 |          20 |           100     |        265.55 |            527    |             608.365 |            29.15 |                0    |   684.098 |                    100 |
|      0.1  | baseline       |  20 |          20 |           100     |        296.85 |            569.95 |             649.315 |             3.65 |                8    |  8775.36  |                    100 |
|      0.1  | improved       |  20 |          20 |           100     |        269.8  |            520.95 |             611.95  |            36.75 |                0    |   702.54  |                    100 |

## Diferencias pareadas e intervalos de confianza

|   density | metric              |   n |   mean_improvement |   ci95_low |   ci95_high |   p_value_exploratory |   baseline_complete |   improved_complete |
|----------:|:--------------------|----:|-------------------:|-----------:|------------:|----------------------:|--------------------:|--------------------:|
|      0    | completitud_pp      |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0    | ticks               |  20 |             77     |     77     |      77     |                 0     |                  20 |                  20 |
|      0    | cobertura_pct       |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0    | distancia_total     |  20 |            121     |    121     |     121     |                 0     |                  20 |                  20 |
|      0    | combustible_total   |  20 |            106.9   |    106.9   |     106.9   |                 0     |                  20 |                  20 |
|      0    | espera_total        |  20 |             -6     |     -6     |      -6     |                 0     |                  20 |                  20 |
|      0    | colisiones          |  20 |             18     |     18     |      18     |                 0     |                  20 |                  20 |
|      0    | acciones_rechazadas |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0    | resiembras          |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0    | desbalance          |  20 |             70     |     70     |      70     |                 0     |                  20 |                  20 |
|      0    | J                   |  20 |          18225.9   |  18225.9   |   18225.9   |                 0     |                  20 |                  20 |
|      0.05 | completitud_pp      |  20 |              5     |     -5.465 |      15.465 |                 0.33  |                  19 |                  20 |
|      0.05 | ticks               |  20 |            170.2   |   -111.544 |     451.944 |                 0.221 |                  19 |                  20 |
|      0.05 | cobertura_pct       |  20 |              0.047 |     -0.052 |       0.146 |                 0.33  |                  19 |                  20 |
|      0.05 | distancia_total     |  20 |             42.8   |     11.445 |      74.155 |                 0.01  |                  19 |                  20 |
|      0.05 | combustible_total   |  20 |             17.035 |    -21.022 |      55.092 |                 0.361 |                  19 |                  20 |
|      0.05 | espera_total        |  20 |            111.05  |   -174.741 |     396.841 |                 0.426 |                  19 |                  20 |
|      0.05 | colisiones          |  20 |             11.35  |      8.488 |      14.212 |                 0     |                  19 |                  20 |
|      0.05 | acciones_rechazadas |  20 |            135.45  |   -148.05  |     418.95  |                 0.33  |                  19 |                  20 |
|      0.05 | resiembras          |  20 |              0     |      0     |       0     |                 1     |                  19 |                  20 |
|      0.05 | desbalance          |  20 |             40.25  |     26.975 |      53.525 |                 0     |                  19 |                  20 |
|      0.05 | J                   |  20 |          11640.8   |   8637.07  |   14644.5   |                 0     |                  19 |                  20 |
|      0.1  | completitud_pp      |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0.1  | ticks               |  20 |             27.05  |     11.408 |      42.692 |                 0.002 |                  20 |                  20 |
|      0.1  | cobertura_pct       |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0.1  | distancia_total     |  20 |             49     |     21.934 |      76.066 |                 0.001 |                  20 |                  20 |
|      0.1  | combustible_total   |  20 |             37.365 |      3.025 |      71.705 |                 0.035 |                  20 |                  20 |
|      0.1  | espera_total        |  20 |            -33.1   |    -60.932 |      -5.268 |                 0.022 |                  20 |                  20 |
|      0.1  | colisiones          |  20 |              8     |      6.178 |       9.822 |                 0     |                  20 |                  20 |
|      0.1  | acciones_rechazadas |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0.1  | resiembras          |  20 |              0     |      0     |       0     |                 1     |                  20 |                  20 |
|      0.1  | desbalance          |  20 |             30.35  |     17.508 |      43.192 |                 0     |                  20 |                  20 |
|      0.1  | J                   |  20 |           8072.82  |   6247.59  |    9898.05  |                 0     |                  20 |                  20 |

## Limitaciones

- Entorno discretizado, combustible y obstáculos idealizados.
- Semillas emparejadas controlan el mapa, pero las decisiones de cada arquitectura difieren.
- Intervalos t descriptivos/exploratorios; no garantizan normalidad ni corrigen multiplicidad.
- La comparación no demuestra rendimiento en maquinaria física.
- Analizar por separado escenarios incompletos y métricas penalizadas por límite de ticks.
- El dashboard CSV muestra completitud y desempeño; no reconstruye trayectorias espaciales.
