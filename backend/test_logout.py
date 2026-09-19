"""Teste de POST /logout: antes, 'sair' so limpava o localStorage do
frontend e o token continuava valido no backend por ate 30 dias. Agora o
token e' apagado no servidor - uma requisicao autenticada com o mesmo
token depois do logout tem que falhar.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_logout -v
"""

import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, AuditLog

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

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


def _criar_usuario(db):
    token_puro = str(uuid.uuid4())
    u = Usuario(
        id=str(uuid.uuid4()),
        login="user_" + uuid.uuid4().hex[:8],
        senha_hash="x",
        grupo_id="grupo-teste",
        token=hash_token_sessao(token_puro),
        token_criado_em=datetime.now(),
        is_admin=False,
    )
    db.add(u)
    db.commit()
    u.token_puro = token_puro  # no banco fica so' o hash; o puro e' o que o cliente manda no header
    return u


class TestLogout(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_logout_invalida_o_token_no_backend(self):
        usuario = _criar_usuario(self.db)
        token_antigo = usuario.token_puro

        resp = client.post("/logout", headers={"x-token": token_antigo})
        self.assertEqual(resp.status_code, 200)

        # o mesmo token, usado de novo depois do logout, nao pode mais
        # autenticar - essa e' a garantia central do fix
        resp2 = client.get("/processos", headers={"x-token": token_antigo})
        self.assertEqual(resp2.status_code, 401)

    def test_logout_registra_auditoria(self):
        usuario = _criar_usuario(self.db)
        client.post("/logout", headers={"x-token": usuario.token_puro})

        log = self.db.query(AuditLog).filter(AuditLog.acao == "logout", AuditLog.usuario_login == usuario.login).first()
        self.assertIsNotNone(log)

    def test_logout_sem_token_401(self):
        resp = client.post("/logout")
        self.assertEqual(resp.status_code, 401)

    def test_logout_com_token_invalido_401(self):
        resp = client.post("/logout", headers={"x-token": "token-que-nunca-existiu"})
        self.assertEqual(resp.status_code, 401)

    def test_logout_duas_vezes_seguidas_a_segunda_falha(self):
        usuario = _criar_usuario(self.db)
        token = usuario.token_puro
        primeiro = client.post("/logout", headers={"x-token": token})
        segundo = client.post("/logout", headers={"x-token": token})
        self.assertEqual(primeiro.status_code, 200)
        self.assertEqual(segundo.status_code, 401)  # token ja foi apagado no primeiro logout


if __name__ == "__main__":
    unittest.main()
