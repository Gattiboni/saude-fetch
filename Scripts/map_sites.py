import os
import json
import time
import logging
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==================== CONFIG ====================
SITES = {
    "unimed": "https://www.unimed.coop.br/site/guia-medico#/",
    "amil": "https://www.amil.com.br/institucional/#/servicos/saude/rede-credenciada/amil/busca-avancada",
    "bradesco": "https://www.bradescoseguros.com.br/clientes/produtos/plano-saude/consulta-de-rede-referenciada",
    "seguros_unimed": "https://www.segurosunimed.com.br/guia-medico/",
    "sulamerica": "https://os11.sulamerica.com.br/SaudeCotador/LoginVendedor.aspx",
}

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "mappings"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADLESS = True
TIMEOUT = 30  # segundos

# Credenciais SulAmérica (não armazenar em produção)
SULA_USER = "leonardofarinazzo.ygg@gmail.com"
SULA_PASS = "Odisseia1!"
SULA_CODIGO = "03077390"

# ==================== LOGGING ====================
log_path = os.path.join(OUTPUT_DIR, "mapper_selenium.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ==================== HELPERS ====================

def snapshot_page(driver, site_key, stage="dynamic"):
    html = driver.page_source
    path = os.path.join(OUTPUT_DIR, f"{site_key}_{stage}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    logging.info(f"Snapshot salvo: {path}")
    return path

def map_elements(driver):
    elements = {"inputs": [], "buttons": [], "labels": []}
    try:
        inputs = driver.find_elements("tag name", "input")
        for el in inputs:
            info = {
                "type": el.get_attribute("type"),
                "id": el.get_attribute("id"),
                "name": el.get_attribute("name"),
                "class": el.get_attribute("class"),
                "placeholder": el.get_attribute("placeholder"),
                "aria_label": el.get_attribute("aria-label"),
            }
            elements["inputs"].append(info)

        buttons = driver.find_elements("xpath", "//button | //*[@role='button']")
        for el in buttons:
            info = {
                "text": (el.text or "").strip(),
                "id": el.get_attribute("id"),
                "class": el.get_attribute("class"),
                "role": el.get_attribute("role"),
            }
            elements["buttons"].append(info)

        labels = driver.find_elements("xpath", "//label | //span | //div | //p | //b | //strong")
        for el in labels:
            txt = (el.text or "").strip()
            if not txt:
                continue
            if any(k in txt.lower() for k in ["cpf", "cnpj", "unimed", "amil", "plano", "categoria"]):
                elements["labels"].append({"text": txt[:200]})

    except Exception as e:
        logging.error(f"Erro ao mapear elementos: {e}")
    return elements

def map_site(site_key, url, driver):
    try:
        logging.info(f"Iniciando mapeamento: {site_key}")
        driver.get(url)
        time.sleep(5)

        # Caso especial: login SulAmérica
        if site_key == "sulamerica":
            try:
                driver.find_element("name", "txtCpf").send_keys("138.213.517-30")
                driver.find_element("name", "txtEmail").send_keys(SULA_USER)
                driver.find_element("name", "txtSenha").send_keys(SULA_PASS)
                driver.find_element("id", "btnEntrar").click()
                time.sleep(3)
                cod_input = driver.find_elements("name", "txtCodCorretor")
                if cod_input:
                    cod_input[0].send_keys(SULA_CODIGO)
                    cod_input[0].submit()
                    time.sleep(4)
            except Exception as e:
                logging.warning(f"Falha ao autenticar SulAmérica: {e}")

        dynamic_path = snapshot_page(driver, site_key, stage="dynamic")
        mapped = map_elements(driver)

        result = {
            "site": site_key,
            "url": url,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "dynamic_snapshot_path": dynamic_path,
            "elements": mapped,
        }

        json_path = os.path.join(OUTPUT_DIR, f"{site_key}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logging.info(f"Mapeamento concluído: {site_key}")

    except Exception as e:
        logging.error(f"Erro no site {site_key}: {e}")

# ==================== MAIN ====================

def main():
    logging.info("==== Início do mapeamento (Selenium) ====")

    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(TIMEOUT)

    for key, url in SITES.items():
        map_site(key, url, driver)

    driver.quit()
    logging.info("==== Mapeamento concluído (Selenium) ====")

if __name__ == "__main__":
    main()