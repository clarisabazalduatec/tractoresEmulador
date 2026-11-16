# Validación de etapa 3

Se añadió una regresión para densidad 10 % y semilla 4, además de un verificador de 60 corridas (20 semillas × 3 densidades).

Ejecutar desde la raíz:

```bash
pytest -q
python -m experiments.validate_stage3
```

**Advertencia:** el caso observado por el usuario con AgentPy real aún no está corregido de forma demostrada. La compatibilidad local de AgentPy puede producir otra secuencia aleatoria y no reproducir el bloqueo. No pasar a etapa 4 hasta que el verificador termine sin fallos en el entorno real.
