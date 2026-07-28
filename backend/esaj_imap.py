"""Monitora uma caixa IMAP em busca de emails do e-SAJ TJSP com certidoes,
baixa o PDF anexado, renomeia (certidao_{numero_processo}_{data}.pdf) e
reenvia aos destinatarios da Enel via SMTP Brevo (mesma funcao usada em
main.py/atualizar_status.py). Roda uma vez por execucao (oneshot) - a
periodicidade fica a cargo do systemd timer, no mesmo padrao de
atos-sla.service/atos-consulta.service.

So marca como processado (move para a pasta de destino) DEPOIS de concluir
o reenvio, entao uma falha no meio do processamento deixa o email intacto
na caixa de entrada para ser tentado de novo na proxima execucao.
"""

import imaplib
import email
import logging
import os
import re
import sys
from datetime import datetime
from email.header import decode_header
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from main import enviar_email_anexo  # noqa: E402  (precisa do .env carregado antes)

IMAP_HOST = os.getenv("ESAJ_IMAP_HOST")
IMAP_PORT = int(os.getenv("ESAJ_IMAP_PORT", "993"))
IMAP_USER = os.getenv("ESAJ_IMAP_USER")
IMAP_PASS = os.getenv("ESAJ_IMAP_PASS")
PASTA_ORIGEM = os.getenv("ESAJ_IMAP_PASTA_ORIGEM", "INBOX")
PASTA_PROCESSADOS = os.getenv("ESAJ_IMAP_PASTA_PROCESSADOS", "Processados")
REMETENTE_FILTRO = os.getenv("ESAJ_REMETENTE_FILTRO", "").strip()
ASSUNTO_FILTRO = os.getenv("ESAJ_ASSUNTO_FILTRO", "certidão").strip()
DESTINATARIOS_ENEL = [
    e.strip() for e in os.getenv("ESAJ_DESTINATARIOS_ENEL", "").split(",") if e.strip()
]

CERTIDOES_DIR = os.path.join(BASE_DIR, "uploads", "esaj_certidoes")
os.makedirs(CERTIDOES_DIR, exist_ok=True)

logger = logging.getLogger("esaj_imap")
logger.setLevel(logging.INFO)
_handler = RotatingFileHandler(
    os.path.join(BASE_DIR, "esaj_imap.log"), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_handler)
logger.addHandler(logging.StreamHandler())

CNJ_REGEX = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def _decodificar(valor):
    if not valor:
        return ""
    partes = decode_header(valor)
    saida = ""
    for texto, cod in partes:
        if isinstance(texto, bytes):
            saida += texto.decode(cod or "utf-8", errors="replace")
        else:
            saida += texto
    return saida


def _extrair_numero_processo(assunto, corpo):
    m = CNJ_REGEX.search(assunto or "")
    if m:
        return m.group(0)
    m = CNJ_REGEX.search(corpo or "")
    if m:
        return m.group(0)
    return "SEM-NUMERO"


def _corpo_texto(msg):
    if msg.is_multipart():
        for parte in msg.walk():
            if parte.get_content_type() == "text/plain" and not parte.get("Content-Disposition"):
                try:
                    return parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


def _anexos_pdf(msg):
    anexos = []
    for parte in msg.walk():
        nome = parte.get_filename()
        if not nome:
            continue
        nome = _decodificar(nome)
        if nome.lower().endswith(".pdf"):
            conteudo = parte.get_payload(decode=True)
            if conteudo:
                anexos.append((nome, conteudo))
    return anexos


def _salvar_pdf(conteudo, numero_processo, data_email):
    data_str = data_email.strftime("%Y%m%d")
    base_nome = f"certidao_{numero_processo}_{data_str}.pdf"
    caminho = os.path.join(CERTIDOES_DIR, base_nome)
    sufixo = 2
    while os.path.exists(caminho):
        base_nome = f"certidao_{numero_processo}_{data_str}_{sufixo}.pdf"
        caminho = os.path.join(CERTIDOES_DIR, base_nome)
        sufixo += 1
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho, base_nome


def _mover_para_processados(imap, num_msg):
    try:
        imap.select(PASTA_ORIGEM)
        resultado = imap.copy(num_msg, PASTA_PROCESSADOS)
        if resultado[0] != "OK":
            imap.create(PASTA_PROCESSADOS)
            resultado = imap.copy(num_msg, PASTA_PROCESSADOS)
        if resultado[0] == "OK":
            imap.store(num_msg, "+FLAGS", "\\Deleted")
            return True
        logger.warning("Nao foi possivel copiar msg %s para %s: %s", num_msg, PASTA_PROCESSADOS, resultado)
    except Exception as e:
        logger.warning("Erro ao mover msg %s para %s: %s", num_msg, PASTA_PROCESSADOS, e)
    return False


def _montar_criterio_busca():
    criterios = ["UNSEEN"]
    if REMETENTE_FILTRO:
        criterios += ["FROM", f'"{REMETENTE_FILTRO}"']
    if ASSUNTO_FILTRO:
        criterios += ["SUBJECT", f'"{ASSUNTO_FILTRO}"']
    return criterios


def processar_caixa():
    if not (IMAP_HOST and IMAP_USER and IMAP_PASS):
        logger.error("ESAJ_IMAP_HOST/USER/PASS nao configurados no .env - abortando.")
        return

    logger.info("Conectando em %s:%s como %s", IMAP_HOST, IMAP_PORT, IMAP_USER)
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        imap.login(IMAP_USER, IMAP_PASS)
        imap.select(PASTA_ORIGEM)

        status, dados = imap.search(None, *_montar_criterio_busca())
        if status != "OK":
            logger.error("Falha na busca IMAP: %s", status)
            return
        ids = dados[0].split()
        logger.info("%d email(s) novo(s) encontrados.", len(ids))

        expunge_necessario = False
        for num_msg in ids:
            try:
                status, msg_dados = imap.fetch(num_msg, "(RFC822)")
                if status != "OK":
                    logger.warning("Falha ao buscar msg %s", num_msg)
                    continue
                msg = email.message_from_bytes(msg_dados[0][1])
                assunto = _decodificar(msg.get("Subject"))
                corpo = _corpo_texto(msg)
                data_email = email.utils.parsedate_to_datetime(msg.get("Date")) or datetime.now()
                numero_processo = _extrair_numero_processo(assunto, corpo)

                pdfs = _anexos_pdf(msg)
                if not pdfs:
                    logger.info("Msg %s (%s) sem anexo PDF - ignorando, marcando como lida.", num_msg, assunto)
                    imap.store(num_msg, "+FLAGS", "\\Seen")
                    continue

                enviados_ok = True
                for nome_original, conteudo in pdfs:
                    caminho, nome_final = _salvar_pdf(conteudo, numero_processo, data_email)
                    logger.info("Certidao salva: %s (processo %s, origem %s)", nome_final, numero_processo, nome_original)

                    if not DESTINATARIOS_ENEL:
                        logger.warning("ESAJ_DESTINATARIOS_ENEL vazio - certidao salva mas nao reenviada.")
                        continue
                    for destinatario in DESTINATARIOS_ENEL:
                        ok = enviar_email_anexo(
                            destinatario,
                            f"Certidao e-SAJ TJSP - Processo {numero_processo}",
                            f"Segue em anexo a certidao do processo {numero_processo}, "
                            f"encaminhada automaticamente a partir do e-SAJ TJSP.",
                            caminho,
                            nome_final,
                        )
                        if not ok:
                            enviados_ok = False
                            logger.error("Falha ao reenviar %s para %s", nome_final, destinatario)

                if enviados_ok:
                    if _mover_para_processados(imap, num_msg):
                        expunge_necessario = True
                    else:
                        imap.store(num_msg, "+FLAGS", "\\Seen")
                else:
                    logger.warning("Msg %s nao movida para processados por falha no reenvio - sera tentada de novo.", num_msg)
            except Exception as e:
                logger.exception("Erro processando msg %s: %s", num_msg, e)

        if expunge_necessario:
            imap.select(PASTA_ORIGEM)
            imap.expunge()
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()

    logger.info("Execucao concluida.")


if __name__ == "__main__":
    processar_caixa()
