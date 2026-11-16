"""Corrida rápida para validar: python -m experiments.quick_run [arquitectura]"""
import sys
import pandas as pd
from src.model import run_episode

arch = sys.argv[1] if len(sys.argv) > 1 else "baseline"
rows = []
for density in (0.0, 0.05, 0.10):
    for seed in range(5):
        _, r = run_episode(arch, density, seed)
        rows.append(dict(densidad=density, seed=seed, **{k: r[k] for k in (
            "completo", "cobertura_pct", "ticks", "distancia_total", "combustible_total",
            "espera_total", "colisiones", "pisadas", "desbalance", "acciones_rechazadas", "J")}))
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df.round(1).to_string(index=False))
print("\nPromedio por densidad:\n", df.groupby("densidad").mean(numeric_only=True).round(1).to_string())
