"""Regra de nomenclatura de exibicao para documentos que entram no ATOS via
upload (manual ou automacao das Juntas). Modulo separado (nao dentro de
main.py nem de atualizar_status.py) porque atualizar_status.py ja importa de
main.py - colocar a funcao em qualquer um dos dois criaria import circular
assim que o outro precisasse dela tambem."""
import os
import re

# Padrao real de "SecN" ainda nao confirmado com exemplos de producao (nenhum
# encontrado em anexos.nome_original nem em audit_logs ate 11/08/2026) - regex
# generico combinado com o Diogo: "Sec" + numero, com espaco/traco opcionais
# antes e entre "Sec" e o numero, perto do fim do nome (antes da extensao).
# Ajustar pontualmente aqui se aparecer um caso real que nao bater.
_PADRAO_SEC = re.compile(r"[\s\-]*Sec[\s\-]*\d+[\s]*$", re.IGNORECASE)
_PADRAO_JA_TEM_JUNTA = re.compile(r"-\s*JUNTA\s*$", re.IGNORECASE)


def aplicar_nomenclatura_junta(nome_arquivo: str) -> str:
    """Nome de exibicao padrao ATOS para qualquer documento que entra no
    sistema via upload (manual ou automatico). NUNCA altera o nome fisico
    em disco - so' o nome usado no anexo do e-mail e no nome de exibicao/
    download. Se o nome ja terminar em "- SecN" (variantes com espaco/traco),
    esse trecho e substituido por "- JUNTA". Caso contrario, "- JUNTA" e'
    so' acrescentado. Idempotente: nomes que ja terminam em "JUNTA" nao sao
    alterados de novo, para nao duplicar em re-processamentos."""
    if not nome_arquivo:
        return " - JUNTA"
    nome, ext = os.path.splitext(nome_arquivo)
    if _PADRAO_JA_TEM_JUNTA.search(nome):
        return nome_arquivo
    if _PADRAO_SEC.search(nome):
        nome = _PADRAO_SEC.sub(" - JUNTA", nome)
    else:
        nome = nome + " - JUNTA"
    return nome + ext
