# -*- coding: utf-8 -*-
"""Emissao automatica da Guia Bancaria (boleto de taxa) na JUCERJA, pra
processos uf="RJ". Login/sessao reaproveitados de consultar_jucerja.py
(mesma conta de automacao). Mapeamento tipo_ato+tipo_sociedade -> Ato/Evento
levantado por inspecao real do formulario em 18/08/2026 (Fase 1, aprovado
por Diogo) - ver CAMPOS ainda nao confirmados abaixo.

ATENCAO - selectors ainda NAO verificados contra o site real (Fase 1 foi
autorizada so ate a selecao de Ato/Evento, sem submeter nada): botao
"Adicionar", busca por CNPJ, selecao de tipo de Protocolo, botao "Gerar
Boleto" e o link/botao "Imprimir Guia Bancaria" (incluindo se o PDF
resultante vem direto ou dentro de um envelope .p7s, como acontece no
download de documento ja registrado). Esses pontos SO devem ser
confirmados/corrigidos na primeira execucao supervisionada (Diogo
acompanhando, headless=False, contra um processo real pendente de guia) -
nunca em execucao autonoma antes disso. Ate la, qualquer selector abaixo
que nao bater trava a automacao e devolve motivo_falha claro, sem
levantar excecao.
"""
import os
import re
from playwright.sync_api import sync_playwright

URL_LOGIN = "https://www.jucerja.rj.gov.br/Conta/Entrar?returnUrl=%2FServicos%2FProtocolo%2FTermoUtilizacaoProtocolo"
URL_GERAR_BOLETO = "https://www.jucerja.rj.gov.br/Servicos/GuiaBancariaGerarBoleto"

TIPO_BOLETO_EMPRESA = "5"
PORTE_NORMAL = "1"
TIPO_JURIDICO_VALUE = {"LTDA": "2", "SA": "3", "OUTRAS": "5"}

# tipo_ato historico (anterior ao vocabulario fechado de 14/08/2026) -> forma
# canonica usada no mapeamento abaixo. Decisao de sinonimos: Diogo, 18/08/2026.
SINONIMOS_TIPO_ATO = {
    "ALTERACAO_CONTRATUAL": "Alteração Contratual",
    "Alteracao Contratual": "Alteração Contratual",
    "ESCRITURA_PUBLICA_CONSTITUICAO": "_CONSTITUTIVO",
    "ESCRITURA_PUBLICA": "_CONSTITUTIVO",
    "Contrato Social": "_CONSTITUTIVO",
}

# (tipo_ato canonico, tipo_sociedade LTDA/SA) -> (ato_valor, ato_label, evento_valor, evento_label)
# Valores = atributo "value" dos <option> reais dos selects
# #campoSelecaoAtoGuiaBancaria / #campoSelecaoEventoGuiaBancaria.
MAPEAMENTO_ATO_EVENTO = {
    ("AGE", "SA"): ("7", "007 - Ata de Assembleia Geral Extraordinária", "284", "999 - Ata de Assembleia Geral Extraordinária"),
    ("AGO", "SA"): ("6", "006 - Ata de Assembleia Geral Ordinária", "284", "999 - Ata de Assembleia Geral Ordinária"),
    ("AGOE", "SA"): ("8", "008 - Ata de Assembleia Geral Ordinária e Extraordinária", "284", "999 - Ata de Assembleia Geral Ordinária e Extraordinária"),
    ("AGD", "SA"): ("14", "014 - Ata de Assembleia Geral dos Debenturistas", "284", "999 - Ata de Assembleia Geral dos Debenturistas"),
    ("RCA", "SA"): ("17", "017 - Ata de Reunião do Conselho de Administração", "284", "999 - Ata de Reunião do Conselho de Administração"),
    ("ARD", "SA"): ("16", "016 - Ata de Reunião da Diretoria", "284", "999 - Ata de Reunião da Diretoria"),
    ("ARS", "LTDA"): ("21", "021 - Ata de Reunião / Assembleia de Sócios", "284", "999 - Ata de Reunião / Assembleia de Sócios"),
    # "Alteração Contratual" e generico (36 eventos possiveis pro Ato 002) -
    # 021 usado como default aprovado (aproximacao, ver relatorio Fase 1).
    ("Alteração Contratual", "LTDA"): ("2", "002 - Alteração", "141", "021 - Alteração de Dados (Exceto Nome Empresarial)"),
    ("Alteração Contratual", "SA"): ("2", "002 - Alteração", "141", "021 - Alteração de Dados (Exceto Nome Empresarial)"),
    ("_CONSTITUTIVO", "SA"): ("5", "005 - Ata de Assembleia Geral de Constituição", "284", "999 - Abertura de Matriz"),
    ("_CONSTITUTIVO", "LTDA"): ("23", "090 - Contrato", "284", "999 - Abertura de Matriz"),
    # ATO_EMPRESA_LIDER: caso especial, Tipo Juridico "Outras/Consorcio", nao
    # depende de tipo_sociedade (que nem se aplica a consorcio).
    ("ATO_EMPRESA_LIDER", "OUTRAS"): ("3", "003 - Extinção / Distrato", "284", "999 - Extinção de Matriz"),
}


def resolver_ato_evento(tipo_ato, tipo_sociedade):
    """Retorna dict com tipo_juridico/ato_valor/ato_label/evento_valor/evento_label
    pra essa combinacao, ou None se nao houver mapeamento aprovado."""
    canonico = SINONIMOS_TIPO_ATO.get(tipo_ato, tipo_ato)
    if canonico == "ATO_EMPRESA_LIDER":
        chave = (canonico, "OUTRAS")
        tj = TIPO_JURIDICO_VALUE["OUTRAS"]
    else:
        ts = (tipo_sociedade or "").strip().upper()
        if ts not in ("LTDA", "SA"):
            return None
        chave = (canonico, ts)
        tj = TIPO_JURIDICO_VALUE[ts]
    par = MAPEAMENTO_ATO_EVENTO.get(chave)
    if not par:
        return None
    ato_v, ato_l, evento_v, evento_l = par
    return {"tipo_juridico": tj, "ato_valor": ato_v, "ato_label": ato_l, "evento_valor": evento_v, "evento_label": evento_l}


def _login(pagina, usuario, senha):
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


def emitir_guia_bancaria(processo, usuario, senha, destino_path, headless=True):
    """Emite a Guia Bancaria pro processo (objeto com .tipo_ato, .tipo_sociedade,
    .cnpj, .id) e baixa o PDF resultante em destino_path.

    Retorna dict {"sucesso": bool, "motivo_falha": str|None, "caminho_pdf": str|None}.
    Nunca levanta excecao - qualquer erro vira motivo_falha, pra quem chama
    decidir o que fazer (registrar + notificar, sem travar o fluxo principal)."""
    mapeamento = resolver_ato_evento(processo.tipo_ato, processo.tipo_sociedade)
    if not mapeamento:
        return {"sucesso": False, "caminho_pdf": None,
                "motivo_falha": f"Sem mapeamento Ato/Evento pra tipo_ato={processo.tipo_ato!r} tipo_sociedade={processo.tipo_sociedade!r}"}

    cnpj_digitos = re.sub(r"\D", "", processo.cnpj or "")
    if not cnpj_digitos:
        return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Processo sem CNPJ cadastrado"}

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=headless)
        ctx = navegador.new_context(accept_downloads=True)
        pagina = ctx.new_page()
        try:
            _login(pagina, usuario, senha)
            print("   [GB] checkpoint: logado")

            pagina.goto(URL_GERAR_BOLETO, timeout=60000)
            pagina.wait_for_timeout(2500)
            pagina.select_option("#campoSelecaoTipoBoleto", value=TIPO_BOLETO_EMPRESA)
            pagina.wait_for_timeout(800)
            pagina.select_option("#campoSelecaoTipoJuridico", value=mapeamento["tipo_juridico"])
            pagina.wait_for_timeout(800)
            pagina.select_option("#campoSelecaoPorteEmpresarial", value=PORTE_NORMAL)
            pagina.wait_for_timeout(1800)
            print("   [GB] checkpoint: Tipo Boleto/Juridico/Porte preenchidos")

            ato_el = pagina.query_selector("#campoSelecaoAtoGuiaBancaria")
            if not ato_el or len(ato_el.query_selector_all("option")) <= 1:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo Ato nao carregou opcoes"}
            pagina.select_option("#campoSelecaoAtoGuiaBancaria", value=mapeamento["ato_valor"])
            pagina.wait_for_timeout(1500)

            evento_el = pagina.query_selector("#campoSelecaoEventoGuiaBancaria")
            if not evento_el or len(evento_el.query_selector_all("option")) <= 1:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo Evento nao carregou opcoes"}
            pagina.select_option("#campoSelecaoEventoGuiaBancaria", value=mapeamento["evento_valor"])
            pagina.wait_for_timeout(500)
            print("   [GB] checkpoint: Ato/Evento selecionados:", mapeamento["ato_label"], "/", mapeamento["evento_label"])

            # --- A PARTIR DAQUI: selectors NAO verificados (ver docstring do
            # modulo). Precisam ser confirmados/ajustados na primeira execucao
            # supervisionada (headless=False, Diogo acompanhando). ---

            # Quantidade: 1 + Adicionar
            botao_adicionar = pagina.query_selector("text=Adicionar")
            if not botao_adicionar:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Adicionar' nao encontrado (selector nao confirmado - ver execucao supervisionada)"}
            botao_adicionar.click()
            pagina.wait_for_timeout(1500)
            print("   [GB] checkpoint: Adicionar clicado")

            # Busca por CNPJ - selector do campo ainda nao confirmado
            campo_cnpj = pagina.query_selector("input[name*='CNPJ' i], input[id*='CNPJ' i]")
            if not campo_cnpj:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo de busca por CNPJ nao encontrado (selector nao confirmado)"}
            campo_cnpj.fill(cnpj_digitos)
            pagina.wait_for_timeout(500)
            botao_buscar_cnpj = pagina.query_selector("text=Buscar")
            if botao_buscar_cnpj:
                botao_buscar_cnpj.click()
                pagina.wait_for_timeout(2000)
            print("   [GB] checkpoint: CNPJ buscado")

            # Tipo de Protocolo = Requerimento Exclusivamente Digital (decisao
            # de Diogo, 18/08/2026) - selector ainda nao confirmado.
            radio_digital = pagina.query_selector("text=Requerimento Exclusivamente Digital")
            if radio_digital:
                radio_digital.click()
                pagina.wait_for_timeout(500)
            else:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Opcao 'Requerimento Exclusivamente Digital' nao encontrada (selector nao confirmado)"}

            botao_gerar = pagina.query_selector("text=Gerar Boleto")
            if not botao_gerar:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Gerar Boleto' nao encontrado (selector nao confirmado)"}
            botao_gerar.click()
            pagina.wait_for_timeout(3000)
            print("   [GB] checkpoint: Gerar Boleto clicado, url:", pagina.url)

            botao_imprimir = pagina.query_selector("text=Imprimir Guia Bancária")
            if not botao_imprimir:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Imprimir Guia Bancária' nao encontrado apos gerar (selector nao confirmado, ou geracao falhou)"}
            try:
                with pagina.expect_download(timeout=20000) as dl_info:
                    botao_imprimir.click()
                download = dl_info.value
                download.save_as(destino_path)
            except Exception as e:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Erro ao baixar PDF da guia: " + str(e)[:200]}

            if not os.path.exists(destino_path) or os.path.getsize(destino_path) == 0:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Download da guia falhou ou arquivo vazio"}

            # NOTA: se o arquivo baixado vier como .p7s (envelope assinado, como
            # acontece no download de documento ja registrado via
            # baixar_documento_jucerja em consultar_jucerja.py) em vez de PDF
            # direto, precisa do mesmo passo de extracao via
            # `openssl cms -verify` - so' descobrimos qual dos dois casos e'
            # este na execucao supervisionada.
            print("   [GB] checkpoint: guia baixada em", destino_path)
            return {"sucesso": True, "caminho_pdf": destino_path, "motivo_falha": None}

        except Exception as e:
            return {"sucesso": False, "caminho_pdf": None, "motivo_falha": str(e)[:300]}
        finally:
            navegador.close()
