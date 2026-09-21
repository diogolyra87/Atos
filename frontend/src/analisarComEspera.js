// Envio de documento para analise que NAO depende de a requisicao ficar aberta.
//
// Incidente 21/09/2026: uma ata cuja leitura cai em OCR leva ~6 minutos, mas o nginx corta
// POST /processos/analisar aos 180s (504) - a tela nunca recebia os dados e o processo ficava
// preso em "Processando". Agora o servidor le em segundo plano: se a leitura terminar logo, a
// resposta e' a de sempre; se demorar, responde na hora {processando: true} e (envio unico)
// o PROPRIO SERVIDOR conclui o processo quando acabar. Estes helpers escondem isso das telas:
// devolvem o mesmo formato de resposta do axios que os fluxos ja esperavam.
//
// - analisarDocumento: POST /processos/analisar. Se a analise demorou, acompanha por
//   GET /processos/{id}/analise e devolve {data: {..., processo_id, ja_criado: true}}. Com
//   ja_criado=true o processo JA foi concluido pelo servidor: a tela NAO deve chamar
//   POST /processos de novo.
// - analisarLote: POST /processos/analisar-pasta-multi. Se demorou, acompanha por
//   GET /processos/analise-lote/{job_id} e devolve {data: <mesma estrutura de sempre>}.
//   No fluxo de pasta a tela continua concluindo cada processo (ha confirmacoes humanas).
//
// Erros: lancam Error com .motivo ("falhou" | "cancelado" | "desconhecido" | "tempo_esgotado")
// e uma mensagem pronta pra mostrar ao usuario.

export const MENSAGEM_LENDO =
  "Lendo o documento (OCR) - pode levar alguns minutos. O processo é concluído automaticamente, mesmo que você feche esta tela.";

const INTERVALO_MS = 4000;
const LIMITE_MS = 30 * 60 * 1000;
const FALHAS_SEGUIDAS_MAX = 5;

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

function erroEspera(motivo, mensagem) {
  const e = new Error(mensagem);
  e.motivo = motivo;
  return e;
}

async function acompanhar(axios, url, config, tratar, opcoes) {
  const { onEspera, intervaloMs = INTERVALO_MS, limiteMs = LIMITE_MS, dormirFn = dormir } = opcoes || {};
  const inicio = Date.now();
  let falhas = 0;
  if (onEspera) onEspera(true);
  try {
    while (Date.now() - inicio < limiteMs) {
      await dormirFn(intervaloMs);
      let r;
      try {
        r = await axios.get(url, config);
        falhas = 0;
      } catch (e) {
        // sessao invalida / sem permissao: nao adianta insistir. Queda de rede pontual: tenta de novo.
        if (e && e.response && (e.response.status === 401 || e.response.status === 403)) throw e;
        falhas += 1;
        if (falhas >= FALHAS_SEGUIDAS_MAX) throw e;
        continue;
      }
      const saida = tratar(r.data || {});
      if (saida !== undefined) return saida;
    }
    throw erroEspera(
      "tempo_esgotado",
      "A leitura do documento está demorando mais que o esperado. O arquivo já foi recebido e aparece na lista como 'Processando'; ele será concluído automaticamente."
    );
  } finally {
    if (onEspera) onEspera(false);
  }
}

export async function analisarDocumento(axios, formData, config, opcoes) {
  const base = (opcoes && opcoes.base) || "";
  const res = await axios.post(`${base}/processos/analisar`, formData, config);
  const d = res.data || {};
  if (!d.processando) return res;
  const pid = d.processo_id;
  return acompanhar(axios, `${base}/processos/${pid}/analise`, config, (r) => {
    if (r.estado === "concluido") {
      return { ...res, data: { ...(r.dados || {}), processo_id: pid, ja_criado: !!r.ja_criado } };
    }
    if (r.estado === "falhou") {
      throw erroEspera("falhou", "Não foi possível ler o documento. Ele foi registrado como falha de processamento e a equipe foi avisada.");
    }
    if (r.estado === "cancelado") {
      throw erroEspera("cancelado", "O processo foi excluído durante a leitura do documento.");
    }
    return undefined;
  }, opcoes);
}

export async function analisarLote(axios, formData, config, opcoes) {
  const base = (opcoes && opcoes.base) || "";
  const res = await axios.post(`${base}/processos/analisar-pasta-multi`, formData, config);
  const d = res.data || {};
  if (!d.processando) return res;
  return acompanhar(axios, `${base}/processos/analise-lote/${d.job_id}`, config, (r) => {
    if (r.estado === "concluido") return { ...res, data: r.resultado };
    if (r.estado === "falhou") {
      throw erroEspera("falhou", "Não foi possível analisar os documentos. Eles foram registrados como falha de processamento e a equipe foi avisada.");
    }
    if (r.estado === "desconhecido") {
      throw erroEspera("desconhecido", "O sistema foi reiniciado durante a leitura. Os arquivos aparecem na lista; se ficarem em falha, envie-os novamente.");
    }
    return undefined;
  }, opcoes);
}
