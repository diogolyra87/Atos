"""Testes de automacao/jucesp_infosimples.py e do redirecionamento de e-mail
em modo teste de automacao/teste_jucesp_infosimples.py.

Nao bate na API real da Infosimples - as chamadas HTTP (requests.post/get) sao
mockadas, porque sao um servico pago de terceiro (nao um banco de dados
interno, que este projeto sempre testa contra sqlite real, nunca mockado).

Rodar com: python -m unittest backend.test_jucesp_infosimples -v
(ou de dentro de backend/: python -m unittest test_jucesp_infosimples -v)
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "automacao"))

import jucesp_infosimples as ji
import teste_jucesp_infosimples as tji


def _resposta(code, data=None, code_message=None):
    resp = MagicMock()
    resp.json.return_value = {
        "code": code,
        "code_message": code_message,
        "data": data or [],
    }
    return resp


class TestConsultaComSucesso(unittest.TestCase):
    @patch("jucesp_infosimples.requests.get")
    @patch("jucesp_infosimples.requests.post")
    def test_baixar_ficha_cadastral_sucesso(self, mock_post, mock_get):
        mock_post.return_value = _resposta(200, data=[{"ficha_emitida": "https://exemplo.com/ficha.pdf"}])
        mock_get.return_value = MagicMock(content=b"%PDF-conteudo-fake")
        mock_get.return_value.raise_for_status = MagicMock()

        destino = os.path.join(os.path.dirname(__file__), "_ficha_teste_tmp.pdf")
        try:
            ok = ji.baixar_ficha_cadastral("35215861263", "tok", "cpf", "senha", destino)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(destino))
            with open(destino, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-conteudo-fake")
        finally:
            if os.path.exists(destino):
                os.remove(destino)

    @patch("jucesp_infosimples.requests.get")
    @patch("jucesp_infosimples.requests.post")
    def test_baixar_certidao_simplificada_sucesso(self, mock_post, mock_get):
        mock_post.return_value = _resposta(200, data=[{"certidao_emitida": "https://exemplo.com/certidao.pdf"}])
        mock_get.return_value = MagicMock(content=b"%PDF-certidao-fake")
        mock_get.return_value.raise_for_status = MagicMock()

        destino = os.path.join(os.path.dirname(__file__), "_certidao_teste_tmp.pdf")
        try:
            ok = ji.baixar_certidao_simplificada("35215861263", "tok", "cpf", "senha", destino)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(destino))
            with open(destino, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-certidao-fake")
        finally:
            if os.path.exists(destino):
                os.remove(destino)

    @patch("jucesp_infosimples.requests.get")
    @patch("jucesp_infosimples.requests.post")
    def test_baixar_documento_sucesso(self, mock_post, mock_get):
        mock_post.return_value = _resposta(200, data=[{"digitalizacao": "https://exemplo.com/doc.pdf"}])
        mock_get.return_value = MagicMock(content=b"conteudo-doc")
        mock_get.return_value.raise_for_status = MagicMock()

        destino = os.path.join(os.path.dirname(__file__), "_doc_teste_tmp.pdf")
        try:
            ok = ji.baixar_documento("35215861263", "2446570264", "tok", "cpf", "senha", destino)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(destino))
        finally:
            if os.path.exists(destino):
                os.remove(destino)


class TestErroCredencialInvalida(unittest.TestCase):
    @patch("jucesp_infosimples.requests.post")
    def test_credencial_invalida_retorna_false(self, mock_post):
        mock_post.return_value = _resposta(611, code_message="Login e/ou senha invalidos")
        ok = ji.baixar_ficha_cadastral("35215861263", "tok", "cpf-errado", "senha-errada", "/tmp/nao_deve_existir.pdf")
        self.assertFalse(ok)

    @patch("jucesp_infosimples.requests.post")
    def test_credencial_invalida_certidao_retorna_false(self, mock_post):
        mock_post.return_value = _resposta(611, code_message="Login e/ou senha invalidos")
        ok = ji.baixar_certidao_simplificada("35215861263", "tok", "cpf-errado", "senha-errada", "/tmp/nao_deve_existir.pdf")
        self.assertFalse(ok)


class TestProtocoloInexistente(unittest.TestCase):
    @patch("jucesp_infosimples.requests.post")
    def test_protocolo_inexistente_retorna_false(self, mock_post):
        mock_post.return_value = _resposta(200, data=[])
        ok = ji.baixar_documento("00000000000", "0000000000", "tok", "cpf", "senha", "/tmp/nao_deve_existir.pdf")
        self.assertFalse(ok)

    @patch("jucesp_infosimples.requests.post")
    def test_nire_inexistente_certidao_retorna_false(self, mock_post):
        mock_post.return_value = _resposta(200, data=[])
        ok = ji.baixar_certidao_simplificada("00000000000", "tok", "cpf", "senha", "/tmp/nao_deve_existir.pdf")
        self.assertFalse(ok)

    @patch("jucesp_infosimples.requests.post")
    def test_erro_de_requisicao_retorna_false(self, mock_post):
        mock_post.side_effect = Exception("timeout")
        ok = ji.baixar_ficha_cadastral("35215861263", "tok", "cpf", "senha", "/tmp/nao_deve_existir.pdf")
        self.assertFalse(ok)


class TestRedirecionamentoEmailModoTeste(unittest.TestCase):
    def test_modo_teste_ativo_redireciona_para_admin(self):
        enviados = []
        with patch.object(tji, "ESCLARA_MODO_TESTE", True):
            tji.notificar_modo_teste(
                "cliente-real@exemplo.com",
                "Assunto Teste",
                "Corpo Teste",
                lambda dest, assunto, corpo: enviados.append((dest, assunto, corpo)),
            )
        self.assertEqual(len(enviados), 1)
        destinatario, assunto, corpo = enviados[0]
        self.assertEqual(destinatario, tji.EMAIL_ADMIN_TESTE)
        self.assertIn("MODO TESTE", corpo)
        self.assertIn("cliente-real@exemplo.com", corpo)

    def test_modo_teste_inativo_envia_para_destinatario_real(self):
        enviados = []
        with patch.object(tji, "ESCLARA_MODO_TESTE", False):
            tji.notificar_modo_teste(
                "cliente-real@exemplo.com",
                "Assunto Teste",
                "Corpo Teste",
                lambda dest, assunto, corpo: enviados.append((dest, assunto, corpo)),
            )
        self.assertEqual(len(enviados), 1)
        destinatario, assunto, corpo = enviados[0]
        self.assertEqual(destinatario, "cliente-real@exemplo.com")
        self.assertNotIn("MODO TESTE", corpo)

    def test_sem_destinatario_real_redireciona_mesmo_com_modo_teste_desligado(self):
        enviados = []
        with patch.object(tji, "ESCLARA_MODO_TESTE", False):
            tji.notificar_modo_teste(
                None,
                "Assunto Teste",
                "Corpo Teste",
                lambda dest, assunto, corpo: enviados.append((dest, assunto, corpo)),
            )
        self.assertEqual(len(enviados), 1)
        destinatario, assunto, corpo = enviados[0]
        self.assertEqual(destinatario, tji.EMAIL_ADMIN_TESTE)
        self.assertIn("MODO TESTE", corpo)


if __name__ == "__main__":
    unittest.main()
