"""Testes do fluxo de convite de primeiro acesso (definir a propria senha
via link com token de uso unico, ao inves de senha temporaria).

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_convite_operador -v
"""

import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

from main import app, get_db, gerar_convite  # noqa: E402  (import apos criar o schema de teste)
from fastapi.testclient import TestClient  # noqa: E402
import bcrypt  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _criar_operador(db, nome="David Rangel", senha_atual="temporaria-antiga"):
    u = Usuario(
        id=str(uuid.uuid4()),
        login="op_" + uuid.uuid4().hex[:8],
        senha_hash=bcrypt.hashpw(senha_atual.encode()[:72], bcrypt.gensalt()).decode(),
        nome=nome,
        email="operador@exemplo.com",
        grupo_id="grupo-admin",
        is_admin=False,
        papel="operador",
    )
    db.add(u)
    db.commit()
    return u


class TestConviteValido(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_get_convite_valido_retorna_nome(self):
        u = _criar_operador(self.db)
        token = gerar_convite(self.db, u)
        resp = client.get(f"/convite/{token}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["nome"], "David Rangel")

    def test_definir_senha_com_token_valido_funciona(self):
        u = _criar_operador(self.db)
        token = gerar_convite(self.db, u)
        senha_hash_antigo = u.senha_hash

        resp = client.post("/convite/definir-senha", json={"token": token, "senha": "NovaSenha123"})
        self.assertEqual(resp.status_code, 200)

        self.db.refresh(u)
        self.assertNotEqual(u.senha_hash, senha_hash_antigo)
        self.assertTrue(bcrypt.checkpw(b"NovaSenha123", u.senha_hash.encode()))
        self.assertIsNone(u.token_convite)
        self.assertIsNone(u.convite_expira_em)

    def test_senha_fraca_e_rejeitada(self):
        u = _criar_operador(self.db)
        token = gerar_convite(self.db, u)
        resp = client.post("/convite/definir-senha", json={"token": token, "senha": "abc123"})
        self.assertEqual(resp.status_code, 400)
        self.db.refresh(u)
        self.assertIsNotNone(u.token_convite)  # token continua valido, nao foi consumido


class TestConviteExpirado(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def _criar_convite_expirado(self):
        u = _criar_operador(self.db)
        u.token_convite = "token-expirado-" + uuid.uuid4().hex
        u.convite_expira_em = datetime.now() - timedelta(hours=1)
        self.db.commit()
        return u

    def test_get_convite_expirado_retorna_410(self):
        u = self._criar_convite_expirado()
        resp = client.get(f"/convite/{u.token_convite}")
        self.assertEqual(resp.status_code, 410)

    def test_definir_senha_com_token_expirado_retorna_410(self):
        u = self._criar_convite_expirado()
        senha_hash_antigo = u.senha_hash
        resp = client.post("/convite/definir-senha", json={"token": u.token_convite, "senha": "NovaSenha123"})
        self.assertEqual(resp.status_code, 410)
        self.db.refresh(u)
        self.assertEqual(u.senha_hash, senha_hash_antigo)


class TestConviteJaUsado(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_token_ja_usado_nao_pode_ser_reutilizado(self):
        u = _criar_operador(self.db)
        token = gerar_convite(self.db, u)

        primeira = client.post("/convite/definir-senha", json={"token": token, "senha": "PrimeiraSenha1"})
        self.assertEqual(primeira.status_code, 200)

        senha_hash_apos_primeira = u.senha_hash
        segunda = client.post("/convite/definir-senha", json={"token": token, "senha": "SegundaSenha2"})
        self.assertEqual(segunda.status_code, 404)

        self.db.refresh(u)
        self.assertEqual(u.senha_hash, senha_hash_apos_primeira)  # segunda tentativa nao alterou nada

    def test_token_inexistente_retorna_404(self):
        resp = client.get("/convite/token-que-nunca-existiu")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
