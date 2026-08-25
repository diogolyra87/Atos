# Auditoria de automações — o que funciona de fato (25/08/2026)

Auditoria empírica, não leitura de código. Cada classificação abaixo tem evidência
concreta (execução real, log, registro no banco) — nunca "parece certo pelo código".
Metodologia: rodei o `atos-consulta.service` real (agendado, 7x/dia) ao vivo durante
esta auditoria (25/08, 10:00–10:14, log completo em `journalctl -u atos-consulta`),
testei conexões (Telegram) diretamente, e cruzei com `mane.db` (LogEmail, AuditLog,
`arquivo_registro`/`arquivo_guia_bancaria`, timestamps de atualização).

Categorias: **OK (verificado)** · **EXISTE MAS DESLIGADO** · **DESCONHECIDO** ·
**QUEBRADO** · **NÃO EXISTE**. Na dúvida, DESCONHECIDO.

## Divergências em relação à expectativa anterior

Três achados desta auditoria contradizem o que era esperado — sinalizados aqui antes
da tabela porque mudam decisões:

1. **Telegram está funcionando**, não com token inválido/401. Testei os dois caminhos
   de código que existem no projeto (`automacao/bot.py`, token hardcoded, e
   `main.py::notificar_telegram()`, via env vars `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID`)
   — ambos usam a mesma credencial (`.env` confirmado), ambos retornaram HTTP 200 /
   `ok:true` com `message_id` real, mensagem chegou no chat do Diogo. O comentário no
   código (`main.py:1369`) documenta um incidente de token 401 **antes de 19/08/2026**
   — já resolvido. A expectativa de 401 é informação desatualizada.
2. **JUCESC consulta não está mais desligada** — foi ativada em 24/08/2026 (commit
   `135af09`) e confirmada ao vivo nesta auditoria (25/08, 10:14, protocolo real
   265529433, histórico completo extraído corretamente).
3. **JUCESP (consulta de status) está QUEBRADA agora, mas por falha do lado deles**,
   não nosso: o site retorna, para toda e qualquer consulta, o erro de configuração
   `"No elements matching the key 'Jucesp_BasicHttpBinding' were found in the
   configuration element collection"` — um erro de binding ASP.NET/WCF no servidor da
   JUCESP. Confirmado em 3/3 protocolos reais testados diretamente (com screenshot).
   Isso explica por que a consulta agendada de hoje devolveu "vazio" para as 35
   empresas de SP — nosso código está corretamente tratando a ausência de resultado
   como fallback gracioso, mas está mascarando um erro de servidor real. Antes de hoje
   (LogEmail: 35 "deferido" + 8 "exigencia" + 38 "protocolo" + 35 "registro" em SP nos
   últimos 30 dias) a consulta funcionava — isto é uma degradação recente do lado da
   JUCESP, não um bug antigo nosso.
4. A emissão da guia bancária JUCERJA **não tem "116/116 testes"** — não existe suíte
   de testes formal para essa automação. O que existe: hoje (24-25/08/2026) rodei a
   primeira execução supervisionada real contra um processo real (Carvalho Hosken
   S.A.), corrigi 5 selectors que estavam incorretos/não confirmados (busca de CNPJ,
   botão de confirmação, tela de "Gerar Boleto" pós-confirmação, checkbox de ciência,
   geração do PDF via impressão em vez de download direto), e confirmei sucesso com
   PDF real validado (boleto bancário, R$ 1.100,00, código de barras, e-mail entregue a
   admin + 2 operadores, aberto e confirmado pelo próprio Diogo). Não foi "116 testes
   passando" — foi uma primeira validação supervisionada bem-sucedida após 5 correções
   ao vivo.

## Tabela por Junta

```
JUCERJA (RJ)
  Consulta de status        → OK (verificado)      25/08 10:05–10:12, 16 processos reais,
                                                     classificações corretas (EM EXIGÊNCIA,
                                                     CANCELADO POR PRAZO VENCIDO, AGUARDANDO
                                                     ASSINATURA, CUMPRINDO EXIGÊNCIA, etc.)
  Download de documento      → OK (verificado)      74 processos com arquivo_registro,
                                                     mais recente 24/08/2026 14:09
  Aviso de exigência         → OK (verificado)      8 e-mails "exigencia" (LogEmail,
                                                     30d); supressão de duplicata
                                                     confirmada ao vivo hoje
  Emissão de guia/taxa       → EXISTE MAS DESLIGADO trigger automático (Etapa 2b) não
                                                     existe em nenhum lugar do código
                                                     (grep confirma zero chamadas
                                                     automáticas a
                                                     processar_guia_bancaria_jucerja) -
                                                     só manual/supervisionado. Testado
                                                     com sucesso hoje (ver acima).
  Protocolo de ato           → NÃO EXISTE
  Certidões                  → NÃO EXISTE

JUCESP (SP)
  Consulta de status         → QUEBRADO (lado deles) Site retorna erro de configuração
                                                     ASP.NET/WCF pra toda consulta,
                                                     confirmado 3/3 hoje com screenshot.
                                                     Historicamente funcionava (evidência
                                                     de 30d em LogEmail) - degradação
                                                     recente, não bug nosso.
  Download de documento      → OK (verificado)      Via Infosimples (API paga, canal
                                                     separado do scraper quebrado acima) -
                                                     20 processos com arquivo_registro,
                                                     mais recente 24/08/2026 22:47
  Aviso de exigência         → OK (verificado, mas   35 "deferido" + 8 "exigencia" em 30d,
                                bloqueado agora)      mas novas detecções dependem da
                                                     consulta acima, que está quebrada
  Emissão de guia/taxa       → NÃO EXISTE
  Protocolo de ato           → NÃO EXISTE
  Certidões                  → EXISTE MAS DESCONHECIDO Endpoint
                                                     (junta-comercial/sp/simplifica) sem
                                                     confirmação de uma consulta 200 real
                                                     ainda, por documentação própria do
                                                     código (jucesp_infosimples.py)

JUCEB (BA)
  Consulta de status         → OK (verificado)      25/08 10:12-10:13, 3/3 processos reais,
                                                     dados completos extraídos
                                                     corretamente (classificação
                                                     "exigencia" com texto detalhado)
  Download de documento      → DESCONHECIDO         Nenhum sucesso desde 23/07/2026 (>1
                                                     mês) - e os 3 arquivos mais recentes
                                                     eram EXATAMENTE os corrompidos
                                                     achados/reparados nesta sessão. Bug de
                                                     substring corrigido hoje; saneamento
                                                     de HTML residual (bug do lado do
                                                     servidor deles) também corrigido hoje
                                                     - ainda sem uma execução limpa
                                                     confirmada pós-fix.
  Aviso de exigência         → OK (verificado)      Supressão de duplicata confirmada ao
                                                     vivo hoje (3/3 processos)
  Emissão de guia/taxa       → NÃO EXISTE
  Bug de substring           → CORRIGIDO            "DEFERIDO" in s capturando dentro de
                                                     "INDEFERIDO" - confirmado corrigido
                                                     em produção (INDEFERIDO checado
                                                     primeiro)

JUCEPE (PE)
  Consulta de status         → EXISTE MAS DESLIGADO  JUCEPE_LOGIN/JUCEPE_SENHA não
                                                     configuradas no .env - código pula
                                                     com aviso claro (bug de credencial
                                                     cruzada com JUCEB corrigido hoje).
                                                     0 processos PE pendentes no momento,
                                                     então nem há o que testar agora.
  Download de documento      → QUEBRADO             Mesma causa (sem credenciais) +
                                                     único arquivo recente (17/08) era um
                                                     dos corrompidos reparados nesta sessão
  Aviso de exigência         → DESCONHECIDO         Sem processos pendentes pra gerar
                                                     evidência fresca
  Emissão de guia/taxa       → NÃO EXISTE

JUCESC (SC)
  Consulta de status         → OK (verificado)      25/08 10:13-10:14, protocolo real
                                                     265529433 (MELI DEVELOPERS BRASIL),
                                                     histórico completo extraído
                                                     corretamente, classificação
                                                     "tramitacao" correta. Ativada
                                                     24/08/2026 (não está mais desligada).
  Download de documento      → NÃO EXISTE
  Aviso de exigência         → DESCONHECIDO         Único processo SC ainda em
                                                     tramitação - sem caso de exigência
                                                     pra testar ainda
  Emissão de guia/taxa       → NÃO EXISTE

Empreendedor Digital (plataforma compartilhada - MG/DF/CE/MS/MT/AP e outras)
  Consulta de status (DF)    → OK (verificado)      25/08 10:14, processo real (NEOENERGIA
                                                     DISTRIBUIÇÃO BRASÍLIA), classificação
                                                     "exigencia" com texto detalhado
                                                     extraído corretamente
  Consulta de status (MG/CE/
  MS/MT/AP)                  → DESCONHECIDO         0 processos pendentes nesses estados
                                                     no momento - código roda mas sem
                                                     nada pra consultar, sem evidência de
                                                     sucesso/falha real
  Download de documento      → DESCONHECIDO         Sem evidência levantada
  Emissão de guia/taxa       → NÃO EXISTE
```

## Buracos e riscos conhecidos (por prioridade)

1. **JUCESP consulta quebrada por erro no servidor deles** (erro de config
   ASP.NET/WCF). Afeta 16 processos SP pendentes agora mesmo — nenhum vai ter
   status atualizado até o lado deles corrigir. Não é algo que dá pra corrigir do
   nosso lado; monitorar e, se persistir por dias, considerar avisar o Diogo pra
   contato manual com a Junta. **Ação recomendada**: diferenciar no log "site
   retornou erro de configuração" de "site não retornou nada" (hoje os dois caem
   no mesmo "JUCESP vazio") pra facilitar detectar isso mais rápido da próxima vez.

2. **BA/PE download de documento sem confirmação recente de sucesso.** BA: mais de
   um mês sem um download limpo confirmado (e os 3 mais recentes eram justamente os
   corrompidos). PE: credenciais nem configuradas. Os fixes de hoje (substring, HTML
   residual, credencial cruzada) ainda não tiveram uma execução real pra confirmar
   que resolveram - só vai ter evidência na próxima vez que um processo BA/PE for
   pra "deferido"/"finalizado" e a automação tentar baixar de novo.

3. **JUCEPE sem credenciais reais configuradas.** `JUCEPE_LOGIN`/`JUCEPE_SENHA`
   vazias no `.env` - toda a automação de PE (consulta e download) fica parada até
   alguém cadastrar as credenciais reais da JUCEPE.

4. **Guia bancária JUCERJA: só uma execução supervisionada bem-sucedida até agora.**
   Funciona, mas é literalmente a primeira vez - vale rodar mais algumas vezes
   supervisionado (outros tipos de ato, outras empresas) antes de considerar ativar
   o gatilho automático (Etapa 2b), que segue desligada por decisão consciente.

5. **Telegram e JUCESC estão em melhor estado do que o esperado** - não é um risco,
   mas vale atualizar o entendimento: não precisa trocar token do Telegram (já está
   ok), e JUCESC já pode ser tratada como "ativa" em decisões futuras, não mais
   "aguardando validação".
