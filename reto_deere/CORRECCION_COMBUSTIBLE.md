# Corrección etapa 3 — reserva de combustible

El diagnóstico mostró T2 detenido con combustible 0 en (14,8), impidiendo el avance de T3. Se corrigió la política de despacho a gasolina y se añadió una comprobación **antes de confirmar cada movimiento** en el blackboard: ningún movimiento de trabajo puede dejar al tractor con menos combustible que el costo mínimo de regreso a G (incluidas vueltas) más margen. Si no cumple, el tractor cambia su objetivo a G. Los movimientos hacia G requieren conservar suficiente combustible para completar la ruta. Se agregaron cuatro casos de regresión (5 %/16, 10 %/4, 10 %/6, 10 %/12).

La validación local de los cuatro casos se realizó con una implementación mínima de compatibilidad de AgentPy, no con AgentPy real. Ejecutar `pytest -q` y `python -m experiments.validate_stage3` en el entorno real antes de dar por aprobada la etapa.
