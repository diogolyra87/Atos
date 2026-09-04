"""Teste do bug de falso positivo sistematico em GET /processos/checar-duplicidade
(04/09/2026): a checagem comparava o processo pendente recem-criado por
/processos/analisar contra TODOS os processos do grupo sem excluir a si mesmo -
como o pendente ja estava gravado no banco com os mesmos dados que estavam sendo
checados, ela sempre se encontrava e retornava duplicado=True pra QUALQUER insercao.

Correcao: novo parametro excluir_processo_id, passado pelo frontend com o
processo_id que ja veio de /processos/analisar.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_checar_duplicidade -v
"""

import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo

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


def _criar_usuario(db, login, papel="operador", grupo_id="grupo-x"):
    u = Usuario(
        id=str(uuid.uuid4()), login=login, senha_hash="x",
        grupo_id=grupo_id, token=str(uuid.uuid4()), token_criado_em=datetime.now(),
        is_admin=(papel == "admin"), papel=papel,
    )
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, grupo_id="grupo-x", **kwargs):
    # sufixo unico por chamada: o banco em memoria e compartilhado entre
    # todos os metodos de teste da classe (StaticPool), entao dados fixos
    # colidiriam entre testes diferentes e fariam parecer duplicidade real
    # quando na verdade e so sujeira de outro teste.
    sufixo = uuid.uuid4().hex[:8]
    dados = dict(
        id=str(uuid.uuid4()), empresa="Empresa Teste LTDA. " + sufixo, cnpj="11.222.333/0001-81",
        tipo_ato="AGE", identificador_ato="AGE 10/01/2026 " + sufixo, data_ata="10/01/2026",
        hora_ata="14:00", uf="SP", grupo_id=grupo_id, status="aberto",
    )
    dados.update(kwargs)
    p = Processo(**dados)
    db.add(p)
    db.commit()
    return p


class TestChecarDuplicidade(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.operador = _criar_usuario(self.db, "op_" + uuid.uuid4().hex[:8])

    def tearDown(self):
        self.db.close()

    def _params(self, p, excluir=None):
        params = {
            "empresa": p.empresa, "tipo_ato": p.tipo_ato,
            "data_ata": p.data_ata, "hora_ata": p.hora_ata,
            "identificador_ato": p.identificador_ato,
        }
        if excluir is not None:
            params["excluir_processo_id"] = excluir
        return params

    def test_bug_original_sem_excluir_processo_id_dava_falso_positivo_contra_si_mesmo(self):
        """Reproduz o comportamento ANTES da correcao (frontend antigo, sem
        mandar excluir_processo_id): comparar o processo pendente contra
        todos os do grupo, incluindo ele mesmo, sempre achava duplicidade -
        mesmo sem existir nenhum outro ato igual no banco."""
        pendente = _criar_processo(self.db)
        resp = client.get(
            "/processos/checar-duplicidade",
            params=self._params(pendente),  # sem excluir_processo_id
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["duplicado"])  # falso positivo sistematico confirmado

    def test_ato_novo_nao_duplicado_com_excluir_processo_id_nao_dispara_alerta(self):
        """Fluxo real corrigido: o processo pendente recem-criado (mesma
        situacao do bug acima) agora manda seu proprio id em
        excluir_processo_id, como o frontend corrigido faz - nao deve mais
        se encontrar como duplicata de si mesmo."""
        pendente = _criar_processo(self.db)
        resp = client.get(
            "/processos/checar-duplicidade",
            params=self._params(pendente, excluir=pendente.id),
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["duplicado"])

    def test_ato_realmente_duplicado_ainda_dispara_alerta(self):
        """Um segundo processo, ja existente antes, com EXATAMENTE os mesmos
        dados (empresa+tipo+data+hora+identificador) - duplicidade genuina,
        deve continuar sendo detectada mesmo com excluir_processo_id setado
        pro processo novo (que e um id diferente do original)."""
        original = _criar_processo(self.db)
        novo_pendente = _criar_processo(
            self.db, empresa=original.empresa, tipo_ato=original.tipo_ato,
            data_ata=original.data_ata, hora_ata=original.hora_ata,
            identificador_ato=original.identificador_ato,
        )
        resp = client.get(
            "/processos/checar-duplicidade",
            params=self._params(novo_pendente, excluir=novo_pendente.id),
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["duplicado"])
        self.assertEqual(body["processo_id"], original.id)

    def test_ato_com_dados_diferentes_nao_dispara_alerta(self):
        """Empresa/data diferentes -> nao e duplicidade, mesmo com outro
        processo existente no mesmo grupo."""
        _criar_processo(self.db, empresa="Outra Empresa LTDA.", identificador_ato="AGE 05/02/2026", data_ata="05/02/2026")
        pendente = _criar_processo(self.db, empresa="Empresa Teste LTDA.", identificador_ato="AGE 10/01/2026", data_ata="10/01/2026")
        resp = client.get(
            "/processos/checar-duplicidade",
            params=self._params(pendente, excluir=pendente.id),
            headers={"x-token": self.operador.token},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["duplicado"])


if __name__ == "__main__":
    unittest.main()
