from .base import BaseDriver

class BradescoDriver(BaseDriver):
    def __init__(self):
        super().__init__("bradesco", supported_id_types=("cpf",))
