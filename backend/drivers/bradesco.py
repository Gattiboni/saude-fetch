from .base import BaseDriver

class BradescoDriver(BaseDriver):
    """Driver para Bradesco, usando o mapping docs/mappings/bradesco.json"""
    def __init__(self):
        super().__init__(operator="bradesco", supported_id_types=("cpf",))
