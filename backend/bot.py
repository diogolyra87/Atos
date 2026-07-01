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
                processar_reply(msg)
        except Exception as e:
            print("erro loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
