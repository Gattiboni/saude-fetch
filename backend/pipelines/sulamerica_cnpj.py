import os
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

LOG_PATH = "/app/data/logs/sulamerica_cnpj.log"
ERROR_DIR = "/app/data/errors/sulamerica"

SUL_CPF = os.environ.get("SUL_CPF", "")
SUL_EMAIL = os.environ.get("SUL_EMAIL", "")
SUL_PASS = os.environ.get("SUL_PASS", "")
SUL_CORRETORA = os.environ.get("SUL_CORRETORA", "")

LOGIN_URL = "https://os11.sulamerica.com.br/SaudeCotador/LoginVendedor.aspx"

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


def _ensure_dirs():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)


def _log(line: str):
    _ensure_dirs()
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


async def screenshot(page, label: str):
    try:
        _ensure_dirs()
        fname = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{label}.png"
        path = os.path.join(ERROR_DIR, fname)
        await page.screenshot(path=path, full_page=True)
        _log(f"screenshot saved: {path}")
    except Exception as e:
        _log(f"screenshot failed: {e}")


async def login_and_navigate(page) -> None:
    # 1) Login
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await _delay()
    _log("Acessou página de login")

    # Campos: CPF, E-mail, Senha — tentativas robustas de seleção
    filled = 0
    for sel in [
        'input[name="cpf"]', 'input[id*="cpf"]', 'input[placeholder*="CPF"]', 'input[aria-label*="CPF"]'
    ]:
        try:
            await page.fill(sel, SUL_CPF)
            filled += 1
            break
        except Exception:
            pass
    for sel in [
        'input[name="email"]', 'input[id*="email"]', 'input[placeholder*="mail"]', 'input[aria-label*="mail"]'
    ]:
        try:
            await page.fill(sel, SUL_EMAIL)
            filled += 1
            break
        except Exception:
            pass
    for sel in [
        'input[type="password"]', 'input[name*="senha"]', 'input[id*="senha"]'
    ]:
        try:
            await page.fill(sel, SUL_PASS)
            filled += 1
            break
        except Exception:
            pass

    if filled < 3:
        await screenshot(page, "login_fields_not_found")
        raise RuntimeError("Campos de login não encontrados")

    # Clicar no botão Entrar
    clicked = False
    for sel in [
        'button:has-text("Entrar")', 'input[type="submit"]', 'button:has-text("Login")'
    ]:
        try:
            await page.click(sel)
            clicked = True
            break
        except Exception:
            pass
    if not clicked:
        await screenshot(page, "login_button_not_found")
        raise RuntimeError("Botão de login não encontrado")

    # Aguarda redirecionamento/carga (10s timeout)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PWTimeoutError:
        _log("Aviso: timeout pós-login, seguindo adiante")

    _log("Login submetido")

    # 2) Código da corretora
    await _delay()
    code_filled = False
    for sel in [
        'input[name*="corretora"]', 'input[id*="corretora"]', 'input[placeholder*="corretora"]'
    ]:
        try:
            await page.fill(sel, SUL_CORRETORA)
            code_filled = True
            break
        except Exception:
            pass
    if not code_filled:
        await screenshot(page, "corretora_input_not_found")
        raise RuntimeError("Campo código da corretora não encontrado")

    advanced = False
    for sel in [
        'button:has-text("Avançar")', 'button:has-text("Continuar")', 'input[type="submit"]'
    ]:
        try:
            await page.click(sel)
            advanced = True
            break
        except Exception:
            pass
    if not advanced:
        await screenshot(page, "corretora_button_not_found")
        raise RuntimeError("Botão para avançar após corretora não encontrado")

    _log("Código corretora enviado")

    # 3) Nova Cotação – PME
    await _delay()
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PWTimeoutError:
        pass

    clicked_nova = False
    for sel in [
        'button:has-text("Nova Cotação")', 'a:has-text("Nova Cotação")', 'button:has-text("PME")'
    ]:
        try:
            await page.click(sel)
            clicked_nova = True
            break
        except Exception:
            pass
    if not clicked_nova:
        await screenshot(page, "nova_cotacao_button_not_found")
        raise RuntimeError("Botão Nova Cotação não encontrado")

    _log("Nova Cotação acionada")

    # 4) Quantidade de Vidas / Odonto (valores fixos)
    await _delay()
    # tentar qualquer campo numérico inicial
    for sel in [
        'input[type="number"]', 'input[name*="vidas"]', 'input[id*="vidas"]'
    ]:
        try:
            await page.fill(sel, "5")
            break
        except Exception:
            pass

    # Continuar
    for sel in [
        'button:has-text("Continuar")', 'button:has-text("Avançar")', 'input[type="submit"]'
    ]:
        try:
            await page.click(sel)
            break
        except Exception:
            pass

    _log("Quantidade de vidas preenchida")

    # 5) Cuidado 360° (seguir default)
    await _delay()
    for sel in [
        'button:has-text("Continuar")', 'button:has-text("Avançar")', 'input[type="submit"]'
    ]:
        try:
            await page.click(sel)
            break
        except Exception:
            pass

    _log("Cuidado 360° avançado")


async def check_single_cnpj_real(page, cnpj: str) -> Dict[str, Any]:
    await _delay()
    stamp = datetime.utcnow().isoformat() + "Z"
    # 6) Informar CNPJ
    filled = False
    for sel in [
        'input[name*="cnpj"]', 'input[id*="cnpj"]', 'input[placeholder*="CNPJ"]', 'input[aria-label*="CNPJ"]'
    ]:
        try:
            await page.fill(sel, format_cnpj(cnpj))
            filled = True
            break
        except Exception:
            pass
    if not filled:
        await screenshot(page, "cnpj_input_not_found")
        raise RuntimeError("Campo CNPJ não encontrado")

    # Enviar / Prosseguir
    advanced = False
    for sel in [
        'button:has-text("Continuar")', 'button:has-text("Avançar")', 'input[type="submit"]'
    ]:
        try:
            await page.click(sel)
            advanced = True
            break
        except Exception:
            pass

    if not advanced:
        _log("Aviso: botão continuar após CNPJ não encontrado, seguindo")

    # Esperar feedback
    await _delay()
    status = "inativo"
    message = ""

    # Heurística: buscar mensagem indicando bloqueio por plano existente
    try:
        locator = page.locator("text=já possui plano")
        if await locator.count() > 0:
            status = "ativo"
            message = "O CNPJ informado já possui plano."
    except Exception:
        pass

    _log(f"CNPJ {format_cnpj(cnpj)} → {status}")
    return {
        "cnpj": format_cnpj(cnpj),
        "status": status,
        "mensagem_portal": message or ("O CNPJ informado já possui plano." if status == "ativo" else ""),
        "timestamp": stamp,
    }


async def run_cnpj_pipeline(cnpjs: List[str]) -> Dict[str, Any]:
    _ensure_dirs()
    # Sanitiza entradas
    norm = [digits_only(c) for c in cnpjs if digits_only(c)]
    results: List[Dict[str, Any]] = []
    ativos = 0
    inativos = 0

    login_attempts = 0
    while True:
        login_attempts += 1
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await login_and_navigate(page)

                for c in norm:
                    try:
                        item = await check_single_cnpj_real(page, c)
                    except Exception as e:
                        await screenshot(page, f"cnpj_error_{c}")
                        item = {
                            "cnpj": format_cnpj(c),
                            "status": "erro",
                            "mensagem_portal": str(e),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    results.append(item)
                    if item["status"] == "ativo":
                        ativos += 1
                    elif item["status"] == "inativo":
                        inativos += 1

                await context.close()
                await browser.close()
                break
        except Exception as e:
            _log(f"Erro no fluxo principal: {e}")
            if login_attempts >= 3:
                break
            await asyncio.sleep(2.0 * login_attempts)

    return {
        "total": len(norm),
        "ativos": ativos,
        "inativos": inativos,
        "resultados": results,
        "items": results,
    }
