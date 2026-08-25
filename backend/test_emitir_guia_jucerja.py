"""Testes da emissao automatica de Guia Bancaria JUCERJA (Etapa 2a):
- resolver_ato_evento (mapeamento tipo_ato+tipo_sociedade -> Ato/Evento)
- notificar_taxa_jucerja (e-mail unificado sucesso/falha, log com
  destinatario_tipo distinto)
- processar_guia_bancaria_jucerja (orquestracao: idempotencia, uf != RJ,
  sucesso/falha da automacao) - emitir_guia_bancaria sempre mockada, nunca
  chama Playwright/rede de verdade.

Etapa 2a NAO liga isso a nenhum gatilho automatico - so' testa as pecas
prontas pra a execucao supervisionada manual.

Roda contra um banco sqlite em memoria (nao toca em backend/mane.db).
Rodar com: python -m unittest test_emitir_guia_jucerja -v
"""

import os
import sys
import uuid
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, LogEmail, AuditLog

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "automacao"))
from emitir_guia_jucerja import resolver_ato_evento  # noqa: E402

from main import notificar_taxa_jucerja, processar_guia_bancaria_jucerja  # noqa: E402


def _criar_operador(db, login, email):
    u = Usuario(id=str(uuid.uuid4()), login=login + "_" + uuid.uuid4().hex[:8], senha_hash="x",
                email=email, grupo_id="grupo-admin", is_admin=False, papel="operador")
    db.add(u)
    db.commit()
    return u


def _criar_processo(db, **kwargs):
    dados = dict(id="MN-teste-" + uuid.uuid4().hex[:8], empresa="Empresa Teste RJ LTDA.",
                 cnpj="11.222.333/0001-81", tipo_ato="AGE", tipo_sociedade="SA",
                 grupo_id="grupo-x", uf="RJ", status="aberto")
    dados.update(kwargs)
    p = Processo(**dados)
    db.add(p)
    db.commit()
    return p


class TestResolverAtoEvento(unittest.TestCase):
    def test_mapeamentos_aprovados_sa(self):
        for tipo_ato, ato_valor in [("AGE", "7"), ("AGO", "6"), ("AGOE", "8"), ("AGD", "14"), ("RCA", "17"), ("ARD", "16")]:
            r = resolver_ato_evento(tipo_ato, "SA")
            self.assertIsNotNone(r, f"{tipo_ato}/SA deveria mapear")
            self.assertEqual(r["ato_valor"], ato_valor)
            self.assertEqual(r["tipo_juridico"], "3")

    def test_ars_so_mapeia_ltda(self):
        self.assertIsNotNone(resolver_ato_evento("ARS", "LTDA"))
        self.assertIsNone(resolver_ato_evento("ARS", "SA"))

    def test_age_nao_mapeia_ltda(self):
        # AGE (Assembleia Geral) nao existe como Ato pra LTDA no formulario real
        self.assertIsNone(resolver_ato_evento("AGE", "LTDA"))

    def test_alteracao_contratual_mapeia_ltda_e_sa(self):
        for ts in ("LTDA", "SA"):
            r = resolver_ato_evento("Alteração Contratual", ts)
            self.assertIsNotNone(r)
            self.assertEqual(r["ato_valor"], "2")
            self.assertEqual(r["evento_valor"], "141")

    def test_sinonimos_alteracao_contratual(self):
        base = resolver_ato_evento("Alteração Contratual", "LTDA")
        for sinonimo in ("ALTERACAO_CONTRATUAL", "Alteracao Contratual"):
            r = resolver_ato_evento(sinonimo, "LTDA")
            self.assertEqual(r, base)

    def test_sinonimos_constitutivo(self):
        base_sa = resolver_ato_evento("_CONSTITUTIVO", "SA")
        base_ltda = resolver_ato_evento("_CONSTITUTIVO", "LTDA")
        for sinonimo in ("ESCRITURA_PUBLICA_CONSTITUICAO", "ESCRITURA_PUBLICA", "Contrato Social"):
            self.assertEqual(resolver_ato_evento(sinonimo, "SA"), base_sa)
            self.assertEqual(resolver_ato_evento(sinonimo, "LTDA"), base_ltda)

    def test_ato_empresa_lider_independe_de_tipo_sociedade(self):
        r1 = resolver_ato_evento("ATO_EMPRESA_LIDER", "")
        r2 = resolver_ato_evento("ATO_EMPRESA_LIDER", "SA")
        self.assertIsNotNone(r1)
        self.assertEqual(r1, r2)
        self.assertEqual(r1["tipo_juridico"], "5")
        self.assertEqual(r1["ato_valor"], "3")

    def test_tipo_ato_desconhecido_retorna_none(self):
        self.assertIsNone(resolver_ato_evento("TIPO_INVENTADO", "SA"))

    def test_tipo_sociedade_vazio_retorna_none(self):
        self.assertIsNone(resolver_ato_evento("AGE", ""))
        self.assertIsNone(resolver_ato_evento("AGE", None))


class TestNotificarTaxaJucerja(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.db.query(Usuario).delete()
        self.db.query(LogEmail).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("main.enviar_email_anexo", return_value=True)
    def test_sucesso_usa_enviar_email_anexo_e_loga_taxa_jucerja(self, mock_anexo):
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        p = _criar_processo(self.db)

        resultado = notificar_taxa_jucerja(self.db, p, sucesso=True, caminho_pdf="/tmp/guia.pdf")

        self.assertTrue(resultado)
        mock_anexo.assert_called_once()
        self.assertEqual(mock_anexo.call_args.kwargs.get("caminho_anexo"), "/tmp/guia.pdf")
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertEqual(log.destinatario_tipo, "taxa_jucerja")
        self.assertTrue(log.sucesso)

    @patch("main.enviar_email", return_value=True)
    def test_falha_usa_enviar_email_sem_anexo_e_loga_taxa_jucerja_falha(self, mock_email):
        _criar_operador(self.db, "joao", "joao@realpublicidade.com.br")
        p = _criar_processo(self.db)

        resultado = notificar_taxa_jucerja(self.db, p, sucesso=False, motivo_falha="site fora do ar")

        self.assertTrue(resultado)
        mock_email.assert_called_once()
        corpo_enviado = mock_email.call_args.args[2]
        self.assertIn("site fora do ar", corpo_enviado)
        log = self.db.query(LogEmail).filter(LogEmail.processo_id == p.id).first()
        self.assertEqual(log.destinatario_tipo, "taxa_jucerja_falha")
        self.assertEqual(log.erro, "site fora do ar")

    @patch("main.enviar_email", return_value=True)
    def test_mesma_lista_destinatarios_sucesso_e_falha(self, mock_email):
        # emails_admin() (admin fixo + operadores) - nao a query so'-operador
        # de notificar_operadores(). Aqui so' testamos o caminho de falha (sem
        # anexo) pra contar destinatarios via mock simples.
        _criar_operador(self.db, "david", "david@realpublicidade.com.br")
        _criar_operador(self.db, "joao", "joao@realpublicidade.com.br")
        p = _criar_processo(self.db)

        notificar_taxa_jucerja(self.db, p, sucesso=False, motivo_falha="erro x")

        self.assertEqual(mock_email.call_count, 2)


class TestProcessarGuiaBancariaJucerja(unittest.TestCase):
    def setUp(self):
        self.db = TestingSessionLocal()
        self.db.query(Usuario).delete()
        self.db.query(LogEmail).delete()
        self.db.query(AuditLog).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("main.notificar_taxa_jucerja", return_value=True)
    @patch("main.emitir_guia_bancaria")
    def test_sucesso_marca_processo_e_notifica(self, mock_emitir, mock_notificar):
        mock_emitir.return_value = {"sucesso": True, "motivo_falha": None, "caminho_pdf": "/root/atos/backend/uploads/x_guia_bancaria.pdf"}
        p = _criar_processo(self.db)

        with patch("main.JUCERJA_USUARIO", "user"), patch("main.JUCERJA_SENHA", "pass"):
            resultado = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)

        self.assertTrue(resultado["sucesso"])
        self.db.refresh(p)
        self.assertEqual(p.arquivo_guia_bancaria, "x_guia_bancaria.pdf")
        mock_notificar.assert_called_once()
        self.assertTrue(mock_notificar.call_args.kwargs.get("sucesso"))
        log = self.db.query(AuditLog).filter(AuditLog.processo_id == p.id).first()
        self.assertEqual(log.acao, "guia_bancaria_emitida")

    @patch("main.notificar_taxa_jucerja", return_value=True)
    @patch("main.emitir_guia_bancaria")
    def test_falha_nao_marca_processo_mas_notifica(self, mock_emitir, mock_notificar):
        mock_emitir.return_value = {"sucesso": False, "motivo_falha": "Campo Ato não carregou", "caminho_pdf": None}
        p = _criar_processo(self.db)

        with patch("main.JUCERJA_USUARIO", "user"), patch("main.JUCERJA_SENHA", "pass"):
            resultado = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)

        self.assertFalse(resultado["sucesso"])
        self.db.refresh(p)
        self.assertIsNone(p.arquivo_guia_bancaria)
        mock_notificar.assert_called_once()
        self.assertFalse(mock_notificar.call_args.kwargs.get("sucesso"))
        log = self.db.query(AuditLog).filter(AuditLog.processo_id == p.id).first()
        self.assertEqual(log.acao, "guia_bancaria_falhou")

    @patch("main.emitir_guia_bancaria")
    def test_idempotencia_nao_reemite_se_ja_tem_guia(self, mock_emitir):
        # Caso: processo que ja tinha a guia ANTES mesmo de rodar o fluxo
        # (estado pre-setado, ex: emitida manualmente por outro caminho).
        p = _criar_processo(self.db, arquivo_guia_bancaria="ja_existente.pdf")

        with patch("main.JUCERJA_USUARIO", "user"), patch("main.JUCERJA_SENHA", "pass"):
            resultado = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)

        self.assertTrue(resultado.get("ja_existia"))
        mock_emitir.assert_not_called()

    @patch("main.notificar_taxa_jucerja", return_value=True)
    @patch("main.emitir_guia_bancaria")
    def test_idempotencia_sequencial_segunda_chamada_nao_reemite(self, mock_emitir, mock_notificar):
        # Caso: idempotencia em sequencia real - primeira chamada emite e
        # marca o processo, segunda chamada pro MESMO processo (sem reset de
        # estado entre as duas) nao deve chamar a automacao de novo.
        mock_emitir.return_value = {"sucesso": True, "motivo_falha": None, "caminho_pdf": "/root/atos/backend/uploads/x_guia_bancaria.pdf"}
        p = _criar_processo(self.db)

        with patch("main.JUCERJA_USUARIO", "user"), patch("main.JUCERJA_SENHA", "pass"):
            primeiro = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)
            segundo = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)

        self.assertTrue(primeiro["sucesso"])
        self.assertNotIn("ja_existia", primeiro)
        mock_emitir.assert_called_once()  # so a primeira chamada de fato invocou a automacao

        self.assertTrue(segundo.get("ja_existia"))
        mock_emitir.assert_called_once()  # ainda 1 - a segunda chamada nao invocou de novo

        self.db.refresh(p)
        self.assertEqual(p.arquivo_guia_bancaria, "x_guia_bancaria.pdf")

    @patch("main.emitir_guia_bancaria")
    def test_uf_diferente_de_rj_nao_processa(self, mock_emitir):
        p = _criar_processo(self.db, uf="SP")

        resultado = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)

        self.assertFalse(resultado["sucesso"])
        mock_emitir.assert_not_called()

    def test_processo_inexistente_nao_quebra(self):
        resultado = processar_guia_bancaria_jucerja(self.db, "id-que-nao-existe", headless=True)
        self.assertFalse(resultado["sucesso"])

    @patch("main.notificar_taxa_jucerja", return_value=False)
    def test_sem_credenciais_configuradas_nao_quebra(self, mock_notificar):
        p = _criar_processo(self.db)
        with patch("main.JUCERJA_USUARIO", None), patch("main.JUCERJA_SENHA", None):
            resultado = processar_guia_bancaria_jucerja(self.db, p.id, headless=True)
        self.assertFalse(resultado["sucesso"])
        self.assertIn("JUCERJA_USUARIO", resultado["motivo_falha"])


if __name__ == "__main__":
    unittest.main()
