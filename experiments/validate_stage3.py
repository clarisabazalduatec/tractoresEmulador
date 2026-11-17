"""Verifica 20 semillas por densidad sin ocultar fallos de cobertura."""
from src.model import run_episode


def main():
    failures = []
    for density in (0.0, 0.05, 0.10):
        for seed in range(20):
            _, result = run_episode('improved', density, seed)
            ok = (bool(result['completo']) and result['colisiones'] == 0
                  and result['resiembras'] == 0 and result['acciones_rechazadas'] == 0)
            print(f'densidad={density:.2f} semilla={seed:02d} '
                  f'cobertura={result["cobertura_pct"]:.2f}% '
                  f'ticks={result["ticks"]} rechazadas={result["acciones_rechazadas"]} '
                  f'{"OK" if ok else "FALLO"}', flush=True)
            if not ok:
                failures.append((density, seed, result))
    print(f'Fallos: {len(failures)} / 60')
    if failures:
        for density, seed, result in failures:
            print('FALLO', density, seed, result)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
