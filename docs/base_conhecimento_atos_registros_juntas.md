# Base de Conhecimento ATOS — Registros em Juntas Comerciais Brasileiras

**Documento vivo — atualizar conforme mudanças normativas.**
**Última consolidação: 01/08/2026.**
**Composto por 3 pesquisas documentais independentes, unificadas aqui em um único arquivo de referência.**

---

## Índice

1. [Como usar este documento](#como-usar)
2. [Parte I — Atos Societários de LTDA e Consórcio](#parte-1)
3. [Parte II — Sociedade Anônima, Debêntures, RDIC e Procurações](#parte-2)
4. [Parte III — Varredura de Viabilidade de Automação (Playwright) por Estado](#parte-3)
5. [Parte IV — Taxas/Emolumentos e Requisitos de Assinatura](#parte-4)
6. [Glossário unificado de códigos de Ato/Evento REDESIM](#glossario)
7. [Sistema de atualização autônoma](#atualizacao-autonoma)
8. [Registro de mudanças / changelog](#changelog)
9. [Fontes primárias consolidadas](#fontes)

---

<a name="como-usar"></a>
## 1. Como usar este documento

Este arquivo consolida três pesquisas documentais realizadas para estruturar a base de conhecimento que vai orientar a IA da plataforma ATOS a identificar automaticamente, ao inserir um ato societário no sistema, **o que precisa ser feito, em que ordem, com que fundamento legal**, e alertar o usuário sobre pontos críticos (prazos, publicações obrigatórias, exceções para ME/EPP, etc.).

**Regras de uso:**
- Cada item tem um **nível de confiança** (ALTA / MÉDIA / BAIXA) — só promover para "resposta automática ao cliente" o que estiver em ALTA confiança; itens MÉDIA/BAIXA precisam de validação jurídica antes de virar resposta automatizada.
- Textos **verbatim** de lei estão marcados como tal — preservar a citação exata quando usados em explicações ao usuário (não parafrasear artigo de lei).
- Datas de "confiança" e normas citadas devem ser revisadas **semestralmente**, pois o DREI e a CVM atualizam instruções normativas com frequência.
- Códigos de ato/evento podem variar ligeiramente entre Juntas estaduais — os códigos aqui são o padrão nacional confirmado nas fontes citadas; validar contra a Junta específica antes de automatizar o preenchimento.

---

<a name="parte-1"></a>
## 2. PARTE I — Atos Societários de LTDA e Consórcio

> Fonte: Pesquisa 1 (IN DREI 81/2020, Código Civil, LC 123/2006, manuais JUCESC/JUCEB/JUCEMG/JucisRS/JUCESP/JUCEPAR/JUCEG)

### 2.1. Norma-mestre
A **Instrução Normativa DREI nº 81/2020** (atualizada pelas INs DREI 55/2021, 112/2022, 88/2022, 1/2024 e 1/2025) é a norma nacional de observância obrigatória por todas as Juntas. O **Anexo IV** é o Manual de Registro de Sociedade Limitada.

### 2.2. ATO — Alteração de Sede

**Eventos**: Ato 002-Alteração; evento 021 (mesmo estado); eventos 038/039/051 (transferência interestadual); evento 059/210 (desistência).

#### 2.2.1. Mesmo estado
Passo a passo: consulta de viabilidade → DBE → requerimento eletrônico + alteração contratual → protocolo e deferimento.
Fundamento: art. 1.053 e art. 999 CC; Anexo IV IN 81/2020.
**Confiança: ALTA.**

#### 2.2.2. Transferência interestadual
**Fase 1 — Origem:**
1. Pesquisa/proteção do nome na Junta de destino.
2. Pedido de Viabilidade direcionado ao destino.
3. Emissão do DBE direcionado ao destino.
4. Alteração contratual com consolidação (evento 038 + 051) arquivada na origem.

**Fase 2 — Destino:**
5. Apresentar a alteração consolidada já arquivada na origem (evento 039).
6. Rerratificação (evento 048) se houver colidência de nome.
7. Deferimento do DBE → CNPJ atualizado.

**Se não se efetivar**: certidão da Junta de destino atestando não arquivamento + evento 059 (desistência) na origem.

Documentos (JUCEB): capa do processo, alteração consolidada registrada na origem, comprovante DAM, identificação de sócios/administradores, declaração de desimpedimento, procuração se aplicável.

Fundamento: IN 81/2020 Anexo IV Cap. II Seção IV item 4.11 (LTDA); Anexo II item 4.7 (Empresário); Anexo III item 4.11 (EIRELI). Prazo de exigência: 30 dias (art. 40 §§2º-3º Lei 8.934/94).
**Confiança: ALTA.**

**Variações estaduais**: PR (SIGFácil) abre processo no destino automaticamente ao iniciar na origem; MT e SC reforçam pré-requisito origem→destino.

### 2.3. ATO — Redução de Capital Social

**Eventos**: Ato 002-Alteração; evento 021/022; evento 051 se consolidar.

#### 2.3.1. Por perdas irreparáveis (art. 1.082, I + art. 1.083 CC)
- Capital totalmente integralizado.
- **NÃO exige publicação nem prazo de 90 dias** — eficaz a partir da averbação (art. 1.083).
**Confiança: ALTA.**

#### 2.3.2. Por capital excessivo (art. 1.082, II + art. 1.084 CC)
- **EXIGE dupla publicação**: Diário Oficial + jornal de grande circulação da sede (art. 1.152, §1º CC).
- **Prazo de 90 dias** para oposição de credor quirografário. Verbatim art. 1.084 §1º: *"No prazo de noventa dias, contado da data da publicação da ata da assembléia que aprovar a redução, o credor quirografário, por título líquido anterior a essa data, poderá opor-se ao deliberado."*
- Verbatim art. 1.084 §2º: *"A redução somente se tornará eficaz se... não for impugnada, ou se provado o pagamento da dívida ou o depósito judicial do respectivo valor."*
- Após os 90 dias: **30 dias** para arquivar a alteração contratual (art. 36 Lei 8.934/94).
- **Comparação com S.A.**: prazo de oposição de credores é de **60 dias** (não 90) — art. 174 Lei 6.404/76.

#### 2.3.3. Por saída/exclusão de sócio (liquidação de quotas)
- **NÃO exige publicações** dos arts. 1.052 §1º e 1.084 CC (nota do Anexo IV, IN 55/2021).

#### 2.3.4. Exceção ME/EPP
Dispensadas de **qualquer publicação** (art. 71 LC 123/2006), independente do motivo. Dispensadas de reunião/assembleia (art. 70), exceto exclusão de sócio por justa causa.

Fundamento geral: arts. 1.082-1.084, 1.152 §1º CC; art. 36 Lei 8.934/94; arts. 70-71 LC 123/2006; Anexo IV IN 81/2020.
**Confiança: ALTA.**

### 2.4. ATO — Aumento de Capital Social

**Eventos**: Ato 002-Alteração; evento 021/022; evento 051 se consolidar.

Passo a passo:
1. Quotas existentes totalmente integralizadas (art. 1.081 CC) — pré-requisito.
2. Deliberação (quórum 3/4 do capital — art. 1.076, I c/c 1.071, V).
3. **Direito de preferência**: 30 dias após deliberação (art. 1.081 §1º).
4. Reunião/assembleia final (art. 1.081 §3º).
5. Integralização (dinheiro, bens, créditos — bens imóveis exigem transcrição no RI).
6. Arquivamento.

Não há exigência de publicação. Fundamento: art. 1.081 CC; Anexo IV IN 81/2020.
**Confiança: ALTA.**

### 2.5. ATO — Alteração de Administrador/Representante Legal

**Eventos**: Ato 002-Alteração; evento 021. No CNPJ: evento 202.

Quóruns (Código Civil):
- Administrador sócio no contrato: **3/4** do capital (art. 1.076, I).
- Administrador em ato separado: **mais da metade** (art. 1.076, II).
- Administrador não sócio: **2/3** (capital integralizado) ou **unanimidade** (não integralizado) — art. 1.061.
- **Destituição de administrador sócio nomeado no contrato**: redação vigente (Lei 13.792/2019) é **"mais da metade do capital"** — verbatim art. 1.063 §1º: *"Tratando-se de sócio nomeado administrador no contrato, sua destituição somente se opera pela aprovação de titulares de quotas correspondentes a mais da metade do capital social, salvo disposição contratual diversa."* ⚠️ **Atenção**: muitas fontes desatualizadas ainda citam o quórum antigo de 2/3.
- Renúncia: eficaz perante sociedade desde a ciência; perante terceiros após averbação e publicação (art. 1.063 §3º).

**Confiança: ALTA** (quanto ao quórum vigente pós-2019); **atenção à divergência histórica** documentada em fontes secundárias.

### 2.6. ATO — Consórcio (constituição, alteração, extinção)

**Natureza CNPJ**: 215-1. Fundamento: arts. 278-279 Lei 6.404/76; arts. 90-93 IN 81/2020. **O consórcio não tem personalidade jurídica** (art. 278 §1º).

#### 2.6.1. Constituição
**Eventos**: Ato/evento 005/005 (ata de constituição); natureza 215-1.

1. **Pré-requisito crítico**: cada consorciada deve **primeiro** registrar em sua própria Junta o ato societário que aprova o contrato de consórcio (ata de reunião/assembleia).
2. Sem consulta de viabilidade.
3. DBE (natureza 215-1).
4. Requerimento Eletrônico ("Ata de assembleia geral de constituição").
5. Contrato de consórcio com cláusulas do art. 91 IN 81 / art. 279 Lei 6.404/76 (identificação das consorciadas e líder; objeto; duração; obrigações; partilha de resultados; administração; deliberações).
6. Anexar ato societário de cada consorciada já autenticado na Junta de origem.
7. Protocolo, deferimento, autenticação. **Certidão do arquivamento deve ser publicada** — verbatim art. 279, parágrafo único: *"O contrato de consórcio e suas alterações serão arquivados no registro do comércio do lugar da sua sede, devendo a certidão do arquivamento ser publicada."*

⚠️ **Erro comum a evitar (já identificado em produção)**: a IA de extração de documentos NÃO deve confundir a "Empresa Líder" (representante que assina) com o "Consórcio" (titular real do ato, identificado por CNPJ/NIRE próprios). O padrão textual típico é: *"A [EMPRESA LÍDER], na qualidade de Empresa Líder do CONSÓRCIO [NOME], (...) inscrito no CNPJ sob o nº [CNPJ DO CONSÓRCIO] ('Consórcio')..."* — o titular é sempre o Consórcio.

Vedações: consórcio não pode ser formado por pessoa física, entidade despersonalizada, associação, fundação, organização religiosa ou partido político (Ofício Circular DREI SEI 2047/2021). Não exige visto de advogado.

#### 2.6.2. Alteração (inclusive troca de empresa líder)
**Eventos**: Ato 002; evento 020/021/022; 051 se consolidar.

#### 2.6.3. Extinção/baixa
**Eventos**: Ato 003-Extinção/Distrato. Documento: distrato assinado pelas consorciadas.

**Confiança: ALTA** (base JUCESC + Lei 6.404/76).

### 2.7. ATO — Incorporação, Fusão e Cisão

**Eventos**: 042-Incorporação; 043-Fusão; 044-Cisão parcial; 045-Cisão total; 050-Absorção de parte cindida.
Fundamento: Lei 6.404/76 arts. 223-234; CC arts. 1.116-1.122; IN 81/2020 arts. 58-84.

Regras gerais (art. 58 IN 81): requerimento/capa, instrumentos de deliberação, DBE, comprovante de pagamento. **Empresário individual não pode** fazer incorporação/fusão/cisão (art. 59 §2º). Prazo: 30 dias da assinatura (art. 36 Lei 8.934/94). Publicação obrigatória (art. 1.122 c/c 1.152 §1º CC; art. 289 LSA).

#### 2.7.1. Incorporação (art. 1.116 CC / art. 227 LSA)
1. Deliberação da incorporadora (protocolo, justificação, peritos, laudo, aumento de capital) e da incorporada (protocolo, justificação, autorização).
2. Arquivamento **concomitante e vinculado**: incorporadora + incorporada (extinção).
3. Se importar reforma do ato constitutivo da LTDA incorporadora → processo separado (art. 71-A, IN 1/2024).
4. Não há vedação a incorporar sociedade com patrimônio líquido negativo (art. 70, parágrafo único) — nesse caso, sem aumento de capital.

#### 2.7.2. Fusão (art. 1.119 CC / art. 228 LSA)
Nova sociedade sucede as fundidas, que se extinguem.

#### 2.7.3. Cisão (art. 229 LSA; IN 81 arts. 80-84)
Total (extinção da cindida) ou parcial (redução de capital).

**Filiais em outra UF**: arquivamento só na Junta da sede; dados encaminhados eletronicamente à outra UF (art. 60, parágrafo único, IN 1/2024).

**Confiança: ALTA.**

### 2.8. ATO — Dissolução, Liquidação e Extinção

Fundamento: CC arts. 1.033-1.038 (dissolução/liquidante) e 1.102-1.112 (liquidação); Anexo IV IN 81/2020.

#### 2.8.1. Ato único (distrato direto)
Sem patrimônio a partilhar / dívidas quitadas. **Eventos**: Ato 003-Extinção/Distrato ("003/003"). Isento de taxa (art. 55 Lei 8.934/94).

#### 2.8.2. Dois processos (dissolução → liquidação → extinção)
1. **Dissolução**: ata nomeando liquidante + acrescentar **"EM LIQUIDAÇÃO"** ao nome (Ato 021 + evento 985 + evento 020; DBE: evento 417 + 220).
2. **Liquidação**: realização do ativo, pagamento do passivo, partilha.
3. **Extinção**: aprovação de contas, extinção averbada (art. 1.109 CC). Ato 003.

**Prazos**: sócio dissidente — 30 dias da publicação para ação (art. 1.109, parágrafo único, decadencial). Arquivamento: 30 dias (art. 36 Lei 8.934/94).

**Exceção ME/EPP**: baixa independe de certidões negativas (art. 9º LC 123/2006, red. LC 147/2014), com responsabilidade solidária de sócios/administradores (§5º). Órgãos têm 60 dias para efetivar.

**Confiança: ALTA.**

### 2.9. ATO — Transformação de Tipo Societário

**Eventos**: Ato 002; evento 046-Transformação. Fundamento: arts. 1.113-1.115 CC; arts. 62 e 68 IN 81/2020.

Independe de dissolução/liquidação (art. 1.113). Mantém CNPJ e IE. Visto de advogado obrigatório salvo ME/EPP.

**EIRELI → LTDA (caso especial já operado)**: transformação **automática** pela Lei 14.195/2021 art. 41, executada de ofício em 09/12/2022. Verbatim: *"As empresas individuais de responsabilidade limitada existentes na data da entrada em vigor desta Lei serão transformadas em sociedades limitadas unipessoais independentemente de qualquer alteração em seu ato constitutivo."* Alterou código de natureza jurídica de 230-5 (EIRELI) para 206-2 (LTDA). Atos a partir de 10/12/2022 devem usar "Ltda"/"Limitada".

**Confiança: ALTA.**

### 2.10. ATO — Exclusão/Saída de Sócio

**Eventos**: Ato 002; evento 021/022.

- **Retirada/recesso** (art. 1.029 CC): notificação com 60 dias de antecedência (prazo indeterminado). Responsabilidade por 2 anos após averbação (art. 1.032).
- **Exclusão de sócio remisso** (arts. 1.004 e 1.058).
- **Exclusão por justa causa de minoritário** (art. 1.085 CC): (a) previsão contratual; (b) maioria representando mais da metade do capital; (c) reunião especial com ciência e defesa do acusado. Exceção Lei 13.792/2019: sociedade com 2 sócios dispensa reunião prévia.

**Exceção ME/EPP**: dispensa de reunião/assembleia (art. 70 LC 123/2006), **exceto** exclusão por justa causa (§1º).

**Confiança: ALTA.**

---

<a name="parte-2"></a>
## 3. PARTE II — Sociedade Anônima, Debêntures, RDIC e Procurações

> Fonte: Pesquisa 2 (Lei 6.404/76, Lei 14.711/2023, Resolução CVM 226/2025, IN DREI 81/2020 Anexo V, manuais JUCERJA/JUCESC/JUCEMG/JUCEB)

### 3.1. Mudança jurídica crítica — Debêntures (2023-2025)

⚠️ **A escritura de debêntures NÃO é mais de registro obrigatório na Junta.** A **Lei 14.711/2023** (Marco Legal das Garantias) **revogou o art. 62, II e os §§3º e 4º** da Lei 6.404/76. Permanece obrigatório apenas o **ato societário** que deliberou a emissão (art. 62, I).

A **Resolução CVM nº 226/2025** (em vigor desde 10/03/2025) determina que, para companhias abertas, o envio da escritura e aditamentos via sistema **ENET (Empresas.NET)** substitui o registro na Junta.

**Ponto de atenção operacional**: as Juntas (ex: JUCESC) ainda mantêm o ato/evento **980** (escritura) e **981** (aditamento) em seus sistemas, por inércia — o processo tramita mas **não é mais requisito legal de validade** da emissão.

### 3.2. Debêntures — detalhamento

#### 3.2.1. Deliberação da emissão (ato societário — requisito legal vigente)
Ata de AGE (ou Conselho de Administração; após CVM 226/2025, também Diretoria). Fundamento: art. 59 (competência) + art. 62, I (arquivamento e publicação).
Prazo: 30 dias da assinatura (art. 36 Lei 8.934/94); divulgação via ENET em até 7 dias úteis para emissores no mercado de capitais.
**Confiança: ALTA.**

#### 3.2.2. Escritura de emissão (não mais obrigatória por lei)
- Ato/evento **980** (JUCESC), ainda operacional mas sem efeito de validade.
- Conteúdo obrigatório: art. 61 (condições) e art. 62 (requisitos); emissão no estrangeiro: art. 62 §3º.
- Garantia real/fidejussória: persiste registro em RTD (arts. 129/130 Lei 6.015/73).
- ⚠️ **Lacuna regulatória**: art. 62 §6º remete a regulamento do Poder Executivo para companhias fechadas, ainda pendente — há divergência doutrinária sobre exigibilidade nesse caso.
**Confiança: MÉDIA** (recomenda-se validação jurídica caso a caso).

#### 3.2.3. Aditamento de escritura
Ato/evento **981**. Modificação de condições depende de AGD com quórum mínimo de metade das debêntures em circulação (conforme escritura).
**Confiança: MÉDIA.**

#### 3.2.4. Espécies (não alteram o rito de registro, só o conteúdo)
Simples, conversível em ações (arts. 57-58), garantia real, garantia flutuante, quirografária, subordinada (art. 58).
**Confiança: MÉDIA** (doutrina).

#### 3.2.5. Agente Fiduciário (arts. 66-70)
Nomeado na escritura. Obrigatório se distribuída/negociada em mercado (art. 61 §1º). Pessoa natural apta a administrador OU instituição financeira autorizada. **Não tem poderes para acordar modificação das condições da emissão** (art. 70, parágrafo único).
**Confiança: ALTA.**

#### 3.2.6. Assembleia Geral de Debenturistas — AGD (art. 71)
Órgão **distinto** da AGE de acionistas. Convocação: agente fiduciário, companhia, CVM, ou debenturistas (≥10%). Competências: alteração de características da emissão, substituição do agente fiduciário, waiver de covenants.
**Registro**: ata arquivável sob ato/evento **014** (JUCESC), quando exigido por lei ou pela escritura.
**Confiança: ALTA.**

#### 3.2.7. Companhia aberta vs. fechada
Aberta: regulação CVM (Resoluções 80/2022, 160/2022, 226/2025); ENET; escritura não vai à Junta.
Fechada: art. 62 §6º pendente de regulamento pleno.
**Confiança: ALTA.**

### 3.3. RDIC — Arquivamento de Documento de Interesse da Companhia

**Código**: ato/evento **310** — "outros documentos de interesse da empresa/empresário" (padrão nacional).

**Exemplos (tabela JUCERJA)**: procuração, emancipação, nomeação/renúncia/destituição de administrador, declaração de exclusividade, alvará, publicação de ato, **ata de reunião de conselho fiscal**, **acordo de acionistas/cotistas**, atos já arquivados em outra Junta, comunicação de funcionamento/paralisação, balanço patrimonial, pacto antenupcial, contrato de alienação/usufruto/arrendamento de estabelecimento.

Passo a passo: módulo integrador → ato "outros documentos de interesse" → anexar → pagar taxa → assinar/transmitir. Prazo de análise: até 2 dias úteis (JUCEMG).

Não exige visto de advogado. Dispensa reconhecimento de firma (art. 63 Lei 8.934/94).

**Confiança: ALTA.**

### 3.4. Procurações

**Código**: ato **206** (arquivada isoladamente) / evento **206** (instrui outro processo); revogação = ato **207**.

Regra DREI (Anexo V, item 1.2), verbatim: *"A procuração poderá, a critério do interessado, apenas instruir o requerimento, devendo ser anexada ao ato (preferencialmente, utilizando-se o evento específico) a ser arquivado, ou ser arquivada em processo separado (utilizando-se o ato específico). Nesta última hipótese, com pagamento do preço do serviço devido."*

**Três situações distintas — CRÍTICO para a árvore de decisão da IA:**
1. **Representação de acionista em assembleia** → entregue à mesa; **não** vai à Junta.
2. **Requerer processo perante a Junta** → documento auxiliar, anexo ao protocolo.
3. **Arquivamento isolado** → ato 206, processo próprio, com taxa.

**Requisitos formais**: dispensa reconhecimento de firma (art. 63 Lei 8.934/94, salvo exigência específica de Junta — JUCERJA exige em certos modelos); outorgante analfabeto/incapaz → instrumento público; assinatura digital ICP-Brasil ou gov.br.

**Outorgante estrangeiro (PF ou PJ)**:
- Representante residente no Brasil, com poderes para receber citação (IN DREI 81/2020 art. 12).
- Documento do exterior: **apostilado** (países da Convenção de Haia) ou **consularizado** (demais países).
- Traduzido por tradutor público matriculado em Junta, se não em português; documento bicolunado (PT + estrangeiro) dispensa tradução mas exige apostila/consularização (art. 15 §4º, IN DREI 1/24).
- PJ estrangeira: prova de constituição/existência legal + CNPJ.
- Exceções: documento lavrado por notário francês dispensa consularização (Decreto 91.207/1985); tratados MERCOSUL podem dispensar.

**Confiança: ALTA.**

### 3.5. Constituição de S.A. (ato/evento 005)

**Subscrição particular**: assembleia de constituição; subscrição de 100% do capital por ≥2 pessoas (art. 80, I); ≥10% de entrada em dinheiro + depósito no Banco do Brasil ou banco autorizado pela CVM (art. 80, II-III); projeto de estatuto; laudo de avaliação se houver bens (art. 8º).

Verbatim art. 80: *"II - realização, como entrada, de 10% (dez por cento), no mínimo, do preço de emissão das ações subscritas em dinheiro; III - depósito, no Banco do Brasil S/A., ou em outro estabelecimento bancário autorizado pela Comissão de Valores Mobiliários, da parte do capital realizado em dinheiro."*

**Subscrição pública**: registro prévio na CVM + intermediação de instituição financeira (art. 82).

Prazo: publicação/arquivamento em 30 dias (arts. 94/98). Companhia não constituída em 6 meses do depósito → banco restitui subscritores (art. 81).

**Confiança: ALTA.**

### 3.6. Partes Beneficiárias e Bônus de Subscrição

Partes beneficiárias: **vedadas a companhias abertas** (art. 47, parágrafo único); podem ter agente fiduciário (arts. 66-71 aplicáveis no que couber).
Bônus de subscrição: deliberação AGE ou CA dentro do capital autorizado (art. 76).
Registro segue a **ata deliberativa**; não há ato/evento próprio identificado além dela.
**Confiança: MÉDIA** — recomenda-se confirmar código de evento junto à Junta específica.

### 3.7. AGO vs. AGE

**AGO (art. 132)**: obrigatória nos **4 primeiros meses** após o exercício social. Verbatim: *"Anualmente, nos 4 (quatro) primeiros meses seguintes ao término do exercício social, deverá haver 1 (uma) assembléia-geral para: I - tomar as contas dos administradores..."*
Atraso: sem multa legal específica na S.A. fechada, mas responsabilização de administradores; **companhia aberta → infração grave à CVM** (ICVM 480/09 art. 60, c/c art. 11 Lei 6.385/76). Ata arquivável mesmo fora do prazo.

**AGE**: demais matérias (reforma de estatuto, emissão de debêntures, operações societárias). Pode ser cumulada com AGO em ata única (art. 131).

**Publicações**: art. 289 (jornal de grande circulação) ou art. 294 (companhia fechada, receita bruta anual ≤ R$ 78 milhões — verbatim: *"realizar as publicações ordenadas por esta Lei de forma eletrônica, em exceção ao disposto no art. 289"*, via Central de Balanços/SPED, Portaria ME 12.071/2021) ou arts. 294-A/B + Resolução CVM 166/2022 (companhia aberta de menor porte, receita bruta < R$ 500 milhões).

**Confiança: ALTA.**

### 3.8. Conselho Fiscal

Instalação deliberada em assembleia; permanente ou de funcionamento (art. 161). Atas arquiváveis como RDIC (ato 310, listado expressamente pela JUCERJA) ou pelo ato próprio **018** (ata de reunião de conselho fiscal, tabela nacional).
**Confiança: ALTA.**

### 3.9. Acordo de Acionistas (art. 118)

Eficácia perante a companhia: arquivamento **na sede** desta (caput). Oponibilidade a terceiros: averbação nos livros de registro de ações (§1º). **Registro na Junta não é obrigatório por lei**, mas admitido via ato 310 e recomendável para eficácia erga omnes. Parte sigilosa pode ser omitida do arquivamento.
**Confiança: ALTA.**

---

<a name="parte-3"></a>
## 4. PARTE III — Varredura de Viabilidade de Automação (Playwright) por Estado

> Fonte: Pesquisa 3 (portais oficiais das 27 Juntas Comerciais estaduais)

### 4.1. Resumo executivo

- Pelo menos **9 estados além de RJ/BA/PE** têm ALTA VIABILIDADE de automação: MG, RS, PR, GO, SC, CE, MS, PA e SE.
- **SP (JUCESP)** é o único caso confirmado de BAIXA VIABILIDADE — barreira no **download** (login gov.br unificado + saldo tarifado via Jucesp Online), não na consulta de status.
- A plataforma **"EMPREENDEDOR DIGITAL"** (convênio público gratuito Sebrae/Gov.br/ITI/DREI) é usada por MG, RS, CE, MS, DF, MT, AC, AP, RR — mesmo layout/URL padrão (`portalservicos.<junta>.<uf>.gov.br/Portal/pages/consultaProcesso.jsf`), permitindo **um único scraper genérico** cobrir até 9 estados.

### 4.2. Ranking — Alta Viabilidade (próximos candidatos, em ordem de prioridade)

| # | Estado/Junta | Sistema | Observação |
|---|---|---|---|
| 1 | Minas Gerais (JUCEMG) | Empreendedor Digital | GET por protocolo na URL; maior prioridade econômica |
| 2 | Rio Grande do Sul (JucisRS) | Empreendedor Digital | Consulta 24/7 confirmada |
| 3 | Paraná (JUCEPAR) | Página ASP legada | Simples, sem defesas visíveis |
| 4 | Santa Catarina (JUCESC) | REGIN | Mesma família de RJ/BA |
| 5 | Goiás (JUCEG) | App JSF próprio | Aberto, sem login |
| 6 | Ceará (JUCEC) | Empreendedor Digital | — |
| 7 | Mato Grosso do Sul (JUCEMS) | Empreendedor Digital | — |
| 8 | Pará (JUCEPA) | Sistema próprio (Cellent) | Download exige conta própria (não gov.br) |
| 9 | Sergipe (JUCESE) | Agiliza Sergipe | Só protocolo/CNPJ |
| — | DF, MT, AC, AP, RR | Empreendedor Digital | Confirmados como parte do convênio fundador (9 juntas originais) |

### 4.3. Baixa viabilidade

**São Paulo (JUCESP)**: download de documentos exige login unificado gov.br/certificado digital e-CPF + saldo pago via Jucesp Online. Barreira no download, não no status.

### 4.4. Não verificado (requer varredura complementar)

Maranhão (possível WAF anti-scraping detectado), Piauí, Alagoas, Rio Grande do Norte, Paraíba, Amazonas, Rondônia, Tocantins, Acre (nível de detalhe).

### 4.5. Recomendação de implementação

**Fase 1 (maior ROI)**: scraper genérico parametrizável para a família Empreendedor Digital — cobre MG, RS, CE, MS de uma vez.
**Fase 2**: reaproveitar scraper REGIN (já validado em RJ/BA) para SC e AC.
**Fase 3**: JUCEPA e JUCESE; validar e ligar DF, MT, AP, RR.

### 4.6. Status de implementação real (ATUALIZAR conforme execução)

> ⚠️ Seção a preencher pela equipe conforme o Claude Code for validando e implementando cada estado.

| Estado | Status | Data | Observação |
|---|---|---|---|
| RJ | ✅ Produção | — | JUCERJA, sistema REGIN |
| BA | ✅ Produção | — | JUCEB, sistema REGIN |
| PE | ✅ Produção | — | JUCEPE, portal próprio |
| MG | 🔲 Pendente | — | Validação ao vivo solicitada em 01/08/2026 |
| RS | 🔲 Pendente | — | Validação ao vivo solicitada em 01/08/2026 |
| DF | 🔲 Pendente | — | Validação ao vivo solicitada em 01/08/2026 |
| CE, MS, MT, AC, AP, RR | 🔲 Não iniciado | — | Extensão planejada para fase seguinte |

---

<a name="parte-4"></a>
## 5. PARTE IV — Taxas/Emolumentos e Requisitos de Assinatura

> Fonte: Pesquisa 4 (tabelas oficiais JUCESP, JUCERJA, JUCEB, JUCEMG; Lei 8.934/94; IN DREI 81/2020; Lei 14.063/2020)


> **Atualizacao automatica (01/08/2026, Nivel 1)** — fonte: [DREI - Instrucoes Normativas (IN 81/2020 atualizada)](https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao)
> [TESTE AUTOMATIZADO - NAO E UMA MUDANCA REAL] Valor de taxa de teste da JUCESP em 2027: R$ 999,99.
>
> *Justificativa: Teste automatizado do mecanismo de aplicacao (sera revertido em seguida).*
### 5.1. Taxas — vigência 2026 (valores em R$, sede)

⚠️ **Valores mudam anualmente** (a maioria em janeiro; JucisRS reajusta em abril). Revisar a cada início de ano.

| Ato societário | JUCESP (SP) | JUCERJA (RJ) | JUCEB (BA) | JUCEMG (MG) | Confiança |
|---|---|---|---|---|---|
| Constituição de LTDA | 218,99 (ME/EPP) / 273,55 (demais) | 650 (500 no deferimento automático) | 360,00 | 268,51 (padrão ME) / 429,61 (personalizado) | ALTA |
| Alteração contratual simples | 218,99 / 273,55 | 650 | 360,00 | não confirmado 2026 | ALTA (SP/RJ/BA) |
| Constituição de S.A. / atas AGO-AGE | 583,98 | 1.100 | 670,00 | não confirmado | ALTA (SP/RJ/BA) |
| Escritura de debêntures + aditamento | 766,48 | 1.100 | 670,00 | não confirmado | ALTA (SP/BA) |
| RDIC / documento de interesse | 164,05 | 650 | 360,00 | não confirmado | ALTA (SP/BA) |
| Procuração isolada | 164,05 | 650 | 360,00 | não confirmado | ALTA (SP/BA) |
| Consórcio (constituição/alteração) | 729,98 | 1.100 | — | não confirmado | ALTA (SP/RJ) |
| Incorporação/fusão/cisão/transformação | 583,98 (por ata) | 1.100 | 670,00 | não confirmado | ALTA (SP/BA) |
| Dissolução/distrato/extinção de LTDA | **Isento** | **Isento** | **Isento** | **Isento** | ALTA (lei federal) |
| Inscrição de Empresário Individual | 94,90 | 100 (ou 50 automático) | 156,00 | ~134,58 (estimativa) | ALTA (SP/RJ/BA) |

**Referência de outros estados (fonte secundária, confirmar antes de usar em produção)**: PR ~79-110; SC ~82-168; RS ~100-172; MG ~135-268; PE ~178-396; MS ~191-378; GO ~178-296; CE ~141-248 (constituição de Empresário/LTDA).

### 5.2. Isenções legais (aplicam-se nacionalmente)

- **Extinção de EI/EIRELI/LTDA**: isenta por lei — art. 55, §2º Lei 8.934/94 (incluído pela Lei 13.874/2019).
- **MEI**: isento de **todos** os custos de abertura, alteração e baixa — art. 4º §3º LC 123/06 (redação LC 147/2014). STJ (REsp 1.812.064/MG) confirmou que a isenção abrange inclusive taxas de fiscalização/vigilância sanitária.
- **ME/EPP**: dispensa de **publicação** (art. 71 LC 123/06) — não isenta a taxa de arquivamento em si, mas algumas Juntas (SP) cobram valor menor.
- **Registro automático/contrato padrão gratuito**: CE (JUCEC), RS (JucisRS "Tudo Fácil Empresas"), SP-capital (Balcão Único, matriz com contrato padrão + conta gov.br prata/ouro).
- **Capital social NÃO altera o valor da taxa** nas Juntas pesquisadas — valor é fixo por tipo de ato (diferente de cartórios extrajudiciais, que são progressivos).

### 5.3. Requisitos de Assinatura

**Regra geral (nacional)**: qualquer ato pode ser assinado com **certificado ICP-Brasil** (e-CPF/e-CNPJ A1 ou A3) OU **conta gov.br nível Prata ou Ouro**. **Reconhecimento de firma está dispensado por lei** — art. 63 Lei 8.934/94 (redação Lei 14.195/2021): *"Os atos levados a arquivamento nas juntas comerciais são dispensados de reconhecimento de firma."* A redação anterior excetuava procurações; essa exceção foi removida.

| Ato | Assinatura aceita | Reconhecimento de firma |
|---|---|---|
| Todos os atos de LTDA, S.A., Consórcio | ICP-Brasil ou gov.br Prata/Ouro | Dispensado |
| Debêntures / AGD / RDIC | ICP-Brasil ou gov.br Prata/Ouro | Dispensado |
| **Procuração** | ICP-Brasil ou gov.br Prata/Ouro | Dispensado (histórico controverso — pacificado pelo STJ) |

**Pontos de atenção operacional:**
- **gov.br Prata**: validação por biometria facial/CNH ou banco credenciado. **gov.br Ouro**: validação via base do TSE. **gov.br Bronze**: NÃO assina, apenas acompanha processos.
- **2FA obrigatório desde agosto/2025** para assinar via gov.br (Ofício Circular SEI 183/2025/MEMP do DREI) — implantação escalonada por Junta (JUCEPAR/JUCEES desde 04/08/2025; JUCEMG desde 18/08/2025).
- **Sócio/administrador estrangeiro sem certificado**: outorgar procuração a representante no Brasil, arquivada em processo autônomo (art. 12 IN DREI 81/2020).
- **Menor relativamente incapaz (assistido)**: procuração sempre por **instrumento público** (não digital) — Ofício DREI SEI 82/2019; art. 654 CC.
- **STJ (REsp 2.243.445-SP, decisão 19/01/2026)**: validou procuração assinada via gov.br **sem** reconhecimento de firma, "salvo se houver impugnação específica quanto à autenticidade da assinatura digital".
- Excepcionalmente, qualquer Junta pode exigir firma reconhecida se houver **dúvida fundada e concreta** sobre autenticidade de assinatura manuscrita (poder-dever de fiscalização, art. 1.153 CC) — só se aplica a documentos em papel, não a assinaturas digitais.

### 5.4. Onde encontrar as tabelas oficiais

- **JUCESP**: institucional.jucesp.sp.gov.br/downloads/ (site bloqueia bots; espelhos em escritórios regionais, ex. jucespsorocaba.com.br)
- **JUCERJA**: jucerja.rj.gov.br/Informacoes/TabelaPrecos
- **JUCEB**: ba.gov.br/juceb/tabelas-de-precos-capital
- **JUCEMG**: jucemg.mg.gov.br/pagina/52/tabela-de-precos (bloqueia bots)
- **JUCEC**: jucec.ce.gov.br/tabela-de-precos/
- **JucisRS**: jucisrs.rs.gov.br/tabela-de-precos
- **JUCESC / JUCEG / JUCEPAR / JUCEMS**: portal oficial de cada estado (ver Parte VII — Fontes)

---

<a name="glossario"></a>
## 6. Glossário unificado de códigos de Ato/Evento REDESIM

| Código | Descrição | Aplicação |
|---|---|---|
| 001 | Constituição | Empresário/LTDA |
| 002 | Alteração | Todos os tipos societários |
| 003 | Extinção/Distrato/Desconstituição | Todos |
| 005 | Ata de assembleia geral de constituição | S.A. e Consórcio (natureza 215-1) |
| 014 | Ata de Assembleia Geral de Debenturistas (AGD) | S.A. |
| 016 | Ata de reunião de diretoria | S.A. |
| 017 | Ata de reunião de conselho de administração | S.A. |
| 018 | Ata de reunião de conselho fiscal | S.A. |
| 020 | Alteração de nome | Todos |
| 021 | Alteração de dados (exceto nome) | Todos |
| 022 | Alteração de dados e nome | Todos |
| 038 | Transferência de sede para outra UF | Todos (Junta de origem) |
| 039 | Inscrição de transferência de sede de outra UF | Todos (Junta de destino) |
| 042 | Incorporação | LTDA/S.A. |
| 043 | Fusão | LTDA/S.A. |
| 044 | Cisão parcial | LTDA/S.A. |
| 045 | Cisão total | LTDA/S.A. |
| 046 | Transformação | Todos |
| 048 | Rerratificação | Todos |
| 050 | Absorção de parte cindida | LTDA/S.A. |
| 051 | Consolidação | Todos |
| 059/210 | Desistência de transferência de sede | Todos |
| 202 | Alteração de responsável perante CNPJ | Todos (nível RFB) |
| 206 | Procuração (arquivamento isolado ou evento auxiliar) | Todos |
| 207 | Revogação de procuração | Todos |
| 220 | Alteração de nome para "EM LIQUIDAÇÃO" (DBE/CNPJ) | Todos |
| 310 | Outros documentos de interesse da companhia (RDIC) | S.A. principalmente |
| 417 | Início de liquidação extrajudicial (DBE/CNPJ) | Todos |
| 980 | Escritura de emissão de debêntures (não mais obrigatório por lei desde a Lei 14.711/2023) | S.A. |
| 981 | Aditamento de escritura de emissão de debêntures | S.A. |
| 985 | Ata (evento genérico, usado em conjunto com outros) | Todos |
| 215-1 | Natureza jurídica — Consórcio de Sociedades/Empresas | Consórcio |

⚠️ Códigos podem variar ligeiramente entre Juntas estaduais — validar contra o manual local antes de automatizar preenchimento.

---

<a name="atualizacao-autonoma"></a>
## 7. Sistema de Atualização Autônoma

**Objetivo**: manter este documento (e a base de dados que a IA consulta em produção) atualizado semanalmente, sem depender de intervenção manual constante, mas sem permitir que a IA reescreva conteúdo jurídico sem rastreabilidade.

### 7.1. Arquitetura de 3 níveis

**Nível 1 — Automático, sem revisão (mudanças factuais/estruturais, não-ambíguas)**
Aplicado automaticamente e registrado no changelog com fonte. Exemplos: URL de portal mudou; valor de taxa mudou em tabela oficial nova; código de evento substituído por outro em manual oficial.

**Nível 2 — Automático, com log auditável (alta confiança, mas envolve conteúdo normativo)**
A IA aplica a mudança (nova IN, nova Resolução) quando consegue mapear com alta confiança qual seção da base ela afeta, citando o trecho legal exato. Não bloqueia — só registra no changelog para auditoria posterior por um humano.

**Nível 3 — Retido para revisão humana (baixa confiança)**
Quando a mudança é ambígua, contraditória entre fontes, ou a IA não consegue mapear com segurança o escopo do impacto. Aciona notificação ao administrador via Telegram (bot ATOS já existente) com: fonte da mudança, trecho detectado, seção candidata da base, e motivo da baixa confiança. Só é aplicada após confirmação humana.

### 7.2. Fontes a monitorar semanalmente

- Portal DREI — legislação e instruções normativas: gov.br/empresas-e-negocios/pt-br/drei/legislacao
- Diário Oficial da União — seção de atos do Ministério do Empreendedorismo (INs DREI, Portarias)
- CVM — normas e resoluções (para a Parte II — S.A./debêntures)
- Páginas de "passo a passo"/tabela de preços das Juntas já mapeadas (JUCERJA, JUCESP, JUCEMG, JUCEB, JUCEPE, JucisRS, JUCESC, JUCEPAR, JUCEG, JUCEC, JUCEMS, JUCIS-DF)
- Publicações de reajuste de unidade fiscal estadual (UFESP, UFEMG, UFIRCE etc.), que impactam a Parte IV

### 7.3. Mecanismo técnico (a implementar)

1. **Job semanal agendado** (cron no servidor) faz snapshot das fontes acima e compara com o snapshot da semana anterior (diff de conteúdo).
2. **Classificador de mudança** (IA) categoriza cada diff detectado em Nível 1, 2 ou 3, conforme critério acima.
3. **Aplicação**: Nível 1 e 2 atualizam a seção correspondente deste arquivo automaticamente, com entrada no changelog (data, fonte, trecho, nível). Nível 3 dispara notificação Telegram e aguarda aprovação antes de tocar no arquivo.
4. **Notificação de resumo semanal**: mesmo em semana sem mudanças de Nível 3, enviar um resumo curto (“nada mudou” ou lista do que foi atualizado automaticamente) para o Telegram do administrador — silêncio também é informação, mas precisa ser confirmado que o robô rodou.

### 7.4. Status de implementação

🔲 **Não implementado ainda** — este documento descreve o desenho funcional; falta o comando de implementação técnica (job cron, classificador, integração Telegram) ser executado pelo Claude Code no repositório `D:\Mane`.

---

<a name="changelog"></a>
## 8. Registro de mudanças / Changelog

| Data | Mudança | Responsável |
|---|---|---|
| 01/08/2026 | [auto] DREI - Instrucoes Normativas (IN 81/2020 atualizada): [TESTE AUTOMATIZADO - NAO E UMA MUDANCA REAL] Valor de taxa de teste da JUCESP em 2027: R$ 999,99. | Vigia normativo (Nivel 1, automatico) |
| 01/08/2026 | Consolidação inicial das 3 pesquisas em documento único | Claude (a pedido de Diogo) |
| 01/08/2026 | Adicionada Parte IV (taxas/emolumentos e assinaturas) | Claude (a pedido de Diogo) |
| 01/08/2026 | Desenhado sistema de atualização autônoma (3 níveis) — implementação técnica pendente | Claude (a pedido de Diogo) |
| — | Pendente: pesquisa complementar de JUCERJA/JUCEPE/JUCIS-DF/JUCEC/JUCEMS com mesmo nível de detalhe das demais | — |
| — | Pendente: validar codificação exata de eventos por Junta antes de automatizar preenchimento | — |
| — | Pendente: confirmar valores JUCEMG 2026 (S.A., atas, procuração, RDIC) em fonte oficial | — |
| — | Pendente: implementação técnica do job de atualização autônoma (Claude Code) | — |

---

<a name="fontes"></a>
## 9. Fontes primárias consolidadas

### Normas federais
- IN DREI nº 81/2020 (atualizada até IN 1/2025): https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao/instrucoes-normativas/arquivos-instrucoes-normativas-em-vigor/INDREI81_Atualizada_in0125.pdf
- Anexo IV – Manual de Registro de Sociedade Limitada: https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao/instrucoes-normativas/arquivos-instrucoes-normativas-em-vigor/anexo-iv-limitada_link.pdf
- IN DREI nº 1/2024 (incorporação/fusão/cisão): https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao/instrucoes-normativas/arquivos-instrucoes-normativas-em-vigor/SEI_39711171_Instrucao_Normativa_11.pdf
- Código Civil (Lei 10.406/2002): https://www.planalto.gov.br/ccivil_03/leis/l10406compilada.htm
- Lei das S.A. (Lei 6.404/1976): https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm
- Lei de Registro de Empresas (Lei 8.934/1994): https://www.planalto.gov.br/ccivil_03/leis/l8934.htm
- LC 123/2006 (ME/EPP): https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm
- Lei 14.195/2021 (art. 41 — EIRELI→LTDA): planalto.gov.br
- Lei 14.711/2023 (Marco Legal das Garantias — revoga art. 62 II Lei 6.404/76): planalto.gov.br
- Resolução CVM nº 226/2025: site da CVM (gov.br/cvm)

### Juntas Comerciais — passo a passo oficiais
- JUCEB – Transferência de sede: http://www.juceb.ba.gov.br/home/passo-a-passo/transferencia-de-sede-entre-uf-distintas/
- JUCEB – Transformação EIRELI→LTDA: http://www.juceb.ba.gov.br/home/passo-a-passo/transformacao-de-eireli-em-sociedade-empresaria/
- JUCESC – Base de conhecimento (consórcio, incorporação, distrato, debêntures, AGD): atendimento.jucesc.sc.gov.br/help
- JUCEPAR – Transferência de sede / Tabela de atos e eventos: juntacomercial.pr.gov.br
- JUCEMAT – Redução de capital: jucemat.mt.gov.br/faqs/2
- JUCEMG – Entendimentos consolidados / Transformação: jucemg.mg.gov.br
- JucisRS – Orientações SRM atos e eventos / Perguntas e respostas CNPJ: jucisrs.rs.gov.br
- JUCEG – Tabela de preços 2026: goias.gov.br/juceg
- JUCESP – Anexo II LTDA / Jucesp Online: institucional.jucesp.sp.gov.br
- JUCIS-DF – IN 81 (texto): jucis.df.gov.br
- JUCERJA – Tabela de emolumentos e consulta de processos: jucerja.rj.gov.br

### Automação (Parte III)
- Portais de consulta pública por estado — ver detalhamento na Parte III, seção 4.

### Taxas e Assinaturas (Parte IV)
- JUCESP – Portaria nº 146/2025 (tabela de preços 2026): institucional.jucesp.sp.gov.br/downloads/
- JUCERJA – Deliberação nº 171/2025 (tabela de preços 2026): jucerja.rj.gov.br/Informacoes/TabelaPrecos
- JUCEB – Tabela de Preços Capital: ba.gov.br/juceb/tabelas-de-precos-capital
- JUCEMG – Resolução Plenária nº 02/2025 + tabela em UFEMG: jucemg.mg.gov.br/pagina/52/tabela-de-precos
- JUCEC – Tabela de serviços 2026: jucec.ce.gov.br/tabela-de-precos/
- JucisRS – Tabela de preços: jucisrs.rs.gov.br/tabela-de-precos
- Lei 8.934/1994, art. 55 e art. 63 (isenções e dispensa de firma): planalto.gov.br
- LC 123/2006, art. 4º §3º e art. 71 (isenções ME/EPP/MEI): planalto.gov.br
- Lei 14.063/2020 (assinaturas eletrônicas — simples, avançada, qualificada): planalto.gov.br
- IN DREI 81/2020, art. 36 (assinatura eletrônica em atos societários): gov.br/drei
- Ofício Circular SEI 183/2025/MEMP (2FA obrigatório gov.br desde ago/2025): DREI
- STJ, REsp 2.243.445-SP (procuração via gov.br, decisão 19/01/2026) e REsp 1.812.064/MG (isenção MEI)

*(URLs verificadas em agosto/2026; revalidar periodicamente pois portais estaduais migram endereços com frequência e taxas mudam anualmente — em geral em janeiro, exceto JucisRS em abril.)*
