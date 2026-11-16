"""Estado de cada tractor: x_k(t) = (posición, dirección, semillas, combustible, modo)."""
from dataclasses import dataclass

DIRECTIONS = ("N", "S", "E", "O")
MODES = ("sembrando", "moviéndose", "esperando", "cargando", "terminado")
ACTIONS = DIRECTIONS + ("sembrar", "esperar", "cargar_G", "cargar_S")


@dataclass
class Tractor:
    id: int                 # 1, 2, 3
    pos: tuple
    direction: str
    seeds: float
    fuel: float
    mode: str = "esperando"
    # contadores para las métricas
    distance: int = 0       # celdas recorridas
    turns: int = 0
    fuel_spent: float = 0.0
    wait_ticks: int = 0
    visits_G: int = 0
    visits_S: int = 0
    trampled: int = 0       # entradas a celdas ya sembradas
    sown: int = 0

    @property
    def name(self) -> str:
        return f"T{self.id}"
