"""Testes do papel "operador": acesso a tela administrativa (movimentar
processos de qualquer grupo) sem acesso a configuracao do sistema
(Aprendizado) nem exclusao de processo - so o papel "admin" pode isso.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_papel_operador -v
"""

import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, Evento, AuditLog

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


def _criar_usuario(db, login, papel, nome=None, grupo_id="grupo-admin"):
    u = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash="x",
        nome=nome,
        grupo_id=grupo_id,
        token=str(uuid.uuid4()),
        token_criado_em=datetime.now(),
        is_admin=(papel == "admin"),
        papel=papel,
    )
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, grupo_id="grupo-cliente-x"):
    p = Processo(
        id=str(uuid.uuid4()),
        empresa="Empresa Teste LTDA.",
        cnpj="11.222.333/0001-81",
        tipo_ato="alteracao",
        grupo_id=grupo_id,
        uf="SP",
        exigencia_ativa=True,
        status="exigencia",
    )
    db.add(p)
    db.commit()
    return p


class TestOperadorMovimentaProcesso(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.operador = _criar_usuario(self.db, "op_" + uuid.uuid4().hex[:8], "operador", nome="David Rangel")
        self.admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], "admin", nome="Diogo")
        self.cliente = _criar_usuario(self.db, "cli_" + uuid.uuid4().hex[:8], "cliente", grupo_id="grupo-cliente-x")

    def tearDown(self):
        self.db.close()

    def test_operador_marca_exigencia_cumprida_e_fica_registrado_com_seu_nome(self):
        p = _criar_processo(self.db, grupo_id="grupo-cliente-x")  # grupo diferente do operador
        resp = client.post(
            f"/processos/{p.id}/exigencia/cumprida",
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)

        # timeline (feed "Atividade recente"): evento gravado com nome + papel de quem agiu
        evento = (
            self.db.query(Evento)
            .filter(Evento.processo_id == p.id, Evento.tipo == "exigencia_cumprida")
            .first()
        )
        self.assertIsNotNone(evento)
        self.assertEqual(evento.usuario_nome, "David Rangel")
        self.assertEqual(evento.usuario_papel, "operador")

    def test_operador_edita_processo_e_fica_em_audit_log_com_nome_e_papel(self):
        p = _criar_processo(self.db, grupo_id="grupo-cliente-x")
        resp = client.patch(
            f"/processos/{p.id}",
            json={"observacoes": "ajuste feito pelo operador"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)

        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.processo_id == p.id, AuditLog.acao == "editar_campo")
            .order_by(AuditLog.data_hora.desc())
            .first()
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario_nome, "David Rangel")
        self.assertEqual(log.usuario_papel, "operador")

    def test_operador_ve_processo_de_grupo_diferente(self):
        p = _criar_processo(self.db, grupo_id="grupo-cliente-y")
        resp = client.get(f"/processos/{p.id}", headers={"x-token": self.operador.token})
        self.assertEqual(resp.status_code, 200)

    def test_admin_continua_com_acesso_total(self):
        p = _criar_processo(self.db, grupo_id="grupo-cliente-z")
        resp = client.post(
            f"/processos/{p.id}/exigencia/cumprida",
            headers={"x-token": self.admin.token},
        )
        self.assertEqual(resp.status_code, 200)

        resp_del = client.delete(f"/processos/{p.id}", headers={"x-token": self.admin.token})
        self.assertEqual(resp_del.status_code, 200)

    def test_cliente_nao_movimenta_processo_de_outro_grupo(self):
        p = _criar_processo(self.db, grupo_id="grupo-cliente-outro")
        resp = client.post(
            f"/processos/{p.id}/exigencia/cumprida",
            headers={"x-token": self.cliente.token},
        )
        self.assertEqual(resp.status_code, 403)


class TestOperadorBloqueadoEmConfiguracao(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.operador = _criar_usuario(self.db, "op_" + uuid.uuid4().hex[:8], "operador", nome="João Victor")
        self.admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], "admin", nome="Diogo")

    def tearDown(self):
        self.db.close()

    def test_operador_recebe_403_em_aprendizado_regras(self):
        resp = client.get("/aprendizado/regras", headers={"x-token": self.operador.token})
        self.assertEqual(resp.status_code, 403)

    def test_operador_recebe_403_ao_excluir_processo(self):
        p = _criar_processo(self.db)
        resp = client.delete(f"/processos/{p.id}", headers={"x-token": self.operador.token})
        self.assertEqual(resp.status_code, 403)

    def test_operador_recebe_403_ao_criar_outro_operador(self):
        with patch("main.enviar_email") as mock_email:
            resp = client.post(
                "/usuarios/operador",
                json={"nome": "Novo Operador", "email": "novo@exemplo.com"},
                headers={"x-token": self.operador.token},
            )
        self.assertEqual(resp.status_code, 403)
        mock_email.assert_not_called()

    def test_admin_acessa_aprendizado_regras(self):
        resp = client.get("/aprendizado/regras", headers={"x-token": self.admin.token})
        self.assertEqual(resp.status_code, 200)

    def test_admin_cria_operador_com_sucesso(self):
        with patch("main.enviar_email") as mock_email:
            resp = client.post(
                "/usuarios/operador",
                json={"nome": "Novo Operador", "email": "novo_" + uuid.uuid4().hex[:6] + "@exemplo.com"},
                headers={"x-token": self.admin.token},
            )
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        criado = self.db.query(Usuario).filter(Usuario.login == corpo["login"]).first()
        self.assertIsNotNone(criado)
        self.assertEqual(criado.papel, "operador")
        self.assertFalse(criado.is_admin)
        # nao recebe senha - convite por e-mail e disparado, com token de uso unico gravado
        self.assertIsNotNone(criado.token_convite)
        self.assertIsNotNone(criado.convite_expira_em)
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args[0][0], criado.email)


if __name__ == "__main__":
    unittest.main()
