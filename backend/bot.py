import os, time, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv("/root/atos/.env")

import requests
from database import SessionLocal, Processo, MensagemProcesso, TelegramVinculo, Usuario

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID") or "")
API = f"https://api.telegram.org/bot{TOKEN}"

def enviar(chat_id, texto, reply_to=None):
    data = {"chat_id": chat_id, "text": texto}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    try:
        requests.post(f"{API}/sendMessage", data=data, timeout=10)
    except Exception as e:
        print("erro enviar:", e)

def achar_admin(db):
    return db.query(Usuario).filter(Usuario.is_admin == True).first()

def processar_reply(msg):
    """Quando o ADM responde (reply) um aviso, grava a resposta no chat do processo."""
    chat_id = str(msg["chat"]["id"])
    if chat_id != ADMIN_CHAT_ID:
        return  # so o ADM autorizado
    texto = (msg.get("text") or "").strip()
    if not texto:
        return
    reply = msg.get("reply_to_message")
    if not reply:
        enviar(chat_id, "Para responder um cliente, use o 'Responder' do Telegram na mensagem do aviso e escreva a resposta.")
        return
    mid = reply["message_id"]
    db = SessionLocal()
    try:
        vinc = db.query(TelegramVinculo).filter(TelegramVinculo.telegram_message_id == mid).order_by(TelegramVinculo.criado_em.desc()).first()
        if not vinc:
            enviar(chat_id, "Nao encontrei a qual processo essa resposta pertence. Responda diretamente a mensagem de aviso do cliente.")
            return
        proc = db.query(Processo).filter(Processo.id == vinc.processo_id).first()
        if not proc:
            enviar(chat_id, "Processo nao encontrado.")
            return
        admin = achar_admin(db)
        nova = MensagemProcesso(
            id=str(uuid.uuid4()),
            processo_id=proc.id,
            autor_login=(admin.login if admin else "admin"),
            autor_tipo="admin",
            texto=texto,
            status_no_momento=proc.status,
            tipo_ato_no_momento=proc.tipo_ato,
        )
        db.add(nova)
        db.commit()
        enviar(chat_id, f"Resposta enviada ao cliente no processo {proc.identificador_ato or proc.tipo_ato or proc.id}.", reply_to=msg["message_id"])
    except Exception as e:
        print("erro processar_reply:", e)
        enviar(chat_id, "Ocorreu um erro ao gravar a resposta.")
    finally:
        db.close()

AJUDA = (
    "Comandos do ATOS:\n"
    "/resumo - totais por status\n"
    "/tramitando - processos em tramitacao\n"
    "/exigencias - processos em exigencia\n"
    "/deferidos - processos deferidos\n"
    "/pendentes - aguardando confirmacao de tipo\n"
    "/buscar <empresa> - status de uma empresa\n"
    "/cliente <grupo> - processos de um grupo\n"
    "/ajuda - esta lista"
)

def _linha(pr):
    ident = pr.identificador_ato or pr.tipo_ato or "-"
    prot = pr.numero_protocolo or "sem protocolo"
    return f"- {pr.empresa or 'sem nome'} | {ident} | prot: {prot}"

def _lista(titulo, itens):
    if not itens:
        return f"{titulo}\n(nenhum)"
    corpo = "\n".join(_linha(x) for x in itens[:50])
    extra = "" if len(itens) <= 50 else f"\n... e mais {len(itens)-50}"
    return f"{titulo} ({len(itens)})\n{corpo}{extra}"

def _sem_acento(s):
    import unicodedata
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _linha(pr):
    ident = pr.identificador_ato or pr.tipo_ato or "-"
    prot = pr.numero_protocolo or "sem protocolo"
    return f"- {pr.empresa or 'sem nome'} | {ident} | prot: {prot}"

def _responder_lista(chat_id, titulo, itens):
    if not itens:
        enviar(chat_id, f"{titulo}\n(nenhum)"); return
    corpo = "\n".join(_linha(x) for x in itens[:50])
    extra = "" if len(itens) <= 50 else f"\n... e mais {len(itens)-50}"
    enviar(chat_id, f"{titulo} ({len(itens)})\n{corpo}{extra}")

def processar_comando(chat_id, texto):
    from database import SessionLocal, Processo, Grupo
    db = SessionLocal()
    try:
        low = _sem_acento(texto).strip().lstrip("/")

        # Filtro de grupo opcional: "... grupo <nome>"
        grupo_obj = None
        grupo_nome = None
        if "grupo" in low:
            partes = low.split("grupo", 1)
            low_status = partes[0].strip()
            grupo_termo = partes[1].strip()
            if grupo_termo:
                for g in db.query(Grupo).all():
                    if _sem_acento(g.nome).find(grupo_termo) >= 0 or grupo_termo.find(_sem_acento(g.nome)) >= 0:
                        grupo_obj = g; grupo_nome = g.nome; break
                if not grupo_obj:
                    enviar(chat_id, f"Grupo '{grupo_termo}' nao encontrado."); return
        else:
            low_status = low

        def base():
            q = db.query(Processo)
            if grupo_obj:
                q = q.filter(Processo.grupo_id == grupo_obj.id)
            return q

        suf = f" - Grupo {grupo_nome}" if grupo_nome else ""

        # AJUDA
        if any(k in low for k in ("ajuda", "help", "comandos")):
            enviar(chat_id,
                "Comandos (com ou sem acento):\n"
                "Visao Geral\n"
                "Processos Tramitando\n"
                "Processos Em Exigencia\n"
                "Processos Deferidos\n"
                "Processos Finalizados\n"
                "\nAdicione 'Grupo <nome>' para filtrar. Ex: Processos Deferidos Grupo Neoenergia")
            return

        # VISAO GERAL
        if "visao geral" in low_status or low_status.strip() in ("visao", "geral", "resumo"):
            def cont(sts): return base().filter(Processo.status.in_(sts)).count()
            total = base().count()
            enviar(chat_id,
                f"Visao Geral{suf}\n"
                f"Total: {total}\n"
                f"Tramitando: {cont(['tramitacao'])}\n"
                f"Em Exigencia: {cont(['exigencia'])}\n"
                f"Deferidos: {cont(['deferido','aprovado'])}\n"
                f"Finalizados: {cont(['finalizado'])}\n"
                f"Abertos: {cont(['recebido','aberto'])}")
            return

        # LISTAS POR STATUS
        if "tramit" in low_status:
            _responder_lista(chat_id, f"Processos Tramitando{suf}", base().filter(Processo.status == "tramitacao").all()); return
        if "exig" in low_status:
            _responder_lista(chat_id, f"Processos Em Exigencia{suf}", base().filter(Processo.status == "exigencia").all()); return
        if "defer" in low_status:
            _responder_lista(chat_id, f"Processos Deferidos{suf}", base().filter(Processo.status.in_(["deferido","aprovado"])).all()); return
        if "finaliz" in low_status:
            _responder_lista(chat_id, f"Processos Finalizados{suf}", base().filter(Processo.status == "finalizado").all()); return

        enviar(chat_id, "Nao entendi. Envie 'ajuda' para ver os comandos.")
    except Exception as e:
        print("erro comando:", e)
        try: enviar(chat_id, "Erro ao consultar. Tente novamente.")
        except: pass
    finally:
        db.close()

def main():
    print("atos-bot iniciado. Polling...")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            r = requests.get(f"{API}/getUpdates", params=params, timeout=40)
            data = r.json()
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg:
                    continue
                if msg.get("reply_to_message"):
                    processar_reply(msg)
                else:
                    _cid = str(msg["chat"]["id"])
                    if _cid == ADMIN_CHAT_ID and (msg.get("text") or "").strip().startswith("/"):
                        processar_comando(_cid, msg.get("text"))
        except Exception as e:
            print("erro loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
