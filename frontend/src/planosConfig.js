// Configuracao centralizada dos planos exibidos na tela "Escolha seu plano"
// (rota /solicitar-acesso/plano, componente EscolhaPlano.js). Pro e Premium
// ainda nao existem de verdade (so' o badge "EM BREVE").
//
// QUANDO OS PLANOS PRO/PREMIUM FOREM DEFINIDOS, EDITE SOMENTE ESTE ARQUIVO:
// - preencha "preco" (ex: "R$ 49") e ajuste "features"/"incluido"
// - troque "emBreve" pra false e "ativo" pra true
// - ajuste "botaoLabel" (ex: "Assinar Pro")
// EscolhaPlano.js ja renderiza qualquer combinacao desses campos sem
// precisar mudar a estrutura/logica do componente.
export const PLANOS = [
  {
    id: "free",
    nome: "Free",
    preco: "R$ 0",
    precoSufixo: "/mês",
    ativo: true,
    emBreve: false,
    features: [
      { texto: "Organização de processos", incluido: true },
      { texto: "Upload de documentos", incluido: true },
      { texto: "Armazenamento na nuvem", incluido: true },
      { texto: "Consulta automática às Juntas", incluido: false },
      { texto: "Assistente iatos.", incluido: false },
    ],
    botaoLabel: "Começar grátis",
  },
  {
    id: "pro",
    nome: "Pro",
    preco: null,
    precoSufixo: "/mês",
    ativo: false,
    emBreve: true,
    features: [
      { texto: "Tudo do Free", incluido: false },
      { texto: "Consulta automática às Juntas", incluido: false },
      { texto: "Assistente iatos.", incluido: false },
      { texto: "Alertas de prazo", incluido: false },
    ],
    botaoLabel: "Em breve",
  },
  {
    id: "premium",
    nome: "Premium",
    preco: null,
    precoSufixo: "/mês",
    ativo: false,
    emBreve: true,
    features: [
      { texto: "Tudo do Pro", incluido: false },
      { texto: "Automação em todas as Juntas", incluido: false },
      { texto: "iatos. prioritário", incluido: false },
      { texto: "Suporte dedicado", incluido: false },
    ],
    botaoLabel: "Em breve",
  },
];
