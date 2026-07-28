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
- **Serviços systemd ativos:** `atos-backend` (API), `atos-bot` (bot Telegram, polling), `atos-sla.timer` (monitor SLA a cada 30min).

### Regras de trabalho importantes
- **Segredos NUNCA no chat.** Ficam só em `/root/atos/.env` (chmod 600). Se precisar de uma senha/chave nova, gerar/colar direto no `.env` do servidor, sem exibir. Se vazar, rotacionar imediatamente.
- Edições de backend no servidor via heredoc Python, validando `count()==1` antes de gravar, removendo BOM.
- Deploy do frontend: `npm run build` no PC → `scp` do JS + index.html pro servidor → remover JS antigo.
- Alinhar servidor após push: `cd /root/atos && git stash && git pull && git stash drop && systemctl restart atos-backend`. (Se houver arquivo novo "untracked" que conflita, `rm` o arquivo no servidor antes do pull — a versão do Git é idêntica.)
- Testar import com o venv e `.env` carregado: `cd /root/atos/backend && /root/atos/venv/bin/python -c "from dotenv import load_dotenv; load_dotenv('/root/atos/.env'); import main; print('import ok')"`.

---

## 3. AUTOMAÇÃO DE JUNTAS (JÁ EXISTENTE — é o modelo a replicar)

Arquivo: **`/root/atos/backend/atualizar_status.py`** (existe também uma cópia em `/root/atos/automacao/atualizar_status.py`; unificar é pendência antiga).

- Usa **Playwright** (navegador headless) para logar no portal da Junta, consultar o processo por **número de protocolo**, ler o resultado e classificar o status.
- Hoje automatiza **SP (JUCESP)** e **RJ (JUCERJA)**.
- Classificação de status: **Deferido / Exigência / Tramitação** (e Finalizado).
- Roda via systemd timer (7x/dia).
- As credenciais das Juntas ficam no `.env`.

**Estude o fluxo RJ (JUCERJA) neste arquivo — ele é o modelo mais próximo do que vamos fazer, pois também é login + consulta por protocolo.**

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
