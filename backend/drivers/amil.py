from .base import BaseDriver

class AmilDriver(BaseDriver):
    """Driver para Amil, usando o mapping docs/mappings/amil.json"""
    def __init__(self):
        super().__init__("amil", supported_id_types=("cpf",))
