import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from playwright.async_api import async_playwright

FETCH_MIN_DELAY = float(os.getenv("FETCH_MIN_DELAY", "0.5"))
FETCH_MAX_DELAY = float(os.getenv("FETCH_MAX_DELAY", "1.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Usa variável de ambiente ou fallback consistente com teu projeto
MAPPINGS_DIR = os.getenv(
    "MAPPINGS_DIR",
    os.path.join(os.getcwd(), "backend", "docs", "mappings")
)

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

    async def _perform(self, identifier: str, id_type: str) -> DriverResult:
        """
        Implementação base:
        - Se houver 'steps' no mapping, executa o fluxo declarativo.
        - Senão, tenta legado via selectors.cpf / selectors.submit.
        """
        if not self.mapping:
            raise Exception("mapping ausente para este driver")

        if "steps" in self.mapping:
            return await self._execute_steps(identifier)

        # Legado
        sel = (self.mapping or {}).get("selectors", {})
        if not sel.get("cpf") or not sel.get("submit"):
            raise Exception("mapping incompleto: selectors.cpf/submit ausentes")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.mapping["url"])
            await page.fill(sel["cpf"], identifier)
            await page.click(sel["submit"])
            await asyncio.sleep(2)
            await browser.close()

        return DriverResult(operator=self.operator, status="indefinido", message="driver legado executado")

    async def _execute_steps(self, identifier: str) -> DriverResult:
        steps = self.mapping.get("steps", [])
        parsing = self.mapping.get("result_parsing", {})
        url = self.mapping.get("url")

        status = "indefinido"
        plan = ""
        message = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                if url:
                    await page.goto(url)

                for step in steps:
                    action = step.get("action")
                    if action == "navigate":
                        await page.goto(step.get("target"))
                        if step.get("wait_for"):
                            try:
                                await page.wait_for_selector(step["wait_for"], timeout=step.get("timeout_ms", 8000))
                            except Exception:
                                pass
                    elif action == "fill":
                        val = (step.get("value") or "").replace("{identifier}", identifier)
                        await page.fill(step["selector"], val)
                    elif action == "click":
                        await page.click(step["selector"])
                    elif action == "keypress":
                        await page.keyboard.press(step.get("key", "Enter"))
                    elif action == "wait_for":
                        try:
                            await page.wait_for_selector(step["selector"], timeout=step.get("timeout_ms", 8000))
                        except Exception:
                            pass
                    await asyncio.sleep(0.2)

                # parsing
                sel = parsing.get("status_selector")
                if sel:
                    try:
                        text = (await page.inner_text(sel)).strip().lower()
                    except Exception:
                        text = ""

                    pos = [s.lower() for s in parsing.get("positive_keywords", [])]
                    neg = [s.lower() for s in parsing.get("negative_keywords", [])]
                    err = [s.lower() for s in parsing.get("error_keywords", [])]

                    if text and any(k in text for k in pos):
                        status = "ativo"
                    elif text and any(k in text for k in neg):
                        status = "inativo"
                    elif text and any(k in text for k in err):
                        status = "erro"
                    else:
                        status = "indefinido"

                    message = text[:300]
                else:
                    status = "erro"
                    message = "status_selector ausente"

            except Exception as e:
                status = "erro"
                message = str(e)
            finally:
                await browser.close()

        return DriverResult(operator=self.operator, status=status, plan=plan, message=message)
