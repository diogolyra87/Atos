# Desvios da implementação do Assistente ATOS + Vigia Normativo (01/08/2026)

Registro rápido de duas decisões tomadas por conta própria durante a implementação, porque o
pedido original partia de premissas que não batiam com o estado real do código. Guardado aqui
pra não se perder em sessões futuras — se alguém for mexer nesse widget ou nos botões do bot
depois, precisa saber que isso foi construído do zero, não é "reaproveitar um padrão existente".

## 1. Paleta de cores — não existe identidade "Ametista" no sistema

O pedido dizia pra "manter a identidade visual Ametista já usada no resto do sistema". Não existe
essa paleta em lugar nenhum do código — nenhuma ocorrência de "ametista", roxo ou violeta em
`frontend/src/`. A paleta real usada em todo o sistema (login, cards, botões) é azul/teal:
`#2563eb` (azul primário) + `#2dd4bf` (teal, usado em gradientes de botão) + `#7a7790`/`#d9d5ea`
(tons neutros dos cards).

Decisão tomada: usei a paleta real como base, e apliquei um gradiente roxo/violeta
(`#7c3aed` → `#2dd4bf`) **só no widget do Assistente ATOS** (cabeçalho do chat e botão "Assistente
ATOS"), pra ele se diferenciar visualmente como "isso é um assistente de IA" sem entrar em
conflito com a identidade visual já estabelecida no resto da tela. Componente:
`frontend/src/components/Compartilhados.js`, função `AssistenteAtos`.

Diogo vai validar visualmente e pode pedir ajuste de cor como tarefa separada.

## 2. Botões inline do Telegram — implementados do zero, não existiam

O pedido dizia pra usar botões inline "Aprovar e aplicar"/"Rejeitar" **"mesmo padrão dos alertas
de SLA já existentes"**. Não existe esse padrão — conferi `monitor_sla.py` e `bot.py` inteiros:
todo alerta do sistema até 31/07/2026 era texto puro (`sendMessage` sem `reply_markup`), e
`bot.py` nunca tratava `callback_query` no loop de polling (só `message`).

O que foi construído do zero pra viabilizar a Parte B:
- `main.py`: `notificar_telegram_com_botoes(texto, botoes)` — primeira função do projeto a montar
  `reply_markup` com `inline_keyboard`.
- `bot.py`: `processar_callback(callback)` — primeiro tratamento de `callback_query` do bot;
  `main()` agora verifica `upd.get("callback_query")` antes de `upd.get("message")` no loop.
  Usa `answerCallbackQuery` (toast de confirmação) e `editMessageText` (marca a mensagem original
  como aprovada/rejeitada, com quem e quando).

Testado ponta a ponta em produção com uma mudança Nível 3 simulada de verdade (ver changelog do
`base_conhecimento_atos_registros_juntas.md`, seção 8) — Telegram real, botões reais, rejeição
simulada via chamada direta a `processar_callback` (não deu pra clicar de verdade sem interação
humana, mas o mesmo código que trataria o clique real foi exercitado).

Como esse padrão (botão + callback) é novo, vale considerar reaproveitá-lo pros alertas de SLA
existentes no futuro, se fizer sentido pro fluxo — não fiz isso agora porque não foi pedido e
mudaria o comportamento de um alerta que já funciona bem como está.

## 3. Vigia Normativo — 2 fontes corrigidas após o primeiro run real (01/08/2026)

O primeiro run real (ver changelog) encontrou erro em JUCESP (esperado, documentado no próprio
base_conhecimento como "bloqueia bots"), JucisRS e JUCEC (inesperado). Investigado e corrigido:

- **JUCEC**: erro era `SSLCertVerificationError` por hostname mismatch — o certificado do site é
  emitido pra `www.jucec.ce.gov.br`, e a URL semeada (vinda do documento-fonte) não tinha o `www`.
  Corrigido adicionando o `www`. Site nunca esteve fora do ar nem mudou nada — só faltava o prefixo.
- **JucisRS**: erro era 404 real, não bloqueio novo. A URL do documento-fonte
  (`jucisrs.rs.gov.br/tabela-de-precos`) está desatualizada — o CMS da JucisRS gera um slug com
  hash novo a cada republicação da página (confirmado via busca: existem pelo menos 3 URLs
  históricas diferentes pra essa mesma tabela, ex. `tabela-de-precos-660af5d9a6344`). Trocado pela
  URL do catálogo de serviços (`carta-de-servicos/servicos?servico=815`), que aponta pra tabela
  atual mas não muda de endereço a cada reajuste de preço — mais estável pra monitoramento por
  hash. Vale ficar de olho: se essa URL de catálogo também mudar no futuro, o padrão de "slug com
  hash" da JucisRS pode exigir uma abordagem diferente (ex: monitorar a página `/servicos` e
  seguir o link, em vez de fixar uma URL final).

Ambas revalidadas com sucesso (baseline gravado, zero erro) antes deste registro.
