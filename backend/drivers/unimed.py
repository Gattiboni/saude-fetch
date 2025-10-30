from typing import Any, Dict, Tuple

from .base import BaseDriver, normalize_text


class UnimedDriver(BaseDriver):
    """Driver para Unimed, usando o mapping docs/mappings/unimed.json"""
    def __init__(self):
        super().__init__("unimed", supported_id_types=("cpf",))

    async def _parse_result(
        self, page: Any, parsing: Dict[str, Any]
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        status, plan, message, debug = await super()._parse_result(page, parsing)

        needs_probe = status in {"indefinido", "erro"} and not plan
        if not needs_probe:
            return status, plan, message, debug

        probe_timeout = parsing.get("status_timeout_ms") or 0
        fallback_text = await self._scan_for_unimed(page, probe_timeout)
        if fallback_text:
            normalized = normalize_text(fallback_text)
            debug.setdefault("fallback_scan", {})["text"] = fallback_text[:500]
            if "UNIMED" in normalized:
                status = "ativo"
                plan = fallback_text.strip()[:300]
                message = fallback_text.strip()[:300]
        return status, plan, message, debug

    async def _scan_for_unimed(self, page: Any, timeout_ms: int) -> str:
        if timeout_ms <= 0:
            timeout_ms = 20000
        poll_interval = 0.2
        attempts = max(1, int((timeout_ms / 1000) / poll_interval))
        locator_str = (
            "xpath=//*[contains(translate(normalize-space(string(.)), 'unimed', 'UNIMED'),'UNIMED')]"
        )
        locator = page.locator(locator_str)
        for _ in range(attempts):
            try:
                count = await locator.count()
            except Exception:
                count = 0
            for idx in range(count):
                element = locator.nth(idx)
                try:
                    if await element.is_visible():
                        box = await element.bounding_box()
                        if not box:
                            continue
                        text = (await element.inner_text()).strip()
                        if text:
                            print(f"[unimed] elemento encontrado: {text[:200]}")
                            return text
                except Exception:
                    continue
            await page.wait_for_timeout(int(poll_interval * 1000))
        return ""
