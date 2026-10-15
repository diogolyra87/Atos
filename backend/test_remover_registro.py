"""Testes do "Remover registro" (DELETE /processos/{id}/registro): o processo
volta pro status de antes do registro (tramitacao, exigencia, deferido...),
o arquivo vai pra quarentena e cliente nao pode remover.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_remover_registro -v
"""

import os
import tempfile
import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, AuditLog, Evento

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

import main  # noqa: E402
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

PDF = b"%PDF-1.4 teste"


def _criar_usuario(db, login, papel, grupo_id="grupo-x"):
    token_puro = str(uuid.uuid4())
    u = Usuario(
        id=str(uuid.uuid4()), login=login, senha_hash="x", nome=login,
        grupo_id=grupo_id, token=hash_token_sessao(token_puro), token_criado_em=datetime.now(),
        is_admin=(papel == "admin"), papel=papel,
    )
    db.add(u)
    db.commit()
    return token_puro


def _criar_processo(db, **kwargs):
    dados = dict(id="T-" + str(uuid.uuid4())[:8], empresa="EMPRESA TESTE", cnpj="11.222.333/0001-81", tipo_ato="RCA", data_ata="01/01/2026", grupo_id="grupo-x",
                 status="tramitacao", numero_protocolo="123", uf="BA")
    dados.update(kwargs)
    p = Processo(**dados)
    db.add(p)
    db.commit()
    return p.id


class RemoverRegistroTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.p_uploads = patch.object(main, "UPLOADS_DIR", cls.tmp)
        cls.p_uploads.start()
        # sem e-mail/notificacao de verdade nos testes
        cls.p_mails = [patch.object(main, n, lambda *a, **k: None) for n in
                       ("notificar_cliente_processo", "notificar_operadores", "notificar_tramitacao_cliente")]
        for m in cls.p_mails:
            m.start()
        db = TestingSessionLocal()
        cls.tok_op = _criar_usuario(db, "op_" + uuid.uuid4().hex[:6], "operador")
        cls.tok_cli = _criar_usuario(db, "cli_" + uuid.uuid4().hex[:6], "cliente")
        db.close()

    @classmethod
    def tearDownClass(cls):
        cls.p_uploads.stop()
        for m in cls.p_mails:
            m.stop()

    def _upload_e_remover(self, **proc):
        db = TestingSessionLocal()
        pid = _criar_processo(db, **proc)
        db.close()
        r = client.post(f"/processos/{pid}/upload/registro", headers={"x-token": self.tok_op},
                        files={"arquivo": ("CELPE - ARD.pdf", PDF, "application/pdf")})
        self.assertEqual(r.status_code, 200, r.text)
        db = TestingSessionLocal()
        self.assertEqual(db.query(Processo).get(pid).status, "finalizado")
        db.close()
        r = client.delete(f"/processos/{pid}/registro", headers={"x-token": self.tok_op})
        self.assertEqual(r.status_code, 200, r.text)
        db = TestingSessionLocal()
        p = db.query(Processo).get(pid)
        return pid, p, db

    def test_volta_para_exigencia(self):
        pid, p, db = self._upload_e_remover(status="exigencia", exigencia_ativa=True)
        self.assertEqual(p.status, "exigencia")
        self.assertTrue(p.exigencia_ativa)
        self.assertFalse(p.arquivo_registro)
        self.assertFalse(p.arquivo_registro_nome_exibicao)
        db.close()

    def test_volta_para_tramitacao(self):
        pid, p, db = self._upload_e_remover(status="tramitacao")
        self.assertEqual(p.status, "tramitacao")
        self.assertFalse(p.exigencia_ativa)
        db.close()

    def test_volta_para_deferido(self):
        pid, p, db = self._upload_e_remover(status="deferido")
        self.assertEqual(p.status, "deferido")
        db.close()

    def test_volta_para_aberto(self):
        pid, p, db = self._upload_e_remover(status="aberto", numero_protocolo=None)
        self.assertEqual(p.status, "aberto")
        db.close()

    def test_arquivo_vai_para_quarentena_e_evento_sai_da_timeline(self):
        pid, p, db = self._upload_e_remover(status="tramitacao")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, f"{pid}_registro.pdf")))
        q = os.listdir(os.path.join(self.tmp, "_quarentena"))
        self.assertTrue(any(n.startswith(f"{pid}_registro_removido_") for n in q))
        self.assertEqual(db.query(Evento).filter(Evento.processo_id == pid,
                                                 Evento.tipo == "registro_finalizado").count(), 0)
        log = db.query(AuditLog).filter(AuditLog.processo_id == pid, AuditLog.acao == "remover_registro").first()
        self.assertIn("-> 'tramitacao'", log.detalhe)
        db.close()

    def test_registro_antigo_sem_status_anterior_usa_deducao(self):
        # registro anexado pela automacao (sem log de upload): deduz pelos dados
        db = TestingSessionLocal()
        pid = _criar_processo(db, status="finalizado", arquivo_registro="x_registro_auto.pdf",
                              deferido_em=datetime.now())
        db.close()
        r = client.delete(f"/processos/{pid}/registro", headers={"x-token": self.tok_op})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "deferido")

    def test_cliente_nao_pode_remover(self):
        db = TestingSessionLocal()
        pid = _criar_processo(db, status="finalizado", arquivo_registro="x.pdf")
        db.close()
        r = client.delete(f"/processos/{pid}/registro", headers={"x-token": self.tok_cli})
        self.assertEqual(r.status_code, 403)

    def test_sem_registro_da_400(self):
        db = TestingSessionLocal()
        pid = _criar_processo(db)
        db.close()
        r = client.delete(f"/processos/{pid}/registro", headers={"x-token": self.tok_op})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
