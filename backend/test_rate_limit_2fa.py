"""Teste do rate limiter de POST /login/verificar (codigo 2FA por e-mail):
- estoura o limite de tentativas erradas -> 429, mesmo com o codigo certo
  na tentativa seguinte (a conta fica temporariamente bloqueada)
- um codigo certo antes de estourar o limite continua funcionando (nao
  quebra o fluxo legitimo)
- acertar o codigo limpa o contador de falhas
- bloqueio nunca e' permanente e cresce a cada novo estouro (unitario,
  direto nas funcoes do rate limiter, sem esperar o relogio de verdade)

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_rate_limit_2fa -v
"""

import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Codigo2FA

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


def _criar_usuario_com_codigo(db, login, codigo="123456", expira_em=None):
    u = Usuario(
        id=str(uuid.uuid4()),
        login=login,
        senha_hash="x",
        grupo_id="grupo-teste",
        is_admin=False,
    )
    db.add(u)
    cod = Codigo2FA(
        id=str(uuid.uuid4()),
        usuario_id=u.id,
        login=login,
        codigo=codigo,
        expira_em=expira_em or (datetime.now() + timedelta(minutes=10)),
        usado=False,
    )
    db.add(cod)
    db.commit()
    return u, cod


class TestRateLimit2FAIntegracao(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        # cada teste usa um login proprio pra nao herdar estado do rate
        # limiter (dict em memoria do processo) de outro teste
        self.login = "usuario_" + uuid.uuid4().hex[:10]

    def tearDown(self):
        self.db.close()
        main._login_verificar_tentativas.pop(self.login, None)

    def test_estoura_limite_de_tentativas_bloqueia_mesmo_com_codigo_certo(self):
        _criar_usuario_com_codigo(self.db, self.login, codigo="654321")

        for _ in range(main._2FA_MAX):
            resp = client.post("/login/verificar", json={"login": self.login, "codigo": "000000"})
            self.assertEqual(resp.status_code, 401)

        # a proxima tentativa, mesmo com o codigo CORRETO, deve ser bloqueada
        resp = client.post("/login/verificar", json={"login": self.login, "codigo": "654321"})
        self.assertEqual(resp.status_code, 429)

    def test_codigo_certo_antes_de_estourar_limite_funciona_normalmente(self):
        _criar_usuario_com_codigo(self.db, self.login, codigo="111222")

        # 2 erros (abaixo do limite de main._2FA_MAX)
        for _ in range(2):
            resp = client.post("/login/verificar", json={"login": self.login, "codigo": "000000"})
            self.assertEqual(resp.status_code, 401)

        resp = client.post("/login/verificar", json={"login": self.login, "codigo": "111222"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.json())

    def test_acerto_limpa_contador_de_falhas(self):
        _criar_usuario_com_codigo(self.db, self.login, codigo="222333")
        for _ in range(2):
            client.post("/login/verificar", json={"login": self.login, "codigo": "000000"})
        client.post("/login/verificar", json={"login": self.login, "codigo": "222333"})

        self.assertNotIn(self.login, main._login_verificar_tentativas)


class TestRateLimit2FAUnitarioEscalonamento(unittest.TestCase):
    """Testa o escalonamento do bloqueio direto nas funcoes do rate limiter,
    sem depender do relogio de verdade (mais rapido e deterministico)."""

    def setUp(self):
        self.login = "conta_teste_" + uuid.uuid4().hex[:10]

    def tearDown(self):
        main._login_verificar_tentativas.pop(self.login, None)

    def _estourar_uma_vez(self):
        for _ in range(main._2FA_MAX):
            main._checar_rate_2fa(self.login)
            main._registrar_falha_2fa(self.login)

    def test_bloqueio_nao_e_permanente(self):
        self._estourar_uma_vez()
        reg = main._login_verificar_tentativas[self.login]
        agora = main._time.time()
        # bloqueado agora...
        self.assertFalse(main._checar_rate_2fa(self.login))
        # ...mas tem prazo pra acabar, nao e' um bloqueio pra sempre
        self.assertGreater(reg["bloqueado_ate"], agora)
        self.assertLess(reg["bloqueado_ate"], agora + main._2FA_BLOQUEIO_TETO + 60)

    def test_bloqueio_cresce_a_cada_novo_estouro(self):
        self._estourar_uma_vez()
        primeiro_bloqueio = main._login_verificar_tentativas[self.login]["bloqueado_ate"] - main._time.time()

        # simula o primeiro bloqueio ja ter expirado, sem esperar o relogio
        main._login_verificar_tentativas[self.login]["bloqueado_ate"] = 0
        main._login_verificar_tentativas[self.login]["inicio"] = 0  # forca reset da janela

        self._estourar_uma_vez()
        segundo_bloqueio = main._login_verificar_tentativas[self.login]["bloqueado_ate"] - main._time.time()

        self.assertGreater(segundo_bloqueio, primeiro_bloqueio)

    def test_bloqueio_tem_teto_e_nao_cresce_indefinidamente(self):
        # forca o nivel de bloqueio direto pra um valor alto, sem precisar
        # estourar o limite dezenas de vezes em loop
        main._login_verificar_tentativas[self.login] = {
            "inicio": main._time.time(), "falhas": main._2FA_MAX - 1, "bloqueado_ate": 0, "nivel_bloqueio": 10,
        }
        main._registrar_falha_2fa(self.login)
        bloqueio = main._login_verificar_tentativas[self.login]["bloqueado_ate"] - main._time.time()

        self.assertLessEqual(bloqueio, main._2FA_BLOQUEIO_TETO + 1)


if __name__ == "__main__":
    unittest.main()
