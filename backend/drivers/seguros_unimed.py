from .base import BaseDriver

class SegurosUnimedDriver(BaseDriver):
    """Driver para Seguros Unimed, usando o mapping docs/mappings/seguros_unimed.json"""
    def __init__(self):
        super().__init__("seguros_unimed", supported_id_types=("cpf",))
