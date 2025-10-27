from .base import BaseDriver, DriverResult

class SulamericaDriver(BaseDriver):
    name = "sulamerica"
    requires_auth = True

    async def _perform(self, identifier: str, id_type: str) -> DriverResult:
        # Nesta fase, login inativo: apenas sinalizar pendência
        return DriverResult(operator=self.name, status="pending", plan="", message="login requerido (inativo nesta fase)")
