from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


async def record_metric(
    db: AsyncIOMotorDatabase,
    operator: str,
    identifier: str,
    success: bool,
    *,
    duration: float,
    cached: bool,
    extra: Any = None,
) -> None:
    payload = {
        "operator": operator,
        "identifier": identifier,
        "success": bool(success),
        "duration": float(duration),
        "cached": bool(cached),
        "timestamp": datetime.utcnow(),
    }
    if extra is not None:
        payload["extra"] = extra
    await db["metrics"].insert_one(payload)
