import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional, Iterable

from .bradesco import BradescoDriver
from .seguros_unimed import SegurosUnimedDriver
from .unimed import UnimedDriver
from .base import BaseDriver, DriverResult
from utils.metrics import record_metric

logger = logging.getLogger("saude_fetch.driver_manager")

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
        # Instantiate driver objects (assumes drivers implement required async methods)
        self._drivers = {
            "bradesco": BradescoDriver(),
            "unimed": UnimedDriver(),
            "seguros_unimed": SegurosUnimedDriver(),
        }

        # semaphores
        self._global_sem = asyncio.Semaphore(MAX_CONCURRENCY)
        self._per_operator_sem: Dict[str, asyncio.Semaphore] = {
            name: asyncio.Semaphore(PER_OPERATOR_CONCURRENCY) for name in self._drivers.keys()
        }

    # basic accessors
    def get(self, operator: str) -> BaseDriver:
        op = (operator or "").strip().lower()
        if op not in self._drivers:
            raise KeyError(f"Operadora nao suportada: {operator}")
        return self._drivers[op]

    def names(self) -> Iterable[str]:
        return self._drivers.keys()

    def items(self):
        return self._drivers.items()

    @property
    def drivers(self):
        return self._drivers

    def reload(self) -> None:
        for driver in self._drivers:
            if hasattr(driver, "_load_mapping"):
                driver._load_mapping()

    def _resolve_driver_name(self, driver: BaseDriver, fallback: Optional[str] = None) -> str:
        operator = getattr(driver, "operator", None)
        if isinstance(operator, str) and operator.strip():
            return operator.strip().lower()

        name_attr = getattr(driver, "name", None)
        if isinstance(name_attr, str) and name_attr.strip():
            return name_attr.strip().lower()

        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip().lower()

        return driver.__class__.__name__.lower()

    def _sync_driver_identity(self, driver: BaseDriver, fallback: Optional[str] = None) -> str:
        resolved = self._resolve_driver_name(driver, fallback)
        if not getattr(driver, "operator", None):
            driver.operator = resolved
        if not getattr(driver, "name", None):
            driver.name = resolved
        return resolved

    async def run_batch(
        self,
        identifiers: List[str],
        id_type: str,
        *,
        cache: Optional[object] = None,
        db: Optional[object] = None,
        progress_callback: Optional[
            Callable[[str, BaseDriver, DriverResult, bool], Awaitable[None]]
        ] = None,
    ) -> List[DriverResult]:
        """Executa uma lista de identificadores em todos os drivers compatÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­veis."""
        if not identifiers:
            return []

        results: List[DriverResult] = []
        active_drivers = [
            driver
            for driver in self._drivers.values()
            if id_type in getattr(driver, "supported_id_types", ("cpf",))
        ]

        for name, driver in self._drivers.items():
            if driver not in active_drivers:
                continue
            operator_name = self._sync_driver_identity(driver, fallback=name)
            logger.info(
                f"Iniciando driver {operator_name} com {len(identifiers)} CPFs"
            )
            print(
                f"[{operator_name}] iniciando consultas em lote ({len(identifiers)} itens)"
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
                logger.error(f"Erro no {operator_name}: {exc}")
                print(f"[DEBUG] {operator_name} falhou: {exc}")
                print(f"[{operator_name}] falha no lote: {exc}")
                for identifier in identifiers:
                    results.append(
                        DriverResult(
                            operator=operator_name,
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
        cache: Optional[object] = None,
        db: Optional[object] = None,
        progress_callback: Optional[
            Callable[[str, BaseDriver, DriverResult, bool], Awaitable[None]]
        ] = None,
    ) -> List[DriverResult]:
        results: List[DriverResult] = []
        operator_name = self._sync_driver_identity(driver)
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
                            if cached_data and self._is_valid_cached_data(cached_data):
                                cached_result = DriverResult(
                                    operator=operator_name,
                                    status=cached_data.get("status", "erro"),
                                    plan=cached_data.get("plan", ""),
                                    message=cached_data.get("message", ""),
                                    captured_at=cached_data.get("captured_at", ""),
                                    debug=cached_data.get("debug", {}),
                                    identifier=identifier,
                                    id_type=id_type,
                                )

                        if cached_result is not None:
                            logger.info(
                                f"{operator_name} retornou (cache): {cached_result}"
                            )
                            print(
                                f"[DEBUG] {operator_name} retorno (cache) -> {cached_result}"
                            )
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

                        logger.info(
                            f"Executando {operator_name} para {identifier}"
                        )
                        print(
                            f"[DEBUG] {operator_name}: processando {identifier}"
                        )
                        start = time.perf_counter()
                        try:
                            result = await driver.consult(
                                identifier, id_type, page=page
                            )
                        except Exception as exc:
                            logger.error(f"Erro no {operator_name}: {exc}")
                            print(f"[DEBUG] {operator_name} falhou: {exc}")
                            result = DriverResult(
                                operator=operator_name,
                                status="erro",
                                plan="",
                                message=str(exc),
                                debug={"exception": str(exc)},
                                identifier=identifier,
                                id_type=id_type,
                            )
                        duration = time.perf_counter() - start
                        results.append(result)
                        logger.info(f"{operator_name} retornou: {result}")
                        print(f"[DEBUG] {operator_name} retorno -> {result}")

                        if cache is not None and self._should_cache_result(result):
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
            logger.error(f"Erro no {operator_name}: {exc}")
            print(f"[DEBUG] {operator_name} falhou: {exc}")
            print(f"[{operator_name}] erro no navegador persistente: {exc}")
        return results

    @staticmethod
    def _is_valid_cached_data(data: Dict[str, object]) -> bool:
        status = str(data.get("status", "")).lower()
        if status in {"erro", "invalid", "indefinido"}:
            return False

        message = str(data.get("message", "")).lower()
        if "captcha" in message or "bloque" in message:
            return False

        debug = data.get("debug")
        if isinstance(debug, dict):
            if debug.get("block_detected"):
                return False
            debug_error = str(debug.get("error", "")).lower()
            if "captcha" in debug_error or "bloque" in debug_error:
                return False

        return True

    @staticmethod
    def _should_cache_result(result: DriverResult) -> bool:
        status = str(result.status or "").lower()
        if status in {"erro", "invalid", "indefinido"}:
            return False

        message = str(result.message or "").lower()
        if "captcha" in message or "bloque" in message:
            return False

        debug = result.debug
        if isinstance(debug, dict):
            if debug.get("block_detected"):
                return False
            debug_error = str(debug.get("error", "")).lower()
            if "captcha" in debug_error or "bloque" in debug_error:
                return False

        return True


manager = DriverManager()


