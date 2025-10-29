from .base import BaseDriver

class AmilDriver(BaseDriver):
    def __init__(self):
        super().__init__("amil", supported_id_types=("cpf",))
