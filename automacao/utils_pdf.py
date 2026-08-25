# -*- coding: utf-8 -*-
"""Validacao de PDF gerado/baixado por automacao. Criado 24/08/2026 apos
o caso da Guia Bancaria JUCERJA salvar uma pagina HTML de erro/impressao
como se fosse PDF (extensao .pdf, conteudo HTML) - o anexo enviado por
email nao abria. Usa PyMuPDF (fitz), ja instalado no projeto (nao
adiciona dependencia nova), em vez de pypdf."""
import os
import fitz  # PyMuPDF


def validar_pdf(caminho):
    """Retorna (True, None) se `caminho` for um PDF valido e abrivel, ou
    (False, motivo) caso contrario. Nunca levanta excecao."""
    try:
        if not os.path.exists(caminho):
            return False, "arquivo nao existe"

        tamanho = os.path.getsize(caminho)
        if tamanho < 1024:
            return False, "arquivo muito pequeno (" + str(tamanho) + " bytes, minimo 1024)"

        with open(caminho, "rb") as f:
            inicio = f.read(5)
            f.seek(-min(1024, tamanho), os.SEEK_END)
            fim = f.read()

        if inicio != b"%PDF-":
            return False, "assinatura invalida no inicio do arquivo (esperado %PDF-, encontrado " + repr(inicio) + ")"

        if b"%%EOF" not in fim:
            return False, "marcador %%EOF nao encontrado no final do arquivo (download possivelmente truncado)"

        try:
            doc = fitz.open(caminho)
            n_paginas = doc.page_count
            doc.close()
        except Exception as e:
            return False, "PyMuPDF nao conseguiu abrir o arquivo: " + str(e)[:200]

        if n_paginas < 1:
            return False, "PDF abriu mas tem 0 paginas"

        return True, None
    except Exception as e:
        return False, "erro inesperado na validacao: " + str(e)[:200]


def primeiros_bytes_legivel(caminho, n=200):
    """Retorna os primeiros `n` bytes do arquivo em formato legivel (texto
    se decodificar como utf-8, senao repr dos bytes) - pra diagnostico em
    logs/alertas quando a validacao falha."""
    try:
        with open(caminho, "rb") as f:
            dados = f.read(n)
        try:
            return dados.decode("utf-8", errors="replace")
        except Exception:
            return repr(dados)
    except Exception as e:
        return "(nao foi possivel ler o arquivo: " + str(e)[:100] + ")"


def sanear_pdf(caminho):
    """Corrige o padrao de corrupcao encontrado 24/08/2026 nos downloads da
    JUCEB e JUCEPE: o PDF real vem completo (com %PDF- e %%EOF validos),
    mas o servidor (bug tipico de ASP.NET WebForms - Response.BinaryWrite
    sem Response.End()/CompleteRequest()) continua escrevendo o HTML normal
    da pagina LOGO DEPOIS do %%EOF, no mesmo arquivo. Trunca tudo depois do
    ultimo %%EOF, SE e' um caso seguro de aparar (tem %PDF- no inicio e
    sobra conteudo depois do EOF) - nunca mexe em arquivo sem cabecalho
    %PDF- valido (isso e' o caso "HTML puro" da guia bancaria JUCERJA,
    tratamento totalmente diferente, sem PDF nenhum pra recuperar).

    Retorna True se aparou algo (ou se o arquivo ja estava limpo), False se
    nao e' um caso aplicavel (sem %PDF- valido pra comecar)."""
    try:
        with open(caminho, "rb") as f:
            dados = f.read()
    except Exception:
        return False

    if not dados.startswith(b"%PDF-"):
        return False

    idx = dados.rfind(b"%%EOF")
    if idx == -1:
        return False

    fim_real = idx + len(b"%%EOF")
    if fim_real >= len(dados):
        return True  # ja estava limpo

    with open(caminho, "wb") as f:
        f.write(dados[:fim_real])
    return True


def quarentena(caminho):
    """Move um PDF invalido pra um nome com sufixo .invalido + timestamp
    (mesma pasta), preservando o conteudo pra diagnostico. Retorna o novo
    caminho, ou None se o arquivo nao existir ou o move falhar."""
    import datetime
    if not os.path.exists(caminho):
        return None
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        novo_caminho = caminho + ".invalido." + ts
        os.rename(caminho, novo_caminho)
        return novo_caminho
    except Exception:
        return None
