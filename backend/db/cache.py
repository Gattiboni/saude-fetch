import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


ERROR_STATUSES = {"erro", "invalid", "indefinido"}


def _is_cacheable_payload(payload: Dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).lower()
    if status in ERROR_STATUSES:
        return False

    message = str(payload.get("message", "")).lower()
    if "captcha" in message or "bloque" in message:
        return False

    debug = payload.get("debug")
    if isinstance(debug, dict):
        if debug.get("block_detected"):
            return False
        debug_error = str(debug.get("error", "")).lower()
        if "captcha" in debug_error or "bloque" in debug_error:
            return False

    return True


class Cache:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db["cache_results"]

    async def get(self, operator: str, identifier: str) -> Optional[Dict[str, Any]]:
        result = await self.collection.find_one(
            {
                "operator": operator,
                "identifier": identifier,
                "expires_at": {"$gt": datetime.utcnow()},
            }
        )
        if not result:
            return None

        data = result.get("data", {})
        if not isinstance(data, dict) or not _is_cacheable_payload(data):
            # Remove entradas antigas não cacheáveis para evitar hits futuros.
            try:
                await self.collection.delete_one({"_id": result["_id"]})
            except Exception:
                pass
            return None

        return data

    async def set(self, operator: str, identifier: str, data: Dict[str, Any]) -> None:
        if not _is_cacheable_payload(data):
            return
        ttl_days = int(data.get("ttl_days") or 0) or int(
            data.pop("cache_ttl_days", 0) or 0
        )
        if not ttl_days:
            ttl_days = int(os.getenv("CACHE_TTL_DAYS", "7"))
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        await self.collection.update_one(
            {"operator": operator, "identifier": identifier},
            {
                "$set": {
                    "data": data,
                    "expires_at": expires_at,
                    "operator": operator,
                    "identifier": identifier,
                }
            },
            upsert=True,
        )
