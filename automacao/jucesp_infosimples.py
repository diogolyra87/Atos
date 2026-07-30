# -*- coding: utf-8 -*-
"""Integracao com a API da Infosimples para JUCESP: ficha cadastral e download
de documento digitalizado por NIRE.

NAO inclui acompanhamento de status (consulta de andamento/protocolo). Isso ja
e feito de graca em automacao/consultar_jucesp.py, via scraping do portal
publico da JUCESP (sem login, sem custo por consulta), e ja roda em producao
dentro de processar_sp() em backend/atualizar_status.py. Repetir isso aqui via
Infosimples (que cobra por consulta) seria pagar por algo que ja funciona.
Este modulo cobre so o que o portal publico gratuito NAO oferece: ficha
cadastral simplificada/completa, certidao simplificada (documento mais pedido
pelos clientes) e download do documento digitalizado de um ato ja registrado.

Slugs de endpoint CONFIRMADOS empiricamente contra a API real (nao mais um
palpite): o padrao correto e /junta-comercial/sp/{servico} (dois segmentos -
categoria generica "junta-comercial" + UF "sp", igual ao padrao usado por
outros orgaos estaduais na propria doc da Infosimples, ex. /tribunal/trf4/
certidao). Testado em 30/07/2026: os 4 slugs abaixo retornam code
606/608/615/620 (erro de parametro/credencial/servico pausado/site-origem)
em vez de 602 ("servico informado na URL nao e valido") - ou seja, o
servidor reconhece os 4 paths como validos.

PENDENTE - login JUCESP (INFOSIMPLES_CPF/INFOSIMPLES_SENHA_NFP no .env) ainda
nao produziu uma consulta 200 de verdade: a credencial ja foi trocada uma vez
(confirmado via hash MD5 na resposta da API, valor mudou de fato) mas
"junta-comercial/sp/simplifica" ainda devolveu "O cadastro do usuario foi
bloqueado" (ERL0003100) mesmo com a credencial nova - ou o novo CPF/senha
tambem esta incorreto, ou o bloqueio e' no cadastro GOV.BR em si (nao na
senha) e precisa ser desbloqueado la antes de qualquer consulta funcionar.
"junta-comercial/sp/ficha" testado separadamente devolveu code 615 ("API
pausada temporariamente" - pausa do lado da Infosimples, nao chega a testar
login) - resultado inconclusivo quanto a credencial, nao confirma nem
descarta o bloqueio. Os nomes exatos dos campos de resposta (ficha_emitida,
certidao_emitida, digitalizacao) permanecem NAO confirmados ate uma consulta
200 real - ver ressalva nas funcoes abaixo. Cada chamada de teste e' cobrada
(~R$0,26 observado) - evitar tentativas repetidas sem necessidade.
"""
import requests

BASE_URL = "https://api.infosimples.com/api/v2/consultas"

ENDPOINT_FICHA_SIMPLIFICADA = "junta-comercial/sp/ficha"
ENDPOINT_FICHA_COMPLETA = "junta-comercial/sp/completa"
ENDPOINT_DOWNLOAD_DOCUMENTO = "junta-comercial/sp/download-dc"
ENDPOINT_CERTIDAO_SIMPLIFICADA = "junta-comercial/sp/simplifica"

TIMEOUT_REQUISICAO = 120


def _chamar(endpoint, params, timeout=TIMEOUT_REQUISICAO):
    """POST generico no padrao de resposta da Infosimples: envelope JSON com
    code, code_message, data (lista), data_count, errors. code 200 = sucesso.
    Retorna {"dados": data[0]} ou {"erro": "..."}."""
    try:
        r = requests.post(BASE_URL + "/" + endpoint, data=params, timeout=timeout)
        resposta = r.json()
    except Exception as e:
        return {"erro": "falha na requisicao: " + str(e)[:150]}
    if resposta.get("code") != 200:
        msg = resposta.get("code_message") or resposta.get("errors") or "erro desconhecido"
        return {"erro": str(msg)[:200]}
    dados = resposta.get("data") or []
    if not dados:
        return {"erro": "resposta sem dados"}
    return {"dados": dados[0]}


def _baixar_arquivo(url, destino_path):
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(destino_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print("   [SP-Infosimples] erro ao baixar arquivo do link retornado:", str(e)[:150])
        return False


def baixar_ficha_cadastral(nire, token, cpf, senha_nfp, destino_path, tipo="simplificada"):
    """Baixa a Ficha Cadastral da JUCESP via Infosimples e salva o PDF em
    destino_path. Retorna True/False.

    Padrao e 'simplificada': cobre os dados cadastrais atuais (endereco,
    capital, participantes, objeto social) que bastam pra confirmar
    existencia/dados basicos da empresa. A 'completa' traz historico desde
    1992 via OCR/RPA, custa mais caro por consulta e demora mais - so
    compensa se um dia precisarmos do historico de alteracoes, nao so o
    estado atual.
    """
    endpoint = ENDPOINT_FICHA_COMPLETA if tipo == "completa" else ENDPOINT_FICHA_SIMPLIFICADA
    params = {"token": token, "nire": nire, "login_cpf": cpf, "login_senha": senha_nfp}
    print("   [SP-Infosimples] consultando ficha cadastral (" + tipo + ") - NIRE " + str(nire))
    resultado = _chamar(endpoint, params)
    if resultado.get("erro"):
        print("   [SP-Infosimples] erro ficha cadastral:", resultado["erro"])
        return False
    dados = resultado["dados"]
    url_pdf = dados.get("ficha_emitida") or dados.get("arquivo") or dados.get("pdf")
    if not url_pdf:
        print("   [SP-Infosimples] resposta sem link de PDF reconhecido, campos recebidos:", list(dados.keys()))
        return False
    return _baixar_arquivo(url_pdf, destino_path)


def baixar_certidao_simplificada(nire, token, cpf, senha_nfp, destino_path):
    """Emite a Certidao Simplificada da JUCESP via Infosimples e salva o PDF em
    destino_path. Retorna True/False.

    Diferente da ficha cadastral (uso mais pontual/interno), a certidao e o
    documento mais pedido pelos clientes: serve como prova formal de
    existencia/regularidade da empresa perante terceiros (bancos, orgaos
    publicos, contratos).

    Confirmado na doc publica (infosimples.com/consultas/junta-comercial-sp-
    simplifica/): parametros de login (nire/login_cpf/login_senha, mesmos das
    outras funcoes) e o campo de resposta 'certidao_emitida' (contem o link do
    PDF - mesmo padrao de 'ficha_emitida' na ficha cadastral). O slug exato do
    endpoint de API (ENDPOINT_CERTIDAO_SIMPLIFICADA acima) segue nao confirmado
    tecnicamente, mesma ressalva do topo do arquivo - so a doc publica (sem
    login) foi consultada.
    """
    params = {"token": token, "nire": nire, "login_cpf": cpf, "login_senha": senha_nfp}
    print("   [SP-Infosimples] emitindo certidao simplificada - NIRE " + str(nire))
    resultado = _chamar(ENDPOINT_CERTIDAO_SIMPLIFICADA, params)
    if resultado.get("erro"):
        print("   [SP-Infosimples] erro certidao simplificada:", resultado["erro"])
        return False
    dados = resultado["dados"]
    url_pdf = dados.get("certidao_emitida") or dados.get("arquivo") or dados.get("pdf")
    if not url_pdf:
        print("   [SP-Infosimples] resposta sem link de PDF reconhecido, campos recebidos:", list(dados.keys()))
        return False
    return _baixar_arquivo(url_pdf, destino_path)


def baixar_documento(nire, numero_registro, token, cpf, senha_nfp, destino_path):
    """Baixa o Documento Digitalizado de um ato ja registrado na JUCESP (por
    NIRE + numero de registro) via Infosimples e salva em destino_path.
    Retorna True/False."""
    params = {
        "token": token,
        "nire": nire,
        "registro": numero_registro,
        "login_cpf": cpf,
        "login_senha": senha_nfp,
    }
    print("   [SP-Infosimples] baixando documento - NIRE " + str(nire) + " registro " + str(numero_registro))
    resultado = _chamar(ENDPOINT_DOWNLOAD_DOCUMENTO, params)
    if resultado.get("erro"):
        print("   [SP-Infosimples] erro download documento:", resultado["erro"])
        return False
    dados = resultado["dados"]
    url_pdf = dados.get("digitalizacao") or dados.get("arquivo") or dados.get("pdf")
    if not url_pdf:
        print("   [SP-Infosimples] resposta sem link de PDF reconhecido, campos recebidos:", list(dados.keys()))
        return False
    return _baixar_arquivo(url_pdf, destino_path)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv("/root/atos/.env")
    TOKEN = os.getenv("INFOSIMPLES_TOKEN")
    CPF = os.getenv("INFOSIMPLES_CPF")
    SENHA_NFP = os.getenv("INFOSIMPLES_SENHA_NFP")
    if not all([TOKEN, CPF, SENHA_NFP]):
        print("Credenciais INFOSIMPLES_TOKEN/INFOSIMPLES_CPF/INFOSIMPLES_SENHA_NFP ausentes no .env.")
    else:
        ok = baixar_ficha_cadastral("35215861263", TOKEN, CPF, SENHA_NFP, "/tmp/ficha_teste_infosimples.pdf")
        print("Ficha cadastral baixada:", ok)
