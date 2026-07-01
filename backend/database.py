from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'mane.db')}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(String, primary_key=True)
    nome = Column(String, nullable=False)
    codigo = Column(String, unique=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.now)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    email = Column(String, nullable=True)
    grupo_id = Column(String, nullable=False)
    token = Column(String, nullable=True)
    token_criado_em = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.now)

class EmailGrupo(Base):
    __tablename__ = "emails_grupo"
    id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    grupo_id = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.now)


class Codigo2FA(Base):
    __tablename__ = "codigos_2fa"
    id = Column(String, primary_key=True)
    usuario_id = Column(String, nullable=False)
    login = Column(String, nullable=False)
    codigo = Column(String, nullable=False)
    expira_em = Column(DateTime, nullable=False)
    usado = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.now)

class Anexo(Base):
    __tablename__ = "anexos"
    id = Column(String, primary_key=True)
    processo_id = Column(String, nullable=False)
    arquivo = Column(String, nullable=False)
    nome_original = Column(String)
    descricao = Column(String)
    enviado_por = Column(String)
    criado_em = Column(DateTime, default=datetime.now)

class RegraAprendizado(Base):
    __tablename__ = "regras_aprendizado"
    id = Column(String, primary_key=True)
    padrao = Column(Text, nullable=False)
    origem = Column(String)
    classificacao = Column(String)
    tipo_correto = Column(String)
    peso = Column(Integer, default=1)
    criado_por = Column(String)
    criado_em = Column(DateTime, default=datetime.now)

class MensagemProcesso(Base):
    __tablename__ = "mensagens_processo"
    id = Column(String, primary_key=True)
    processo_id = Column(String, nullable=False)
    autor_login = Column(String)
    autor_tipo = Column(String)
    texto = Column(Text, nullable=False)
    status_no_momento = Column(String)
    tipo_ato_no_momento = Column(String)
    criado_em = Column(DateTime, default=datetime.now)

class TelegramVinculo(Base):
    __tablename__ = "telegram_vinculos"
    id = Column(String, primary_key=True)
    telegram_message_id = Column(Integer)
    chat_id = Column(String)
    processo_id = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    usuario_login = Column(String)
    usuario_id = Column(String)
    grupo_id = Column(String)
    is_admin = Column(Boolean, default=False)
    acao = Column(String, nullable=False)
    processo_id = Column(String)
    detalhe = Column(String)
    ip = Column(String)
    data_hora = Column(DateTime, default=datetime.now)

class Processo(Base):
    __tablename__ = "processos"
    id = Column(String, primary_key=True)
    empresa = Column(String, nullable=False)
    cnpj = Column(String, nullable=False)
    nire = Column(String)
    tipo_sociedade = Column(String)
    tipo_ato = Column(String, nullable=False)
    identificador_ato = Column(String)
    data_ata = Column(String)
    hora_ata = Column(String)
    data_recebimento = Column(DateTime, default=datetime.now)
    status = Column(String, default="recebido")
    numero_protocolo = Column(String)
    data_protocolo = Column(String)
    data_registro = Column(String)
    eventos = Column(Text)
    checklist = Column(Text)
    requer_cpl = Column(Boolean, default=False)
    observacoes = Column(Text)
    valor_cobranca = Column(Float)
    numero_nf = Column(String)
    nf_enviada = Column(Boolean, default=False)
    email_cliente = Column(String)
    arquivo_ata = Column(String)
    arquivo_protocolo = Column(String)
    arquivo_registro = Column(String)
    arquivo_nd = Column(String)
    arquivo_nf = Column(String)
    criado_em = Column(DateTime, default=datetime.now)
    grupo_id = Column(String, nullable=True)
    uf = Column(String, nullable=True)
    texto_exigencia = Column(Text, nullable=True)
    arquivo_exigencia = Column(String, nullable=True)
    exigencia_ativa = Column(Boolean, default=False)
    status_jucesp = Column(String, nullable=True)
    confirmacao_pendente = Column(Boolean, default=False)
    tipo_ato_sugerido = Column(String, nullable=True)
    ultima_consulta_em = Column(DateTime, nullable=True)
    ultimo_alerta_em = Column(DateTime, nullable=True)
    aguardando_cliente = Column(Boolean, default=False)
    avisado_deferido = Column(Boolean, default=False)
    atualizado_em = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def criar_banco():
    Base.metadata.create_all(bind=engine)
    print("Banco de dados criado!")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    criar_banco()