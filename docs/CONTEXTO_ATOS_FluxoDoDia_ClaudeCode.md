# CONTEXTO ATOS — Fluxo do Dia + Dashboard novo (para o Claude Code)

Cópia local (dentro do repo, `D:\Mane\docs\`) do spec original que vive em
`D:\ATOS\docs\CONTEXTO_ATOS_FluxoDoDia_ClaudeCode.md` (fora do git — por isso
uma sessão anterior "perdeu" esse arquivo depois de um reboot: ele nunca
esteve versionado). Guardar aqui também para aparecer no `git status`/`git log`
e não depender só de `D:\ATOS\docs`.

Este documento complementa o `CONTEXTO_ATOS_ClaudeCode.md` já existente (infra, stack,
regras de trabalho, estilo do Diogo — leia aquele primeiro se ainda não leu). Este aqui é
específico da tarefa: reestruturar o dashboard (admin e cliente) com cards de métrica,
o card "Fluxo do dia" e listagem agrupada por empresa.

---

## STATUS ATUAL (atualizado nesta sessão — 2026-07-24)

Backend da peça 2 (`vincular_fluxo_do_dia` + `registrar_evento`) **concluído e plugado em
todos os pontos de entrada**. Diferenças do spec original abaixo, decididas nesta sessão:

- **`registrar_evento`**: segue o padrão do spec (`db.add()` só, `except: pass` silencioso,
  sem `db.commit()` próprio). Por isso é chamada **sempre ANTES** do `db.commit()` da
  operação principal em cada ponto — não depois, senão o evento fica pendente na sessão e
  se perde no `db.close()` do `get_db()` (que não commita). Todos os 7 pontos abaixo já
  seguem essa ordem, conferido via `grep -n registrar_evento`.
- **Taxonomia de eventos foi ampliada além do spec original** (decisão consciente, não
  esquecimento): em vez de só 4 tipos (`protocolo_confirmado`, `exigencia_recebida`,
  `ata_enviada`, `finalizado`), ficou:
  - `ata_enviada` — `criar_processo` (main.py:1464)
  - `processo_criado_transferencia` — `_criar_processo_transferencia` (main.py:1510)
  - `protocolo_inserido` — PATCH manual (main.py:1576), upload de arquivo tipo=protocolo
    (main.py:1648), e bot Telegram (bot.py:325)
  - `registro_finalizado` — upload de arquivo tipo=registro (main.py:1648, via dict
    `_evento_upload`)
  - `nd_inserida` / `nf_inserida` — upload de Nota de Débito/Fiscal (main.py:1648)
  - `exigencia_registrada` — `registrar_exigencia` (main.py:1696)
  - `exigencia_cumprida` — `exigencia_cumprida` (main.py:1724)

  Se o frontend (`/eventos/recentes`, ainda não implementado) precisar filtrar por um
  conjunto fechado de tipos, mapear esses 8 tipos, não só os 4 do spec original.

- **Pontos de entrada de processo cobertos**: os dois únicos lugares que criam `Processo`
  no backend são `criar_processo` e `_criar_processo_transferencia` — ambos plugados com
  `vincular_fluxo_do_dia`. `bot.py` não cria processo, só vincula protocolo a um já
  existente, por isso lá só entra `registrar_evento`, não `vincular_fluxo_do_dia`.

- **LEITURA A CONFIRMADA POR DIOGO NESTA SESSÃO (2026-07-24).** Ver seção 0 abaixo — o
  gatilho de ">5 protocolos no dia" soma todas as empresas do mesmo `grupo_id`, não conta
  por CNPJ/empresa individual. Confirmado por mensagem direta do Diogo no chat: "Vou manter
  minha taxonomia, só ajusta o padrão de registrar_evento. E confirmado: Leitura A pro
  gatilho (soma todas as empresas do grupo, não por CNPJ individual)." Código atual já
  implementa Leitura A (`vincular_fluxo_do_dia` agrupa por `grupo_id`) — nenhuma mudança de
  código necessária, só a confirmação formal que faltava.

- **Deploy do backend em produção — CONCLUÍDO (2026-07-24).** `vincular_fluxo_do_dia` +
  `registrar_evento` + migração (`fluxos`, `eventos`, `fluxo_id`) e depois os endpoints
  `/fluxo/ativo` + `/eventos/recentes` foram enviados em dois deploys separados nesta sessão
  (push → pull no servidor → migração quando aplicável → restart `atos-backend`). Validado
  com teste ponta a ponta criando processo de verdade em produção (grupo NEOENERGIA, via
  chamada direta ao mesmo caminho de código de `criar_processo`, sem passar pela rota HTTP)
  e conferindo a gravação na tabela `eventos` — depois apagado. Commits: `07c0297` (tabelas +
  instrumentação) e `3e177de` (endpoints).

- **Etapa 3 concluída: endpoints `/fluxo/ativo` e `/eventos/recentes` implementados,
  testados localmente e em produção.** Ver seção 3.3 atualizada abaixo — a assinatura real
  usa `codigo_grupo` (não `grupo_id` cru), mesmo padrão de `listar_processos`.

- **Bug de segurança encontrado e corrigido nesta sessão: vazamento de dado entre grupos em
  `/fluxo/ativo`.** Quando um admin passava um `codigo_grupo` que não resolvia pra nenhum
  `Grupo` real (typo, código errado), o filtro da query não era aplicado (buscava fluxos de
  TODOS os grupos), mas a lógica de retorno ainda colapsava pro primeiro resultado
  (`resultado[0]`) por achar que "codigo_grupo foi passado" = "filtro está ativo" — sem
  checar se a resolução deu certo. Corrigido com um `return None` imediato quando o
  `codigo_grupo` não resolve. **Comprovado com teste empírico**: criado um Fluxo + Processo
  de teste pro grupo "ENEL TESTE" localmente, confirmado que um `codigo_grupo` inválido
  retornava o fluxo da Enel (vazamento real, não hipotético) antes da correção, e `null`
  depois. Dado de teste apagado ao final.

- **Drift de schema descoberto no banco LOCAL (`mane.db`), não em produção.** Ao testar os
  endpoints novos localmente, `db.query(Processo)`/`db.query(Usuario)` quebravam com
  `OperationalError: no such column`. O `mane.db` local estava desatualizado: tabela
  `usuarios` faltando 3 colunas (`email`, `token_criado_em`, `is_admin`) e `processos`
  faltando 12 colunas (`status_jucesp`, `uf_destino_transferencia`, `transferencia_criada`,
  `processo_origem_id`, `confirmacao_pendente`, `tipo_ato_sugerido`, `ultima_consulta_em`,
  `ultimo_alerta_em`, `aguardando_cliente`, `avisado_deferido`, `deferido_em`,
  `alertado_atraso_deferido`). Corrigido localmente via `ALTER TABLE` (dados preservados).
  **Confirmado por comparação direta contra produção (`PRAGMA table_info` via SSH, só
  leitura) que produção NÃO tem esse drift** — schema de produção bate 100% com o modelo
  atual em `database.py`, tanto em `processos` quanto em `usuarios`. Ou seja, o `mane.db`
  local é um artefato antigo de dev, nunca mantido em sincronia; não afeta produção nem foi
  causado por nada desta sessão.

- **Frontend do admin (App.js) — CONCLUÍDO (2026-07-27).** Os 5 componentes da seção 4
  implementados, testados visualmente no navegador (local, com dados de teste criados e
  apagados pra cada um) e commitados: `StatCard` (`1e77f08`), `FluxoDoDiaCard` (`9f4800f`),
  `StatusDonut` (`49a3351`), `AtividadeRecente` (`ec4d877`), `ListaProcessosAgrupada`
  (`cd04507`). Ver seção 4 abaixo pra detalhes/divergências do rascunho original de cada um
  (o mais notável: `ListaProcessosAgrupada` acabou agrupando por **data do ato**, não por
  empresa como o spec original sugeria — decisão tomada durante a implementação, ver seção 4).

- **Bug de dado encontrado durante o teste do `ListaProcessosAgrupada`: inconsistência de
  maiúscula/minúscula em `processos.empresa`** (ex: "Esperanca" vs "ESPERANCA" pra mesma
  empresa/CNPJ), gerando quase-duplicados na lista. Não é bug do Fluxo do Dia, mas foi achado
  e corrigido nesta sessão por afetar a qualidade do agrupamento: `empresa` agora é
  normalizado pra maiúscula em todo ponto de gravação (`criar_processo`,
  `_criar_processo_transferencia`, PATCH genérico — commit `1eb1f2d`). Migração dos
  registros existentes em **Python**, não SQL puro — confirmado que `UPPER()` nativo do
  SQLite não trata acentos (`ã`, `ç`, `é` ficam minúsculos). Script `aplica_uppercase_empresa.py`
  (gitignored) rodado local **e em produção** (5 de 72 processos corrigidos, com backup do
  `mane.db` do servidor antes — `mane-20260727-1521.db.gz.enc`); código deployado e
  `atos-backend` reiniciado. **Concluído, nada pendente aqui.**

- **Frontend do cliente (Cliente.js) — CONCLUÍDO (2026-07-27).** Os mesmos 5 componentes
  espelhados (commit `427cf79`), adaptados ao markup/estilos já existentes em `Cliente.js`
  (`s.empresa`/`s.metaEmp` em vez de `s.company`/`s.cnpj`, badge clicável com `clicarStatus`,
  botão "Ver processo", `abreviarAto` com 2 parâmetros — não 3, não tem `hora_ata` aqui).
  Confirmado e testado visualmente (local, injeção de sessão via `localStorage["mane_sessao"]`
  com usuário "Cliente" já existente no banco local). **Nenhum filtro de grupo novo foi
  necessário**: `/metricas`, `/fluxo/ativo`, `/eventos/recentes` e `/processos` já restringem
  sozinhos ao `grupo_id` do usuário logado quando `not usuario.is_admin` — confirmado lendo o
  código dos 4 endpoints antes de implementar, não por suposição. `FluxoDoDiaCard` só precisou
  tratar a resposta como objeto único/`null` em vez de lista (mesmo componente reaproveitado
  do admin sem nenhuma mudança de código, já que ele já recebia um `fluxo` único via prop).

  Com isso, a **seção 4 do doc está inteiramente concluída** (admin + cliente).

- **Deploy do frontend em produção — CONCLUÍDO (2026-07-27).** `npm run build` local →
  `scp` do bundle JS (`main.6ee78e94.js` + `.LICENSE.txt` + `.map`) e `index.html` pro
  servidor (`/var/www/atos/`) → bundle antigo (`main.265967f1.js`) removido. Cuidado tomado
  antes do build: `favicon.ico`/`index.html` tinham mudanças locais não commitadas de **outra
  tarefa** (não relacionada ao Fluxo do Dia) — feito `git stash push --` seletivo só nesses 2
  arquivos, build limpo gerado a partir da versão committed, deploy feito, depois
  `git stash pop` restaurando o trabalho da outra tarefa intacto. Smoke test via HTTPS com
  Host correto (nginx é vhost por nome, `server_name atos.net.br`) confirmou `200` em
  `index.html` e no bundle novo, referenciando o hash certo. **Fluxo do Dia está 100% em
  produção**: backend + frontend (admin e cliente).

### AINDA PENDENTE
Nada relacionado ao Fluxo do Dia. Se algum dia for necessário rodar o backend localmente de
novo, lembrar que o `mane.db` local tinha drift de schema (corrigido em sessão anterior, ver
acima) — se aparecer de novo `OperationalError: no such column`, comparar contra
`database.py` e aplicar `ALTER TABLE` pontual, sem recriar o banco (tem dado de dev que vale
manter).

---

## 0. GATILHO DO FLUXO DO DIA — LEITURA A (CONFIRMADO)

**Como contar o gatilho de ">5 protocolos no dia" que abre o Fluxo do dia?**

- **Leitura A (CONFIRMADA):** soma todos os protocolos de **todas as empresas do
  mesmo `grupo_id`** no mesmo dia. Ex: Neoenergia S.A. protocola 3 e Neoenergia Vale do
  Itajaí protocola 3 no mesmo dia = 6, dispara — mesmo sendo CNPJs diferentes, mesmo grupo.
- ~~Leitura B (alternativa, descartada):~~ contar por empresa individual (CNPJ), não por
  grupo.

O código já está escrito e confirmado para a **Leitura A** — `vincular_fluxo_do_dia` agrupa
por `grupo_id` (main.py). Nenhuma mudança pendente aqui.

---

## 1. RESUMO DO QUE MUDA

- Dashboard novo pro **admin** (`App.js`) e pro **cliente** (`Cliente.js`), mesma estrutura
  visual, dados diferentes (admin vê tudo/todos os grupos, cliente só o dele).
- Cards de métrica no topo (Total, Tramitação, Exigência, Finalizados) — dado que já existe
  hoje, só muda a apresentação (cards coloridos, não números soltos).
- Card **"Fluxo do dia"**: aparece só quando um grupo bate mais de 5 protocolos no mesmo
  dia. Mostra progresso (X de Y confirmados pela Junta) com polling ao vivo. **Some
  sozinho quando todos os processos daquele fluxo viram `finalizado`.**
- Card "Status dos processos" (donut SVG) — visual novo, dado já existe (contagem por status).
- Card "Atividade recente" — **é o único pedaço 100% novo**, não existe nada parecido hoje.
  Precisa de tabela nova e de instrumentar os pontos do código que já mudam status/arquivo.
- Listagem de processos passa de lista vertical plana pra **agrupada por empresa,
  colapsável**.

---

## 2. BACKEND — `database.py`

Duas tabelas novas.

```python
class Fluxo(Base):
    __tablename__ = "fluxos"
    id = Column(String, primary_key=True)  # uuid
    grupo_id = Column(String, ForeignKey("grupos.id"), nullable=False)
    data = Column(Date, nullable=False)  # data de abertura do fluxo
    total_processos = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.utcnow)

class Evento(Base):
    __tablename__ = "eventos"
    id = Column(String, primary_key=True)  # uuid
    processo_id = Column(String, ForeignKey("processos.id"), nullable=False)
    grupo_id = Column(String, nullable=True)  # denormalizado, facilita query do feed
    tipo = Column(String, nullable=False)  # ver taxonomia real (8 tipos) na secao STATUS ATUAL
    descricao = Column(String, nullable=False)  # texto pronto pra exibir, ex: "Protocolo confirmado"
    criado_em = Column(DateTime, default=datetime.utcnow)
```

Adicionar coluna em `Processo`:
```python
fluxo_id = Column(String, ForeignKey("fluxos.id"), nullable=True)
```

*(Nota da sessão atual: `database.py` real usa `datetime.now` em vez de `datetime.utcnow`,
por consistência com o resto do arquivo — divergência intencional do trecho acima.)*

---

## 3. BACKEND — `main.py`

### 3.1 Função compartilhada para abrir/vincular fluxo

Chamar no mesmo lugar onde hoje `criar_processo` grava `grupo_id` (inserção em massa via
pasta/bot/upload). Segue o padrão que vocês já usaram em `notificar_tramitacao_cliente`
(tópico 1.12 do log de problemas): uma função só, chamada de todos os caminhos de entrada.

```python
def vincular_fluxo_do_dia(db, processo, grupo_id):
    hoje = date.today()
    fluxo = db.query(Fluxo).filter(
        Fluxo.grupo_id == grupo_id, Fluxo.data == hoje
    ).first()
    total_hoje = db.query(Processo).filter(
        Processo.grupo_id == grupo_id,
        func.date(Processo.criado_em) == hoje
    ).count()

    if not fluxo and total_hoje > 5:
        fluxo = Fluxo(id=str(uuid.uuid4()), grupo_id=grupo_id, data=hoje, total_processos=total_hoje)
        db.add(fluxo)
        db.flush()

    if fluxo:
        processo.fluxo_id = fluxo.id
        fluxo.total_processos = total_hoje
```

*(Nota da sessão atual: a versão real em `main.py` roda esse corpo dentro de
`with db.begin_nested():` + `try/except`, pra nunca quebrar o fluxo principal de criação de
processo mesmo se essa parte falhar — reforço de robustez além do spec original.)*

Chamar essa função logo depois de setar `processo.grupo_id`, em **todos** os pontos que
criam processo (igual fizeram pro email de Tramitação — não deixar nenhum caminho de fora).

### 3.2 Função compartilhada para registrar evento

```python
def registrar_evento(db, processo, tipo, descricao):
    try:
        evento = Evento(
            id=str(uuid.uuid4()), processo_id=processo.id,
            grupo_id=processo.grupo_id, tipo=tipo, descricao=descricao
        )
        db.add(evento)
    except Exception:
        pass  # nunca deve quebrar o fluxo principal, igual notificar_tramitacao_cliente
```

**Importante: chamar sempre ANTES do `db.commit()` da operação principal** — essa função não
commita sozinha, então se for chamada depois de um commit que já rodou, o evento fica
pendente na sessão e se perde quando a sessão fecha sem commitar de novo. Todos os pontos
abaixo já seguem essa ordem.

Chamado em (7 pontos, todos em ordem evento→commit):
- `criar_processo` → `'ata_enviada'`
- `_criar_processo_transferencia` → `'processo_criado_transferencia'`
- `PATCH /processos/{id}` quando protocolo é editado manualmente → `'protocolo_inserido'`
- `upload_arquivo` — `'protocolo_inserido'` / `'registro_finalizado'` / `'nd_inserida'` /
  `'nf_inserida'`, conforme o tipo
- `registrar_exigencia` → `'exigencia_registrada'`
- `exigencia_cumprida` → `'exigencia_cumprida'`
- `bot.py` (`processar_confirmacao_anexo`, protocolo vinculado via Telegram) →
  `'protocolo_inserido'`

### 3.3 Endpoints novos — AINDA NÃO IMPLEMENTADOS

**IMPLEMENTADO (main.py, logo após `obter_processo`) — código real, já com a correção do
vazamento entre grupos:**

```python
@app.get("/fluxo/ativo")
def fluxo_ativo(codigo_grupo: str = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    grupo_id_filtro = None
    if usuario.is_admin:
        if codigo_grupo:
            grupo = db.query(Grupo).filter(Grupo.codigo == codigo_grupo).first()
            if not grupo:
                return None  # codigo_grupo invalido -> nao ha fluxo pra retornar, nao cai na busca sem filtro
            grupo_id_filtro = grupo.id
    else:
        grupo_id_filtro = usuario.grupo_id

    hoje = date.today()
    query = db.query(Fluxo).filter(Fluxo.data == hoje)
    if grupo_id_filtro:
        query = query.filter(Fluxo.grupo_id == grupo_id_filtro)
    fluxos = query.all()

    resultado = []
    for f in fluxos:
        processos = db.query(Processo).filter(Processo.fluxo_id == f.id).all()
        pendentes = [p for p in processos if p.status != "finalizado"]
        if not pendentes:
            continue  # todos finalizaram -> nao retorna, card some
        confirmados = len([p for p in processos if p.status in ("deferido", "finalizado")])
        resultado.append({
            "grupo_id": f.grupo_id,
            "data": f.data.isoformat(),
            "total": len(processos),
            "confirmados": confirmados,
            "em_tramitacao": len([p for p in processos if p.status == "tramitacao"]),
        })

    if usuario.is_admin and not codigo_grupo:
        return resultado
    return resultado[0] if resultado else None


@app.get("/eventos/recentes")
def eventos_recentes(codigo_grupo: str = None, limit: int = 10, x_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Token necessario")
    usuario = validar_token(x_token, db)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou sessao expirada")
    query = db.query(Evento).order_by(Evento.criado_em.desc())
    if usuario.is_admin:
        if codigo_grupo:
            grupo = db.query(Grupo).filter(Grupo.codigo == codigo_grupo).first()
            if grupo:
                query = query.filter(Evento.grupo_id == grupo.id)
    else:
        query = query.filter(Evento.grupo_id == usuario.grupo_id)
    eventos = query.limit(limit).all()
    return [{"tipo": e.tipo, "descricao": e.descricao, "processo_id": e.processo_id,
             "criado_em": e.criado_em.isoformat()} for e in eventos]
```

Diferenças da versão implementada em relação ao rascunho original acima desta seção:
`codigo_grupo` (não `grupo_id` cru) como query param, resolvido via `Grupo.codigo`, mesmo
padrão de autorização de `listar_processos` (admin filtra por `codigo_grupo` opcional,
cliente sempre restrito ao próprio `usuario.grupo_id`). `/fluxo/ativo` tem o `return None`
extra explicado na seção STATUS ATUAL (correção do vazamento entre grupos) — `/eventos/recentes`
não precisou dessa correção porque sempre retorna lista, nunca colapsa pra objeto único.

---

## 4. FRONTEND — estrutura comum (App.js admin + Cliente.js cliente)

**Admin (`App.js`): CONCLUÍDO. Cliente (`Cliente.js`): CONCLUÍDO.** Só falta o deploy
(build + scp), ver seção 5.

Paleta já em uso (não inventar cor nova):
- Roxo principal `#4f46b7`, gradiente sidebar `#241b4a → #4f46b7`
- Cards de métrica: fundo tonal claro por categoria — roxo `#EEEDFE`/texto `#3C3489`
  (total), verde-água `#E1F5EE`/`#085041` (tramitação), âmbar `#FAEEDA`/`#633806`
  (exigência), verde `#EAF3DE`/`#27500A` (finalizados)
- Card Fluxo do dia: fundo `#FAFAFF`, borda `#AFA9EC`, barra de progresso `#534AB7`

### Componentes (status real após implementação no App.js)
1. `StatCard` — **feito**. Props exatas: `valor, label, corFundo, corTexto, icone, onClick`
   (`onClick` foi adicionado, não estava no rascunho original — cards continuam clicáveis pra
   filtrar por status, como já eram antes da migração pro componente). 5 usos no topo (Total,
   Tramitação, Exigência, **Deferidos** — cor azul `#d5e3df`/`#2563eb` reaproveitada do
   `STATUS_CONFIG` existente, não inventada — e Finalizados).
2. `FluxoDoDiaCard` — **feito**, exatamente como no rascunho: busca `/fluxo/ativo` no mount +
   polling 5s, não renderiza nada se vazio/null.
3. `StatusDonut` — **feito**. Cores dos segmentos reaproveitam `STATUS_CONFIG` (mesmas cores
   já usadas nos badges de status em todo o app), não a paleta do `StatCard` — decisão pra
   manter uma linguagem visual só pra "status" em toda a tela. SVG puro via
   `stroke-dasharray`/`stroke-dashoffset` empilhado (técnica padrão de donut sem lib), total
   no centro, legenda lateral com contagem por status.
4. `AtividadeRecente` — **feito**, busca `/eventos/recentes?limit=5`, polling 5s (não estava
   explícito no rascunho, mas seguido por consistência com `FluxoDoDiaCard`/`StatusDonut`).
5. `ListaProcessosAgrupada` — **feito, mas com uma mudança de escopo pedida pelo Diogo durante
   a implementação**: agrupa por **data do ato** (`p.data_ata`, formato `DD/MM/AAAA` no banco
   — convertido pra `AAAA-MM-DD` internamente só pra ordenar/comparar certo, já que a string
   crua brasileira ordena errado), **não por `empresa`** como este doc sugeria originalmente.
   Ordenado do mais recente pro mais antigo, grupo `"Sem data"` sempre por último. Cabeçalho
   de cada grupo é clicável (expandir/colapsar), com ícone `▾`/`▸` — isso também mudou de ideia
   no meio do caminho: a primeira versão implementada tirava o clique por completo (cabeçalho
   fixo, sem interação), depois o Diogo pediu de volta o expandir/colapsar, só que vinculado à
   **chave de data**, não mais ao nome da empresa. Continua sem chamada nova de API
   (`Array.prototype.reduce` sobre `processosFiltrados`, já carregado). Componente aninhado
   **dentro do `AppPainel`** (não top-level como os outros 4), porque referencia `s` (objeto
   de estilos) e `processosFiltrados`/`setProcessoSelecionado` da closure — mesmo padrão já
   usado por `BannerPendencias`/`ChatProcesso` no arquivo.

### Diferença admin x cliente
- Admin: `FluxoDoDiaCard` pode renderizar **mais de um** (map sobre a lista de
  `/fluxo/ativo` sem `codigo_grupo`) — um por grupo que bateu o gatilho hoje. **Implementado
  assim**: sempre busca a lista global, sem respeitar o filtro `fGrupo` da tabela de baixo (que
  já era só um filtro client-side, nunca mandava pro backend — `/metricas` também já era
  global, então manter `FluxoDoDiaCard`/`StatusDonut`/`AtividadeRecente` globais ficou
  consistente com o que já existia).
- Cliente: chama `/fluxo/ativo` sem parâmetro (backend resolve pelo token) — no máximo um
  card. Sem seletor de grupo. **Ainda não implementado.**

---

## 5. ORDEM DE IMPLEMENTAÇÃO SUGERIDA

1. ~~Migração de banco (tabelas `fluxos`, `eventos`, coluna `fluxo_id`)~~ — **feita e
   deployada em produção** (`aplica_migracao_fluxo.py`, rodada local e no servidor).
2. ~~`vincular_fluxo_do_dia` + `registrar_evento`, plugadas nos pontos de entrada~~ —
   **feita e deployada em produção**, todos os 7 pontos conferidos e testados ponta a
   ponta com processo real (criado e apagado em seguida).
3. ~~Endpoints `/fluxo/ativo` e `/eventos/recentes`~~ — **feita, testada (local e
   produção) e deployada**. Bug de vazamento entre grupos encontrado e corrigido nesse
   processo (ver STATUS ATUAL).
4. ~~Componentes de frontend no admin (`App.js`) e no cliente (`Cliente.js`)~~ — **feito nos
   dois**, 5 componentes cada, ver seção 4.
5. ~~Deploy do frontend (build + scp)~~ — **feito**, admin e cliente juntos, num deploy só.
   Smoke test via curl/HTTPS OK. **Falta só o Diogo confirmar visualmente em aba anônima.**

**FLUXO DO DIA: TODAS AS ETAPAS CONCLUÍDAS E EM PRODUÇÃO.**

## 6. RISCO CONHECIDO (já sinalizado ao Diogo)

A peça de eventos exige tocar em vários pontos do código pra não deixar nenhum caminho de
inserção sem o `registrar_evento` — é o mesmo tipo de lacuna que causou o bug do tópico
1.12 do log de problemas (email de Tramitação que não disparava por certos caminhos).
Testar explicitamente os três caminhos de entrada de protocolo (manual, upload admin, bot
Telegram) depois de implementar.

*(Nota da sessão atual: risco levado a sério — a primeira versão de `registrar_evento`
tinha `db.commit()` próprio e as chamadas foram coladas depois do commit principal, o que
por pouco reintroduzia esse exato tipo de bug — evento nunca persistido em nenhum dos 7
pontos. Corrigido: `registrar_evento` sem commit próprio, chamada sempre antes do commit
principal, conferido ponto a ponto via `grep -n`.)*
