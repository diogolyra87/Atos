# -*- coding: utf-8 -*-
import unicodedata
import re
from playwright.sync_api import sync_playwright

def _formatar_protocolo_jucerja(protocolo):
    """Normaliza o numero de protocolo para o formato YYYY/NNNNNNNN-N exigido
    pelo campo de busca da JUCERJA, independente de como esta salvo no banco
    (com ou sem barra/traco)."""
    digitos = re.sub(r"\D", "", protocolo or "")
    if len(digitos) == 13:
        return digitos[:4] + "/" + digitos[4:12] + "-" + digitos[12]
    return protocolo

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
    protocolo = _formatar_protocolo_jucerja(protocolo)
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

def baixar_documento_jucerja(protocolo, usuario, senha, destino_path, headless=True):
    protocolo = _formatar_protocolo_jucerja(protocolo)
    """Loga na JUCERJA, busca o protocolo, e se estiver DEFERIDO/FINALIZADO baixa
    o Documento Digital (.p7s), extrai o PDF real de dentro do envelope PKCS#7
    via openssl, e salva o PDF final em destino_path. Retorna True/False."""
    import subprocess, tempfile, os
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=headless)
        ctx = navegador.new_context(accept_downloads=True)
        pagina = ctx.new_page()
        try:
            pagina.goto(URL_LOGIN, timeout=60000)
            pagina.wait_for_timeout(2000)
            pagina.fill("#campoUsuario", usuario)
            pagina.fill("#campoSenhaUsuario", senha)
            try:
                with pagina.expect_navigation(timeout=15000):
                    pagina.eval_on_selector("#campoSenhaUsuario", "el => el.form.submit()")
            except Exception:
                pass
            pagina.wait_for_timeout(2500)

            if "Termo" in pagina.url:
                pagina.eval_on_selector("#ConcordoComTermo", "el => { el.checked = true; el.dispatchEvent(new Event('change',{bubbles:true})); }")
                pagina.wait_for_timeout(500)
                try:
                    with pagina.expect_navigation(timeout=15000):
                        pagina.click("#btnConfirmarTermoUtilizacao")
                except Exception:
                    pass
                pagina.wait_for_timeout(2000)

            pagina.goto(URL_CONSULTA, timeout=60000)
            pagina.wait_for_timeout(2500)
            campo = "#Prow-Consultas-ProtocoloNumero-field"
            pagina.click(campo)
            pagina.type(campo, protocolo, delay=120)
            pagina.wait_for_timeout(500)
            pagina.click("#Prow-Consultas-PesquisarProtocolos-Btn")
            pagina.wait_for_selector("tbody tr", timeout=15000)
            pagina.wait_for_timeout(1500)

            linhas = pagina.query_selector_all("tbody tr")
            proto_norm = protocolo.replace(" ", "")
            linha_ok = None
            status_texto = None
            for ln in linhas:
                if not ln.is_visible():
                    continue
                celulas = [c.inner_text().strip() for c in ln.query_selector_all("td")]
                if len(celulas) >= 3 and proto_norm in celulas[0].replace(" ", ""):
                    linha_ok = ln
                    status_texto = celulas[2]
                    break

            if not linha_ok:
                return False
            if classificar_status_rj(status_texto) != "deferido":
                return False

            linha_ok.click()
            pagina.wait_for_timeout(2000)

            botao_doc = pagina.query_selector("#Prow-Consultas-DocDigital-Btn")
            if not botao_doc:
                return False

            try:
                with pagina.expect_navigation(timeout=15000):
                    botao_doc.click()
            except Exception:
                pass
            pagina.wait_for_timeout(2000)

            botao_pesquisar = pagina.query_selector("text=Pesquisar")
            if botao_pesquisar:
                botao_pesquisar.click()
                pagina.wait_for_timeout(3000)

            try:
                pagina.wait_for_selector("text=Faça download", timeout=15000)
            except Exception:
                return False

            with tempfile.TemporaryDirectory() as tmpdir:
                caminho_p7s = os.path.join(tmpdir, "documento.p7s")
                try:
                    with pagina.expect_download(timeout=20000) as dl_info:
                        pagina.click("text=Faça download")
                    download = dl_info.value
                    download.save_as(caminho_p7s)
                except Exception as e:
                    print("Erro ao baixar documento JUCERJA:", str(e)[:150])
                    return False

                resultado = subprocess.run(
                    ["openssl", "cms", "-verify", "-noverify", "-inform", "DER",
                     "-in", caminho_p7s, "-out", destino_path],
                    capture_output=True, text=True, timeout=30
                )
                if resultado.returncode != 0:
                    return False
                return os.path.exists(destino_path)
        except Exception as e:
            print("Erro ao baixar documento JUCERJA:", str(e)[:150])
            return False
        finally:
            navegador.close()


if __name__ == "__main__":
    USUARIO = "certificado@realpublicidade.com.br"
    SENHA = "Real2544"
    PROTOCOLO = "2026/00692268-3"
    print("Consultando JUCERJA...")
    r = consultar_jucerja(PROTOCOLO, USUARIO, SENHA, headless=False)
    print("\nRESULTADO:", r)
