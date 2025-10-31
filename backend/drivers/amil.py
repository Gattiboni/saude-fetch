# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from typing import Any, Dict, Optional

from .base import BaseDriver, DriverResult, BlockedRequestError


logger = logging.getLogger(__name__)


class AmilDriver(BaseDriver):
    """Driver para Amil com validacao do campo CPF apos renderizacao completa da SPA."""

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
            self.step("Carregando shell principal e injetando hash do formulario")

            current_url = getattr(page_obj, "url", "") or ""
            current_url_lower = current_url.lower()

            if "amil.com.br" in current_url_lower:
                print("[DEBUG] Iniciando teste de renderizacao Amil (modo manual detectado)")
                if "rede-credenciada/amil" not in current_url_lower:
                    print("[INFO] Tentando ajustar hash local sem recarregar pagina...")
                    try:
                        await page_obj.evaluate(
                            "if (!window.location.hash.includes('rede-credenciada/amil')) "
                            "window.location.hash = '#/servicos/saude/rede-credenciada/amil/busca-avancada';"
                        )
                    except Exception as exc:
                        print(f"[WARN] Falha ao ajustar hash automaticamente: {exc}")
                await asyncio.sleep(5)
                print("[DEBUG] Pagina pronta, iniciando varredura do DOM.")
            else:
                if current_url:
                    print("[WARN] Pagina nao esta na Amil a abortando execucao.")
                    raise Exception(
                        "Pagina incorreta: abra manualmente a busca Amil antes de executar."
                    )
                print("[DEBUG] Iniciando teste de renderizacao Amil (modo automatico)")
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
                "[DEBUG] Texto visivel (primeiros 300 chars):",
                text_snapshot[:300],
            )
            os.makedirs("debug", exist_ok=True)
            await page_obj.screenshot(path="debug/amil_debug.png", full_page=True)
            print("[DEBUG] Screenshot salva em debug/amil_debug.png")

            raw_html = await page_obj.content()

            try:
                normalized_html = raw_html.encode("latin1").decode("utf-8", errors="ignore")
            except Exception:
                normalized_html = raw_html

            visible_text = await page_obj.inner_text("body")
            visible_text_norm = visible_text.lower()

            self.step("Varredura textual apos normalizacao concluida.")

            if "beneficiario" not in visible_text_norm:
                raise Exception("Texto 'Beneficiario ou CPF' nao encontrado - possivel mismatch de encoding.")

            self.step("Texto 'Beneficiario ou CPF' localizado com sucesso (encoding normalizado).")

            self.step("Buscando input associado ao texto encontrado")
            cpf_input = None

            cpf_input = await page_obj.query_selector("#cpf_input")

            if cpf_input is None:
                cpf_input = await page_obj.query_selector(
                    "input[placeholder*='Beneficiario'], input[placeholder*='Beneficiario']"
                )

            if cpf_input is None:
                cpf_input_handle = await page_obj.evaluate_handle(
                    """
                    () => {
                        const all = Array.from(document.querySelectorAll('input'));
                        for (const el of all) {
                            if (!el) continue;
                            const placeholder = (el.getAttribute('placeholder') || '')
                                .normalize('NFD')
                                .replace(/[-]/g, '');
                            const label = (el.getAttribute('label') || '')
                                .normalize('NFD')
                                .replace(/[-]/g, '');
                            const visible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                            if (visible && (placeholder.includes('Beneficiario') || label.includes('Beneficiario'))) {
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
                raise Exception("Campo 'No do Beneficiario ou CPF' nao encontrado.")

            tag_name = await cpf_input.evaluate("(el) => el.tagName.toLowerCase()")
            if tag_name != "input":
                raise Exception("Elemento localizado nao e um campo de input.")

            placeholder = await cpf_input.get_attribute("placeholder") or ""
            self.step(f"Campo CPF localizado (placeholder={placeholder}), preenchendo valor.")
            await cpf_input.click()
            await cpf_input.fill(identifier)

            self.step("Pressionando ENTER")
            await page_obj.keyboard.press("Enter")
            self.step("Aguardando resultado da consulta")

            debug_info: Dict[str, Any] = {}

            try:
                await page_obj.wait_for_selector("text=Plano ou rede:", timeout=8000)
            except Exception:
                logger.debug("[amil] Timeout aguardando campo 'Plano ou rede', tentando detectar modal.")
                debug_info["wait_timeout"] = True

            try:
                aviso_modal = await page_obj.query_selector("text='Aviso'")
                if aviso_modal:
                    texto_modal = await page_obj.text_content("text='Nenhum resultado encontrado.'")
                    if texto_modal:
                        logger.debug("[amil] Resultado negativo detectado via modal.")
                        self.step("Resultado negativo detectado via modal da Amil.")
                        debug_info["status_source"] = "modal"
                        return DriverResult(
                            operator=self.operator,
                            status="negativo",
                            plan="-",
                            message="Nenhum resultado encontrado.",
                            debug=debug_info,
                            identifier=identifier,
                            id_type=id_type,
                        )
            except Exception as exc:
                logger.debug("[amil] Nenhum modal de aviso encontrado: %s", exc)
                debug_info["modal_error"] = str(exc)

            try:
                value_el = await page_obj.query_selector("div.search-select-redux .rw-input")
                if value_el:
                    plano_nome = (await value_el.text_content() or "").strip()
                    if plano_nome and plano_nome.lower() != "plano ou rede":
                        logger.debug("[amil] Plano detectado: %s", plano_nome)
                        self.step(f"Resultado positivo identificado: {plano_nome}")
                        debug_info["status_source"] = "campo_plano"
                        return DriverResult(
                            operator=self.operator,
                            status="positivo",
                            plan=plano_nome,
                            message="Plano identificado com sucesso.",
                            debug=debug_info,
                            identifier=identifier,
                            id_type=id_type,
                        )
            except Exception as exc:
                logger.debug("[amil] Falha ao capturar nome do plano: %s", exc)
                debug_info["plano_error"] = str(exc)

            logger.debug("[amil] Nenhum status reconhecido: nem modal nem campo de plano renderizado.")
            self.step("Nenhum status reconhecido apos a consulta.")
            debug_info["status_source"] = "indefinido"
            return DriverResult(
                operator=self.operator,
                status="erro",
                plan="-",
                message="status_selector ausente",
                debug=debug_info,
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
