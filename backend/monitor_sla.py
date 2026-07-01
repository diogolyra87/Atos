import os, sys, sqlite3
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv("/root/atos/.env")

DB = "/root/atos/backend/mane.db"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# Reusa funcoes do backend (email Brevo + telegram)
try:
    from main import enviar_email, notificar_telegram
except Exception as e:
    print("Falha ao importar funcoes do main:", e)
    def enviar_email(*a, **k): print("email indisponivel")
    def notificar_telegram(*a, **k): print("telegram indisponivel")

AGORA = datetime.now()

def alertar(assunto, corpo):
    print(">>", assunto)
    try:
        if ADMIN_EMAIL:
            enviar_email(ADMIN_EMAIL, assunto, corpo)
    except Exception as e:
        print("erro email:", e)
    try:
        notificar_telegram("ATOS ALERTA\n" + assunto + "\n\n" + corpo)
    except Exception as e:
        print("erro telegram:", e)

def parse(dt):
    if not dt: return None
    if isinstance(dt, datetime): return dt
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try: return datetime.strptime(str(dt), fmt)
        except: pass
    return None

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    procs = cur.execute("SELECT id, empresa, identificador_ato, tipo_ato, status, numero_protocolo, arquivo_registro, criado_em, data_recebimento FROM processos").fetchall()

    for p in procs:
        pid = p["id"]
        status = (p["status"] or "").lower()
        empresa = p["empresa"] or "sem nome"
        ident = p["identificador_ato"] or p["tipo_ato"] or pid

        r = cur.execute("SELECT * FROM sla_rastreamento WHERE processo_id=?", (pid,)).fetchone()
        if not r:
            cur.execute("INSERT INTO sla_rastreamento (processo_id, criado_visto_em) VALUES (?,?)", (pid, AGORA.strftime("%Y-%m-%d %H:%M:%S")))
            con.commit()
            r = cur.execute("SELECT * FROM sla_rastreamento WHERE processo_id=?", (pid,)).fetchone()

        criado = parse(p["criado_em"]) or parse(p["data_recebimento"]) or parse(r["criado_visto_em"])
        exig_desde = parse(r["exigencia_desde"])
        defer_desde = parse(r["deferido_desde"])

        # Atualiza marcos conforme status atual
        if status == "exigencia" and not exig_desde:
            exig_desde = AGORA
            cur.execute("UPDATE sla_rastreamento SET exigencia_desde=?, alerta_exigencia=0 WHERE processo_id=?", (AGORA.strftime("%Y-%m-%d %H:%M:%S"), pid))
        if status != "exigencia" and exig_desde:
            cur.execute("UPDATE sla_rastreamento SET exigencia_desde=NULL, alerta_exigencia=0 WHERE processo_id=?", (pid,))
            exig_desde = None
        if status == "deferido" and not defer_desde:
            defer_desde = AGORA
            cur.execute("UPDATE sla_rastreamento SET deferido_desde=?, alerta_deferido=0 WHERE processo_id=?", (AGORA.strftime("%Y-%m-%d %H:%M:%S"), pid))
        if status != "deferido" and defer_desde:
            cur.execute("UPDATE sla_rastreamento SET deferido_desde=NULL, alerta_deferido=0 WHERE processo_id=?", (pid,))
            defer_desde = None
        con.commit()

        # REGRA 1: criado + 6h sem protocolo
        if not (p["numero_protocolo"] or "").strip() and status not in ("finalizado", "deferido") and not r["alerta_protocolo"]:
            if criado and AGORA - criado >= timedelta(hours=6):
                alertar(f"Protocolo pendente ha mais de 6h: {empresa}",
                        f"O processo {ident} ({empresa}) foi criado ha mais de 6 horas e ainda nao tem numero de protocolo.")
                cur.execute("UPDATE sla_rastreamento SET alerta_protocolo=1 WHERE processo_id=?", (pid,))
                con.commit()

        # REGRA 2: exigencia + 12h sem movimentacao
        if status == "exigencia" and exig_desde and not r["alerta_exigencia"]:
            if AGORA - exig_desde >= timedelta(hours=12):
                alertar(f"Exigencia parada ha mais de 12h: {empresa}",
                        f"O processo {ident} ({empresa}) esta em exigencia ha mais de 12 horas sem movimentacao.")
                cur.execute("UPDATE sla_rastreamento SET alerta_exigencia=1 WHERE processo_id=?", (pid,))
                con.commit()

        # REGRA 3: deferido + 24h sem registro anexado
        if status == "deferido" and defer_desde and not (p["arquivo_registro"] or "").strip() and not r["alerta_deferido"]:
            if AGORA - defer_desde >= timedelta(hours=24):
                alertar(f"Deferido sem insercao ha mais de 24h: {empresa}",
                        f"O processo {ident} ({empresa}) esta deferido ha mais de 24 horas e o documento aprovado ainda nao foi inserido.")
                cur.execute("UPDATE sla_rastreamento SET alerta_deferido=1 WHERE processo_id=?", (pid,))
                con.commit()

    con.close()
    print("monitor_sla concluido.")

if __name__ == "__main__":
    main()
