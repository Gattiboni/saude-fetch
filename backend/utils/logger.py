import json
import os
from datetime import datetime
from typing import Any, Dict

class JobLogger:
    def __init__(self, job_id: str, log_dir: str) -> None:
        self.job_id = job_id
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.path = os.path.join(self.log_dir, f"{self.job_id}.log")

    def _write(self, record: Dict[str, Any]) -> None:
        record["time"] = datetime.utcnow().isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def info(self, msg: str, **kwargs: Any) -> None:
        self._write({"level": "INFO", "message": msg, **kwargs})

    def error(self, msg: str, **kwargs: Any) -> None:
        self._write({"level": "ERROR", "message": msg, **kwargs})
