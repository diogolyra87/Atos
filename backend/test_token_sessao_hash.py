"""Teste do token de sessao guardado como hash (auditoria de seguranca
18/09/2026, item "token de sessao em texto puro no banco"):

Antes, usuarios.token guardava o proprio token que o cliente manda no header
x-token - quem lesse o banco (backup vazado, SQL injection futura) virava
qualquer usuario logado so' copiando o valor. Agora o banco guarda
sha256(token) e o token puro (secrets.token_urlsafe(32)) so' existe no cliente.

Garantias cobertas:
- login (/login/verificar) devolve o token puro e grava SO' o hash no banco
- o token puro devolvido autentica normalmente (validar_token compara hash)
- o proprio hash guardado no banco NAO autentica (a razao de ser do fix:
  ler o banco nao da' acesso)
- token em texto puro de antes da migracao (uuid4, 36 chars) e' invalidado
  explicitamente: o cliente manda o valor, o banco tem o mesmo valor, mas
  sha256(valor) != valor -> 401. Ninguem fica logado com token legado.
- expiracao de 30 dias continua valendo sobre o token com hash
- novo login substitui o token anterior (renovacao) - o antigo para de valer
- logout apaga o hash do banco

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_token_sessao_hash -v
"""

import hashlib
import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Codigo2FA

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


def _criar_usuario(db, token_gravado=None, token_criado_em=None):
    u = Usuario(
        id=str(uuid.uuid4()),
        login="user_" + uuid.uuid4().hex[:10],
        senha_hash="x",
        grupo_id="grupo-teste",
        token=token_gravado,
        token_criado_em=token_criado_em,
        is_admin=False,
    )
    db.add(u)
    db.commit()
    return u


def _logar(db, usuario):
    """Faz o passo final do login (POST /login/verificar) com um codigo 2FA valido
    e devolve o JSON da resposta - onde vem o token puro."""
    codigo = "{:06d}".format(uuid.uuid4().int % 1000000)
    db.add(Codigo2FA(
        id=str(uuid.uuid4()), usuario_id=usuario.id, login=usuario.login,
        codigo=codigo, expira_em=datetime.now() + timedelta(minutes=10), usado=False,
    ))
    db.commit()
    resp = client.post("/login/verificar", json={"login": usuario.login, "codigo": codigo})
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestHashTokenSessao(unittest.TestCase):
    def test_e_sha256_hex_de_64_chars(self):
        # vetor de teste padrao do SHA-256
        self.assertEqual(
            hash_token_sessao("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        self.assertEqual(hash_token_sessao("abc"), hashlib.sha256(b"abc").hexdigest())

    def test_deterministico_e_distinto_entre_tokens(self):
        self.assertEqual(hash_token_sessao("x"), hash_token_sessao("x"))
        self.assertNotEqual(hash_token_sessao("x"), hash_token_sessao("y"))


class TestLoginGravaHash(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()
        main._login_verificar_tentativas.pop(self.usuario.login, None)

    def test_login_devolve_token_puro_e_grava_so_o_hash(self):
        token = _logar(self.db, self.usuario)["token"]

        self.db.refresh(self.usuario)
        self.assertNotEqual(self.usuario.token, token)  # o banco NAO tem o token puro
        self.assertEqual(self.usuario.token, hash_token_sessao(token))
        self.assertEqual(len(self.usuario.token), 64)
        self.assertIsNotNone(self.usuario.token_criado_em)

    def test_token_puro_nao_aparece_em_nenhuma_coluna_do_usuario(self):
        token = _logar(self.db, self.usuario)["token"]

        self.db.refresh(self.usuario)
        for coluna in Usuario.__table__.columns:
            valor = getattr(self.usuario, coluna.name)
            self.assertNotEqual(valor, token, "token puro vazou na coluna " + coluna.name)

    def test_token_tem_256_bits_de_entropia_e_e_unico_por_login(self):
        t1 = _logar(self.db, self.usuario)["token"]
        t2 = _logar(self.db, self.usuario)["token"]
        # token_urlsafe(32) = 32 bytes = 43 chars base64url, sem padding
        self.assertEqual(len(t1), 43)
        self.assertRegex(t1, r"^[A-Za-z0-9_-]+$")
        self.assertNotEqual(t1, t2)

    def test_token_puro_devolvido_no_login_autentica(self):
        token = _logar(self.db, self.usuario)["token"]

        resp = client.get("/processos", headers={"x-token": token})
        self.assertEqual(resp.status_code, 200)

    def test_o_hash_guardado_no_banco_nao_autentica(self):
        # cenario do fix: atacante leu o banco e tenta usar o valor de
        # usuarios.token como se fosse o token de sessao
        _logar(self.db, self.usuario)
        self.db.refresh(self.usuario)

        resp = client.get("/processos", headers={"x-token": self.usuario.token})
        self.assertEqual(resp.status_code, 401)

    def test_novo_login_invalida_o_token_anterior(self):
        antigo = _logar(self.db, self.usuario)["token"]
        novo = _logar(self.db, self.usuario)["token"]

        self.assertEqual(client.get("/processos", headers={"x-token": antigo}).status_code, 401)
        self.assertEqual(client.get("/processos", headers={"x-token": novo}).status_code, 200)


class TestValidacaoDoToken(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_token_legado_em_texto_puro_e_invalidado(self):
        # estado do banco de producao ANTES do deploy: usuarios.token = uuid4 puro,
        # e o cliente logado continua mandando esse mesmo valor
        legado = str(uuid.uuid4())
        _criar_usuario(self.db, token_gravado=legado, token_criado_em=datetime.now())

        resp = client.get("/processos", headers={"x-token": legado})
        self.assertEqual(resp.status_code, 401)

    def test_token_com_hash_valido_dentro_do_prazo_autentica(self):
        token = "token-de-teste-" + uuid.uuid4().hex
        _criar_usuario(self.db, token_gravado=hash_token_sessao(token), token_criado_em=datetime.now())

        self.assertEqual(client.get("/processos", headers={"x-token": token}).status_code, 200)

    def test_expiracao_de_30_dias_continua_valendo(self):
        token = "token-expirado-" + uuid.uuid4().hex
        _criar_usuario(
            self.db, token_gravado=hash_token_sessao(token),
            token_criado_em=datetime.now() - timedelta(days=31),
        )

        self.assertEqual(client.get("/processos", headers={"x-token": token}).status_code, 401)

    def test_token_errado_ausente_ou_vazio_401(self):
        token = "token-certo-" + uuid.uuid4().hex
        _criar_usuario(self.db, token_gravado=hash_token_sessao(token), token_criado_em=datetime.now())

        self.assertEqual(client.get("/processos", headers={"x-token": token + "x"}).status_code, 401)
        self.assertEqual(client.get("/processos", headers={"x-token": ""}).status_code, 401)
        self.assertEqual(client.get("/processos").status_code, 401)

    def test_token_de_um_usuario_nao_autentica_como_outro(self):
        t_a = "token-a-" + uuid.uuid4().hex
        t_b = "token-b-" + uuid.uuid4().hex
        a = _criar_usuario(self.db, token_gravado=hash_token_sessao(t_a), token_criado_em=datetime.now())
        b = _criar_usuario(self.db, token_gravado=hash_token_sessao(t_b), token_criado_em=datetime.now())

        self.assertEqual(main.validar_token(t_a, self.db).id, a.id)
        self.assertEqual(main.validar_token(t_b, self.db).id, b.id)

    def test_token_com_caracteres_nao_ascii_nao_quebra(self):
        # o hash faz .encode("utf-8") - header estranho tem que dar 401, nao 500.
        # bytes porque o httpx do TestClient recusa str nao-ASCII; um cliente real manda bytes
        resp = client.get("/processos", headers={"x-token": "tokém-ç".encode("utf-8")})
        self.assertEqual(resp.status_code, 401)


class TestLogoutComHash(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.usuario = _criar_usuario(self.db)

    def tearDown(self):
        self.db.close()
        main._login_verificar_tentativas.pop(self.usuario.login, None)

    def test_logout_apaga_o_hash_do_banco_e_o_token_para_de_valer(self):
        token = _logar(self.db, self.usuario)["token"]

        self.assertEqual(client.post("/logout", headers={"x-token": token}).status_code, 200)

        self.db.refresh(self.usuario)
        self.assertIsNone(self.usuario.token)
        self.assertIsNone(self.usuario.token_criado_em)
        self.assertEqual(client.get("/processos", headers={"x-token": token}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
