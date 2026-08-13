"""Testes da funcao central de disparo de e-mail ao cliente
(notificar_cliente_processo, main.py) e do fix de classificacao da JUCEB
(classificar_status_ba, automacao/consultar_juceb.py).

Cobre a correcao do incidente de 30/07/2026: e-mail de SP ficava suprimido
de forma silenciosa (upload/registro continuava normal, ninguem era avisado
do aviso pendente). Agora a supressao fica visivel via email_status +
log_emails, e avisado_deferido so avanca com envio confirmado.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_notificacao_email_processo -v
"""

import unittest
import uuid
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Processo, EmailGrupo, LogEmail

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

from main import notificar_cliente_processo, UFS_EMAIL_AUTOMATICO_SUSPENSO  # noqa: E402


def _criar_processo(db, uf="RJ", grupo_id=None):
    grupo_id = grupo_id or ("grupo-" + uuid.uuid4().hex[:8])
    p = Processo(
        id=str(uuid.uuid4()),
        empresa="Empresa Teste LTDA.",
        cnpj="11.222.333/0001-81",
        tipo_ato="alteracao",
        grupo_id=grupo_id,
        uf=uf,
    )
    db.add(p)
    db.commit()
    return p


class TestSupressaoPorUf(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_registro_sp_suprimido_nao_chama_envio_e_marca_pendente_revisao(self):
        p = _criar_processo(self.db, uf="SP")
        with patch("main.enviar_email") as mock_email, patch("main.enviar_email_anexo") as mock_anexo:
            resultado = notificar_cliente_processo(
                self.db, p, "registro", "Processo Finalizado - Empresa Teste", "corpo", "corpo_html",
                anexo_caminho="/tmp/x.pdf", anexo_nome="x.pdf",
            )
        self.assertFalse(resultado)
        mock_email.assert_not_called()
        mock_anexo.assert_not_called()
        self.assertEqual(p.email_status, "pendente_revisao")
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.sucesso)
        self.assertIn("suprimido", log.erro)

    def test_deferido_sp_tambem_suprimido(self):
        p = _criar_processo(self.db, uf="sp")  # minuscula - .upper() precisa cobrir
        with patch("main.enviar_email") as mock_email:
            resultado = notificar_cliente_processo(self.db, p, "deferido", "assunto", "corpo")
        self.assertFalse(resultado)
        mock_email.assert_not_called()
        self.assertEqual(p.email_status, "pendente_revisao")

    def test_protocolo_sp_nao_e_suprimido(self):
        """Tipo 'protocolo' nunca teve excecao de UF - so 'registro' e 'deferido'."""
        p = _criar_processo(self.db, uf="SP")
        self.db.add(EmailGrupo(id=str(uuid.uuid4()), email="cliente@exemplo.com", grupo_id=p.grupo_id))
        self.db.commit()
        with patch("main.enviar_email", return_value=True) as mock_email:
            resultado = notificar_cliente_processo(self.db, p, "protocolo", "assunto", "corpo")
        self.assertTrue(resultado)
        mock_email.assert_called_once()
        self.assertEqual(p.email_status, "enviado")

    def test_exigencia_sp_nao_e_suprimido(self):
        p = _criar_processo(self.db, uf="SP")
        self.db.add(EmailGrupo(id=str(uuid.uuid4()), email="cliente@exemplo.com", grupo_id=p.grupo_id))
        self.db.commit()
        with patch("main.enviar_email", return_value=True) as mock_email:
            resultado = notificar_cliente_processo(self.db, p, "exigencia", "assunto", "corpo")
        self.assertTrue(resultado)
        mock_email.assert_called_once()

    def test_registro_rj_nao_e_suprimido(self):
        p = _criar_processo(self.db, uf="RJ")
        self.db.add(EmailGrupo(id=str(uuid.uuid4()), email="cliente@exemplo.com", grupo_id=p.grupo_id))
        self.db.commit()
        with patch("main.enviar_email_anexo", return_value=True) as mock_anexo:
            resultado = notificar_cliente_processo(
                self.db, p, "registro", "assunto", "corpo", anexo_caminho="/tmp/x.pdf", anexo_nome="x.pdf",
            )
        self.assertTrue(resultado)
        mock_anexo.assert_called_once()
        self.assertEqual(p.email_status, "enviado")


class TestEmailStatusELog(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_envio_com_sucesso_marca_enviado_e_loga_sucesso(self):
        p = _criar_processo(self.db, uf="RJ")
        with patch("main.enviar_email", return_value=True):
            notificar_cliente_processo(self.db, p, "protocolo", "assunto", "corpo", destinatarios=["a@x.com", "b@x.com"])
        self.assertEqual(p.email_status, "enviado")
        logs = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).all()
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(l.sucesso for l in logs))

    def test_falha_em_todos_os_envios_marca_falhou_nao_pendente_revisao(self):
        """Falha de SMTP (destinatario invalido, timeout) e' um caso diferente
        de supressao proposital - precisa ficar visivel como 'falhou', nao
        confundir com 'pendente_revisao' (que so' e' pra supressao por UF)."""
        p = _criar_processo(self.db, uf="RJ")
        with patch("main.enviar_email", return_value=False):
            resultado = notificar_cliente_processo(self.db, p, "protocolo", "assunto", "corpo", destinatarios=["a@x.com"])
        self.assertFalse(resultado)
        self.assertEqual(p.email_status, "falhou")
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertFalse(log.sucesso)

    def test_sem_destinatario_marca_falhou_e_loga(self):
        p = _criar_processo(self.db, uf="RJ", grupo_id="grupo-sem-email")
        resultado = notificar_cliente_processo(self.db, p, "protocolo", "assunto", "corpo")
        self.assertFalse(resultado)
        self.assertEqual(p.email_status, "falhou")
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertIsNotNone(log)
        self.assertFalse(log.sucesso)

    def test_sucesso_parcial_conta_como_enviado(self):
        p = _criar_processo(self.db, uf="RJ")
        with patch("main.enviar_email", side_effect=[True, False]):
            resultado = notificar_cliente_processo(self.db, p, "protocolo", "assunto", "corpo", destinatarios=["a@x.com", "b@x.com"])
        self.assertTrue(resultado)
        self.assertEqual(p.email_status, "enviado")


class TestClassificacaoJuceb(unittest.TestCase):
    def setUp(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "automacao"))
        global classificar_status_ba
        from consultar_juceb import classificar_status_ba

    def test_indeferido_nao_e_classificado_como_deferido(self):
        self.assertEqual(classificar_status_ba("Requerimento INDEFERIDO em sessao"), "tramitacao")
        self.assertNotEqual(classificar_status_ba("Requerimento INDEFERIDO em sessao"), "deferido")

    def test_deferido_continua_classificado_corretamente(self):
        self.assertEqual(classificar_status_ba("Processo DEFERIDO"), "deferido")

    def test_finalizado_continua_classificado_como_deferido(self):
        self.assertEqual(classificar_status_ba("FINALIZADO"), "deferido")

    def test_exigencia_continua_classificada_corretamente(self):
        self.assertEqual(classificar_status_ba("Em EXIGENCIA"), "exigencia")

    def test_indeferido_tem_prioridade_mesmo_com_acento_e_minuscula(self):
        self.assertEqual(classificar_status_ba("indeferido - processo arquivado"), "tramitacao")


class TestAvisadoDeferidoSoAvancaComSucesso(unittest.TestCase):
    """Antes desta correcao, p.avisado_deferido = True era setado incondicional,
    entao uma falha de envio (ou uma supressao por UF) nunca era detectada nem
    repetida no proximo ciclo de consulta. As duas chamadas reais de e-mail
    dentro de aplicar_classificacao (alerta admin + aviso cliente) sao
    mockadas explicitamente - nunca deixar isso sem mock aqui, o .env local
    tem credenciais SMTP reais."""

    def setUp(self):
        self.db = TestingSessionLocal()
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        import atualizar_status
        self.aplicar_classificacao = atualizar_status.aplicar_classificacao
        self._patch_admin = patch("atualizar_status.enviar_email_admin_todos")
        self._patch_admin.start()

    def tearDown(self):
        self._patch_admin.stop()
        self.db.close()

    def test_envio_com_sucesso_marca_avisado_deferido(self):
        import datetime
        p = _criar_processo(self.db, uf="RJ")
        self.db.add(EmailGrupo(id=str(uuid.uuid4()), email="cliente@exemplo.com", grupo_id=p.grupo_id))
        self.db.commit()
        with patch("main.enviar_email", return_value=True):
            self.aplicar_classificacao(self.db, p, "deferido", datetime.datetime.now())
        self.assertTrue(p.avisado_deferido)

    def test_falha_de_envio_nao_marca_avisado_deferido(self):
        import datetime
        p = _criar_processo(self.db, uf="RJ")
        self.db.add(EmailGrupo(id=str(uuid.uuid4()), email="cliente@exemplo.com", grupo_id=p.grupo_id))
        self.db.commit()
        with patch("main.enviar_email", return_value=False):
            self.aplicar_classificacao(self.db, p, "deferido", datetime.datetime.now())
        self.assertFalse(p.avisado_deferido)
        self.assertEqual(p.email_status, "falhou")

    def test_supressao_sp_nao_marca_avisado_deferido(self):
        import datetime
        p = _criar_processo(self.db, uf="SP")
        with patch("main.enviar_email") as mock_email:
            self.aplicar_classificacao(self.db, p, "deferido", datetime.datetime.now())
        mock_email.assert_not_called()
        self.assertFalse(p.avisado_deferido)
        self.assertEqual(p.email_status, "pendente_revisao")


if __name__ == "__main__":
    unittest.main()
