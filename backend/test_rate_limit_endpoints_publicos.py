"""Teste do rate limiter por IP dos 3 endpoints publicos que nao tinham
nenhuma protecao contra abuso: POST /cadastro, POST /solicitar-acesso e
POST /convite/definir-senha. Cada teste usa um IP proprio (header
x-real-ip) pra nao herdar contador de outro teste - o rate limiter e' um
dict em memoria do processo, nao reseta entre metodos de teste.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_rate_limit_endpoints_publicos -v
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

import main  # noqa: E402  (import apos criar o schema de teste)
from main import app, get_db  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _ip_unico():
    return "10.0.0." + str(uuid.uuid4().int % 250 + 1)


class TestRateLimitCadastro(unittest.TestCase):
    def test_estoura_limite_bloqueia_a_proxima_tentativa(self):
        ip = _ip_unico()
        for _ in range(main._LOGIN_MAX):
            resp = client.post("/cadastro", json={}, headers={"x-real-ip": ip})
            self.assertEqual(resp.status_code, 400)  # payload vazio -> 400, mas ja conta pro limite
        resp = client.post(
            "/cadastro",
            json={"codigo_grupo": "X", "login": "y", "senha": "123456", "email": "a@b.com"},
            headers={"x-real-ip": ip},
        )
        self.assertEqual(resp.status_code, 429)

    def test_ip_diferente_nao_e_afetado(self):
        ip_atacante = _ip_unico()
        for _ in range(main._LOGIN_MAX):
            client.post("/cadastro", json={}, headers={"x-real-ip": ip_atacante})

        ip_legitimo = _ip_unico()
        resp = client.post("/cadastro", json={}, headers={"x-real-ip": ip_legitimo})
        self.assertEqual(resp.status_code, 400)  # nao e' 429 - IP diferente nao herda o bloqueio


class TestRateLimitSolicitarAcesso(unittest.TestCase):
    def test_estoura_limite_bloqueia_a_proxima_tentativa(self):
        ip = _ip_unico()
        for _ in range(main._LOGIN_MAX):
            resp = client.post("/solicitar-acesso", json={}, headers={"x-real-ip": ip})
            self.assertEqual(resp.status_code, 400)
        resp = client.post("/solicitar-acesso", json={"nome": "Fulano", "email": "fulano@teste.com"}, headers={"x-real-ip": ip})
        self.assertEqual(resp.status_code, 429)


class TestRateLimitDefinirSenhaConvite(unittest.TestCase):
    def test_estoura_limite_bloqueia_a_proxima_tentativa(self):
        ip = _ip_unico()
        for _ in range(main._LOGIN_MAX):
            resp = client.post("/convite/definir-senha", json={"token": "nao-existe", "senha": "NovaSenha123"}, headers={"x-real-ip": ip})
            self.assertEqual(resp.status_code, 404)
        resp = client.post("/convite/definir-senha", json={"token": "nao-existe", "senha": "NovaSenha123"}, headers={"x-real-ip": ip})
        self.assertEqual(resp.status_code, 429)

    def test_convite_valido_dentro_do_limite_continua_funcionando(self):
        db = TestingSessionLocal()
        try:
            token = str(uuid.uuid4())
            u = Usuario(
                id=str(uuid.uuid4()), login="convidado_" + uuid.uuid4().hex[:8], senha_hash="x",
                grupo_id="grupo-teste", is_admin=False,
                token_convite=token, convite_expira_em=datetime.now() + timedelta(hours=1),
            )
            db.add(u)
            db.commit()
        finally:
            db.close()

        ip = _ip_unico()
        resp = client.post("/convite/definir-senha", json={"token": token, "senha": "NovaSenha123"}, headers={"x-real-ip": ip})
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
