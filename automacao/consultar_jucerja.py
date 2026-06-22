# -*- coding: utf-8 -*-
import unicodedata
from playwright.sync_api import sync_playwright

URL_LOGIN = "https://www.jucerja.rj.gov.br/Conta/Entrar?returnUrl=%2FServicos%2FProtocolo%2FTermoUtilizacaoProtocolo"
URL_CONSULTA = "https://www.jucerja.rj.gov.br/Servicos/Protocolo/ProtocoloConsultas"

def _norm(txt):
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.upper().strip()

def classificar_status_rj(status_texto):
    s = _norm(status_texto)
    deferido = ["DEFERIDO", "AUTENTICADO E DISPONIVEL PARA CADASTRO", "FINALIZADO"]
    exigencia = ["EM EXIGENCIA", "CUMPRINDO EXIGENCIA"]
    for d in deferido:
        if d in s:
            return "deferido"
    for e in exigencia:
        if e in s:
            return "exigencia"
    return "tramitacao"

def consultar_jucerja(protocolo, usuario, senha, headless=True):
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=headless)
        pagina = navegador.new_page()
        try:
            pagina.goto(URL_LOGIN, timeout=60000)
            pagina.wait_for_timeout(2000)
            pagina.fill("#campoUsuario", usuario)
            pagina.fill("#campoSenhaUsuario", senha)
            try:
                with pagina.expect_navigation(timeout=15000):
                    pagina.eval_on_selector("#campoSenhaUsuario", "el => el.form.submit()")
            except: pass
            pagina.wait_for_timeout(2500)

            if "Termo" in pagina.url:
                pagina.eval_on_selector("#ConcordoComTermo", "el => { el.checked = true; el.dispatchEvent(new Event('change',{bubbles:true})); }")
                pagina.wait_for_timeout(500)
                try:
                    with pagina.expect_navigation(timeout=15000):
                        pagina.click("#btnConfirmarTermoUtilizacao")
                except: pass
                pagina.wait_for_timeout(2000)

            pagina.goto(URL_CONSULTA, timeout=60000)
            pagina.wait_for_timeout(2500)
            campo = "#Prow-Consultas-ProtocoloNumero-field"
            pagina.click(campo)
            pagina.type(campo, protocolo, delay=120)
            pagina.wait_for_timeout(500)
            pagina.click("#Prow-Consultas-PesquisarProtocolos-Btn")

            # espera a tabela de resultado aparecer (chave do sucesso)
            try:
                pagina.wait_for_selector("tbody tr", timeout=15000)
            except:
                return {"erro": "tabela de resultado nao apareceu"}
            pagina.wait_for_timeout(1500)

            linhas = pagina.query_selector_all("tbody tr")
            proto_norm = protocolo.replace(" ", "")
            for ln in linhas:
                if not ln.is_visible():
                    continue
                celulas = [c.inner_text().strip() for c in ln.query_selector_all("td")]
                if len(celulas) >= 3 and proto_norm in celulas[0].replace(" ", ""):
                    status_texto = celulas[2]
                    return {"status_texto": status_texto, "classificacao": classificar_status_rj(status_texto)}
            return {"erro": "protocolo nao encontrado no resultado"}
        except Exception as e:
            return {"erro": str(e)[:120]}
        finally:
            navegador.close()

if __name__ == "__main__":
    USUARIO = "certificado@realpublicidade.com.br"
    SENHA = "Real2544"
    PROTOCOLO = "2026/00692268-3"
    print("Consultando JUCERJA...")
    r = consultar_jucerja(PROTOCOLO, USUARIO, SENHA, headless=False)
    print("\nRESULTADO:", r)
