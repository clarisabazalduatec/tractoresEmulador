import json
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from src.model import FarmModel
from src.unity_server import SimulationSession, make_handler
from src.world import load_params

ROOT = Path(__file__).resolve().parents[1]


def setup_model(seed, density=0.10, start_mode="random"):
    model = FarmModel({
        "architecture": "improved",
        "obstacle_density": density,
        "seed": seed,
        "start_mode": start_mode,
    })
    model.sim_setup(steps=1, seed=seed)
    return model


def test_random_starts_are_seeded_distinct_and_accessible():
    first = setup_model(73)
    repeated = setup_model(73)
    first_field = first.world.field
    repeated_field = repeated.world.field

    assert first.start_positions == repeated.start_positions
    assert first_field.obstacles == repeated_field.obstacles
    assert len(set(first.start_positions)) == len(first.world.tractors)
    assert all(cell in first_field.sowable for cell in first.start_positions)
    assert all(cell in first_field.bfs_dist(first_field.gas) for cell in first.start_positions)
    assert all(cell in first_field.bfs_dist(first_field.seed_station)
               for cell in first.start_positions)


def test_fixed_starts_remain_the_default_and_are_unchanged():
    params = load_params(ROOT / "config" / "params.yaml")
    fixed = tuple(tuple(cell) for cell in params["tractors"]["starts"])
    explicit = setup_model(73, start_mode="fixed")
    default = FarmModel({"architecture": "improved", "obstacle_density": 0.10, "seed": 73})
    default.sim_setup(steps=1, seed=73)

    assert explicit.start_positions == fixed
    assert default.start_positions == fixed
    assert explicit.world.field.obstacles == default.world.field.obstacles


def test_reset_api_returns_real_random_tick_zero_and_steps_once():
    policy_path = ROOT / "config" / "qlearning_demo_policies.json"
    policy_hash_before = sha256(policy_path.read_bytes()).hexdigest()
    session = SimulationSession(
        density=0.0,
        seed=1,
        q_policies_path=policy_path,
        max_ticks=25,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(session))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    def request(method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(base_url + path, data=body, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        initial = request("POST", "/reset", {
            "density": 0.05,
            "seed": 211,
            "start_mode": "random",
            "q_learning": True,
            "architecture": "improved",
        })
        assert initial["tick"] == 0
        assert initial["scenario"]["start_mode"] == "random"
        assert initial["scenario"]["initial_positions"] == "random"
        assert initial["scenario"]["q_learning"] is True
        assert initial["scenario"]["seed"] == 211
        assert initial["scenario"]["density"] == 0.05
        assert initial["scenario"]["obstacle_density"] == 0.05
        starts = {(tractor["row"], tractor["col"]) for tractor in initial["tractors"]}
        assert len(starts) == len(initial["tractors"])
        obstacles = {(cell["row"], cell["col"])
                     for cell in initial["field"]["obstacles"]}
        stations = {
            (initial["field"]["stations"][name]["row"],
             initial["field"]["stations"][name]["col"])
            for name in ("gas", "seeds")
        }
        assert not starts & obstacles
        assert not starts & stations
        assert all(
            0 <= row < initial["field"]["rows"]
            and 0 <= col < initial["field"]["columns"]
            for row, col in starts
        )

        unchanged = request("GET", "/state")
        assert unchanged["tick"] == 0
        stepped = request("POST", "/step", {})
        assert stepped["tick"] == 1
        assert stepped["scenario"]["seed"] == 211

        repeated = request("POST", "/reset", {
            "density": 0.05,
            "seed": 211,
            "start_mode": "random",
            "q_learning": True,
            "architecture": "improved",
        })
        assert repeated["tick"] == 0
        assert repeated["field"]["obstacles"] == initial["field"]["obstacles"]
        assert repeated["tractors"] == initial["tractors"]

        fixed = request("POST", "/reset", {
            "density": 0.05,
            "seed": 211,
            "start_mode": "fixed",
            "q_learning": False,
            "architecture": "improved",
        })
        assert fixed["tick"] == 0
        assert fixed["scenario"]["q_learning"] is False
        assert [(t["row"], t["col"]) for t in fixed["tractors"]] == [
            (0, 0), (0, 5), (0, 10)
        ]
        assert sha256(policy_path.read_bytes()).hexdigest() == policy_hash_before
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_tracked_q_policy_file_has_stable_digest():
    policy_path = ROOT / "config" / "qlearning_demo_policies.json"
    with open(policy_path, "rb") as handle:
        before = sha256(handle.read()).hexdigest()
    from src.qlearning import load_policies

    policies = load_policies(policy_path)
    assert len(policies) == 3
    with open(policy_path, "rb") as handle:
        after = sha256(handle.read()).hexdigest()
    assert before == after
