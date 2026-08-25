"""Testes de notificar_operadores() - notificacao por e-mail a TODOS os
operadores (papel='operador', com e-mail cadastrado) a cada insercao ou
atualizacao de processo. Ao contrario de notificar_cliente_processo, esta
funcao roda em paralelo e NUNCA suprime nada (sem logica de UF/status).

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_notificar_operadores -v
"""

import unittest
import uuid
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, LogEmail

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

from main import notificar_operadores  # noqa: E402


def _criar_operador(db, login, email, nome=None):
    login_unico = login + "_" + uuid.uuid4().hex[:8]
    u = Usuario(id=str(uuid.uuid4()), login=login_unico, senha_hash="x", nome=nome or login,
                email=email, grupo_id="grupo-admin", is_admin=False, papel="operador")
    db.add(u)
    db.commit()
    return u


def _criar_cliente(db, grupo_id="grupo-x"):
    u = Usuario(id=str(uuid.uuid4()), login="cli_" + uuid.uuid4().hex[:8], senha_hash="x",
                grupo_id=grupo_id, is_admin=False, papel="cliente")
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, uf="SP", **kwargs):
    dados = dict(id="MN-teste-" + uuid.uuid4().hex[:8], empresa="Empresa Teste LTDA.",
                 cnpj="11.222.333/0001-81", tipo_ato="AGE", grupo_id="grupo-x", uf=uf, status="aberto")
    dados.update(kwargs)
    p = Processo(**dados)
    db.add(p)
    db.commit()
    return p


class TestNotificarOperadores(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        # notificar_operadores consulta TODOS os operadores da tabela, sem
        # filtro por processo/grupo - limpa entre testes pra um teste nao
        # ver operadores criados por outro.
        self.db.query(Usuario).delete()
        self.db.query(LogEmail).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("main.enviar_email", return_value=True)
    def test_envia_para_todos_operadores_com_email(self, mock_email):
        _criar_operador(self.db, "david", "david@realpublicidade.com.br", "David Rangel")
        _criar_operador(self.db, "joao", "joao@realpublicidade.com.br", "Joao Victor")
        p = _criar_processo(self.db)

        resultado = notificar_operadores(self.db, "processo_criado", p.id, {"empresa": p.empresa})

        self.assertTrue(resultado)
        self.assertEqual(mock_email.call_count, 2)
        destinatarios = {call.args[0] for call in mock_email.call_args_list}
        self.assertEqual(destinatarios, {"david@realpublicidade.com.br", "joao@realpublicidade.com.br"})

    @patch("main.enviar_email", return_value=True)
    def test_ignora_operador_sem_email(self, mock_email):
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        _criar_operador(self.db, "conta_teste", "")  # sem email, tipo claude_teste_admin
        p = _criar_processo(self.db)

        notificar_operadores(self.db, "processo_criado", p.id, {"empresa": p.empresa})

        self.assertEqual(mock_email.call_count, 1)
        self.assertEqual(mock_email.call_args_list[0].args[0], "david@realpublicidade.com.br")

    @patch("main.enviar_email", return_value=True)
    def test_ignora_cliente_e_admin_puro(self, mock_email):
        _criar_cliente(self.db)  # papel=cliente, nao deve receber
        u_admin = Usuario(id=str(uuid.uuid4()), login="admin_puro", senha_hash="x",
                           email="admin@atos.net.br", grupo_id="grupo-admin", is_admin=True, papel="admin")
        self.db.add(u_admin)
        self.db.commit()
        p = _criar_processo(self.db)

        notificar_operadores(self.db, "processo_criado", p.id, {"empresa": p.empresa})

        mock_email.assert_not_called()

    @patch("main.enviar_email", return_value=True)
    def test_registra_log_com_destinatario_tipo_operador(self, mock_email):
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        p = _criar_processo(self.db)

        notificar_operadores(self.db, "processo_editado", p.id, {"empresa": p.empresa, "info": "uf: 'SP' -> 'RJ'"})

        logs = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].destinatario_tipo, "operador")
        self.assertEqual(logs[0].destinatario, "david@realpublicidade.com.br")
        self.assertEqual(logs[0].tipo, "processo_editado")
        self.assertTrue(logs[0].sucesso)

    @patch("main.enviar_email", return_value=True)
    def test_nunca_suprime_por_uf_sp(self, mock_email):
        # notificar_cliente_processo suprime registro/deferido para UFs em
        # UFS_EMAIL_AUTOMATICO_SUSPENSO - notificar_operadores NUNCA deve
        # ter essa logica, mesmo que o processo seja de uma UF suprimida.
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        p = _criar_processo(self.db, uf="SP")

        resultado = notificar_operadores(self.db, "status_atualizado_automatico", p.id,
                                          {"empresa": p.empresa, "valor_anterior": "tramitacao", "valor_novo": "deferido"})

        self.assertTrue(resultado)
        mock_email.assert_called_once()

    @patch("main.enviar_email", return_value=False)
    def test_falha_de_envio_fica_registrada_sem_quebrar(self, mock_email):
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        p = _criar_processo(self.db)

        resultado = notificar_operadores(self.db, "processo_criado", p.id, {"empresa": p.empresa})

        self.assertFalse(resultado)
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertFalse(log.sucesso)
        self.assertIsNotNone(log.erro)

    def test_sem_operador_nenhum_nao_quebra(self):
        p = _criar_processo(self.db)
        resultado = notificar_operadores(self.db, "processo_criado", p.id, {"empresa": p.empresa})
        self.assertFalse(resultado)


if __name__ == "__main__":
    unittest.main()
