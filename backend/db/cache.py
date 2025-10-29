import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


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
        return result["data"] if result else None

    async def set(self, operator: str, identifier: str, data: Dict[str, Any]) -> None:
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
