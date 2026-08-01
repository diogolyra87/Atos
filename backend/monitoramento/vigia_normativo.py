# -*- coding: utf-8 -*-
"""Vigia normativo (Parte B do Assistente ATOS): job semanal que monitora as
fontes juridicas/administrativas listadas em fontes_monitoramento_normativo,
detecta mudanca de conteudo (hash), classifica o impacto via Gemini em 3
niveis, e aplica automaticamente (Nivel 1/2, com log) ou escala pro Telegram
com botoes de aprovacao (Nivel 3) - nunca edita o arquivo de base de
conhecimento sem rastro no changelog.

Rodado via systemd timer (atos-vigia-normativo.timer), toda segunda 6h.
"""
import os
import sys
import re
import json
import uuid
import hashlib
import difflib
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # backend/monitoramento
BACKEND_DIR = os.path.dirname(BASE_DIR)                         # backend/
REPO_DIR = os.path.dirname(BACKEND_DIR)                         # raiz do repo (D:\Mane ou /root/atos)
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(REPO_DIR, ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from database import SessionLocal, FonteMonitoramentoNormativo, MudancaNormativaPendente, LogAtualizacaoNormativa
from main import GEMINI_KEY, notificar_telegram, notificar_telegram_com_botoes

BASE_CONHECIMENTO_PATH = os.path.join(REPO_DIR, "docs", "base_conhecimento_atos_registros_juntas.md")

# -------------------- seed inicial das fontes (secao 7.2/9 do documento) --------------------
# Todas as URLs abaixo vem literalmente da secao 9 (Fontes primarias consolidadas) ou 5.4
# (Onde encontrar as tabelas oficiais) do base_conhecimento - nao inventadas. Quando o
# documento nao trouxe uma URL de pagina especifica pra uma Junta (so o dominio geral),
# isso fica marcado no nome da fonte com "(dominio geral)" pra revisao futura.
FONTES_SEED = [
    {"nome": "DREI - Instrucoes Normativas (IN 81/2020 atualizada)", "url": "https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao", "tipo": "drei", "estado": None},
    {"nome": "DOU - Consulta (Ministerio do Empreendedorismo)", "url": "https://www.in.gov.br/consulta/-/buscar/dou", "tipo": "dou", "estado": None},
    {"nome": "CVM - Portal (normas e resolucoes)", "url": "https://www.gov.br/cvm/pt-br", "tipo": "cvm", "estado": None},
    {"nome": "JUCERJA - Tabela de Emolumentos", "url": "https://www.jucerja.rj.gov.br/Informacoes/TabelaPrecos", "tipo": "junta_estadual", "estado": "RJ"},
    {"nome": "JUCESP - Downloads/Tabela de Precos", "url": "https://institucional.jucesp.sp.gov.br/downloads/", "tipo": "junta_estadual", "estado": "SP"},
    {"nome": "JUCEB - Tabela de Precos Capital", "url": "https://www.ba.gov.br/juceb/tabelas-de-precos-capital", "tipo": "junta_estadual", "estado": "BA"},
    {"nome": "JUCEMG - Tabela de Precos", "url": "https://jucemg.mg.gov.br/pagina/52/tabela-de-precos", "tipo": "junta_estadual", "estado": "MG"},
    {"nome": "JUCEPE (dominio geral)", "url": "https://www.jucepe.pe.gov.br", "tipo": "junta_estadual", "estado": "PE"},
    {"nome": "JucisRS - Tabela de Precos", "url": "https://jucisrs.rs.gov.br/tabela-de-precos", "tipo": "junta_estadual", "estado": "RS"},
    {"nome": "JUCESC - Base de Conhecimento (Atendimento)", "url": "https://atendimento.jucesc.sc.gov.br/help", "tipo": "junta_estadual", "estado": "SC"},
    {"nome": "JUCEPAR (dominio geral)", "url": "https://www.juntacomercial.pr.gov.br", "tipo": "junta_estadual", "estado": "PR"},
    {"nome": "JUCEG (dominio geral)", "url": "https://www.goias.gov.br/juceg", "tipo": "junta_estadual", "estado": "GO"},
    {"nome": "JUCEC - Tabela de Precos", "url": "https://jucec.ce.gov.br/tabela-de-precos/", "tipo": "junta_estadual", "estado": "CE"},
    {"nome": "JUCEMS (dominio geral)", "url": "https://www.jucems.ms.gov.br", "tipo": "junta_estadual", "estado": "MS"},
    {"nome": "JUCIS-DF (dominio geral)", "url": "https://jucis.df.gov.br", "tipo": "junta_estadual", "estado": "DF"},
]


def garantir_fontes_seed(db):
    """Popula fontes_monitoramento_normativo na primeira execucao (idempotente -
    nao duplica se ja existir fonte com a mesma URL)."""
    existentes = set(u for (u,) in db.query(FonteMonitoramentoNormativo.url).all())
    novas = 0
    for f in FONTES_SEED:
        if f["url"] in existentes:
            continue
        db.add(FonteMonitoramentoNormativo(
            id=str(uuid.uuid4()), nome_fonte=f["nome"], url=f["url"],
            tipo=f["tipo"], estado=f["estado"], ativo=True,
        ))
        novas += 1
    if novas:
        db.commit()
    return novas


def log_acao(db, fonte_id, acao, nivel=None, detalhe=None):
    db.add(LogAtualizacaoNormativa(
        id=str(uuid.uuid4()), fonte_id=fonte_id, acao=acao, nivel=nivel,
        detalhe=(detalhe or "")[:4000],
    ))
    db.commit()


def extrair_texto_pagina(url):
    import requests
    r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0 (compatible; AtosVigiaNormativo/1.0)"})
    r.raise_for_status()
    texto = r.text
    texto = re.sub(r"<script.*?</script>", " ", texto, flags=re.S | re.I)
    texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.S | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"&nbsp;|&amp;|&quot;|&#\d+;", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def calcular_hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _gemini_classificar(prompt):
    import urllib.request
    if not GEMINI_KEY:
        return None
    try:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" + GEMINI_KEY
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=40)
        data = json.loads(resp.read().decode())
        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        print("Erro Gemini (classificador vigia normativo):", str(e)[:200])
        return None


def classificar_mudanca(fonte, texto_antigo, texto_novo):
    """Pede ao Gemini pra classificar o diff em Nivel 1/2/3, conforme os
    criterios da secao 7.1 do base_conhecimento (arquitetura de 3 niveis)."""
    diff = "\n".join(list(difflib.unified_diff(
        (texto_antigo or "")[:6000].split(". "),
        (texto_novo or "")[:6000].split(". "),
        lineterm="", n=1,
    ))[:200])
    prompt = f"""Voce e o classificador do "vigia normativo" do sistema ATOS. Uma fonte oficial
monitorada mudou de conteudo. Classifique o impacto dessa mudanca em um dos 3 niveis:

NIVEL 1 - Automatico, sem revisao: mudanca factual/estrutural clara e nao-ambigua
(URL mudou, valor numerico de taxa mudou em tabela oficial, codigo de evento substituido).
NIVEL 2 - Automatico, com log: mudanca normativa (nova IN, nova Resolucao) que voce consegue
mapear com ALTA confianca pra uma secao especifica da base, citando o trecho legal exato.
NIVEL 3 - Retido para revisao humana: mudanca ambigua, conflito entre fontes, ou baixa
confianca no mapeamento do impacto. Use Nivel 3 sempre que nao tiver certeza.

FONTE: {fonte.nome_fonte} ({fonte.url})

DIFF DETECTADO (formato unified diff, "-" = versao anterior, "+" = versao nova):
{diff if diff.strip() else "(nao foi possivel gerar diff legivel - avalie como Nivel 3 por seguranca)"}

Responda APENAS com um JSON no formato exato:
{{"nivel": 1 | 2 | 3, "secao_afetada": "titulo aproximado da secao do documento afetada (ex: 'PARTE IV - Taxas/Emolumentos') ou null se nao souber", "trecho_sugerido": "texto curto pronto pra inserir na base, com a atualizacao (ou null se Nivel 3)", "justificativa": "1-2 frases explicando a classificacao"}}"""
    return _gemini_classificar(prompt)


def _carregar_secoes_arquivo():
    with open(BASE_CONHECIMENTO_PATH, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    secoes = []  # cada item: {"titulo", "inicio_idx", "fim_idx"} (indices em `linhas`)
    titulo_atual, inicio = None, None
    for i, linha in enumerate(linhas):
        if linha.startswith("### ") or linha.startswith("## "):
            if titulo_atual is not None:
                secoes.append({"titulo": titulo_atual, "inicio": inicio, "fim": i})
            titulo_atual = linha.lstrip("#").strip()
            inicio = i
    if titulo_atual is not None:
        secoes.append({"titulo": titulo_atual, "inicio": inicio, "fim": len(linhas)})
    return linhas, secoes


def _normalizar(txt):
    import unicodedata
    t = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _achar_secao(secoes, secao_afetada):
    if not secao_afetada:
        return None
    alvo = _normalizar(secao_afetada)
    palavras_alvo = set(w for w in re.split(r"\W+", alvo) if len(w) > 3)
    melhor, melhor_pontos = None, 0
    for s in secoes:
        titulo_norm = _normalizar(s["titulo"])
        pontos = sum(1 for w in palavras_alvo if w in titulo_norm)
        if pontos > melhor_pontos:
            melhor, melhor_pontos = s, pontos
    return melhor if melhor_pontos > 0 else None


def _adicionar_linha_changelog(linhas, data_str, mudanca_desc, responsavel):
    """Insere uma nova linha na tabela de changelog (secao 8), logo apos a
    linha de cabecalho '| Data | Mudanca | Responsavel |' + separador."""
    for i, linha in enumerate(linhas):
        if linha.strip().startswith("| Data") and "Mudan" in linha:
            # proxima linha e o separador |---|---|---|; insere logo depois
            idx_insercao = i + 2
            nova_linha = f"| {data_str} | {mudanca_desc} | {responsavel} |\n"
            linhas.insert(idx_insercao, nova_linha)
            return True
    return False


def aplicar_mudanca_no_arquivo(mudanca, fonte, aprovado_por=None):
    """Edita o base_conhecimento: insere o trecho sugerido logo apos a secao
    afetada (bloco marcado, nunca sobrescreve texto legal existente) e
    adiciona a linha correspondente no changelog. Faz commit local (sem
    push) no git do repo. Retorna True/False."""
    try:
        linhas, secoes = _carregar_secoes_arquivo()
        secao = _achar_secao(secoes, mudanca.secao_afetada)
        data_str = datetime.now().strftime("%d/%m/%Y")
        responsavel = f"Vigia normativo (Nivel {mudanca.nivel}, automatico)" if not aprovado_por else f"Vigia normativo (Nivel {mudanca.nivel}, aprovado manualmente via Telegram por {aprovado_por} em {data_str})"

        bloco = (
            f"\n> **Atualizacao automatica ({data_str}, Nivel {mudanca.nivel})** — fonte: "
            f"[{fonte.nome_fonte}]({fonte.url})\n> {mudanca.trecho_sugerido}\n"
            + (f">\n> *Justificativa: {mudanca.justificativa}*\n" if mudanca.justificativa else "")
        )
        if secao:
            ponto_insercao = secao["fim"]
            linhas.insert(ponto_insercao, bloco)
        else:
            # secao nao identificada - adiciona no fim do documento, marcado, pra revisao
            linhas.append("\n" + bloco)

        mudanca_desc = f"[auto] {fonte.nome_fonte}: {(mudanca.trecho_sugerido or '')[:120]}"
        _adicionar_linha_changelog(linhas, data_str, mudanca_desc, responsavel)

        with open(BASE_CONHECIMENTO_PATH, "w", encoding="utf-8") as f:
            f.writelines(linhas)

        msg_commit = f"[auto] Atualizacao normativa: {fonte.nome_fonte} - Nivel {mudanca.nivel}"
        subprocess.run(["git", "-C", REPO_DIR, "add", "docs/base_conhecimento_atos_registros_juntas.md"], check=False, capture_output=True)
        subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", msg_commit], check=False, capture_output=True)
        return True
    except Exception as e:
        print("Erro ao aplicar mudanca no arquivo:", str(e)[:300])
        return False


def processar_fonte(db, fonte, resumo):
    try:
        texto_novo = extrair_texto_pagina(fonte.url)
    except Exception as e:
        log_acao(db, fonte.id, "verificacao", detalhe="ERRO ao buscar fonte: " + str(e)[:250])
        resumo["erros"].append(fonte.nome_fonte)
        return

    novo_hash = calcular_hash(texto_novo)
    fonte.ultima_verificacao = datetime.now()

    if not fonte.ultimo_snapshot_hash:
        fonte.ultimo_snapshot_hash = novo_hash
        fonte.ultimo_snapshot_texto = texto_novo[:20000]
        db.commit()
        log_acao(db, fonte.id, "verificacao", detalhe="baseline inicial gravado (primeira execucao para esta fonte)")
        resumo["sem_mudanca"] += 1
        return

    if novo_hash == fonte.ultimo_snapshot_hash:
        db.commit()
        log_acao(db, fonte.id, "verificacao", detalhe="sem mudancas")
        resumo["sem_mudanca"] += 1
        return

    texto_antigo = fonte.ultimo_snapshot_texto or ""
    log_acao(db, fonte.id, "verificacao", detalhe="MUDANCA DETECTADA - hash anterior " + fonte.ultimo_snapshot_hash[:16])

    classificacao = classificar_mudanca(fonte, texto_antigo, texto_novo)
    if not classificacao or not classificacao.get("nivel"):
        classificacao = {"nivel": 3, "secao_afetada": None, "trecho_sugerido": None, "justificativa": "Classificador indisponivel - retido por seguranca."}
    nivel = classificacao.get("nivel")
    if nivel not in (1, 2, 3):
        nivel = 3
    log_acao(db, fonte.id, "classificacao", nivel=nivel, detalhe=json.dumps(classificacao, ensure_ascii=False)[:2000])

    diff_texto = "\n".join(list(difflib.unified_diff(
        texto_antigo[:4000].split(". "), texto_novo[:4000].split(". "), lineterm="", n=1))[:150])

    mudanca = MudancaNormativaPendente(
        id=str(uuid.uuid4()), fonte_id=fonte.id, nivel=nivel,
        secao_afetada=classificacao.get("secao_afetada"),
        trecho_sugerido=classificacao.get("trecho_sugerido"),
        justificativa=classificacao.get("justificativa"),
        diff_texto=diff_texto,
        status="pendente",
    )
    db.add(mudanca)
    db.commit()

    if nivel in (1, 2) and mudanca.trecho_sugerido:
        ok = aplicar_mudanca_no_arquivo(mudanca, fonte)
        if ok:
            mudanca.status = "aprovado"
            mudanca.resolvido_por = "automatico"
            mudanca.resolvido_em = datetime.now()
            fonte.ultimo_snapshot_hash = novo_hash
            fonte.ultimo_snapshot_texto = texto_novo[:20000]
            db.commit()
            log_acao(db, fonte.id, "aplicacao", nivel=nivel, detalhe="Aplicado automaticamente e commitado (sem push). Mudanca id=" + mudanca.id)
            resumo["nivel1" if nivel == 1 else "nivel2"].append(fonte.nome_fonte)
        else:
            log_acao(db, fonte.id, "aplicacao", nivel=nivel, detalhe="FALHA ao aplicar mudanca automaticamente - tratando como Nivel 3")
            nivel = 3
            mudanca.nivel = 3
            db.commit()

    if nivel == 3:
        # snapshot so' atualiza apos aprovacao humana (ver bot.py callback) -
        # assim, se ninguem responder, a proxima execucao ainda ve a mesma mudanca pendente
        texto_aviso = (
            "[Vigia Normativo] Mudanca Nivel 3 (revisao necessaria)\n\n"
            f"Fonte: {fonte.nome_fonte}\n{fonte.url}\n\n"
            f"Secao candidata: {mudanca.secao_afetada or '(nao identificada)'}\n"
            f"Motivo: {mudanca.justificativa or '(sem justificativa)'}\n\n"
            f"Diff (trecho):\n{diff_texto[:800]}"
        )
        res = notificar_telegram_com_botoes(texto_aviso, [
            {"texto": "Aprovar e aplicar", "callback_data": "vigia_aprovar:" + mudanca.id},
            {"texto": "Rejeitar", "callback_data": "vigia_rejeitar:" + mudanca.id},
        ])
        if res:
            mudanca.telegram_chat_id, mudanca.telegram_message_id = res
            db.commit()
        log_acao(db, fonte.id, "verificacao", nivel=3, detalhe="Notificacao Telegram enviada, aguardando aprovacao. Mudanca id=" + mudanca.id)
        resumo["nivel3"].append(fonte.nome_fonte)


def enviar_resumo_semanal(db, resumo):
    partes = [
        "[Vigia Normativo] Resumo semanal",
        f"Fontes verificadas: {resumo['verificadas']}",
        f"Sem mudanca: {resumo['sem_mudanca']}",
    ]
    if resumo["nivel1"]:
        partes.append(f"Nivel 1 aplicado automaticamente ({len(resumo['nivel1'])}): " + ", ".join(resumo["nivel1"]))
    if resumo["nivel2"]:
        partes.append(f"Nivel 2 aplicado automaticamente ({len(resumo['nivel2'])}): " + ", ".join(resumo["nivel2"]))
    if resumo["nivel3"]:
        partes.append(f"Nivel 3 pendente de aprovacao ({len(resumo['nivel3'])}): " + ", ".join(resumo["nivel3"]))
    else:
        pendentes = db.query(MudancaNormativaPendente).filter(MudancaNormativaPendente.status == "pendente").count()
        if pendentes:
            partes.append(f"Nivel 3 ainda pendente de execucoes anteriores: {pendentes}")
    if resumo["erros"]:
        partes.append(f"Fontes com erro ao verificar ({len(resumo['erros'])}): " + ", ".join(resumo["erros"]))
    texto = "\n".join(partes)
    notificar_telegram(texto)
    log_acao(db, None, "resumo_semanal", detalhe=texto)


def processar():
    db = SessionLocal()
    novas = garantir_fontes_seed(db)
    if novas:
        print(f"{novas} fonte(s) nova(s) semeada(s) em fontes_monitoramento_normativo.")
    fontes = db.query(FonteMonitoramentoNormativo).filter(FonteMonitoramentoNormativo.ativo == True).all()
    resumo = {"verificadas": 0, "sem_mudanca": 0, "nivel1": [], "nivel2": [], "nivel3": [], "erros": []}
    for fonte in fontes:
        resumo["verificadas"] += 1
        print("Verificando:", fonte.nome_fonte, "-", fonte.url)
        try:
            processar_fonte(db, fonte, resumo)
        except Exception as e:
            print("   ERRO GERAL processando fonte (mantem demais):", str(e)[:200])
            log_acao(db, fonte.id, "verificacao", detalhe="ERRO GERAL: " + str(e)[:250])
            resumo["erros"].append(fonte.nome_fonte)
    enviar_resumo_semanal(db, resumo)
    db.close()
    print("Vigia normativo concluido.", resumo)


if __name__ == "__main__":
    processar()
