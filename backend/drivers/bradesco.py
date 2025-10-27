from .base import BaseDriver, DriverResult

class BradescoDriver(BaseDriver):
    name = "bradesco"
    requires_auth = False

    async def _perform(self, identifier: str, id_type: str) -> DriverResult:
        if not self.mapping:
            return DriverResult(operator=self.name, status="pending", plan="", message="mapeamento pendente")
        # TODO: implementar lógica real baseada no mapping
        return DriverResult(operator=self.name, status="unknown", plan="", message="aguardando automação real")
