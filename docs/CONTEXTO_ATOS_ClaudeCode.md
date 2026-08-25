# CONTEXTO ATOS — para o Claude Code

Este documento te coloca a par do sistema ATOS e da tarefa atual. Leia com atenção antes de agir.

---

## 1. O QUE É O ATOS

Plataforma de **gestão societária** — acompanha processos de registro em Juntas Comerciais (constituição, alteração, atas, etc.). O cliente envia a ata/documento, o sistema lê via IA, cria o processo e acompanha o status no portal da Junta.

Papel LGPD: o ATOS é **operador** de dados (trata em nome dos clientes, que são os controladores).

---

## 2. INFRAESTRUTURA

- **Servidor:** VPS Hostinger, Ubuntu 24.04, IP **187.77.60.91**, em Campinas/SP. Acesso `ssh root@187.77.60.91`.
- **Backend:** FastAPI (Python), em `/root/atos/backend/main.py` + `database.py`. Roda como serviço systemd `atos-backend` (`systemctl restart atos-backend`). Python do venv: `/root/atos/venv/bin/python`. Porta 8000, só via nginx.
- **Frontend:** React, servido por nginx em `/var/www/atos/`. Fonte no PC: `D:\Mane\frontend\src\App.js` (admin) e `Cliente.js` (cliente).
- **Banco:** SQLite em `/root/atos/backend/mane.db`. Documentos em `/root/atos/backend/uploads/`.
- **Git:** repo `github.com/diogolyra87/Atos.git`. Fluxo: commits saem do **PC** (`D:\Mane\`); o **servidor** só faz `git pull`. Servidor NÃO faz push.
- **Serviços systemd ativos:** `atos-backend` (API), `atos-bot` (bot Telegram, polling), `atos-sla.timer` (monitor SLA a cada 30min), `atos-consulta.timer` (consulta automática de status SP/RJ, 7x/dia — ver nota de timeout na seção 3), `atos-backup.timer` (backup cifrado do banco, **de hora em hora**), `atos-check.timer` (verificação de integridade do banco, **de hora em hora** — auto-restaura do backup mais recente se detectar corrupção; ver incidente abaixo).

### Regras de trabalho importantes
- **Segredos NUNCA no chat.** Ficam só em `/root/atos/.env` (chmod 600). Se precisar de uma senha/chave nova, gerar/colar direto no `.env` do servidor, sem exibir. Se vazar, rotacionar imediatamente.
- Edições de backend no servidor via heredoc Python, validando `count()==1` antes de gravar, removendo BOM.
- Deploy do frontend: `npm run build` no PC → `scp` do JS + index.html pro servidor → remover JS antigo.
- Alinhar servidor após push: `cd /root/atos && git stash && git pull && git stash drop && systemctl restart atos-backend`. (Se houver arquivo novo "untracked" que conflita, `rm` o arquivo no servidor antes do pull — a versão do Git é idêntica.)
- Testar import com o venv e `.env` carregado: `cd /root/atos/backend && /root/atos/venv/bin/python -c "from dotenv import load_dotenv; load_dotenv('/root/atos/.env'); import main; print('import ok')"`.

### ⚠️ Incidente: teste do check_db.sh reiniciou atos-backend em produção sem querer (11/08/2026)

Durante o levantamento pré-rename do `mane.db` (parte de um rename Mane→Iatos que **não** mexe nesse arquivo ainda — só planejamento), rodei um teste-baseline do `check_db.sh` (script de auto-restore de corrupção) contra uma cópia isolada (`/root/atos/TESTE-corrupcao.db`, nunca o banco real). O teste funcionou tecnicamente (detectou a corrupção proposital, achou o backup certo, restaurou o arquivo de teste em ~3s), mas teve um efeito colateral não previsto: **`check_db.sh` chamava `systemctl restart atos-backend` de forma incondicional**, disparando mesmo quando o banco verificado era o arquivo de teste, não o `mane.db` real. Resultado: o `atos-backend` de produção reiniciou de verdade às 14:10:01, sem essa ação ter sido autorizada especificamente.

**Verificação de impacto (evidência, não suposição):**
- `mane.db` real nunca foi sobrescrito — prova: o registro mais recente em `audit_logs` no momento do teste (14:04:21) é **posterior** ao backup usado na restauração (14:00) e continuou presente depois; se o banco real tivesse sido restaurado, esse registro teria sumido.
- O arquivo "corrompido preservado" (`CORROMPIDO-20260811-141000.db`) foi inspecionado byte a byte: estrutura normal de SQLite até o offset 5120, ruído aleatório puro exatamente até o offset 9216, estrutura normal depois — bate exatamente com os parâmetros do comando `dd` usado no teste (não é corrupção real/independente).
- Nenhum request de cliente foi afetado: log do nginx mostra o último request antes do restart às 14:09:40 e o próximo às 14:10:13 (janela de 20s sem tráfego); log do `atos-backend` mostra shutdown gracioso (`Waiting for application shutdown` → `Application shutdown complete`), não um kill forçado.

**Causa raiz:** o restart não era condicionado a qual banco (`$DB`) estava sendo checado.

**Correção aplicada:** adicionada variável `DB_PRODUCAO="/root/atos/backend/mane.db"` e os dois `systemctl restart atos-backend` agora só disparam `if [ "$DB" = "$DB_PRODUCAO" ]`. Já implantado em `/root/atos/check_db.sh` (backup do original preservado em `check_db.sh.bak.20260811_142404`) e commitado no repo (`scripts/check_db.sh`, antes disso o arquivo nunca tinha sido versionado — ver seção sobre `mane.db` abaixo). Re-testado depois da correção: rodada completa de corrupção+restauração no arquivo de teste, `atos-backend` confirmado **sem restart** (`ActiveEnterTimestamp` inalterado antes/depois do teste).

**Lição para o rename do `mane.db` (Categoria C, ainda não autorizado):** qualquer script que aja sobre "o banco verificado" só pode disparar efeitos em produção (restart de serviço, etc.) quando o caminho verificado é literalmente o caminho de produção — nunca assumir isso implicitamente por só existir um único uso hoje.

---

## 3. AUTOMAÇÃO DE JUNTAS (JÁ EXISTENTE — é o modelo a replicar)

Arquivo: **`/root/atos/backend/atualizar_status.py`** (existe também uma cópia em `/root/atos/automacao/atualizar_status.py`; unificar é pendência antiga).

- Usa **Playwright** (navegador headless) para logar no portal da Junta, consultar o processo por **número de protocolo**, ler o resultado e classificar o status.
- Hoje automatiza **SP (JUCESP)** e **RJ (JUCERJA)**.
- Classificação de status: **Deferido / Exigência / Tramitação** (e Finalizado).
- Roda via systemd timer (7x/dia).
- As credenciais das Juntas ficam no `.env`.

**Estude o fluxo RJ (JUCERJA) neste arquivo — ele é o modelo mais próximo do que vamos fazer, pois também é login + consulta por protocolo.**

### ⚠️ Ajuste de TimeoutStartSec (11/08/2026) — remendo, não solução definitiva

O serviço `atos-consulta.service` (unit em `/etc/systemd/system/atos-consulta.service`, dispara via `atos-consulta.timer`) passou a falhar **toda execução** com `Result: timeout` a partir de ~10/08/2026. Diagnóstico via `journalctl -u atos-consulta.service`: não era hCaptcha, credencial expirada, API (Gemini) ou disco/memória — era volume de trabalho puro. O script consulta cada processo (SP + RJ) sequencialmente via Playwright, ~19-30s por processo; com a base de clientes atual isso soma ~64 processos por execução (~20-25min necessários), acima do `TimeoutStartSec=900` (15min) original — o systemd matava o processo (SIGTERM) antes de terminar, toda vez.

Antes de aumentar o timeout, confirmamos (via `man systemd.timer` no próprio servidor, não suposição) que não há risco de sobreposição: *"in case the unit to activate is already active at the time the timer elapses it is not restarted, but simply left running"* — o systemd nunca inicia uma segunda instância do mesmo service enquanto a anterior ainda roda.

Aumentado para `TimeoutStartSec=2400` (40min) em 11/08/2026, direto no servidor (esse unit file não é versionado no Git — não faz parte do repo do app).

**Isso é um remendo, não a solução definitiva.** Se o volume de processos continuar crescendo com a base de clientes, esse timeout pode precisar subir de novo. A solução definitiva seria paralelizar as consultas (ou de outra forma parar de depender de rodar tudo sequencial numa janela crescente). Se `atos-consulta.service` voltar a falhar com `Result: timeout`, é esse mesmo problema — revisar o volume atual antes de simplesmente aumentar o número de novo.

---

## 4. TAREFA ATUAL: adicionar consulta para BAHIA e PERNAMBUCO

Objetivo: replicar o padrão de automação existente para **duas Juntas novas**, começando pela **BAHIA (JUCEB)**.

### JUCEB — Bahia (fazer primeiro)
- Portal: **https://regin.juceb.ba.gov.br/RequerimentoUniversal/Principal.aspx**
- Acesso: **login e senha** (SEM captcha).
- Consulta: por **número de protocolo**.
- As credenciais (usuário/senha) serão adicionadas ao `.env` pelo Diogo, direto no servidor — NÃO peça a senha no chat. Use nomes de variável tipo `JUCEB_USER` / `JUCEB_PASS` lendo com `os.getenv()`.

### Pernambuco (fazer depois da Bahia)
- Detalhes do portal ainda a levantar com o Diogo.

### Como abordar
1. Leia `atualizar_status.py` inteiro e entenda o fluxo RJ (login → consulta por protocolo → leitura → classificação de status).
2. Escreva o fluxo da JUCEB replicando esse padrão e o estilo do código.
3. Automação de portal é tentativa-e-erro: abra o portal, identifique os seletores reais dos campos (login, senha, botão entrar, campo de protocolo, onde aparece o resultado), teste ao vivo e ajuste.
4. Classifique o status no mesmo padrão (Deferido/Exigência/Tramitação).
5. Integre ao mesmo mecanismo de execução das outras Juntas.
6. Ao terminar e testar, os arquivos alterados precisam ser **commitados a partir do PC** (o Diogo faz isso) — avise quais arquivos mudaram.

---

## 5. ESTILO DO DIOGO (o dono/programador)
- Quer que você **decida as questões técnicas e execute**, sem perguntar escopo a cada passo.
- Comunicação concisa, em português.
- Pragmático, orientado a ação.
- Sempre sinalize onde cada comando roda (servidor vs PC), pois ele alterna entre os dois.
- Tudo deve ser versionado no Git para não perder.

---

## 6. O QUE FOI CONSTRUÍDO RECENTEMENTE (contexto, não precisa mexer)
Anexos (UI + backend), detecção automática de documento principal vs anexo (regras DREI), avisos "Documento Sem Valor Societário" e "Possível Duplicidade de Atos", banner de pendências, aprendizado por regras acumuladas, chat por processo (isolado por grupo, permanente, com polling 5s), notificação Telegram ao ADM quando cliente escreve, bot Telegram (comandos `/consulta` + responder cliente por reply), e monitor de SLA (protocolo 6h / exigência 12h / deferido 24h, alertas por e-mail + Telegram). Tudo já versionado. NÃO precisa mexer nisso — a tarefa é só a automação das Juntas novas.

---

## 7. CHECKLIST DE DEPLOY (rodar SEMPRE, nesta ordem, antes de considerar um deploy concluído)

Criado depois do incidente de 13/08/2026 (ver histórico de incidentes / memória) — um deploy que
alterou `database.py` derrubou login e listagem de processos em produção por ~5min, porque duas
migrações pendentes (não relacionadas à mudança do dia) foram commitadas sem rodar, e o "health
check" pós-restart só testou o endpoint raiz, que não prova que uma rota autenticada funciona.

### Antes de commitar

1. **Nunca `git add <arquivo>` cego quando a intenção é "só a feature X".** Rodar `git diff <arquivo>`
   antes e conferir se não tem OUTRA mudança pendente não relacionada misturada no mesmo arquivo
   (comum quando há trabalho de uma feature anterior ainda não commitado). Se tiver, isolar por
   conteúdo (edição cirúrgica ou `git add -p`), não por arquivo inteiro.
2. **Se a mudança tocou `backend/database.py`** (nova coluna, nova tabela, novo campo em model
   existente): checar se existe um `aplica_migracao_*.py` correspondente em `backend/` (convenção do
   projeto — gitignorado, `aplica_*.py`). Se não existir, criar um, seguindo o padrão dos scripts já
   existentes (idempotente: checa `PRAGMA table_info` antes de `ALTER TABLE`; usa
   `Base.metadata.create_all()` pra tabela nova).

### Antes do restart (depois do `git pull` no servidor)

3. **Listar TODOS os `aplica_migracao_*.py` em `backend/` no servidor e confirmar quais já rodaram
   e quais não** — não assumir que só a migração da mudança do dia importa. Uma mudança de meses
   atrás pode ter ficado pendente de propósito (sem urgência) e ainda quebrar quando outro deploy
   mexe no mesmo arquivo. Rodar todas as pendentes, uma de cada vez, conferindo a saída.
4. **Não confiar só na saída impressa do script de migração.** Depois de rodar, checar
   `PRAGMA table_info(<tabela>)` direto no `sqlite3` pra confirmar a coluna/tabela existe de fato —
   já aconteceu do script imprimir "OK, criada" sem ter criado nada (dependia de uma classe do
   modelo que o `database.py` importado aindas não tinha).
5. **Auditoria programática final, tabela por tabela**, comparando o `Base.metadata` inteiro do
   SQLAlchemy contra o schema real do banco (evita erro de comparar colunas a olho):
   ```python
   # rodar no servidor, dentro de backend/, com o venv ativo
   import sqlite3
   from database import Base
   con = sqlite3.connect('mane.db')
   cur = con.cursor()
   for table in Base.metadata.sorted_tables:
       cols_modelo = set(c.name for c in table.columns)
       cur.execute(f"PRAGMA table_info({table.name})")
       cols_banco = set(row[1] for row in cur.fetchall())
       faltando = cols_modelo - cols_banco
       if faltando:
           print(f'FALTANDO em {table.name}: {sorted(faltando)}')
   ```
   Só seguir pro restart se não imprimir nada.

### Depois do restart

6. **`smoke_check.py` (hook `post-merge`) só pega import quebrado, NÃO pega schema desatualizado**
   (o import funciona normalmente; só a query real em runtime quebra). Não é suficiente sozinho.
7. **Testar com uma requisição autenticada de verdade**, não só `curl` no endpoint raiz (`GET /`,
   que não toca nenhuma tabela de negócio e sempre vai retornar 200 mesmo com o resto quebrado).
   Reaproveitar um token de sessão já existente no banco (não precisa senha de ninguém):
   ```bash
   # pegar um token real
   sqlite3 /root/atos/backend/mane.db "SELECT token FROM usuarios WHERE token IS NOT NULL LIMIT 1;"
   # testar pelo menos um endpoint que toque as tabelas alteradas no deploy
   curl -s -o /dev/null -w '%{http_code}\n' -H 'x-token: <token>' http://localhost:8000/processos
   ```
8. **Checar `journalctl -u atos-backend --since <hora do restart>`** por qualquer traceback, não só
   "Application startup complete" (isso só prova que o processo iniciou, não que uma rota funciona).

### Se algo quebrar de verdade (incidente real)

9. **Medir o impacto real no `nginx access.log`** (`/var/log/nginx/access.log`), filtrando por IPs
   de cliente (não `127.0.0.1`) na janela do erro, em vez de estimar a duração ou assumir que
   "ninguém deve ter notado". Documentar no histórico de incidentes com hora exata de início/fim
   e se algum request de cliente real bateu em erro.
