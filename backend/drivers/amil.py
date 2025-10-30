import asyncio
import os
from typing import Any, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base import BaseDriver, DriverResult, BlockedRequestError


class AmilDriver(BaseDriver):
    """Driver para Amil com validação do campo CPF após renderização completa da SPA."""

    def __init__(self) -> None:
        super().__init__("amil", supported_id_types=("cpf",))

    async def _perform(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        async def _run(page_obj: Any) -> DriverResult:
            url = ((self.mapping or {}).get("navigate") or {}).get("url")
            if url:
                self.step("Navegando para página da Amil")
                await page_obj.goto(
                    url,
                    wait_until="networkidle",
                )

            self.step("Aguardando React montar o conteúdo visual da página")
            await page_obj.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

            self.step("Lendo texto renderizado no corpo da página")
            page_text = await page_obj.evaluate("() => document.body.innerText")

            if "Beneficiário ou CPF" not in page_text:
                raise Exception(
                    "Texto 'Beneficiário ou CPF' não encontrado na tela (SPA possivelmente não renderizou)."
                )

            self.step("Buscando input associado ao texto encontrado")
            cpf_input = await page_obj.query_selector(
                "input[placeholder*='Beneficiário'], input[name='cpf'], input[type='text']"
            )
            if cpf_input is None:
                cpf_input_handle = await page_obj.evaluate_handle(
                    """
                    () => {
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        while (walker.nextNode()) {
                            if (walker.currentNode.textContent.includes('Beneficiário')) {
                                let el = walker.currentNode.parentElement;
                                for (let i = 0; i < 5; i++) {
                                    el = el?.nextElementSibling || el?.parentElement?.querySelector('input');
                                    if (el && el.tagName === 'INPUT') return el;
                                }
                            }
                        }
                        return null;
                    }
                    """
                )
                if cpf_input_handle is None:
                    raise Exception("Input de CPF não encontrado mesmo após varredura de texto.")
                cpf_input = cpf_input_handle.as_element()
                if cpf_input is None:
                    raise Exception("Handle retornado não é um elemento de input.")

            placeholder = await cpf_input.get_attribute("placeholder") or ""
            self.step(
                f"Campo CPF localizado visualmente (placeholder={placeholder or 'desconhecido'}), preenchendo valor"
            )
            if hasattr(cpf_input, "fill"):
                await cpf_input.fill(identifier)
            else:
                await page_obj.fill("input[type='text']", identifier)

            self.step("Pressionando ENTER")
            await page_obj.keyboard.press("Enter")

            self.step("Aguardando resultado da consulta")
            await asyncio.sleep(3)

            self.step("Capturando screenshot de verificação de layout")
            os.makedirs("debug", exist_ok=True)
            await page_obj.screenshot(path=f"debug/amil_{identifier}.png")

            parsing = (self.mapping or {}).get("result_parsing", {})
            if parsing:
                status, plan, message, debug = await self._parse_result(page_obj, parsing)
            else:
                status, plan, message, debug = "indefinido", "", "", {}
            debug.setdefault("steps_extra", True)

            self.step(
                f"Resultado final: status={status} | plano={plan or '-'} | mensagem={message or '-'}"
            )
            return DriverResult(
                operator=self.operator,
                status=status,
                plan=plan,
                message=message,
                debug=debug,
                identifier=identifier,
                id_type=id_type,
            )

        if page is not None:
            try:
                return await _run(page)
            except BlockedRequestError:
                raise
            except Exception as error:
                self.log_exception(error)
                raise

        async with self._persistent_browser() as page_obj:
            try:
                return await _run(page_obj)
            except BlockedRequestError:
                raise
            except Exception as error:
                self.log_exception(error)
                raise
