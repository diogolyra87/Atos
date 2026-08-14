"""Testes do fluxo "esqueci minha senha": solicitar reset -> token gerado
-> trocar senha com o token -> login com a nova senha funciona. Cobre
tambem o rate-limit dedicado (independente do rate-limit de /login) e a
nao-enumeracao de contas (mensagem generica sempre).

Reaproveita o mesmo mecanismo de token de /convite/definir-senha (ver
test_convite_operador.py) - /esqueci-senha so preenche token_convite via
gerar_convite() e manda o e-mail; a validacao/troca de senha e' o endpoint
de convite ja existente e ja testado.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_esqueci_senha -v
"""

import unittest
import uuid
from unittest.mock import patch

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

from main import (  # noqa: E402
    app, get_db, _login_tentativas, _esqueci_senha_tentativas,
)
from fastapi.testclient import TestClient  # noqa: E402
import bcrypt  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _criar_usuario(db, senha_atual="SenhaAntiga123"):
    u = Usuario(
        id=str(uuid.uuid4()),
        login="cli_" + uuid.uuid4().hex[:8],
        senha_hash=bcrypt.hashpw(senha_atual.encode()[:72], bcrypt.gensalt()).decode(),
        nome="Cliente Teste",
        email="cliente@exemplo.com",
        grupo_id="grupo-x",
        is_admin=False,
        papel="cliente",
    )
    db.add(u)
    db.commit()
    return u


class TestFluxoEsqueciSenha(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        _login_tentativas.clear()
        _esqueci_senha_tentativas.clear()

    def tearDown(self):
        self.db.close()

    @patch("main.enviar_email", return_value=True)
    def test_fluxo_completo_solicitar_trocar_e_logar_com_nova_senha(self, mock_email):
        u = _criar_usuario(self.db, senha_atual="SenhaAntiga123")

        resp = client.post("/esqueci-senha", json={"login": u.login})
        self.assertEqual(resp.status_code, 200)
        mock_email.assert_called_once()

        self.db.refresh(u)
        self.assertIsNotNone(u.token_convite)
        token = u.token_convite

        resp_troca = client.post("/convite/definir-senha", json={"token": token, "senha": "SenhaNova456"})
        self.assertEqual(resp_troca.status_code, 200)

        resp_login_antiga = client.post("/login", json={"login": u.login, "senha": "SenhaAntiga123"})
        self.assertEqual(resp_login_antiga.status_code, 401)

        resp_login_nova = client.post("/login", json={"login": u.login, "senha": "SenhaNova456"})
        self.assertEqual(resp_login_nova.status_code, 200)

    @patch("main.enviar_email", return_value=True)
    def test_login_inexistente_retorna_mensagem_generica_sem_confirmar_nem_negar(self, mock_email):
        resp = client.post("/esqueci-senha", json={"login": "login-que-nao-existe-" + uuid.uuid4().hex})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Se o login existir", resp.json()["mensagem"])
        mock_email.assert_not_called()

    @patch("main.enviar_email", return_value=True)
    def test_token_expirado_rejeitado_ao_trocar_senha(self, mock_email):
        u = _criar_usuario(self.db)
        client.post("/esqueci-senha", json={"login": u.login})
        self.db.refresh(u)
        from datetime import datetime, timedelta
        u.convite_expira_em = datetime.now() - timedelta(hours=1)
        self.db.commit()

        resp = client.post("/convite/definir-senha", json={"token": u.token_convite, "senha": "OutraSenha789"})
        self.assertEqual(resp.status_code, 410)

    @patch("main.enviar_email", return_value=True)
    def test_token_invalido_retorna_404(self, mock_email):
        resp = client.post("/convite/definir-senha", json={"token": "token-que-nunca-existiu", "senha": "SenhaX123"})
        self.assertEqual(resp.status_code, 404)

    @patch("main.enviar_email", return_value=True)
    def test_rate_limit_de_esqueci_senha_nao_bloqueia_login_do_mesmo_ip(self, mock_email):
        u = _criar_usuario(self.db, senha_atual="SenhaValida123")
        # Estoura o limite (5) so' de pedidos de "esqueci minha senha"
        for _ in range(6):
            client.post("/esqueci-senha", json={"login": u.login})
        bloqueado = client.post("/esqueci-senha", json={"login": u.login})
        self.assertEqual(bloqueado.status_code, 429)

        # Login continua funcionando normalmente - balde separado
        resp_login = client.post("/login", json={"login": u.login, "senha": "SenhaValida123"})
        self.assertEqual(resp_login.status_code, 200)

    def test_rate_limit_de_login_nao_bloqueia_esqueci_senha_do_mesmo_ip(self):
        u = _criar_usuario(self.db, senha_atual="SenhaValida123")
        # Estoura o limite (5) so' de tentativas de login com senha errada
        for _ in range(6):
            client.post("/login", json={"login": u.login, "senha": "senha-errada"})
        bloqueado = client.post("/login", json={"login": u.login, "senha": "senha-errada"})
        self.assertEqual(bloqueado.status_code, 429)

        # Esqueci-senha continua funcionando normalmente - balde separado
        with patch("main.enviar_email", return_value=True) as mock_email:
            resp = client.post("/esqueci-senha", json={"login": u.login})
            self.assertEqual(resp.status_code, 200)
            mock_email.assert_called_once()


if __name__ == "__main__":
    unittest.main()
