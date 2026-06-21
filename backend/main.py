from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import get_db, Processo, Grupo, Usuario, EmailGrupo, criar_banco
from datetime import datetime
from openai import OpenAI
import json, os, uuid, shutil, bcrypt

from dotenv import load_dotenv
import os
load_dotenv()

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT_SMTP = int(os.getenv("EMAIL_PORT_SMTP", "587"))
BASE_URL_SISTEMA = os.getenv("BASE_URL_SISTEMA", "https://atos.net.br")

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
        print(f"Erro ao enviar email para {destinatario}: {e}")
        return False

def _disparar_convites(nome, link, emails):
    corpo = (
        "Ola!\n\n"
        "Voce foi cadastrado para acessar o sistema Atos - Gestao Societaria, no grupo " + nome + ".\n\n"
        "Para criar seu usuario e senha de acesso, clique no link abaixo:\n"
        + link + "\n\n"
        "Apos criar seu acesso, voce podera acompanhar seus processos pelo endereco " + BASE_URL_SISTEMA + ".\n\n"
        "Atenciosamente,\nEquipe Atos"
    )
    for email in emails:
        enviar_email(email, "Acesso ao sistema Atos - " + nome, corpo)


app = FastAPI(title="Mané API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")  # desativado: arquivos agora so via /download protegido

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

Retorne APENAS um JSON válido com esta estrutura exata:
{{
  "empresa": "nome completo da empresa",
  "cnpj": "XX.XXX.XXX/XXXX-XX",
  "nire": "número NIRE se encontrado",
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
    return json.loads(texto_limpo)

# ============================================================
# ROTAS
# ============================================================
@app.get("/")
def root():
    return {"status": "Mané online"}


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
def login(dados: dict, db: Session = Depends(get_db)):
    login = (dados.get("login") or "").strip()
    senha = dados.get("senha") or ""

    if not login or not senha:
        raise HTTPException(status_code=400, detail="login e senha sao obrigatorios")

    usuario = db.query(Usuario).filter(Usuario.login == login).first()
    if not usuario or not bcrypt.checkpw(senha.encode()[:72], usuario.senha_hash.encode()):
        raise HTTPException(status_code=401, detail="login ou senha invalidos")

    token = str(uuid.uuid4())
    usuario.token = token
    db.commit()
    grupo = db.query(Grupo).filter(Grupo.id == usuario.grupo_id).first()
    return {"token": token, "login": usuario.login, "grupo_id": usuario.grupo_id, "grupo": grupo.nome if grupo else None, "is_admin": bool(usuario.is_admin)}


@app.get("/download/{processo_id}/{tipo}")
def download(processo_id: str, tipo: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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
    return FileResponse(caminho, filename=nome_arquivo)

@app.get("/processos")
def listar_processos(codigo_grupo: str = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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
    processos = query.order_by(Processo.criado_em.desc()).all()
    return processos

@app.get("/processos/{processo_id}")
def obter_processo(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return p

@app.post("/processos/analisar")
async def analisar_documento(arquivo: UploadFile = File(...), x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    import fitz
    import docx as docx_lib

    conteudo = await arquivo.read()
    nome = arquivo.filename.lower()
    texto = ""

    if nome.endswith(".pdf"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(conteudo)
            tmp = f.name
        doc = fitz.open(tmp)
        for page in doc:
            texto += page.get_text()
        doc.close()
        os.unlink(tmp)
    elif nome.endswith(".docx"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as f:
            f.write(conteudo)
            tmp = f.name
        doc = docx_lib.Document(tmp)
        texto = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        os.unlink(tmp)
    else:
        texto = conteudo.decode("utf-8", errors="ignore")

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
    usuario_tok = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario_tok:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
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
        status="recebido",
        arquivo_ata=arquivo_ata,
        grupo_id=grupo_id
    )
    db.add(p)
    db.commit()
    return {"id": processo_id, "mensagem": "Processo criado com sucesso"}

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
def atualizar_processo(processo_id: str, dados: dict, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    for campo, valor in dados.items():
        if hasattr(p, campo):
            setattr(p, campo, valor)
    # Reinserir/atualizar protocolo cumpre a exigencia ativa
    if ("numero_protocolo" in dados or "arquivo_protocolo" in dados) and getattr(p, "exigencia_ativa", False):
        p.exigencia_ativa = False
    p.status = recalcular_status(p)
    p.atualizado_em = datetime.now()
    db.commit()
    return {"mensagem": "Atualizado com sucesso"}

@app.post("/processos/{processo_id}/upload/{tipo}")
async def upload_arquivo(
    processo_id: str,
    tipo: str,
    arquivo: UploadFile = File(...),
    x_token: str = Header(None),
    db: Session = Depends(get_db)
):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if p and not usuario.is_admin and p.grupo_id != usuario.grupo_id:
        raise HTTPException(status_code=403, detail="Sem permissao para este processo")
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    ext = os.path.splitext(arquivo.filename)[1]
    nome_arquivo = f"{processo_id}_{tipo}{ext}"
    caminho = os.path.join(UPLOADS_DIR, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(await arquivo.read())

    campo_map = {
        "protocolo": "arquivo_protocolo",
        "registro": "arquivo_registro",
        "nd": "arquivo_nd",
        "nf": "arquivo_nf"
    }
    if tipo in campo_map:
        setattr(p, campo_map[tipo], nome_arquivo)
        if tipo == "protocolo" and getattr(p, "exigencia_ativa", False):
            p.exigencia_ativa = False
        p.status = recalcular_status(p)
        p.atualizado_em = datetime.now()
        db.commit()

    return {"mensagem": f"Arquivo {tipo} salvo", "arquivo": nome_arquivo}

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
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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
    return {"mensagem": "Exigencia registrada", "status": p.status}


@app.post("/processos/{processo_id}/exigencia/cumprida")
def exigencia_cumprida(processo_id: str, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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


@app.get("/grupos")
def listar_grupos(x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario or not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")
    grupos = db.query(Grupo).order_by(Grupo.nome).all()
    return [{"id": g.id, "nome": g.nome, "codigo": g.codigo} for g in grupos]

@app.post("/grupos/criar")
def criar_grupo(dados: dict, background: BackgroundTasks, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido")
    query = db.query(Processo).filter(Processo.grupo_id == usuario.grupo_id)
    if status and status != "todos":
        query = query.filter(Processo.status == status)
    processos = query.order_by(Processo.criado_em.desc()).all()
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
    usuario = db.query(Usuario).filter(Usuario.token == x_token).first()
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