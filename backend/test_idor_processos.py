"""Teste de IDOR em POST /processos: o campo processo_id enviado no body so
pode ser reaproveitado (POST atua como "completar"/sobrescrever) se o
processo ja existente pertencer ao grupo do usuario autenticado. Cliente de
um grupo nao pode sequestrar/sobrescrever processo de outro grupo so
passando o ID no body.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_idor_processos -v
"""

import json
import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Processo, Usuario

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

from main import app, get_db, hash_token_sessao  # noqa: E402  (import apos criar o schema de teste)
from fastapi.testclient import TestClient  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _criar_usuario(db, login, grupo_id, is_admin=False):
    token_puro = str(uuid.uuid4())
    u = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash="x",
        grupo_id=grupo_id,
        token=hash_token_sessao(token_puro),
        token_criado_em=datetime.now(),
        is_admin=is_admin,
    )
    db.add(u)
    db.commit()
    u.token_puro = token_puro  # no banco fica so' o hash; o puro e' o que o cliente manda no header
    return u


def _criar_processo(db, grupo_id, empresa="EMPRESA VITIMA LTDA"):
    p = Processo(
        id="MN-" + uuid.uuid4().hex[:12].upper(),
        empresa=empresa,
        cnpj="11.111.111/0001-11",
        tipo_ato="Alteracao Contratual",
        grupo_id=grupo_id,
        status="aberto",
    )
    db.add(p)
    db.commit()
    return p


class TestIdorPostProcessos(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_cliente_nao_sequestra_processo_de_outro_grupo(self):
        vitima_grupo = "grupo-vitima-" + uuid.uuid4().hex[:6]
        atacante_grupo = "grupo-atacante-" + uuid.uuid4().hex[:6]
        atacante = _criar_usuario(self.db, "atacante_" + uuid.uuid4().hex[:8], atacante_grupo)
        processo_vitima = _criar_processo(self.db, vitima_grupo, empresa="EMPRESA VITIMA LTDA")

        payload = {
            "processo_id": processo_vitima.id,
            "empresa": "EMPRESA SEQUESTRADA PELO ATACANTE",
            "tipo_ato": "Alteracao Contratual",
            "data_ata": "01/01/2026",
        }
        resp = client.post(
            "/processos",
            data={"dados": json.dumps(payload)},
            headers={"x-token": atacante.token_puro},
        )

        self.assertEqual(resp.status_code, 403)

        # o processo da vitima continua intacto: nem os dados nem o grupo_id
        # foram sobrescritos pelo atacante
        self.db.expire_all()
        p_apos = self.db.query(Processo).filter(Processo.id == processo_vitima.id).first()
        self.assertIsNotNone(p_apos)
        self.assertEqual(p_apos.grupo_id, vitima_grupo)
        self.assertEqual(p_apos.empresa, "EMPRESA VITIMA LTDA")

    def test_cliente_completa_processo_pendente_do_proprio_grupo(self):
        grupo = "grupo-legitimo-" + uuid.uuid4().hex[:6]
        cliente = _criar_usuario(self.db, "cliente_" + uuid.uuid4().hex[:8], grupo)
        processo_proprio = _criar_processo(self.db, grupo, empresa="EMPRESA PROPRIA LTDA")

        payload = {
            "processo_id": processo_proprio.id,
            "empresa": "EMPRESA PROPRIA LTDA - ATUALIZADA",
            "tipo_ato": "Alteracao Contratual",
            "data_ata": "01/01/2026",
        }
        resp = client.post(
            "/processos",
            data={"dados": json.dumps(payload)},
            headers={"x-token": cliente.token_puro},
        )

        self.assertEqual(resp.status_code, 200)
        self.db.expire_all()
        p_apos = self.db.query(Processo).filter(Processo.id == processo_proprio.id).first()
        self.assertEqual(p_apos.grupo_id, grupo)
        self.assertEqual(p_apos.empresa, "EMPRESA PROPRIA LTDA - ATUALIZADA")

    def test_admin_pode_completar_processo_de_qualquer_grupo(self):
        vitima_grupo = "grupo-vitima-" + uuid.uuid4().hex[:6]
        admin = _criar_usuario(self.db, "admin_" + uuid.uuid4().hex[:8], "grupo-admin", is_admin=True)
        processo = _criar_processo(self.db, vitima_grupo, empresa="EMPRESA QUALQUER LTDA")

        payload = {
            "processo_id": processo.id,
            "empresa": "EMPRESA QUALQUER LTDA - CORRIGIDA PELO ADMIN",
            "tipo_ato": "Alteracao Contratual",
            "data_ata": "01/01/2026",
        }
        resp = client.post(
            "/processos",
            data={"dados": json.dumps(payload)},
            headers={"x-token": admin.token_puro},
        )

        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
