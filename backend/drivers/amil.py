import asyncio
import os
from typing import Any, Optional

from .base import BaseDriver, DriverResult, BlockedRequestError


class AmilDriver(BaseDriver):
    """Driver para Amil com validaÃ§Ã£o do campo CPF apÃ³s renderizaÃ§Ã£o completa da SPA."""

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
            self.step("Carregando shell principal e injetando hash do formulÃ¡rio")

            current_url = getattr(page_obj, "url", "") or ""
            current_url_lower = current_url.lower()

            if "amil.com.br" in current_url_lower:
                print("[DEBUG] Iniciando teste de renderizaÃ§Ã£o Amil (modo manual detectado)")
                if "rede-credenciada/amil" not in current_url_lower:
                    print("[INFO] Tentando ajustar hash local sem recarregar pÃ¡gina...")
                    try:
                        await page_obj.evaluate(
                            "if (!window.location.hash.includes('rede-credenciada/amil')) "
                            "window.location.hash = '#/servicos/saude/rede-credenciada/amil/busca-avancada';"
                        )
                    except Exception as exc:
                        print(f"[WARN] Falha ao ajustar hash automaticamente: {exc}")
                await asyncio.sleep(5)
                print("[DEBUG] PÃ¡gina pronta, iniciando varredura do DOM.")
            else:
                if current_url:
                    print("[WARN] PÃ¡gina nÃ£o estÃ¡ na Amil â€” abortando execuÃ§Ã£o.")
                    raise Exception(
                        "PÃ¡gina incorreta: abra manualmente a busca Amil antes de executar."
                    )
                print("[DEBUG] Iniciando teste de renderizaÃ§Ã£o Amil (modo automÃ¡tico)")
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
                "[DEBUG] Texto visÃ­vel (primeiros 300 chars):",
                text_snapshot[:300],
            )
            os.makedirs("debug", exist_ok=True)
            await page_obj.screenshot(path="debug/amil_debug.png", full_page=True)
            print("[DEBUG] Screenshot salva em debug/amil_debug.png")

            self.step("Lendo texto renderizado no corpo da pÃ¡gina")
            page_text = await page_obj.evaluate("() => document.body.innerText || ''")

            if (
                "BeneficiÃ¡rio ou CPF" not in page_text
                and "Beneficiario ou CPF" not in page_text
            ):
                raise Exception(
                    "Texto 'BeneficiÃ¡rio ou CPF' nÃ£o encontrado na tela (SPA possivelmente nÃ£o renderizou)."
                )

            self.step("Buscando input associado ao texto encontrado")
            cpf_input = None

            cpf_locator = page_obj.locator(
                "section:has-text('Passo 1') input[placeholder*='Beneficiário'], "
                "div[class*='step']:has-text('Nº do Beneficiário') input[placeholder*='Beneficiário'], "
                "div[class*='step']:has-text('Selecione o plano ou rede') input[placeholder*='Beneficiário']"
            )
            try:
                if await cpf_locator.count():
                    candidate = await cpf_locator.nth(0).element_handle()
                    if candidate:
                        tag_name = await candidate.evaluate("(el) => el.tagName?.toLowerCase?.() or ''")
                        if tag_name == 'input':
                            cpf_input = candidate
            except Exception:
                cpf_input = None

            if cpf_input is None:
                candidate = await page_obj.query_selector(
                    "form input[type='text'][placeholder*='Beneficiário']"
                )
                if candidate:
                    placeholder_check = (await candidate.get_attribute("placeholder") or "").lower()
                    is_visible = await page_obj.evaluate("(el) => el and el.offsetParent is not None", candidate)
                    if is_visible and ('beneficiário' in placeholder_check or 'beneficiario' in placeholder_check or 'cpf' in placeholder_check):
                        cpf_input = candidate

            if cpf_input is None:
                cpf_input_handle = await page_obj.evaluate_handle(
                    """
                    () => {
                        const candidates = Array.from(document.querySelectorAll("input[placeholder*='Beneficiário']"));
                        for (const el of candidates) {
                            if (!el || el.tagName !== 'INPUT') continue;
                            const visible = el.offsetParent !== null;
                            const placeholder = (el.placeholder || '').toLowerCase();
                            const withinMain = !!el.closest('main, section, div[class*\"step\"]');
                            if (visible && withinMain && (placeholder.includes('beneficiário') || placeholder.includes('beneficiario') || placeholder.includes('cpf'))) {
                                return el;
                            }
                        }
                        return null;
                    }
                    """
                )
                if cpf_input_handle:
                    cpf_input = cpf_input_handle.as_element()

            if cpf_input is None:
                raise Exception("Campo 'Nº do Beneficiário ou CPF' não encontrado ou inválido.")

            placeholder = (await cpf_input.get_attribute("placeholder") or "")
            if 'beneficiário' not in placeholder and 'Beneficiário' not in placeholder and 'CPF' not in placeholder:
                raise Exception("Elemento identificado não corresponde ao campo de CPF do formulário.")

            self.step(f"Campo CPF localizado (placeholder={placeholder}), preenchendo valor.")
            await cpf_input.click()
            await cpf_input.fill(identifier)

            self.step("Pressionando ENTER")
            await page_obj.keyboard.press("Enter")

            self.step("Aguardando resultado da consulta")
            await asyncio.sleep(3)

            self.step("Capturando screenshot de verificaÃ§Ã£o de layout")
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
