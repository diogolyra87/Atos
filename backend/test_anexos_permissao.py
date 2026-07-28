"""Teste de permissao do DELETE /anexos/{id}: so admin ou quem enviou o
anexo pode excluir; qualquer outro usuario do mesmo grupo recebe 403 e a
tentativa fica registrada em audit_logs.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_anexos_permissao -v
"""

import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Anexo, Usuario, AuditLog

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

from main import app, get_db  # noqa: E402  (import apos criar o schema de teste)
from fastapi.testclient import TestClient  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _criar_usuario(db, login, is_admin):
    token = str(uuid.uuid4())
    u = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash="x",
        grupo_id="grupo-teste",
        token=token,
        token_criado_em=datetime.now(),
        is_admin=is_admin,
    )
    db.add(u)
    db.commit()
    return u


def _criar_anexo(db, enviado_por):
    a = Anexo(
        id=str(uuid.uuid4()),
        processo_id="processo-teste",
        arquivo="arquivo_inexistente.pdf",
        nome_original="documento.pdf",
        enviado_por=enviado_por,
    )
    db.add(a)
    db.commit()
    return a


class TestPermissaoExcluirAnexo(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_admin_exclui_com_sucesso(self):
        admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], is_admin=True)
        anexo = _criar_anexo(self.db, enviado_por="outro_usuario")

        resp = client.delete(f"/anexos/{anexo.id}", headers={"x-token": admin.token})

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.db.query(Anexo).filter(Anexo.id == anexo.id).first())
        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.acao == "anexo_excluir", AuditLog.processo_id == anexo.processo_id)
            .first()
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario_login, admin.login)

    def test_cliente_recebe_403_e_fica_registrado(self):
        cliente = _criar_usuario(self.db, "cliente_" + uuid.uuid4().hex[:8], is_admin=False)
        anexo = _criar_anexo(self.db, enviado_por="outro_usuario")

        resp = client.delete(f"/anexos/{anexo.id}", headers={"x-token": cliente.token})

        self.assertEqual(resp.status_code, 403)
        # o anexo continua existindo
        self.assertIsNotNone(self.db.query(Anexo).filter(Anexo.id == anexo.id).first())
        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.acao == "anexo_excluir_negado", AuditLog.processo_id == anexo.processo_id)
            .first()
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario_login, cliente.login)

    def test_cliente_exclui_o_proprio_anexo_enviado(self):
        cliente = _criar_usuario(self.db, "cliente_" + uuid.uuid4().hex[:8], is_admin=False)
        anexo = _criar_anexo(self.db, enviado_por=cliente.login)

        resp = client.delete(f"/anexos/{anexo.id}", headers={"x-token": cliente.token})

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.db.query(Anexo).filter(Anexo.id == anexo.id).first())


if __name__ == "__main__":
    unittest.main()
