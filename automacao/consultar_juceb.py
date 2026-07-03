# -*- coding: utf-8 -*-
import unicodedata
from playwright.sync_api import sync_playwright

URL_LOGIN = "https://regin.juceb.ba.gov.br/RequerimentoUniversal/Principal.aspx"

def _norm(txt):
    if not txt:
        return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.upper().strip()

def classificar_status_ba(status_texto):
    s = _norm(status_texto)
    if "EXIGENCIA" in s:
        return "exigencia"
    if "FINALIZADO" in s or "DEFERIDO" in s:
        return "deferido"
    if "TRAMITACAO" in s:
        return "tramitacao"
    return "tramitacao"

def _fechar_cookie(pg):
    for sel in ["text=Aceito", "button:has-text('Aceito')", "#onetrust-accept-btn-handler"]:
        try:
            pg.click(sel, timeout=2500); pg.wait_for_timeout(600); return
        except Exception:
            pass

def consultar_juceb(protocolo, login, senha, headless=True):
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=headless)
        ctx = nav.new_context()
        pg = ctx.new_page()
        try:
            pg.goto(URL_LOGIN, timeout=60000)
            pg.wait_for_timeout(2500)
            _fechar_cookie(pg)
            pg.fill("#_ctl0_MainContent_txtCPFCNPJ", login)
            pg.fill("#_ctl0_MainContent_txtSenha", senha)
            try:
                pg.click("#_ctl0_MainContent_btnEntrar", timeout=8000)
            except Exception:
                pg.eval_on_selector("#_ctl0_MainContent_btnEntrar", "el => el.click()")
            pg.wait_for_timeout(4000)

            # abre "Acompanhamento de Requerimentos" (nova aba)
            with ctx.expect_page(timeout=10000) as info:
                try:
                    pg.click("#_ctl0_MainContent_btnReimpressaoDocumentos", timeout=6000)
                except Exception:
                    pg.eval_on_selector("#_ctl0_MainContent_btnReimpressaoDocumentos", "el => el.click()")
            aba = info.value
            aba.wait_for_timeout(2500)

            # busca pelo protocolo
            aba.fill("#ctl00_ContentPlaceHolder_txtRequerimento", str(protocolo))
            aba.wait_for_timeout(400)
            aba.click("#ctl00_ContentPlaceHolder_btnBuscar")
            aba.wait_for_timeout(4000)

            # le a tabela de resultado
            try:
                aba.wait_for_selector("table", timeout=15000)
            except Exception:
                return {"erro": "tabela de resultado nao apareceu"}

            linhas_tr = aba.query_selector_all("table tr")
            for tr in linhas_tr:
                txt_tr = (tr.inner_text() or "")
                if str(protocolo) in txt_tr:
                    botoes = tr.query_selector_all("input[type=submit]")
                    for b_el in botoes:
                        val = (b_el.get_attribute("value") or "").strip()
                        if val and "atualizar" not in val.lower():
                            status_final = (txt_tr.strip()[:150] + " | " + val)[:200]
                            return {"status_texto": status_final, "classificacao": classificar_status_ba(status_final)}
                    if txt_tr.strip():
                        return {"status_texto": txt_tr.strip()[:200], "classificacao": classificar_status_ba(txt_tr)}
            corpo = aba.inner_text("body")
            # procura a linha que contem o protocolo
            for linha in corpo.split("\n"):
                if str(protocolo) in linha:
                    # a situacao esta na mesma linha; classifica pelo texto
                    return {"status_texto": linha.strip()[:200], "classificacao": classificar_status_ba(linha)}
            # fallback: procura por palavras-chave no corpo todo
            if _norm("EXIGENCIA") in _norm(corpo):
                return {"status_texto": "EM EXIGENCIA", "classificacao": "exigencia"}
            if "FINALIZADO" in _norm(corpo):
                return {"status_texto": "FINALIZADO", "classificacao": "deferido"}
            if _norm("TRAMITACAO") in _norm(corpo):
                return {"status_texto": "EM TRAMITACAO", "classificacao": "tramitacao"}
            return {"erro": "protocolo nao encontrado no resultado"}
        except Exception as e:
            return {"erro": str(e)[:150]}
        finally:
            nav.close()

def baixar_documento_juceb(protocolo, login, senha, destino_path, headless=True):
    """Loga na JUCEB, busca o protocolo, e se estiver FINALIZADO baixa o documento
    de registro (botao da lupa) salvando em destino_path. Retorna True/False."""
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=headless)
        ctx = nav.new_context(accept_downloads=True)
        pg = ctx.new_page()
        try:
            pg.goto(URL_LOGIN, timeout=60000)
            pg.wait_for_timeout(2500)
            _fechar_cookie(pg)
            pg.fill("#_ctl0_MainContent_txtCPFCNPJ", login)
            pg.fill("#_ctl0_MainContent_txtSenha", senha)
            try:
                pg.click("#_ctl0_MainContent_btnEntrar", timeout=8000)
            except Exception:
                pg.eval_on_selector("#_ctl0_MainContent_btnEntrar", "el => el.click()")
            pg.wait_for_timeout(4000)

            with ctx.expect_page(timeout=10000) as info:
                try:
                    pg.click("#_ctl0_MainContent_btnReimpressaoDocumentos", timeout=6000)
                except Exception:
                    pg.eval_on_selector("#_ctl0_MainContent_btnReimpressaoDocumentos", "el => el.click()")
            aba = info.value
            aba.wait_for_timeout(2500)

            aba.fill("#ctl00_ContentPlaceHolder_txtRequerimento", str(protocolo))
            aba.wait_for_timeout(400)
            aba.click("#ctl00_ContentPlaceHolder_btnBuscar")
            aba.wait_for_timeout(4000)

            linhas_tr = aba.query_selector_all("table tr")
            for tr in linhas_tr:
                txt_tr = (tr.inner_text() or "")
                if str(protocolo) not in txt_tr:
                    continue
                if "finalizado" not in txt_tr.lower():
                    return False
                botoes = tr.query_selector_all("input[type=submit]")
                for b_el in botoes:
                    try:
                        with aba.expect_download(timeout=15000) as dl_info:
                            b_el.click()
                        download = dl_info.value
                        download.save_as(destino_path)
                        return True
                    except Exception:
                        continue
            return False
        except Exception as e:
            print("Erro ao baixar documento JUCEB:", str(e)[:150])
            return False
        finally:
            nav.close()

# teste manual
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv("/root/atos/.env")
    r = consultar_juceb("267951590", os.getenv("JUCEB_LOGIN"), os.getenv("JUCEB_SENHA"))
    print(r)
