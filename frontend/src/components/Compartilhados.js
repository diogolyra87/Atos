import { useState, useEffect } from "react";
import axios from "axios";

export const STATUS_CONFIG = {
  recebido: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  aberto: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  tramitacao: { label: "Tramitação", bg: "#f0e0cb", color: "#8a5818" },
  exigencia: { label: "Exigência", bg: "#f0dcd5", color: "#a8492a" },
  deferido: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  aprovado: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  finalizado: { label: "Finalizado", bg: "#cfe8d8", color: "#15803d" },
};

export const JUNTA_POR_UF = {
  AC: "JUCEAC", AL: "JUCEAL", AP: "JUCAP", AM: "JUCEA", BA: "JUCEB", CE: "JUCEC",
  DF: "JUCIS-DF", ES: "JUCEES", GO: "JUCEG", MA: "JUCEMA", MT: "JUCEMAT", MS: "JUCEMS",
  MG: "JUCEMG", PA: "JUCEPA", PB: "JUCEP", PR: "JUCEPAR", PE: "JUCEPE", PI: "JUCEPI",
  RJ: "JUCERJA", RN: "JUCERN", RS: "JucisRS", RO: "JUCER", RR: "JUCERR", SC: "JUCESC",
  SP: "JUCESP", SE: "JUCESE", TO: "JUCETO",
};

export function nomeJunta(uf) {
  const sigla = (uf || "").toUpperCase().trim();
  return JUNTA_POR_UF[sigla] || sigla || "-";
}

export function subtituloProcesso(p) {
  const ato = p.identificador_ato || p.tipo_ato || "-";
  return ato + " · " + nomeJunta(p.uf);
}

export function chaveDataAta(dataAta) {
  const m = (dataAta || "").match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return null;
  return `${m[3]}-${m[2]}-${m[1]}`;
}

export function formatarDataExtenso(chaveAAAAMMDD) {
  const [ano, mes, dia] = chaveAAAAMMDD.split("-").map(Number);
  const d = new Date(ano, mes - 1, dia);
  return d.toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}

export function StatCard({ valor, label, corFundo, corTexto, icone, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{ background: corFundo, borderRadius: 10, padding: 16, cursor: onClick ? "pointer" : "default" }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <div style={{ fontSize: 12, color: corTexto, fontWeight: 500, opacity: 0.85 }}>{label}</div>
        {icone && <div style={{ fontSize: 14, color: corTexto, opacity: 0.55 }}>{icone}</div>}
      </div>
      <div style={{ fontFamily: "'DM Serif Display', serif", fontSize: 40, fontWeight: 400, color: corTexto, lineHeight: 1 }}>
        {valor}
      </div>
    </div>
  );
}

export function FluxoDoDiaCard({ fluxo }) {
  if (!fluxo) return null;
  const pct = fluxo.total > 0 ? Math.round((fluxo.confirmados / fluxo.total) * 100) : 0;
  return (
    <div style={{ background: "#FAFAFF", border: "1px solid #AFA9EC", borderRadius: 10, padding: 16, marginBottom: 12 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#3C3489", marginBottom: 8 }}>
        Fluxo do dia
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>
        {fluxo.confirmados} de {fluxo.total} confirmados pela Junta
      </div>
      <div style={{ background: "#EEEDFE", borderRadius: 6, height: 8, overflow: "hidden" }}>
        <div style={{ background: "#534AB7", height: "100%", width: `${pct}%`, transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}

export function AtividadeRecente({ eventos }) {
  return (
    <div style={{ background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 10, padding: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#23282a", marginBottom: 14 }}>
        Atividade recente
      </div>
      {(!eventos || eventos.length === 0) ? (
        <div style={{ fontSize: 13, color: "#94a3b8" }}>Nenhuma atividade ainda.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {eventos.map((ev, i) => (
            <div
              key={i}
              style={{
                fontSize: 12,
                color: "#475569",
                borderBottom: i < eventos.length - 1 ? "0.5px solid #f1f5f9" : "none",
                paddingBottom: 8,
              }}
            >
              <div style={{ color: "#23282a" }}>{ev.descricao}</div>
              <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 2 }}>
                {ev.autor_nome ? `por ${ev.autor_nome} · ` : ""}{new Date(ev.criado_em).toLocaleString("pt-BR")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function StatusDonut({ metricas }) {
  const total = metricas.total || 0;
  const aberto = Math.max(0, total - (metricas.tramitacao || 0) - (metricas.exigencia || 0) - (metricas.deferido || 0) - (metricas.finalizado || 0));
  const segmentos = [
    { valor: aberto, cor: STATUS_CONFIG.aberto.color, label: "Aberto" },
    { valor: metricas.tramitacao || 0, cor: STATUS_CONFIG.tramitacao.color, label: "Tramitação" },
    { valor: metricas.exigencia || 0, cor: STATUS_CONFIG.exigencia.color, label: "Exigência" },
    { valor: metricas.deferido || 0, cor: STATUS_CONFIG.deferido.color, label: "Deferido" },
    { valor: metricas.finalizado || 0, cor: STATUS_CONFIG.finalizado.color, label: "Finalizado" },
  ].filter(seg => seg.valor > 0);

  const raio = 60;
  const circ = 2 * Math.PI * raio;
  let acumulado = 0;

  return (
    <div style={{ background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 10, padding: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#23282a", marginBottom: 14 }}>
        Status dos processos
      </div>
      {total === 0 ? (
        <div style={{ fontSize: 13, color: "#94a3b8" }}>Nenhum processo ainda.</div>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <svg width="140" height="140" viewBox="0 0 140 140">
            <g transform="rotate(-90 70 70)">
              <circle cx="70" cy="70" r={raio} fill="none" stroke="#eceae2" strokeWidth="18" />
              {segmentos.map((seg, i) => {
                const comprimento = (seg.valor / total) * circ;
                const offset = -acumulado;
                acumulado += comprimento;
                return (
                  <circle
                    key={i}
                    cx="70"
                    cy="70"
                    r={raio}
                    fill="none"
                    stroke={seg.cor}
                    strokeWidth="18"
                    strokeDasharray={`${comprimento} ${circ - comprimento}`}
                    strokeDashoffset={offset}
                  />
                );
              })}
            </g>
            <text
              x="70"
              y="70"
              textAnchor="middle"
              dominantBaseline="central"
              style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fill: "#23282a" }}
            >
              {total}
            </text>
          </svg>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {segmentos.map((seg, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#475569" }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: seg.cor }} />
                {seg.label}: {seg.valor}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const API = "";

function mensagemInicialIatos(p) {
  const status = (p.status || "").toLowerCase();
  if (status === "exigencia") {
    return "Esse ato está em exigência" + (p.numero_protocolo ? " (protocolo " + p.numero_protocolo + ")" : "") + ". Posso te explicar o que precisa ser feito para cumprir a exigência — é só perguntar.";
  }
  if (status === "deferido" || status === "aprovado") {
    return "Esse ato já foi deferido! Assim que a Junta liberar o registro, você recebe o documento por aqui. Posso te explicar os próximos passos.";
  }
  if (status === "finalizado") {
    return "Esse ato está finalizado — o registro já foi liberado e está disponível pra download. Posso esclarecer alguma dúvida sobre ele.";
  }
  if (status === "tramitacao") {
    return "Esse ato já está protocolado. Só falta aguardar o deferimento — eu aviso quando mudar. Alguma dúvida sobre esse processo?";
  }
  return "Esse ato ainda está sendo preparado para protocolo. Posso te ajudar a entender os próximos passos.";
}

// Icone oficial do iatos. (quadrado azul + "a." em serifada preta) - reusado
// identico no botao fechado e no cabecalho do chat aberto, conforme
// docs/iatos_referencia_visual.html. "AtosBrand" e' a fonte oficial da logo
// "atos." (@font-face em public/index.html) - cai pra Georgia se o arquivo
// da fonte nao estiver disponivel (ver nota no relatorio).
function IconeIatos({ tamanho = 22 }) {
  return (
    <span style={{ width: tamanho, height: tamanho, borderRadius: 5, background: "#0091D4", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <span style={{ fontFamily: "AtosBrand, Georgia, 'Times New Roman', serif", fontWeight: 700, fontSize: 15, color: "#000000", lineHeight: 1, display: "flex", alignItems: "baseline" }}>
        a<span style={{ fontSize: 10, marginLeft: 1 }}>.</span>
      </span>
    </span>
  );
}

// Botao pra barra de acoes (ao lado de "Ver processo"/"Ver") - area clicavel
// UNICA: onClick fica so' no <button> pai, os spans internos (icone/texto/
// separador) nao tem handler proprio nenhum, entao qualquer clique dentro
// borbulha pro botao (comportamento nativo do <button>). Dispara
// onAbrir(processo); quem guarda "qual processo esta com o chat aberto" e
// renderiza <IatosChat> e' o componente pai (Cliente.js/App.js).
export function BotaoIatos({ processo, onAbrir }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={() => onAbrir(processo)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "10px 14px", border: "0.5px solid #c9c9c4", borderRadius: 8, background: hover ? "#f5f5f3" : "#fff", cursor: "pointer", fontFamily: "inherit" }}>
      <IconeIatos />
      <span style={{ fontSize: 13.5, color: "#2451D6", whiteSpace: "nowrap" }}>iatos.</span>
      <span style={{ width: 1, height: 14, background: "#d5d5d0" }} />
      <span style={{ fontSize: 12, color: "#6b6b68", whiteSpace: "nowrap" }}>Posso ajudar?</span>
    </button>
  );
}

// Chat em modal/overlay, acessivel a qualquer momento (lista, detalhe, onde
// o BotaoIatos for colocado) - nao fica escondido dentro de um fluxo
// especifico (ex: so' na insercao de um ato novo).
export function IatosChat({ processo, token, onFechar }) {
  const [msgs, setMsgs] = useState([]);
  const [pergunta, setPergunta] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!processo) return;
    (async () => {
      // Monta (ou remonta) o contexto completo do processo - documento integral +
      // dados estruturados + base de conhecimento - ANTES de qualquer pergunta,
      // no exato momento em que o chat abre. Ver /assistente/abrir em main.py.
      try {
        await axios.post(`${API}/assistente/abrir`, { processo_id: processo.id },
          token ? { headers: { "x-token": token } } : {});
      } catch (e) { /* silencioso - /assistente/perguntar monta na 1a pergunta se isso falhar */ }
      let historico = [];
      try {
        const r = await axios.get(`${API}/processos/${processo.id}/assistente/historico`, token ? { headers: { "x-token": token } } : {});
        historico = r.data || [];
      } catch (e) { /* silencioso - segue so com a mensagem inicial */ }
      const iniciais = [{ autor: "assistente", texto: mensagemInicialIatos(processo) }];
      for (const h of historico) {
        iniciais.push({ autor: "usuario", texto: h.mensagem });
        iniciais.push({ autor: "assistente", texto: h.resposta });
      }
      setMsgs(iniciais);
    })();
    /* eslint-disable-next-line */
  }, [processo && processo.id]);

  if (!processo) return null;

  async function enviar() {
    const t = pergunta.trim();
    if (!t || enviando) return;
    setEnviando(true);
    const historicoParaEnvio = msgs.slice(1).map(m => ({ autor: m.autor, texto: m.texto }));
    setMsgs(m => [...m, { autor: "usuario", texto: t }]);
    setPergunta("");
    try {
      const r = await axios.post(`${API}/assistente/perguntar`,
        { processo_id: processo.id, pergunta: t, historico: historicoParaEnvio },
        token ? { headers: { "x-token": token } } : {});
      setMsgs(m => [...m, { autor: "assistente", texto: r.data.resposta }]);
    } catch (e) {
      setMsgs(m => [...m, { autor: "assistente", texto: "Sua dúvida é específica e por isso um Operador Atos vai entrar em contato. Obrigado." }]);
    }
    setEnviando(false);
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100 }}
      onClick={onFechar}>
      <div style={{ width: 420, maxWidth: "92vw", maxHeight: "80vh", border: "0.5px solid #e0e0dc", borderRadius: 12, overflow: "hidden", boxShadow: "0 10px 50px rgba(20,10,50,0.25)" }}
        onClick={e => e.stopPropagation()}>
        <div style={{ padding: "10px 14px", borderBottom: "0.5px solid #e0e0dc", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <IconeIatos />
            <span style={{ fontSize: 14.5, color: "#1a1a1a" }}>iatos<span style={{ color: "#2451D6" }}>.</span></span>
          </span>
          <span onClick={onFechar} style={{ fontSize: 14, color: "#999", cursor: "pointer" }}>✕</span>
        </div>
        <div style={{ padding: 14, background: "#fff" }}>
          <div style={{ maxHeight: 340, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
            {msgs.map((m, i) => {
              const meu = m.autor === "usuario";
              return (
                <div key={i} style={{ alignSelf: meu ? "flex-end" : "flex-start", maxWidth: "85%", background: meu ? "#dbeafe" : "#f5f5f3", borderRadius: 10, padding: "8px 12px" }}>
                  <div style={{ fontSize: 13, color: "#1a1a1a", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{m.texto}</div>
                </div>
              );
            })}
            {enviando && (
              <div style={{ alignSelf: "flex-start", maxWidth: "85%", background: "#f5f5f3", borderRadius: 10, padding: "8px 12px", fontSize: 13, color: "#94a3b8" }}>
                digitando...
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <textarea value={pergunta} onChange={e => setPergunta(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }}
              placeholder="Digite sua pergunta..."
              style={{ flex: 1, minHeight: 40, maxHeight: 120, padding: "8px 12px", border: "0.5px solid #e2e8f0", borderRadius: 8, fontSize: 13, outline: "none", resize: "vertical", fontFamily: "sans-serif" }} />
            <button onClick={enviar} disabled={enviando}
              style={{ background: "#2451D6", color: "#fff", border: "none", padding: "10px 18px", borderRadius: 8, fontSize: 13, cursor: "pointer", height: 40 }}>
              {enviando ? "..." : "Enviar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
