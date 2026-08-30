# -*- coding: utf-8 -*-
"""DEGRAU 3 (29/08/2026) - os Degraus 1 e 2 de setup_sessao_jucesc.py (Chrome
real + perfil persistente) nao resolveram o travamento do gov.br depois do
CPF - hipotese de deteccao de automacao mais agressiva do que essas
mitigacoes cobrem. Este degrau tira o Playwright do caminho do login por
completo: Diogo loga no Chrome NORMAL dele (sem nenhuma automacao
envolvida), exporta os cookies, e este script converte pro formato que o
Playwright usa (storage_state).

PASSO A PASSO PRO DIOGO:

1. Instalar a extensao "Cookie-Editor" no Chrome normal (nao precisa ser um
   perfil separado - e' o extensor free e bem conhecido, by cookie-editor.com,
   disponivel na Chrome Web Store). Buscar "Cookie-Editor" na Chrome Web
   Store e instalar.

2. Logar normalmente no REGIN da JUCESC:
   https://regin.jucesc.sc.gov.br/requerimentoV2/ReimpressaoDocs.aspx
   (vai cair no gov.br, fazer login + 2FA como sempre faz - sem Playwright
   no meio, entao nao deve travar).

3. Depois de logado, com a pagina do ReimpressaoDocs.aspx (ou qualquer
   pagina do REGIN) aberta e carregada de verdade:
   a. Clicar no icone da extensao Cookie-Editor na barra do Chrome.
   b. Clicar em "Export" (ou o icone de exportar).
   c. Escolher formato JSON (o Cookie-Editor as vezes oferece Header
      String/JSON/Netscape - escolher JSON).
   d. Isso copia o JSON pra area de transferencia (clipboard) - ou tem
      opcao de baixar como arquivo, dependendo da versao da extensao.
   e. Colar (ou salvar) esse conteudo num arquivo chamado
      cookies_jucesc_export.json, nesta mesma pasta
      (D:\\Mane\\automacao\\).

4. Rodar: python converter_cookies_jucesc.py
   Isso le cookies_jucesc_export.json e gera jucesc_session.json no formato
   que o Playwright entende (storage_state).

5. Subir jucesc_session.json pro servidor (o script imprime o comando scp
   no final, igual o setup_sessao_jucesc.py).

SEGURANCA: cookies_jucesc_export.json e jucesc_session.json contem cookies
de sessao autenticada - tratar como senha. Ja estao no .gitignore. Apagar
cookies_jucesc_export.json depois de gerar o jucesc_session.json (nao
precisa mais dele, e' so' um arquivo intermediario)."""
import json
import os
import sys

DIR_MODULO = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENTRADA = os.path.join(DIR_MODULO, "cookies_jucesc_export.json")
ARQUIVO_SAIDA = os.path.join(DIR_MODULO, "jucesc_session.json")

_MAPA_SAMESITE = {
    "strict": "Strict",
    "lax": "Lax",
    "no_restriction": "None",
    "unspecified": "Lax",
}


def _converter_cookie(c):
    """Converte um cookie no formato do Cookie-Editor/EditThisCookie
    (campos: domain, name, value, path, expirationDate, httpOnly, secure,
    sameSite, session) pro formato que Playwright storage_state espera
    (expires em vez de expirationDate, sameSite capitalizado)."""
    if c.get("session") or not c.get("expirationDate"):
        expires = -1
    else:
        expires = c["expirationDate"]

    same_site_bruto = str(c.get("sameSite", "unspecified")).lower()
    same_site = _MAPA_SAMESITE.get(same_site_bruto, "Lax")

    return {
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
        "expires": expires,
        "httpOnly": bool(c.get("httpOnly", False)),
        "secure": bool(c.get("secure", False)),
        "sameSite": same_site,
    }


def main():
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: {ARQUIVO_ENTRADA} nao existe.")
        print("Exporte os cookies do Cookie-Editor (formato JSON) e salve com esse")
        print("nome exato nesta pasta antes de rodar este script. Ver instrucoes no")
        print("topo deste arquivo (converter_cookies_jucesc.py).")
        sys.exit(1)

    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as f:
        try:
            cookies_brutos = json.load(f)
        except json.JSONDecodeError as e:
            print("ERRO: o arquivo nao e' um JSON valido:", e)
            print("Confirme que colou o conteudo exportado pelo Cookie-Editor sem")
            print("alterar nada (inclusive sem texto extra antes/depois do JSON).")
            sys.exit(1)

    if not isinstance(cookies_brutos, list):
        print("ERRO: esperava uma lista de cookies (formato do Cookie-Editor) mas")
        print("recebi:", type(cookies_brutos).__name__)
        sys.exit(1)

    relevantes = [c for c in cookies_brutos if "jucesc" in c.get("domain", "").lower() or "gov.br" in c.get("domain", "").lower()]
    if not relevantes:
        print("AVISO: nenhum cookie de dominio 'jucesc' ou 'gov.br' encontrado no")
        print("export - confirme que exportou estando na aba do REGIN (nao outra")
        print("aba/site). Convertendo TODOS os cookies do arquivo mesmo assim, pra")
        print("nao travar - revise o resultado antes de subir pro servidor.")
        relevantes = cookies_brutos

    cookies_convertidos = [_converter_cookie(c) for c in relevantes]

    storage_state = {
        "cookies": cookies_convertidos,
        "origins": [],
    }

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(storage_state, f, ensure_ascii=False, indent=2)

    print(f"OK - {len(cookies_convertidos)} cookie(s) convertido(s).")
    print(f"Salvo em: {ARQUIVO_SAIDA}")
    print()
    print("Dominios encontrados:", sorted(set(c["domain"] for c in cookies_convertidos)))
    print()
    print("Agora suba esse arquivo pro servidor:")
    print()
    print(f'  scp "{ARQUIVO_SAIDA}" root@187.77.60.91:/root/atos/automacao/jucesc_session.json')
    print()
    print(f"Depois, apague {ARQUIVO_ENTRADA} (nao precisa mais dele) e avise que o")
    print("arquivo esta no servidor pra continuar.")


if __name__ == "__main__":
    main()
