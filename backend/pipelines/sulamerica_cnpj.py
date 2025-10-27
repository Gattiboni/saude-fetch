import os
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Any

LOG_PATH = "/app/data/logs/sulamerica_cnpj.log"

SUL_CPF = os.environ.get("SUL_CPF", "")
SUL_EMAIL = os.environ.get("SUL_EMAIL", "")
SUL_PASS = os.environ.get("SUL_PASS", "")
SUL_CORRETORA = os.environ.get("SUL_CORRETORA", "")

# Helper
def digits_only(s: str) -> str:
    return "".join(ch for ch in str(s) if ch.isdigit())

def format_cnpj(c: str) -> str:
    d = digits_only(c)
    if len(d) != 14:
        return c
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"

async def _delay(min_s: float = 1.0, max_s: float = 3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))

def _log(line: str):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

async def check_single_cnpj(cnpj: str) -> Dict[str, Any]:
    # Placeholder: implement Playwright/Selenium here using provided creds/env
    # For now, obey mapping from brief:
    d = digits_only(cnpj)
    stamp = datetime.utcnow().isoformat() + "Z"
    # Simulados do brief
    if d == digits_only("56.319.166/0001-20"):
        status = "ativo"
        msg = "O CNPJ informado já possui plano."
    elif d == digits_only("11.325.048/0001-96"):
        status = "inativo"
        msg = "Não possui plano."
    else:
        status = "inativo"
        msg = "Sem plano identificado (placeholder)."
    # Log
    _log(f"{stamp} cnpj={format_cnpj(cnpj)} status={status} msg={msg}")
    return {
        "cnpj": format_cnpj(cnpj),
        "status": status,
        "mensagem_portal": msg,
        "timestamp": stamp,
    }

async def run_cnpj_pipeline(cnpjs: List[str]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    ativos = 0
    inativos = 0
    for c in cnpjs:
        await _delay(1.0, 3.0)
        item = await check_single_cnpj(c)
        results.append(item)
        if item["status"] == "ativo":
            ativos += 1
        else:
            inativos += 1
    return {"total": len(cnpjs), "ativos": ativos, "inativos": inativos, "items": results}
