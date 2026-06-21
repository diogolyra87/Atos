# -*- coding: utf-8 -*-
import sys, os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, "/root/atos/backend")
from database import SessionLocal, Processo, Grupo, EmailGrupo
from consultar_jucesp import consultar

load_dotenv("/root/atos/.env")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_HOST = os.getenv("EMAIL_HOST", "mail.realpublicidade.com.br")
EMAIL_PORT_SMTP = int(os.getenv("EMAIL_PORT_SMTP", "587"))

EMAIL_ADMIN = "diogo@realpublicidade.com.br"
BASE_URL = "https://atos.net.br"

INTERVALO_NORMAL = timedelta(hours=24)
INTERVALO_AGUARDANDO = timedelta(days=7)


def enviar_email(destinatario, assunto, corpo):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain"))
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT_SMTP)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("   [ERRO email para", destinatario, "]:", e)
        return False


def emails_do_grupo(db, grupo_id):
    regs = db.query(EmailGrupo).filter(EmailGrupo.grupo_id == grupo_id).all()
    return [r.email for r in regs if r.email]


def precisa_alertar(p, agora):
    if not p.ultimo_alerta_em:
        return True
    intervalo = INTERVALO_AGUARDANDO if p.aguardando_cliente else INTERVALO_NORMAL
    return (agora - p.ultimo_alerta_em) >= intervalo


def corpo_admin(p, status_label):
    ato = p.identificador_ato or p.tipo_ato or ""
    return "Empresa: " + (p.empresa or "") + "\nAto: " + ato + "\nStatus: " + status_label + "\n\nProtocolo: " + (p.numero_protocolo or "")


def processar():
    db = SessionLocal()
    agora = datetime.now()
    processos = db.query(Processo).filter(
        Processo.uf == "SP",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    print("[" + str(agora) + "] " + str(len(processos)) + " processo(s) SP com protocolo.\n")

    for p in processos:
        status_atual = (p.status or "").lower()
        if status_atual == "finalizado":
            continue

        print("-> " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status atual: " + status_atual)
        try:
            resultado = consultar(p.numero_protocolo)
        except Exception as e:
            print("   ERRO consulta (mantem status):", e)
            continue

        if not resultado:
            print("   JUCESP vazio (mantem status).")
            continue

        print("   JUCESP:", resultado)
        p.status_jucesp = resultado
        p.ultima_consulta_em = agora
        r = resultado.upper()

        if r == "EXIGENCIA":
            if status_atual != "exigencia":
                p.status = "exigencia"
                p.exigencia_ativa = True
                p.aguardando_cliente = False
                p.ultimo_alerta_em = agora
                db.commit()
                enviar_email(EMAIL_ADMIN, "[Atos] Exigencia - " + str(p.empresa), corpo_admin(p, "Exigencia"))
                print("   -> mudou para EXIGENCIA + alertou admin")
            else:
                if precisa_alertar(p, agora):
                    p.ultimo_alerta_em = agora
                    db.commit()
                    enviar_email(EMAIL_ADMIN, "[Atos] Exigencia (lembrete) - " + str(p.empresa), corpo_admin(p, "Exigencia"))
                    print("   -> lembrete de exigencia ao admin")
                else:
                    db.commit()
                    print("   -> exigencia ainda no intervalo, sem novo email")

        elif r == "DEFERIDO":
            if status_atual != "deferido":
                p.status = "deferido"
                p.exigencia_ativa = False
                p.ultimo_alerta_em = agora
                db.commit()
                enviar_email(EMAIL_ADMIN, "[Atos] Deferido - " + str(p.empresa), corpo_admin(p, "Deferido"))
                if not p.avisado_deferido:
                    for em in emails_do_grupo(db, p.grupo_id):
                        enviar_email(em, "Atualizacao do seu processo - " + str(p.empresa), "Documento Deferido, aguardando liberacao do Registro.")
                    p.avisado_deferido = True
                    db.commit()
                print("   -> mudou para DEFERIDO + alertou admin e cliente")
            else:
                if precisa_alertar(p, agora):
                    p.ultimo_alerta_em = agora
                    db.commit()
                    enviar_email(EMAIL_ADMIN, "[Atos] Deferido (lembrete) - " + str(p.empresa), corpo_admin(p, "Deferido"))
                    print("   -> lembrete de deferido ao admin")
                else:
                    db.commit()
                    print("   -> deferido ainda no intervalo, sem novo email")

        else:
            if status_atual not in ("tramitacao", "exigencia", "deferido"):
                p.status = "tramitacao"
            db.commit()
            print("   -> tramitacao (mantido)")

        print()

    db.close()
    print("FIM.")


if __name__ == "__main__":
    processar()
