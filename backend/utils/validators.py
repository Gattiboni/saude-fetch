import re

CPF_PATTERN = re.compile(r"^\d{11}$")
CNPJ_PATTERN = re.compile(r"^\d{14}$")


def validate_cpf_cnpj(identifier: str) -> bool:
    if not identifier:
        return False
    digits = re.sub(r"\D", "", identifier)
    return bool(CPF_PATTERN.fullmatch(digits) or CNPJ_PATTERN.fullmatch(digits))
