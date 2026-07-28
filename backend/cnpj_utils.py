"""Validacao/normalizacao de CNPJ, incluindo o padrao alfanumerico que entra
em vigor em 31/07/2026 (Nota Tecnica COTEC/RFB). CNPJs numericos legados
continuam validos: a conversao de caractere para valor (ord(ch) - 48) da
o mesmo resultado de int(ch) para digitos 0-9, entao o mesmo algoritmo
mod-11 cobre os dois formatos.
"""

import re

_PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_CARACTERE_VALIDO = re.compile(r"^[A-Z0-9]$")


def normalizar_cnpj(cnpj: str) -> str:
    """Remove mascara (pontos, barra, hifen, espacos) e sobe para maiusculas."""
    if cnpj is None:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", cnpj).upper()


def _valor_caractere(ch: str) -> int:
    return ord(ch) - 48


def _calcular_dv(base: str, pesos: list) -> str:
    soma = sum(_valor_caractere(ch) * peso for ch, peso in zip(base, pesos))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def validar_cnpj(cnpj: str) -> bool:
    """True se o CNPJ (numerico legado ou alfanumerico novo) tem formato e
    digitos verificadores corretos."""
    doc = normalizar_cnpj(cnpj)
    if len(doc) != 14:
        return False
    if not all(_CARACTERE_VALIDO.match(ch) for ch in doc[:12]):
        return False
    if not doc[12:14].isdigit():
        return False

    dv1 = _calcular_dv(doc[:12], _PESOS_DV1)
    dv2 = _calcular_dv(doc[:12] + dv1, _PESOS_DV2)
    return doc[12:14] == dv1 + dv2


def formatar_cnpj(cnpj: str) -> str:
    """Aplica a mascara XX.XXX.XXX/XXXX-XX. Retorna o valor normalizado
    sem mascara se o comprimento nao for 14 (evita mascarar lixo)."""
    doc = normalizar_cnpj(cnpj)
    if len(doc) != 14:
        return doc
    return f"{doc[0:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:14]}"


def extrair_raiz(cnpj: str) -> str:
    """8 primeiros caracteres (raiz da matriz, usada pra agrupar filiais)."""
    return normalizar_cnpj(cnpj)[:8]
