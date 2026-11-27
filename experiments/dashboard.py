"""Interactive analysis for the experiment episode CSVs.

The notebook is the UI; this module discovers and validates the saved data,
keeps training rows out of evaluation comparisons, and regenerates telemetry
only after the user presses the replay button.
"""
from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from IPython.display import Markdown, display


METRICS = {
    "cobertura_pct": ("Cobertura final (%)", "higher"),
    "tasa_completitud_pct": ("Tasa de finalización (%)", "higher"),
    "ticks": ("Ticks registrados", "lower"),
    "distancia_total": ("Distancia (celdas)", "lower"),
    "combustible_total": ("Combustible consumido", "lower"),
    "espera_total": ("Ticks de espera", "lower"),
    "colisiones": ("Colisiones", "lower"),
    "acciones_rechazadas": ("Acciones rechazadas", "lower"),
}
ALIASES = {
    "coverage_pct": "cobertura_pct", "distance_total": "distancia_total",
    "fuel_total": "combustible_total", "wait_total": "espera_total",
    "collisions": "colisiones", "rejected_actions": "acciones_rechazadas",
    "rejected": "acciones_rechazadas", "complete": "completo",
}
PAIR_METADATA = (
    "start_mode", "initial_position_mode", "initial_positions_mode", "starting_positions_mode",
    "start_seed", "initial_position_seed", "initial_positions_seed", "positions_seed",
    "scenario_id", "start_positions", "initial_positions", "starts_json",
    "start_positions_json", "initial_positions_json", "obstacle_sha256", "config_hash", "parameter_hash",
)
REQUIRED = {"density", "seed", "architecture", "completo"}


def _read_episodes(csv_path: Path, kind: str) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    if "architecture" in frame:
        frame["architecture"] = frame["architecture"].replace({"improved_no_q": "improved"})
    frame = frame.rename(columns={old: new for old, new in ALIASES.items()
                                  if old in frame and new not in frame})
    optional_aliases = {
        "initial_position_mode": "start_mode", "initial_positions_mode": "start_mode",
        "starting_positions_mode": "start_mode", "initial_position_seed": "start_seed",
        "initial_positions_seed": "start_seed", "positions_seed": "start_seed",
    }
    frame = frame.rename(columns={old: new for old, new in optional_aliases.items()
                                  if old in frame and new not in frame})
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")
    if kind == "qlearning" and "phase" not in frame:
        raise ValueError("El CSV Q-learning debe distinguir phase=train/eval.")
    if "phase" not in frame:
        frame["phase"] = "eval"
    frame["phase"] = frame["phase"].astype(str).str.strip().str.lower()
    if not set(frame["phase"]).issubset({"eval", "train"}):
        raise ValueError("phase solo puede contener train o eval.")
    raw_complete = frame["completo"].astype(str).str.strip().str.lower()
    if not raw_complete.isin({"true", "false", "1", "0"}).all():
        raise ValueError("completo debe contener true/false o 1/0.")
    frame["completo"] = raw_complete.isin({"true", "1"})
    frame["density"] = pd.to_numeric(frame["density"], errors="raise")
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    for column in METRICS:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame.empty or not frame["density"].between(0, .5, inclusive="left").all():
        raise ValueError("CSV vacío o densidades fuera del rango [0, 0.5).")
    identity = ["phase", "density", "seed", "architecture"]
    identity.extend(column for column in PAIR_METADATA if column in frame)
    if frame.duplicated(identity).any():
        raise ValueError(f"Hay episodios duplicados según {identity}.")
    return frame


def _manifest_files(folder: Path) -> list[str]:
    names = ("manifest.json", "metadata.json", "experiment.json", "config.json", "params.yaml")
    return [name for name in names if (folder / name).is_file()]


def _discover(results_root: Path) -> tuple[dict, list]:
    datasets, issues = {}, []
    candidates = []
    stage4 = results_root / "stage4" / "episodes.csv"
    if stage4.is_file():
        candidates.append(("stage4", stage4, "stage4"))
    candidates.extend((path.parent.name, path, "qlearning")
                      for path in sorted(results_root.glob("qlearning*/episodes.csv")))
    archived = results_root.parent / "docs" / "evaluations" / "qlearning_random_starts" / "episodes.csv"
    if archived.is_file():
        candidates.append(("evaluacion_inicios_aleatorios", archived, "qlearning"))
    for key, path, kind in candidates:
        try:
            frame = _read_episodes(path, kind)
            eval_rows = frame[frame.phase == "eval"]
            train_rows = frame[frame.phase == "train"]
            datasets[key] = {
                "path": path, "kind": kind, "frame": frame,
                "manifest": _manifest_files(path.parent),
                "policy": ((path.parent / "policies.json").is_file() or
                           (key == "evaluacion_inicios_aleatorios" and
                            (results_root.parent / "config" / "qlearning_demo_policies.json").is_file())),
                "start_declared": "start_mode" in frame and frame.start_mode.notna().any(),
                "eval_rows": len(eval_rows), "train_rows": len(train_rows),
            }
        except Exception as exc:
            issues.append((str(path.relative_to(results_root.parent)), str(exc)))
    return datasets, issues


def _arch_pair(frame: pd.DataFrame, kind: str):
    present = set(frame.loc[frame.phase == "eval", "architecture"].astype(str))
    if kind == "stage4" and {"baseline", "improved"} <= present:
        return "baseline", "improved"
    if {"improved", "q_learning"} <= present:
        return "improved", "q_learning"
    if {"baseline", "improved"} <= present:
        return "baseline", "improved"
    return None


def _pair_rows(frame: pd.DataFrame, left_name: str, right_name: str):
    source = frame[frame.phase == "eval"]
    keys = ["density", "seed"] + [c for c in PAIR_METADATA if c in source]
    left = source[source.architecture.astype(str) == left_name].drop(columns=["phase", "architecture"])
    right = source[source.architecture.astype(str) == right_name].drop(columns=["phase", "architecture"])
    return left.merge(right, on=keys, how="inner", suffixes=("_left", "_right"), validate="one_to_one")


def _metric_values(frame: pd.DataFrame, name: str):
    return frame.completo.astype(float) * 100 if name == "tasa_completitud_pct" else frame[name]


def _paired_summary(frame: pd.DataFrame, left_name: str, right_name: str, densities: list[float]):
    pairs = _pair_rows(frame, left_name, right_name)
    rows = []
    for density in densities:
        subset = pairs[pairs.density == density]
        both_complete = subset.completo_left & subset.completo_right
        for name, (label, direction) in METRICS.items():
            if name != "tasa_completitud_pct" and name not in frame:
                continue
            if name == "tasa_completitud_pct":
                left, right = subset.completo_left.astype(float) * 100, subset.completo_right.astype(float) * 100
            else:
                left, right = subset[f"{name}_left"], subset[f"{name}_right"]
            delta = right - left
            all_pairs = name in {"tasa_completitud_pct", "cobertura_pct", "ticks"}
            used = delta if all_pairs else delta[both_complete]
            favorable = int((used > 0).sum()) if direction == "higher" else int((used < 0).sum())
            rows.append({
                "Obstáculos": density, "Métrica": label,
                "Pares emparejados": len(subset), "Terminados ambos": int(both_complete.sum()),
                "Pares usados para Δ": len(used),
                "Δ media (derecha − izquierda)": float(used.mean()) if len(used) else np.nan,
                "Δ mediana": float(used.median()) if len(used) else np.nan,
                "Pares a favor de etapa derecha": favorable,
                "Regla": "todos los pares" if all_pairs else "solo episodios completos en ambas",
            })
    return pd.DataFrame(rows), pairs


def _configure_matplotlib():
    plt.rcParams.update({"figure.figsize": (10, 4.8), "axes.titlesize": 12,
                         "axes.labelsize": 10, "grid.alpha": .22, "font.size": 10})


def show_dashboard(repo_root: Path):
    """Discover available CSVs and display the interactive episode dashboard."""
    results_root = repo_root / "results"
    params = yaml.safe_load((repo_root / "config" / "params.yaml").read_text(encoding="utf-8"))
    datasets, issues = _discover(results_root)
    if not datasets:
        raise FileNotFoundError("No hay CSV de episodios. Ejecuta experiments.stage4 para generar la fuente principal.")
    _configure_matplotlib()

    catalog = []
    for key, item in datasets.items():
        frame = item["frame"]
        evaluation = frame[frame.phase == "eval"]
        training = frame[frame.phase == "train"]
        starts = ", ".join(sorted(evaluation.start_mode.dropna().astype(str).unique())) if item["start_declared"] else "no declarado"
        seeds = sorted(evaluation.seed.unique())
        seed_label = (f"{seeds[0]}–{seeds[-1]} (n={len(seeds)})" if seeds
                      and seeds == list(range(seeds[0], seeds[-1] + 1))
                      else f"{len(seeds)} valores")
        catalog.append({
            "Experimento": key, "Fuente": str(item["path"].relative_to(repo_root)),
            "Filas eval": len(evaluation), "Filas train": len(training),
            "Densidades": ", ".join(f"{d:.0%}" for d in sorted(evaluation.density.unique())),
            "Semillas eval": seed_label,
            "Modo inicial": starts,
            "Manifiesto": ", ".join(item["manifest"]) if item["manifest"] else "ausente",
            "Política Q": "sí" if item["policy"] else "no",
        })
    display(Markdown("## Fuentes detectadas\nLos CSV se analizan desde sus filas; los resúmenes y PNG se consideran artefactos derivados."))
    display(pd.DataFrame(catalog))
    if issues:
        display(Markdown("### Archivos omitidos por errores de lectura"))
        display(pd.DataFrame(issues, columns=["Archivo", "Motivo"]))
    display(Markdown(
        f"**YAML del checkout actual:** campo {params['field']['size']} × {params['field']['size']}; "
        f"inicios {params['tractors']['starts']}; límite actual {params['sim']['max_ticks']} ticks. "
        "Los CSV no registran una huella de configuración."
    ))

    labels = {key: ("Etapas 1 → 2 · baseline vs improved" if item["kind"] == "stage4"
                    else f"Etapa 3 · Q-learning · {key}") for key, item in datasets.items()}
    first = "stage4" if "stage4" in datasets else next(iter(datasets))
    source = widgets.Dropdown(options=[(v, k) for k, v in labels.items()], value=first,
                              description="Experimento:", layout=widgets.Layout(width="65%"))
    density = widgets.Dropdown(options=[("Todas", None)], description="Obstáculos:")
    start_mode = widgets.Dropdown(options=[("Todos", "__all__")], description="Modo de inicio:",
                                  layout=widgets.Layout(width="45%"))
    seed = widgets.Dropdown(options=[("Todas", None)], description="Semilla:")
    metric_options = [(label, key) for key, (label, _) in METRICS.items()]
    metric = widgets.Dropdown(options=metric_options, value="ticks", description="Métrica:",
                              layout=widgets.Layout(width="55%"))

    def refresh_seeds(_=None):
        rows = datasets[source.value]["frame"]
        rows = rows[rows.phase == "eval"]
        if density.value is not None:
            rows = rows[rows.density == density.value]
        if "start_mode" in rows:
            if start_mode.value == "__missing__":
                rows = rows[rows.start_mode.isna()]
            elif start_mode.value != "__all__":
                rows = rows[rows.start_mode.astype(str) == str(start_mode.value)]
        values = sorted(rows.seed.unique())
        seed.options = [("Todas", None)] + [(str(value), int(value)) for value in values]
        if seed.value not in [None, *values]:
            seed.value = None

    def refresh_filters(_=None):
        rows = datasets[source.value]["frame"]
        rows = rows[rows.phase == "eval"]
        densities = sorted(rows.density.unique())
        density.options = [("Todas", None)] + [(f"{value:.0%}", float(value)) for value in densities]
        if density.value not in [None, *densities]:
            density.value = None
        if "start_mode" in rows:
            modes = sorted(rows.start_mode.dropna().astype(str).unique())
            start_mode.options = [("Todos", "__all__"), ("Sin declarar", "__missing__")] + [(v, v) for v in modes]
            start_mode.disabled = False
        else:
            start_mode.options = [("No disponible en CSV", "__all__")]
            start_mode.value = "__all__"
            start_mode.disabled = True
        refresh_seeds()

    source.observe(refresh_filters, names="value")
    density.observe(refresh_seeds, names="value")
    start_mode.observe(refresh_seeds, names="value")
    refresh_filters()

    def render(source_id, density_value, start_value, seed_value, metric_name):
        item = datasets[source_id]
        full = item["frame"]
        rows = full[full.phase == "eval"].copy()
        if start_value == "__missing__" and "start_mode" in rows:
            rows = rows[rows.start_mode.isna()]
        elif start_value != "__all__" and "start_mode" in rows:
            rows = rows[rows.start_mode.astype(str) == str(start_value)]
        if density_value is not None:
            rows = rows[rows.density == density_value]
        if seed_value is not None:
            rows = rows[rows.seed == seed_value]
        if rows.empty:
            display(Markdown("No hay filas de evaluación para este filtro."))
            return
        if item["kind"] == "stage4":
            left_name, right_name = "baseline", "improved"
            context = ("Etapas 1 → 2. A* está en ambas arquitecturas; la etapa improved añade Blackboard. "
                       f"Emparejamiento por densidad y semilla. Inicios del YAML del checkout actual: "
                       f"{params['tractors']['starts']} (el CSV no guarda una copia de esa configuración).")
        else:
            pair = _arch_pair(rows, item["kind"])
            left_name, right_name = pair if pair else (None, None)
            context = f"Evaluación Q aislada: {source_id}. Se excluyen las filas train de las comparaciones. No se combina con otra carpeta."
            if not item["start_declared"]:
                context += " Modo de posiciones iniciales no declarado en el CSV."
            if not item["manifest"]:
                context += " Falta manifiesto con la configuración completa y procedencia de la política."
        display(Markdown(context))

        train = full[full.phase == "train"]
        if item["kind"] == "qlearning":
            if train.empty:
                display(Markdown("**Entrenamiento:** no hay filas train en este CSV; documenta por separado el origen de la política."))
            else:
                table = train.groupby("density", as_index=False).agg(
                    episodios=("seed", "size"), completos=("completo", "sum"),
                    ticks_medios=("ticks", "mean"), cobertura_media=("cobertura_pct", "mean"))
                table = table.rename(columns={"density": "Obstáculos", "episodios": "Episodios train",
                    "completos": "Completos", "ticks_medios": "Ticks medios", "cobertura_media": "Cobertura media (%)"})
                display(Markdown("**Entrenamiento separado** · puede explorar y actualizar la política; no es evaluación."))
                display(table.round(2))

        summary_rows = []
        for (d, arch), group in rows.groupby(["density", "architecture"], sort=True):
            row = {"Obstáculos": d, "Arquitectura": arch, "Episodios": len(group),
                   "Completados": int(group.completo.sum()), "Incompletos": int((~group.completo).sum()),
                   "Finalización (%)": 100 * group.completo.mean()}
            for column in ("cobertura_pct", "ticks", "distancia_total", "combustible_total", "espera_total", "colisiones", "acciones_rechazadas"):
                if column in group:
                    row[METRICS[column][0]] = group[column].mean()
            summary_rows.append(row)
        display(Markdown("### Resumen por densidad y arquitectura\nMedias por episodio; incluye incompletos, contados por separado."))
        display(pd.DataFrame(summary_rows).round(2))

        if metric_name not in METRICS or (metric_name != "tasa_completitud_pct" and metric_name not in rows):
            metric_name = next((m for m in METRICS if m == "tasa_completitud_pct" or m in rows), "ticks")
        archs = sorted(rows.architecture.astype(str).unique())
        ds = sorted(rows.density.unique())
        x = np.arange(len(ds))
        colors = plt.cm.Set2(np.linspace(.08, .92, max(1, len(archs))))
        fig, ax = plt.subplots(figsize=(10, 4.5))
        for i, arch in enumerate(archs):
            medians = []
            for position, d in enumerate(ds):
                group = rows[(rows.density == d) & (rows.architecture.astype(str) == arch)]
                values = _metric_values(group, metric_name).astype(float)
                medians.append(values.median() if len(values) else np.nan)
                if len(values):
                    jitter = np.linspace(-.035, .035, len(values)) if len(values) > 1 else np.array([0.])
                    ax.scatter(np.full(len(values), position + (i - (len(archs)-1)/2) * .16) + jitter,
                               values, s=19, alpha=.55, color=colors[i], edgecolor="none")
            ax.plot(x + (i - (len(archs)-1)/2) * .16, medians, marker="D", color=colors[i], label=f"{arch} · mediana")
        ax.set_xticks(x, [f"{d:.0%}" for d in ds])
        ax.set(xlabel="Densidad de obstáculos", ylabel=METRICS[metric_name][0],
               title="Puntos: episodios · rombos: mediana")
        ax.grid(axis="y")
        ax.legend(frameon=False, ncol=2)
        fig.tight_layout()
        plt.show()

        if left_name and right_name:
            display(Markdown(
                f"### Diferencias pareadas · {left_name} → {right_name}\n"
                "Δ = derecha − izquierda. Positivo favorece cobertura/finalización; negativo favorece métricas de coste. "
                "Cobertura, ticks y finalización usan todos los pares; las otras métricas usan solo pares completos en ambas etapas."
            ))
            density_values = sorted(rows.density.unique())
            result, pairs = _paired_summary(rows, left_name, right_name, density_values)
            if start_value == "__missing__" and "start_mode" in pairs:
                pairs = pairs[pairs.start_mode.isna()]
            elif start_value != "__all__" and "start_mode" in pairs:
                pairs = pairs[pairs.start_mode.astype(str) == str(start_value)]
            if density_value is not None:
                result = result[result["Obstáculos"] == density_value]
                pairs = pairs[pairs.density == density_value]
            if seed_value is not None:
                pairs = pairs[pairs.seed == seed_value]
                result = result[result["Pares emparejados"] > 0]
            display(result.round(2))
            label = METRICS[metric_name][0]
            effect = result[result.Métrica == label]
            if not effect.empty:
                fig, ax = plt.subplots(figsize=(7.5, 3.4))
                y = effect["Δ media (derecha − izquierda)"].to_numpy(dtype=float)
                xx = np.arange(len(effect))
                ax.axhline(0, color="#64748b", linestyle="--", linewidth=1)
                ax.scatter(xx, y, s=65, color="#277da1")
                for px, py, n in zip(xx, y, effect["Pares usados para Δ"]):
                    if np.isfinite(py):
                        ax.annotate(f"n={int(n)}", (px, py), xytext=(5, 7), textcoords="offset points", fontsize=9)
                ax.set_xticks(xx, [f"{d:.0%}" for d in effect.Obstáculos])
                ax.set(xlabel="Densidad", ylabel="Δ media pareada", title=f"{right_name} − {left_name} · {label}")
                ax.grid(axis="y")
                fig.tight_layout()
                plt.show()
            if pairs.empty:
                display(Markdown("No se encontró ningún par que coincida en todas las claves disponibles."))
        else:
            display(Markdown("No hay dos arquitecturas emparejables bajo estos filtros."))

        display(Markdown("### Episodios incompletos"))
        incomplete = rows[~rows.completo].copy()
        if incomplete.empty:
            display(Markdown("No hay episodios incompletos bajo estos filtros."))
        else:
            limit = incomplete["max_ticks"].dropna().unique().tolist() if "max_ticks" in incomplete else []
            if not limit:
                limit = [params["sim"]["max_ticks"]]
            max_tick = limit[0] if len(limit) == 1 else None
            incomplete["Estado"] = (np.where(incomplete.ticks >= max_tick,
                f"Incompleto; coincide con límite del YAML actual ({max_tick}), no guardado en esta fila",
                "Incompleto; causa/tope no registrado") if max_tick is not None else "Incompleto; causa/tope no registrado")
            cols = ["density", "seed", "architecture", "cobertura_pct", "ticks", "Estado"]
            cols += [c for c in ("distancia_total", "combustible_total", "espera_total", "colisiones", "acciones_rechazadas") if c in incomplete]
            display(incomplete[cols].rename(columns={"density": "Obstáculos", "seed": "Semilla",
                "architecture": "Arquitectura", "cobertura_pct": "Cobertura (%)", "ticks": "Ticks",
                "distancia_total": "Distancia", "combustible_total": "Combustible", "espera_total": "Esperas",
                "colisiones": "Colisiones", "acciones_rechazadas": "Acciones rechazadas"}).round(2))

        scenario_cols = ["density", "seed"] + [c for c in PAIR_METADATA if c in rows]
        scenario_cols += ["architecture", "completo"] + [c for c in METRICS if c in rows]
        display(Markdown("### Episodios del filtro"))
        display(rows.sort_values(["density", "seed"])[scenario_cols].rename(columns={
            "density": "Obstáculos", "seed": "Semilla", "architecture": "Arquitectura",
            "start_mode": "Modo inicio", "start_seed": "Semilla de inicio", "scenario_id": "Escenario",
            "completo": "Completado", **{k: v[0] for k, v in METRICS.items()},
        }).round(2))

    display(widgets.VBox([widgets.HBox([source, density]),
                          widgets.HBox([start_mode, seed, metric])]))
    display(widgets.interactive_output(render, {
        "source_id": source, "density_value": density,
        "start_value": start_mode, "seed_value": seed, "metric_name": metric,
    }))


def _record_episode(params: dict):
    """Run one episode and retain coverage plus spatial snapshots in memory."""
    from src.model import FarmModel

    class RecordedFarmModel(FarmModel):
        def setup(self):
            self.timeline, self.snapshots = [], []
            super().setup()
            self.capture_state()
        def update(self):
            super().update()
            self.capture_state()
        def capture_state(self):
            world = self.world
            coverage = 100 * float(world.M.sum()) / len(world.field.sowable)
            tick = int(world.t)
            sample = (tick, coverage)
            snapshot = (tick, world.M.copy(), [tuple(t.pos) for t in world.tractors])
            if self.timeline and self.timeline[-1][0] == tick:
                self.timeline[-1] = sample
                self.snapshots[-1] = snapshot
            else:
                self.timeline.append(sample)
                self.snapshots.append(snapshot)

    model = RecordedFarmModel(params)
    model.run(display=False)
    return model


def show_episode_replay(repo_root: Path):
    """Show controls for a one-episode, in-memory telemetry regeneration."""
    datasets, issues = _discover(repo_root / "results")
    if not datasets:
        display(Markdown("No hay CSV válido para elegir episodio."))
        return
    labels = {key: ("Etapas 1–2" if item["kind"] == "stage4" else f"Q-learning · {key}")
              for key, item in datasets.items()}
    first = "stage4" if "stage4" in datasets else next(iter(datasets))
    source = widgets.Dropdown(options=[(v, k) for k, v in labels.items()], value=first,
                              description="Experimento:", layout=widgets.Layout(width="60%"))
    density = widgets.Dropdown(description="Obstáculos:")
    seed = widgets.Dropdown(description="Semilla:")
    architecture = widgets.Dropdown(description="Arquitectura:")
    button = widgets.Button(description="Regenerar telemetría", button_style="primary", icon="play")
    output = widgets.Output()

    def refresh(_=None):
        frame = datasets[source.value]["frame"]
        frame = frame[frame.phase == "eval"]
        values = sorted(frame.density.unique())
        density.options = [(f"{d:.0%}", float(d)) for d in values]
        if density.value not in values:
            density.value = values[0] if values else None
        refresh_dependents()

    def refresh_dependents(_=None):
        frame = datasets[source.value]["frame"]
        frame = frame[(frame.phase == "eval") & (frame.density == density.value)]
        seeds = sorted(frame.seed.unique())
        seed.options = [(str(s), int(s)) for s in seeds]
        if seed.value not in seeds:
            seed.value = seeds[0] if seeds else None
        archs = sorted(frame.architecture.astype(str).unique())
        architecture.options = [(a, a) for a in archs]
        if architecture.value not in archs:
            architecture.value = "improved" if "improved" in archs else (archs[0] if archs else None)

    source.observe(refresh, names="value")
    density.observe(refresh_dependents, names="value")
    refresh()

    def replay(_button):
        with output:
            output.clear_output(wait=True)
            from src.model import FarmModel
            item = datasets[source.value]
            rows = item["frame"]
            rows = rows[(rows.phase == "eval") & (rows.density == density.value)
                        & (rows.seed == seed.value)
                        & (rows.architecture.astype(str) == str(architecture.value))]
            if rows.empty:
                display(Markdown("No existe esa fila de evaluación."))
                return
            row = rows.iloc[0]
            params = {"architecture": "improved" if row.architecture == "q_learning" else row.architecture,
                      "obstacle_density": float(row.density), "seed": int(row.seed)}
            if row.architecture == "q_learning":
                policy_path = item["path"].parent / "policies.json"
                if item["path"].parent.name == "qlearning_random_starts" and not policy_path.is_file():
                    policy_path = Path("config/qlearning_demo_policies.json")
                if not policy_path.is_file():
                    display(Markdown("Falta policies.json en la carpeta seleccionada; no se puede regenerar Q-learning."))
                    return
                from src.qlearning import load_policies
                params.update(q_enabled=True, q_policies=load_policies(policy_path))
            setup_source = inspect.getsource(FarmModel.setup)
            positions_fields = ("start_positions", "initial_positions", "starts_json",
                                "start_positions_json", "initial_positions_json")
            supplied_positions = False
            for field in positions_fields:
                if field in rows and pd.notna(row.get(field)) and field in setup_source:
                    value = row[field]
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            value = ast.literal_eval(value)
                    params[field] = value
                    supplied_positions = True
            if "start_mode" in rows and pd.notna(row.get("start_mode")):
                mode = str(row["start_mode"])
                if (mode.lower() not in {"fixed", "fijo", "fija", "yaml"}
                        and "start_mode" not in setup_source and not supplied_positions):
                    display(Markdown(f"El CSV pide modo `{mode}`, pero el checkout no expone ese parámetro. No se supondrá una posición inicial."))
                    return
                params["start_mode"] = mode
            if "start_seed" in rows and pd.notna(row.get("start_seed")):
                params["start_seed"] = int(row["start_seed"])
            if ("max_ticks" in rows and pd.notna(row.get("max_ticks"))
                    and "max_ticks" in inspect.getsource(FarmModel.setup)):
                params["max_ticks"] = int(row["max_ticks"])

            model = _record_episode(params)
            world = model.world
            display(Markdown(f"**Reproducción con el checkout actual:** {row.architecture}, {row.density:.0%}, semilla {int(row.seed)} · cobertura final {model.timeline[-1][1]:.2f} %."))
            fig, ax = plt.subplots(figsize=(8, 3.5))
            times, coverage = zip(*model.timeline)
            ax.plot(times, coverage, color="#277da1", linewidth=2)
            ax.set(xlabel="Tick", ylabel="Cobertura sembrada (%)", ylim=(0, 105), title="Evolución temporal")
            ax.grid(True)
            fig.tight_layout()
            plt.show()

            from matplotlib.colors import ListedColormap
            from matplotlib.patches import Patch
            from matplotlib.lines import Line2D
            snapshots = model.snapshots
            indices = sorted(set([0, len(snapshots)//3, 2*len(snapshots)//3, len(snapshots)-1]))
            palette = ListedColormap(["#fff3cd", "#78b77b", "#545454", "#4c82d6", "#e5a44b"])
            tractor_colors = ["#d62728", "#9467bd", "#17becf"]
            fig, axes = plt.subplots(1, len(indices), figsize=(4*len(indices), 4), squeeze=False)
            field = world.field
            for ax, index in zip(axes.flat, indices):
                tick, planted, positions = snapshots[index]
                values = np.zeros((field.size, field.size), dtype=int)
                for r, c in field.sowable:
                    values[r, c] = int(planted[r, c])
                for r, c in field.obstacles:
                    values[r, c] = 2
                values[field.gas] = 3
                values[field.seed_station] = 4
                ax.imshow(values, cmap=palette, vmin=-.5, vmax=4.5, interpolation="nearest")
                for tractor_index in range(len(positions)):
                    route = np.array([s[2][tractor_index] for s in snapshots[:index+1]])
                    ax.plot(route[:, 1], route[:, 0], color=tractor_colors[tractor_index], linewidth=1, alpha=.65)
                    r, c = positions[tractor_index]
                    ax.scatter(c, r, marker="s", s=60, color=tractor_colors[tractor_index], edgecolor="black", zorder=3)
                ax.set_title(f"Tick {tick} · {100*float(planted.sum())/len(field.sowable):.1f}%")
                ax.set_xlabel("Columna")
                ax.set_xticks(range(0, field.size, 3))
                ax.set_yticks(range(0, field.size, 3))
            axes[0, 0].set_ylabel("Fila")
            handles = [Patch(color=palette(i), label=name) for i, name in enumerate(["Sin sembrar", "Sembrada", "Obstáculo", "Gas G", "Semillas S"])]
            handles += [Line2D([0], [0], marker="s", linestyle="", color=tractor_colors[i], label=f"Tractor T{i+1}") for i in range(len(world.tractors))]
            fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8)
            fig.suptitle("Secuencia espacial y rutas")
            fig.tight_layout(rect=(0, .12, 1, .92))
            plt.show()
            summary = world.summary()
            result = {"Completado": bool(world.is_done()), "Ticks": int(world.t), "Cobertura (%)": model.timeline[-1][1]}
            for key, label in (("distancia_total", "Distancia"), ("combustible_total", "Combustible"),
                               ("espera_total", "Esperas"), ("colisiones", "Colisiones"),
                               ("acciones_rechazadas", "Acciones rechazadas")):
                if key in summary:
                    result[label] = summary[key]
            display(pd.DataFrame([result]))

    button.on_click(replay)
    display(widgets.VBox([widgets.HBox([source, density, seed, architecture]), button, output]))

