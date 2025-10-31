# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import random
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

async_playwright = None
try:
    import importlib

    _pw = importlib.import_module("playwright.async_api")
    async_playwright = getattr(_pw, "async_playwright", None)
except Exception:
    # Allow static analysis to succeed when playwright is not installed; runtime
    # callers will get a clear ImportError.
    async_playwright = None
    logging.getLogger(__name__).warning(
        "playwright.async_api not available; browser automation functions will fail if invoked."
    )


def _resolve_mappings_dir() -> str:
    # 1) Se o env estiver setado e a pasta existir, usar
    env_dir = os.environ.get("MAPPINGS_DIR")
    if env_dir and os.path.isdir(env_dir):
        return os.path.normpath(env_dir)

    # 2) Caminho relativo ao arquivo atual: backend/drivers/ -> ../docs/mappings
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.normpath(os.path.join(here, "..", "docs", "mappings")),
        # 3) Alternativas comuns, caso a estrutura mude levemente
        os.path.normpath(os.path.join(here, "..", "..", "docs", "mappings")),
        os.path.normpath(os.path.join(os.getcwd(), "backend", "docs", "mappings")),
        os.path.normpath(os.path.join(os.getcwd(), "docs", "mappings")),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    # 4) Ultimo recurso: volta para o 1o candidato (mesmo que nao exista)
    return candidates[0]


MAPPINGS_DIR = _resolve_mappings_dir()
_PRINTED_MAPPINGS_DIR = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "data"))
ERRORS_DIR = os.path.normpath(os.path.join(DATA_DIR, "errors"))
STORAGE_STATES_DIR = os.path.normpath(os.path.join(DATA_DIR, "storage_states"))

os.makedirs(ERRORS_DIR, exist_ok=True)
os.makedirs(STORAGE_STATES_DIR, exist_ok=True)

FETCH_MIN_DELAY = float(os.getenv("FETCH_MIN_DELAY", "0.5"))
FETCH_MAX_DELAY = float(os.getenv("FETCH_MAX_DELAY", "1.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
TIMEOUT_SELECTOR_MS = int(os.getenv("TIMEOUT_SELECTOR_MS", "20000"))
BLOCK_SLEEP_SECONDS = int(os.getenv("BLOCK_SLEEP_SECONDS", "120"))
DEFAULT_BLOCK_KEYWORDS = [
    "captcha",
    "bloque",
    "bloqueado",
    "bloqueio",
    "acesso negado",
]

async def launch_chrome_real(headless: bool = False, slow_mo: int = 150):
    if async_playwright is None:
        raise ImportError(
            "playwright.async_api is not available; install the 'playwright' package and run 'playwright install' to enable browser automation."
        )
    pw = await async_playwright().start()
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    user_dir = os.path.join(os.getcwd(), "chrome_profile_amil")
    os.makedirs(user_dir, exist_ok=True)
logger = logging.getLogger(__name__)


async def launch_chrome_real(headless: bool = False, slow_mo: int = 150):
    pw = await async_playwright().start()
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    user_dir = os.path.join(os.getcwd(), "chrome_profile_amil")
    os.makedirs(user_dir, exist_ok=True)

    # Abre Chrome real com contexto persistente e janela separada
    browser_context = await pw.chromium.launch_persistent_context(
        user_dir,
        headless=False,
        slow_mo=slow_mo,
        executable_path=chrome_path,
        viewport=None,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "--start-maximized",
        ],
    )
    page = await browser_context.new_page()
    try:
        await page.evaluate(
            "window.moveTo(0,0); window.resizeTo(screen.width, screen.height);"
        )
    except Exception:
        pass
    return browser_context.browser, browser_context, page



class BlockedRequestError(Exception):
    """Raised when the remote website indicates an anti-bot block."""


def normalize_text(value: str) -> str:
    """Normaliza texto removendo espacos repetidos e padronizando para maiusculas."""
    if not value:
        return ""
    cleaned = value.replace("\u00A0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().upper()


async def _run(page: Any) -> None:
    """
    No-op legacy runner to satisfy older code paths that call `await _run(page)`.
    New mappings should use the declarative "steps" flow; this placeholder prevents
    a NameError when a legacy call is made without providing an implementation.
    """
    # Intentionally do nothing; keep function asynchronous to match previous usage.
    return None


@dataclass
class DriverResult:
    operator: str
    status: str
    plan: str = ""
    message: str = ""
    captured_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    debug: Dict[str, Any] = field(default_factory=dict)
    identifier: str = ""
    id_type: str = ""

class BaseDriver:
    """
    Contrato minimo exigido pelo pipeline:
    - .operator (lowercase)
    - .name     (igual ao operator; algumas partes do codigo usam .name)
    - .mapping  (dict carregado a partir de <MAPPINGS_DIR>/<OPERATOR>.json)
    - .consult(identifier, id_type) -> DriverResult
    """
    def __init__(self, operator: str, supported_id_types: Optional[Tuple[str, ...]] = None):
        self.operator = operator.lower()
        self.name = self.operator  # <- FALTAVA. O pipeline usa driver.name
        self.mapping = None
        self.supported_id_types: Tuple[str, ...] = tuple(
            supported_id_types or ("cpf",)
        )
        global _PRINTED_MAPPINGS_DIR
        if not _PRINTED_MAPPINGS_DIR:
            print(f"[drivers] using MAPPINGS_DIR: {MAPPINGS_DIR}")
            _PRINTED_MAPPINGS_DIR = True

        self.mapping_path = self._resolve_mapping_path()

        if os.path.exists(self.mapping_path):
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    self.mapping = json.load(f)
            except Exception as e:
                print(f"[{self.operator}] erro ao carregar mapping: {e}")
        else:
            print(f"[{self.operator}] mapping nao encontrado em {self.mapping_path}")

    def _load_mapping(self):
        """Permite reload sem recriar a instancia."""
        resolved_path = self._resolve_mapping_path()
        if resolved_path != self.mapping_path:
            print(
                f"[{self.operator}] atualizando caminho do mapping para {resolved_path}"
            )
            self.mapping_path = resolved_path
        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                self.mapping = json.load(f)
        except Exception as e:
            self.mapping = None
            print(f"[{self.operator}] erro no reload do mapping: {e}")

    def step(self, message: str) -> None:
        logger.debug(f"[{self.operator}] {message}")
        print(f"[DEBUG] [{self.operator}] {message}")

    def log_exception(self, error: Exception) -> None:
        logger.error(f"[{self.operator}] ERRO durante execucao: {error}")
        print(f"[DEBUG] [{self.operator}] ERRO durante execucao: {error}")

    def _resolve_mapping_path(self) -> str:
        """Resolve o caminho do mapping aceitando variacoes de nomenclatura."""
        base_filename = f"{self.operator}.json"
        candidates = [os.path.join(MAPPINGS_DIR, base_filename)]

        collapsed = self.operator.replace("_", "")
        if collapsed and collapsed != self.operator:
            candidates.append(os.path.join(MAPPINGS_DIR, f"{collapsed}.json"))

        dashed = self.operator.replace("_", "-")
        if dashed and dashed not in {self.operator, collapsed}:
            candidates.append(os.path.join(MAPPINGS_DIR, f"{dashed}.json"))

        for candidate in candidates:
            if os.path.exists(candidate):
                if candidate != candidates[0]:
                    print(
                        f"[{self.operator}] mapping encontrado usando variacao de nome: {candidate}"
                    )
                return candidate

        return candidates[0]

    async def consult(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        if id_type not in self.supported_id_types:
            raise ValueError(f"{self.operator} nao suporta identificador do tipo '{id_type}'")

        self.step(f"Iniciando consulta para {id_type.upper()} {identifier}")

        for attempt in range(MAX_RETRIES):
            try:
                self.step(f"Tentativa {attempt + 1}/{MAX_RETRIES} para {identifier}")
                await asyncio.sleep(random.uniform(FETCH_MIN_DELAY, FETCH_MAX_DELAY))
                self.step("Disparando fluxo principal do driver")
                result = await self._perform(identifier, id_type, page=page)
                if not result.identifier:
                    result.identifier = identifier
                if not result.id_type:
                    result.id_type = id_type
                self.step(
                    f"Resultado final: status={result.status} | plano={result.plan or '-'} | mensagem={result.message or '-'}"
                )
                return result
            except BlockedRequestError as block:
                self.log_exception(block)
                logger.warning(
                    'Bloqueio detectado em %s: %s (tentativa %s/%s)',
                    self.operator,
                    block,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(BLOCK_SLEEP_SECONDS)
            except Exception as exc:
                self.log_exception(exc)
                if attempt + 1 == MAX_RETRIES:
                    self.step('Ultima tentativa esgotada, retornando erro para o pipeline')
                    return DriverResult(
                        operator=self.operator,
                        status='erro',
                        plan='',
                        message=str(exc),
                        identifier=identifier,
                        id_type=id_type,
                    )
                await asyncio.sleep(1.25)

        return DriverResult(
            operator=self.operator,
            status='erro',
            message='falha apos retries',
            identifier=identifier,
            id_type=id_type,
        )

    async def _perform(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        """
        Implementacao base:
        - Se houver 'steps' no mapping, executa o fluxo declarativo.
        - Senao, tenta legado via selectors.cpf / selectors.submit.
        """
        if not self.mapping:
            raise Exception("mapping ausente para este driver")

        if "steps" in self.mapping:
            return await self._execute_steps(identifier, id_type, page=page)
        if page is not None:
            await _run(page)
        else:
            if async_playwright is None:
                raise ImportError(
                    "playwright.async_api is not available; install the 'playwright' package and run 'playwright install' to enable browser automation."
                )
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--start-maximized"],
                )
                page_obj = await browser.new_page(viewport=None)
                try:
                    await page_obj.evaluate(
                        "window.moveTo(0,0); window.resizeTo(screen.width, screen.height);"
                    )
                except Exception:
                    pass
                try:
                    await _run(page_obj)
                finally:
                    await browser.close()
                page_obj = await browser.new_page(viewport=None)
                try:
                    await page_obj.evaluate(
                        "window.moveTo(0,0); window.resizeTo(screen.width, screen.height);"
                    )
                except Exception:
                    pass
                try:
                    await _run(page_obj)
                finally:
                    await browser.close()

        return DriverResult(
            operator=self.operator,
            status="indefinido",
            message="driver legado executado",
            identifier=identifier,
            id_type=id_type,
        )

    @asynccontextmanager
    async def _persistent_browser(self):
        browser, context, page = await launch_chrome_real(headless=False, slow_mo=150)

        storage_file = os.path.join(STORAGE_STATES_DIR, f"{self.operator}.json")
        storage_state = None
        if os.path.exists(storage_file):
            try:
                with open(storage_file, "r", encoding="utf-8") as fh:
                    storage_state = json.load(fh)
            except Exception as exc:
                logger.debug(
                    "[%s] falha ao carregar storage state: %s", self.operator, exc
                )

        await context.add_init_script(
            """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = {runtime: {}};
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt']});
"""
        )
        if storage_state:
            cookies = storage_state.get("cookies") or []
            if cookies:
                try:
                    await context.add_cookies(cookies)
                except Exception as exc:
                    logger.debug(
                        "[%s] falha ao restaurar cookies: %s", self.operator, exc
                    )
            origins = storage_state.get("origins") or []
            for origin in origins:
                origin_url = origin.get("origin")
                local_storage_items = origin.get("localStorage") or []
                if not origin_url or not local_storage_items:
                    continue
                assignments = ";".join(
                    f"window.localStorage.setItem({json.dumps(item.get('name', ''))}, {json.dumps(item.get('value', ''))});"
                    for item in local_storage_items
                    if item.get("name") is not None
                )
                if not assignments:
                    continue
                script = f"""
(function() {{
    if (window.location.origin === {json.dumps(origin_url)}) {{
        try {{
            {assignments}
        }} catch (e) {{}}
    }}
}})();
"""
                await context.add_init_script(script)

        await context.grant_permissions(["geolocation"])

        if self.operator == "amil":
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://www.amil.com.br/",
                }
            )

        try:
            yield page
            try:
                await context.storage_state(path=storage_file)
            except Exception as exc:
                logger.debug("[%s] falha ao salvar storage state: %s", self.operator, exc)
        finally:
            await context.close()
            await browser.close()
            playwright = getattr(browser, "_playwright_instance", None)
            if playwright is not None:
                await playwright.stop()

    async def _execute_steps(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        if page is not None:
            return await self._execute_steps_on_page(page, identifier, id_type)

        async with self._persistent_browser() as page_obj:
            return await self._execute_steps_on_page(page_obj, identifier, id_type)

    async def _execute_steps_on_page(
        self, page: Any, identifier: str, id_type: str
    ) -> DriverResult:
        steps = self.mapping.get("steps", [])
        parsing = self.mapping.get("result_parsing", {})
        url = self.mapping.get("url")

        run_debug: Dict[str, Any] = {
            "mapping_path": self.mapping_path,
            "steps": [],
        }

        try:
            if url:
                self.step(f"Navegando para {url}")
                await page.goto(url)
                run_debug.setdefault("navigation", {}).update({"target": url})

            for idx, step in enumerate(steps):
                self.step(f"Executando passo {idx}: {step.get('action', 'desconhecido')}")
                await self._run_step(page, step, identifier, run_debug, idx)

            block_indicators = [
                str(item).lower()
                for item in self.mapping.get("block_indicators", [])
                if str(item).strip()
            ]
            if not block_indicators:
                block_indicators = list(DEFAULT_BLOCK_KEYWORDS)

            if block_indicators:
                self.step("Verificando indicadores de bloqueio")
                html_snapshot = (await page.content()).lower()
                if any(indicator in html_snapshot for indicator in block_indicators):
                    run_debug.setdefault("block_detected", True)
                    raise BlockedRequestError("indicativo de bloqueio detectado na pagina")

            self.step("Verificando elemento de sucesso e extraindo resultado")
            status, plan, message, parse_debug = await self._parse_result(page, parsing)
            run_debug.update(parse_debug)
        except Exception as error:
            self.log_exception(error)
            screenshot_path = await self._capture_failure_artifact(page)
            if screenshot_path:
                run_debug.setdefault("artifacts", {})["screenshot"] = screenshot_path
            run_debug.setdefault("error", str(error))
            return DriverResult(
                operator=self.operator,
                status="erro",
                plan="",
                message=str(error),
                debug=run_debug,
                identifier=identifier,
                id_type=id_type,
            )

        self.step(
            f"Resultado final: status={status} | plano={plan or '-'} | mensagem={message or '-'}"
        )
        return DriverResult(
            operator=self.operator,
            status=status,
            plan=plan,
            message=message,
            debug=run_debug,
            identifier=identifier,
            id_type=id_type,
        )

    async def _run_step(
        self,
        page: Any,
        step: Dict[str, Any],
        identifier: str,
        run_debug: Dict[str, Any],
        index: int,
    ) -> None:
        action = step.get("action")
        optional = bool(step.get("optional", False))
        post_delay = float(step.get("delay", 0.0)) if step.get("delay") else 0.0
        post_wait_selector = step.get("wait_selector")
        timeout = step.get("timeout_ms", TIMEOUT_SELECTOR_MS)

        step_log = {
            "index": index,
            "action": action,
            "selector": step.get("selector"),
            "target": step.get("target"),
            "key": step.get("key"),
            "timeout_ms": timeout,
            "optional": optional,
        }

        wait_for_any = step.get("wait_for_any") or []
        if isinstance(wait_for_any, str):
            wait_for_any = [wait_for_any]

        try:
            if action == "navigate":
                target = step.get("target") or self.mapping.get("url")
                if target:
                    self.step(f"Navegando para {target}")
                    await page.goto(target)
                wait_for = step.get("wait_for")
                if isinstance(wait_for, list):
                    self.step("Aguardando um dos seletores de destino ficar visivel")
                    matched = await self._wait_for_any(
                        page, wait_for, timeout, state="visible"
                    )
                    step_log["matched_wait_for"] = matched
                elif wait_for:
                    self.step(f"Aguardando selector {wait_for}")
                    await page.locator(wait_for).first.wait_for(
                        state="visible", timeout=timeout
                    )
                    step_log["matched_wait_for"] = wait_for
                if wait_for_any:
                    self.step("Aguardando qualquer selector adicional configurado")
                    matched = await self._wait_for_any(
                        page, wait_for_any, timeout, state="visible"
                    )
                    step_log["matched_wait_for_any"] = matched
            elif action == "fill":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("fill action requer 'selector'")
                val = (step.get("value") or "").replace("{identifier}", identifier)
                self.step(f"Preenchendo campo {selector} com valor {val}")
                await page.fill(selector, val, timeout=timeout)
                self.step("Campo preenchido com sucesso")
            elif action == "click":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("click action requer 'selector'")
                click_kwargs = {"timeout": timeout}
                if step.get("force"):
                    click_kwargs["force"] = True
                if step.get("no_wait_after") is not None:
                    click_kwargs["no_wait_after"] = bool(step.get("no_wait_after"))
                self.step(f"Clicando no elemento {selector}")
                await page.click(selector, **click_kwargs)
            elif action == "keypress":
                key = step.get("key", "Enter")
                self.step(f"Pressionando tecla {key}")
                await self.keypress(page, step.get("selector"), key=key, timeout=timeout)
                self.step(f"Tecla {key} enviada")
            elif action == "wait_for":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("wait_for action requer 'selector'")
                if isinstance(selector, list):
                    self.step("Aguardando qualquer selector configurado ficar disponivel")
                    matched = await self._wait_for_any(
                        page,
                        selector,
                        timeout,
                        state=step.get("state", "visible"),
                    )
                    step_log["matched_wait_for"] = matched
                else:
                    self.step(f"Aguardando selector {selector}")
                    await page.locator(selector).first.wait_for(
                        state=step.get("state", "visible"), timeout=timeout
                    )
                    step_log["matched_wait_for"] = selector
            elif action == "wait_for_state":
                state = step.get("state", "load")
                self.step(f"Aguardando estado de carregamento {state}")
                await page.wait_for_load_state(state)
            elif action == "sleep":
                post_delay = float(step.get("seconds", 0.0))
                self.step(f"Aguardando {post_delay} segundos antes de continuar")
            else:
                raise ValueError(f"acao desconhecida: {action}")
            step_log["status"] = "ok"
        except Exception as error:
            if optional:
                self.step(f"Passo opcional '{action}' ignorado por erro: {error}")
                step_log["status"] = "skipped"
                step_log["error"] = str(error)
            else:
                self.log_exception(error)
                step_log["status"] = "error"
                step_log["error"] = str(error)
                run_debug.setdefault("steps", []).append(step_log)
                raise
        finally:
            if post_wait_selector:
                try:
                    if isinstance(post_wait_selector, list):
                        self.step("Aguardando pos-acao por qualquer selector configurado")
                        matched = await self._wait_for_any(
                            page, post_wait_selector, timeout, state="visible"
                        )
                        step_log["matched_post_wait"] = matched
                    else:
                        self.step(f"Aguardando pos-acao pelo selector {post_wait_selector}")
                        await page.locator(post_wait_selector).first.wait_for(
                            state="visible", timeout=timeout
                        )
                        step_log["matched_post_wait"] = post_wait_selector
                except Exception as wait_err:
                    if not optional:
                        self.log_exception(wait_err)
                        step_log.setdefault("warnings", []).append(str(wait_err))
            elif post_delay:
                self.step(f"Aguardando {post_delay} segundos (delay configurado)")
                await page.wait_for_timeout(int(post_delay * 1000))

        run_debug.setdefault("steps", []).append(step_log)

    async def keypress(
        self, page: Any, selector: Optional[str], key: str = "Enter", timeout: Optional[int] = None
    ) -> None:
        if selector:
            await page.press(selector, key, timeout=timeout)
        else:
            await page.keyboard.press(key)

    async def _wait_for_any(
        self,
        page: Any,
        selectors: Iterable[str],
        timeout: int,
        state: str = "visible",
    ) -> str:
        selector_list = [candidate for candidate in selectors if candidate]
        last_error: Optional[Exception] = None
        for candidate in selector_list:
            try:
                await page.locator(candidate).first.wait_for(
                    state=state, timeout=timeout
                )
                return candidate
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise TimeoutError(
                f"Nenhum seletor em {selector_list} foi encontrado: {last_error}"
            )
        raise TimeoutError(f"Nenhum seletor valido informado: {selector_list}")

    async def _parse_result(self, page: Any, parsing: Dict[str, Any]):
        status_selectors = parsing.get("status_selectors") or (
            parsing.get("status_selector_any")
            or parsing.get("status_selector")
        )
        if isinstance(status_selectors, str):
            status_selectors = [status_selectors]

        if not status_selectors:
            return "erro", "", "status_selector ausente", {
                "status_selector": None,
                "status_timeout_ms": parsing.get("status_timeout_ms", 12000),
                "captured_text": "",
            }

        status_timeout = parsing.get("status_timeout_ms", TIMEOUT_SELECTOR_MS)
        poll_interval = max(
            0.1, float(parsing.get("status_poll_interval_ms", 300)) / 1000.0
        )
        raw_text = ""
        matched_selector: Optional[str] = None

        self.step("Verificando seletores de status para identificar o resultado")
        for selector in status_selectors:
            self.step(f"Verificando seletor de status {selector}")
            locator = page.locator(selector).first
            deadline = time.monotonic() + (status_timeout / 1000.0)
            candidate_text = ""

            while time.monotonic() < deadline:
                try:
                    await locator.wait_for(
                        state="visible",
                        timeout=min(1000, max(200, int(poll_interval * 1000))),
                    )
                except Exception:
                    pass
                try:
                    candidate = (await locator.inner_text()).strip()
                except Exception:
                    candidate = ""
                if candidate:
                    candidate_text = candidate
                    break
                await asyncio.sleep(poll_interval)

            if candidate_text:
                raw_text = candidate_text
                matched_selector = selector
                break

        if not raw_text:
            try:
                page_html = (await page.content()).lower()
                if "captcha" in page_html or "bloque" in page_html:
                    raise BlockedRequestError("bloqueio detectado (captcha)")
            except BlockedRequestError:
                raise
            except Exception:
                pass

        if matched_selector:
            self.step(f"Texto de status encontrado no seletor {matched_selector}")
            print(
                f"[{self.operator}] texto capturado em '{matched_selector}': {raw_text[:200]}"
            )
        else:
            self.step("Nenhum seletor de status retornou informacao")
            print(
                f"[{self.operator}] nenhum texto encontrado para {status_selectors}"
            )

        normalized = normalize_text(raw_text)
        positive = [normalize_text(s) for s in parsing.get("positive_keywords", [])]
        negative = [normalize_text(s) for s in parsing.get("negative_keywords", [])]
        errors = [normalize_text(s) for s in parsing.get("error_keywords", [])]

        status = "indefinido"
        if normalized and any(k and k in normalized for k in positive):
            status = "ativo"
        elif normalized and any(k and k in normalized for k in negative):
            status = "inativo"
        elif normalized and any(k and k in normalized for k in errors):
            status = "erro"

        message = raw_text[:300]

        plan = ""
        plan_selectors = parsing.get("plan_selectors") or parsing.get("plan_selector")
        if isinstance(plan_selectors, str):
            plan_selectors = [plan_selectors]
        plan_text = ""
        last_error: Optional[Exception] = None
        if plan_selectors:
            for selector in plan_selectors:
                try:
                    self.step(f"Capturando informacoes de plano no seletor {selector}")
                    plan_locator = page.locator(selector).first
                    await plan_locator.wait_for(
                        state="visible", timeout=status_timeout
                    )
                    plan_candidate = (await plan_locator.inner_text()).strip()
                    if plan_candidate:
                        plan_text = plan_candidate
                        plan = plan_candidate[:300]
                        break
                except Exception as err:
                    last_error = err
                    continue
            else:
                if (
                    not parsing.get("plan_optional", False)
                    and last_error is not None
                ):
                    self.log_exception(last_error)
                    print(
                        f"[{self.operator}] falha ao capturar plano em '{plan_selectors}': {last_error}"
                    )

        if plan_text:
            normalized_plan = normalize_text(plan_text)
            if normalized_plan and status in {"indefinido", "inativo"}:
                status = "ativo"
        elif status == "ativo" and message:
            plan = message

        debug_info = {
            "status_selector": matched_selector or status_selectors,
            "status_timeout_ms": status_timeout,
            "captured_text": raw_text[:500],
            "plan_selector": plan_selectors,
            "plan_text": plan_text[:500] if plan_text else "",
            "decided_status": status,
        }

        self.step(
            f"Parse concluido: status={status} | plano={plan or '-'} | mensagem={message or '-'}"
        )
        return status, plan, message, debug_info

    async def _capture_failure_artifact(self, page: Any) -> Optional[str]:
        if page is None:
            return None
        try:
            operator_dir = os.path.join(ERRORS_DIR, self.operator)
            os.makedirs(operator_dir, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(operator_dir, f"{ts}.png")
            await page.screenshot(path=path, full_page=True)
            return os.path.normpath(path)
        except Exception as exc:
            print(f"[{self.operator}] falha ao salvar screenshot de erro: {exc}")
            return None



