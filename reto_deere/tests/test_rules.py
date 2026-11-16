import copy
from pathlib import Path
import numpy as np
import pytest
from src.rules import WorldState, objective
from src.world import Field, build_field, generate_obstacles, load_params, validate_params
from src.state import ACTIONS

ROOT = Path(__file__).resolve().parent.parent
G, S = (14, 4), (14, 10)


@pytest.fixture
def params():
    return load_params(ROOT / "config" / "params.yaml")


def make(params, positions=None, obstacles=(), tiebreak=True, allow=False, seed=1):
    p = copy.deepcopy(params)
    p["coordination"].update(random_tiebreak=tiebreak, allow_collisions=allow)
    ws = WorldState(Field(15, G, S, obstacles), p, np.random.default_rng(seed))
    for tr, pos in zip(ws.tractors, positions or []):
        tr.pos = pos
    return ws


# ---- Regla 1: no salir del campo ----
@pytest.mark.parametrize("a", ["N", "O"])
def test_r1_fuera_del_campo_rechazado(params, a):
    ws = make(params)
    out = ws.step({1: a})
    assert out[1].status == "rechazada" and ws.tractors[0].pos == (0, 0)


def test_r1_obstaculo_rechazado(params):
    ws = make(params, [(5, 4), (0, 5), (0, 10)], obstacles={(5, 5)})
    assert ws.step({1: "E"})[1].status == "rechazada"


# ---- Regla 2: misma celda, solo uno entra ----
@pytest.mark.parametrize("tiebreak", [True, False])
def test_r2_misma_celda(params, tiebreak):
    ws = make(params, [(5, 4), (5, 6), (0, 10)], tiebreak=tiebreak)
    ws.step({1: "E", 2: "O"})
    p1, p2 = ws.tractors[0].pos, ws.tractors[1].pos
    assert sorted([p1, p2]) in ([(5, 4), (5, 5)], [(5, 5), (5, 6)])
    assert p1 != p2 and ws.collisions == 0 and ws.conflicts_blocked == 1


def test_r2_prioridad_fija_gana_id_menor(params):
    ws = make(params, [(5, 4), (5, 6), (0, 10)], tiebreak=False)
    ws.step({1: "E", 2: "O"})
    assert ws.tractors[0].pos == (5, 5) and ws.tractors[1].pos == (5, 6)


def test_r2_no_entra_a_celda_de_tractor_quieto(params):
    ws = make(params, [(5, 4), (5, 5), (0, 10)])
    out = ws.step({1: "E", 2: "sembrar"})
    assert out[1].status == "bloqueada" and ws.tractors[0].pos == (5, 4)


def test_colision_se_cuenta_en_modo_linea_base(params):
    ws = make(params, [(5, 4), (5, 6), (0, 10)], allow=True)
    ws.step({1: "E", 2: "O"})
    assert ws.tractors[0].pos == ws.tractors[1].pos and ws.collisions == 1


# ---- Regla 3: sin intercambio de celdas ----
def test_r3_no_hay_cruce_de_frente(params):
    ws = make(params, [(5, 4), (5, 5), (0, 10)])
    out = ws.step({1: "E", 2: "O"})
    p1, p2 = ws.tractors[0].pos, ws.tractors[1].pos
    assert not (p1 == (5, 5) and p2 == (5, 4))
    assert "bloqueada" in (out[1].status, out[2].status) and ws.collisions == 0


# ---- Regla 4: no resembrar ----
def test_r4_no_resembrar(params):
    ws = make(params, [(3, 3), (0, 5), (0, 10)])
    assert ws.step({1: "sembrar"})[1].status == "ok"
    assert ws.step({1: "sembrar"})[1].status == "rechazada"
    assert ws.tractors[0].seeds == 29 and ws.summary()["resiembras"] == 0


def test_r4_no_siembra_estacion_ni_sin_semillas(params):
    ws = make(params, [G, (0, 5), (0, 10)])
    assert ws.step({1: "sembrar"})[1].status == "rechazada"
    ws.tractors[1].seeds = 0
    assert ws.step({2: "sembrar"})[2].reason == "sin semillas"


def test_pisadas_y_costo_de_vuelta(params):
    ws = make(params, [(3, 3), (0, 5), (0, 10)])
    ws.M[4, 3] = 1
    ws.step({1: "S"})                       # misma dirección inicial: costo 1
    assert ws.tractors[0].fuel == 79 and ws.tractors[0].trampled == 1
    ws.step({1: "E"})                       # vuelta: 1.5
    assert ws.tractors[0].fuel == 77.5 and ws.tractors[0].turns == 1


# ---- Regla 5: combustible ----
def test_r5_combustible_insuficiente_nunca_negativo(params):
    ws = make(params, [(3, 3), (0, 5), (0, 10)])
    ws.tractors[0].fuel = 0.5
    assert ws.step({1: "S"})[1].status == "rechazada"
    assert ws.tractors[0].pos == (3, 3) and ws.tractors[0].fuel >= 0


def test_r5_needs_refuel_umbral(params):
    ws = make(params)                       # (0,0) dir S -> G: 18 pasos + 1 vuelta = 18.5; + margen 5
    ws.tractors[0].fuel = 23.0
    assert ws.needs_refuel(ws.tractors[0])
    ws.tractors[0].fuel = 24.0
    assert not ws.needs_refuel(ws.tractors[0])


# ---- Regla 6: un tractor por estación ----
def test_r6_un_tractor_por_estacion(params):
    ws = make(params, [(13, 4), (14, 3), (0, 10)], tiebreak=False)
    out = ws.step({1: "S", 2: "E"})
    assert ws.O["G"] == 1 and out[2].status == "bloqueada" and ws.tractors[1].mode == "esperando"
    ws.step({1: "cargar_G", 2: "E"})        # mientras carga, el otro sigue esperando
    assert ws.O["G"] == 1 and ws.tractors[1].pos == (14, 3)


# ---- Carga válida ----
def test_carga_valida(params):
    ws = make(params, [G, S, (0, 10)])
    ws.tractors[0].fuel, ws.tractors[1].seeds = 10, 0
    assert ws.step({1: "cargar_G", 2: "cargar_S"})[1].status == "ok"
    assert ws.tractors[0].fuel == 80 and ws.tractors[1].seeds == 30
    assert ws.step({3: "cargar_G"})[3].status == "rechazada"
    assert ws.step({1: "cargar_S"})[1].status == "rechazada"


# ---- Obstáculos y mapa ----
@pytest.mark.parametrize("density", [0.05, 0.10])
def test_obstaculos_conectados_y_reproducibles(params, density):
    starts = [tuple(s) for s in params["tractors"]["starts"]]
    for seed in range(20):
        obs = generate_obstacles(15, density, np.random.default_rng(seed), starts, G, S)
        assert len(obs) == round(density * 225)
        assert not (obs & set(starts + [G, S]))
        f = Field(15, G, S, obs)
        assert f.is_connected() and len(f.sowable) == 223 - len(obs)
        assert obs == generate_obstacles(15, density, np.random.default_rng(seed), starts, G, S)


def test_campo_sin_obstaculos_tiene_223(params):
    assert len(build_field(params).sowable) == 223


def test_validacion_de_parametros(params):
    bad = copy.deepcopy(params)
    bad["field"]["gas_station"] = [20, 4]
    with pytest.raises(ValueError):
        validate_params(bad)


def test_fin_cuando_todo_sembrado(params):
    ws = make(params)
    assert not ws.is_done()
    for r, c in ws.field.sowable:
        ws.M[r, c] = 1
    assert ws.is_done()


# ---- Invariantes bajo acciones aleatorias ----
def test_invariantes_con_acciones_aleatorias(params):
    obs = generate_obstacles(15, 0.10, np.random.default_rng(3), params["tractors"]["starts"], G, S)
    ws = make(params, obstacles=obs, seed=7)
    rng = np.random.default_rng(11)
    for _ in range(400):
        before = [t.pos for t in ws.tractors]
        ws.step({t.id: ACTIONS[rng.integers(len(ACTIONS))] for t in ws.tractors})
        after = [t.pos for t in ws.tractors]
        assert len(set(after)) == 3
        assert all(ws.field.passable(p) for p in after)
        assert not any(after[i] == before[j] and after[j] == before[i]
                       for i in range(3) for j in range(i + 1, 3))
        assert all(0 <= t.fuel <= 80 and 0 <= t.seeds <= 30 for t in ws.tractors)
    s = ws.summary()
    assert s["colisiones"] == 0 and s["resiembras"] == 0


def test_objetivo(params):
    s = dict(ticks=10, distancia_total=20, colisiones=0, espera_total=4, combustible_total=30, desbalance=2)
    assert objective(s, params["objective_weights"]) == 10 + 10 + 0 + 2 + 6 + 2
