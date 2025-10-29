import asyncio
import os
import time
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional

from .amil import AmilDriver
from .bradesco import BradescoDriver
from .seguros_unimed import SegurosUnimedDriver
from .sulamerica import SulamericaDriver
from .unimed import UnimedDriver
from .base import BaseDriver, DriverResult
from utils.metrics import record_metric

try:
    from db.cache import Cache
except ImportError:  # pragma: no cover
    Cache = None  # type: ignore

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "3"))
PER_OPERATOR_CONCURRENCY = int(os.getenv("PER_OPERATOR_CONCURRENCY", "1"))

default_lock_factory = lambda: asyncio.Semaphore(PER_OPERATOR_CONCURRENCY)

_global_sem = asyncio.Semaphore(MAX_CONCURRENCY)
_operator_locks: Dict[str, asyncio.Semaphore] = defaultdict(default_lock_factory)


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
        for driver in self._drivers:
            if hasattr(driver, "_load_mapping"):
                driver._load_mapping()

    async def run_batch(
        self,
        identifiers: List[str],
        id_type: str,
        *,
        cache: Optional["Cache"] = None,
        db: Optional[object] = None,
        progress_callback: Optional[
            Callable[[str, BaseDriver, DriverResult, bool], Awaitable[None]]
        ] = None,
    ) -> List[DriverResult]:
        """Executa uma lista de identificadores em todos os drivers compatíveis."""
        if not identifiers:
            return []

        results: List[DriverResult] = []
        active_drivers = [
            driver
            for driver in self._drivers
            if id_type in getattr(driver, "supported_id_types", ("cpf",))
        ]

        for driver in active_drivers:
            print(
                f"[{driver.operator}] iniciando consultas em lote ({len(identifiers)} itens)"
            )
            try:
                batch_results = await self._run_driver_batch(
                    driver,
                    identifiers,
                    id_type,
                    cache=cache,
                    db=db,
                    progress_callback=progress_callback,
                )
                results.extend(batch_results)
            except Exception as exc:
                print(f"[{driver.operator}] falha no lote: {exc}")
                for identifier in identifiers:
                    results.append(
                        DriverResult(
                            operator=driver.operator,
                            status="erro",
                            message=f"falha no lote: {exc}",
                            identifier=identifier,
                            id_type=id_type,
                        )
                    )
        return results

    async def _run_driver_batch(
        self,
        driver: BaseDriver,
        identifiers: List[str],
        id_type: str,
        *,
        cache: Optional["Cache"] = None,
        db: Optional[object] = None,
        progress_callback: Optional[
            Callable[[str, BaseDriver, DriverResult, bool], Awaitable[None]]
        ] = None,
    ) -> List[DriverResult]:
        results: List[DriverResult] = []
        try:
            async with _global_sem, _operator_locks[driver.name]:
                async with driver._persistent_browser() as page:
                    for identifier in identifiers:
                        cached_result: Optional[DriverResult] = None
                        if cache is not None:
                            try:
                                cached_data = await cache.get(driver.name, identifier)
                            except Exception:
                                cached_data = None
                            if cached_data:
                                cached_result = DriverResult(
                                    operator=driver.operator,
                                    status=cached_data.get("status", "erro"),
                                    plan=cached_data.get("plan", ""),
                                    message=cached_data.get("message", ""),
                                    captured_at=cached_data.get("captured_at", ""),
                                    debug=cached_data.get("debug", {}),
                                    identifier=identifier,
                                    id_type=id_type,
                                )

                        if cached_result is not None:
                            results.append(cached_result)
                            if db is not None:
                                await record_metric(
                                    db,
                                    driver.name,
                                    identifier,
                                    cached_result.status not in {"erro", "invalid"},
                                    duration=0.0,
                                    cached=True,
                                )
                            if progress_callback:
                                await progress_callback(
                                    identifier, driver, cached_result, True
                                )
                            continue

                        start = time.perf_counter()
                        try:
                            result = await driver.consult(
                                identifier, id_type, page=page
                            )
                        except Exception as exc:
                            result = DriverResult(
                                operator=driver.operator,
                                status="erro",
                                plan="",
                                message=str(exc),
                                debug={"exception": str(exc)},
                                identifier=identifier,
                                id_type=id_type,
                            )
                        duration = time.perf_counter() - start
                        results.append(result)

                        if cache is not None:
                            try:
                                await cache.set(
                                    driver.name,
                                    identifier,
                                    {
                                        "status": result.status,
                                        "plan": result.plan,
                                        "message": result.message,
                                        "captured_at": result.captured_at,
                                        "debug": result.debug,
                                        "id_type": result.id_type,
                                    },
                                )
                            except Exception:
                                pass

                        if db is not None:
                            await record_metric(
                                db,
                                driver.name,
                                identifier,
                                result.status not in {"erro", "invalid"},
                                duration=duration,
                                cached=False,
                            )

                        if progress_callback:
                            await progress_callback(identifier, driver, result, False)
        except Exception as exc:
            print(f"[{driver.operator}] erro no navegador persistente: {exc}")
        return results


manager = DriverManager()
