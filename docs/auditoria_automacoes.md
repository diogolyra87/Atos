# Auditoria de Automações — ATOS (24/08/2026)

Auditoria só de leitura/diagnóstico (nenhum código ou deploy alterado nesta
tarefa). Critério: nada é "OK" só porque o código existe e parece correto —
cada linha marcada OK tem evidência empírica citada (log real, registro no
banco, ou teste executado agora). Regra usada em caso de dúvida: marcar
DESCONHECIDO em vez de chutar OK.

**Limitação de evidência importante**: os logs do `journalctl` só cobrem os
últimos **~6 dias** (desde 18/08/2026), não os 30 dias pedidos — é o limite
de retenção do journald no servidor, não uma escolha minha. Toda evidência de
log abaixo é desse período de 6 dias, salvo indicação contrária.

## Tabela-resumo

```
JUCERJA (RJ) → Consulta: OK*    | Download: OK      | Exigência: OK | Guia bancária: EXISTE MAS NÃO DEPLOYADO
JUCESP  (SP) → Consulta: OK*    | Download: EXISTE MAS DESLIGADO | Exigência: OK | Certidão simplificada: NÃO VERIFICADO
JUCEB   (BA) → Consulta: OK     | Download: NÃO VERIFICADO (sem caso no período) | Exigência: OK
JUCEPE  (PE) → Consulta: NÃO VERIFICADO | Download: NÃO VERIFICADO | RISCO CRÍTICO: credenciais erradas (ver abaixo)
JUCESC  (SC) → Consulta: OK (validado hoje) | Download: NÃO EXISTE (fora de escopo) | Exigência: NÃO VERIFICADO
JUCIS-DF     → Consulta: OK     | (via Empreendedor Digital)
JUCEMG       → Consulta: EXISTE MAS NÃO VALIDADO (só testado com protocolo fake)
JUCEC/JUCEMS/JUCEMAT/JUCAP → Consulta: EXISTE MAS NÃO VALIDADO (zero processo real no banco pra testar)
JucisRS      → Consulta: EXISTE MAS DESLIGADO (bloqueado por captcha Cloudflare)
JUCEAC/JUCERR → NÃO EXISTE (domínio nunca confirmado)
RN, PB       → NÃO EXISTE nenhuma automação (processos reais no banco, zero cobertura)

* OK com ressalva de taxa de falha intermitente relevante — ver detalhe por Junta.
```

Nenhuma Junta tem **protocolo/envio de ato** automatizado — capacidade
inexistente em todo o sistema hoje.

---

## JUCERJA (RJ)

| Capacidade | Status | Evidência |
|---|---|---|
| Consulta de status | **OK (verificado), com falha intermitente ~35%** | 790 tentativas no período, 516 sucessos (`JUCERJA: {...}`), 274 erros (264× "tabela de resultado nao apareceu" + 10× "protocolo nao encontrado"). Sucesso mais recente confirmado: hoje 24/08 16:09:19. |
| Download de documento (deferido/finalizado) | **OK (verificado)** | 14 tentativas no período, 13 sucessos ("documento baixado e processo atualizado para: finalizado"), 1 falha (link "Faça download" não apareceu em 15s). |
| Aviso de exigência | **OK (verificado)** | Mesma função compartilhada `aplicar_classificacao()`; e-mails de exigência confirmados em `log_emails` (7 no período, 6 com sucesso). |
| Emissão de guia bancária/taxa (`emitir_guia_jucerja.py`) | **EXISTE MAS NÃO DEPLOYADO** (mais grave que "desligado") | O módulo (`automacao/emitir_guia_jucerja.py`, 219 linhas) e a função que o orquestra (`processar_guia_bancaria_jucerja` em `main.py`) **só existem no PC local** (`D:\Mane`), nunca foram enviados pro servidor de produção — `grep` em `/root/atos/automacao/` e `/root/atos/backend/main.py` não encontra nenhum traço. A coluna `arquivo_guia_bancaria` também **não existe** na tabela `processos` do banco de produção. A própria docstring local confirma a intenção: *"ETAPA 2A: ainda NAO ligada a nenhum gatilho automatico, so' chamada manualmente (supervisionada) ate a Etapa 2b ser aprovada separadamente."* Os "116/116 testes" mencionados (`test_emitir_guia_jucerja.py`, 269 linhas) também são só locais — não há evidência de execução em produção. |

**Risco encontrado em `consultar_jucerja.py`**: 3 blocos `except: pass` /
`except:` genéricos (linhas 50, 59, 73) nos passos de login e confirmação do
"Termo de Utilização". Se o login ou a confirmação do termo falhar, o erro é
engolido silenciosamente e o script segue adiante — o problema só aparece
2 passos depois como o genérico "tabela de resultado nao apareceu". É
plausível que boa parte dos 264 erros desse tipo tenham causa raiz no login
(sessão expirada, timing, etc.) e não na tabela em si — mas isso está
mascarado.

**Risco de classificação**: `classificar_status_rj()` usa
`if d in s: return "deferido"` com `"DEFERIDO"` na lista de chaves — o mesmo
padrão de bug de substring do JUCEB (ver seção final), **não corrigido**
aqui. Um indeferimento real na JUCERJA seria classificado incorretamente
como deferido.

---

## JUCESP (SP)

| Capacidade | Status | Evidência |
|---|---|---|
| Consulta de status | **OK (verificado), com falha intermitente ~29%** | 629 tentativas, 448 sucessos, 181 "vazio" (nem erro nem exceção — `classificar()` roda mas as duas seletores de andamento/despacho voltam vazios). Zero exceções (`ERRO consulta JUCESP`) — as falhas são todas silenciosas, mais difíceis de diagnosticar que as da RJ (que ao menos têm mensagem de erro clara). |
| Download de documento deferido (Infosimples) | **EXISTE MAS DESLIGADO** | Bloco inteiro protegido por `if False and cls == "deferido" and not p.arquivo_registro:` em `processar_sp()`, desde 30/07/2026. Comentário no código explica o motivo: o endpoint `download-dc` baixava a cópia digitalizada avulsa ("SEM VALOR DE CERTIDAO"), não a Certidão de Inteiro Teor oficial — **4 processos reais** (NBD Brasil, Neoenergia Transmissora 13/16/17) chegaram a ser marcados "finalizado" com o documento errado antes de ser detectado, e foram revertidos manualmente. `processar_sp_registro_sem_protocolo()` também está desligada pelo mesmo motivo (`processos = []` hardcoded logo após a query). |
| Aviso de exigência | **OK (verificado)** | Mesma `aplicar_classificacao()` compartilhada; múltiplas linhas "EXIGENCIA" no log do período. |
| Certidão Simplificada (via Infosimples, botão manual) | **DESCONHECIDO / NÃO VERIFICADO** | Endpoint existe (`/processos/{id}/certidao-simplificada`), mas **zero linhas** em `audit_logs` com ação relacionada a certidão simplificada no histórico inteiro do banco — nunca foi usado com sucesso (ou nunca foi usado, ponto). Pra confirmar: alguém precisaria clicar o botão uma vez e eu verificar se o PDF chega e o `audit_logs` registra. |
| Emissão de guia/taxa | **NÃO EXISTE** | — |

**Risco de qualidade**: `consultar_jucesp.py` usa `pagina.wait_for_timeout(4000)`
fixo (não uma espera dinâmica por seletor) antes de ler o resultado — isso é
uma causa plausível dos 29% de "vazio" (a JUCESP pode estar simplesmente mais
lenta que 4s às vezes). Os outros módulos (RJ, BA, SC) usam
`wait_for_selector` com timeout mais longo, mais robusto.

**Risco de classificação**: `classificar()` também usa `if ch in junto: return "DEFERIDO"`
com `"DEFERIDO"` na lista — mesmo bug de substring, **não corrigido**.

---

## JUCEB (BA)

| Capacidade | Status | Evidência |
|---|---|---|
| Consulta de status | **OK (verificado)** | 132 tentativas no período, **132 sucessos, 0 erros** — 100%. Vários processos reais (Neoenergia Operação e Manutenção, Muçununga, Coelba) classificados corretamente como "EM EXIGÊNCIA" nos últimos dias. |
| Download de documento | **DESCONHECIDO / NÃO VERIFICADO (sem oportunidade no período)** | Nenhum processo BA chegou a "FINALIZADO" nesses 6 dias, então o download nunca foi disparado — não há evidência recente nem de sucesso nem de falha. Estruturalmente é o mesmo padrão de código do RJ (que funciona 93% das vezes), mas isso não é evidência de que funciona pra BA especificamente. |
| Aviso de exigência | **OK (verificado)** | Ver acima — múltiplos casos reais nos últimos dias. |
| Bug de substring DEFERIDO/INDEFERIDO | **CORRIGIDO** | Único módulo dos 4 (RJ/SP/BA/PE) com o fix — `INDEFERIDO` checado antes de `DEFERIDO`, com comentário explícito no código. |
| Emissão de taxa | **NÃO EXISTE** | — |

---

## JUCEPE (PE)

| Capacidade | Status | Evidência |
|---|---|---|
| Consulta de status | **DESCONHECIDO / NÃO VERIFICADO** | O ciclo roda normalmente (44 execuções no período, sempre "[PE] 0 processo(s) com protocolo") — mas isso é porque **não havia nada pra consultar**: dos 3 processos PE no banco, 2 já estão "finalizado" (corretamente excluídos) e 1 ainda não tem protocolo. Zero tentativas reais de consulta no período. |
| **RISCO CRÍTICO — credenciais erradas** | | `processar_pe()` chama `consultar_jucepe(p.numero_protocolo, JUCEB_LOGIN, JUCEB_SENHA, ...)` — usa as credenciais da **Bahia** pra logar no portal da **Pernambuco**. São domínios completamente diferentes: `consultar_jucepe.py` aponta pra `redesim.jucepe.pe.gov.br`, enquanto `JUCEB_LOGIN`/`JUCEB_SENHA` são credenciais de `regin.juceb.ba.gov.br`. Não existe `JUCEPE_LOGIN`/`JUCEPE_SENHA` nem no `.env` nem referenciado em nenhum lugar do código. **Isso quase certamente vai falhar no login** na primeira vez que houver um processo PE pendente de consulta real — e como nunca aconteceu no período auditado, ninguém percebeu ainda. |
| Download de documento | Mesmo problema de credenciais acima — **não testável até corrigir**. | |
| Bug de substring DEFERIDO/INDEFERIDO | **NÃO corrigido** | `classificar_status_pe()` idêntico ao padrão antigo do JUCEB, sem checagem de INDEFERIDO. |
| Emissão de taxa | **NÃO EXISTE** | — |

---

## JUCESC (SC)

| Capacidade | Status | Evidência |
|---|---|---|
| Consulta de status | **OK (validado hoje, 24/08)** | Testado contra o protocolo real 265529433 (MELI DEVELOPERS BRASIL LTDA) — extração de status e histórico corretos, classificação "Em Tramitação" → tramitacao correta. Ativado em `processar()` hoje às ~17:38. Só passou pelo ciclo automático hourly uma vez até o momento desta auditoria (o teste manual) — ainda não tenho um segundo ciclo automático independente pra confirmar estabilidade contínua. |
| Download de documento | **NÃO EXISTE** | Fora do escopo pedido nesse módulo (só acompanhamento de status). |
| Aviso de exigência | **NÃO VERIFICADO** | Reaproveita `aplicar_classificacao()` (mesma função testada em RJ/SP/BA), mas nenhum processo SC entrou em exigência ainda pra confirmar o caminho real. |
| Emissão de taxa | **NÃO EXISTE** | — |
| Bug de substring DEFERIDO/INDEFERIDO | **CORRIGIDO** (escrito já com o fix, junto com JUCEB) | — |

---

## Empreendedor Digital (plataforma pública compartilhada — MG/DF/CE/MS/MT/AP/RS/AC/RR)

Config em `automacao/estados_empreendedor_digital.json`, que já traz um campo
`validado_com_protocolo_real` — usei como evidência de primeira mão, mas
confirmei contra os logs também.

| Estado | Status | Evidência |
|---|---|---|
| **DF** (JUCIS-DF) | **OK (verificado)** | `validado_com_protocolo_real: true` no config (protocolo real 262347954, Neoenergia Distribuição Brasília, 01/08/2026). Confirmado nos logs de hoje: `[DF] {'status_texto': 'PENDENTE', 'classificacao': 'exigencia', ...}`. |
| **MG** (JUCEMG) | **EXISTE MAS NÃO VALIDADO** | `ativo: true`, mas `validado_com_protocolo_real: false` — só testado com protocolo **falso** (999999999), confirmando apenas o caminho de "não encontrado". Caminho de sucesso nunca visto. |
| **CE, MS, MT, AP** | **EXISTE MAS NÃO VALIDADO** | Mesma situação — ativos "por extrapolação" do comportamento do DF, mas **zero processos reais desses estados no banco** pra testar de verdade. |
| **RS** (JucisRS) | **EXISTE MAS DESLIGADO** | `ativo: false` — bloqueado por Cloudflare Turnstile (checkbox não valida, "Erro: null"). Precisaria de serviço de resolução de captcha (2Captcha/CapSolver) pra ativar. |
| **AC, RR** | **NÃO EXISTE** | Domínio nunca confirmado (DNS não resolveu nas tentativas registradas). |

---

## Buraco encontrado fora do pedido original: RN e PB sem nenhuma cobertura

O banco tem processos reais com `uf='RN'` (1) e `uf='PB'` (1), mas **nenhuma**
automação cobre esses estados — não estão nos módulos dedicados (SP/RJ/BA/PE/SC)
nem no config do Empreendedor Digital. Esses processos, se tiverem protocolo,
nunca são consultados automaticamente.

---

## Telegram — divergência da expectativa

O pedido original citava "token inválido/revogado (HTTP 401)" como um item
esperado. **Testei agora e não confirmei isso**:

- `getMe`: retornou HTTP 200, `ok: true` — token válido.
- `getChat` no `TELEGRAM_GRUPO_CHAT_ID` configurado: retornou `ok: true`,
  grupo "Atos" — o bot ainda tem acesso ao grupo.
- Busquei por erros de Telegram/401 nos logs do `atos-backend` e do
  `atos-consulta` dos últimos 6 dias: **nenhuma ocorrência real**. Os 401 que
  aparecem no log do backend são sessão expirada do próprio sistema ATOS
  (`x-token`), não relacionados ao Telegram.

Ou o problema já foi corrigido (rotação de token) sem anotação em nenhum
lugar que eu tenha visto, ou a informação que eu tinha estava desatualizada.
**Vale você confirmar** se ainda considera isso um problema em aberto — não
quero que essa auditoria dê a entender que "consertei" algo que talvez nunca
tenha sido meu escopo mexer.

---

## Buracos e riscos conhecidos — priorizado

1. **[ALTO] JUCEPE usando credenciais da Bahia** — `processar_pe()` vai
   falhar login na primeira consulta real de um processo PE pendente. Fácil
   de corrigir (criar `JUCEPE_LOGIN`/`JUCEPE_SENHA` reais no `.env` e trocar
   a referência), mas até lá é uma automação que *parece* ativa e vai
   simplesmente não funcionar quando for testada de verdade.
2. **[ALTO] Bug de substring DEFERIDO/INDEFERIDO presente em 3 dos 4 módulos
   dedicados** (RJ, SP, PE) — só JUCEB foi corrigido. Um indeferimento real
   nessas Juntas seria classificado como "deferido", notificando o cliente
   incorretamente de que o processo foi aprovado.
3. **[MÉDIO] Excepts genéricos em `consultar_jucerja.py` mascarando a causa
   raiz** dos ~35% de falha de consulta — o erro real (provavelmente no
   login) nunca aparece no log, só o sintoma downstream.
4. **[MÉDIO] RN e PB sem nenhuma automação** — gap de cobertura não
   documentado em lugar nenhum antes desta auditoria.
5. **[BAIXO/INFORMATIVO] Guia bancária JUCERJA nunca foi deployada** —
   confirma o que você já esperava, mas o estado real é "nem existe em
   produção", não só "trigger desligado".
6. **[BAIXO] `consultar_jucesp.py` com espera fixa de 4s** — plausível causa
   raiz de parte dos 29% de falha silenciosa; trocar por `wait_for_selector`
   como os outros módulos já fazem seria uma correção pequena e de baixo
   risco.
7. **[INFORMATIVO] Telegram parece saudável** — diverge do que você
   descreveu, confirmar se ainda é um problema.

---

## O que eu NÃO consegui verificar (e por quê)

- **Histórico além de 6 dias**: retenção do journald não cobre os 30 dias
  pedidos. Se quiser esse histórico mais longo no futuro, dá pra configurar
  `SystemMaxUse`/`MaxRetentionSec` no journald, ou apontar os logs pra um
  arquivo persistente próprio.
- **Download BA e exigência/download SC**: sem caso real no período — só
  vou ter evidência quando (se) acontecer naturalmente, ou você me avisa
  quando tiver um processo BA deferido / SC em exigência pra eu confirmar
  na hora, como fizemos com o protocolo da JUCESC hoje.
- **Certidão Simplificada (SP)**: preciso de um clique real (ou você me
  autoriza a disparar um teste) pra confirmar se funciona.
