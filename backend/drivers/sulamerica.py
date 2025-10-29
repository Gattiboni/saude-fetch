from .base import BaseDriver


class SulamericaDriver(BaseDriver):
    def __init__(self):
        super().__init__("sulamerica", supported_id_types=("cnpj",))
