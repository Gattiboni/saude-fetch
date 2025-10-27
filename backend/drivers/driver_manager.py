from typing import List
from .amil import AmilDriver
from .bradesco import BradescoDriver
from .unimed import UnimedDriver
from .seguros_unimed import SegurosUnimedDriver
from .sulamerica import SulamericaDriver
from .base import BaseDriver

class DriverManager:
    def __init__(self) -> None:
        self._drivers: List[BaseDriver] = [
            UnimedDriver(),
            AmilDriver(),
            BradescoDriver(),
            SegurosUnimedDriver(),
            SulamericaDriver(),
        ]

    @property
    def drivers(self) -> List[BaseDriver]:
        return self._drivers

    def reload(self) -> None:
        for d in self._drivers:
            d._load_mapping()  # reload

manager = DriverManager()
