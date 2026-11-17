import pytest
from src.model import FarmModel, run_episode


@pytest.mark.parametrize("density", [0.0, 0.05, 0.10])
@pytest.mark.parametrize("seed", range(4))
def test_linea_base_completa_sin_resembrar(density, seed):
    m, r = run_episode("baseline", density, seed)
    assert r["completo"] and r["cobertura_pct"] == 100.0
    assert r["resiembras"] == 0
    assert r["ticks"] < m.cfg["sim"]["max_ticks"]
    assert r["acciones_rechazadas"] == 0          # ninguna acción inválida (p. ej. sin combustible)
    assert r["celdas_sembrables"] == 223 - r["obstaculos"]
    assert all(t.mode == "terminado" for t in m.world.tractors)


def test_reproducible_con_misma_semilla():
    _, a = run_episode("baseline", 0.10, 7)
    _, b = run_episode("baseline", 0.10, 7)
    assert a == b


def test_semillas_distintas_dan_mapas_distintos():
    ma, _ = run_episode("baseline", 0.10, 1)
    mb, _ = run_episode("baseline", 0.10, 2)
    assert ma.world.field.obstacles != mb.world.field.obstacles


def test_cada_tractor_siembra_solo_su_franja():
    m, _ = run_episode("baseline", 0.05, 3)
    cols = [{0, 1, 2, 3, 4}, {5, 6, 7, 8, 9}, {10, 11, 12, 13, 14}]
    for ag in m.agents:
        assert {c for _, c in ag.order} <= cols[ag.tid - 1]
    assert sum(t.sown for t in m.world.tractors) == len(m.world.field.sowable)


def test_responde_a_parametros(tmp_path):
    import yaml
    from src.model import DEFAULT_CONFIG
    cfg = yaml.safe_load(open(DEFAULT_CONFIG, encoding="utf-8"))
    cfg["sim"]["max_ticks"] = 50
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    _, corto = run_episode("baseline", 0.0, 0, config_path=str(path))
    assert not corto["completo"] and corto["ticks"] == 50 and corto["cobertura_pct"] < 100
    cfg["sim"]["max_ticks"] = 3000
    cfg["tractors"]["fuel_capacity"] = 40.0       # menos combustible -> más visitas a G
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    _, base = run_episode("baseline", 0.0, 0)
    _, poco = run_episode("baseline", 0.0, 0, config_path=str(path))
    assert sum(poco[f"visitas_G_T{i}"] for i in (1, 2, 3)) > sum(base[f"visitas_G_T{i}"] for i in (1, 2, 3))


def test_improved_implementado():
    _, result = run_episode("improved", 0.0, 0)
    assert result["colisiones"] == 0
