from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import get_db, Processo, Grupo, Usuario, EmailGrupo, criar_banco, AuditLog, Codigo2FA, Anexo, RegraAprendizado, MensagemProcesso, TelegramVinculo
from datetime import datetime, timedelta
from openai import OpenAI
import json, os, uuid, shutil, bcrypt

from dotenv import load_dotenv
import os
load_dotenv()

# --- Rate limiter simples em memoria (anti-forca-bruta no login) ---
import time as _time
_login_tentativas = {}
_LOGIN_MAX = 5          # tentativas
_LOGIN_JANELA = 300     # segundos (5 min)
_LOGIN_BLOQUEIO = 900   # segundos (15 min de bloqueio)
def _checar_rate_login(ip):
    agora = _time.time()
    reg = _login_tentativas.get(ip)
    if reg and reg.get("bloqueado_ate", 0) > agora:
        return False
    if not reg or (agora - reg.get("inicio", 0)) > _LOGIN_JANELA:
        _login_tentativas[ip] = {"inicio": agora, "falhas": 0, "bloqueado_ate": 0}
    return True
def _registrar_falha_login(ip):
    agora = _time.time()
    reg = _login_tentativas.get(ip) or {"inicio": agora, "falhas": 0, "bloqueado_ate": 0}
    reg["falhas"] = reg.get("falhas", 0) + 1
    if reg["falhas"] >= _LOGIN_MAX:
        reg["bloqueado_ate"] = agora + _LOGIN_BLOQUEIO
    _login_tentativas[ip] = reg
def _limpar_falhas_login(ip):
    if ip in _login_tentativas:
        del _login_tentativas[ip]

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_FROM = os.getenv("EMAIL_FROM") or EMAIL_USER
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT_SMTP = int(os.getenv("EMAIL_PORT_SMTP", "587"))
BASE_URL_SISTEMA = os.getenv("BASE_URL_SISTEMA", "https://atos.net.br")

def enviar_email(destinatario, assunto, corpo, corpo_html=None):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Atos - Gestao Societaria <%s>" % EMAIL_FROM
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain"))
        if not corpo_html:
            try:
                corpo_html = envolver_html(corpo)
            except Exception:
                corpo_html = None
        if corpo_html:
            msg.attach(MIMEText(corpo_html, "html"))
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT_SMTP)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email para {destinatario}: {e}")
        return False

def enviar_email_anexo(destinatario, assunto, corpo, caminho_anexo=None, nome_anexo=None):
    try:
        from email.mime.application import MIMEApplication
        msg = MIMEMultipart("mixed")
        msg["From"] = "Atos - Gestao Societaria <%s>" % EMAIL_FROM
        msg["To"] = destinatario
        msg["Subject"] = assunto
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(corpo, "plain"))
        try:
            alt.attach(MIMEText(envolver_html(corpo), "html"))
        except Exception as _e:
            print("aviso html anexo:", _e)
        msg.attach(alt)
        if caminho_anexo and os.path.exists(caminho_anexo):
            with open(caminho_anexo, "rb") as fa:
                part = MIMEApplication(fa.read(), Name=(nome_anexo or os.path.basename(caminho_anexo)))
            part["Content-Disposition"] = 'attachment; filename="%s"' % (nome_anexo or os.path.basename(caminho_anexo))
            msg.attach(part)
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT_SMTP)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email (anexo) para {destinatario}: {e}")
        return False

def validar_token(x_token, db):
    """Busca o usuario pelo token e verifica se nao expirou (30 dias)."""
    if not x_token:
        return None
    u = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not u:
        return None
    tc = getattr(u, "token_criado_em", None)
    if tc is not None:
        from datetime import timedelta
        if datetime.now() - tc > timedelta(days=30):
            return None  # token expirado
    return u

def obter_ip(request):
    """Retorna o IP real do cliente, lendo cabecalhos do proxy nginx."""
    if not request:
        return None
    xr = request.headers.get("x-real-ip")
    if xr:
        return xr
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None

def email_do_usuario(db, usuario):
    """Retorna o e-mail do usuario (proprio se houver, senao o primeiro e-mail do grupo)."""
    try:
        e = getattr(usuario, "email", None)
        if e:
            return e
        eg = db.query(EmailGrupo).filter(EmailGrupo.grupo_id == usuario.grupo_id).first()
        return eg.email if eg else None
    except Exception as ex:
        print("Erro email_do_usuario:", ex)
        return None


def registrar_auditoria(db, usuario, acao, processo_id=None, detalhe=None, ip=None):
    """Registra uma acao na trilha de auditoria. Nunca quebra a operacao principal."""
    try:
        import uuid as _uuid
        log = AuditLog(
            id=str(_uuid.uuid4()),
            usuario_login=getattr(usuario, "login", None) if usuario else None,
            usuario_id=getattr(usuario, "id", None) if usuario else None,
            grupo_id=getattr(usuario, "grupo_id", None) if usuario else None,
            is_admin=bool(getattr(usuario, "is_admin", False)) if usuario else False,
            acao=acao,
            processo_id=processo_id,
            detalhe=detalhe,
            ip=ip,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print("Falha ao registrar auditoria:", e)

def emails_do_grupo(db, grupo_id):
    if not grupo_id:
        return []
    regs = db.query(EmailGrupo).filter(EmailGrupo.grupo_id == grupo_id).all()
    return [r.email for r in regs if r.email]

def _regex_protocolo(texto):
    import re
    up = texto.upper()
    if "JUCESP PROTOCOLO" in up:
        idx = up.find("JUCESP PROTOCOLO")
        m = re.search(r"\d\.\d{3}\.\d{3}/\d{2}-\d", texto[idx: idx + 120])
        if m:
            return m.group(0)
    m = re.search(r"\d\.\d{3}\.\d{3}/\d{2}-\d", texto)
    if m:
        return m.group(0)
    if "PROTOCOLO" in up:
        idx = up.rfind("PROTOCOLO")
        mm = re.search(r"(20\d{2})\s*/\s*([\d/\s]+?)\s*-\s*(\d)", texto[idx: idx + 80])
        if mm:
            meio = re.sub(r"[^0-9]", "", mm.group(2)).zfill(8)[-8:]
            return mm.group(1) + "/" + meio + "-" + mm.group(3)
    m = re.search(r"20\d{2}/\d{8}-\d", texto)
    if m:
        return m.group(0)
    return None

def _texto_pdf(caminho_pdf):
    import subprocess
    try:
        out = subprocess.run(["pdftotext", caminho_pdf, "-"], capture_output=True, text=True, timeout=30)
        return out.stdout or ""
    except Exception:
        return ""

def _gemini_protocolo(caminho_pdf):
    import base64, json, urllib.request
    if not GEMINI_KEY:
        return None
    try:
        with open(caminho_pdf, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode()
        prompt = ("Este e um comprovante de protocolo de Junta Comercial (JUCESP ou JUCERJA). "
                  "Extraia APENAS o numero do protocolo e responda somente com ele, sem mais nada. "
                  "JUCESP tem formato 0.000.000/00-0. JUCERJA tem formato 2026/00000000-0.")
        body = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}}
            ]}]
        }
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" + GEMINI_KEY
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=40)
        data = json.loads(resp.read().decode())
        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return _regex_protocolo(txt) or txt.strip()
    except Exception as e:
        print("Gemini protocolo falhou:", e)
        return None

def _tesseract_protocolo(caminho_pdf):
    import subprocess, os, glob, tempfile
    try:
        d = tempfile.mkdtemp()
        subprocess.run(["pdftoppm", "-r", "300", "-png", caminho_pdf, os.path.join(d, "pg")], check=True, timeout=60)
        texto = ""
        for img in sorted(glob.glob(os.path.join(d, "*.png"))):
            out = subprocess.run(["tesseract", img, "stdout", "-l", "por"], capture_output=True, text=True, timeout=60)
            if not out.stdout.strip():
                out = subprocess.run(["tesseract", img, "stdout"], capture_output=True, text=True, timeout=60)
            texto += out.stdout + "\n"
        return _regex_protocolo(texto)
    except Exception as e:
        print("Tesseract protocolo falhou:", e)
        return None

def _extrair_protocolo_barcode(caminho_pdf):
    """Tenta ler o codigo de barras do protocolo direto da imagem do PDF.
    Muito mais confiavel que OCR/IA: leitura deterministica, sem risco de
    confundir digitos visualmente (ex: 6 lido como 0)."""
    import subprocess, tempfile, os, glob, re as _re
    try:
        from pyzbar.pyzbar import decode as _zbar_decode
        from PIL import Image as _PILImage
    except Exception:
        return None
    try:
        d = tempfile.mkdtemp()
        subprocess.run(["pdftoppm", "-r", "200", "-jpeg", caminho_pdf, os.path.join(d, "pg")], check=True, timeout=60)
        for img_path in sorted(glob.glob(os.path.join(d, "*.jpg"))):
            img = _PILImage.open(img_path)
            for r in _zbar_decode(img):
                digitos = _re.sub(r"\D", "", r.data.decode("utf-8", errors="ignore"))
                if len(digitos) == 10:
                    return digitos[0] + "." + digitos[1:4] + "." + digitos[4:7] + "/" + digitos[7:9] + "-" + digitos[9]
                if len(digitos) == 13:
                    return digitos[:4] + "/" + digitos[4:12] + "-" + digitos[12]
        return None
    except Exception as e:
        print("Erro ao ler codigo de barras:", str(e)[:150])
        return None


def extrair_protocolo_ocr(caminho_pdf):
    # 0) Codigo de barras: deterministico, mais confiavel que qualquer OCR/IA
    num = _extrair_protocolo_barcode(caminho_pdf)
    if num:
        print("protocolo via codigo de barras:", num)
        return num
    # 1) PDF editavel: texto direto (gratis, instantaneo)
    texto = _texto_pdf(caminho_pdf)
    if len(texto.strip()) > 30:
        num = _regex_protocolo(texto)
        if num:
            print("protocolo via texto:", num)
            return num
    # 2) PDF fechado: Gemini (preciso)
    num = _gemini_protocolo(caminho_pdf)
    if num:
        print("protocolo via Gemini:", num)
        return num
    # 3) fallback: Tesseract
    num = _tesseract_protocolo(caminho_pdf)
    if num:
        print("protocolo via Tesseract:", num)
    return num

def corpo_status_cliente(p, status_label, frase_final):
    ato = p.identificador_ato or p.tipo_ato or ""
    linhas = []
    linhas.append("Empresa: " + (p.empresa or ""))
    linhas.append("Ato: " + ato)
    linhas.append("Status: " + status_label)
    if p.numero_protocolo:
        linhas.append("")
        linhas.append("Protocolo: " + p.numero_protocolo)
    if frase_final:
        linhas.append("")
        linhas.append(frase_final)
    return "\n".join(linhas)

def rodape_atos():
    return (
        '<div style="border-top:1px solid #eef1f5;padding:18px 24px;background:#f7f9fc;">'
        '<div style="font-size:26px;font-weight:bold;color:#111111;letter-spacing:-1px;line-height:1;">atos<span style="color:#2d6cdf;">.</span></div>'
        '<div style="font-size:11px;color:#5a7088;letter-spacing:1px;margin-top:2px;">Gestao Societaria</div>'
        '<div style="font-size:11px;color:#9aa4b2;margin-top:8px;">contato@atos.net.br &middot; atos.net.br</div>'
        '</div>'
    )

def _badge_status(status_label):
    cores = {"Aberto": ("#eceae2", "#6b6c66"), "Tramitacao": ("#f0e0cb", "#8a5818"), "Exigencia": ("#f0dcd5", "#a8492a"), "Deferido": ("#d5e3df", "#15803d"), "Finalizado": ("#cfe8d8", "#15803d")}
    bg, cor = cores.get(status_label, ("#e6f1fb", "#185fa5"))
    return '<span style="display:inline-block;background:' + bg + ';color:' + cor + ';font-size:12px;font-weight:bold;padding:5px 14px;border-radius:20px;">' + status_label + '</span>'

def envolver_html(corpo_texto, titulo="Atualizacao do seu processo"):
    linhas = corpo_texto.split(chr(10))
    corpo_p = ""
    for ln in linhas:
        if ln.strip() == "":
            continue
        corpo_p = corpo_p + '<div style="font-size:14px;color:#445;line-height:1.65;margin-bottom:4px;">' + ln + '</div>'
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e6ebf2;border-radius:12px;overflow:hidden;">'
        '<div style="height:5px;background:linear-gradient(90deg,#2563eb,#2dd4bf);"></div>'
        '<div style="padding:28px 24px;">'
        '<div style="font-size:19px;font-weight:bold;color:#1a2330;margin-bottom:14px;">' + titulo + '</div>'
        + corpo_p +
        '</div>'
        + rodape_atos() +
        '</div>'
    )


def _disparar_convites(nome, link, emails):
    corpo = (
        "Ola!\n\n"
        "Voce foi cadastrado para acessar o sistema Atos - Gestao Societaria, no grupo " + nome + ".\n\n"
        "Para criar seu usuario e senha de acesso, clique no link abaixo:\n"
        + link + "\n\n"
        "Apos criar seu acesso, voce podera acompanhar seus processos pelo endereco " + BASE_URL_SISTEMA + ".\n\n"
        "Atenciosamente,\nEquipe Atos"
    )
    corpo_html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:0 auto;color:#241b4a;">'
        '<h2 style="color:#111111;margin:0 0 4px;">atos<span style="color:#2d6cdf;">.</span></h2>'
        '<p style="font-size:12px;color:#7a7790;margin:0 0 18px;">Gestao Societaria</p>'
        '<p>Ola!</p>'
        '<p>Voce foi cadastrado para acessar o sistema <strong>Atos - Gestao Societaria</strong>, no grupo <strong>' + nome + '</strong>.</p>'
        '<p>Para criar seu usuario e senha de acesso, clique no botao abaixo:</p>'
        '<p style="text-align:center;margin:24px 0;"><a href="' + link + '" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:13px 28px;border-radius:8px;font-weight:bold;display:inline-block;">Criar meu acesso</a></p>'
        '<p style="font-size:13px;color:#7a7790;">Ou copie e cole este endereco no navegador:<br><a href="' + link + '">' + link + '</a></p>'
        '<p style="margin-top:24px;">Atenciosamente,<br>Equipe Atos</p>'
        + rodape_atos() +
        '</div>'
    )
    for email in emails:
        enviar_email(email, "Acesso ao sistema Atos - " + nome, corpo, corpo_html)


app = FastAPI(title="Atos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://atos.net.br", "https://www.atos.net.br"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")  # desativado: arquivos agora so via /download protegido

GEMINI_KEY = os.getenv("GEMINI_KEY")
EMAIL_ADMIN = os.getenv("ADMIN_EMAIL")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

CONHECIMENTO_FILE = r"D:\Mane\dados\conhecimento_registro.json"
def carregar_conhecimento():
    if os.path.exists(CONHECIMENTO_FILE):
        with open(CONHECIMENTO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

CONHECIMENTO = carregar_conhecimento()

criar_banco()

# ============================================================
# ANALISAR ATA COM IA
# ============================================================
def analisar_ata_ia(texto_ata: str) -> dict:
    conhecimento = json.dumps(CONHECIMENTO, ensure_ascii=False)[:3000]
    prompt = f"""Analise esta ata/documento e extraia as informações no formato JSON exato abaixo.

CONHECIMENTO BASE:
{conhecimento}

DOCUMENTO:
{texto_ata[:4000]}

REGRA IMPORTANTE PARA UF: Identifique a UF (sigla do estado, 2 letras) da sede da sociedade. Em alteracoes contratuais de sociedades limitadas, a UF aparece no campo de qualificacao da sociedade, no padrao Cidade/UF (exemplo: 'Rio de Janeiro/RJ' significa UF=RJ; 'Sao Paulo/SP' significa UF=SP). Procure a cidade seguida de barra e a sigla do estado no endereco da sede. Retorne so a sigla de 2 letras maiuscula.

Retorne APENAS um JSON válido com esta estrutura exata:
{{
  "empresa": "nome completo da empresa",
  "cnpj": "XX.XXX.XXX/XXXX-XX",
  "nire": "número NIRE se encontrado",
  "uf": "sigla de 2 letras do estado da sede, ex RJ ou SP",
  "uf_destino_transferencia": "APENAS se a ata tratar de TRANSFERENCIA DE SEDE para outro Estado (mudanca de endereco da sede social de um Estado para outro, nao mudanca de endereco dentro do mesmo Estado): informe a sigla de 2 letras do Estado de DESTINO. Caso contrario deixe vazio.",
  "tipo_sociedade": "SA ou LTDA",
  "tipo_ato": "AGO, AGE, AGOE, RCA, ALTERACAO_CONTRATUAL, ARS etc",
  "identificador_ato": "ex: RCA 25/05/2026, 39ª Alteração Contratual, AGE 10/05/2026",
  "data_ata": "DD/MM/AAAA",
  "hora_ata": "HH:MM ou vazio",
  "email_cliente": "",
  "eventos": ["lista", "de", "eventos", "identificados"],
  "requer_cpl": true ou false,
  "checklist": ["lista", "de", "documentos", "necessários"],
  "observacoes": "alertas importantes"
}}"""

    resposta = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.1
    )
    texto = resposta.choices[0].message.content
    texto_limpo = texto.replace("```json", "").replace("```", "").strip()
    dados = json.loads(texto_limpo)

    # Fallback: se a UF nao foi identificada pelo endereco da ata, infere pelo prefixo do NIRE
    # 333/332 = RJ | 353/352 = SP | 292/293 = BA | 262/263 = PE
    # (lista sera expandida com mais UFs futuramente)
    if not (dados.get("uf") or "").strip():
        nire_digitos = "".join(c for c in (dados.get("nire") or "") if c.isdigit())
        prefixo_nire = nire_digitos[:3]
        if prefixo_nire in ("333", "332"):
            dados["uf"] = "RJ"
        elif prefixo_nire in ("353", "352"):
            dados["uf"] = "SP"
        elif prefixo_nire in ("292", "293"):
            dados["uf"] = "BA"
        elif prefixo_nire in ("262", "263"):
            dados["uf"] = "PE"

    return dados

# ============================================================
# ROTAS
# ============================================================
@app.get("/")
def root():
    return {"status": "Atos online"}


@app.post("/cadastro")
def cadastro(dados: dict, db: Session = Depends(get_db)):
    codigo_grupo = (dados.get("codigo_grupo") or "").strip()
    login = (dados.get("login") or "").strip()
    senha = dados.get("senha") or ""

    if not codigo_grupo or not login or not senha:
        raise HTTPException(status_code=400, detail="codigo_grupo, login e senha sao obrigatorios")
    if len(senha) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")

    grupo = db.query(Grupo).filter(Grupo.codigo == codigo_grupo).first()
    if not grupo:
        raise HTTPException(status_code=400, detail="Codigo de grupo invalido")

    existente = db.query(Usuario).filter(Usuario.login == login).first()
    if existente:
        raise HTTPException(status_code=400, detail="Esse login ja esta em uso")

    senha_hash = bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()
    novo = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash=senha_hash,
        grupo_id=grupo.id
    )
    db.add(novo)
    db.commit()
    return {"mensagem": "Usuario criado com sucesso", "login": login, "grupo": grupo.nome}


@app.post("/login")
def login(dados: dict, request: Request, db: Session = Depends(get_db)):
    ip = obter_ip(request) or "desconhecido"
    if not _checar_rate_login(ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente em alguns minutos.")
    login = (dados.get("login") or "").strip()
    senha = dados.get("senha") or ""

    if not login or not senha:
        raise HTTPException(status_code=400, detail="login e senha sao obrigatorios")

    usuario = db.query(Usuario).filter(Usuario.login == login).first()
    if not usuario or not bcrypt.checkpw(senha.encode()[:72], usuario.senha_hash.encode()):
        _registrar_falha_login(ip)
        raise HTTPException(status_code=401, detail="login ou senha invalidos")
    _limpar_falhas_login(ip)
    import random as _random
    codigo = "{:06d}".format(_random.randint(0, 999999))
    novo_cod = Codigo2FA(
        id=str(uuid.uuid4()),
        usuario_id=usuario.id,
        login=usuario.login,
        codigo=codigo,
        expira_em=datetime.now() + timedelta(minutes=10),
        usado=False,
    )
    db.add(novo_cod)
    db.commit()
    email_destino = email_do_usuario(db, usuario)
    if email_destino:
        try:
            corpo = "Seu codigo de acesso ao ATOS e: " + codigo + ". Valido por 10 minutos. Se voce nao tentou acessar, ignore este e-mail."
            enviar_email(email_destino, "Codigo de acesso ATOS", corpo)
        except Exception as e:
            print("Erro ao enviar codigo 2FA:", e)
    return {"requer_2fa": True, "login": usuario.login, "mensagem": "Enviamos um codigo de acesso para o seu e-mail."}

@app.post("/login/verificar")
def login_verificar(dados: dict, request: Request, db: Session = Depends(get_db)):
    ip = obter_ip(request) or "desconhecido"
    login = (dados.get("login") or "").strip()
    codigo = (dados.get("codigo") or "").strip()
    if not login or not codigo:
        raise HTTPException(status_code=400, detail="login e codigo sao obrigatorios")
    usuario = db.query(Usuario).filter(Usuario.login == login).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="usuario invalido")
    reg = db.query(Codigo2FA).filter(
        Codigo2FA.login == login,
        Codigo2FA.codigo == codigo,
        Codigo2FA.usado == False,
    ).order_by(Codigo2FA.criado_em.desc()).first()
    if not reg:
        raise HTTPException(status_code=401, detail="codigo invalido")
    if reg.expira_em < datetime.now():
        raise HTTPException(status_code=401, detail="codigo expirado, faca login novamente")
    reg.usado = True
    token = str(uuid.uuid4())
    usuario.token = token
    usuario.token_criado_em = datetime.now()
    db.commit()
    registrar_auditoria(db, usuario, "login", None, "acesso ao sistema (2FA)", ip)
    grupo = db.query(Grupo).filter(Grupo.id == usuario.grupo_id).first()
    return {"token": token, "login": usuario.login, "grupo_id": usuario.grupo_id, "grupo": grupo.nome if grupo else None, "is_admin": bool(usuario.is_admin)}




# ===== ANEXOS DO PROCESSO =====
def notificar_telegram(texto: str):
    """Envia um aviso ao ADM via Telegram. Retorna (chat_id, message_id) ou None."""
    try:
        import os, requests
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return None
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": texto},
            timeout=5,
        )
        j = r.json()
        if j.get("ok"):
            return (str(chat_id), j["result"]["message_id"])
    except Exception:
        pass
    return None

@app.post("/processos/{processo_id}/mensagens")
async def enviar_mensagem(processo_id: str, dados: str = Form(...), request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    if not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    info = json.loads(dados)
    texto = (info.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    msg = MensagemProcesso(
        id=str(uuid.uuid4()),
        processo_id=processo_id,
        autor_login=usuario.login,
        autor_tipo=("admin" if usuario.is_admin else "cliente"),
        texto=texto,
        status_no_momento=p.status,
        tipo_ato_no_momento=p.tipo_ato,
    )
    db.add(msg)
    db.commit()
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "mensagem_processo", processo_id, "", _ip)
    if not usuario.is_admin:
        _grupo = db.query(Grupo).filter(Grupo.id == p.grupo_id).first()
        _empresa = (_grupo.nome if _grupo else None) or p.empresa or "cliente"
        _ato = p.identificador_ato or p.tipo_ato or "processo"
        _preview = texto if len(texto) <= 500 else texto[:500] + "..."
        _aviso = f"O Cliente {_empresa}, no Processo: {_ato}, Usuario: {usuario.login}, fez uma pergunta:\n\n{_preview}"
        _res = notificar_telegram(_aviso)
        if _res:
            _cid, _mid = _res
            db.add(TelegramVinculo(id=str(uuid.uuid4()), telegram_message_id=_mid, chat_id=_cid, processo_id=processo_id))
            db.commit()
    return {"mensagem": "enviada", "id": msg.id}

@app.get("/processos/{processo_id}/mensagens")
async def listar_mensagens(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    if not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    msgs = db.query(MensagemProcesso).filter(MensagemProcesso.processo_id == processo_id).order_by(MensagemProcesso.criado_em.asc()).all()
    return [{"id": mm.id, "autor_login": mm.autor_login, "autor_tipo": mm.autor_tipo, "texto": mm.texto, "criado_em": mm.criado_em.isoformat() if mm.criado_em else None} for mm in msgs]

@app.post("/processos/{processo_id}/anexos")
async def enviar_anexo(processo_id: str, arquivo: UploadFile = File(...), descricao: str = Form(None), request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    if not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    EXT_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".xml", ".txt"}
    if ext not in EXT_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo nao permitido para anexo.")
    conteudo = await arquivo.read()
    if len(conteudo) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Limite de 20 MB.")
    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    anexo_id = str(uuid.uuid4())
    nome_arquivo = "anexo_" + anexo_id + ext
    caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    novo = Anexo(id=anexo_id, processo_id=processo_id, arquivo=nome_arquivo, nome_original=(arquivo.filename or ""), descricao=(descricao or ""), enviado_por=usuario.login)
    db.add(novo)
    db.commit()
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "anexo_upload", processo_id, "arquivo=" + (arquivo.filename or ""), _ip)
    return {"mensagem": "Anexo enviado", "id": anexo_id, "nome_original": arquivo.filename}

@app.get("/processos/{processo_id}/anexos")
def listar_anexos(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    if not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    anexos = db.query(Anexo).filter(Anexo.processo_id == processo_id).order_by(Anexo.criado_em).all()
    return [{"id": a.id, "nome_original": a.nome_original, "descricao": a.descricao, "enviado_por": a.enviado_por, "criado_em": str(a.criado_em)} for a in anexos]

@app.get("/anexos/{anexo_id}/download")
def baixar_anexo(anexo_id: str, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    a = db.query(Anexo).filter(Anexo.id == anexo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Anexo nao encontrado")
    p = db.query(Processo).filter(Processo.id == a.processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este anexo")
    caminho = os.path.join(UPLOADS_DIR, a.arquivo)
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado no disco")
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "anexo_download", a.processo_id, "anexo=" + (a.nome_original or ""), _ip)
    return FileResponse(caminho, filename=(a.nome_original or a.arquivo))

@app.delete("/anexos/{anexo_id}")
def excluir_anexo(anexo_id: str, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    a = db.query(Anexo).filter(Anexo.id == anexo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Anexo nao encontrado")
    p = db.query(Processo).filter(Processo.id == a.processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este anexo")
    caminho = os.path.join(UPLOADS_DIR, a.arquivo)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except Exception as e:
        print("erro ao remover anexo do disco:", e)
    proc_id = a.processo_id
    nome = a.nome_original
    db.delete(a)
    db.commit()
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "anexo_excluir", proc_id, "anexo=" + (nome or ""), _ip)
    return {"mensagem": "Anexo removido"}

@app.get("/download/{processo_id}/{tipo}")
def download(processo_id: str, tipo: str, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    if not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este processo")
    campo_map = {"ata": p.arquivo_ata, "protocolo": p.arquivo_protocolo, "registro": p.arquivo_registro, "nd": p.arquivo_nd, "nf": p.arquivo_nf, "exigencia": p.arquivo_exigencia}
    if tipo not in campo_map:
        raise HTTPException(status_code=400, detail="Tipo invalido")
    nome_arquivo = campo_map[tipo]
    if not nome_arquivo:
        raise HTTPException(status_code=404, detail="Arquivo nao disponivel")
    caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado no disco")
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "download", processo_id, "tipo=" + str(tipo) + " arquivo=" + str(nome_arquivo), _ip)
    return FileResponse(caminho, filename=nome_arquivo)

@app.get("/processos")
def listar_processos(codigo_grupo: str = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    query = db.query(Processo)
    if usuario.is_admin:
        if codigo_grupo:
            grupo = db.query(Grupo).filter(Grupo.codigo == codigo_grupo).first()
            if grupo:
                query = query.filter(Processo.grupo_id == grupo.id)
    else:
        query = query.filter(Processo.grupo_id == usuario.grupo_id)
    from sqlalchemy import case
    processos = query.order_by(
        case((Processo.status == "finalizado", 1), else_=0),
        case((Processo.status == "finalizado", Processo.atualizado_em), else_=Processo.criado_em).desc()
    ).all()
    return processos

@app.get("/processos/{processo_id}")
def obter_processo(processo_id: str, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "visualizar", processo_id, "empresa=" + str(p.empresa), _ip)
    return p

# ===== PARTE 2: deteccao automatica do documento principal =====
TIPOS_PRINCIPAIS = {
    "Contrato Social": ["contrato social"],
    "Alteracao Contratual": ["alteracao do contrato social", "alteracao contratual", "alteração do contrato social", "alteração contratual", "alteracao e consolidacao do contrato social", "alteração e consolidação do contrato social", "alteracao e consolidacao de contrato social", "alteração e consolidação de contrato social", "consolidacao do contrato social", "consolidação do contrato social"],
    "Ata de Reuniao/Assembleia de Socios": ["ata de reuniao de socios", "ata de assembleia de socios", "reuniao de socios", "ata de reunião de sócios", "ata de assembleia de sócios", "reunião de sócios"],
    "Distrato/Dissolucao/Liquidacao": ["distrato", "dissolucao", "liquidacao", "dissolução", "liquidação"],
    "Estatuto Social": ["estatuto social"],
    "Ata de Assembleia Geral de Constituicao": ["assembleia geral de constituicao", "assembleia geral de constituição"],
    "Ata de AGO": ["assembleia geral ordinaria", "assembleia geral ordinária"],
    "Ata de AGE": ["assembleia geral extraordinaria", "assembleia geral extraordinária"],
    "Ata de Reuniao do Conselho de Administracao": ["reuniao do conselho", "conselho de administra", "reunião do conselho"],
    "Ata de Reuniao de Diretoria": ["reuniao de diretoria", "reunião de diretoria"],
    "Escritura de Emissao de Debentures": ["escritura de emissao de debentures", "emissao de debentures", "escritura de emissão de debêntures", "emissão de debêntures"],
    "Boletim/Lista/Carta de Subscricao": ["boletim de subscricao", "lista de subscricao", "carta de subscricao", "boletim de subscrição", "lista de subscrição", "carta de subscrição"],
    "Ata de Assembleia Geral": ["ata de assembleia geral", "ata da assembleia geral"],
}
MARCADORES_ANEXO = [
    "requerimento", "ficha de cadastro nacional", "consulta de viabilidade",
    "documento basico de entrada", "documento básico de entrada",
    "procuracao", "procuração", "declaracao de desimpedimento", "declaração de desimpedimento",
    "darf", "gare", "comprovante de pagamento", "comprovante", "certidao", "certidão",
    "balanco patrimonial", "balanço patrimonial", "sped", "prospecto",
    "diario oficial", "diário oficial",
    "carteira de identidade", "documento de identidade", "doc identidade", "identidade",
    "lista de presenca", "lista de presenca de socios", "lista de presenca de acionistas", "registro geral", "cnh", "carteira nacional de habilitacao", "carteira nacional de habilitação", "habilitacao", "habilitação",
]
EXT_IMAGEM = {".jpg", ".jpeg", ".png"}

def _gemini_texto_documento(caminho_pdf):
    import base64, json, urllib.request
    if not GEMINI_KEY:
        return None
    try:
        with open(caminho_pdf, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode()
        prompt = ("Transcreva todo o texto visivel deste documento (ata, certidao ou comprovante de registro "
                  "de Junta Comercial), incluindo carimbos, selos e textos de certificacao de registro/arquivamento. "
                  "Responda APENAS com o texto transcrito, sem comentarios.")
        body = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}}]}]}
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" + GEMINI_KEY
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=40)
        data = json.loads(resp.read().decode())
        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return txt
    except Exception as e:
        print("Gemini texto documento falhou:", e)
        return None

def _tesseract_texto_documento(caminho_pdf):
    import subprocess, os, glob, tempfile
    try:
        d = tempfile.mkdtemp()
        subprocess.run(["pdftoppm", "-r", "300", "-png", caminho_pdf, os.path.join(d, "pg")], check=True, timeout=90)
        texto = ""
        for img in sorted(glob.glob(os.path.join(d, "*.png"))):
            out = subprocess.run(["tesseract", img, "stdout", "-l", "por"], capture_output=True, text=True, timeout=60)
            if not out.stdout.strip():
                out = subprocess.run(["tesseract", img, "stdout"], capture_output=True, text=True, timeout=60)
            texto += out.stdout + "\n"
        return texto
    except Exception as e:
        print("Tesseract texto documento falhou:", e)
        return None

def _texto_parece_valido(texto: str) -> bool:
    """Detecta texto corrompido (fonte de PDF sem mapeamento Unicode correto).
    Um texto extraido corretamente deve ter alta proporcao de caracteres validos
    e conter palavras comuns em portugues."""
    import re
    if not texto or len(texto.strip()) < 50:
        return False
    validos = re.findall(r"[a-z0-9\u00e1\u00e0\u00e2\u00e3\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00fc\u00e7A-Z\s.,;:()\-/\u00ba\u00aa%]", texto)
    proporcao_valida = len(validos) / max(len(texto), 1)
    if proporcao_valida < 0.85:
        return False
    t = texto.lower()
    palavras_comuns = [" de ", " da ", " do ", " que ", " para ", " com ", " em ", " uma ", " os ", " as ", " e "]
    if not any(p in t for p in palavras_comuns):
        return False
    return True

def _extrair_texto_bytes(conteudo: bytes, nome: str) -> str:
    import tempfile
    nm = (nome or "").lower()
    texto = ""
    try:
        if nm.endswith(".pdf"):
            import fitz
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(conteudo); tmp = f.name
            doc = fitz.open(tmp)
            for page in doc:
                texto += page.get_text()
            doc.close()
            print("DEBUG_EXTRACAO nome=", repr(nome), "| texto_direto_len=", len(texto.strip()), "| trecho=", repr(texto.strip()[:150]))
            if not _texto_parece_valido(texto):
                texto_extra = _gemini_texto_documento(tmp)
                if not texto_extra:
                    texto_extra = _tesseract_texto_documento(tmp)
                if texto_extra:
                    texto = texto_extra
                    print("Texto extraido via OCR/Gemini para:", nome, "| novo_len=", len(texto))
            os.unlink(tmp)
        elif nm.endswith(".docx"):
            import docx as docx_lib
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as f:
                f.write(conteudo); tmp = f.name
            doc = docx_lib.Document(tmp)
            texto = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            os.unlink(tmp)
        else:
            texto = conteudo.decode("utf-8", errors="ignore")
    except Exception:
        texto = ""
    return texto

def _ja_registrada(texto_l: str) -> bool:
    """Detecta se o texto e' de uma ata JA REGISTRADA (comprovante de arquivamento),
    e portanto nunca deve ser tratada como documento principal (novo ato)."""
    tem_certifico = ("certifico o registro" in texto_l) or ("certifico o arquivamento" in texto_l)
    tem_sob_num = "sob o n" in texto_l
    return tem_certifico and tem_sob_num

def _classificar(nome: str, texto: str):
    import os as _os, unicodedata
    def _sa(s):
        s = (s or "").lower()
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    nome_l = _sa(nome)
    texto_l = _sa(texto[:4000])
    ext = _os.path.splitext((nome or "").lower())[1]
    score = 0
    tipo = None
    # PASSO 1 - nome do arquivo (prioridade)
    for t, marcs in TIPOS_PRINCIPAIS.items():
        for m in marcs:
            if _sa(m) in nome_l:
                score += 20
                if tipo is None:
                    tipo = t
    for m in MARCADORES_ANEXO:
        if _sa(m) in nome_l:
            score -= 12
    # PASSO 2 - conteudo (confirma/desempata)
    for t, marcs in TIPOS_PRINCIPAIS.items():
        for m in marcs:
            if _sa(m) in texto_l:
                score += 10
                if tipo is None:
                    tipo = t
    for m in MARCADORES_ANEXO:
        if _sa(m) in texto_l:
            score -= 4
    # PASSO 3 - imagem inclina a anexo (nao proibe)
    if ext in EXT_IMAGEM:
        score -= 6
    _jr = _ja_registrada(texto_l)
    print("DEBUG_JAREG nome=", repr(nome), "| ja_registrada=", _jr, "| trecho=", repr(texto_l[:300]))
    if _jr:
        tipo = None
        score -= 200
    return tipo, score

# ===== APRENDIZADO POR REGRAS ACUMULADAS =====
def _norm_ap(s):
    import unicodedata
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(s.split())

def consultar_regras(nome, texto, db):
    """Retorna (classificacao, tipo_correto, peso) da melhor regra que casa, ou None."""
    base = _norm_ap((nome or "") + " " + (texto[:2000] or ""))
    if not base.strip():
        return None
    regras = db.query(RegraAprendizado).all()
    melhor = None
    for r in regras:
        padrao = _norm_ap(r.padrao)
        if padrao and padrao in base:
            if melhor is None or (r.peso or 1) > (melhor.peso or 1):
                melhor = r
    if melhor:
        return {"classificacao": melhor.classificacao, "tipo_correto": melhor.tipo_correto, "peso": melhor.peso}
    return None

@app.post("/aprendizado/registrar")
async def aprendizado_registrar(dados: str = Form(...), x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador")
    info = json.loads(dados)
    padrao = (info.get("padrao") or "").strip()
    classificacao = (info.get("classificacao") or "").strip()  # "principal" ou "anexo"
    tipo_correto = (info.get("tipo_correto") or "").strip()
    origem = (info.get("origem") or "nome").strip()
    if not padrao:
        raise HTTPException(status_code=400, detail="padrao obrigatorio")
    # se ja existe regra com mesmo padrao normalizado + classificacao, reforca o peso
    alvo = _norm_ap(padrao)
    existente = None
    for r in db.query(RegraAprendizado).all():
        if _norm_ap(r.padrao) == alvo and (r.classificacao or "") == classificacao and (r.tipo_correto or "") == tipo_correto:
            existente = r; break
    if existente:
        existente.peso = (existente.peso or 1) + 1
        db.commit()
        return {"mensagem": "Regra reforcada", "id": existente.id, "peso": existente.peso}
    nova = RegraAprendizado(id=str(uuid.uuid4()), padrao=padrao, origem=origem, classificacao=classificacao, tipo_correto=tipo_correto, peso=1, criado_por=usuario.login)
    db.add(nova)
    db.commit()
    return {"mensagem": "Regra criada", "id": nova.id}

@app.get("/aprendizado/regras")
async def aprendizado_listar(x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador")
    rs = db.query(RegraAprendizado).order_by(RegraAprendizado.peso.desc()).all()
    return [{"id": r.id, "padrao": r.padrao, "origem": r.origem, "classificacao": r.classificacao, "tipo_correto": r.tipo_correto, "peso": r.peso, "criado_por": r.criado_por} for r in rs]

@app.delete("/aprendizado/regras/{regra_id}")
async def aprendizado_apagar(regra_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador")
    r = db.query(RegraAprendizado).filter(RegraAprendizado.id == regra_id).first()
    if r:
        db.delete(r); db.commit()
    return {"mensagem": "Regra removida"}

@app.post("/processos/analisar-pasta")
async def analisar_pasta(arquivos: list[UploadFile] = File(...), x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    itens = []
    for idx, arq in enumerate(arquivos):
        conteudo = await arq.read()
        texto = _extrair_texto_bytes(conteudo, arq.filename or "")
        tipo, score = _classificar(arq.filename or "", texto)
        regra = consultar_regras(arq.filename or "", texto, db)
        regra_aplicada = None
        if regra:
            regra_aplicada = regra.get("classificacao")
            if regra.get("classificacao") == "principal":
                score += 100 + (regra.get("peso") or 1)
                if regra.get("tipo_correto"):
                    tipo = regra.get("tipo_correto")
            elif regra.get("classificacao") == "anexo":
                score -= 100 + (regra.get("peso") or 1)
        itens.append({"indice": idx, "nome": arq.filename or ("arquivo_" + str(idx)), "texto": texto, "tipo": tipo, "score": score, "regra_aplicada": regra_aplicada})
    if not itens:
        raise HTTPException(status_code=400, detail="Nenhum arquivo recebido.")
    ordenados = sorted(itens, key=lambda x: x["score"], reverse=True)
    melhor = ordenados[0]
    maior = melhor["score"]
    bateram_principal = [i for i in itens if i["tipo"] is not None and i["score"] > 0]
    empatados_topo = [i for i in ordenados if i["score"] == maior]
    pendente = (len(bateram_principal) != 1) or (maior <= 0) or (len(empatados_topo) > 1)
    dados = analisar_ata_ia(melhor["texto"]) if melhor["texto"].strip() else {}
    if melhor["tipo"]:
        dados["tipo_ato"] = dados.get("tipo_ato") or melhor["tipo"]
    anexos = [{"indice": i["indice"], "nome": i["nome"]} for i in itens if i["indice"] != melhor["indice"]]
    return {
        "principal": {"indice": melhor["indice"], "nome": melhor["nome"], "tipo_sugerido": melhor["tipo"], "dados": dados, "score": melhor["score"]},
        "anexos": anexos,
        "confirmacao_pendente": pendente,
        "tipos_disponiveis": list(TIPOS_PRINCIPAIS.keys()),
        "candidatos": [{"indice": i["indice"], "nome": i["nome"], "tipo": i["tipo"], "score": i["score"]} for i in ordenados],
    }

def _filtrar_origem_destino(principais_out):
    """Se dois principais do mesmo lote forem a mesma empresa/ato/data mas UFs diferentes,
    e um apontar (uf_destino_transferencia) para a UF do outro, mantem so o de ORIGEM
    (o destino sera criado automaticamente depois, via _criar_processo_transferencia)."""
    def chave(item):
        d = item.get("dados") or {}
        return (_norm(d.get("empresa")), _norm(d.get("identificador_ato")), _norm(d.get("data_ata")))
    descartar = set()
    for i, a in enumerate(principais_out):
        for j, b in enumerate(principais_out):
            if i == j or i in descartar or j in descartar:
                continue
            if chave(a) != chave(b) or not chave(a)[0]:
                continue
            da = a.get("dados") or {}
            db_ = b.get("dados") or {}
            uf_a = (da.get("uf") or "").upper().strip()
            uf_b = (db_.get("uf") or "").upper().strip()
            dest_a = (da.get("uf_destino_transferencia") or "").upper().strip()
            dest_b = (db_.get("uf_destino_transferencia") or "").upper().strip()
            if dest_a and dest_a == uf_b:
                descartar.add(j)  # b e' o destino de a -> descarta b
            elif dest_b and dest_b == uf_a:
                descartar.add(i)  # a e' o destino de b -> descarta a
    return [p for k, p in enumerate(principais_out) if k not in descartar]


def _classificar_lote_ia(itens):
    """Classifica TODOS os documentos de um lote em uma unica chamada de IA,
    substituindo o antigo sistema de palavras-chave (fragil, quebra com qualquer
    variacao de titulo de documento nao prevista). Retorna dict {indice: {"principal": bool, "tipo_ato": str|None}}."""
    import json as _json, urllib.request
    if not GEMINI_KEY or not itens:
        return {}
    partes_doc = []
    for i in itens:
        trecho = (i["texto"] or "")[:3000]
        partes_doc.append(f"--- DOCUMENTO indice={i['indice']} nome=\"{i['nome']}\" ---\n{trecho}\n")
    prompt = (
        "Voce esta analisando um lote de documentos enviados para um sistema de gestao "
        "societaria brasileiro (Juntas Comerciais). Para CADA documento abaixo, determine:\n"
        "1) Se e um ATO PRINCIPAL (um documento que representa um ato societario formal que "
        "vira um processo proprio - ex: ata de assembleia/reuniao, alteracao contratual, "
        "contrato social, estatuto, distrato, protocolo de incorporacao, ata de resolucao de "
        "socio(a), qualquer documento assinado que registra uma deliberacao societaria) OU um "
        "ANEXO (documento de apoio - ex: identidade/CNH/RG de uma pessoa, procuracao, certidao, "
        "comprovante de pagamento, balanco, ficha cadastral, protocolo de junta comercial de "
        "OUTRO processo ja existente).\n"
        "2) Se for ANEXO, qual empresa/CNPJ ele parece se referir (para associa-lo ao ato principal certo).\n"
        "3) Se for PRINCIPAL, qual empresa/CNPJ esse documento se refere.\n\n"
        "Responda APENAS com um JSON no formato exato:\n"
        '{"classificacoes": [{"indice": 0, "principal": true, "empresa_ou_cnpj": "texto"}, '
        '{"indice": 1, "principal": false, "empresa_ou_cnpj": "texto"}]}\n\n'
        "Documentos:\n\n" + "\n".join(partes_doc)
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" + GEMINI_KEY
    try:
        req = urllib.request.Request(url, data=_json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        data = _json.loads(resp.read().decode())
        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        resultado = _json.loads(txt)
        saida = {}
        for c in resultado.get("classificacoes", []):
            saida[c["indice"]] = {"principal": bool(c.get("principal")), "empresa_ou_cnpj": c.get("empresa_ou_cnpj") or ""}
        return saida
    except Exception as e:
        print("Erro na classificacao por IA do lote:", str(e)[:200])
        return {}

def _sa_texto_local(s):
    import unicodedata
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

@app.post("/processos/analisar-pasta-multi")
async def analisar_pasta_multi(arquivos: list[UploadFile] = File(...), x_token: str = Header(None), db: Session = Depends(get_db)):
    """Detecta TODOS os documentos principais numa pasta/subpasta (nao so o melhor).
    Se houver mais de um principal, cada um vira um processo, e os demais arquivos
    (anexos) sao compartilhados/replicados entre todos os processos gerados."""
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    itens = []
    for idx, arq in enumerate(arquivos):
        conteudo = await arq.read()
        texto = _extrair_texto_bytes(conteudo, arq.filename or "")
        ja_reg_flag = _ja_registrada(_sa_texto_local(texto[:4000]))
        itens.append({"indice": idx, "nome": arq.filename or ("arquivo_" + str(idx)), "texto": texto, "ja_reg": ja_reg_flag})
    if not itens:
        raise HTTPException(status_code=400, detail="Nenhum arquivo recebido.")

    # CLASSIFICACAO POR IA (uma chamada para o lote inteiro) - substitui o antigo
    # sistema de palavras-chave, que quebrava com qualquer variacao de titulo nao
    # prevista. Documentos ja registrados nunca sao candidatos.
    candidatos_ia = [i for i in itens if not i.get("ja_reg")]
    classificacao_ia = _classificar_lote_ia(candidatos_ia)

    principais_itens = []
    pendente = False
    for i in candidatos_ia:
        c = classificacao_ia.get(i["indice"])
        if c is None:
            principais_itens.append(i)
            pendente = True
        elif c.get("principal"):
            principais_itens.append(i)

    indices_principais = {i["indice"] for i in principais_itens}
    anexos = [{"indice": i["indice"], "nome": i["nome"]} for i in itens if i["indice"] not in indices_principais]

    principais_out = []
    for i in principais_itens:
        dados = analisar_ata_ia(i["texto"]) if i["texto"].strip() else {}
        principais_out.append({"indice": i["indice"], "nome": i["nome"], "tipo_sugerido": dados.get("tipo_ato"), "dados": dados, "score": 0})

    for _pp in principais_out:
        _dd = _pp.get("dados") or {}
        print("DEBUG_DEDUP antes: nome=", _pp.get("nome"), "| empresa=", _dd.get("empresa"), "| ato=", _dd.get("identificador_ato"), "| data=", _dd.get("data_ata"), "| uf=", _dd.get("uf"), "| uf_destino=", _dd.get("uf_destino_transferencia"))
    principais_out = _filtrar_origem_destino(principais_out)
    print("DEBUG_DEDUP depois: total=", len(principais_out))

    return {
        "principais": principais_out,
        "anexos": anexos,
        "multiplo": len(principais_out) > 1,
        "confirmacao_pendente": pendente,
        "tipos_disponiveis": list(TIPOS_PRINCIPAIS.keys()),
    }

@app.get("/processos/pendentes")
async def listar_pendentes(x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador")
    ps = db.query(Processo).filter(Processo.confirmacao_pendente == True).all()
    return [{"id": p.id, "empresa": p.empresa, "tipo_ato": p.tipo_ato, "tipo_ato_sugerido": p.tipo_ato_sugerido, "identificador_ato": p.identificador_ato, "data_ata": p.data_ata} for p in ps]

@app.post("/processos/{processo_id}/confirmar-tipo")
async def confirmar_tipo(processo_id: str, dados: str = Form(...), request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    info = json.loads(dados)
    novo_tipo = (info.get("tipo_ato") or "").strip()
    if novo_tipo:
        p.tipo_ato = novo_tipo
    p.confirmacao_pendente = False
    db.commit()
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "confirmar_tipo", processo_id, "tipo=" + (novo_tipo or p.tipo_ato or ""), _ip)
    return {"mensagem": "Tipo confirmado", "id": processo_id, "tipo_ato": p.tipo_ato}

def _norm(s):
    import unicodedata
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(s.split())

@app.get("/processos/checar-duplicidade")
async def checar_duplicidade(empresa: str = "", tipo_ato: str = "", data_ata: str = "", hora_ata: str = "", identificador_ato: str = "", x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    q = db.query(Processo)
    if not usuario.is_admin:
        q = q.filter(Processo.grupo_id == usuario.grupo_id)
    alvo = (_norm(empresa), _norm(tipo_ato), _norm(data_ata), _norm(hora_ata), _norm(identificador_ato))
    for p in q.all():
        atual = (_norm(p.empresa), _norm(p.tipo_ato), _norm(p.data_ata), _norm(p.hora_ata), _norm(p.identificador_ato))
        if atual == alvo and any(alvo):
            return {"duplicado": True, "processo_id": p.id, "empresa": p.empresa, "identificador_ato": p.identificador_ato}
    return {"duplicado": False}

@app.post("/processos/analisar")
async def analisar_documento(arquivo: UploadFile = File(...), x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")

    conteudo = await arquivo.read()
    nome = arquivo.filename or ""
    texto = _extrair_texto_bytes(conteudo, nome)

    dados = analisar_ata_ia(texto)
    return dados

@app.post("/processos")
async def criar_processo(
    arquivo: UploadFile = File(None),
    dados: str = Form(...),
    x_token: str = Header(None),
    db: Session = Depends(get_db)
):
    info = json.loads(dados)
    processo_id = f"MN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario_tok = validar_token(x_token, db)
    if not usuario_tok:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")

    obrigatorios = {
        "empresa": (info.get("empresa") or "").strip(),
        "tipo_ato": (info.get("tipo_ato") or "").strip(),
        "data_ata": (info.get("data_ata") or "").strip(),
    }
    faltando = [campo for campo, valor in obrigatorios.items() if not valor]
    # URGENTE - NUNCA bloquear a insercao do processo por falta de campo extraido.
    # Sempre insere o processo, marca para revisao manual, e avisa o administrador.

    grupo_id = None
    if usuario_tok.is_admin:
        codigo_grupo = info.get("codigo_grupo", "").strip()
        if codigo_grupo:
            grupo = db.query(Grupo).filter(Grupo.codigo == codigo_grupo).first()
            if not grupo:
                raise HTTPException(status_code=400, detail=f"Grupo com codigo '{codigo_grupo}' nao encontrado")
            grupo_id = grupo.id
    else:
        grupo_id = usuario_tok.grupo_id

    arquivo_ata = None
    if arquivo:
        ext = os.path.splitext(arquivo.filename)[1]
        nome_arquivo = f"{processo_id}_ata{ext}"
        caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
        with open(caminho, "wb") as f:
            f.write(await arquivo.read())
        arquivo_ata = nome_arquivo

    p = Processo(
        id=processo_id,
        empresa=info.get("empresa", ""),
        cnpj=info.get("cnpj", ""),
        nire=info.get("nire", ""),
        uf=(info.get("uf") or "").upper().strip()[:2],
        tipo_sociedade=info.get("tipo_sociedade", ""),
        tipo_ato=info.get("tipo_ato", ""),
        identificador_ato=info.get("identificador_ato", ""),
        data_ata=info.get("data_ata", ""),
        hora_ata=info.get("hora_ata", ""),
        email_cliente=info.get("email_cliente", ""),
        eventos=json.dumps(info.get("eventos", []), ensure_ascii=False),
        checklist=json.dumps(info.get("checklist", []), ensure_ascii=False),
        requer_cpl=info.get("requer_cpl", False),
        observacoes=info.get("observacoes", ""),
        status="aberto",
        arquivo_ata=arquivo_ata,
        grupo_id=grupo_id,
        uf_destino_transferencia=(info.get("uf_destino_transferencia") or "").upper().strip()[:2] or None
    )
    db.add(p)
    db.commit()
    try:
        corpo = "Processo Inserido no Atos:\n\n" + corpo_status_cliente(p, "Aberto", "")
        for em in emails_do_grupo(db, grupo_id):
            enviar_email(em, "Processo inserido no Atos - " + (p.empresa or ""), corpo)
    except Exception as e:
        print("Erro ao notificar abertura:", e)
    if faltando:
        try:
            p.confirmacao_pendente = True
            db.commit()
            enviar_email(EMAIL_ADMIN, "[Atos] ATENCAO - Processo inserido com campos incompletos - " + (p.empresa or processo_id),
                "O processo " + processo_id + " (" + (p.empresa or "sem nome") + ") foi inserido no sistema, mas a extracao automatica nao conseguiu identificar: " + ", ".join(faltando) + ".\n\nRevise manualmente e complete os dados faltantes o quanto antes.")
        except Exception as e:
            print("Erro ao notificar campos incompletos:", e)
    return {"id": processo_id, "mensagem": "Processo criado com sucesso"}

def _criar_processo_transferencia(db, p_origem):
    """Cria automaticamente o processo de destino apos a origem ser finalizada,
    quando a ata identificou transferencia de sede interestadual."""
    uf_destino = (p_origem.uf_destino_transferencia or "").strip().upper()
    if not uf_destino or p_origem.transferencia_criada:
        return None
    novo_id = f"MN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
    obs = f"Processo criado automaticamente apos transferencia de sede. Origem: {p_origem.id} ({p_origem.uf or '-'})."
    novo = Processo(
        id=novo_id,
        empresa=p_origem.empresa,
        cnpj=p_origem.cnpj,
        nire=p_origem.nire,
        uf=uf_destino,
        tipo_sociedade=p_origem.tipo_sociedade,
        tipo_ato=p_origem.tipo_ato,
        identificador_ato=(p_origem.identificador_ato or "") + " - Transferencia de Sede (Destino)",
        data_ata=p_origem.data_ata,
        hora_ata=p_origem.hora_ata,
        email_cliente=p_origem.email_cliente,
        observacoes=obs,
        status="aberto",
        grupo_id=p_origem.grupo_id,
        processo_origem_id=p_origem.id,
    )
    db.add(novo)
    db.flush()
    # anexa a ata de origem (ja registrada) como comprovante no processo novo
    if p_origem.arquivo_ata:
        try:
            origem_path = os.path.join(UPLOADS_DIR, p_origem.arquivo_ata)
            if os.path.exists(origem_path):
                ext = os.path.splitext(p_origem.arquivo_ata)[1]
                anexo_id = str(uuid.uuid4())
                nome_anexo = "anexo_" + anexo_id + ext
                destino_path = os.path.join(UPLOADS_DIR, nome_anexo)
                with open(origem_path, "rb") as fr, open(destino_path, "wb") as fw:
                    fw.write(fr.read())
                db.add(Anexo(
                    id=anexo_id, processo_id=novo_id, arquivo=nome_anexo,
                    nome_original="Ata registrada (origem " + (p_origem.uf or "") + ")",
                    descricao="Comprovante de registro na Junta de origem, anexado automaticamente.",
                    enviado_por="sistema",
                ))
        except Exception as e:
            print("Erro ao anexar ata de origem no processo de transferencia:", e)
    p_origem.transferencia_criada = True
    db.commit()
    try:
        notificar_telegram(f"ATOS - Transferencia de sede\nProcesso de destino criado: {novo_id}\nEmpresa: {p_origem.empresa}\nDestino: {uf_destino}\nAguardando protocolo.")
    except Exception:
        pass
    return novo_id

def recalcular_status(p):
    # Prioridade: registro(finalizado) > exigencia > deferido(automacao) > protocolo(tramitacao) > aberto
    if p.arquivo_registro:
        return "finalizado"
    if getattr(p, "exigencia_ativa", False):
        return "exigencia"
    if (p.status or "").lower() == "deferido":
        return "deferido"
    if p.numero_protocolo or p.arquivo_protocolo:
        return "tramitacao"
    return "aberto"


@app.patch("/processos/{processo_id}")
def atualizar_processo(processo_id: str, dados: dict, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "editar", processo_id, "campos=" + ",".join(list(dados.keys())), _ip)
    for campo, valor in dados.items():
        if hasattr(p, campo):
            setattr(p, campo, valor)
    # Reinserir/atualizar protocolo cumpre a exigencia ativa
    if ("numero_protocolo" in dados or "arquivo_protocolo" in dados) and getattr(p, "exigencia_ativa", False):
        p.exigencia_ativa = False
    status_antes_patch = (p.status or "").lower()
    p.status = recalcular_status(p)
    p.atualizado_em = datetime.now()
    db.commit()
    if status_antes_patch != "tramitacao" and (p.status or "").lower() == "tramitacao":
        tem_numero = bool((p.numero_protocolo or "").strip())
        tem_pdf = bool((p.arquivo_protocolo or "").strip())
        if tem_numero and tem_pdf:
            try:
                corpo = corpo_status_cliente(p, "Tramitacao", "Aguardando analise da Junta Comercial.")
                cam = os.path.join(UPLOADS_DIR, p.arquivo_protocolo)
                for em in emails_do_grupo(db, p.grupo_id):
                    enviar_email_anexo(em, "Atualizacao do seu processo - " + (p.empresa or ""), corpo, cam, p.arquivo_protocolo)
            except Exception as e:
                print("Erro ao notificar tramitacao:", e)
        else:
            print("Tramitacao sem email - falta numero ou pdf. numero:", tem_numero, "pdf:", tem_pdf)
    return {"mensagem": "Atualizado com sucesso"}

@app.post("/processos/{processo_id}/upload/{tipo}")
async def upload_arquivo(
    processo_id: str,
    tipo: str,
    arquivo: UploadFile = File(...),
    request: Request = None,
    x_token: str = Header(None),
    db: Session = Depends(get_db)
):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    # validacao: so extensoes permitidas
    EXT_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg"}
    if ext not in EXT_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo nao permitido. Envie PDF ou imagem.")
    # validacao: tamanho maximo 20 MB
    conteudo = await arquivo.read()
    MAX_BYTES = 20 * 1024 * 1024
    if len(conteudo) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Limite de 20 MB.")
    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    # validacao: se diz ser PDF, conferir a assinatura real do arquivo
    if ext == ".pdf" and not conteudo[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Arquivo nao e um PDF valido.")
    nome_arquivo = f"{processo_id}_{tipo}{ext}"
    caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "upload", processo_id, "tipo=" + str(tipo) + " arquivo=" + str(nome_arquivo), _ip)

    campo_map = {
        "protocolo": "arquivo_protocolo",
        "registro": "arquivo_registro",
        "nd": "arquivo_nd",
        "nf": "arquivo_nf"
    }
    if tipo in campo_map:
        status_antes_up = (p.status or "").lower()
        setattr(p, campo_map[tipo], nome_arquivo)
        if tipo == "protocolo":
            _num = extrair_protocolo_ocr(caminho)
            if _num:
                p.numero_protocolo = _num
                print("OCR protocolo detectado:", _num)
        if tipo == "protocolo" and getattr(p, "exigencia_ativa", False):
            p.exigencia_ativa = False
        if tipo != "protocolo":
            p.status = recalcular_status(p)
        p.atualizado_em = datetime.now()
        db.commit()
        try:
            novo_status = (p.status or "").lower()
            if tipo == "registro" and novo_status == "finalizado":
                corpo = corpo_status_cliente(p, "Finalizado", "Seu Processo foi Finalizado, em Anexo o Registro.")
                for em in emails_do_grupo(db, p.grupo_id):
                    enviar_email_anexo(em, "Processo Finalizado - " + (p.empresa or ""), corpo, caminho, nome_arquivo)
                try:
                    _criar_processo_transferencia(db, p)
                except Exception as e:
                    print("Erro ao criar processo de transferencia:", e)
        except Exception as e:
            print("Erro ao notificar upload:", e)

    return {"mensagem": f"Arquivo {tipo} salvo", "arquivo": nome_arquivo, "numero_protocolo": (p.numero_protocolo or "")}

@app.post("/processos/{processo_id}/exigencia")
async def registrar_exigencia(
    processo_id: str,
    texto: str = Form(""),
    arquivo: UploadFile = File(None),
    x_token: str = Header(None),
    db: Session = Depends(get_db)
):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    p.texto_exigencia = texto
    if arquivo is not None:
        ext = os.path.splitext(arquivo.filename)[1]
        nome_arquivo = f"{processo_id}_exigencia{ext}"
        caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
        with open(caminho, "wb") as f:
            f.write(await arquivo.read())
        p.arquivo_exigencia = nome_arquivo
    p.exigencia_ativa = True
    p.status = recalcular_status(p)
    p.atualizado_em = datetime.now()
    db.commit()
    if arquivo is not None and p.arquivo_exigencia:
        try:
            cam = os.path.join(UPLOADS_DIR, p.arquivo_exigencia)
            for em in emails_do_grupo(db, p.grupo_id):
                enviar_email_anexo(em, "Exigencia no seu processo - " + (p.empresa or ""), "Seu processo recebeu uma exigencia, segue em anexo o documento", cam, p.arquivo_exigencia)
        except Exception as e:
            print("Erro ao notificar exigencia ao cliente:", e)
    return {"mensagem": "Exigencia registrada", "status": p.status}


@app.post("/processos/{processo_id}/exigencia/cumprida")
def exigencia_cumprida(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    p.exigencia_ativa = False
    p.status = recalcular_status(p)
    p.atualizado_em = datetime.now()
    db.commit()
    return {"mensagem": "Exigencia marcada como cumprida", "status": p.status}

@app.delete("/processos/{processo_id}")
def excluir_processo(processo_id: str, request: Request = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administrador pode excluir processos")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    _ip = obter_ip(request)
    registrar_auditoria(db, usuario, "excluir", processo_id, "empresa=" + str(p.empresa) + " cnpj=" + str(p.cnpj), _ip)
    db.delete(p)
    db.commit()
    return {"mensagem": "Processo excluido"}

@app.post("/processos/{processo_id}/exigencia/aguardando-cliente")
def exigencia_aguardando_cliente(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    p.aguardando_cliente = True
    p.atualizado_em = datetime.now()
    db.commit()
    return {"mensagem": "Marcado como aguardando cliente", "aguardando_cliente": True}


@app.get("/grupos")
def listar_grupos(x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")
    grupos = db.query(Grupo).order_by(Grupo.nome).all()
    return [{"id": g.id, "nome": g.nome, "codigo": g.codigo} for g in grupos]

@app.post("/grupos/criar")
def criar_grupo(dados: dict, background: BackgroundTasks, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")

    nome = (dados.get("nome") or "").strip()
    emails = dados.get("emails") or []
    emails = [e.strip() for e in emails if e and e.strip()]

    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do grupo")
    if not emails:
        raise HTTPException(status_code=400, detail="Informe ao menos um email")

    existente = db.query(Grupo).filter(Grupo.nome == nome).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ja existe um grupo chamado '{nome}'")

    base = "".join(ch for ch in nome.upper() if ch.isalnum())[:8] or "GRUPO"
    codigo = f"{base}-{uuid.uuid4().hex[:4].upper()}"
    grupo = Grupo(id=str(uuid.uuid4()), nome=nome, codigo=codigo)
    db.add(grupo)
    db.commit()

    link = f"{BASE_URL_SISTEMA}/cliente?grupo={codigo}"
    for email in emails:
        ja = db.query(EmailGrupo).filter(EmailGrupo.email == email, EmailGrupo.grupo_id == grupo.id).first()
        if not ja:
            db.add(EmailGrupo(id=str(uuid.uuid4()), email=email, grupo_id=grupo.id))
            db.commit()
    background.add_task(_disparar_convites, nome, link, emails)
    enviados = emails
    falharam = []

    return {
        "mensagem": "Grupo criado com sucesso",
        "grupo": nome,
        "codigo": codigo,
        "emails_enviados": enviados,
        "emails_falharam": falharam,
        "link": link
    }


@app.get("/relatorio")
def gerar_relatorio(status: str = "todos", x_token: str = Header(None), db: Session = Depends(get_db)):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from fastapi.responses import StreamingResponse
    import io
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido")
    query = db.query(Processo).filter(Processo.grupo_id == usuario.grupo_id)
    if status and status != "todos":
        query = query.filter(Processo.status == status)
    from sqlalchemy import case
    processos = query.order_by(
        case((Processo.status == "finalizado", 1), else_=0),
        case((Processo.status == "finalizado", Processo.atualizado_em), else_=Processo.criado_em).desc()
    ).all()
    rotulos = {"recebido": "Aberto", "tramitacao": "Tramitacao", "exigencia": "Exigencia", "aprovado": "Deferido"}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Processos"
    cabecalho = ["Empresa", "CNPJ", "UF", "Ato", "Protocolo", "Status"]
    ws.append(cabecalho)
    for c in range(1, len(cabecalho) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4D52")
    for p in processos:
        ws.append([
            p.empresa or "",
            p.cnpj or "",
            p.uf or "",
            p.identificador_ato or p.tipo_ato or "",
            (p.numero_protocolo or ""),
            rotulos.get(p.status, p.status or ""),
        ])
    larguras = [42, 22, 6, 50, 16, 14]
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nome = f"relatorio_{status}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={nome}"})


@app.get("/metricas")
def metricas(x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    base = db.query(Processo)
    if not usuario.is_admin:
        base = base.filter(Processo.grupo_id == usuario.grupo_id)
    total = base.count()
    tramitacao = base.filter(Processo.status == "tramitacao").count()
    exigencia = base.filter(Processo.status == "exigencia").count()
    aprovado = base.filter(Processo.status == "aprovado").count()
    deferido = base.filter(Processo.status == "deferido").count()
    finalizado = base.filter(Processo.status == "finalizado").count()
    cobranca_pendente = base.filter(
        Processo.status.in_(["aprovado", "finalizado"]),
        Processo.nf_enviada == False
    ).count()
    return {
        "total": total,
        "tramitacao": tramitacao,
        "exigencia": exigencia,
        "aprovado": aprovado,
        "deferido": deferido,
        "finalizado": finalizado,
        "cobranca_pendente": cobranca_pendente
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)