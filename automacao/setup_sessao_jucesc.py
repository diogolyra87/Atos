# -*- coding: utf-8 -*-
"""Login supervisionado na JUCESC via gov.br, pra gerar o arquivo de sessao
persistida (jucesc_session.json) que o servidor reutiliza sem nunca ver a
senha do Diogo.

COMO RODAR (no PC do Diogo, nunca no servidor - o VPS nao tem tela):
    1. FECHE todas as janelas do Chrome normal antes de rodar (esse script
       usa um perfil dedicado separado do seu Chrome do dia a dia, mas o
       Chrome as vezes reclama de perfil em uso se houver qualquer instancia
       aberta - fechar tudo evita esse conflito).
    2. python setup_sessao_jucesc.py

O QUE ACONTECE:
1. Abre uma janela real do Chrome (headless=False, o Chrome de verdade
   instalado no PC - nao o Chromium generico do Playwright), usando um
   PERFIL DEDICADO em D:\\Mane\\automacao\\.chrome_profile_jucesc (separado
   do seu perfil pessoal - nao mexe nos seus favoritos/senhas/historico).
2. A JUCESC redireciona pro gov.br - Diogo digita usuario/senha e resolve
   o 2FA (app gov.br, SMS, o que estiver configurado) DIRETO na janela do
   navegador. Essa e' a UNICA vez que a senha e digitada, e nunca em lugar
   nenhum controlado por este script ou pelo ATOS - so' na tela oficial do
   gov.br.
3. Depois que a pagina da JUCESC carregar de verdade (nao mais o gov.br),
   volte pro terminal e aperte Enter.
4. O script salva os cookies/estado da sessao em jucesc_session.json (nesta
   mesma pasta) e imprime o comando pra subir esse arquivo pro servidor.

O jucesc_session.json contem cookies de uma sessao AUTENTICADA - equivale a
estar logado. Nunca commitar, nunca mandar por e-mail/chat sem necessidade,
nunca deixar em pasta compartilhada. Ja esta no .gitignore do projeto - o
mesmo vale pra pasta .chrome_profile_jucesc/ inteira (tambem contem cookies
de sessao), tambem ja adicionada.

A sessao do gov.br expira (nao se sabe ainda em quanto tempo - primeira vez
rodando isso). Quando o servidor detectar que a sessao caducou, ele avisa
(e-mail + Telegram) pedindo pra rodar este script de novo.

DEGRAU 1 (29/08/2026, NAO RESOLVEU): canal 'chrome' real +
--disable-blink-features=AutomationControlled + esconder navigator.webdriver
+ UA real - a tela do gov.br continuou travando depois do CPF (mesmo
sintoma). Confirmado por Diogo.

DEGRAU 2 (29/08/2026, tentativa atual): perfil persistente de verdade
(launch_persistent_context) em vez de contexto efemero - um perfil Chrome
com historico/cookies proprios acumulados ao longo do tempo passa mais
credibilidade pra deteccao de bot que um contexto squeaky-clean recem
criado. Mantém as mitigações do Degrau 1 (AutomationControlled desabilitado,
webdriver escondido, UA real, locale/timezone BR).

Se isso tambem travar, e' o Degrau 3 (cookies exportados do Chrome normal do
Diogo, sem o Playwright nunca tocar o login) - ver o pedido original."""
import sys
import os
from playwright.sync_api import sync_playwright

URL_ALVO = "https://regin.jucesc.sc.gov.br/requerimentoV2/ReimpressaoDocs.aspx"
DIR_MODULO = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SESSAO = os.path.join(DIR_MODULO, "jucesc_session.json")
DIR_PERFIL_CHROME = os.path.join(DIR_MODULO, ".chrome_profile_jucesc")

_SCRIPT_ANTI_DETECCAO = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


def _capturar_user_agent_real():
    """Abre uma instancia efemera do Chrome so' pra ler o User-Agent real,
    fecha em seguida. Feito separado do perfil persistente porque
    user_agent so' pode ser definido na hora de criar o contexto/perfil -
    precisa saber o valor ANTES de abrir o perfil de verdade."""
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True, channel="chrome")
        pg = nav.new_page()
        ua = pg.evaluate("() => navigator.userAgent")
        nav.close()
        return ua


def main():
    if not os.path.exists(DIR_PERFIL_CHROME):
        os.makedirs(DIR_PERFIL_CHROME)

    print("Capturando User-Agent real do Chrome...")
    user_agent_real = _capturar_user_agent_real()
    print("User-Agent:", user_agent_real)

    print("\nAbrindo o Chrome de verdade com perfil dedicado em:")
    print(" ", DIR_PERFIL_CHROME)
    print("(se der erro de perfil em uso, feche TODAS as janelas do Chrome e rode de novo)\n")

    with sync_playwright() as p:
        try:
            contexto = p.chromium.launch_persistent_context(
                user_data_dir=DIR_PERFIL_CHROME,
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
                user_agent=user_agent_real,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
            )
        except Exception as e:
            print("\nERRO ao abrir o Chrome com perfil persistente:", str(e)[:300])
            print("Se a mensagem mencionar perfil/lock em uso, feche TODAS as janelas")
            print("do Chrome (inclusive em segundo plano, verifique o gerenciador de")
            print("tarefas) e rode o script de novo.")
            sys.exit(1)

        contexto.add_init_script(_SCRIPT_ANTI_DETECCAO)
        pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
        pagina.goto(URL_ALVO, timeout=60000)

        print("=" * 70)
        print("Faca o login normalmente na janela do navegador que abriu:")
        print("  1. Se cair no gov.br, digite seu usuario/senha la.")
        print("  2. Resolva a verificacao em duas etapas (app/SMS) se pedir.")
        print("  3. Espere a pagina da JUCESC (ReimpressaoDocs) carregar de")
        print("     verdade, com o formulario de busca visivel.")
        print("=" * 70)
        print()
        print("Se travar de novo no mesmo ponto (depois do CPF, carregando pra")
        print("sempre), avise - precisamos ir pro Degrau 3 (cookies exportados do")
        print("seu Chrome normal, sem passar pelo Playwright).")
        input("\nDepois que a pagina da JUCESC carregar, volte aqui e aperte Enter... ")

        url_final = pagina.url
        titulo_final = pagina.title()
        print(f"\nURL atual: {url_final}")
        print(f"Titulo da pagina: {titulo_final}")

        ainda_no_login = (
            "sso.acesso.gov.br" in url_final
            or "login" in url_final.lower()
            or "acesso.gov.br" in url_final
        )
        if ainda_no_login:
            print("\nATENCAO: a pagina atual ainda parece ser do gov.br/login, nao da")
            print("JUCESC. A sessao provavelmente NAO vai funcionar. Confirme que")
            print("terminou o login (inclusive o 2FA) antes de continuar.")
            resposta = input("Salvar mesmo assim? (s/N): ").strip().lower()
            if resposta != "s":
                print("Cancelado - nada foi salvo. Rode o script de novo depois de logar.")
                contexto.close()
                sys.exit(1)

        contexto.storage_state(path=ARQUIVO_SESSAO)
        contexto.close()

    print()
    print("=" * 70)
    print(f"Sessao salva em: {ARQUIVO_SESSAO}")
    print("=" * 70)
    print()
    print("Agora suba esse arquivo pro servidor (rode este comando no seu PC,")
    print("fora deste script, num terminal com acesso SSH configurado):")
    print()
    print(f'  scp "{ARQUIVO_SESSAO}" root@187.77.60.91:/root/atos/automacao/jucesc_session.json')
    print()
    print("Depois de subir, avise que o arquivo esta no servidor pra continuar.")
    print()
    print("O perfil Chrome dedicado ficou salvo em", DIR_PERFIL_CHROME, "- da proxima")
    print("vez que precisar refazer o login, rodar este script de novo reaproveita")
    print("esse mesmo perfil (nao precisa recriar do zero).")


if __name__ == "__main__":
    main()
