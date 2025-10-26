import os
import json
from typing import Tuple

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BASE_DIR, 'docs', 'mappings')
# Fallback para variação de caixa em Windows, se existir 'Docs/mappings'
if not os.path.isdir(MAPPINGS_DIR):
    alt_dir = os.path.join(BASE_DIR, 'Docs', 'mappings')
    if os.path.isdir(alt_dir):
        MAPPINGS_DIR = alt_dir

OUTPUT_FILE = os.path.join(MAPPINGS_DIR, 'mappings_reference.json')

# Lista de operadoras e respectivos arquivos
OPERADORAS = {
    'unimed': 'unimed.json',
    'unimed_seguros': 'unimed seguros.json',
    'amil': 'amil.json',
    'bradesco': 'bradesco.json',
    'sulamerica': 'sulamerica.json'
}

# Regras de sucesso e falha definidas manualmente
REGRAS = {
    'unimed': {
        'success_criteria': 'Retorna dados de plano e cooperativa',
        'failure_criteria': 'Mensagem de CPF inválido'
    },
    'amil': {
        'success_criteria': 'Exibe nome do plano (ex.: OURO)',
        'failure_criteria': 'Modal "não encontrado"'
    },
    'bradesco': {
        'success_criteria': 'Modal "Selecione o beneficiário"',
        'failure_criteria': 'Modal "Beneficiário não encontrado"'
    },
    'unimed_seguros': {
        'success_criteria': 'Exibe informações do plano diretamente',
        'failure_criteria': 'Modal de erro / CPF inválido'
    },
    'sulamerica': {
        'success_criteria': 'Exige login (CNPJ)',
        'failure_criteria': 'Acesso negado sem autenticação'
    }
}

def sniff_format(text: str) -> str:
    sample = text.lstrip()[:16].lower()
    if not sample:
        return 'empty'
    if sample.startswith('{') or sample.startswith('['):
        return 'json'
    if sample.startswith('<!doctype') or sample.startswith('<html') or '<html' in sample:
        return 'html'
    return 'text'


def carregar_arquivo_bruto(path: str) -> Tuple[str, int]:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        data = f.read()
    return data, len(data.encode('utf-8'))


def carregar_json_robusto(operadora: str, arquivo: str) -> Tuple[dict, dict]:
    """
    Retorna uma tupla (conteudo_json, meta_dom)
    - Se o arquivo for JSON válido, retorna o JSON e meta {format: json, size_bytes}
    - Se for HTML ou texto, retorna {} e meta {format: html|text, size_bytes, path}
    - Se estiver vazio, retorna {} e meta {format: empty}
    """
    caminho = os.path.join(MAPPINGS_DIR, arquivo)
    if not os.path.exists(caminho):
        print(f"[Aviso] Arquivo não encontrado para {operadora}: {arquivo}")
        return {}, {"format": "missing", "path": caminho}

    raw, size_b = carregar_arquivo_bruto(caminho)
    kind = sniff_format(raw)

    if kind == 'json':
        try:
            return json.loads(raw), {"format": "json", "size_bytes": size_b, "path": caminho}
        except Exception as e:
            print(f"[Erro] JSON inválido em {arquivo}: {e}")
            # cai para meta básica sem conteúdo
            return {}, {"format": "invalid_json", "size_bytes": size_b, "path": caminho}
    elif kind == 'html':
        print(f"[Info] {arquivo} parece HTML, não JSON. Vou referenciar apenas o caminho.")
        return {}, {"format": "html", "size_bytes": size_b, "path": caminho}
    elif kind == 'empty':
        print(f"[Erro] Arquivo vazio: {arquivo}")
        return {}, {"format": "empty", "size_bytes": size_b, "path": caminho}
    else:
        print(f"[Info] {arquivo} é texto não-JSON. Vou referenciar apenas o caminho.")
        return {}, {"format": "text", "size_bytes": size_b, "path": caminho}


def gerar_mapeamento():
    resultado = {
        "_meta": {
            "mappings_dir": MAPPINGS_DIR,
            "note": "Arquivo gerado a partir de artefatos finais em docs/mappings. Não embute DOM para evitar arquivos gigantes; referencia apenas o caminho e o tamanho.",
        },
        "providers": {}
    }

    for operadora, arquivo in OPERADORAS.items():
        conteudo, meta = carregar_json_robusto(operadora, arquivo)

        resultado["providers"][operadora] = {
            "source_file": arquivo,
            "status": "placeholder" if operadora == 'sulamerica' else "confirmed",
            "success_criteria": REGRAS[operadora]["success_criteria"],
            "failure_criteria": REGRAS[operadora]["failure_criteria"],
            # Não embutimos o DOM inteiro; só repassamos metadados do arquivo
            "dom_snapshot": meta,
            "notes": (
                "Mapeamento manual confirmado." if operadora != 'sulamerica' else
                "Placeholder aguardando credenciais e teste de login."
            ),
        }

        # Se for JSON válido e contiver estrutura 'elements', adiciona indicadores úteis
        if conteudo and isinstance(conteudo, dict):
            elements = conteudo.get('elements')
            if isinstance(elements, dict):
                resultado["providers"][operadora]["elements_count"] = {
                    k: len(v) if isinstance(v, list) else 0 for k, v in elements.items()
                }

    os.makedirs(MAPPINGS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"[OK] Mapeamento consolidado gerado em: {OUTPUT_FILE}")

if __name__ == '__main__':
    gerar_mapeamento()
