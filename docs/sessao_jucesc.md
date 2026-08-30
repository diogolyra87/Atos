# Sessão JUCESC (login gov.br) — passo a passo

A automação de download da JUCESC opera autenticada no REGIN
(`regin.jucesc.sc.gov.br`), que exige login gov.br. Login gov.br não é
automatizável de ponta a ponta (2FA, e detecção de automação — ver histórico
abaixo), então usamos **sessão persistida**: Diogo loga uma vez no navegador
normal, exporta os cookies, e o servidor reutiliza essa sessão sem nunca ver
usuário/senha.

## Quando fazer isso

Sempre que o servidor avisar (e-mail + Telegram) que a sessão da JUCESC
expirou ou nunca existiu, **ou** proativamente quando o processo de teste
(atualmente 265529433, MELI DEVELOPERS BRASIL LTDA/SC) for deferido — nesse
caso o alerta de deferimento (mesma cadeia de notificação de sempre) é o
sinal pra fazer isso correndo, porque o teste real de download depende
disso.

## Passo a passo

1. **Instalar a extensão "Cookie-Editor"** no Chrome (Chrome Web Store,
   nome exato "Cookie-Editor", ícone de biscoito). Instalação só funciona
   manualmente — o Chrome bloqueia scripts/automação na própria Web Store
   ("The extensions gallery cannot be scripted"), confirmado em 29/08/2026.

2. **Logar normalmente** em:
   `https://regin.jucesc.sc.gov.br/requerimentoV2/ReimpressaoDocs.aspx`
   Vai cair no gov.br — logar com usuário/senha + 2FA como sempre. Sem
   automação no meio, então não deve travar (o travamento nos Degraus 1 e 2
   — Chrome via Playwright, com e sem perfil persistente — só acontecia
   quando o login passava pelo Playwright; login manual normal nunca
   travou).

3. **Com a página do REGIN carregada e logada:**
   - Clicar no ícone do Cookie-Editor na barra do Chrome.
   - Clicar em **Export** → escolher formato **JSON**.
   - Salvar/colar esse conteúdo num arquivo chamado
     `cookies_jucesc_export.json`, dentro de `D:\Mane\automacao\`.

4. **Rodar o conversor:**
   ```
   cd D:\Mane\automacao
   python converter_cookies_jucesc.py
   ```
   Isso lê `cookies_jucesc_export.json`, filtra só os cookies de domínio
   `jucesc`/`gov.br`, converte pro formato `storage_state` do Playwright, e
   gera `jucesc_session.json` na mesma pasta. Testado (29/08/2026) com dados
   sintéticos — inclusive validado carregando o resultado num contexto real
   do Playwright sem erro.

5. **Subir pro servidor** (o script já imprime esse comando no final):
   ```
   scp "D:\Mane\automacao\jucesc_session.json" root@187.77.60.91:/root/atos/automacao/jucesc_session.json
   ```

6. **Apagar o arquivo intermediário** `cookies_jucesc_export.json` (não
   precisa mais dele depois de gerar o `jucesc_session.json`).

7. Avisar que o arquivo está no servidor. A partir daí:
   - Roda-se `explorar_jucesc.py <protocolo>` no servidor pra confirmar/
     ajustar os seletores contra a página autenticada real (ver nota em
     `automacao/consultar_jucesc.py`, função `baixar_documento_jucesc`, pra
     saber exatamente o que já está confirmado e o que ainda é palpite).
   - Testa-se o download real contra um processo já deferido.
   - Só depois disso o gatilho automático é ligado — nunca antes de um
     download real bem-sucedido e validado (o PDF abre de fato, não só
     passa no `utils_pdf.py`).

## Segurança

`cookies_jucesc_export.json`, `jucesc_session.json` e a pasta
`.chrome_profile_jucesc/` (do Degrau 2, perfil persistente do
`setup_sessao_jucesc.py`) contêm cookies de sessão autenticada — tratar como
senha. Já estão no `.gitignore` (local e servidor). Nunca commitar. O repo
é público — conferir `git status` antes de qualquer push que toque a pasta
`automacao/`.

## Histórico (por que o fluxo é esse)

- **Degrau 1** (Chrome real via Playwright + `--disable-blink-features=
  AutomationControlled` + UA real + esconder `navigator.webdriver`) —
  travou na tela de login do gov.br depois do CPF. Não resolveu.
- **Degrau 2** (perfil Chrome persistente via `launch_persistent_context`,
  mesmas mitigações do Degrau 1) — travou do mesmo jeito. Não resolveu.
- **Degrau 3** (este documento) — login manual normal, sem Playwright,
  cookies exportados depois. Funciona porque o gov.br nunca vê nenhuma
  automação durante o login em si.
- Também tentado: `claude-in-chrome` (extensão controlando o Chrome real de
  Diogo) para navegar e clicar até a tela do gov.br — funcionou até a tela
  de login (a extensão foi bloqueada de interagir além disso, corretamente,
  e Diogo terminou o login manualmente na mesma janela). Confirmou que o
  problema é especificamente automação tocando os campos de
  usuário/senha/2FA, não o Chrome em si.
