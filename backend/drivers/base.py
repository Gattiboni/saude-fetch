import asyncio
import json
import os
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import async_playwright

FETCH_MIN_DELAY = float(os.getenv("FETCH_MIN_DELAY", "0.5"))
FETCH_MAX_DELAY = float(os.getenv("FETCH_MAX_DELAY", "1.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Usa variável de ambiente ou fallback consistente com o diretório do arquivo
_DEFAULT_MAPPINGS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "mappings")
)
MAPPINGS_DIR = os.path.abspath(os.getenv("MAPPINGS_DIR", _DEFAULT_MAPPINGS_DIR))

@dataclass
class DriverResult:
    operator: str
    status: str
    plan: str = ""
    message: str = ""
    captured_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class BaseDriver:
    """
    Contrato mínimo exigido pelo pipeline:
    - .operator (lowercase)
    - .name     (igual ao operator; algumas partes do código usam .name)
    - .mapping  (dict carregado a partir de <MAPPINGS_DIR>/<OPERATOR>.json)
    - .consult(identifier, id_type) -> DriverResult
    """
    def __init__(self, operator: str):
        self.operator = operator.lower()
        self.name = self.operator  # <- FALTAVA. O pipeline usa driver.name
        self.mapping = None
        self.mapping_path = os.path.join(MAPPINGS_DIR, f"{self.operator}.json")  # nomes em minúsculo

        if os.path.exists(self.mapping_path):
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    self.mapping = json.load(f)
            except Exception as e:
                print(f"[{self.operator}] erro ao carregar mapping: {e}")
        else:
            print(f"[{self.operator}] mapping não encontrado em {self.mapping_path}")

    def _load_mapping(self):
        """Permite reload sem recriar a instância."""
        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                self.mapping = json.load(f)
        except Exception as e:
            self.mapping = None
            print(f"[{self.operator}] erro no reload do mapping: {e}")

    async def consult(self, identifier: str, id_type: str) -> DriverResult:
        # throttle + retries genéricos
        for attempt in range(MAX_RETRIES):
            try:
                await asyncio.sleep(random.uniform(FETCH_MIN_DELAY, FETCH_MAX_DELAY))
                return await self._perform(identifier, id_type)
            except Exception as e:
                if attempt + 1 == MAX_RETRIES:
                    return DriverResult(
                        operator=self.operator,
                        status="erro",
                        plan="",
                        message=str(e),
                    )
                await asyncio.sleep(1.25)
        # nunca cai aqui, mas deixa o retorno defensivo
        return DriverResult(operator=self.operator, status="erro", message="falha após retries")

    async def _perform(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        """
        Implementação base:
        - Se houver 'steps' no mapping, executa o fluxo declarativo.
        - Senão, tenta legado via selectors.cpf / selectors.submit.
        """
        if not self.mapping:
            raise Exception("mapping ausente para este driver")

        if "steps" in self.mapping:
            return await self._execute_steps(identifier, page=page)

        # Legado
        sel = (self.mapping or {}).get("selectors", {})
        if not sel.get("cpf") or not sel.get("submit"):
            raise Exception("mapping incompleto: selectors.cpf/submit ausentes")

        async def _run(page_obj):
            await page_obj.goto(self.mapping["url"])
            await page_obj.fill(sel["cpf"], identifier)
            await page_obj.click(sel["submit"])
            await asyncio.sleep(2)

        if page is not None:
            await _run(page)
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page_obj = await browser.new_page()
                try:
                    await _run(page_obj)
                finally:
                    await browser.close()

        return DriverResult(operator=self.operator, status="indefinido", message="driver legado executado")

    @asynccontextmanager
    async def _persistent_browser(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                yield page
            finally:
                await browser.close()

    async def _execute_steps(
        self,
        identifier: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        if page is not None:
            return await self._execute_steps_on_page(page, identifier)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page_obj = await browser.new_page()
            try:
                return await self._execute_steps_on_page(page_obj, identifier)
            finally:
                await browser.close()

    async def _execute_steps_on_page(self, page: Any, identifier: str) -> DriverResult:
        steps = self.mapping.get("steps", [])
        parsing = self.mapping.get("result_parsing", {})
        url = self.mapping.get("url")

        try:
            if url:
                await page.goto(url)

            for step in steps:
                await self._run_step(page, step, identifier)

            status, plan, message = await self._parse_result(page, parsing)
        except Exception as e:
            return DriverResult(operator=self.operator, status="erro", plan="", message=str(e))

        return DriverResult(operator=self.operator, status=status, plan=plan, message=message)

    async def _run_step(self, page: Any, step: Dict[str, Any], identifier: str) -> None:
        action = step.get("action")
        optional = bool(step.get("optional", False))
        post_delay = float(step.get("delay", 0.2)) if step.get("delay", 0.2) else 0.0
        timeout = step.get("timeout_ms", 8000)

        try:
            if action == "navigate":
                target = step.get("target") or self.mapping.get("url")
                if target:
                    await page.goto(target)
                wait_for = step.get("wait_for")
                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=timeout)
            elif action == "fill":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("fill action requer 'selector'")
                val = (step.get("value") or "").replace("{identifier}", identifier)
                await page.fill(selector, val, timeout=timeout)
            elif action == "click":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("click action requer 'selector'")
                await page.click(selector, timeout=timeout)
            elif action == "keypress":
                focus_selector = step.get("selector")
                if focus_selector:
                    await page.focus(focus_selector)
                await page.keyboard.press(step.get("key", "Enter"))
            elif action == "wait_for":
                selector = step.get("selector")
                if not selector:
                    raise ValueError("wait_for action requer 'selector'")
                await page.wait_for_selector(selector, timeout=timeout)
            elif action == "wait_for_state":
                await page.wait_for_load_state(step.get("state", "load"))
            elif action == "sleep":
                post_delay = float(step.get("seconds", 0.0))
            else:
                raise ValueError(f"ação desconhecida: {action}")
        except Exception as e:
            if optional:
                print(f"[{self.operator}] passo opcional '{action}' ignorado: {e}")
            else:
                raise
        finally:
            if post_delay:
                await asyncio.sleep(post_delay)

    async def _parse_result(self, page: Any, parsing: Dict[str, Any]) -> Tuple[str, str, str]:
        status_selector = parsing.get("status_selector")
        if not status_selector:
            return "erro", "", "status_selector ausente"

        try:
            raw_text = (await page.inner_text(status_selector)).strip()
        except Exception:
            raw_text = ""

        print(
            f"[{self.operator}] texto capturado em '{status_selector}': {raw_text[:200]}"
        )

        lowered = raw_text.lower()
        pos = [s.lower() for s in parsing.get("positive_keywords", [])]
        neg = [s.lower() for s in parsing.get("negative_keywords", [])]
        err = [s.lower() for s in parsing.get("error_keywords", [])]

        if lowered and any(k in lowered for k in pos):
            status = "ativo"
        elif lowered and any(k in lowered for k in neg):
            status = "inativo"
        elif lowered and any(k in lowered for k in err):
            status = "erro"
        else:
            status = "indefinido"

        message = raw_text[:300]

        plan = ""
        plan_selector = parsing.get("plan_selector")
        if plan_selector:
            try:
                plan_text = (await page.inner_text(plan_selector)).strip()
                plan = plan_text[:300]
            except Exception as e:
                if not parsing.get("plan_optional", False):
                    print(f"[{self.operator}] falha ao capturar plano em '{plan_selector}': {e}")
        if not plan and status == "ativo" and message:
            plan = message

        return status, plan, message
