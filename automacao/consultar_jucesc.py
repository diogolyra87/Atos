# -*- coding: utf-8 -*-
import re
import unicodedata
from playwright.sync_api import sync_playwright

# Formulario de consulta publica (sem login) roda num dominio separado
# (atendimentovirtual.jucesc.sc.gov.br), embutido via iframe na pagina
# institucional (jucesc.sc.gov.br/.../consulta-processo) - navegar direto
# pra essa URL evita ter que lidar com iframe no Playwright.
URL_BUSCA = "https://atendimentovirtual.jucesc.sc.gov.br/buscador.php"


def _norm(txt):
    if not txt:
        return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.upper().strip()


def classificar_status_sc(status_texto):
    """Mapeia o texto bruto retornado pela JUCESC pros status internos do
    ATOS. INDEFERIDO e checado ANTES de DEFERIDO com word-boundary (nao
    substring) - o bug conhecido em consultar_juceb.py era "DEFERIDO" in s
    tambem casar dentro de "INDEFERIDO". Retorna uma classificacao propria
    'indeferido' (diferente de BA/RJ/PE, que jogam indeferimento em
    tramitacao) - decisao de como tratar isso no fluxo de notificacao fica
    pra quando tivermos texto real de um indeferimento da JUCESC pra
    confirmar o vocabulario exato (ver nota em processar_sc)."""
    s = _norm(status_texto)
    if re.search(r"\bINDEFERID[OA]\b", s):
        return "indeferido"
    if re.search(r"\bEXIGENCIA\b", s) or "CUMPRINDO EXIGENCIA" in s:
        return "exigencia"
    if re.search(r"\bDEFERID[OA]\b", s) or "ARQUIVADO" in s or "REGISTRADO" in s:
        return "deferido"
    return "tramitacao"


def _extrair_historico_tabela(pg):
    """Extrai qualquer tabela de andamento/historico presente na pagina de
    resultado. Generico de proposito - a estrutura exata da pagina de
    resultado ainda nao foi validada contra um protocolo real (JUCESC nao
    tem processo de teste publico conhecido no momento em que este modulo
    foi escrito, ver Parte 3 do pedido original)."""
    historico = []
    try:
        linhas = pg.query_selector_all("table tr")
        for tr in linhas:
            celulas = [c.inner_text().strip() for c in tr.query_selector_all("td")]
            celulas = [c for c in celulas if c]
            if celulas:
                historico.append({"texto": " | ".join(celulas)})
    except Exception:
        pass
    return historico


def consultar_jucesc(numero_protocolo, headless=True):
    """Consulta publica de processo na JUCESC (sem login/certificado -
    formulario aberto). Retorna:
    {"status_bruto": str, "status_classificado": str,
     "data_ultima_movimentacao": str|None, "historico": list[dict]}
    ou {"erro": str} se o protocolo nao for encontrado ou algo falhar.

    IMPORTANTE: a extracao do resultado (historico/data) ainda NAO foi
    validada contra uma resposta real de sucesso da JUCESC - so o caminho
    de "protocolo nao encontrado" foi confirmado manualmente (a pagina
    recarrega com ?ne=<mensagem> na URL). Antes de ligar esse modulo no
    polling automatico (processar_sc em atualizar_status.py), rodar
    `python consultar_jucesc.py <protocolo real>` e comparar o resultado
    com o que aparece no navegador - ver Parte 3 do pedido original."""
    protocolo_str = str(numero_protocolo).strip()
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=headless)
        pg = nav.new_page()
        try:
            pg.goto(URL_BUSCA, timeout=60000)
            pg.wait_for_timeout(1500)
            pg.fill("#protocolo", protocolo_str)
            try:
                with pg.expect_navigation(timeout=15000):
                    pg.click("#busca")
            except Exception:
                # se nao navegar (ex: validacao client-side bloqueou, ou o
                # resultado e injetado via JS sem reload de pagina), segue
                # mesmo assim e tenta ler o que estiver na tela.
                pg.wait_for_timeout(3000)
            pg.wait_for_timeout(1500)

            if "ne=" in pg.url:
                return {"erro": "protocolo nao encontrado: " + protocolo_str}

            corpo = (pg.inner_text("body") or "").strip()
            if not corpo:
                return {"erro": "pagina de resultado vazia"}

            historico = _extrair_historico_tabela(pg)
            status_bruto = historico[0]["texto"] if historico else corpo[:300]

            return {
                "status_bruto": status_bruto,
                "status_classificado": classificar_status_sc(status_bruto),
                "data_ultima_movimentacao": None,
                "historico": historico,
            }
        except Exception as e:
            return {"erro": str(e)[:150]}
        finally:
            nav.close()


# teste manual: python consultar_jucesc.py <numero_protocolo>
# (headless=True por padrao - o VPS de producao nao tem XServer; rodar com
# headless=False so numa maquina com display, pra depurar visualmente)
if __name__ == "__main__":
    import sys
    protocolo_teste = sys.argv[1] if len(sys.argv) > 1 else "26/123456-7"
    print("Consultando JUCESC, protocolo:", protocolo_teste)
    r = consultar_jucesc(protocolo_teste, headless=True)
    print("\nRESULTADO:", r)
