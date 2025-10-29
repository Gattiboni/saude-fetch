from .base import BaseDriver

class SegurosUnimedDriver(BaseDriver):
    def __init__(self):
        super().__init__("seguros_unimed", supported_id_types=("cpf",))
