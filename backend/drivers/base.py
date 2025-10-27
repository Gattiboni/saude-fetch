import os
import json
import asyncio
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

MAPPINGS_DIR = "/app/docs/mappings"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
]

@dataclass
class DriverResult:
    operator: str
    status: str
    plan: str
    message: str

class BaseDriver:
    name: str = "base"
    requires_auth: bool = False
    max_retries: int = 2

    def __init__(self) -> None:
        self.mapping: Optional[Dict[str, Any]] = None
        self._load_mapping()

    def _mapping_path(self) -> str:
        return os.path.join(MAPPINGS_DIR, f"{self.name}.json")

    def _load_mapping(self) -> None:
        try:
            path = self._mapping_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.mapping = json.load(f)
            else:
                self.mapping = None
        except Exception:
            self.mapping = None

    def _get_delay_range(self) -> tuple[float, float]:
        try:
            lo = float(os.environ.get("FETCH_MIN_DELAY", "0.6"))
            hi = float(os.environ.get("FETCH_MAX_DELAY", "1.2"))
            if hi < lo:
                lo, hi = hi, lo
            return (lo, hi)
        except Exception:
            return (0.6, 1.2)

    def _choose_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    async def _throttle(self) -> None:
        lo, hi = self._get_delay_range()
        await asyncio.sleep(random.uniform(lo, hi))

    async def consult(self, identifier: str, id_type: str) -> DriverResult:
        # Generic retry wrapper
        attempt = 0
        last_err: Optional[str] = None
        while attempt <= self.max_retries:
            try:
                ua = self._choose_user_agent()  # picked UA (would be used on real HTTP)
                await self._throttle()
                return await self._perform(identifier, id_type)
            except Exception as e:
                last_err = str(e)
                attempt += 1
                await asyncio.sleep(min(2.0, 0.5 * (attempt + 1)))
        return DriverResult(operator=self.name, status="error", plan="", message=last_err or "erro desconhecido")

    async def _perform(self, identifier: str, id_type: str) -> DriverResult:
        # To be implemented by subclasses
        raise NotImplementedError
