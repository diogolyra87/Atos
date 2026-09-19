"""Teste de HTML injection em _email_status_html: titulo, empresa_linha,
protocolo, nota_texto e o botao (label/href) podem vir de extracao por
IA/OCR ou edicao manual - se contiverem marcacao HTML, isso nao pode ir
cru pro e-mail que o cliente real recebe.

Teste unitario direto na funcao, sem tocar nenhuma tabela - so' precisa
importar main.py (mesmo import feito por todos os outros arquivos de
teste do projeto).
Rodar com: python -m unittest test_html_escape_email -v
"""

import unittest

from main import _email_status_html


PAYLOAD_SCRIPT = '<script>alert(1)</script>'
PAYLOAD_IMG_ONERROR = '<img src=x onerror=alert(document.cookie)>'


class TestEscapeEmailStatusHtml(unittest.TestCase):
    def test_empresa_linha_maliciosa_e_escapada(self):
        html_gerado = _email_status_html("aberto", "Aberto", "Seu processo foi recebido", PAYLOAD_SCRIPT)
        self.assertNotIn(PAYLOAD_SCRIPT, html_gerado)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html_gerado)

    def test_titulo_malicioso_e_escapado(self):
        html_gerado = _email_status_html("aberto", "Aberto", PAYLOAD_IMG_ONERROR, "Empresa Teste LTDA.")
        self.assertNotIn(PAYLOAD_IMG_ONERROR, html_gerado)
        self.assertIn('&lt;img src=x onerror=alert(document.cookie)&gt;', html_gerado)

    def test_protocolo_malicioso_e_escapado(self):
        html_gerado = _email_status_html(
            "tramitacao", "Tramitação", "Documento Protocolado", "Empresa Teste LTDA.",
            protocolo=PAYLOAD_SCRIPT,
        )
        self.assertNotIn(PAYLOAD_SCRIPT, html_gerado)
        self.assertIn('&lt;script&gt;', html_gerado)

    def test_nota_texto_malicioso_e_escapado(self):
        html_gerado = _email_status_html(
            "exigencia", "Exigência", "Processo em Exigência", "Empresa Teste LTDA.",
            nota_tipo="aguardando", nota_texto=PAYLOAD_IMG_ONERROR,
        )
        self.assertNotIn(PAYLOAD_IMG_ONERROR, html_gerado)

    def test_botao_href_malicioso_nao_quebra_o_atributo(self):
        html_gerado = _email_status_html(
            "aberto", "Aberto", "Seu processo foi recebido", "Empresa Teste LTDA.",
            botao={"label": "Acessar", "href": '"><script>alert(1)</script>'},
        )
        self.assertNotIn('"><script>', html_gerado)
        self.assertNotIn('<script>alert(1)</script>', html_gerado)

    def test_conteudo_legitimo_sem_marcacao_continua_normal(self):
        html_gerado = _email_status_html(
            "finalizado", "Finalizado", "Processo Finalizado, em anexo o registro",
            "Empresa Teste LTDA. · AGE 10/01/2026", protocolo="2026/00692268-3",
        )
        self.assertIn("Empresa Teste LTDA.", html_gerado)
        self.assertIn("2026/00692268-3", html_gerado)
        self.assertIn("Processo Finalizado, em anexo o registro", html_gerado)


if __name__ == "__main__":
    unittest.main()
