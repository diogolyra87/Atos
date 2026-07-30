"""Testes do POST /processos/{id}/certidao-simplificada: emissao via
Infosimples, anexando o PDF ao processo (mesma logica de armazenamento dos
anexos manuais).

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db) e mocka
main.baixar_certidao_simplificada (chamada real de terceiro paga - nunca bate
na API de verdade em teste automatizado).

Rodar com: python -m unittest test_certidao_simplificada -v
"""

import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Anexo, Usuario, Processo, AuditLog

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


def _criar_usuario(db, login, is_admin, grupo_id="grupo-teste"):
    u = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash="x",
        grupo_id=grupo_id,
        token=str(uuid.uuid4()),
        token_criado_em=datetime.now(),
        is_admin=is_admin,
    )
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, nire="35215861263", grupo_id="grupo-teste"):
    p = Processo(
        id=str(uuid.uuid4()),
        empresa="Empresa Teste LTDA.",
        cnpj="11.222.333/0001-81",
        nire=nire,
        tipo_ato="alteracao",
        grupo_id=grupo_id,
        uf="SP",
    )
    db.add(p)
    db.commit()
    return p


class TestCertidaoSimplificada(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], is_admin=True)
        self._patch_credenciais = patch.multiple(
            main,
            INFOSIMPLES_TOKEN="token-teste",
            INFOSIMPLES_CPF="cpf-teste",
            INFOSIMPLES_SENHA_NFP="senha-teste",
        )
        self._patch_credenciais.start()

    def tearDown(self):
        self._patch_credenciais.stop()
        self.db.close()

    def test_emissao_bem_sucedida_cria_anexo_e_auditoria(self):
        p = _criar_processo(self.db)

        with patch("main.baixar_certidao_simplificada", return_value=True) as mock_baixar, \
             patch("main.enviar_email") as mock_email:
            resp = client.post(
                f"/processos/{p.id}/certidao-simplificada",
                headers={"x-token": self.admin.token},
            )

        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertIn("anexo_id", corpo)
        mock_baixar.assert_called_once()
        chamado_com_nire = mock_baixar.call_args[0][0]
        self.assertEqual(chamado_com_nire, p.nire)

        anexo = self.db.query(Anexo).filter(Anexo.id == corpo["anexo_id"]).first()
        self.assertIsNotNone(anexo)
        self.assertEqual(anexo.processo_id, p.id)

        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.acao == "certidao_simplificada_emitida", AuditLog.processo_id == p.id)
            .first()
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario_login, self.admin.login)

        # Regra do pedido: NAO notifica o cliente automaticamente ainda.
        mock_email.assert_not_called()

    def test_nire_nao_encontrado_ou_invalido_retorna_502_e_nao_cria_anexo(self):
        p = _criar_processo(self.db, nire="00000000000")

        with patch("main.baixar_certidao_simplificada", return_value=False), \
             patch("main.enviar_email") as mock_email:
            resp = client.post(
                f"/processos/{p.id}/certidao-simplificada",
                headers={"x-token": self.admin.token},
            )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(self.db.query(Anexo).filter(Anexo.processo_id == p.id).count(), 0)
        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.acao == "certidao_simplificada_erro", AuditLog.processo_id == p.id)
            .first()
        )
        self.assertIsNotNone(log)
        mock_email.assert_not_called()

    def test_credenciais_ausentes_retorna_503_sem_chamar_infosimples(self):
        p = _criar_processo(self.db)

        with patch.multiple(main, INFOSIMPLES_TOKEN=None, INFOSIMPLES_CPF=None, INFOSIMPLES_SENHA_NFP=None), \
             patch("main.baixar_certidao_simplificada") as mock_baixar:
            resp = client.post(
                f"/processos/{p.id}/certidao-simplificada",
                headers={"x-token": self.admin.token},
            )

        self.assertEqual(resp.status_code, 503)
        mock_baixar.assert_not_called()

    def test_processo_sem_nire_retorna_400(self):
        p = _criar_processo(self.db, nire=None)

        with patch("main.baixar_certidao_simplificada") as mock_baixar:
            resp = client.post(
                f"/processos/{p.id}/certidao-simplificada",
                headers={"x-token": self.admin.token},
            )

        self.assertEqual(resp.status_code, 400)
        mock_baixar.assert_not_called()

    def test_processo_inexistente_retorna_404(self):
        resp = client.post(
            "/processos/id-que-nao-existe/certidao-simplificada",
            headers={"x-token": self.admin.token},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
