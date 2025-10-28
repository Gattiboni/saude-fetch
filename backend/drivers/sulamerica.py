from .base import BaseDriver, DriverResult

class SulamericaDriver(BaseDriver):
    def __init__(self):
        super().__init__("sulamerica")

    async def _perform(self, identifier, id_type):
        # placeholder, se o CNPJ ainda é quem usa SulAmérica real
        return DriverResult(
            operator="sulamerica",
            status="pending",
            message="Driver SulAmérica não implementado para CPF."
        )
