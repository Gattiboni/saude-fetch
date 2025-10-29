from .base import BaseDriver

class UnimedDriver(BaseDriver):
    def __init__(self):
        super().__init__("unimed", supported_id_types=("cpf",))
