"""Testes da edicao manual de dados do processo (PATCH /processos/{id}):
whitelist de campos, vocabulario fechado de tipo_ato, log de auditoria
granular por campo, alteracao sensivel de protocolo ja preenchido, e
supressao da notificacao de e-mail quando "status" nao vem no payload.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_editar_dados_processo -v
"""

import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, AuditLog

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

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


def _criar_usuario(db, login, papel, nome=None, grupo_id="grupo-x"):
    u = Usuario(
        id=str(uuid.uuid4()), login=login, senha_hash="x", nome=nome,
        grupo_id=grupo_id, token=str(uuid.uuid4()), token_criado_em=datetime.now(),
        is_admin=(papel == "admin"), papel=papel,
    )
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, grupo_id="grupo-x", **kwargs):
    dados = dict(
        id=str(uuid.uuid4()), empresa="Empresa Teste LTDA.", cnpj="11.222.333/0001-81",
        tipo_ato="AGE", identificador_ato="AGE 10/01/2026", uf="SP",
        grupo_id=grupo_id, status="aberto",
    )
    dados.update(kwargs)
    p = Processo(**dados)
    db.add(p)
    db.commit()
    return p


class TestEdicaoDadosProcesso(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.operador = _criar_usuario(self.db, "op_" + uuid.uuid4().hex[:8], "operador", nome="David Rangel")
        self.admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], "admin", nome="Diogo")
        self.cliente = _criar_usuario(self.db, "cli_" + uuid.uuid4().hex[:8], "cliente")

    def tearDown(self):
        self.db.close()

    @patch("main.notificar_tramitacao_cliente")
    def test_operador_corrige_tipo_ato_ard_para_rca_e_volta(self, mock_notificar):
        p = _criar_processo(self.db, tipo_ato="RCA")
        resp = client.patch(
            f"/processos/{p.id}", json={"tipo_ato": "ARD"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        self.db.refresh(p)
        self.assertEqual(p.tipo_ato, "ARD")

        resp2 = client.patch(
            f"/processos/{p.id}", json={"tipo_ato": "RCA"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp2.status_code, 200)
        self.db.refresh(p)
        self.assertEqual(p.tipo_ato, "RCA")

        logs = (
            self.db.query(AuditLog)
            .filter(AuditLog.processo_id == p.id, AuditLog.acao == "editar_campo")
            .order_by(AuditLog.data_hora.asc())
            .all()
        )
        self.assertEqual(len(logs), 2)
        self.assertIn("tipo_ato: 'RCA' -> 'ARD'", logs[0].detalhe)
        self.assertIn("tipo_ato: 'ARD' -> 'RCA'", logs[1].detalhe)
        self.assertEqual(logs[0].usuario_nome, "David Rangel")
        # edicao manual nao envia status -> nunca notifica cliente
        mock_notificar.assert_not_called()

    def test_tipo_ato_fora_do_vocabulario_e_rejeitado(self):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}", json={"tipo_ato": "TIPO_INVENTADO"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Tipo de ato inválido", resp.json()["detail"])
        self.db.refresh(p)
        self.assertEqual(p.tipo_ato, "AGE")

    def test_identificador_ato_continua_texto_livre_sem_validacao(self):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}",
            json={"identificador_ato": "Ata de Reunião de Sócios de 27/03/2026"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        self.db.refresh(p)
        self.assertEqual(p.identificador_ato, "Ata de Reunião de Sócios de 27/03/2026")

    def test_campo_fora_da_whitelist_e_rejeitado(self):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}", json={"grupo_id": "outro-grupo"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("grupo_id", resp.json()["detail"])

    def test_cliente_nao_pode_editar_processo(self):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}", json={"empresa": "OUTRA EMPRESA"},
            headers={"x-token": self.cliente.token},
        )
        self.assertEqual(resp.status_code, 403)

    def test_troca_de_protocolo_ja_preenchido_e_marcada_sensivel(self):
        p = _criar_processo(self.db, numero_protocolo="111.111")
        resp = client.patch(
            f"/processos/{p.id}", json={"numero_protocolo": "222.222"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.processo_id == p.id, AuditLog.acao == "editar_campo_sensivel")
            .first()
        )
        self.assertIsNotNone(log)
        self.assertIn("111.111", log.detalhe)
        self.assertIn("222.222", log.detalhe)

    def test_protocolo_preenchido_pela_primeira_vez_nao_e_sensivel(self):
        p = _criar_processo(self.db, numero_protocolo=None)
        resp = client.patch(
            f"/processos/{p.id}", json={"numero_protocolo": "333.333"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        log_sensivel = (
            self.db.query(AuditLog)
            .filter(AuditLog.processo_id == p.id, AuditLog.acao == "editar_campo_sensivel")
            .first()
        )
        self.assertIsNone(log_sensivel)

    @patch("main.notificar_tramitacao_cliente")
    def test_status_no_payload_sempre_notifica_mesmo_com_outros_campos(self, mock_notificar):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}",
            json={"status": "finalizado", "identificador_ato": "Novo texto"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        mock_notificar.assert_called_once()

    @patch("main.notificar_tramitacao_cliente")
    def test_sem_status_no_payload_nunca_notifica(self, mock_notificar):
        p = _criar_processo(self.db)
        resp = client.patch(
            f"/processos/{p.id}",
            json={"empresa": "NOVA EMPRESA", "uf": "MG", "data_ata": "01/01/2026", "hora_ata": "10:00"},
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        mock_notificar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
