import os, time, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv("/root/atos/.env")

import requests
from database import SessionLocal, Processo, MensagemProcesso, TelegramVinculo, Usuario
import sys as _sys
_sys.path.insert(0, os.path.dirname(__file__))
from main import extrair_protocolo_ocr, recalcular_status, UPLOADS_DIR, GEMINI_KEY, notificar_tramitacao_cliente

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID") or "")
API = f"https://api.telegram.org/bot{TOKEN}"

# ===== Integracao do agente Mane (execucao autonoma via Telegram) =====
import subprocess as _subprocess
import anthropic as _anthropic

_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
_mane_client = _anthropic.Anthropic(api_key=_ANTHROPIC_KEY) if _ANTHROPIC_KEY else None

def _mane_carregar_conhecimento():
    partes = []
    for nome in ["ATOS_registro_problemas_corrigidos.md", "ATOS_ESTADO_COMPLETO.md"]:
        caminho = os.path.join(os.path.dirname(__file__), nome)
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                partes.append("=== " + nome + " ===\n" + f.read())
    return "\n\n".join(partes)

_MANE_CONHECIMENTO = _mane_carregar_conhecimento()

_MANE_SYSTEM_PROMPT = """Voce e o Mane, agente de IA do sistema ATOS, respondendo pelo bot do Telegram.

IMPORTANTE - LIMITE DE ESCOPO NESTA INTERFACE (Telegram):
Voce esta rodando DIRETO NO SERVIDOR de producao. Por isso, nesta interface, voce NAO deve
editar nenhum arquivo de codigo (.py, .js) do sistema - essas mudancas devem sempre partir
do PC do usuario (via o Mane local, outra interface), seguindo o fluxo de deploy padrao
documentado na base de conhecimento (commit no PC -> push -> pull no servidor).

Nesta interface (Telegram) voce PODE, com seguranca:
- Consultar o banco de dados (sqlite3, somente leitura preferencialmente)
- Verificar status de servicos (systemctl status)
- Ver logs (journalctl)
- Rodar consultas de automacao ja existentes (ex: processar_rj, processar_ba, processar_pe)
- Reiniciar servicos quando fizer sentido e for seguro
- Responder perguntas sobre o sistema usando a base de conhecimento abaixo

Se o usuario pedir uma mudanca de CODIGO, explique educadamente que essa tarefa deve ser
feita pelo Mane local (no PC), nao por aqui, e sugira a mensagem que ele pode usar la.

Seja direto e conciso nas respostas - isso e um chat do Telegram, nao um terminal.

BASE DE CONHECIMENTO DO SISTEMA:

""" + _MANE_CONHECIMENTO

_MANE_TOOLS = [
    {
        "name": "executar_bash",
        "description": "Executa um comando bash diretamente no servidor (voce ja esta rodando nele) e retorna a saida.",
        "input_schema": {
            "type": "object",
            "properties": {
                "comando": {"type": "string", "description": "O comando bash a executar"}
            },
            "required": ["comando"]
        }
    }
]

def _mane_executar_bash(comando):
    try:
        resultado = _subprocess.run(
            ["bash", "-c", comando],
            capture_output=True, text=True, timeout=120
        )
        saida = (resultado.stdout or "") + (resultado.stderr or "")
        saida = saida.strip()
        if len(saida) > 3500:
            saida = saida[:3500] + "\n...(saida truncada)..."
        return saida if saida else "(comando executado sem saida)"
    except _subprocess.TimeoutExpired:
        return "ERRO: comando excedeu o tempo limite de 120 segundos"
    except Exception as e:
        return "ERRO ao executar: " + str(e)

def processar_pedido_mane(chat_id, texto):
    if not _mane_client:
        enviar(chat_id, "Mane indisponivel: ANTHROPIC_API_KEY nao configurada no .env do servidor.")
        return
    enviar(chat_id, "Processando...")
    mensagens = [{"role": "user", "content": texto}]
    try:
        while True:
            resposta = _mane_client.messages.create(
                model="claude-sonnet-5",
                max_tokens=2048,
                system=_MANE_SYSTEM_PROMPT,
                tools=_MANE_TOOLS,
                messages=mensagens
            )
            mensagens.append({"role": "assistant", "content": resposta.content})
            blocos_ferramenta = [b for b in resposta.content if b.type == "tool_use"]
            blocos_texto = [b.text for b in resposta.content if b.type == "text"]
            for t in blocos_texto:
                if t.strip():
                    enviar(chat_id, t)
            if not blocos_ferramenta:
                break
            resultados = []
            for bloco in blocos_ferramenta:
                if bloco.name == "executar_bash":
                    saida = _mane_executar_bash(bloco.input.get("comando", ""))
                    resultados.append({"type": "tool_result", "tool_use_id": bloco.id, "content": saida})
            mensagens.append({"role": "user", "content": resultados})
    except Exception as e:
        enviar(chat_id, "Erro no Mane: " + str(e))

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

AUTORIZADOS_ANEXO = set([ADMIN_CHAT_ID]) | set(x.strip() for x in (os.getenv("TELEGRAM_AUTORIZADOS_ANEXO") or "").split(",") if x.strip())

def _extrair_empresa_ato_ia(caminho_pdf):
    """Le o nome empresarial e o(s) ato(s) descritos na capa do protocolo (JUCESP/JUCERJA
    etc), via Gemini. Funciona com texto impresso e manuscrito legivel. Nunca lanca excecao."""
    import base64, json as _json, urllib.request
    if not GEMINI_KEY:
        return None, None
    try:
        with open(caminho_pdf, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode()
        prompt = (
            "Esta e uma capa de protocolo de Junta Comercial brasileira. Leia o campo "
            "NOME EMPRESARIAL (nome da empresa) e o campo ATO(S) (pode estar escrito a mao, "
            "ex: 7a Alteracao Contratual, AGE, etc). Responda APENAS com um JSON no formato "
            '{"empresa": "...", "ato": "..."}. Se nao conseguir ler algum campo, deixe como string vazia.'
        )
        body = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}}]}]}
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" + GEMINI_KEY
        req = urllib.request.Request(url, data=_json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=40)
        data = _json.loads(resp.read().decode())
        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        resultado = _json.loads(txt)
        return (resultado.get("empresa") or None), (resultado.get("ato") or None)
    except Exception as e:
        print("Erro ao extrair empresa/ato do protocolo:", str(e)[:150])
        return None, None
_PENDENTES_ANEXO = {}

def _baixar_arquivo_telegram(file_id, destino_path):
    r = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=20)
    caminho_remoto = r.json()["result"]["file_path"]
    url_download = f"https://api.telegram.org/file/bot{TOKEN}/{caminho_remoto}"
    resp = requests.get(url_download, timeout=30)
    with open(destino_path, "wb") as f:
        f.write(resp.content)
    return destino_path

def processar_anexo_protocolo(chat_id, msg):
    if chat_id not in AUTORIZADOS_ANEXO:
        return
    import tempfile, img2pdf as _img2pdf

    file_id = None
    eh_foto = False
    if msg.get("photo"):
        file_id = msg["photo"][-1]["file_id"]
        eh_foto = True
    elif msg.get("document"):
        file_id = msg["document"]["file_id"]
        nome_doc = (msg["document"].get("file_name") or "").lower()
        eh_foto = not nome_doc.endswith(".pdf")

    if not file_id:
        return

    enviar(chat_id, "Recebido, analisando o protocolo...")
    tmpdir = tempfile.mkdtemp()
    try:
        ext = ".jpg" if eh_foto else ".pdf"
        caminho_bruto = os.path.join(tmpdir, "anexo" + ext)
        _baixar_arquivo_telegram(file_id, caminho_bruto)

        if eh_foto:
            caminho_pdf = os.path.join(tmpdir, "anexo.pdf")
            with open(caminho_pdf, "wb") as f:
                f.write(_img2pdf.convert(caminho_bruto))
        else:
            caminho_pdf = caminho_bruto

        numero = extrair_protocolo_ocr(caminho_pdf)
        if not numero:
            enviar(chat_id, "Nao consegui identificar o numero do protocolo neste documento. Envie uma foto/PDF mais nitido, ou digite o numero manualmente pelo sistema.")
            return

        empresa_lida, ato_lido = _extrair_empresa_ato_ia(caminho_pdf)

        with open(caminho_pdf, "rb") as f:
            pdf_bytes = f.read()

        db = SessionLocal()
        try:
            candidatos = db.query(Processo).filter(Processo.status == "aberto").order_by(Processo.criado_em.desc()).all()
        finally:
            db.close()

        if not candidatos:
            enviar(chat_id, "Protocolo identificado: " + numero + "\n\nMas nao ha nenhum processo em aberto (sem protocolo) no sistema no momento para vincular.")
            return

        def _pontua(p):
            score = 0
            if empresa_lida and p.empresa and empresa_lida.lower()[:15] in p.empresa.lower():
                score += 10
            if ato_lido and (p.tipo_ato or ""):
                if ato_lido.lower()[:6] in (p.tipo_ato or "").lower():
                    score += 5
            if ato_lido and (p.identificador_ato or ""):
                if ato_lido.lower()[:6] in (p.identificador_ato or "").lower():
                    score += 5
            return score

        candidatos_ordenados = sorted(candidatos, key=_pontua, reverse=True)[:8]

        cabecalho = "Protocolo identificado: *" + numero + "*\n"
        if empresa_lida or ato_lido:
            cabecalho += "Lido do documento -> Empresa: " + (empresa_lida or "-") + " | Ato: " + (ato_lido or "-") + "\n\n"
        linhas = [cabecalho, "A qual processo pertence? Responda esta mensagem com o numero:\n"]
        opcoes = {}
        for i, p in enumerate(candidatos_ordenados, start=1):
            linhas.append(str(i) + ". " + str(p.empresa) + " (" + (p.uf or "-") + ") - " + (p.tipo_ato or ""))
            opcoes[str(i)] = p.id
        texto_msg = "\n".join(linhas)

        r = requests.post(f"{API}/sendMessage", data={"chat_id": chat_id, "text": texto_msg, "parse_mode": "Markdown"}, timeout=10)
        message_id_enviado = r.json()["result"]["message_id"]
        _PENDENTES_ANEXO[message_id_enviado] = {"numero_protocolo": numero, "opcoes": opcoes, "pdf_bytes": pdf_bytes}
    except Exception as e:
        print("erro processar_anexo_protocolo:", e)
        enviar(chat_id, "Erro ao processar o anexo: " + str(e))

def processar_confirmacao_anexo(chat_id, msg):
    reply = msg.get("reply_to_message")
    if not reply:
        return False
    mid = reply["message_id"]
    pendente = _PENDENTES_ANEXO.get(mid)
    if not pendente:
        return False
    escolha = (msg.get("text") or "").strip()
    processo_id = pendente["opcoes"].get(escolha)
    if not processo_id:
        enviar(chat_id, "Numero invalido. Responda com um dos numeros da lista, ou ignore para cancelar.")
        return True
    db = SessionLocal()
    try:
        p = db.query(Processo).filter(Processo.id == processo_id).first()
        if not p:
            enviar(chat_id, "Processo nao encontrado (pode ter sido alterado nesse meio tempo).")
            return True
        status_antes_bot = (p.status or "").lower()
        nome_arquivo = p.id + "_protocolo.pdf"
        caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
        with open(caminho, "wb") as f:
            f.write(pendente["pdf_bytes"])
        p.arquivo_protocolo = nome_arquivo
        p.numero_protocolo = pendente["numero_protocolo"]
        p.status = recalcular_status(p)
        db.commit()
        try:
            notificar_tramitacao_cliente(db, p, status_antes_bot)
        except Exception as e:
            print("erro ao notificar tramitacao (bot):", e)
        enviar(chat_id, "Protocolo " + pendente["numero_protocolo"] + " vinculado ao processo de " + str(p.empresa) + ". Documento salvo. Status atualizado para: " + str(p.status) + ".")
    except Exception as e:
        print("erro processar_confirmacao_anexo:", e)
        enviar(chat_id, "Erro ao vincular o protocolo.")
    finally:
        db.close()
    del _PENDENTES_ANEXO[mid]
    return True

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
                if msg.get("photo") or msg.get("document"):
                    _cid = str(msg["chat"]["id"])
                    processar_anexo_protocolo(_cid, msg)
                elif msg.get("reply_to_message"):
                    _cid = str(msg["chat"]["id"])
                    if not processar_confirmacao_anexo(_cid, msg):
                        processar_reply(msg)
                else:
                    _cid = str(msg["chat"]["id"])
                    _texto_msg = (msg.get("text") or "").strip()
                    if _cid == ADMIN_CHAT_ID and _texto_msg.startswith("/"):
                        processar_comando(_cid, msg.get("text"))
                    elif _cid == ADMIN_CHAT_ID and _texto_msg:
                        processar_pedido_mane(_cid, _texto_msg)
        except Exception as e:
            print("erro loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
