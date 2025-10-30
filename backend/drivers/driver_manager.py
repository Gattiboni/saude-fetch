from typing import Dict, Iterable

from .amil import AmilDriver
from .bradesco import BradescoDriver
from .unimed import UnimedDriver
from .seguros_unimed import SegurosUnimedDriver
from .base import BaseDriver

class DriverManager:
    def __init__(self) -> None:
        self._drivers: Dict[str, BaseDriver] = {
            "amil": AmilDriver(),
            "bradesco": BradescoDriver(),
            "unimed": UnimedDriver(),
            "seguros_unimed": SegurosUnimedDriver(),
        }

    def get(self, operator: str) -> BaseDriver:
        op = (operator or "").strip().lower()
        if op not in self._drivers:
            raise KeyError(f"Operadora não suportada: {operator}")
        return self._drivers[op]

    def names(self) -> Iterable[str]:
        return self._drivers.keys()

    def items(self):
        return self._drivers.items()
    
    @property
def drivers(self):
    return self._drivers


manager = DriverManager()
