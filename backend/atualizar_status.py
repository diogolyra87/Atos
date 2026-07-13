# -*- coding: utf-8 -*-
import sys, os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, "/root/atos/backend")
sys.path.insert(0, "/root/atos/automacao")
from database import SessionLocal, Processo, Grupo, EmailGrupo
sys.path.insert(0, "/root/atos/backend")
from main import corpo_status_cliente, enviar_email_anexo, emails_do_grupo, UPLOADS_DIR, recalcular_status
from consultar_jucesp import consultar
from consultar_jucerja import consultar_jucerja, classificar_status_rj, baixar_documento_jucerja
from consultar_juceb import consultar_juceb, classificar_status_ba, baixar_documento_juceb
from consultar_jucepe import consultar_jucepe, classificar_status_pe, baixar_documento_jucepe
from bot import enviar as enviar_telegram, ADMIN_CHAT_ID

load_dotenv("/root/atos/.env")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_FROM = os.getenv("EMAIL_FROM") or EMAIL_USER
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_HOST = os.getenv("EMAIL_HOST", "mail.realpublicidade.com.br")
EMAIL_PORT_SMTP = int(os.getenv("EMAIL_PORT_SMTP", "587"))

JUCERJA_USUARIO = os.getenv("JUCERJA_USUARIO")
JUCERJA_SENHA = os.getenv("JUCERJA_SENHA")
JUCEB_LOGIN = os.getenv("JUCEB_LOGIN")
JUCEB_SENHA = os.getenv("JUCEB_SENHA")

EMAIL_ADMIN = os.getenv("ADMIN_EMAIL")

def aplicar_nomenclatura_junta(nome_base):
    """Regra padrao de nomenclatura para documentos de registro baixados
    automaticamente das Juntas Comerciais (RJ, BA, PE, e futuras). Se o nome
    contiver 'Sec-Manifesto', troca por 'Sec-Junta'. Caso contrario, adiciona
    '-Junta' antes da extensao. Aplicada uma unica vez, usada tanto no
    salvamento do arquivo quanto no nome do anexo enviado por email - qualquer
    automacao nova que reutilizar essa funcao ja herda a regra automaticamente."""
    if "Sec-Manifesto" in nome_base:
        return nome_base.replace("Sec-Manifesto", "Sec-Junta")
    nome, ext = os.path.splitext(nome_base)
    return nome + "-Junta" + ext
BASE_URL = "https://atos.net.br"

INTERVALO_NORMAL = timedelta(hours=24)
INTERVALO_AGUARDANDO = timedelta(days=7)


def enviar_email(destinatario, assunto, corpo):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Atos - Gestao Societaria <%s>" % EMAIL_FROM
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain"))
        try:
            from main import envolver_html
            msg.attach(MIMEText(envolver_html(corpo), "html"))
        except Exception as _e:
            print("   [aviso html]:", _e)
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


def aplicar_classificacao(db, p, classificacao, agora):
    """classificacao: 'exigencia' | 'deferido' | 'tramitacao'. Mesma logica para SP e RJ."""
    status_atual = (p.status or "").lower()
    p.ultima_consulta_em = agora

    if classificacao == "exigencia":
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

    elif classificacao == "deferido":
        if status_atual != "deferido":
            p.status = "deferido"
            p.exigencia_ativa = False
            p.ultimo_alerta_em = agora
            p.deferido_em = agora
            db.commit()
            enviar_email(EMAIL_ADMIN, "[Atos] Deferido - " + str(p.empresa), corpo_admin(p, "Deferido") + "\n\nAguardando a Junta Comercial disponibilizar o Registro.")
            if not p.avisado_deferido:
                for em in emails_do_grupo(db, p.grupo_id):
                    enviar_email(em, "Atualizacao do seu processo - " + str(p.empresa), corpo_status_cliente(p, "Deferido", "Aguardando liberacao do Registro."))
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


def processar_sp(db, agora):
    processos = db.query(Processo).filter(
        Processo.uf == "SP",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    print("[SP] " + str(len(processos)) + " processo(s) com protocolo.\n")
    for p in processos:
        if (p.status or "").lower() == "finalizado":
            continue
        print("-> [SP] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            resultado = consultar(p.numero_protocolo)
        except Exception as e:
            print("   ERRO consulta JUCESP (mantem):", e)
            continue
        if not resultado:
            print("   JUCESP vazio (mantem status).")
            continue
        print("   JUCESP:", resultado)
        p.status_jucesp = resultado
        r = resultado.upper()
        if r == "EXIGENCIA":
            cls = "exigencia"
        elif r == "DEFERIDO":
            cls = "deferido"
        else:
            cls = "tramitacao"
        aplicar_classificacao(db, p, cls, agora)
        print()


def processar_rj(db, agora):
    processos = db.query(Processo).filter(
        Processo.uf == "RJ",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    pendentes = [p for p in processos if (p.status or "").lower() != "finalizado"]
    print("[RJ] " + str(len(pendentes)) + " processo(s) com protocolo.\n")
    if not pendentes:
        return
    if not JUCERJA_USUARIO or not JUCERJA_SENHA:
        print("   [RJ] credenciais JUCERJA ausentes no .env - pulando RJ.")
        return
    for p in pendentes:
        print("-> [RJ] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            res = consultar_jucerja(p.numero_protocolo, JUCERJA_USUARIO, JUCERJA_SENHA, headless=True)
        except Exception as e:
            print("   ERRO consulta JUCERJA (mantem):", e)
            continue
        if res.get("erro"):
            print("   JUCERJA erro (mantem status):", res["erro"])
            continue
        print("   JUCERJA:", res)
        p.status_jucesp = res.get("status_texto")
        aplicar_classificacao(db, p, res.get("classificacao", "tramitacao"), agora)
        print()
        if "FINALIZADO" in (res.get("status_texto") or "").upper() and not p.arquivo_registro:
            try:
                nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
                caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
                ok_dl = baixar_documento_jucerja(p.numero_protocolo, JUCERJA_USUARIO, JUCERJA_SENHA, caminho, headless=True)
                if ok_dl and os.path.exists(caminho):
                    p.arquivo_registro = nome_arquivo
                    p.status = recalcular_status(p)
                    db.commit()
                    print("   [RJ] documento baixado e processo atualizado para:", p.status)
                    if p.status == "finalizado":
                        try:
                            corpo = corpo_status_cliente(p, "Finalizado", "Seu Processo foi Finalizado, em Anexo o Registro.")
                            for em in emails_do_grupo(db, p.grupo_id):
                                enviar_email_anexo(em, "Processo Finalizado - " + (p.empresa or ""), corpo, caminho, nome_arquivo)
                            print("   [RJ] e-mail de finalizacao enviado.")
                        except Exception as e:
                            print("   [RJ] erro ao enviar e-mail de finalizacao:", e)
                else:
                    print("   [RJ] documento ainda nao disponivel para download (aguardando).")
            except Exception as e:
                print("   [RJ] erro ao baixar documento automaticamente:", e)


def processar_ba(db, agora):
    processos = db.query(Processo).filter(
        Processo.uf == "BA",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    pendentes = [p for p in processos if (p.status or "").lower() != "finalizado"]
    print("[BA] " + str(len(pendentes)) + " processo(s) com protocolo.\n")
    if not pendentes:
        return
    if not JUCEB_LOGIN or not JUCEB_SENHA:
        print("   [BA] credenciais JUCEB ausentes no .env - pulando BA.")
        return
    for p in pendentes:
        print("-> [BA] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            res = consultar_juceb(p.numero_protocolo, JUCEB_LOGIN, JUCEB_SENHA, headless=True)
        except Exception as e:
            print("   ERRO consulta JUCEB (mantem):", e)
            continue
        if res.get("erro"):
            print("   JUCEB erro (mantem status):", res["erro"])
            continue
        print("   JUCEB:", res)
        p.status_jucesp = res.get("status_texto")
        aplicar_classificacao(db, p, res.get("classificacao", "tramitacao"), agora)
        print()
        if "FINALIZADO" in (res.get("status_texto") or "").upper() and not p.arquivo_registro:
            try:
                nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
                caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
                ok_dl = baixar_documento_juceb(p.numero_protocolo, JUCEB_LOGIN, JUCEB_SENHA, caminho, headless=True)
                if ok_dl and os.path.exists(caminho):
                    p.arquivo_registro = nome_arquivo
                    p.status = recalcular_status(p)
                    db.commit()
                    print("   [BA] documento baixado e processo atualizado para:", p.status)
                    if p.status == "finalizado":
                        try:
                            corpo = corpo_status_cliente(p, "Finalizado", "Seu Processo foi Finalizado, em Anexo o Registro.")
                            for em in emails_do_grupo(db, p.grupo_id):
                                enviar_email_anexo(em, "Processo Finalizado - " + (p.empresa or ""), corpo, caminho, nome_arquivo)
                            print("   [BA] e-mail de finalizacao enviado.")
                        except Exception as e:
                            print("   [BA] erro ao enviar e-mail de finalizacao:", e)
                else:
                    print("   [BA] documento ainda nao disponivel para download (aguardando).")
            except Exception as e:
                print("   [BA] erro ao baixar documento automaticamente:", e)


def processar_pe(db, agora):
    processos = db.query(Processo).filter(
        Processo.uf == "PE",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    pendentes = [p for p in processos if (p.status or "").lower() != "finalizado"]
    print("[PE] " + str(len(pendentes)) + " processo(s) com protocolo.\n")
    if not pendentes:
        return
    if not JUCEB_LOGIN or not JUCEB_SENHA:
        print("   [PE] credenciais ausentes no .env - pulando PE.")
        return
    for p in pendentes:
        print("-> [PE] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            res = consultar_jucepe(p.numero_protocolo, JUCEB_LOGIN, JUCEB_SENHA, headless=True)
        except Exception as e:
            print("   ERRO consulta JUCEPE (mantem):", e)
            continue
        if res.get("erro"):
            print("   JUCEPE erro (mantem status):", res["erro"])
            continue
        print("   JUCEPE:", res)
        p.status_jucesp = res.get("status_texto")
        aplicar_classificacao(db, p, res.get("classificacao", "tramitacao"), agora)
        print()


        if "FINALIZADO" in (res.get("status_texto") or "").upper() and not p.arquivo_registro:
            try:
                nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
                caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
                ok_dl = baixar_documento_jucepe(p.numero_protocolo, JUCEB_LOGIN, JUCEB_SENHA, caminho, headless=True)
                if ok_dl and os.path.exists(caminho):
                    p.arquivo_registro = nome_arquivo
                    p.status = recalcular_status(p)
                    db.commit()
                    print("   [PE] documento baixado e processo atualizado para:", p.status)
                    if p.status == "finalizado":
                        try:
                            corpo = corpo_status_cliente(p, "Finalizado", "Seu Processo foi Finalizado, em Anexo o Registro.")
                            for em in emails_do_grupo(db, p.grupo_id):
                                enviar_email_anexo(em, "Processo Finalizado - " + (p.empresa or ""), corpo, caminho, nome_arquivo)
                            print("   [PE] e-mail de finalizacao enviado.")
                        except Exception as e:
                            print("   [PE] erro ao enviar e-mail de finalizacao:", e)
                else:
                    print("   [PE] documento ainda nao disponivel para download (aguardando).")
            except Exception as e:
                print("   [PE] erro ao baixar documento automaticamente:", e)


def verificar_atrasos_deferido(db, agora):
    """Verifica processos parados em deferido ha mais de 24h (UFs com download
    automatico) e alerta o admin via bot + email, uma unica vez por processo."""
    from datetime import timedelta as _td
    limite = agora - _td(hours=24)
    processos = db.query(Processo).filter(
        Processo.uf.in_(["RJ", "BA", "PE"]),
        Processo.status == "deferido",
        Processo.deferido_em.isnot(None),
        Processo.deferido_em < limite,
        Processo.alertado_atraso_deferido == False,
    ).all()
    if not processos:
        return
    for p in processos:
        try:
            horas = int((agora - p.deferido_em).total_seconds() // 3600)
            texto = (
                "ATENCAO: processo parado em DEFERIDO ha mais de 24h sem finalizar.\n\n"
                "Empresa: " + str(p.empresa) + "\n"
                "UF: " + str(p.uf) + "\n"
                "Protocolo: " + str(p.numero_protocolo) + "\n"
                "Deferido ha aproximadamente " + str(horas) + "h.\n"
                "Verificar manualmente."
            )
            enviar_email(EMAIL_ADMIN, "[Atos] ALERTA - Processo travado ha 24h+ - " + str(p.empresa), texto)
            try:
                enviar_telegram(ADMIN_CHAT_ID, texto)
            except Exception as e:
                print("   erro ao enviar alerta via bot:", e)
            p.alertado_atraso_deferido = True
            db.commit()
            print("   [ALERTA 24H] enviado para:", p.empresa)
        except Exception as e:
            print("   erro ao processar alerta de atraso:", e)

def processar():
    db = SessionLocal()
    agora = datetime.now()
    print("[" + str(agora) + "] Iniciando consultas autonomas.\n")
    processar_sp(db, agora)
    processar_rj(db, agora)
    processar_ba(db, agora)
    processar_pe(db, agora)
    db.close()
    print("FIM.")


if __name__ == "__main__":
    processar()
