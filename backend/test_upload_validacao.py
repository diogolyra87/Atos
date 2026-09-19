"""Teste de validacao de upload (extensao + tamanho + arquivo vazio) nos
endpoints que gravavam arquivo em disco (ou liam tudo em memoria) sem
nenhuma checagem: POST /processos (ata), POST /processos/{id}/exigencia,
POST /processos/analisar, POST /processos/analisar-pasta e
POST /processos/analisar-pasta-multi.

A validacao roda ANTES de qualquer extracao de texto/chamada de IA, entao
os testes de rejeicao (extensao invalida, arquivo vazio) nunca disparam
chamada de rede real. Os testes de "arquivo valido continua funcionando"
usam um .txt com so espaco em branco, que cai no fallback de decode de
texto puro em _extrair_texto_bytes e fica vazio apos strip() - pula a
chamada real a analisar_ata_ia (ver main.py: "if texto.strip()").

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_upload_validacao -v
"""

import json
import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

import main  # noqa: E402  (import apos criar o schema de teste)
from main import app, get_db, hash_token_sessao  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _criar_usuario(db, grupo_id="grupo-teste"):
    token_puro = str(uuid.uuid4())
    u = Usuario(
        id=str(uuid.uuid4()),
        login="user_" + uuid.uuid4().hex[:8],
        senha_hash="x",
        grupo_id=grupo_id,
        token=hash_token_sessao(token_puro),
        token_criado_em=datetime.now(),
        is_admin=False,
    )
    db.add(u)
    db.commit()
    u.token_puro = token_puro  # no banco fica so' o hash; o puro e' o que o cliente manda no header
    return u


def _criar_processo(db, grupo_id="grupo-teste"):
    p = Processo(
        id="MN-" + uuid.uuid4().hex[:12].upper(),
        empresa="Empresa Teste LTDA.",
        cnpj="11.111.111/0001-11",
        tipo_ato="Alteracao Contratual",
        grupo_id=grupo_id,
        status="aberto",
    )
    db.add(p)
    db.commit()
    return p


TXT_VAZIO_APOS_STRIP = b"   "  # nao vazio (passa a checagem de tamanho), mas strip() fica "" (pula a IA)


class TestUploadCriarProcesso(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()

    def _payload(self):
        return {"dados": json.dumps({"empresa": "Empresa X", "tipo_ato": "AGE", "data_ata": "01/01/2026"})}

    def test_extensao_nao_permitida_e_rejeitada(self):
        resp = client.post(
            "/processos",
            data=self._payload(),
            files={"arquivo": ("malicioso.exe", b"conteudo qualquer", "application/octet-stream")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)

    def test_arquivo_vazio_e_rejeitado(self):
        resp = client.post(
            "/processos",
            data=self._payload(),
            files={"arquivo": ("ata.pdf", b"", "application/pdf")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)

    def test_arquivo_acima_do_limite_e_rejeitado(self):
        grande = b"x" * (main.LIMITE_UPLOAD_DOCUMENTO_BYTES + 1)
        resp = client.post(
            "/processos",
            data=self._payload(),
            files={"arquivo": ("ata.pdf", grande, "application/pdf")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)

    def test_arquivo_valido_continua_funcionando(self):
        resp = client.post(
            "/processos",
            data=self._payload(),
            files={"arquivo": ("ata.pdf", b"%PDF-1.4 conteudo minimo", "application/pdf")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 200)

    def test_sem_arquivo_continua_funcionando(self):
        # arquivo e opcional (File(None)) - completar um processo sem
        # reenviar a ata nao pode ser afetado pela validacao nova
        resp = client.post("/processos", data=self._payload(), headers={"x-token": self.usuario.token_puro})
        self.assertEqual(resp.status_code, 200)


class TestUploadExigencia(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)
        self.processo = _criar_processo(self.db, grupo_id=self.usuario.grupo_id)

    def tearDown(self):
        self.db.close()

    def test_extensao_nao_permitida_e_rejeitada(self):
        resp = client.post(
            f"/processos/{self.processo.id}/exigencia",
            data={"texto": "falta documento X"},
            files={"arquivo": ("script.js", b"alert(1)", "application/javascript")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)

    def test_arquivo_valido_continua_funcionando(self):
        resp = client.post(
            f"/processos/{self.processo.id}/exigencia",
            data={"texto": "falta documento X"},
            files={"arquivo": ("exigencia.pdf", b"%PDF-1.4 conteudo minimo", "application/pdf")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 200)


class TestUploadAnalisarDocumento(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()

    def test_extensao_nao_permitida_e_rejeitada_sem_criar_processo(self):
        antes = self.db.query(Processo).count()
        resp = client.post(
            "/processos/analisar",
            files={"arquivo": ("ata.exe", b"conteudo qualquer", "application/octet-stream")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)
        # rejeitado ANTES de _criar_processo_pendente - nao deve sobrar
        # processo pendente orfao no banco
        self.db.expire_all()
        self.assertEqual(self.db.query(Processo).count(), antes)

    def test_arquivo_valido_continua_funcionando(self):
        resp = client.post(
            "/processos/analisar",
            files={"arquivo": ("ata.txt", TXT_VAZIO_APOS_STRIP, "text/plain")},
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 200)


class TestUploadAnalisarPasta(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()

    def test_um_arquivo_invalido_no_lote_rejeita_o_lote_inteiro(self):
        resp = client.post(
            "/processos/analisar-pasta",
            files=[
                ("arquivos", ("ata.txt", TXT_VAZIO_APOS_STRIP, "text/plain")),
                ("arquivos", ("suspeito.exe", b"conteudo qualquer", "application/octet-stream")),
            ],
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)


class TestUploadAnalisarPastaMulti(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()

    def test_um_arquivo_invalido_no_lote_rejeita_o_lote_inteiro(self):
        resp = client.post(
            "/processos/analisar-pasta-multi",
            data={"pre_classificacao": "true"},  # pre_classificacao=True nao cria processo, mais simples de isolar
            files=[
                ("arquivos", ("ata.txt", TXT_VAZIO_APOS_STRIP, "text/plain")),
                ("arquivos", ("suspeito.exe", b"conteudo qualquer", "application/octet-stream")),
            ],
            headers={"x-token": self.usuario.token_puro},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
