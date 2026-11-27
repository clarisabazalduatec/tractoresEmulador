# Evaluación de Q-learning con posiciones iniciales aleatorias

## Diseño

Se comparó la política guardada en `config/qlearning_demo_policies.json` con la arquitectura `improved` sin Q-learning. Cada tractor inicia en una celda aleatoria válida. Se usaron 20 semillas (50000–50019) por densidad: 0 %, 5 % y 10 %; son 60 pares y 120 episodios. En cada par se verificó que ambos modelos recibieran exactamente el mismo mapa de obstáculos y las mismas posiciones iniciales.

La política se cargó en modo de evaluación (`epsilon = 0` y `q_training = false`). El evaluador comprueba que las tablas en memoria y el archivo no cambien. El SHA-256 de la política antes y después fue `f846954c2402901633b3cea17285c7e5715dd14342576b9db69c0fa302371a2c`.

El límite fue 3000 ticks. Los ticks promedio de la tabla siguiente solo incluyen pares donde ambos episodios completaron. Combustible y esperas también se comparan en esos mismos pares para evitar que episodios censurados sesguen su promedio. El CSV conserva, además, el resultado de cada episodio y los acumulados observados hasta el límite. No se calcularon intervalos de confianza; la muestra es exploratoria.

## Resultados

| Obstáculos | Completados `improved` | Completados Q | `improved` al límite | Q al límite | Pares completados por ambos | Ticks promedio `improved` / Q | Mediana de diferencia de ticks (Q − improved) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 % | 19/20 | 18/20 | 1 | 2 | 18 | 261.6 / 259.4 | +7 |
| 5 % | 18/20 | 20/20 | 2 | 0 | 18 | 277.2 / 273.7 | −1 |
| 10 % | 18/20 | 19/20 | 2 | 1 | 18 | 291.9 / 279.2 | −16 |
| **Total** | **55/60** | **57/60** | **5** | **3** | **54** | — | — |

En los pares que completaron ambos episodios:

| Obstáculos | Cobertura media `improved` / Q | Combustible medio `improved` / Q | Esperas medias `improved` / Q | Colisiones en los 20 episodios | Acciones rechazadas en los 20 episodios |
|---|---:|---:|---:|---:|---:|
| 0 % | 100 % / 100 % | 567.5 / 566.8 | 22.1 / 20.3 | 0 / 0 | 0 / 0 |
| 5 % | 100 % / 100 % | 617.2 / 617.3 | 18.8 / 19.6 | 0 / 0 | 0 / 0 |
| 10 % | 100 % / 100 % | 667.7 / 634.0 | 30.2 / 18.1 | 0 / 0 | 0 / 0 |

Q terminó dos episodios más en el conjunto, y fue más rápido en promedio entre pares completos en las tres densidades. La diferencia de ticks fue pequeña en 0 % y 5 %; en 10 % fue mayor. Combustible y esperas también variaron por densidad. Ambos métodos registraron cero colisiones y cero acciones rechazadas. Estos 20 pares por densidad no demuestran una ventaja general de Q-learning.

Ocho episodios llegaron al límite: cinco `improved` y tres Q. Sus ticks no son tiempos de finalización y sus combustible/esperas son acumulados hasta 3000. Se deben consultar como episodios incompletos en el CSV, no mezclarlos con promedios de finalización. El archivo registra la cobertura y los acumulados particulares de cada uno.

## Conclusión y siguiente paso

La política existente se comporta de forma comparable a `improved` y no muestra una degradación general al cambiar las posiciones iniciales. No hay evidencia suficiente para reemplazarla por una política nueva ni para afirmar que sea superior. Conviene conservarla para la demostración actual. Si el uso esperado incluye inicios aleatorios, el siguiente experimento recomendado es continuar su entrenamiento con inicios aleatorios, guardar el resultado en un archivo versionado distinto y validarlo con semillas holdout nuevas. El entrenador actual solo inicia tablas nuevas y todavía no ofrece reanudación ni una opción de inicio aleatorio; ese soporte queda pendiente. No se inició entrenamiento ni se sobrescribió la política.

## Reproducir

Desde la raíz del repositorio, instala `requirements.txt` y ejecuta:

```powershell
python -m experiments.evaluate_qlearning `
  --train-per-density 20 `
  --eval-per-density 20 `
  --eval-start-seed 50000 `
  --start-mode random `
  --policy config/qlearning_demo_policies.json `
  --output results/qlearning_random_starts
```

El evaluador rechaza un directorio de salida no vacío para no reemplazar resultados existentes. Produce `episodes.csv` y `summary.json`. Las copias de los datos de esta corrida están en `docs/evaluations/qlearning_random_starts/`; `results/` sigue ignorado por Git.
