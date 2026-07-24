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

### AINDA PENDENTE (não mexido nesta sessão)
1. Endpoints `/fluxo/ativo` e `/eventos/recentes` (seção 3.3) — **não implementados ainda**.
2. Frontend inteiro (seção 4) — **não implementado ainda**. Nenhuma mudança de UI foi feita
   nesta sessão, só backend (`database.py`, `main.py`, `bot.py`).
3. Migração (`aplica_migracao_fluxo.py`) já existe e já foi rodada localmente (script
   avulso, não vai pro git — confirmar se já rodou no servidor também antes do deploy).
4. Testar com processo de mentira e conferir no banco se `vincular_fluxo_do_dia` e
   `registrar_evento` gravaram certo (instrumentação está pronta, mas não foi testada
   ponta a ponta ainda nesta sessão).

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

```python
@app.get("/fluxo/ativo")
def fluxo_ativo(grupo_id: str = None, x_token: str = Header(None), db: Session = Depends(get_db)):
    # se vier x_token (cliente): resolver grupo_id do usuário, ignorar param
    # se não vier (admin) e grupo_id vier: usa o param
    # se não vier nada (admin sem filtro): retorna lista de TODOS os fluxos ativos hoje
    hoje = date.today()
    query = db.query(Fluxo).filter(Fluxo.data == hoje)
    if grupo_id:
        query = query.filter(Fluxo.grupo_id == grupo_id)
    fluxos = query.all()

    resultado = []
    for f in fluxos:
        processos = db.query(Processo).filter(Processo.fluxo_id == f.id).all()
        pendentes = [p for p in processos if p.status != "finalizado"]
        if not pendentes:
            continue  # todos finalizaram -> não retorna, card some
        confirmados = len([p for p in processos if p.status in ("deferido", "finalizado")])
        resultado.append({
            "grupo_id": f.grupo_id,
            "data": f.data.isoformat(),
            "total": len(processos),
            "confirmados": confirmados,
            "em_tramitacao": len([p for p in processos if p.status == "tramitacao"]),
        })
    return resultado if not grupo_id else (resultado[0] if resultado else None)


@app.get("/eventos/recentes")
def eventos_recentes(grupo_id: str = None, x_token: str = Header(None), db: Session = Depends(get_db), limit: int = 10):
    query = db.query(Evento).order_by(Evento.criado_em.desc())
    if grupo_id:
        query = query.filter(Evento.grupo_id == grupo_id)
    eventos = query.limit(limit).all()
    return [{"tipo": e.tipo, "descricao": e.descricao, "processo_id": e.processo_id,
             "criado_em": e.criado_em.isoformat()} for e in eventos]
```

Ajustar filtro de `x_token` igual já é feito em `listar_processos` (peça 5A do histórico) —
reusar a mesma lógica de resolver `grupo_id` a partir do token do cliente.

---

## 4. FRONTEND — estrutura comum (App.js admin + Cliente.js cliente) — AINDA NÃO IMPLEMENTADO

Paleta já em uso (não inventar cor nova):
- Roxo principal `#4f46b7`, gradiente sidebar `#241b4a → #4f46b7`
- Cards de métrica: fundo tonal claro por categoria — roxo `#EEEDFE`/texto `#3C3489`
  (total), verde-água `#E1F5EE`/`#085041` (tramitação), âmbar `#FAEEDA`/`#633806`
  (exigência), verde `#EAF3DE`/`#27500A` (finalizados)
- Card Fluxo do dia: fundo `#FAFAFF`, borda `#AFA9EC`, barra de progresso `#534AB7`

### Componentes a criar
1. `StatCard` — 4 usos no topo, props: `valor, label, corFundo, corTexto, icone`
2. `FluxoDoDiaCard` — busca `/fluxo/ativo` no mount + polling 5s (mesmo padrão do chat do
   processo); se resposta vazia/null, **não renderiza nada** (sem placeholder, sem "sem
   fluxo hoje" — some por completo)
3. `StatusDonut` — SVG puro, sem lib nova (ver exemplo já validado no mockup)
4. `AtividadeRecente` — busca `/eventos/recentes`, lista os 3-5 mais novos
5. `ListaProcessosAgrupada` — substitui a lista vertical atual; agrupa por `empresa` no
   próprio frontend (`Array.prototype.reduce`), cabeçalho de grupo clicável
   (expandir/colapsar), sem chamada nova de API

### Diferença admin x cliente
- Admin: `FluxoDoDiaCard` pode renderizar **mais de um** (map sobre a lista de
  `/fluxo/ativo` sem `grupo_id`) — um por grupo que bateu o gatilho hoje. Tem seletor de
  Grupo Empresarial no topo (já existe hoje, manter).
- Cliente: chama `/fluxo/ativo` sem parâmetro (backend resolve pelo token) — no máximo um
  card. Sem seletor de grupo.

---

## 5. ORDEM DE IMPLEMENTAÇÃO SUGERIDA

1. ~~Migração de banco (tabelas `fluxos`, `eventos`, coluna `fluxo_id`)~~ — **feita**
   (`aplica_migracao_fluxo.py`, rodada localmente).
2. ~~`vincular_fluxo_do_dia` + `registrar_evento`, plugadas nos pontos de entrada~~ —
   **feita nesta sessão**, todos os 7 pontos conferidos. Falta testar com processo de
   mentira e conferir no banco se gravou certo (não feito ainda nesta sessão).
3. Endpoints `/fluxo/ativo` e `/eventos/recentes` — **próximo passo**. Testar via curl
   antes de mexer no frontend.
4. Componentes de frontend, um de cada vez, primeiro no admin (`App.js`, já mais perto do
   visual novo), depois espelhar no `Cliente.js`
5. Deploy e teste em aba anônima, do jeito que vocês já fazem

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
