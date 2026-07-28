"""Testes da validacao de CNPJ (padrao numerico legado + alfanumerico
2026). Rodar com: python -m unittest backend.test_cnpj_utils -v
(ou de dentro de backend/: python -m unittest test_cnpj_utils -v)
"""

import unittest

from cnpj_utils import (
    extrair_raiz,
    formatar_cnpj,
    normalizar_cnpj,
    validar_cnpj,
)

# CNPJ numerico legado, valido e amplamente usado como caso de teste publico
CNPJ_NUMERICO_VALIDO = "11.222.333/0001-81"

# CNPJ alfanumerico valido, gerado e conferido via cnpj_utils._calcular_dv
# a partir da raiz de exemplo "12ABC34801FA" (ver historico de geracao)
CNPJ_ALFANUMERICO_VALIDO = "12.ABC.348/01FA-99"


class TestNormalizarCnpj(unittest.TestCase):
    def test_remove_mascara_e_sobe_maiuscula(self):
        self.assertEqual(normalizar_cnpj("12.abc.348/01fa-99"), "12ABC34801FA99")

    def test_string_vazia(self):
        self.assertEqual(normalizar_cnpj(""), "")

    def test_none(self):
        self.assertEqual(normalizar_cnpj(None), "")


class TestValidarCnpj(unittest.TestCase):
    def test_numerico_legado_valido(self):
        self.assertTrue(validar_cnpj(CNPJ_NUMERICO_VALIDO))

    def test_numerico_legado_sem_mascara(self):
        self.assertTrue(validar_cnpj("11222333000181"))

    def test_numerico_legado_dv_invalido(self):
        self.assertFalse(validar_cnpj("11.222.333/0001-80"))

    def test_alfanumerico_valido(self):
        self.assertTrue(validar_cnpj(CNPJ_ALFANUMERICO_VALIDO))

    def test_alfanumerico_valido_minusculo(self):
        self.assertTrue(validar_cnpj(CNPJ_ALFANUMERICO_VALIDO.lower()))

    def test_alfanumerico_dv_invalido(self):
        self.assertFalse(validar_cnpj("12.ABC.348/01FA-00"))

    def test_letra_nos_digitos_verificadores_invalido(self):
        # DVs sao sempre numericos, mesmo no padrao novo
        self.assertFalse(validar_cnpj("12ABC34801FAAB"))

    def test_comprimento_invalido(self):
        self.assertFalse(validar_cnpj("12ABC34801FA9"))
        self.assertFalse(validar_cnpj("12ABC34801FA999"))

    def test_caracter_invalido_no_corpo(self):
        self.assertFalse(validar_cnpj("12@BC34801FA99"))

    def test_string_vazia(self):
        self.assertFalse(validar_cnpj(""))


class TestFormatarCnpj(unittest.TestCase):
    def test_formata_numerico(self):
        self.assertEqual(formatar_cnpj("11222333000181"), "11.222.333/0001-81")

    def test_formata_alfanumerico(self):
        self.assertEqual(
            formatar_cnpj("12abc34801fa99"), "12.ABC.348/01FA-99"
        )

    def test_nao_formata_comprimento_invalido(self):
        self.assertEqual(formatar_cnpj("123"), "123")


class TestExtrairRaiz(unittest.TestCase):
    def test_raiz_numerica(self):
        self.assertEqual(extrair_raiz("11.222.333/0001-81"), "11222333")

    def test_raiz_alfanumerica(self):
        self.assertEqual(extrair_raiz(CNPJ_ALFANUMERICO_VALIDO), "12ABC348")

    def test_matriz_e_filial_compartilham_raiz(self):
        matriz = "12.ABC.348/0001-XX"
        filial = "12.ABC.348/0002-XX"
        self.assertEqual(extrair_raiz(matriz), extrair_raiz(filial))


if __name__ == "__main__":
    unittest.main()
