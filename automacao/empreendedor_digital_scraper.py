# -*- coding: utf-8 -*-
"""Consulta generica de protocolo na plataforma publica "Empreendedor
Digital", reaproveitada (mesmo WAR JSF/PrimeFaces) por varias Juntas
Comerciais estaduais - confirmado rodando o mesmo template em MG, RS, DF,
CE, MS, MT e AP (validado ao vivo em 01/08/2026). Diferente de JUCERJA/
JUCEB/JUCEPE, essa consulta e publica - NAO exige login.

Estrutura do resultado (confirmada com protocolo real da JUCIS-DF,
262347954): quando o protocolo existe, aparece um bloco
`div.dados-processo` contendo `div.situacao` (o texto do status, com uma
classe CSS adicional que reproduz o status em minusculo, ex:
"desc desc-lg situacao pendente") e, se houver exigencia, uma secao
`div.pendencias` com o texto da exigencia e o prazo. Quando o protocolo
nao existe, a pagina mostra o texto solto "Nenhum registro encontrado."
(sem o bloco `dados-processo`).

Varios desses portais tem um widget Cloudflare Turnstile visivel no HTML,
mas na pratica ele nem sempre bloqueia a consulta (confirmado: DF nao
bloqueou com Chromium headless; RS bloqueou). Ver
estados_empreendedor_digital.json pra saber quais estados estao ativos.
"""
import re
import unicodedata
from playwright.sync_api import sync_playwright


def _norm(txt):
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.upper().strip()


def classificar_status_empreendedor_digital(status_texto):
    """Classificacao conservadora: so marca deferido/exigencia quando o
    texto bate claramente com o vocabulario ja confirmado; qualquer coisa
    fora disso cai em 'tramitacao' (mantido), igual ao padrao usado em
    classificar_status_rj - nunca finaliza/decide por um texto ambiguo."""
    s = _norm(status_texto)
    if "DEFERID" in s and "INDEFERID" not in s:
        return "deferido"
    if "PENDENT" in s or "EXIGENC" in s:
        return "exigencia"
    return "tramitacao"


def consultar_empreendedor_digital(dominio, protocolo, headless=True):
    """Consulta o protocolo no portal publico do dominio informado (ex:
    "portalservicos.jucemg.mg.gov.br"). Retorna:
    - {"status_texto", "classificacao", "exigencia_texto"} em caso de sucesso
    - {"erro": "..."} se nao encontrou, deu timeout ou o layout mudou
    """
    url = "https://" + dominio + "/Portal/pages/consultaProcesso.jsf"
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=headless)
        pagina = navegador.new_page()
        try:
            pagina.goto(url, timeout=25000, wait_until="domcontentloaded")
            pagina.wait_for_timeout(1500)
            pagina.fill("#protocolo", protocolo)
            pagina.click("text=Pesquisar")
            try:
                pagina.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            pagina.wait_for_timeout(3000)

            corpo_texto = pagina.inner_text("body")
            if "Nenhum registro encontrado" in corpo_texto:
                return {"erro": "protocolo nao encontrado"}
            if not pagina.query_selector(".dados-processo"):
                return {"erro": "resultado nao apareceu (timeout - possivel bloqueio de captcha)"}

            situacao_el = pagina.query_selector(".situacao")
            status_texto = situacao_el.inner_text().strip() if situacao_el else ""
            classe = situacao_el.get_attribute("class") if situacao_el else ""
            palavra_classe = ""
            if classe:
                partes = [c for c in classe.split() if c not in ("desc", "desc-lg", "situacao")]
                palavra_classe = partes[-1] if partes else ""

            exigencia_texto = ""
            pend_el = pagina.query_selector(".pendencias")
            if pend_el:
                exigencia_texto = pend_el.inner_text().strip()

            classificacao = classificar_status_empreendedor_digital(palavra_classe or status_texto)
            return {
                "status_texto": status_texto or palavra_classe or "desconhecido",
                "classificacao": classificacao,
                "exigencia_texto": exigencia_texto,
            }
        except Exception as e:
            return {"erro": str(e)[:150]}
        finally:
            navegador.close()


if __name__ == "__main__":
    print("Testando DF com protocolo real...")
    r = consultar_empreendedor_digital("portalservicos.jucis.df.gov.br", "262347954", headless=True)
    print("\nRESULTADO:", r)
