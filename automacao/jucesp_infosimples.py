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

CONFIRMADO PONTA A PONTA em 30/07/2026: "junta-comercial/sp/ficha" retornou
code 200 com dados reais (NIRE 35225626798, OTA HOLD BRASIL PARTICIPACOES
LTDA) apos corrigir a credencial de login - INFOSIMPLES_SENHA_NFP e' na
verdade a SENHA DO GOV.BR (login federado), nao uma senha separada da Nota
Fiscal Paulista - nome da variavel ficou como estava por continuidade, mas
o valor certo e' a senha do GOV.BR da mesma pessoa do INFOSIMPLES_CPF.

Campo do PDF confirmado: data[0]["site_receipt"] (URL terminada em .pdf,
baixado e validado - comeca com a assinatura %PDF-). NAO e' "ficha_emitida"
(esse campo e' booleano, so indica que a ficha foi emitida) nem "arquivo"/
"pdf" como o codigo assumia antes de confirmar - mantidos como fallback por
seguranca, mas "site_receipt" e' o campo real. Os outros 3 servicos (completa,
simplifica, download-dc) ainda nao tiveram uma consulta 200 real - assumindo
o mesmo campo "site_receipt" por ser um padrao generico da Infosimples (visto
tambem no header de respostas de erro de outros servicos), mas isso e' uma
extrapolacao, nao confirmacao direta pra esses 3.
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
    url_pdf = dados.get("site_receipt") or dados.get("arquivo") or dados.get("pdf")
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

    Endpoint confirmado (junta-comercial/sp/simplifica), mas ainda sem uma
    consulta 200 real neste servico especifico - ver ressalva no topo do
    arquivo. Assume-se o mesmo campo 'site_receipt' confirmado em
    baixar_ficha_cadastral (padrao generico da Infosimples), por extrapolacao.
    """
    params = {"token": token, "nire": nire, "login_cpf": cpf, "login_senha": senha_nfp}
    print("   [SP-Infosimples] emitindo certidao simplificada - NIRE " + str(nire))
    resultado = _chamar(ENDPOINT_CERTIDAO_SIMPLIFICADA, params)
    if resultado.get("erro"):
        print("   [SP-Infosimples] erro certidao simplificada:", resultado["erro"])
        return False
    dados = resultado["dados"]
    url_pdf = dados.get("site_receipt") or dados.get("certidao_emitida") or dados.get("arquivo") or dados.get("pdf")
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
    url_pdf = dados.get("site_receipt") or dados.get("digitalizacao") or dados.get("arquivo") or dados.get("pdf")
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
