from .base import BaseDriver

class UnimedDriver(BaseDriver):
    """Driver para Unimed, usando o mapping docs/mappings/unimed.json"""
    def __init__(self):
        super().__init__(operator="unimed", supported_id_types=("cpf",))
