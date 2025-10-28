from typing import List
import asyncio
from .amil import AmilDriver
from .bradesco import BradescoDriver
from .unimed import UnimedDriver
from .seguros_unimed import SegurosUnimedDriver
from .sulamerica import SulamericaDriver
from .base import BaseDriver, DriverResult

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
            if hasattr(d, "_load_mapping"):
                d._load_mapping()

    async def run_batch(self, identifiers: List[str], id_type: str) -> List[DriverResult]:
        """
        Executa todas as operadoras, processando todos os CPFs de uma vez por driver.
        Exemplo:
            [Unimed -> todos os CPFs],
            [Amil -> todos os CPFs],
            ...
        """
        results: List[DriverResult] = []

        for driver in self._drivers:
            print(f"[{driver.operator}] iniciando consultas em lote ({len(identifiers)} CPFs)")
            try:
                batch_results = await self._run_driver_batch(driver, identifiers, id_type)
                results.extend(batch_results)
            except Exception as e:
                print(f"[{driver.operator}] falha no lote: {e}")
                for identifier in identifiers:
                    results.append(
                        DriverResult(
                            operator=driver.operator,
                            status="erro",
                            message=f"falha no lote: {e}"
                        )
                    )
        return results

    async def _run_driver_batch(
        self, driver: BaseDriver, identifiers: List[str], id_type: str
    ) -> List[DriverResult]:
        """Abre 1 browser e consulta todos os CPFs para a operadora."""
        results = []
        try:
            async with driver._persistent_browser() as page:
                for identifier in identifiers:
                    try:
                        res = await driver._perform(identifier, id_type, page)
                        results.append(res)
                    except Exception as e:
                        results.append(
                            DriverResult(
                                operator=driver.operator,
                                status="erro",
                                message=str(e)
                            )
                        )
        except Exception as e:
            print(f"[{driver.operator}] erro no navegador persistente: {e}")
        return results


manager = DriverManager()
