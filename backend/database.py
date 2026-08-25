from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Boolean, Integer, Date
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
    nome = Column(String, nullable=True)
    grupo_id = Column(String, nullable=False)
    token = Column(String, nullable=True)
    token_criado_em = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    # "admin" (superadmin, acesso total) | "operador" (acesso a tela administrativa,
    # sem config/usuarios/identidade visual) | "cliente" (portal do cliente).
    # is_admin continua True somente para papel "admin" - operador usa is_admin=False
    # de proposito, pra herdar automaticamente todo bloqueio ja existente baseado em
    # is_admin (config, usuarios, exclusao de processo/anexo) sem precisar tocar nesses
    # endpoints. Endpoints que devem liberar operador usam _tem_acesso_admin() em vez
    # de checar is_admin direto.
    papel = Column(String, default="cliente")
    # Convite de primeiro acesso (definir senha propria): token de uso unico,
    # limpo (None) assim que a senha e definida ou nunca gerado pra quem
    # sempre teve senha definida pelo fluxo antigo (cliente via /cadastro).
    token_convite = Column(String, nullable=True)
    convite_expira_em = Column(DateTime, nullable=True)
    # Plano da conta: None = conta de Grupo tradicional (criada por admin, sem
    # limite de plano). "free" = Usuario Individual auto-cadastrado via
    # /solicitar-acesso (ver main.py) - bloqueado de iatos e consulta
    # automatica as Juntas. Futuros planos pagos usam esse mesmo campo
    # ("pro", "premium").
    plano = Column(String, nullable=True)
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
    # Nome de exibicao calculado uma unica vez no upload (regra "- JUNTA",
    # ver backend/nomenclatura.py), reutilizado na listagem/download - nunca
    # recalculado. NULL em anexos antigos, anteriores a essa coluna: cai no
    # fallback pro nome_original sem transformacao.
    nome_exibicao = Column(String, nullable=True)
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

class AssistenteConversa(Base):
    __tablename__ = "assistente_conversas"
    id = Column(String, primary_key=True)
    processo_id = Column(String, nullable=False)
    usuario_id = Column(String, nullable=True)
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    nivel_confianca = Column(String, nullable=True)  # alta | media | baixa
    secao_usada = Column(String, nullable=True)  # ancora da base de conhecimento usada como contexto (auditoria/debug)
    escalado_admin = Column(Boolean, default=False)
    # so' preenchido quando escalado_admin=True: "falha_tecnica" (Gemini fora do ar/erro
    # mesmo apos retries) ou "baixa_confianca" (base de conhecimento nao cobre a pergunta).
    # Permite monitorar se um dos dois motivos esta acontecendo com frequencia demais.
    motivo_escalonamento = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)


class FonteMonitoramentoNormativo(Base):
    __tablename__ = "fontes_monitoramento_normativo"
    id = Column(String, primary_key=True)
    nome_fonte = Column(String, nullable=False)
    url = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # drei | cvm | junta_estadual | dou
    estado = Column(String, nullable=True)  # UF, se aplicavel
    ultimo_snapshot_hash = Column(String, nullable=True)
    ultimo_snapshot_texto = Column(Text, nullable=True)
    ultima_verificacao = Column(DateTime, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.now)


class MudancaNormativaPendente(Base):
    __tablename__ = "mudancas_normativas_pendentes"
    id = Column(String, primary_key=True)
    fonte_id = Column(String, nullable=False)
    nivel = Column(Integer, nullable=False)
    secao_afetada = Column(String, nullable=True)
    trecho_sugerido = Column(Text, nullable=True)
    justificativa = Column(Text, nullable=True)
    diff_texto = Column(Text, nullable=True)
    status = Column(String, default="pendente")  # pendente | aprovado | rejeitado
    telegram_chat_id = Column(String, nullable=True)
    telegram_message_id = Column(Integer, nullable=True)
    resolvido_por = Column(String, nullable=True)
    resolvido_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)


class LogAtualizacaoNormativa(Base):
    __tablename__ = "logs_atualizacao_normativa"
    id = Column(String, primary_key=True)
    fonte_id = Column(String, nullable=True)
    acao = Column(String, nullable=False)  # verificacao | classificacao | aplicacao | aprovacao | rejeicao | resumo_semanal
    nivel = Column(Integer, nullable=True)
    detalhe = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    usuario_login = Column(String)
    usuario_nome = Column(String)
    usuario_papel = Column(String)
    usuario_id = Column(String)
    grupo_id = Column(String)
    is_admin = Column(Boolean, default=False)
    acao = Column(String, nullable=False)
    processo_id = Column(String)
    detalhe = Column(String)
    ip = Column(String)
    data_hora = Column(DateTime, default=datetime.now)

class Fluxo(Base):
    __tablename__ = "fluxos"
    id = Column(String, primary_key=True)
    grupo_id = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    total_processos = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.now)

class Evento(Base):
    __tablename__ = "eventos"
    id = Column(String, primary_key=True)
    processo_id = Column(String, nullable=False)
    grupo_id = Column(String, nullable=True)
    tipo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    # Autor da acao (para atribuicao visivel na timeline - "por Fulano, dd/mm/aaaa").
    # None/NULL quando o evento foi gerado por automacao sem usuario logado (ex:
    # criacao automatica de processo de transferencia de sede).
    usuario_login = Column(String, nullable=True)
    usuario_nome = Column(String, nullable=True)
    usuario_papel = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)

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
    # Numero de registro da JUCESP (ex: "300.504/26-3") - preenchido quando o
    # processo nao tem protocolo mas o registro foi identificado por outra via
    # (ex: revisao manual). Usado como fallback pro download via Infosimples
    # quando numero_protocolo esta vazio.
    numero_registro = Column(String, nullable=True)
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
    # Nomes de exibicao (regra "- JUNTA", ver backend/nomenclatura.py),
    # calculados uma unica vez no upload sobre o nome original recebido -
    # nunca recalculados no envio de email/download. Usados no lugar do nome
    # fisico (que continua sintetico, ex: "{id}_protocolo.pdf") sempre que
    # existirem; NULL em processos antigos, anteriores a essas colunas, cai
    # no fallback pro nome fisico sem transformacao (nunca tiveram o nome
    # original preservado, entao nao ha o que recalcular retroativamente).
    arquivo_ata_nome_exibicao = Column(String, nullable=True)
    arquivo_protocolo_nome_exibicao = Column(String, nullable=True)
    arquivo_registro_nome_exibicao = Column(String, nullable=True)
    arquivo_nd_nome_exibicao = Column(String, nullable=True)
    arquivo_nf_nome_exibicao = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)
    grupo_id = Column(String, nullable=True)
    uf = Column(String, nullable=True)
    texto_exigencia = Column(Text, nullable=True)
    arquivo_exigencia = Column(String, nullable=True)
    arquivo_exigencia_nome_exibicao = Column(String, nullable=True)
    exigencia_ativa = Column(Boolean, default=False)
    status_jucesp = Column(String, nullable=True)
    uf_destino_transferencia = Column(String, nullable=True)
    transferencia_criada = Column(Boolean, default=False)
    processo_origem_id = Column(String, nullable=True)
    confirmacao_pendente = Column(Boolean, default=False)
    # True quando a leitura do PDF (texto direto + OCR, ver
    # extrair_texto_pdf_em_camadas em main.py) nao conseguiu extrair texto
    # suficiente (camada 3/fallback total) - processo e criado normalmente
    # mesmo assim, so fica marcado pra revisao manual do operador.
    leitura_parcial = Column(Boolean, default=False)
    tipo_ato_sugerido = Column(String, nullable=True)
    ultima_consulta_em = Column(DateTime, nullable=True)
    ultimo_alerta_em = Column(DateTime, nullable=True)
    aguardando_cliente = Column(Boolean, default=False)
    avisado_deferido = Column(Boolean, default=False)
    atualizado_em = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deferido_em = Column(DateTime, nullable=True)
    alertado_atraso_deferido = Column(Boolean, default=False)
    fluxo_id = Column(String, nullable=True)
    # Estado do ultimo evento de e-mail ao cliente relevante (registro
    # finalizado, deferido, protocolo, exigencia) - ver notificar_cliente_processo
    # em main.py. "enviado" = pelo menos um destinatario recebeu; "falhou" =
    # tentou mas nenhum envio teve sucesso; "pendente_revisao" = suprimido de
    # proposito (ex: UF em UFS_EMAIL_AUTOMATICO_SUSPENSO) - visivel no painel
    # admin em vez de silencioso, ao contrario da supressao de SP de 30/07/2026
    # que nao deixava rastro nenhum. NULL = processo nunca passou por um evento
    # de e-mail (comportamento anterior a esta coluna, ou nenhum evento ainda).
    email_status = Column(String, nullable=True)
    # Texto integral extraido do documento/ata deste processo (mesma extracao
    # ja feita na insercao para classificacao via IA) - antes era descartado
    # apos a classificacao; agora persistido pra alimentar o contexto do
    # iatos. (nao precisa re-OCRizar o PDF a cada pergunta do cliente).
    texto_documento_extraido = Column(Text, nullable=True)
    # Nome do arquivo da Guia Bancaria (boleto) emitida automaticamente na
    # JUCERJA (ver automacao/emitir_guia_jucerja.py) - so processos uf="RJ".
    # NULL = ainda nao emitida. Preenchida = tambem serve de trava de
    # idempotencia (nao gera boleto duplicado pro mesmo processo).
    arquivo_guia_bancaria = Column(String, nullable=True)


class LogEmail(Base):
    """Log persistente de toda tentativa de e-mail relacionada a processo -
    tanto ao cliente (registro/protocolo/deferido/exigencia, via
    notificar_cliente_processo) quanto aos operadores (qualquer
    insercao/atualizacao, via notificar_operadores) em main.py. Antes desta
    tabela a unica evidencia era print() no journalctl, que expira em 7
    dias - insuficiente pra auditar reclamacao que chega semanas depois.

    destinatario_tipo diferencia os dois fluxos ("cliente" | "operador").
    Nulo em linhas gravadas antes desse campo existir (todas eram cliente,
    unico fluxo que existia)."""
    __tablename__ = "log_emails"
    id = Column(String, primary_key=True)
    processo_id = Column(String, nullable=False)
    destinatario = Column(String, nullable=True)
    tipo = Column(String, nullable=False)
    sucesso = Column(Boolean, nullable=True)
    erro = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)
    destinatario_tipo = Column(String, nullable=True)


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