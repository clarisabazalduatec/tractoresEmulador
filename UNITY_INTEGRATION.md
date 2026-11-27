# Integración Python–Unity

## Cómo funcionan los proyectos y qué comunicación existía

El repositorio Python ejecuta una simulación AgentPy del campo y tres tractores. `FarmModel` obtiene decisiones de los agentes, el Blackboard coordina la arquitectura improved, el planificador conserva A* y `WorldState` valida y aplica cada tick. El estado del mundo contiene obstáculos, estaciones, combustible, semillas y la matriz de siembra. Q-learning es una opción de evaluación para decidir el reabastecimiento de semillas de cada tractor.

Unity ya contiene una escena de campo 15×15, tractores, celdas, obstáculos, estaciones y `ComunicacionPython.cs`. La comunicación anterior era un demo FastAPI separado en `ServidorPython/api_unity.py`: cada GET a `/estado` avanzaba una ruta corta codificada a mano y solo enviaba posiciones. No conectaba con `FarmModel`; el archivo de obstáculos de la escena tampoco coincide con las rocas generadas por Python para seed 0.

## Protocolo nuevo

`src/unity_server.py` es un adaptador de transporte. No duplica políticas ni modifica Blackboard, A*, reglas, mundo o agentes. El servidor crea una instancia del modelo y usa sus métodos AgentPy existentes `sim_setup` y `sim_step`.

- `GET /health`: comprueba que el servidor responde.
- `GET /state`: devuelve el snapshot actual sin avanzar el modelo. El primer snapshot es tick 0.
- `POST /step`: hace que Python avance exactamente un tick y devuelve el nuevo snapshot. Al finalizar el episodio, responde con el último estado sin avanzar más.

Python conserva la autoridad sobre las decisiones y el avance de los ticks. Unity controla el ritmo visual al enviar `POST /step` desde el presentador; el intervalo de reproducción no cambia la lógica de simulación. `complete` indica cobertura completa; `finished` indica que el episodio se detuvo por cobertura o por alcanzar el máximo de ticks.

Los cuerpos JSON usan `row` y `col` (fila y columna), como Python. La grilla de Unity usa `x = col`, `z = row`, con paso de una unidad y origen `(0,0)`. Por ejemplo, la gasolinera `(14,4)` se representa en Unity en `(x=4,z=14)`.

Un snapshot tiene este formato:

```json
{
  "schema_version": 1,
  "scenario": {"architecture": "improved", "obstacle_density": 0.0, "seed": 0, "q_learning": false},
  "tick": 0,
  "complete": false,
  "finished": false,
  "field": {
    "rows": 15,
    "columns": 15,
    "coordinate_order": ["row", "col"],
    "obstacles": [],
    "stations": {"gas": {"row": 14, "col": 4}, "seeds": {"row": 14, "col": 10}},
    "sowable_count": 223
  },
  "planted": [],
  "tractors": [
    {"id": 1, "row": 0, "col": 0, "direction": "S", "seeds": 30.0, "fuel": 80.0, "mode": "esperando"},
    {"id": 2, "row": 0, "col": 5, "direction": "S", "seeds": 30.0, "fuel": 80.0, "mode": "esperando"},
    {"id": 3, "row": 0, "col": 10, "direction": "S", "seeds": 30.0, "fuel": 80.0, "mode": "esperando"}
  ],
  "metrics": {"coverage_pct": 0.0, "collisions": 0, "rejected_actions": 0}
}
```

El snapshot completo siempre incluye los tres tractores y todas las celdas sembradas hasta ese tick. Unity representa posiciones, estados/recursos, obstáculos, estaciones y siembra; no calcula destinos ni aplica reglas.

## Ejecutar la demostración preparada en Windows

El repositorio incluye las tres tablas entrenadas en `config/qlearning_demo_policies.json` y un lanzador que las activa automáticamente. No es necesario entrenar de nuevo ni copiar una política desde la computadora de desarrollo.

1. Instala Python 3 en Windows si aún no está instalado.
2. Desde el Explorador, ejecuta `run_unity_demo.bat` en la raíz del repositorio Python. La primera ejecución crea `.venv` e instala solo las dependencias del servidor; las siguientes reutilizan ese entorno.
3. Deja abierta la ventana del servidor. Abre `Assets/Scenes/SampleScene.unity` en el proyecto Unity y pulsa Play.
4. La simulación inicia con arquitectura `improved`, densidad de obstáculos del 10 %, semilla `0` y Q-learning activado. El HUD de Unity lo confirma. Para detener el servidor, pulsa Ctrl+C en su ventana.

El servidor de Python controla las decisiones de los tractores. Unity solicita el estado inicial y luego avanza un tick por cada actualización visual; no replica las decisiones de Q-learning, A* ni las reglas del mundo.

También se puede ejecutar `run_unity_demo.ps1` desde PowerShell. En otro sistema operativo, instala las dependencias de `requirements-unity.txt` y ejecuta el comando manual siguiente desde la raíz del repositorio.

## Ejecución manual reproducible

Desde la raíz de `Reto_Multiagentes`, con dependencias de `requirements-unity.txt` instaladas:

```powershell
.\.venv\Scripts\python.exe -m src.unity_server --architecture improved --density 0.10 --seed 0 --q-policies config/qlearning_demo_policies.json
```

El comando activa Q-learning en modo de evaluación, sin exploración ni entrenamiento, usando tres tablas ya entrenadas. Para utilizar otra política, proporciona su ruta con `--q-policies`; para comparar con la política improved original, omite esa opción. La API informa el estado real en `scenario.q_learning` y Unity lo muestra en pantalla.

Las tablas de demostración provienen del experimento local `qlearning_experiment_v3`: 20 semillas de entrenamiento por cada una de las tres densidades de obstáculos. Son una política experimental para reproducir la visualización, no una garantía de mejor desempeño. Se pueden generar nuevas tablas mediante `python -m experiments.train_qlearning` o evaluar mediante `python -m experiments.evaluate_qlearning`.

En Unity, con el servidor Python activo:

1. Abre `Assets/Scenes/SampleScene.unity`, que tiene `FarmSimulationBridge` agregado a `ConexionPython`.
2. Pulsa Play. La escena consulta el tick inicial y avanza automáticamente cada 0.5 segundos. El HUD permite pausar, reanudar y pedir el siguiente tick manualmente.

El modelo del tractor apunta hacia su eje local +X; el presentador corrige su orientación -90° y lo gira antes de desplazarlo. Las estaciones y los obstáculos se representan según el snapshot durante Play Mode. Los botones de cámara permiten elegir la vista orbital, la panorámica o el seguimiento de cada tractor. Los modelos de árboles, animales y cielo requieren los paquetes detallados en `ASSET_STORE_DEPENDENCIES.md` del proyecto Unity.

## Escenario de referencia Week 2

Sin `--q-policies`, la combinación `improved`, densidad `0.10`, seed `0` reproduce el episodio de la visualización temporal: 22 obstáculos, 201 celdas sembrables y finalización en tick 269. Al activar Q-learning, las decisiones y el tick final pueden cambiar. El servidor entrega snapshots por tick; los CSV de métricas finales no se usan para inferir trayectorias.

## Verificación y límites

Se validó en la sesión actual que el modelo termina el escenario seed 0 / 10 % con 201 celdas sembradas en 269 ticks. El protocolo expone el estado inicial y avance de un solo tick para que Unity solicite y represente cada transición. El servidor enlaza por defecto a `127.0.0.1`; una instancia Unity en otro equipo necesitaría una dirección accesible y una configuración de red apropiada. El demo antiguo de `ServidorPython` no forma parte de este adaptador.
