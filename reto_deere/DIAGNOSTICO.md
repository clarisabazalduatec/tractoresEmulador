# Diagnóstico de bloqueos pendientes

Los casos 0.05/16, 0.10/4, 0.10/6 y 0.10/12 fallan con AgentPy real.
El test suite anterior no los cubría todos. Antes de cambiar reglas físicas o
atribuir el fallo a una causa específica, ejecutar:

```bash
python -m experiments.diagnose_deadlock --density 0.10 --seed 4
python -m experiments.diagnose_deadlock --density 0.05 --seed 16
python -m experiments.diagnose_deadlock --density 0.10 --seed 6
python -m experiments.diagnose_deadlock --density 0.10 --seed 12
```

Esta versión es de diagnóstico, no una corrección validada. La prueba de
regresión sigue fallando hasta solucionar la causa real.
