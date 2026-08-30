# -*- coding: utf-8 -*-
import os
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
    """Mapeia o texto bruto da CONSULTA PUBLICA da JUCESC (buscador.php,
    sem login) pros status internos do ATOS. Esse vocabulario e' o da tela
    publica de acompanhamento - DIFERENTE do vocabulario do REGIN
    (ReimpressaoDocs.aspx, autenticado), que usa
    classificar_situacao_regin_sc() logo abaixo. As duas telas descrevem o
    MESMO estado com termos distintos - confirmado em 29/08/2026 com o
    protocolo 265529433 (MELI DEVELOPERS BRASIL LTDA/SC):

        Consulta publica          | REGIN
        ---------------------------|--------------------------------
        "Em Tramitacao"            | "EM ANALISE NO ORGAO DE REGISTRO"
        "Em Exigencia"             | (ainda nao observado)
        (deferido - nao observado) | (ainda nao observado)

    INDEFERIDO e checado ANTES de DEFERIDO com word-boundary (nao
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
    # "Em Tramitacao" (confirmado 29/08/2026) cai aqui pelo default -
    # mantido implicito de proposito (qualquer texto novo/desconhecido da
    # consulta publica tambem deve cair em tramitacao, nunca travar o
    # pipeline por vocabulario nao mapeado).
    return "tramitacao"


def classificar_situacao_regin_sc(situacao_texto):
    """Mapeia o texto da coluna 'Situacao' do REGIN (ReimpressaoDocs.aspx,
    autenticado) - vocabulario DIFERENTE do da consulta publica (ver
    classificar_status_sc acima). Usado exclusivamente por
    baixar_documento_jucesc() pra decidir se o processo esta de fato
    deferido ANTES de tentar baixar - nao usado por processar_sc()/status
    publico.

    NAO CONFIRMADO EMPIRICAMENTE (29/08/2026): so' observamos ate agora
    "EM ANALISE NO ORGAO DE REGISTRO" (tramitacao) pro protocolo de teste
    265529433. Os termos de deferido abaixo (DEFERIDO/ARQUIVADO/REGISTRADO)
    sao um palpite espelhado do vocabulario da consulta publica - CONFIRMAR
    contra o texto real assim que o processo de teste for deferido (ver
    Parte E do pedido). Mantem a mesma protecao word-boundary contra
    INDEFERIDO."""
    s = _norm(situacao_texto)
    if re.search(r"\bINDEFERID[OA]\b", s):
        return "indeferido"
    if re.search(r"\bEXIGENCIA\b", s) or "CUMPRINDO EXIGENCIA" in s:
        return "exigencia"
    if re.search(r"\bDEFERID[OA]\b", s) or "ARQUIVADO" in s or "REGISTRADO" in s:
        return "deferido"
    # "EM ANALISE NO ORGAO DE REGISTRO" (confirmado 29/08/2026) cai aqui.
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


URL_REIMPRESSAO = "https://regin.jucesc.sc.gov.br/requerimentoV2/ReimpressaoDocs.aspx"
_DIR_MODULO = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SESSAO_PADRAO = os.path.join(_DIR_MODULO, "jucesc_session.json")

# CONFIRMADO por Diogo em 29/08/2026 (tela real, com sessao logada): o campo
# de busca do ReimpressaoDocs.aspx se chama "No Requerimento/Protocolo
# Principal" e ACEITA o numero de protocolo (265529433 funcionou, achou o
# resultado). O resultado tem colunas: Requerimento | Protocolo Principal |
# Ato | Razao Social | Situacao | Protocolo(s) Vinculado(s) | Capa | Boleto
# | Doc. O numero de "Requerimento" (ex: 81600003602818) e' DIFERENTE do
# protocolo e o REGIN pode exigir ele (nao o protocolo) pro download em si -
# por isso extraimos e persistimos os dois.
NOME_COLUNA_REQUERIMENTO = "REQUERIMENTO"
NOME_COLUNA_SITUACAO = "SITUACAO"
NOME_COLUNA_DOWNLOAD = "DOCUMENTO"  # CONFIRMADO 29/08/2026 direto na tela autenticada
                                     # real (protocolo 265529433): colunas reais sao
                                     # "Capa", "Boleto", "Documento", "Atualizar" (nao
                                     # "Doc"). "Boleto" tem um botao de lupa disponivel
                                     # mesmo com o processo ainda EM ANALISE (nao
                                     # deferido) - parece ser geracao/consulta de boleto
                                     # de taxa, independente do deferimento do ato. Ja
                                     # "Documento"/"Capa" ficam vazios ate deferir -
                                     # confirmado empiricamente (celula sem filho
                                     # algum, nao so' sem texto).


def _sessao_expirada(pagina):
    """Deteta se fomos redirecionados pro login do gov.br em vez de cair na
    pagina real da JUCESC - sinal de que a sessao persistida caducou."""
    url = pagina.url
    return "sso.acesso.gov.br" in url or "acesso.gov.br" in url


def _preencher_periodo_amplo(pg):
    """Diogo confirmou (29/08/2026) que sem periodo informado a busca do
    REGIN usa uma janela padrao de 90 dias - processos mais antigos que isso
    NAO apareceriam no resultado (falharia em silencio, parecendo
    "protocolo_nao_encontrado" quando na verdade e' so' filtro de data).
    Tenta preencher um periodo bem amplo (ultimos ~5 anos ate hoje) ANTES de
    buscar, pra nunca depender do default. NAO CONFIRMADO contra o HTML real
    quais sao os ids/names dos campos de data - tenta alguns nomes prováveis
    e desiste em silencio (nao trava o fluxo) se nenhum bater; nesse caso a
    busca roda com o filtro padrao de 90 dias mesmo, e quem chamar deve
    saber que protocolos antigos podem nao aparecer ate isso ser confirmado
    com explorar_jucesc.py."""
    # CORRIGIDO 29/08/2026: os campos sao <input type="date"> HTML5 de
    # verdade (confirmado inspecionando a pagina autenticada real), que
    # exigem valor no formato ISO AAAA-MM-DD via .fill() - nao
    # DD/MM/AAAA (formato so' de exibicao, o .fill() ia falhar em
    # silencio ou preencher errado).
    from datetime import datetime as _dt, timedelta as _td
    hoje = _dt.now().strftime("%Y-%m-%d")
    inicio = (_dt.now() - _td(days=5 * 365)).strftime("%Y-%m-%d")
    candidatos_inicio = ["#ctl00_ContentPlaceHolder_txtDtInicio", "input[name*=DtInicio]"]
    candidatos_fim = ["#ctl00_ContentPlaceHolder_txtDtFim", "input[name*=DtFim]"]
    try:
        for sel in candidatos_inicio:
            campo = pg.query_selector(sel)
            if campo:
                campo.fill(inicio)
                break
        for sel in candidatos_fim:
            campo = pg.query_selector(sel)
            if campo:
                campo.fill(hoje)
                break
    except Exception:
        pass


def _indice_coluna(pg, nome_coluna_norm):
    """Acha o indice (0-based) da coluna cujo cabecalho normalizado bate com
    nome_coluna_norm, procurando na primeira linha da(s) tabela(s) da
    pagina. Retorna None se nao achar - quem chama decide o fallback."""
    for tabela in pg.query_selector_all("table"):
        cabecalhos = tabela.query_selector_all("tr:first-child th, tr:first-child td")
        for i, c in enumerate(cabecalhos):
            if _norm(c.inner_text()) == nome_coluna_norm:
                return i
    return None


def baixar_documento_jucesc(numero_protocolo, destino_path, headless=True, sessao_path=None):
    """CONFIRMADO EMPIRICAMENTE EM 29/08/2026 (inspecionando o DOM real da
    pagina autenticada, via claude-in-chrome controlando a aba ja logada do
    Diogo - NAO via explorar_jucesc.py, que ainda nao rodou por falta de
    sessao persistida):
    - id do campo de busca: ctl00_ContentPlaceHolder_txtRequerimento
    - ids dos campos de periodo: ctl00_ContentPlaceHolder_txtDtInicio /
      txtDtFim - CONFIRMADO que sao <input type="date"> HTML5 de verdade
      (exigem valor ISO AAAA-MM-DD via .fill(), nao DD/MM/AAAA)
    - id do botao: ctl00_ContentPlaceHolder_btnBuscar
    - cabecalhos reais da tabela de resultado: "", Requerimento, Protocolo
      Principal, Ato, Razao Social, Situacao, Protocolo(s) Vinculado(s),
      Capa, Boleto, Documento, Atualizar (coluna e' "Documento", nao "Doc")
    - testado contra o protocolo real 265529433 (MELI DEVELOPERS BRASIL
      LTDA/SC): Requerimento real = 81600003602818, Situacao real = "EM
      ANALISE NO ORGAO DE REGISTRO", celulas "Capa" e "Documento" client-
      side genuinamente vazias (sem nenhum elemento filho, nao so' sem
      texto) - "Boleto" tem um <input class="btn btn-light"> (icone de
      lupa) mesmo sem deferimento, aparentemente uma acao separada
      (consulta/geracao de boleto de taxa), nao o documento final.

    AINDA NAO CONFIRMADO (palpite, nao chutar sem avisar):
    - O texto real do REGIN pra situacao "deferido" - so' foi observado "EM
      ANALISE NO ORGAO DE REGISTRO" (nao-deferido) ate agora. Os termos em
      classificar_situacao_regin_sc() (DEFERIDO/ARQUIVADO/REGISTRADO) sao
      espelhados do vocabulario da consulta publica, nunca vistos de fato
      no REGIN.
    - O elemento clicavel que vai aparecer dentro da celula "Documento"
      quando ela for populada (link? botao? icone com onclick?) - a celula
      nunca foi vista com conteudo, porque nenhum processo deferido
      apareceu ainda pro Diogo verificar. O codigo abaixo tenta varios
      seletores plausiveis dentro dessa celula (input[type=submit], a,
      button, img) mas isso SO fica confirmado de verdade quando um
      processo real deferido for inspecionado.

    Falta, nessa ordem, pra fechar a validacao (processo real 265529433
    previsto pra deferir ate 02/09/2026, prazo definido pela propria
    JUCESC - nada que a gente faca acelera isso):
    1. Diogo exportar os cookies da sessao ja autenticada (Cookie-Editor,
       ver docs/sessao_jucesc.md) assim que o alerta de deferimento chegar.
    2. Subir jucesc_session.json pro servidor.
    3. Rodar explorar_jucesc.py contra o protocolo real ja deferido, pra
       confirmar/ajustar o elemento clicavel da celula "Documento" e o
       texto real de "deferido".
    4. Testar o download de ponta a ponta - PDF abre de fato, nao so'
       passa no validador.

    Requer sessao persistida (storage_state) ja autenticada via gov.br -
    NUNCA recebe usuario/senha, nunca tenta logar sozinho. SEMPRE re-checa a
    situacao real da linha do REGIN antes de clicar em baixar (nao confia
    so' no chamador ter avaliado isso) - processo nao-deferido no REGIN
    nunca aciona o download, mesmo se essa funcao for chamada sem
    pre-checagem externa.

    Retorna sempre um dict, nunca levanta excecao. numero_requerimento vem
    preenchido sempre que a linha do processo foi localizada, mesmo em caso
    de falha (o chamador deve persistir isso independente do resultado):
      {"sucesso": True, "caminho_pdf": destino_path, "motivo_falha": None,
       "numero_requerimento": str}
      {"sucesso": False, "motivo_falha": "sessao_ausente", "numero_requerimento": None}
      {"sucesso": False, "motivo_falha": "sessao_expirada", ...}  <- alertar
      {"sucesso": False, "motivo_falha": "protocolo_nao_encontrado", ...}
      {"sucesso": False, "motivo_falha": "processo nao deferido no REGIN (situacao real: '...')", "numero_requerimento": str}
      {"sucesso": False, "motivo_falha": "<outro motivo>", ...}
    "sessao_expirada" e' o unico motivo que deve gerar alerta imediato pro
    Diogo (e-mail + Telegram) pedindo pra refazer o login supervisionado -
    os demais ficam so' registrados/retentados, mesmo padrao dos outros
    pontos de download (JUCEB/JUCEPE/JUCERJA)."""
    sessao_path = sessao_path or ARQUIVO_SESSAO_PADRAO
    if not os.path.exists(sessao_path):
        return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "sessao_ausente", "numero_requerimento": None}

    from utils_pdf import validar_pdf, quarentena, sanear_pdf

    with sync_playwright() as p:
        nav = p.chromium.launch(headless=headless)
        ctx = nav.new_context(storage_state=sessao_path, accept_downloads=True)
        pg = ctx.new_page()
        try:
            pg.goto(URL_REIMPRESSAO, timeout=60000)
            pg.wait_for_timeout(2500)

            if _sessao_expirada(pg):
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "sessao_expirada", "numero_requerimento": None}

            _preencher_periodo_amplo(pg)

            # TODO (nao confirmado): id/name exato do campo "No
            # Requerimento/Protocolo Principal" - ajustar apos
            # explorar_jucesc.py. Fallback pro primeiro campo de texto
            # visivel do formulario.
            # CONFIRMADO 29/08/2026 direto na pagina autenticada real:
            # id = ctl00_ContentPlaceHolder_txtRequerimento (mesmo padrao
            # ctl00_ContentPlaceHolder_* da JUCEB). Mantidos fallbacks
            # genericos caso a JUCESC troque a versao da tela no futuro.
            campo_busca = None
            for sel in ["#ctl00_ContentPlaceHolder_txtRequerimento", "input[name*=Requerimento]", "input[name*=Protocolo]"]:
                campo_busca = pg.query_selector(sel)
                if campo_busca:
                    break
            if not campo_busca:
                candidatos = [el for el in pg.query_selector_all("input[type=text]") if el.is_visible()]
                campo_busca = candidatos[0] if candidatos else None
            if not campo_busca:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "campo de busca nao encontrado (seletor nao confirmado)", "numero_requerimento": None}
            campo_busca.fill(str(numero_protocolo))
            pg.wait_for_timeout(400)

            # CONFIRMADO 29/08/2026: id = ctl00_ContentPlaceHolder_btnBuscar.
            botao_buscar = None
            for sel in ["#ctl00_ContentPlaceHolder_btnBuscar", "input[type=submit]", "button[type=submit]"]:
                botao_buscar = pg.query_selector(sel)
                if botao_buscar:
                    break
            if not botao_buscar:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "botao de busca nao encontrado (seletor nao confirmado)", "numero_requerimento": None}
            botao_buscar.click()
            pg.wait_for_timeout(4000)

            if _sessao_expirada(pg):
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "sessao_expirada", "numero_requerimento": None}

            idx_requerimento = _indice_coluna(pg, "REQUERIMENTO")
            idx_situacao = _indice_coluna(pg, "SITUACAO")
            idx_download = _indice_coluna(pg, NOME_COLUNA_DOWNLOAD)

            linhas_tr = pg.query_selector_all("table tr")
            linha_alvo = None
            for tr in linhas_tr:
                if str(numero_protocolo) in (tr.inner_text() or ""):
                    linha_alvo = tr
                    break
            if not linha_alvo:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "protocolo_nao_encontrado", "numero_requerimento": None}

            celulas = linha_alvo.query_selector_all("td")

            numero_requerimento = None
            if idx_requerimento is not None and idx_requerimento < len(celulas):
                numero_requerimento = (celulas[idx_requerimento].inner_text() or "").strip() or None

            situacao_real = None
            if idx_situacao is not None and idx_situacao < len(celulas):
                situacao_real = (celulas[idx_situacao].inner_text() or "").strip()

            if situacao_real:
                classificacao_regin = classificar_situacao_regin_sc(situacao_real)
                if classificacao_regin != "deferido":
                    return {
                        "sucesso": False, "caminho_pdf": None,
                        "motivo_falha": "processo nao deferido no REGIN (situacao real: '" + situacao_real + "')",
                        "numero_requerimento": numero_requerimento,
                    }
            else:
                # Coluna Situacao nao localizada por cabecalho (seletor nao
                # confirmado) - nao arrisca baixar sem confirmar deferimento,
                # falha explicito em vez de assumir.
                return {
                    "sucesso": False, "caminho_pdf": None,
                    "motivo_falha": "coluna 'Situacao' nao localizada na tabela de resultado (seletor nao confirmado) - download nao tentado por seguranca",
                    "numero_requerimento": numero_requerimento,
                }

            celula_download = celulas[idx_download] if (idx_download is not None and idx_download < len(celulas)) else None
            botao_download = None
            if celula_download:
                botao_download = (
                    celula_download.query_selector("input[type=submit]")
                    or celula_download.query_selector("a")
                    or celula_download.query_selector("button")
                    or celula_download.query_selector("img")
                )
            if not botao_download:
                # Fallback: qualquer elemento clicavel na linha inteira -
                # menos preciso, mas melhor que desistir sem tentar.
                botao_download = (
                    linha_alvo.query_selector("input[type=submit]")
                    or linha_alvo.query_selector("a")
                )
            if not botao_download:
                return {
                    "sucesso": False, "caminho_pdf": None,
                    "motivo_falha": "elemento de download da coluna 'Doc' nao encontrado (seletor nao confirmado)",
                    "numero_requerimento": numero_requerimento,
                }

            try:
                with pg.expect_download(timeout=20000) as dl_info:
                    botao_download.click()
                download = dl_info.value
                download.save_as(destino_path)
            except Exception as e:
                return {
                    "sucesso": False, "caminho_pdf": None,
                    "motivo_falha": "erro ao aguardar/salvar download: " + str(e)[:200],
                    "numero_requerimento": numero_requerimento,
                }

            # Mesmo padrao ja usado em JUCEB/JUCEPE: se o link levar a uma
            # pagina de impressao HTML em vez de PDF binario (bug tipico de
            # servidor ASP.NET WebForms), o arquivo salvo pode ser HTML puro
            # ou ter lixo colado depois do %%EOF - saneia e valida antes de
            # aceitar.
            sanear_pdf(destino_path)
            valido, motivo_invalido = validar_pdf(destino_path)
            if not valido:
                quarentena(destino_path)
                return {
                    "sucesso": False, "caminho_pdf": None,
                    "motivo_falha": "PDF invalido apos download: " + str(motivo_invalido),
                    "numero_requerimento": numero_requerimento,
                }

            return {"sucesso": True, "caminho_pdf": destino_path, "motivo_falha": None, "numero_requerimento": numero_requerimento}
        except Exception as e:
            return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "erro inesperado: " + str(e)[:200], "numero_requerimento": None}
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
