import asyncio
import os
from typing import Any, Optional

from .base import BaseDriver, DriverResult, BlockedRequestError


class AmilDriver(BaseDriver):
    """Driver para Amil com validação do campo CPF após renderização completa da SPA."""

    def __init__(self) -> None:
        super().__init__("amil", supported_id_types=("cpf",))

    async def consult(
        self,
        identifier: str,
        id_type: str,
        *,
        page: Optional[Any] = None,
    ) -> DriverResult:
        if page is None:
            return await super().consult(identifier, id_type, page=page)
        return await self._perform(identifier, id_type, page=page)

    async def _perform(
        self,
        identifier: str,
        id_type: str,
        page: Optional[Any] = None,
    ) -> DriverResult:
        async def _run(page_obj: Any) -> DriverResult:
            self.step("Carregando shell principal e injetando hash do formulário")

            current_url = getattr(page_obj, "url", "") or ""
            current_url_lower = current_url.lower()

            if "amil.com.br" in current_url_lower:
                print("[DEBUG] Iniciando teste de renderização Amil (modo manual detectado)")
                if "rede-credenciada/amil" not in current_url_lower:
                    print("[INFO] Tentando ajustar hash local sem recarregar página...")
                    try:
                        await page_obj.evaluate(
                            "if (!window.location.hash.includes('rede-credenciada/amil')) "
                            "window.location.hash = '#/servicos/saude/rede-credenciada/amil/busca-avancada';"
                        )
                    except Exception as exc:
                        print(f"[WARN] Falha ao ajustar hash automaticamente: {exc}")
                await asyncio.sleep(5)
                print("[DEBUG] Página pronta, iniciando varredura do DOM.")
            else:
                if current_url:
                    print("[WARN] Página não está na Amil — abortando execução.")
                    raise Exception(
                        "Página incorreta: abra manualmente a busca Amil antes de executar."
                    )
                print("[DEBUG] Iniciando teste de renderização Amil (modo automático)")
                await page_obj.goto(
                    "https://www.amil.com.br/institucional/",
                    wait_until="commit",
                )
                await asyncio.sleep(12)
                await page_obj.evaluate(
                    "window.location.hash = '#/servicos/saude/rede-credenciada/amil/busca-avancada'"
                )
                await asyncio.sleep(12)

            html = await page_obj.content()
            print("[DEBUG] Tamanho do HTML renderizado:", len(html))
            text_snapshot = await page_obj.inner_text("body")
            print(
                "[DEBUG] Texto visível (primeiros 300 chars):",
                text_snapshot[:300],
            )
            os.makedirs("debug", exist_ok=True)
            await page_obj.screenshot(path="debug/amil_debug.png", full_page=True)
            print("[DEBUG] Screenshot salva em debug/amil_debug.png")

            self.step("Lendo texto renderizado no corpo da página")
            page_text = await page_obj.evaluate("() => document.body.innerText || ''")

            if (
                "Beneficiário ou CPF" not in page_text
                and "Beneficiario ou CPF" not in page_text
            ):
                raise Exception(
                    "Texto 'Beneficiário ou CPF' não encontrado na tela (SPA possivelmente não renderizou)."
                )

            self.step("Buscando input associado ao texto encontrado")

            cpf_locator = page_obj.locator(
                "section:has-text('Passo 1') input[placeholder*='Beneficiário'], "
                "div[class*='step']:has-text('Selecione o plano ou rede') input[placeholder*='Beneficiário']"
            )
            cpf_input = None
            try:
                if await cpf_locator.count():
                    cpf_input = await cpf_locator.nth(0).element_handle()
            except Exception:
                cpf_input = None

            if cpf_input is None:
                cpf_input = await page_obj.query_selector(
                    "form input[placeholder*='Beneficiário'][type='text']"
                )

            if cpf_input is None:
                cpf_input_handle = await page_obj.evaluate_handle(
                    """
                    () => {
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        while (walker.nextNode()) {
                            const txt = walker.currentNode.textContent || '';
                            if (txt.includes('Beneficiário') || txt.includes('Beneficiario')) {
                                let scope = walker.currentNode.parentElement;
                                const container =
                                    scope?.closest('section') ||
                                    scope?.closest(\"div[class*='step']\") ||
                                    scope;
                                if (container) {
                                    const candidate = container.querySelector(\"input[placeholder*='Beneficiário']\");
                                    if (candidate && candidate.tagName === 'INPUT') {
                                        return candidate;
                                    }
                                }
                            }
                        }
                        return null;
                    }
                    """
                )
                if cpf_input_handle is None:
                    raise Exception("Campo 'Nº do Beneficiário ou CPF' não encontrado no formulário principal.")
                cpf_input = cpf_input_handle.as_element()
                if cpf_input is None:
                    raise Exception("Handle retornado não é um elemento de input válido.")

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
