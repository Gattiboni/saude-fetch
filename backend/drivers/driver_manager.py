# backend/drivers/driver_manager.py
import asyncio
import logging
from typing import Dict, Iterable, List, Any

from .amil import AmilDriver
from .bradesco import BradescoDriver
from .unimed import UnimedDriver
from .seguros_unimed import SegurosUnimedDriver
from .base import BaseDriver

logger = logging.getLogger("driver_manager")
logger.setLevel(logging.INFO)

# --- TUNE THESE FOR AGGRESSIVE PARALLELISM (you asked "go no limite") ---
MAX_CONCURRENCY = 50               # global simultaneous browser/worker slots
PER_OPERATOR_CONCURRENCY = 10      # simultaneous slots per operator
# ----------------------------------------------------------------------

class DriverManager:
    def __init__(self) -> None:
        # Instantiate driver objects (assumes drivers implement required async methods)
        self._drivers: Dict[str, BaseDriver] = {
            "amil": AmilDriver(),
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
            raise KeyError(f"Operadora não suportada: {operator}")
        return self._drivers[op]

    def names(self) -> Iterable[str]:
        return self._drivers.keys()

    def items(self):
        return self._drivers.items()

    @property
    def drivers(self):
        return self._drivers

    # ---- Core orchestration ----
    async def _run_one_with_semaphores(self, operator: str, identifier: str, job_context: dict = None) -> dict:
        """
        Run a single identifier under global + per-operator semaphores.
        Returns dict: {"id": identifier, "status": "positive|negative|error", "detail": ...}
        """
        driver = self.get(operator)
        op_sem = self._per_operator_sem.get(operator, asyncio.Semaphore(PER_OPERATOR_CONCURRENCY))

        async with self._global_sem, op_sem:
            try:
                # Preferred driver methods (in order)
                if hasattr(driver, "run_one") and asyncio.iscoroutinefunction(driver.run_one):
                    res = await driver.run_one(identifier, job_context)
                elif hasattr(driver, "run") and asyncio.iscoroutinefunction(driver.run):
                    # older drivers may have run(identifier) async
                    res = await driver.run(identifier, job_context)
                elif hasattr(driver, "execute") and asyncio.iscoroutinefunction(driver.execute):
                    res = await driver.execute(identifier, job_context)
                else:
                    # If driver only has sync method, call in threadpool
                    if hasattr(driver, "run_one"):
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(None, driver.run_one, identifier, job_context)
                    else:
                        raise NotImplementedError("Driver does not expose async run_one/run/execute methods")

                # normalise returned result into dict
                if isinstance(res, dict):
                    out = {"id": identifier, **res}
                else:
                    out = {"id": identifier, "status": "ok", "detail": res}
                logger.info("identifier_processed", operator=operator, identifier=identifier, result=out)
                return out
            except Exception as e:
                logger.exception("identifier_error", extra={"operator": operator, "identifier": identifier})
                return {"id": identifier, "status": "error", "detail": str(e)}

    async def run_batch(self, operator: str, identifiers: List[str], job_context: dict = None, concurrency: int = None) -> List[dict]:
        """
        Main entrypoint used by server code. Returns list of per-identifier dicts.
        Parameters:
          - operator: name of operator (e.g. "amil")
          - identifiers: list of CPFs (strings)
          - job_context: optional dict with job metadata (job_id, logger, etc.)
          - concurrency: optional override for MAX_CONCURRENCY for this batch (int)
        Behavior:
          - If driver implements async run_batch(operator, identifiers, job_context) it will be used directly.
          - Otherwise will execute per-identifier using semaphores.
        """
        operator = (operator or "").strip().lower()
        if operator not in self._drivers:
            raise KeyError(f"Operadora não suportada: {operator}")

        driver = self.get(operator)

        # If driver itself provides a batch method, prefer it (allows driver-specific optimizations)
        if hasattr(driver, "run_batch") and asyncio.iscoroutinefunction(driver.run_batch):
            logger.info("delegating_to_driver_run_batch", operator=operator, total=len(identifiers))
            try:
                res = await driver.run_batch(identifiers, job_context)
                logger.info("driver_run_batch_completed", operator=operator, total=len(identifiers))
                return res
            except Exception:
                logger.exception("driver_run_batch_failed", extra={"operator": operator})
                # fallback to per-id processing

        # Fallback: per-identifier parallel execution
        logger.info("running_per_identifier", operator=operator, total=len(identifiers))

        # Optionally override semaphores if concurrency param provided (simple local override)
        if concurrency and isinstance(concurrency, int) and concurrency > 0:
            # Replace the global sem temporarily for this batch
            temp_global = asyncio.Semaphore(concurrency)
            global_sem_backup = self._global_sem
            self._global_sem = temp_global
        else:
            global_sem_backup = None

        try:
            tasks = [self._run_one_with_semaphores(operator, ident, job_context) for ident in identifiers]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            return results
        finally:
            if global_sem_backup is not None:
                self._global_sem = global_sem_backup

    # convenience sync wrapper for code that may call manager.run_batch synchronously
    def run_batch_sync(self, *args, **kwargs) -> List[dict]:
        """
        Synchronous wrapper for run_batch. Uses asyncio.run().
        Use only in contexts where event loop is not running.
        """
        return asyncio.run(self.run_batch(*args, **kwargs))


# singleton instance used by server.py
manager = DriverManager()
