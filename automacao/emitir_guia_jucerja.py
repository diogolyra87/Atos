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
from utils_pdf import validar_pdf, primeiros_bytes_legivel, quarentena

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


def emitir_guia_bancaria(processo, usuario, senha, destino_path, headless=True, debug_dir=None):
    """Emite a Guia Bancaria pro processo (objeto com .tipo_ato, .tipo_sociedade,
    .cnpj, .id) e baixa o PDF resultante em destino_path.

    debug_dir (24/08/2026, primeira execucao real): se informado, salva um
    screenshot .png numerado a cada checkpoint (e no ponto exato de qualquer
    falha) - serve de "supervisao gravada" quando nao da pra rodar
    headless=False de verdade (servidor sem XServer). Nunca falha por causa
    do screenshot (best-effort, ignora erro de escrita).

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

    _contador_shot = [0]
    def _shot(pagina, rotulo):
        if not debug_dir:
            return
        try:
            _contador_shot[0] += 1
            nome = f"{_contador_shot[0]:02d}_{rotulo}.png"
            pagina.screenshot(path=os.path.join(debug_dir, nome), full_page=True)
        except Exception as e:
            print("   [GB] aviso: falha ao salvar screenshot de debug:", str(e)[:100])

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=headless)
        ctx = navegador.new_context(accept_downloads=True)
        pagina = ctx.new_page()
        try:
            _login(pagina, usuario, senha)
            print("   [GB] checkpoint: logado")
            _shot(pagina, "logado")

            pagina.goto(URL_GERAR_BOLETO, timeout=60000)
            pagina.wait_for_timeout(2500)
            pagina.select_option("#campoSelecaoTipoBoleto", value=TIPO_BOLETO_EMPRESA)
            pagina.wait_for_timeout(800)
            pagina.select_option("#campoSelecaoTipoJuridico", value=mapeamento["tipo_juridico"])
            pagina.wait_for_timeout(800)
            pagina.select_option("#campoSelecaoPorteEmpresarial", value=PORTE_NORMAL)
            pagina.wait_for_timeout(1800)
            print("   [GB] checkpoint: Tipo Boleto/Juridico/Porte preenchidos")
            _shot(pagina, "tipo_boleto_juridico_porte")

            ato_el = pagina.query_selector("#campoSelecaoAtoGuiaBancaria")
            if not ato_el or len(ato_el.query_selector_all("option")) <= 1:
                _shot(pagina, "FALHA_campo_ato_vazio")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo Ato nao carregou opcoes"}
            pagina.select_option("#campoSelecaoAtoGuiaBancaria", value=mapeamento["ato_valor"])
            pagina.wait_for_timeout(1500)

            evento_el = pagina.query_selector("#campoSelecaoEventoGuiaBancaria")
            if not evento_el or len(evento_el.query_selector_all("option")) <= 1:
                _shot(pagina, "FALHA_campo_evento_vazio")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo Evento nao carregou opcoes"}
            pagina.select_option("#campoSelecaoEventoGuiaBancaria", value=mapeamento["evento_valor"])
            pagina.wait_for_timeout(500)
            print("   [GB] checkpoint: Ato/Evento selecionados:", mapeamento["ato_label"], "/", mapeamento["evento_label"])
            _shot(pagina, "ato_evento_selecionados")

            # --- A PARTIR DAQUI: selectors NAO verificados (ver docstring do
            # modulo). Precisam ser confirmados/ajustados na primeira execucao
            # supervisionada (headless=False, Diogo acompanhando). ---

            # Quantidade: 1 + Adicionar
            botao_adicionar = pagina.query_selector("text=Adicionar")
            if not botao_adicionar:
                _shot(pagina, "FALHA_botao_adicionar_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Adicionar' nao encontrado (selector nao confirmado - ver execucao supervisionada)"}
            botao_adicionar.click()
            pagina.wait_for_timeout(1500)
            print("   [GB] checkpoint: Adicionar clicado")
            _shot(pagina, "adicionar_clicado")

            # Busca por CNPJ - campo confirmado na execucao real de 24/08/2026.
            campo_cnpj = pagina.query_selector("input[name*='CNPJ' i], input[id*='CNPJ' i]")
            if not campo_cnpj:
                _shot(pagina, "FALHA_campo_cnpj_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Campo de busca por CNPJ nao encontrado (selector nao confirmado)"}
            campo_cnpj.fill(cnpj_digitos)
            pagina.wait_for_timeout(500)
            # CORRIGIDO 24/08/2026 (execucao real): o botao se chama
            # "Pesquisar", nao "Buscar" - o codigo anterior nao encontrava
            # "Buscar" e simplesmente pulava o clique (campo opcional por
            # engano), entao o CNPJ nunca era de fato pesquisado/validado.
            botao_pesquisar_cnpj = pagina.query_selector("button:has-text('Pesquisar')")
            if not botao_pesquisar_cnpj:
                _shot(pagina, "FALHA_botao_pesquisar_cnpj_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Pesquisar' (busca de CNPJ) nao encontrado"}
            botao_pesquisar_cnpj.click()
            pagina.wait_for_timeout(2000)
            print("   [GB] checkpoint: CNPJ pesquisado")
            _shot(pagina, "cnpj_pesquisado")

            # Tipo de Protocolo = Requerimento Exclusivamente Digital (decisao
            # de Diogo, 18/08/2026) - selector ainda nao confirmado.
            radio_digital = pagina.query_selector("text=Requerimento Exclusivamente Digital")
            if radio_digital:
                radio_digital.click()
                pagina.wait_for_timeout(500)
                _shot(pagina, "requerimento_digital_selecionado")
            else:
                _shot(pagina, "FALHA_requerimento_digital_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Opcao 'Requerimento Exclusivamente Digital' nao encontrada (selector nao confirmado)"}

            # CORRIGIDO 24/08/2026 (execucao real): nao existe botao "Gerar
            # Boleto" nessa tela - "GERAR BOLETO" e' so o TITULO da pagina
            # (<h1>), e "text=Gerar Boleto" estava clicando nele por engano
            # (elemento sem acao, por isso a pagina nunca saia do lugar). O
            # botao real de submissao se chama "Confirmar".
            botao_gerar = pagina.query_selector("button:has-text('Confirmar')")
            if not botao_gerar:
                _shot(pagina, "FALHA_botao_confirmar_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Confirmar' nao encontrado (selector nao confirmado)"}
            botao_gerar.click()
            pagina.wait_for_timeout(3000)
            print("   [GB] checkpoint: Confirmar clicado, url:", pagina.url)
            _shot(pagina, "confirmar_clicado")

            # DESCOBERTO 24/08/2026 (execucao real): apos "Confirmar" a
            # pagina abre uma tela de "Confirmacao do Boleto" (NIRE, CNPJ,
            # Nome e Valor exibidos) com um botao real "Gerar Boleto" no
            # rodape - esse clique estava faltando, por isso a busca por
            # "Imprimir Guia Bancaria" sempre falhava (pagina nunca saia da
            # tela de confirmacao).
            botao_gerar_boleto_confirmacao = pagina.query_selector("button:has-text('Gerar Boleto')")
            if not botao_gerar_boleto_confirmacao:
                _shot(pagina, "FALHA_botao_gerar_boleto_confirmacao_nao_encontrado")
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Gerar Boleto' (tela de confirmacao) nao encontrado"}
            botao_gerar_boleto_confirmacao.click()
            pagina.wait_for_timeout(3000)
            print("   [GB] checkpoint: Gerar Boleto (confirmacao) clicado, url:", pagina.url)
            _shot(pagina, "gerar_boleto_confirmacao_clicado")

            # DESCOBERTO 24/08/2026 (execucao real): a tela de sucesso
            # ("Solicitacao de Guia Bancaria Realizada com sucesso!") exige
            # marcar o checkbox "Estou ciente das orientacoes de pagamento"
            # antes do botao "Imprimir Guia Bancaria" ficar habilitado -
            # sem isso o botao fica visivel mas nao reage ao clique
            # (por isso o clique anterior sempre estourava timeout).
            checkbox_input = pagina.query_selector("input[type=checkbox]")
            if not checkbox_input:
                _shot(pagina, "FALHA_checkbox_ciente_nao_encontrado")
                if debug_dir:
                    with open(os.path.join(debug_dir, "pagina_sem_checkbox.html"), "w", encoding="utf-8") as f:
                        f.write(pagina.content())
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Checkbox 'Estou ciente das orientacoes de pagamento' nao encontrado"}
            # DESCOBERTO 24/08/2026 (execucao real): o <input type=checkbox>
            # real fica fora do viewport (checkbox custom-estilizado, input
            # nativo escondido) - clique fisico (mesmo com force=True) falha
            # com "Element is outside of the viewport". Usa el.click() via
            # JS (metodo nativo do DOM, nao depende de coordenadas na tela)
            # e, se ainda assim nao marcar, forca a propriedade via o
            # setter nativo do prototype (necessario para inputs
            # controlados por React/Angular, que ignoram atribuicao direta
            # de el.checked).
            pagina.evaluate("(el) => el.click()", checkbox_input)
            pagina.wait_for_timeout(500)
            marcado = checkbox_input.is_checked()
            if not marcado:
                pagina.evaluate(
                    "(el) => { const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'checked').set; setter.call(el, true); el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); }",
                    checkbox_input,
                )
                pagina.wait_for_timeout(500)
                marcado = checkbox_input.is_checked()
            print("   [GB] checkpoint: checkbox ciente marcado =", marcado)
            _shot(pagina, "checkbox_ciente_marcado")
            if debug_dir and not marcado:
                with open(os.path.join(debug_dir, "pagina_checkbox_nao_marcado.html"), "w", encoding="utf-8") as f:
                    f.write(pagina.content())

            botao_imprimir = pagina.query_selector("button:has-text('Imprimir Guia Bancária'), a:has-text('Imprimir Guia Bancária')")
            if not botao_imprimir:
                _shot(pagina, "FALHA_botao_imprimir_nao_encontrado")
                if debug_dir:
                    with open(os.path.join(debug_dir, "pagina_sem_botao_imprimir.html"), "w", encoding="utf-8") as f:
                        f.write(pagina.content())
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Botao 'Imprimir Guia Bancária' nao encontrado apos gerar (selector nao confirmado, ou geracao falhou)"}
            if debug_dir:
                try:
                    outer_html = botao_imprimir.evaluate("el => el.outerHTML")
                    with open(os.path.join(debug_dir, "botao_imprimir_outerhtml.txt"), "w", encoding="utf-8") as f:
                        f.write(outer_html)
                except Exception:
                    pass

            # DESCOBERTO 24/08/2026 (execucao real): o elemento e' um <a
            # id="imprimirGuiaHref" href="/Servicos/GuiaBancariaImpressaoBoleto"
            # class="... ats-href-disabled">. A classe "ats-href-disabled"
            # aplica pointer-events:none (por isso o clique do Playwright
            # travava esperando "receber eventos"). PORTANTO: buscar essa
            # URL direto via GET (tentativa anterior) baixa a pagina HTML de
            # impressao (title "JUCERJA - Guia Bancaria"), NAO um PDF binario
            # - "Imprimir" aqui significa literalmente renderizar a pagina
            # pra PDF via engine do navegador, nao um endpoint que devolve
            # PDF pronto. Fix: navega ate' essa URL na propria `pagina` e
            # usa pagina.pdf() (Chromium headless) pra gerar o PDF real.
            href = botao_imprimir.get_attribute("href")
            if href:
                url_completa = href if href.startswith("http") else ("https://www.jucerja.rj.gov.br" + href)
                try:
                    pagina.goto(url_completa, wait_until="networkidle", timeout=20000)
                    pagina.wait_for_timeout(1000)
                    _shot(pagina, "pagina_impressao_carregada")
                    pagina.pdf(path=destino_path, format="A4", print_background=True)
                except Exception as e:
                    _shot(pagina, "FALHA_download_guia")
                    if debug_dir:
                        with open(os.path.join(debug_dir, "pagina_falha_download.html"), "w", encoding="utf-8") as f:
                            f.write(pagina.content())
                    return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Erro ao gerar PDF da guia via pagina.pdf() (" + url_completa + "): " + str(e)[:200]}
            else:
                paginas_antes = len(ctx.pages)
                try:
                    with pagina.expect_download(timeout=15000) as dl_info:
                        botao_imprimir.click(timeout=8000)
                    download = dl_info.value
                    download.save_as(destino_path)
                except Exception as e:
                    _shot(pagina, "FALHA_download_guia")
                    if debug_dir:
                        with open(os.path.join(debug_dir, "pagina_falha_download.html"), "w", encoding="utf-8") as f:
                            f.write(pagina.content())
                    if len(ctx.pages) > paginas_antes:
                        nova_pagina = ctx.pages[-1]
                        _shot(nova_pagina, "nova_aba_apos_imprimir")
                        return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Clique em 'Imprimir Guia Bancaria' abriu nova aba (url: " + nova_pagina.url[:150] + ") em vez de baixar na mesma pagina - ajuste necessario"}
                    return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Erro ao baixar PDF da guia: " + str(e)[:200]}

            if not os.path.exists(destino_path) or os.path.getsize(destino_path) == 0:
                return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "Download da guia falhou ou arquivo vazio"}

            # GUARDA DE SEGURANCA 24/08/2026: ja aconteceu de o arquivo salvo
            # ser HTML (pagina de erro/impressao) em vez de PDF de verdade,
            # e isso quase foi enviado por e-mail como anexo ".pdf" invalido.
            # Nunca reportar sucesso sem validar o PDF de verdade (assinatura,
            # %%EOF, e abertura real via PyMuPDF).
            valido, motivo_invalido = validar_pdf(destino_path)
            if not valido:
                trecho = primeiros_bytes_legivel(destino_path)
                caminho_quarentena = quarentena(destino_path)
                return {
                    "sucesso": False,
                    "caminho_pdf": None,
                    "motivo_falha": "Arquivo gerado nao e' um PDF valido (" + motivo_invalido + "). Primeiros bytes: " + trecho[:200] + ". Preservado em: " + str(caminho_quarentena),
                }

            # NOTA: se o arquivo baixado vier como .p7s (envelope assinado, como
            # acontece no download de documento ja registrado via
            # baixar_documento_jucerja em consultar_jucerja.py) em vez de PDF
            # direto, precisa do mesmo passo de extracao via
            # `openssl cms -verify` - so' descobrimos qual dos dois casos e'
            # este na execucao supervisionada.
            print("   [GB] checkpoint: guia baixada em", destino_path)
            _shot(pagina, "guia_baixada_sucesso")
            return {"sucesso": True, "caminho_pdf": destino_path, "motivo_falha": None}

        except Exception as e:
            _shot(pagina, "FALHA_excecao_inesperada")
            return {"sucesso": False, "caminho_pdf": None, "motivo_falha": str(e)[:300]}
        finally:
            navegador.close()
