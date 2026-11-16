# Corrección de bloqueos de la etapa 3

- La política de combustible anticipa el regreso a G usando el costo real del camino y una reserva de 12 unidades. La reserva adicional evita el error previo de enviar al tractor de vuelta a G antes de alcanzar sus objetivos.
- Al terminar de cargar en G, el tractor intenta desocuparla inmediatamente mediante una celda adyacente libre, conservando suficiente combustible para volver a la estación.
- Cuando hay tractores con objetivo G, se evita que otros entren a G solo como atajo.
- Se conserva la comprobación de combustible por movimiento del blackboard, que impide acciones inválidas.
- Se cachea el costo mínimo entre estados del mapa para reducir los cálculos repetidos.
- Se incluyen regresiones para los escenarios 0.05/3, 0.05/16 y 0.10/10.

## Validación en AgentPy real

```bash
pytest -q
python -m experiments.validate_stage3
```

**Nota:** las pruebas locales con un sustituto mínimo de AgentPy no garantizan equivalencia con AgentPy real. La validación definitiva debe realizarse en el entorno del proyecto.
