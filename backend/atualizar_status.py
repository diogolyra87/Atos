# -*- coding: utf-8 -*-
import sys, os, re
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, "/root/atos/backend")
sys.path.insert(0, "/root/atos/automacao")
from database import SessionLocal, Processo, Grupo, EmailGrupo
sys.path.insert(0, "/root/atos/backend")
from main import corpo_status_cliente, enviar_email, emails_do_grupo, UPLOADS_DIR, recalcular_status, emails_admin, notificar_exigencia_cliente, _email_status_html, _empresa_linha, _email_finalizado, notificar_cliente_processo, UFS_EMAIL_AUTOMATICO_SUSPENSO, notificar_operadores, notificar_falha_sessao_jucesc
from nomenclatura import aplicar_nomenclatura_junta
from consultar_jucesp import consultar
from jucesp_infosimples import baixar_documento as baixar_documento_infosimples_sp
from consultar_jucerja import consultar_jucerja, classificar_status_rj, baixar_documento_jucerja
from consultar_juceb import consultar_juceb, classificar_status_ba, baixar_documento_juceb
from consultar_jucepe import consultar_jucepe, classificar_status_pe, baixar_documento_jucepe
from consultar_jucesc import consultar_jucesc, classificar_status_sc, baixar_documento_jucesc
from empreendedor_digital_scraper import consultar_empreendedor_digital
from bot import enviar as enviar_telegram, ADMIN_CHAT_ID
import json as _json

load_dotenv("/root/atos/.env")

INFOSIMPLES_TOKEN = os.getenv("INFOSIMPLES_TOKEN")
INFOSIMPLES_CPF = os.getenv("INFOSIMPLES_CPF")
INFOSIMPLES_SENHA_NFP = os.getenv("INFOSIMPLES_SENHA_NFP")

JUCERJA_USUARIO = os.getenv("JUCERJA_USUARIO")
JUCERJA_SENHA = os.getenv("JUCERJA_SENHA")
JUCEB_LOGIN = os.getenv("JUCEB_LOGIN")
JUCEB_SENHA = os.getenv("JUCEB_SENHA")
# BUG CORRIGIDO 24/08/2026 (auditoria): processar_pe() usava JUCEB_LOGIN/
# JUCEB_SENHA (credenciais da JUCEB-Bahia) pra autenticar na JUCEPE-
# Pernambuco, um portal completamente diferente - a consulta/download de
# PE sempre falhava (credencial errada). JUCEPE_LOGIN/JUCEPE_SENHA ainda
# NAO estao configuradas no .env - processar_pe() pula com aviso claro
# ate serem cadastradas, em vez de tentar com credenciais erradas.
JUCEPE_LOGIN = os.getenv("JUCEPE_LOGIN")
JUCEPE_SENHA = os.getenv("JUCEPE_SENHA")

EMAIL_ADMIN = os.getenv("ADMIN_EMAIL")

BASE_URL = "https://atos.net.br"

INTERVALO_NORMAL = timedelta(hours=24)
INTERVALO_AGUARDANDO = timedelta(days=7)


def enviar_email_admin_todos(db, assunto, corpo):
    """Envia um alerta administrativo pra todos os destinatarios de
    emails_admin(db) (admin + operadores) - lista definida uma unica vez em
    main.py, reaproveitada aqui pra nao duplicar quem recebe."""
    for destinatario in emails_admin(db):
        enviar_email(destinatario, assunto, corpo)


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
            enviar_email_admin_todos(db, "[Atos] Exigencia - " + str(p.empresa), corpo_admin(p, "Exigencia"))
            notificar_exigencia_cliente(db, p, origem="autonoma")
            notificar_operadores(db, "status_atualizado_automatico", p.id, {"empresa": p.empresa, "valor_anterior": status_atual, "valor_novo": "exigencia"})
            print("   -> mudou para EXIGENCIA + alertou admin" + " e cliente")
        else:
            if precisa_alertar(p, agora):
                p.ultimo_alerta_em = agora
                db.commit()
                enviar_email_admin_todos(db, "[Atos] Exigencia (lembrete) - " + str(p.empresa), corpo_admin(p, "Exigencia"))
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
            enviar_email_admin_todos(db, "[Atos] Deferido - " + str(p.empresa), corpo_admin(p, "Deferido") + "\n\nAguardando a Junta Comercial disponibilizar o Registro.")
            if not p.avisado_deferido:
                _frase_deferido = "Seu processo foi aprovado, aguardando a Junta Comercial disponibilizar o Registro."
                _corpo_deferido = corpo_status_cliente(p, "Deferido", _frase_deferido)
                _corpo_html_deferido = _email_status_html("deferido", "Deferido", "Seu Processo foi Deferido", _empresa_linha(p),
                                                            protocolo=p.numero_protocolo or None, nota_tipo="aguardando", nota_texto=_frase_deferido)
                # avisado_deferido so avanca em envio confirmado (>=1
                # destinatario recebeu) - antes era setado incondicionalmente,
                # entao uma falha de envio nunca era repetida nem sinalizada.
                # Suprimido (UFS_EMAIL_AUTOMATICO_SUSPENSO) continua tentando
                # a cada consulta, visivel via p.email_status="pendente_revisao".
                if notificar_cliente_processo(db, p, "deferido", "Atualizacao do seu processo - " + str(p.empresa), _corpo_deferido, _corpo_html_deferido):
                    p.avisado_deferido = True
                    db.commit()
            notificar_operadores(db, "status_atualizado_automatico", p.id, {"empresa": p.empresa, "valor_anterior": status_atual, "valor_novo": "deferido"})
            print("   -> mudou para DEFERIDO + alertou admin" + (" (cliente suspenso - " + (p.uf or "") + ")" if (p.uf or "").upper() in UFS_EMAIL_AUTOMATICO_SUSPENSO else " e cliente"))
        else:
            if precisa_alertar(p, agora):
                p.ultimo_alerta_em = agora
                db.commit()
                enviar_email_admin_todos(db, "[Atos] Deferido (lembrete) - " + str(p.empresa), corpo_admin(p, "Deferido"))
                print("   -> lembrete de deferido ao admin")
            else:
                db.commit()
                print("   -> deferido ainda no intervalo, sem novo email")

    else:
        if status_atual not in ("tramitacao", "exigencia", "deferido"):
            p.status = "tramitacao"
            db.commit()
            notificar_operadores(db, "status_atualizado_automatico", p.id, {"empresa": p.empresa, "valor_anterior": status_atual, "valor_novo": "tramitacao"})
        else:
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

        # DESATIVADO 30/07/2026: download-dc baixa a copia digitalizada avulsa
        # do arquivamento ("SEM VALOR DE CERTIDAO"), nao a Certidao de Inteiro
        # Teor oficial (com registro/carimbo/valor probatorio) que o processo
        # realmente precisa. 4 processos reais (NBD BRASIL, NEOENERGIA
        # TRANSMISSORA 13/16/17) chegaram a ser marcados "finalizado" com o
        # documento errado e o cliente foi notificado por e-mail antes de
        # detectarmos o problema - ja revertido manualmente (arquivo removido,
        # status de volta pra deferido). Reativar so depois de trocar pelo
        # fluxo correto de emissao da Certidao de Inteiro Teor.
        if False and cls == "deferido" and not p.arquivo_registro:
            nire_limpo = re.sub(r"\D", "", p.nire or "")
            if not nire_limpo:
                print("   [SP] deferido, mas sem NIRE cadastrado - nao da pra baixar via Infosimples.")
            elif not all([INFOSIMPLES_TOKEN, INFOSIMPLES_CPF, INFOSIMPLES_SENHA_NFP]):
                print("   [SP] deferido, mas credenciais Infosimples ausentes no .env - pulando download.")
            else:
                try:
                    # download-dc exige o numero de REGISTRO da JUCESP (ex:
                    # "300.504/26-3"), nao o numero de protocolo - os dois nao
                    # tem relacao previsivel entre si (confirmado em teste real
                    # 30/07/2026). Descobre automaticamente via lista de
                    # documentos do NIRE antes de tentar o download.
                    registro = p.numero_registro or descobrir_registro_infosimples_sp(
                        nire_limpo, p.numero_protocolo, INFOSIMPLES_TOKEN, INFOSIMPLES_CPF, INFOSIMPLES_SENHA_NFP
                    )
                    if not registro:
                        ok_dl = False
                        caminho = None
                        nome_arquivo = None
                    else:
                        p.numero_registro = registro
                        db.commit()
                        nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
                        caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
                        ok_dl = baixar_documento_infosimples_sp(
                            nire_limpo, registro, INFOSIMPLES_TOKEN, INFOSIMPLES_CPF, INFOSIMPLES_SENHA_NFP, caminho
                        )
                    if ok_dl and os.path.exists(caminho):
                        p.arquivo_registro = nome_arquivo
                        p.status = recalcular_status(p)
                        db.commit()
                        print("   [SP] documento baixado via Infosimples e processo atualizado para:", p.status)
                        if p.status == "finalizado":
                            try:
                                corpo, corpo_html = _email_finalizado(p)
                                destinatarios = list(set(emails_do_grupo(db, p.grupo_id)) | set(emails_admin(db)))
                                notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                                            anexo_caminho=caminho, anexo_nome=nome_arquivo, destinatarios=destinatarios)
                                print("   [SP] e-mail de finalizacao enviado (cliente + administradores).")
                            except Exception as e:
                                print("   [SP] erro ao enviar e-mail de finalizacao:", e)
                    else:
                        print("   [SP] documento ainda nao disponivel para download via Infosimples (aguardando).")
                except Exception as e:
                    print("   [SP] erro ao baixar documento automaticamente via Infosimples:", e)
        print()


def processar_sp_registro_sem_protocolo(db, agora):
    """Fallback pra processos SP sem numero_protocolo, mas com numero_registro
    ja identificado (ex: revisao manual via listagem da Certidao de Inteiro
    Teor). Sem protocolo nao da pra usar o scraper gratuito de status
    (consultar_jucesp exige protocolo), entao aqui so tenta o download direto
    via Infosimples usando o numero de registro no lugar do protocolo -
    mesmo padrao de e-mail (cliente + administradores) de processar_sp."""
    processos = db.query(Processo).filter(
        Processo.uf == "SP",
        Processo.numero_registro.isnot(None),
        Processo.numero_registro != "",
        (Processo.numero_protocolo.is_(None)) | (Processo.numero_protocolo == ""),
        Processo.arquivo_registro.is_(None),
    ).all()
    print("[SP-sem-protocolo] " + str(len(processos)) + " processo(s) com numero_registro, sem protocolo.\n")
    # DESATIVADO 30/07/2026: mesmo motivo de processar_sp - download-dc baixa
    # a copia avulsa sem valor de certidao, nao a Certidao de Inteiro Teor
    # oficial. Ver comentario em processar_sp.
    processos = []
    for p in processos:
        if (p.status or "").lower() == "finalizado":
            continue
        nire_limpo = re.sub(r"\D", "", p.nire or "")
        print("-> [SP-sem-protocolo] " + str(p.empresa) + " | registro " + str(p.numero_registro))
        if not nire_limpo:
            print("   sem NIRE cadastrado - nao da pra baixar via Infosimples.")
            continue
        if not all([INFOSIMPLES_TOKEN, INFOSIMPLES_CPF, INFOSIMPLES_SENHA_NFP]):
            print("   credenciais Infosimples ausentes no .env - pulando download.")
            continue
        try:
            nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
            caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
            ok_dl = baixar_documento_infosimples_sp(
                nire_limpo, p.numero_registro, INFOSIMPLES_TOKEN, INFOSIMPLES_CPF, INFOSIMPLES_SENHA_NFP, caminho
            )
            if ok_dl and os.path.exists(caminho):
                p.arquivo_registro = nome_arquivo
                p.status = recalcular_status(p)
                db.commit()
                print("   documento baixado via Infosimples e processo atualizado para:", p.status)
                if p.status == "finalizado":
                    try:
                        corpo, corpo_html = _email_finalizado(p)
                        destinatarios = list(set(emails_do_grupo(db, p.grupo_id)) | set(emails_admin(db)))
                        notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                                    anexo_caminho=caminho, anexo_nome=nome_arquivo, destinatarios=destinatarios)
                        print("   e-mail de finalizacao enviado (cliente + administradores).")
                    except Exception as e:
                        print("   erro ao enviar e-mail de finalizacao:", e)
            else:
                print("   documento ainda nao disponivel para download via Infosimples (aguardando).")
        except Exception as e:
            print("   erro ao baixar documento automaticamente via Infosimples:", e)
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
                            corpo, corpo_html = _email_finalizado(p)
                            notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                                        anexo_caminho=caminho, anexo_nome=nome_arquivo)
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
                            corpo, corpo_html = _email_finalizado(p)
                            notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                                        anexo_caminho=caminho, anexo_nome=nome_arquivo)
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
    if not JUCEPE_LOGIN or not JUCEPE_SENHA:
        print("   [PE] JUCEPE_LOGIN/JUCEPE_SENHA ausentes no .env - pulando PE.")
        return
    for p in pendentes:
        print("-> [PE] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            res = consultar_jucepe(p.numero_protocolo, JUCEPE_LOGIN, JUCEPE_SENHA, headless=True)
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
                ok_dl = baixar_documento_jucepe(p.numero_protocolo, JUCEPE_LOGIN, JUCEPE_SENHA, caminho, headless=True)
                if ok_dl and os.path.exists(caminho):
                    p.arquivo_registro = nome_arquivo
                    p.status = recalcular_status(p)
                    db.commit()
                    print("   [PE] documento baixado e processo atualizado para:", p.status)
                    if p.status == "finalizado":
                        try:
                            corpo, corpo_html = _email_finalizado(p)
                            notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                                        anexo_caminho=caminho, anexo_nome=nome_arquivo)
                            print("   [PE] e-mail de finalizacao enviado.")
                        except Exception as e:
                            print("   [PE] erro ao enviar e-mail de finalizacao:", e)
                else:
                    print("   [PE] documento ainda nao disponivel para download (aguardando).")
            except Exception as e:
                print("   [PE] erro ao baixar documento automaticamente:", e)


def processar_sc(db, agora):
    """Consulta publica da JUCESC (sem login/certificado). Escopo desse
    modulo (24/08/2026) e so acompanhamento de status - ao contrario de
    RJ/BA/PE, NAO baixa documento automaticamente (fora do pedido original).

    Validado em 24/08/2026 contra o protocolo real 265529433 (MELI
    DEVELOPERS BRASIL LTDA/SC) - extracao de status_bruto/historico e
    classificacao (tramitacao) confirmadas corretas, ativado em
    processar()."""
    processos = db.query(Processo).filter(
        Processo.uf == "SC",
        Processo.numero_protocolo.isnot(None),
        Processo.numero_protocolo != "",
    ).all()
    pendentes = [p for p in processos if (p.status or "").lower() != "finalizado"]
    print("[SC] " + str(len(pendentes)) + " processo(s) com protocolo.\n")
    for p in pendentes:
        print("-> [SC] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
        try:
            res = consultar_jucesc(p.numero_protocolo, headless=True)
        except Exception as e:
            print("   ERRO consulta JUCESC (mantem):", e)
            continue
        if res.get("erro"):
            print("   JUCESC erro (mantem status):", res["erro"])
            continue
        print("   JUCESC:", res)
        p.status_jucesp = res.get("status_bruto")
        # classificacao "indeferido" nao tem branch propria em
        # aplicar_classificacao() - cai no else (tramitacao), mesmo
        # comportamento seguro ja usado pra BA/RJ/PE hoje. Se a JUCESC
        # mandar indeferimento com frequencia relevante, decidir depois se
        # merece fluxo proprio (avaliar com texto real, nao especular agora).
        aplicar_classificacao(db, p, res.get("status_classificado", "tramitacao"), agora)
        print()


def processar_download_deferido_sc(db, processo_id, headless=True):
    """ETAPA MANUAL/SUPERVISIONADA (29/08/2026, mesmo padrao usado antes pra
    guia bancaria JUCERJA na etapa 2A): baixa o documento de um processo SC
    especifico quando DEFERIDO na JUCESC, usando a sessao gov.br persistida.
    NAO e' chamada automaticamente por processar_sc() nem por processar() -
    precisa ser chamada manualmente (script/console) ate os seletores serem
    validados contra a pagina real (ver baixar_documento_jucesc em
    consultar_jucesc.py) e o teste end-to-end descrito no pedido original
    passar. So' depois disso decidir, com o Diogo, se entra no polling
    automatico.

    Retorna o dict de baixar_documento_jucesc (sucesso/motivo_falha/
    caminho_pdf). Se motivo_falha == 'sessao_expirada', dispara
    notificar_falha_sessao_jucesc() (e-mail + Telegram) automaticamente."""
    p = db.query(Processo).filter(Processo.id == processo_id, Processo.uf == "SC").first()
    if not p:
        return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "processo nao encontrado ou nao e SC"}
    if not p.numero_protocolo:
        return {"sucesso": False, "caminho_pdf": None, "motivo_falha": "processo sem numero_protocolo"}
    if p.arquivo_registro:
        print("   [SC] documento ja registrado antes para", processo_id, "- ignorando (idempotencia)")
        return {"sucesso": True, "caminho_pdf": None, "motivo_falha": None, "ja_existia": True}

    nome_arquivo = aplicar_nomenclatura_junta(p.id + "_registro_auto.pdf")
    caminho = os.path.join(UPLOADS_DIR, nome_arquivo)

    max_tentativas = 3
    resultado = None
    for tentativa in range(1, max_tentativas + 1):
        resultado = baixar_documento_jucesc(p.numero_protocolo, caminho, headless=headless)
        if resultado.get("sucesso"):
            break
        if resultado.get("motivo_falha") == "sessao_expirada":
            print("   [SC] sessao gov.br expirada - alertando, sem retentar (nao adianta).")
            notificar_falha_sessao_jucesc(db)
            break
        if resultado.get("motivo_falha", "").startswith("processo nao deferido no REGIN"):
            print("   [SC] processo ainda nao deferido no REGIN, sem retentar nesta chamada:", resultado.get("motivo_falha"))
            break
        print(f"   [SC] tentativa {tentativa}/{max_tentativas} falhou:", resultado.get("motivo_falha"))

    # Persiste o numero de requerimento sempre que descoberto, mesmo em
    # falha - util pra proximas tentativas e pra conferencia manual, e o
    # REGIN pode exigir ele (nao o protocolo) pro download em si.
    if resultado.get("numero_requerimento") and not p.numero_requerimento:
        p.numero_requerimento = resultado["numero_requerimento"]
        db.commit()

    if resultado.get("sucesso"):
        p.arquivo_registro = nome_arquivo
        p.status = recalcular_status(p)
        db.commit()
        print("   [SC] documento baixado e processo atualizado para:", p.status)
        if p.status == "finalizado":
            try:
                corpo, corpo_html = _email_finalizado(p)
                notificar_cliente_processo(db, p, "registro", "Processo Finalizado - " + (p.empresa or ""), corpo, corpo_html,
                                            anexo_caminho=caminho, anexo_nome=nome_arquivo)
                print("   [SC] e-mail de finalizacao enviado.")
            except Exception as e:
                print("   [SC] erro ao enviar e-mail de finalizacao:", e)
    return resultado


def _carregar_estados_empreendedor_digital():
    """Le automacao/estados_empreendedor_digital.json (estados ativos na
    plataforma publica compartilhada 'Empreendedor Digital' - MG/DF/CE/MS/
    MT/AP confirmados rodando o mesmo template). Nunca derruba o processo
    principal se o arquivo faltar ou estiver invalido - so desativa essa
    parte da consulta."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "automacao", "estados_empreendedor_digital.json")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception as e:
        print("   [Empreendedor Digital] falha ao carregar config de estados:", e)
        return {}


def processar_empreendedor_digital(db, agora):
    """Consulta generica pra qualquer estado configurado como ativo em
    estados_empreendedor_digital.json (plataforma publica 'Empreendedor
    Digital', sem login). Erro em um estado ou em um processo especifico
    NUNCA interrompe os demais - mesmo padrao de isolamento de erro usado
    em processar_rj/ba/pe."""
    estados = _carregar_estados_empreendedor_digital()
    for uf, cfg in estados.items():
        if not cfg.get("ativo") or not cfg.get("dominio"):
            continue
        try:
            processos = db.query(Processo).filter(
                Processo.uf == uf,
                Processo.numero_protocolo.isnot(None),
                Processo.numero_protocolo != "",
            ).all()
            pendentes = [p for p in processos if (p.status or "").lower() != "finalizado"]
            print("[" + uf + "] " + str(len(pendentes)) + " processo(s) com protocolo (Empreendedor Digital).\n")
            for p in pendentes:
                print("-> [" + uf + "] " + str(p.empresa) + " | prot " + str(p.numero_protocolo) + " | status: " + (p.status or ""))
                try:
                    res = consultar_empreendedor_digital(cfg["dominio"], p.numero_protocolo, headless=True)
                except Exception as e:
                    print("   ERRO consulta " + uf + " (mantem):", e)
                    continue
                if res.get("erro"):
                    print("   " + uf + " erro (mantem status):", res["erro"])
                    continue
                print("   " + uf + ":", res)
                p.status_jucesp = res.get("status_texto")
                aplicar_classificacao(db, p, res.get("classificacao", "tramitacao"), agora)
                print()
        except Exception as e:
            print("   ERRO GERAL processando " + uf + " (Empreendedor Digital, mantem demais estados):", e)


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
            enviar_email_admin_todos(db, "[Atos] ALERTA - Processo travado ha 24h+ - " + str(p.empresa), texto)
            try:
                enviar_telegram(ADMIN_CHAT_ID, texto)
            except Exception as e:
                print("   erro ao enviar alerta via bot:", e)
            p.alertado_atraso_deferido = True
            db.commit()
            print("   [ALERTA 24H] enviado para:", p.empresa)
        except Exception as e:
            print("   erro ao processar alerta de atraso:", e)

def _marcar_execucao_ok():
    """Grava um heartbeat de sucesso (so' chega aqui se processar() completou
    sem excecao nao tratada, inclusive sem erro de import no carregamento do
    modulo). monitor_sla.py - processo INDEPENDENTE, com seu proprio timer,
    que nao importa este arquivo - le esse heartbeat e alerta (email+
    telegram) se ele parar de ser atualizado. Precisa ser um processo
    separado: se este script quebrar no import (como aconteceu de
    31/07 a 01/08, crash-loop nunca detectado), ele mesmo nao teria como se
    auto-alertar."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultima_consulta_ok.txt")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print("   [aviso] falha ao gravar heartbeat de saude do cron:", e)


def processar():
    db = SessionLocal()
    agora = datetime.now()
    print("[" + str(agora) + "] Iniciando consultas autonomas.\n")
    processar_sp(db, agora)
    processar_sp_registro_sem_protocolo(db, agora)
    processar_rj(db, agora)
    processar_ba(db, agora)
    processar_pe(db, agora)
    processar_sc(db, agora)  # ativado 24/08/2026 - validado com protocolo
    # real (265529433, MELI DEVELOPERS BRASIL LTDA/SC), extracao de status
    # e historico confirmada correta.
    processar_empreendedor_digital(db, agora)
    db.close()
    _marcar_execucao_ok()
    print("FIM.")


if __name__ == "__main__":
    processar()
