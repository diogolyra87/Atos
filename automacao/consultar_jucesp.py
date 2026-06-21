import sys
import unicodedata
from playwright.sync_api import sync_playwright

URL = "https://www.jucesp.sp.gov.br/vre/Consulta/ConsultaAndamento.aspx"

def sem_acento(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper()

def classificar(andamento, despacho):
    junto = sem_acento(andamento) + " " + sem_acento(despacho)

    # 1) Exigencia tem prioridade
    if "EXIGENCIA" in junto:
        return "EXIGENCIA"

    # 2) Deferido (varias formas de aparecer na JUCESP)
    chaves_deferido = [
        "DEFERIDO",
        "CERTIDAO DE INTEIRO TEOR",
        "DISPONIBILIZADA PARA EMISSAO",
        "ACESSIVEL POR 30 DIAS",
    ]
    for ch in chaves_deferido:
        if ch in junto:
            return "DEFERIDO"

    # 3) Caso normal: devolve o andamento literal
    return andamento or None

def consultar(protocolo, mostrar_navegador=False):
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=not mostrar_navegador)
        pagina = navegador.new_page()
        pagina.goto(URL, timeout=60000)
        pagina.wait_for_timeout(1500)
        pagina.fill("#txtProtocolo_txt", protocolo)
        pagina.click("#btnPesquisar")
        pagina.wait_for_timeout(4000)

        def pegar(seletor):
            el = pagina.query_selector(seletor)
            return (el.inner_text() or "").strip() if el else ""

        andamento = pegar("#lblDadosDoUltimoArquivamento")
        despacho = pegar("#lblDadosDoDespacho")
        navegador.close()
        return classificar(andamento, despacho)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prot = sys.argv[1]
    else:
        prot = input("Digite o protocolo: ").strip()
    resultado = consultar(prot)
    print()
    if resultado:
        print(f"Dados do Último Andamento: {resultado}")
    else:
        print("Nao foi possivel obter o andamento.")
