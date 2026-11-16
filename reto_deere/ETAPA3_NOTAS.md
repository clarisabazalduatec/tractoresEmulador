# Etapa 3 — revisión de coordinación (no validada)

Se corrigió el test obsoleto de etapa 2, la asignación inicial por franjas,
las reservas simultáneas con seguimiento y cesión de paso, el retorno a una
posición de estacionamiento para tractores sin trabajo, y el despacho de
combustible con margen adicional en la arquitectura mejorada.

**Limitación importante:** todavía existen casos de bloqueo y agotamiento de
combustible cuando coinciden varios tractores cerca de las estaciones, en
particular densidad 10%, semilla 1. No se deben utilizar resultados de estos
casos como experimentos concluyentes.

Para validar en el entorno real: `pytest -q` y
`python -m experiments.quick_run improved`.
