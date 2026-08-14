import { useState, useEffect } from "react";
import axios from "axios";

// Breakpoints do redesign-visual-2026: mobile <768, tablet 768-1024, desktop
// >1024. O projeto usa estilo inline em quase tudo (nao CSS classes) - reagir
// a largura de tela via JS (em vez de @media + !important) mantem o mesmo
// padrao do resto do codebase e evita brigar com a especificidade do inline
// style (que sempre vence sobre classe, !important a parte).
export function useBreakpoint() {
  const calc = () => {
    if (typeof window === "undefined") return "desktop";
    const w = window.innerWidth;
    if (w < 768) return "mobile";
    if (w < 1024) return "tablet";
    return "desktop";
  };
  const [bp, setBp] = useState(calc);
  useEffect(() => {
    function onResize() { setBp(calc()); }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    /* eslint-disable-next-line */
  }, []);
  return bp;
}

export const STATUS_CONFIG = {
  recebido: { label: "Aberto", bg: "rgba(255,159,10,0.12)", color: "#ff9f0a", borda: "rgba(255,159,10,0.3)" },
  aberto: { label: "Aberto", bg: "rgba(255,159,10,0.12)", color: "#ff9f0a", borda: "rgba(255,159,10,0.3)" },
  tramitacao: { label: "Tramitação", bg: "rgba(0,212,255,0.12)", color: "#00d4ff", borda: "rgba(0,212,255,0.3)" },
  exigencia: { label: "Exigência", bg: "rgba(255,77,77,0.12)", color: "#ff4d4d", borda: "rgba(255,77,77,0.3)" },
  deferido: { label: "Deferido", bg: "rgba(77,148,255,0.12)", color: "#4d94ff", borda: "rgba(77,148,255,0.3)" },
  aprovado: { label: "Deferido", bg: "rgba(77,148,255,0.12)", color: "#4d94ff", borda: "rgba(77,148,255,0.3)" },
  finalizado: { label: "Finalizado", bg: "rgba(0,255,170,0.12)", color: "#00ffaa", borda: "rgba(0,255,170,0.3)" },
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

// Variantes escuras de FluxoDoDiaCard/AtividadeRecente (redesign-visual-2026) -
// os mockups de referencia nao mostram esses dois widgets (nao fazem parte do
// "Meus Processos"/"Todos os Processos" ali), mas ambos tem dado real por tras
// (GET /fluxo/ativo, GET /eventos/recentes) que precisa continuar visivel em
// algum lugar da tela - aqui, abaixo do card principal, com a mesma paleta
// escura do resto do dashboard.
export function FluxoDoDiaCardEscuro({ fluxo }) {
  if (!fluxo) return null;
  const pct = fluxo.total > 0 ? Math.round((fluxo.confirmados / fluxo.total) * 100) : 0;
  return (
    <div style={{ background: "#0e0e14", border: "1px solid rgba(140,90,255,0.3)", borderRadius: 14, padding: 18, fontFamily: FONTE_CORPO }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#c4b5fd", marginBottom: 8 }}>Fluxo do dia</div>
      <div style={{ fontSize: 12, color: "#8a90b8", marginBottom: 8 }}>{fluxo.confirmados} de {fluxo.total} confirmados pela Junta</div>
      <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: 6, height: 8, overflow: "hidden" }}>
        <div style={{ background: "linear-gradient(90deg, #4d94ff, #8c5aff)", height: "100%", width: `${pct}%`, transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}

export function AtividadeRecenteEscura({ eventos }) {
  return (
    <div style={{ background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: 18, fontFamily: FONTE_CORPO }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#a8b0d8", marginBottom: 12 }}>Atividade recente</div>
      {(!eventos || eventos.length === 0) ? (
        <div style={{ fontSize: 13, color: "#62666d" }}>Nenhuma atividade ainda.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {eventos.map((ev, i) => (
            <div key={i} style={{ fontSize: 12, color: "#c4c8e4", borderBottom: i < eventos.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none", paddingBottom: 8 }}>
              <div style={{ color: "#e4e4e7" }}>{ev.descricao}</div>
              <div style={{ color: "#62666d", fontSize: 11, marginTop: 2 }}>{ev.autor_nome ? `por ${ev.autor_nome} · ` : ""}{new Date(ev.criado_em).toLocaleString("pt-BR")}</div>
            </div>
          ))}
        </div>
      )}
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

// Icone oficial do iatos. (quadrado com gradiente azul->roxo + "a." em
// serifada branca) - reusado identico no botao fechado (lista/barra de acoes)
// e replica exatamente docs/dashboard_cliente_v11.html / .btn-iatos .icone-a.
function IconeIatos({ tamanho = 18 }) {
  return (
    <span style={{ width: tamanho, height: tamanho, borderRadius: 5, background: "linear-gradient(135deg, #4d94ff, #8c5aff)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "0 0 12px rgba(140,90,255,0.6)" }}>
      <span style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontWeight: 700, fontSize: 12, color: "#fff", lineHeight: 1 }}>a.</span>
    </span>
  );
}

// Botao pra barra de acoes (ao lado de "Ver processo"/"Ver") - area clicavel
// UNICA: onClick fica so' no <button> pai, os spans internos (icone/texto)
// nao tem handler proprio nenhum, entao qualquer clique dentro borbulha pro
// botao (comportamento nativo do <button>). Dispara onAbrir(processo); quem
// guarda "qual processo esta com o chat aberto" e renderiza <IatosChat> e' o
// componente pai (Cliente.js/App.js).
export function BotaoIatos({ processo, onAbrir }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={() => onAbrir(processo)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 7, padding: "9px 13px",
        border: "1px solid rgba(77,148,255,0.4)", borderRadius: 8,
        background: hover ? "linear-gradient(135deg, rgba(77,148,255,0.2), rgba(140,90,255,0.2))" : "linear-gradient(135deg, rgba(77,148,255,0.1), rgba(140,90,255,0.1))",
        cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap",
      }}>
      <IconeIatos />
      <span style={{ fontSize: 12, color: "#8ec2ff" }}>iatos.</span>
      <span style={{ fontSize: 11, color: "#a8b0d8" }}>Posso ajudar?</span>
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

// ============================================================================
// Identidade visual escura (redesign-visual-2026) - replica fielmente
// docs/landing_animada_v9.html, dashboard_cliente_v11.html, dashboard_admin_v8.html,
// ver_processo_cliente_*.html e criar_acesso_v1.html. Fundo #060608, sidebar
// com gradiente + glows radiais, 'Space Grotesk' pra titulos/numeros e
// 'Plus Jakarta Sans' pro corpo (ver public/index.html para o import das fontes).
// ============================================================================

export const FONTE_TITULO = "'Space Grotesk', sans-serif";
export const FONTE_CORPO = "'Plus Jakarta Sans', -apple-system, sans-serif";

// Sidebar reutilizada por Cliente.js e App.js (admin) - so' os itens de
// navegacao e o rodape (indicador de grupo vs. badge ADMINISTRADOR) mudam.
export function SidebarAtos({ itens, rodape, onLogoClick }) {
  const bp = useBreakpoint();
  const mobile = bp === "mobile";
  const [menuAberto, setMenuAberto] = useState(false);

  const navBtnStyle = (it) => ({
    padding: "9px 12px", borderRadius: 8, fontSize: 13, fontFamily: FONTE_CORPO,
    color: it.disabled ? "#8b93b8" : (it.ativo ? "#b0dcff" : "#8b93b8"),
    background: it.ativo ? "linear-gradient(90deg, rgba(77,148,255,0.28), rgba(0,212,255,0.1))" : "transparent",
    borderLeft: it.ativo ? "2px solid #4d94ff" : "2px solid transparent",
    boxShadow: it.ativo ? "0 0 24px rgba(77,148,255,0.2)" : "none",
    border: "none", textAlign: "left", display: "flex", alignItems: "center", gap: 8,
    cursor: it.disabled ? "default" : "pointer", opacity: it.disabled ? 0.35 : 1, width: "100%",
  });

  if (mobile) {
    // Em telas <768px a sidebar vertical de 220px fixos nao cabe - vira uma
    // barra horizontal compacta com o menu recolhido atras de um botao
    // hamburguer, em vez de forcar 220px numa tela de ~375px.
    return (
      <div style={{ width: "100%", background: "linear-gradient(180deg,#0a0e2e 0%,#060810 100%)", borderBottom: "1px solid rgba(64,120,255,0.15)", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px" }}>
          <div style={{ cursor: onLogoClick ? "pointer" : "default" }} onClick={() => { onLogoClick && onLogoClick(); setMenuAberto(false); }}>
            <div style={{ fontFamily: FONTE_TITULO, fontSize: 18, fontWeight: 700, color: "#fff" }}>atos<span style={{ color: "#6db2ff", textShadow: "0 0 16px #4d94ff" }}>.</span></div>
          </div>
          <button onClick={() => setMenuAberto(a => !a)}
            aria-label="Abrir menu"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, width: 36, height: 36, color: "#fff", fontSize: 16, cursor: "pointer" }}>
            {menuAberto ? "✕" : "☰"}
          </button>
        </div>
        {menuAberto && (
          <div style={{ padding: "0 16px 16px" }}>
            {rodape}
            <nav style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 10 }}>
              {itens.map((it, i) => (
                <button key={i} onClick={it.disabled ? undefined : () => { it.onClick(); setMenuAberto(false); }} style={navBtnStyle(it)}>
                  {it.icone}{it.label}
                </button>
              ))}
            </nav>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ width: 220, flexShrink: 0, background: "linear-gradient(180deg,#0a0e2e 0%,#060810 100%)", borderRight: "1px solid rgba(64,120,255,0.15)", padding: "24px 16px", position: "relative", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ position: "absolute", top: -60, left: -60, width: 260, height: 260, background: "radial-gradient(circle, #4d94ff65 0%, transparent 70%)", filter: "blur(35px)" }} />
      <div style={{ position: "absolute", top: "40%", left: -50, width: 240, height: 240, background: "radial-gradient(circle, #00d4ff55 0%, transparent 70%)", filter: "blur(35px)" }} />
      <div style={{ position: "absolute", bottom: -80, left: -40, width: 260, height: 260, background: "radial-gradient(circle, #4d94ff60 0%, transparent 70%)", filter: "blur(35px)" }} />
      <div style={{ position: "absolute", top: 0, right: 0, width: 2, height: "100%", background: "linear-gradient(180deg, transparent, #4d94ff90 20%, #00d4ff90 50%, #4d94ff90 80%, transparent)", boxShadow: "0 0 20px 2px rgba(77,148,255,0.5)" }} />
      <div style={{ position: "relative", zIndex: 2, padding: "4px 0 20px", marginBottom: 12, cursor: onLogoClick ? "pointer" : "default" }} onClick={onLogoClick}>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: 20, fontWeight: 700, color: "#fff" }}>atos<span style={{ color: "#6db2ff", textShadow: "0 0 16px #4d94ff" }}>.</span></div>
        <div style={{ fontSize: 11, color: "#9aa8d8", marginTop: 2, fontFamily: FONTE_CORPO }}>Gestão Societária</div>
        {rodape}
      </div>
      <nav style={{ position: "relative", zIndex: 2, display: "flex", flexDirection: "column", gap: 3 }}>
        {itens.map((it, i) => (
          <button key={i} onClick={it.disabled ? undefined : it.onClick} style={navBtnStyle(it)}>
            {it.icone}
            {it.label}
          </button>
        ))}
      </nav>
      <div style={{ flex: 1 }} />
    </div>
  );
}

export function IconeProcessos() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>;
}
export function IconeRelatorios() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M3 3v18h18" /><rect x="7" y="12" width="3" height="6" rx="0.5" /><rect x="12" y="8" width="3" height="10" rx="0.5" /><rect x="17" y="5" width="3" height="13" rx="0.5" /></svg>;
}
export function IconeGrupos() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
}
export function IconeAprendizado() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M22 10 12 5 2 10l10 5 10-5Z" /><path d="M6 12v5c0 1.5 2.5 3 6 3s6-1.5 6-3v-5" /></svg>;
}

// Card principal do dashboard (Meus Processos / Todos os Processos): donut
// com gradientes+glow (SVG) + legenda + grid de status-cards. idPrefix evita
// colisao de ids de <defs> caso mais de um donut exista na mesma pagina.
// Glow de canto (halo irradiando do canto superior direito) nos cards de
// status do DonutStatusCard, quando selecionado (ver statusAtivo). So' o
// ::before precisa de CSS de verdade (pseudo-elemento nao da' pra fazer via
// style inline, unico motivo de sair do padrao inline-only do resto do
// arquivo) - a cor em si continua vindo por variavel CSS setada inline por
// card (--glow-color), igual o resto do componente controla cor por dado.
const CARD_GLOW_CSS = `
.card-glow-canto { position: relative; overflow: hidden; }
.card-glow-canto::before {
  content: "";
  position: absolute;
  top: -45%;
  right: -45%;
  width: 75%;
  height: 150%;
  opacity: 0;
  pointer-events: none;
  background: radial-gradient(circle, var(--glow-color, transparent), transparent 70%);
  transition: opacity .25s ease;
}
.card-glow-canto.glow-ativo::before { opacity: 1; }
`;

export function DonutStatusCard({ titulo, metricas, onClickStatus, idPrefix = "d", extra, grande = false, legenda = true, statusAtivo = "" }) {
  const bp = useBreakpoint();
  const mobile = bp === "mobile";
  // "grande" (usado em "Meus Processos") aumenta donut/legenda/cards pra
  // ocupar melhor a altura do card principal - so' entra em tablet/desktop
  // (mobile mantem o layout empilhado de sempre) e e' opt-in: sem a prop,
  // o componente renderiza IDENTICO ao que sempre foi (usado por "Todos os
  // Processos" no admin, que nao deve mudar em nada).
  const big = grande && !mobile;
  // "legenda=false" (opt-in, so' usado em Meus Processos/Cliente) remove a
  // lista Total/Aberto/.../Finalizado ao lado do donut - ja' redundante com
  // os 6 cards - e usa o espaco liberado pra exibir o donut maior (so' o
  // tamanho de renderizacao do svg cresce; viewBox/raio/strokeWidth, ou
  // seja a geometria dos arcos, continuam os mesmos de sempre). No mobile a
  // legenda nunca some (nao foi pedido e mantem a responsividade de sempre).
  const semLegenda = big && !legenda;
  const total = metricas.total || 0;
  const tram = metricas.tramitacao || 0;
  const exig = metricas.exigencia || 0;
  const defer = metricas.deferido || 0;
  const final = metricas.finalizado || 0;
  const aberto = Math.max(0, total - tram - exig - defer - final);
  const donutSize = big ? 200 : 180;
  const donutStroke = big ? 22 : 20;
  const raio = big ? 79 : 70, circ = 2 * Math.PI * raio;
  const segmentos = [
    { valor: aberto, stroke: "#5a5a68", filtro: false },
    { valor: tram, stroke: `url(#${idPrefix}Tram)`, filtro: true },
    { valor: exig, stroke: `url(#${idPrefix}Exig)`, filtro: true },
    { valor: defer, stroke: `url(#${idPrefix}Defer)`, filtro: true },
    { valor: final, stroke: `url(#${idPrefix}Final)`, filtro: true },
  ];
  let acumulado = 0;
  const clicavel = (chave) => onClickStatus ? { cursor: "pointer" } : {};
  const cardsDados = [
    { lbl: "TOTAL", val: total, cor: "#fff", borda: "rgba(255,255,255,0.15)", bordaAtiva: "rgba(175,169,236,0.35)", glow: "rgba(175,169,236,0.30)", bg: "rgba(255,255,255,0.06)", chave: "" },
    { lbl: "EM TRAMITAÇÃO", val: tram, cor: "#ff9f0a", borda: "rgba(255,159,10,0.3)", bordaAtiva: "rgba(255,159,10,0.4)", glow: "rgba(255,159,10,0.35)", chave: "tramitacao" },
    { lbl: "EM EXIGÊNCIA", val: exig, cor: "#ff4d4d", borda: "rgba(255,77,77,0.3)", bordaAtiva: "rgba(255,77,77,0.4)", glow: "rgba(255,77,77,0.35)", chave: "exigencia" },
    { lbl: "ABERTOS", val: aberto, cor: "#ff9f0a", borda: "rgba(255,159,10,0.3)", bordaAtiva: "rgba(250,199,117,0.4)", glow: "rgba(250,199,117,0.32)", chave: "aberto" },
    { lbl: "DEFERIDOS", val: defer, cor: "#4d94ff", borda: "rgba(77,148,255,0.3)", bordaAtiva: "rgba(77,148,255,0.4)", glow: "rgba(77,148,255,0.35)", chave: "deferido" },
    { lbl: "FINALIZADOS", val: final, cor: "#00ffaa", borda: "rgba(0,255,170,0.3)", bordaAtiva: "rgba(0,255,170,0.4)", glow: "rgba(0,255,170,0.35)", chave: "finalizado" },
  ];
  // Os 6 cards de status precisam ser QUADRADOS e, juntos, ocupar a mesma
  // altura total do donut (180px, svg fixo, ou 200px no modo "grande") - por
  // isso o grid usa tracks em pixel fixo (nao 1fr, que estica a celula pra
  // preencher a coluna "1fr" do layout externo e vira retangulo gigante) em
  // telas tablet/desktop. No mobile os cards abandonam o formato quadrado
  // (auto-height, mais legivel) e o grid vira 2 colunas.
  const CARD = big ? 94 : 84; // (donutSize - gap) / 2 linhas
  const gridCardsStyle = mobile
    ? { display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 10, width: "100%" }
    : { display: "grid", gridTemplateColumns: `repeat(3, ${CARD}px)`, gridTemplateRows: `repeat(2, ${CARD}px)`, gap: 12 };
  // No modo "grande" o donut+legenda+cards crescem e podem nao sobrar largura
  // pra "extra" (Atividade Recente/Fluxo do dia) manter a largura de sempre -
  // nesse caso quem cede espaco e' o "extra" (flex-shrink, minWidth baixo),
  // nunca o donut/cards, e a linha nunca quebra (nowrap) pra nao empurrar
  // "extra" pra baixo de novo.
  const extraStyle = mobile
    ? { flex: "none", minWidth: 0, width: "100%", alignSelf: "stretch" }
    : big
      ? { flex: "1 1 200px", minWidth: 0, width: "auto", alignSelf: "stretch" }
      : { flex: 1, minWidth: 260, width: "auto", alignSelf: "stretch" };
  return (
    <div style={{ background: "radial-gradient(circle at 10% 0%, #1a1470 0%, #0e0e14 55%)", border: "1px solid rgba(140,90,255,0.35)", borderRadius: 22, padding: mobile ? "22px 18px" : (big ? "32px 38px" : "28px 32px"), marginBottom: 16, position: "relative", overflow: "hidden", fontFamily: FONTE_CORPO }}>
      <style>{CARD_GLOW_CSS}</style>
      <div style={{ position: "absolute", top: "-30%", right: "-10%", width: 320, height: 320, background: "radial-gradient(circle, #7d3fff28, transparent 65%)", filter: "blur(24px)", pointerEvents: "none" }} />
      <div style={{ position: "relative", zIndex: 1, marginBottom: 24 }}>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: mobile ? 20 : 24, fontWeight: 700, color: "#fff" }}>{titulo}</div>
      </div>
      {semLegenda ? (
        // Layout literal do mockup aprovado (opcao_C_v3.html) - so' usado em
        // Meus Processos/Cliente (grande=true, legenda=false). CSS Grid com
        // tracks fixos pro donut (210px) e atividade (170px), cards ocupam o
        // 1fr do meio - valores copiados 1:1 do arquivo, sem adaptar.
        <div style={{ position: "relative", zIndex: 1, display: "grid", gridTemplateColumns: "210px 1fr 170px", gap: 24, alignItems: "stretch" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <svg width={225} height={225} viewBox={`0 0 ${donutSize} ${donutSize}`}>
              <defs>
                <filter id={`${idPrefix}Glow`} x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="6.3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                <linearGradient id={`${idPrefix}Tram`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#ffd699" /><stop offset="100%" stopColor="#ff9f0a" /></linearGradient>
                <linearGradient id={`${idPrefix}Exig`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#ffa3a3" /><stop offset="100%" stopColor="#ff2b2b" /></linearGradient>
                <linearGradient id={`${idPrefix}Defer`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#9ecaff" /><stop offset="100%" stopColor="#2f7cff" /></linearGradient>
                <linearGradient id={`${idPrefix}Final`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#7fffd4" /><stop offset="100%" stopColor="#00e691" /></linearGradient>
              </defs>
              <circle cx={donutSize / 2} cy={donutSize / 2} r={raio} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={donutStroke} />
              {total === 0 ? null : segmentos.map((seg, i) => {
                if (seg.valor <= 0) return null;
                const comprimento = (seg.valor / total) * circ;
                const offset = -acumulado;
                acumulado += comprimento;
                return (
                  <circle key={i} cx={donutSize / 2} cy={donutSize / 2} r={raio} fill="none" stroke={seg.stroke} strokeWidth={donutStroke} strokeLinecap="round"
                    strokeDasharray={`${comprimento} ${circ - comprimento}`} strokeDashoffset={offset}
                    transform={`rotate(-90 ${donutSize / 2} ${donutSize / 2})`} filter={seg.filtro ? `url(#${idPrefix}Glow)` : undefined} />
                );
              })}
              <text x={donutSize / 2} y={donutSize / 2 - 6} textAnchor="middle" fill="#fff" fontSize={42} fontFamily={FONTE_TITULO} fontWeight="800" letterSpacing="-1.5">{total}</text>
              <text x={donutSize / 2} y={donutSize / 2 + 19} textAnchor="middle" fill="#9aa4d0" fontSize={12} letterSpacing="0.8">PROCESSOS</text>
            </svg>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gridTemplateRows: "repeat(2, 1fr)", gap: 16 }}>
            {cardsDados.map((c, i) => {
              const selecionado = statusAtivo === c.chave;
              return (
                <div key={i} onClick={() => onClickStatus && onClickStatus(c.chave)}
                  className={"card-glow-canto" + (selecionado ? " glow-ativo" : "")}
                  style={{
                    boxSizing: "border-box",
                    background: "rgba(255,255,255,0.05)", border: `1px solid ${selecionado ? c.bordaAtiva : c.borda}`, borderRadius: 18,
                    padding: 22, display: "flex", flexDirection: "column", justifyContent: "center",
                    transition: "border-color .25s ease",
                    "--glow-color": c.glow,
                    ...clicavel(c.chave),
                  }}>
                  <div style={{ fontSize: 13, color: "#a8b0d8", marginBottom: 10 }}>{c.lbl}</div>
                  <div style={{ fontFamily: FONTE_TITULO, fontSize: 38, fontWeight: 700, color: c.cor }}>{c.val}</div>
                </div>
              );
            })}
          </div>
          {extra && <div style={{ minWidth: 0 }}>{extra}</div>}
        </div>
      ) : (
        <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: mobile ? "column" : "row", flexWrap: big ? "nowrap" : "wrap", gap: mobile ? 20 : 36, alignItems: mobile ? "stretch" : "flex-start" }}>
          <div style={{ display: "flex", alignItems: "center", gap: big ? 28 : 24, flexWrap: mobile ? "wrap" : "nowrap" }}>
            <svg width={donutSize} height={donutSize} viewBox={`0 0 ${donutSize} ${donutSize}`}>
              <defs>
                <filter id={`${idPrefix}Glow`} x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="6.3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                <linearGradient id={`${idPrefix}Tram`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#ffd699" /><stop offset="100%" stopColor="#ff9f0a" /></linearGradient>
                <linearGradient id={`${idPrefix}Exig`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#ffa3a3" /><stop offset="100%" stopColor="#ff2b2b" /></linearGradient>
                <linearGradient id={`${idPrefix}Defer`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#9ecaff" /><stop offset="100%" stopColor="#2f7cff" /></linearGradient>
                <linearGradient id={`${idPrefix}Final`} x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#7fffd4" /><stop offset="100%" stopColor="#00e691" /></linearGradient>
              </defs>
              <circle cx={donutSize / 2} cy={donutSize / 2} r={raio} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={donutStroke} />
              {total === 0 ? null : segmentos.map((seg, i) => {
                if (seg.valor <= 0) return null;
                const comprimento = (seg.valor / total) * circ;
                const offset = -acumulado;
                acumulado += comprimento;
                return (
                  <circle key={i} cx={donutSize / 2} cy={donutSize / 2} r={raio} fill="none" stroke={seg.stroke} strokeWidth={donutStroke} strokeLinecap="round"
                    strokeDasharray={`${comprimento} ${circ - comprimento}`} strokeDashoffset={offset}
                    transform={`rotate(-90 ${donutSize / 2} ${donutSize / 2})`} filter={seg.filtro ? `url(#${idPrefix}Glow)` : undefined} />
                );
              })}
              <text x={donutSize / 2} y={big ? donutSize / 2 - 6 : donutSize / 2 - 5} textAnchor="middle" fill="#fff" fontSize={big ? 42 : 38} fontFamily={FONTE_TITULO} fontWeight="800" letterSpacing="-1.5">{total}</text>
              <text x={donutSize / 2} y={big ? donutSize / 2 + 19 : donutSize / 2 + 17} textAnchor="middle" fill="#9aa4d0" fontSize={big ? 12 : 11} letterSpacing="0.8">PROCESSOS</text>
            </svg>
            <div style={{ display: "flex", flexDirection: "column", gap: big ? 9 : 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("") }} onClick={() => onClickStatus && onClickStatus("")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#fff", flexShrink: 0 }} />Total <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{total}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("aberto") }} onClick={() => onClickStatus && onClickStatus("aberto")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#5a5a68", flexShrink: 0 }} />Aberto <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{aberto}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("tramitacao") }} onClick={() => onClickStatus && onClickStatus("tramitacao")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#ff9f0a", flexShrink: 0 }} />Tramitação <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{tram}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("exigencia") }} onClick={() => onClickStatus && onClickStatus("exigencia")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#ff4d4d", flexShrink: 0 }} />Exigência <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{exig}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("deferido") }} onClick={() => onClickStatus && onClickStatus("deferido")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#4d94ff", flexShrink: 0 }} />Deferido <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{defer}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: big ? 9 : 8, fontSize: big ? 14 : 12.5, color: "#c4c8e4", ...clicavel("finalizado") }} onClick={() => onClickStatus && onClickStatus("finalizado")}>
                <span style={{ width: big ? 9 : 8, height: big ? 9 : 8, borderRadius: 2, background: "#00ffaa", flexShrink: 0 }} />Finalizado <span style={{ fontWeight: 700, color: "#fff", marginLeft: 2 }}>{final}</span>
              </div>
            </div>
          </div>
          <div style={gridCardsStyle}>
            {cardsDados.map((c, i) => {
              const selecionado = statusAtivo === c.chave;
              return (
                <div key={i} onClick={() => onClickStatus && onClickStatus(c.chave)}
                  className={"card-glow-canto" + (selecionado ? " glow-ativo" : "")}
                  style={{
                    boxSizing: "border-box",
                    background: c.bg || "rgba(255,255,255,0.04)", border: `1px solid ${selecionado ? c.bordaAtiva : c.borda}`, borderRadius: 14,
                    padding: mobile ? "12px 14px" : (big ? 16 : 14), display: "flex", flexDirection: "column", justifyContent: "center",
                    transition: "border-color .25s ease",
                    "--glow-color": c.glow,
                    ...(mobile ? { minHeight: 74 } : { width: CARD, height: CARD }),
                    ...clicavel(c.chave),
                  }}>
                  <div style={{ fontSize: big ? 11.5 : 10, color: "#a8b0d8", marginBottom: 6 }}>{c.lbl}</div>
                  <div style={{ fontFamily: FONTE_TITULO, fontSize: mobile ? 20 : (big ? 28 : 24), fontWeight: 700, color: c.cor }}>{c.val}</div>
                </div>
              );
            })}
          </div>
          {extra && (
            <div style={extraStyle}>
              {extra}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const KEYFRAMES_LANDING = `
  @keyframes atosDrift { 0%,100%{ transform:translate(0,0) scale(1); } 50%{ transform:translate(3%,-4%) scale(1.05); } }
  @keyframes atosMarquee { 0%{ transform:translateX(0); } 100%{ transform:translateX(-50%); } }
  @keyframes atosGlowScaleIn { 0% { opacity: 0; transform: scale(0.4); } 100% { opacity: 1; transform: scale(1); } }
  @keyframes atosFadeUp { 0% { opacity: 0; transform: translateY(18px); } 100% { opacity: 1; transform: translateY(0); } }
  @keyframes atosTileCascade { 0% { opacity: 0; transform: translateY(14px) scale(0.96); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
  @keyframes atosSlideInRight { 0% { opacity: 0; transform: translateX(48px); } 100% { opacity: 1; transform: translateX(0); } }
  .atos-glow-1 { animation: atosGlowScaleIn 0.6s cubic-bezier(0.22,1,0.36,1) 0s both, atosDrift 11s ease-in-out 0.6s infinite; }
  .atos-glow-2 { animation: atosGlowScaleIn 0.6s cubic-bezier(0.22,1,0.36,1) 0.08s both, atosDrift 13s ease-in-out reverse 0.68s infinite; }
  .atos-glow-3 { animation: atosGlowScaleIn 0.6s cubic-bezier(0.22,1,0.36,1) 0.16s both, atosDrift 9s ease-in-out 0.76s infinite; }
  .atos-logo-block { animation: atosFadeUp 0.5s cubic-bezier(0.22,1,0.36,1) 0.32s both; }
  .atos-headline-block { animation: atosFadeUp 0.5s cubic-bezier(0.22,1,0.36,1) 0.4s both; }
  .atos-subtext-block { animation: atosFadeUp 0.5s cubic-bezier(0.22,1,0.36,1) 0.46s both; }
  .atos-tile-a { animation: atosTileCascade 0.45s cubic-bezier(0.22,1,0.36,1) 0.55s both; }
  .atos-tile-b { animation: atosTileCascade 0.45s cubic-bezier(0.22,1,0.36,1) 0.62s both; }
  .atos-tile-e { animation: atosTileCascade 0.45s cubic-bezier(0.22,1,0.36,1) 0.69s both; }
  .atos-marquee-wrap { animation: atosFadeUp 0.4s ease 0.92s both; }
  .atos-login-card-anim { animation: atosSlideInRight 0.55s cubic-bezier(0.22,1,0.36,1) 0.5s both; }
`;

// Tela de login/abertura do sistema - replica fielmente docs/landing_animada_v9.html
// (painel esquerdo animado com 3 tiles + login card a direita). Compartilhada
// entre o login do admin (App.js) e do cliente (Cliente.js) - unica fonte
// visual pros dois, evitando divergencia entre eles. Campos usam Login (nao
// E-mail) porque a autenticacao real e' por login/senha, nao por e-mail.
export function TelaLogin({ subtitulo, erro, aviso, etapa, login, senha, codigo, carregando, onChangeLogin, onChangeSenha, onChangeCodigo, onEntrar, onVerificarCodigo, onVoltarEtapa }) {
  const bp = useBreakpoint();
  const mobile = bp === "mobile";
  const [modoEsqueci, setModoEsqueci] = useState(false);
  const [loginEsqueci, setLoginEsqueci] = useState("");
  const [statusEsqueci, setStatusEsqueci] = useState("");
  async function enviarEsqueciSenha() {
    if (!loginEsqueci || statusEsqueci === "enviando") return;
    setStatusEsqueci("enviando");
    try { await axios.post("/esqueci-senha", { login: loginEsqueci }); } catch (e) {}
    setStatusEsqueci("enviado");
  }
  const campoLabel = { fontSize: 12, color: "oklch(75% 0.03 250)", marginBottom: 6, display: "block", fontWeight: 600, fontFamily: FONTE_CORPO };
  const campoInput = { width: "100%", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: "12px 14px", color: "#fff", fontSize: 13.5, marginBottom: 18, fontFamily: FONTE_CORPO, outline: "none", boxSizing: "border-box" };
  const campoBtn = { width: "100%", background: "linear-gradient(120deg, oklch(65% 0.22 255), oklch(68% 0.2 210))", border: "none", borderRadius: 10, padding: 13, color: "#08070d", fontSize: 14, fontWeight: 700, fontFamily: FONTE_CORPO, boxShadow: "0 0 26px oklch(65% 0.22 255 / 0.4)", cursor: "pointer" };

  // Pecas reutilizadas nas duas variantes (mobile e desktop) - extraidas pra
  // variaveis pra poder REORDENAR o fluxo no mobile (logo->headline->login->
  // cards) sem duplicar JSX nem arriscar o desktop divergir por engano.
  const glows = (<>
    <div className="atos-glow-1" style={{ position: "absolute", top: -90, left: -70, width: 360, height: 360, borderRadius: "50%", background: "radial-gradient(circle, oklch(65% 0.22 255 / 0.35), transparent 70%)", filter: "blur(10px)" }} />
    <div className="atos-glow-2" style={{ position: "absolute", bottom: "5%", left: "22%", width: 320, height: 320, borderRadius: "50%", background: "radial-gradient(circle, oklch(75% 0.17 195 / 0.22), transparent 70%)", filter: "blur(10px)" }} />
    <div className="atos-glow-3" style={{ position: "absolute", top: "25%", right: -70, width: 280, height: 280, borderRadius: "50%", background: "radial-gradient(circle, oklch(62% 0.24 300 / 0.28), transparent 70%)", filter: "blur(10px)" }} />
  </>);

  const logoBlock = (
    <div className="atos-logo-block" style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 2, marginBottom: 24 }}>
      <span style={{ fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 28, color: "#fff" }}>atos<span style={{ color: "oklch(75% 0.2 250)", textShadow: "0 0 16px oklch(65% 0.24 255 / 0.7)" }}>.</span></span>
      <span style={{ fontSize: 14, color: "oklch(72% 0.06 250)", letterSpacing: "0.05em" }}>Gestão Societária</span>
    </div>
  );

  const headline = (<>
    <h1 className="atos-headline-block" style={{ position: "relative", zIndex: 1, fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 30, lineHeight: 1.22, color: "#fff", maxWidth: 500, margin: "0 0 10px" }}>
      Todos os seus <span style={{ color: "oklch(75% 0.2 250)" }}>registros societários</span>, sob controle em tempo real.
    </h1>
    <p className="atos-subtext-block" style={{ position: "relative", zIndex: 1, fontSize: 13.5, color: "oklch(78% 0.03 250)", lineHeight: 1.55, maxWidth: 460, margin: "0 0 22px" }}>
      Do protocolo ao deferimento em qualquer Junta Comercial do Brasil — com IA acompanhando cada etapa por você.
    </p>
  </>);

  const tilesGrid = (
    <div style={{ position: "relative", zIndex: 1, display: "grid", gridTemplateColumns: mobile ? "1fr" : "repeat(3,1fr)", gap: 12, flex: mobile ? "none" : 1, minHeight: mobile ? 0 : 200, minWidth: 0 }}>
      <div className="atos-tile-a" style={{ minHeight: 0, minWidth: 0, background: "rgba(255,255,255,0.04)", border: "1px solid oklch(80% 0.22 145 / 0.3)", borderRadius: 20, padding: "22px 20px", display: "flex", flexDirection: "column", justifyContent: "center", boxShadow: "0 0 22px oklch(80% 0.22 145 / 0.1)" }}>
        <div style={{ width: 39, height: 39, borderRadius: 10, background: "oklch(80% 0.22 145 / 0.18)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, boxShadow: "0 0 18px oklch(80% 0.22 145 / 0.6), 0 0 34px oklch(80% 0.22 145 / 0.3)" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="oklch(85% 0.22 145)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="M18 17V9" /><path d="M13 17V5" /><path d="M8 17v-3" /></svg>
        </div>
        <div>
          <div style={{ fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 16, color: "#fff", marginBottom: 8 }}>Visão Completa dos Seus Atos em Tempo Real</div>
          <div style={{ fontSize: 12.5, color: "oklch(70% 0.02 270)", lineHeight: 1.55 }}>Relatórios de processos gerados automaticamente, sua gestão societária organizada.</div>
        </div>
      </div>
      <div className="atos-tile-b" style={{ minHeight: 0, minWidth: 0, background: "linear-gradient(135deg, oklch(30% 0.13 300 / 0.5), rgba(255,255,255,0.04))", border: "1px solid oklch(65% 0.24 300 / 0.35)", borderRadius: 20, padding: "22px 20px", display: "flex", flexDirection: "column", justifyContent: "center", boxShadow: "0 0 22px oklch(65% 0.24 300 / 0.15)" }}>
        <div style={{ width: 39, height: 39, borderRadius: 10, background: "oklch(75% 0.2 250)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, boxShadow: "0 0 18px oklch(75% 0.2 250 / 0.9), 0 0 34px oklch(75% 0.2 250 / 0.5)" }}>
          <span style={{ fontFamily: "Georgia, serif", fontWeight: 700, fontSize: 18, color: "#08070d" }}>a.</span>
        </div>
        <div>
          <div style={{ fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 16, color: "#fff", marginBottom: 8 }}>iatos<span style={{ color: "oklch(78% 0.22 300)" }}>.</span> ao seu lado</div>
          <div style={{ fontSize: 12.5, color: "oklch(78% 0.05 300)", lineHeight: 1.55 }}>Assistente de IA para suporte em cada etapa do seu processo.</div>
        </div>
      </div>
      <div className="atos-tile-e" style={{ minHeight: 0, minWidth: 0, background: "rgba(255,255,255,0.045)", border: "1px solid oklch(70% 0.2 250 / 0.25)", borderRadius: 20, padding: "22px 20px", display: "flex", flexDirection: "column", justifyContent: "center", boxShadow: "0 0 30px oklch(70% 0.2 250 / 0.1)" }}>
        <div style={{ width: 39, height: 39, borderRadius: 10, background: "oklch(70% 0.2 250 / 0.18)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, boxShadow: "0 0 18px oklch(70% 0.2 250 / 0.6), 0 0 34px oklch(70% 0.2 250 / 0.3)" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="oklch(78% 0.2 250)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
        </div>
        <div>
          <div style={{ fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 16, color: "#fff", marginBottom: 8 }}>Monitoramento de Prazos</div>
          <div style={{ fontSize: 12.5, color: "oklch(70% 0.02 270)", lineHeight: 1.55 }}>Tramitação, Exigências e Deferimentos com Alertas em cada etapa.</div>
        </div>
      </div>
    </div>
  );

  const marqueeWrap = (
    <div className="atos-marquee-wrap" style={{ position: "relative", zIndex: 1, flexShrink: 0, marginTop: 14, overflow: "hidden", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 12 }}>
      <div style={{ display: "flex", gap: 40, whiteSpace: "nowrap", animation: "atosMarquee 22s linear infinite", fontSize: 12, color: "oklch(60% 0.02 270)", letterSpacing: "0.04em" }}>
        {["JUCESP", "JUCERJA", "JUCEMG", "JUCEPAR", "JUCERGS", "JUCEB", "JUCESP", "JUCERJA", "JUCEMG", "JUCEPAR", "JUCERGS", "JUCEB"].map((n, i) => <span key={i}>{n}</span>)}
      </div>
    </div>
  );

  const loginDecorGlow = (
    <div style={{ position: "absolute", top: "-10%", right: "-20%", width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, oklch(65% 0.22 255 / 0.14), transparent 70%)" }} />
  );

  const loginFormCard = (
    <div className="atos-login-card-anim" style={{ position: "relative", width: "100%", maxWidth: 320, borderRadius: 22, background: "rgba(255,255,255,0.035)", border: "1px solid rgba(255,255,255,0.09)", padding: "32px 28px", boxShadow: "0 0 40px oklch(65% 0.22 255 / 0.1), 0 20px 50px rgba(0,0,0,0.4)" }}>
      <div style={{ fontFamily: FONTE_TITULO, fontSize: 21, fontWeight: 700, color: "#fff", marginBottom: 6 }}>Acessar plataforma</div>
      <div style={{ fontSize: 13, color: "oklch(70% 0.02 270)", marginBottom: 30 }}>{subtitulo || "Entre com sua conta"}</div>
      {erro && <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}
      {aviso && <div style={{ background: "rgba(0,255,170,0.12)", color: "#7dffce", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{aviso}</div>}
      {etapa === 1 && (<>
        <label style={campoLabel}>Login</label>
        <input style={campoInput} value={login} onChange={e => onChangeLogin(e.target.value)} onKeyDown={e => e.key === "Enter" && onEntrar()} />
        <label style={campoLabel}>Senha</label>
        <input style={campoInput} type="password" value={senha} onChange={e => onChangeSenha(e.target.value)} onKeyDown={e => e.key === "Enter" && onEntrar()} />
        <button style={campoBtn} onClick={onEntrar} disabled={carregando}>{carregando ? "Aguarde..." : "Entrar"}</button>
        <div style={{ textAlign: "center", marginTop: 14 }}>
          <button
            onClick={() => { setModoEsqueci(m => !m); setStatusEsqueci(""); setLoginEsqueci(""); }}
            style={{ background: "none", border: "none", color: "oklch(70% 0.05 250)", fontSize: 12.5, cursor: "pointer", textDecoration: "underline", fontFamily: FONTE_CORPO, padding: 0 }}>
            Esqueci minha senha
          </button>
        </div>
        {modoEsqueci && (
          <div style={{ marginTop: 14, padding: 14, borderRadius: 10, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}>
            {statusEsqueci === "enviado" ? (
              <div style={{ fontSize: 12.5, color: "oklch(78% 0.15 160)", lineHeight: 1.5 }}>Se o login existir, enviamos um link de redefinição de senha para o e-mail cadastrado.</div>
            ) : (<>
              <label style={campoLabel}>Seu login</label>
              <input style={{ ...campoInput, marginBottom: 10 }} value={loginEsqueci} onChange={e => setLoginEsqueci(e.target.value)} onKeyDown={e => e.key === "Enter" && enviarEsqueciSenha()} />
              <button style={{ ...campoBtn, padding: 10, fontSize: 13 }} onClick={enviarEsqueciSenha} disabled={statusEsqueci === "enviando" || !loginEsqueci}>
                {statusEsqueci === "enviando" ? "Enviando..." : "Enviar link de redefinição"}
              </button>
            </>)}
          </div>
        )}
        <a href="mailto:contato@atos.net.br?subject=Solicita%C3%A7%C3%A3o%20de%20acesso%20%E2%80%94%20ATOS"
          style={{ display: "block", textAlign: "center", fontSize: 12.5, color: "oklch(70% 0.02 270)", textDecoration: "none", fontFamily: FONTE_CORPO, marginTop: 16 }}>
          Solicitar acesso
        </a>
      </>)}
      {etapa === 2 && (<>
        <div style={{ fontSize: 13, color: "oklch(70% 0.02 270)", marginBottom: 12 }}>Enviamos um código para o seu e-mail. Digite-o abaixo para entrar.</div>
        <label style={campoLabel}>Código de acesso</label>
        <input style={{ ...campoInput, fontSize: 18, letterSpacing: 4, textAlign: "center" }} value={codigo} onChange={e => onChangeCodigo(e.target.value)} onKeyDown={e => e.key === "Enter" && onVerificarCodigo()} maxLength={6} />
        <button style={campoBtn} onClick={onVerificarCodigo} disabled={carregando}>{carregando ? "Aguarde..." : "Verificar código"}</button>
        <button style={{ ...campoBtn, background: "transparent", color: "oklch(70% 0.02 270)", boxShadow: "none", marginTop: 8 }} onClick={onVoltarEtapa}>Voltar</button>
      </>)}
    </div>
  );

  if (mobile) {
    // Ordem exigida no mobile: logo -> headline -> LOGIN (centralizado) ->
    // cards informativos. E' um fluxo vertical proprio (nao o mesmo par
    // "coluna marketing / coluna login" do desktop com order trocado) porque
    // o login precisa entrar ENTRE a headline e os cards, nao so' antes/depois
    // do bloco inteiro.
    return (
      <div style={{ minHeight: "100vh", color: "#e4e4e7", WebkitFontSmoothing: "antialiased", fontFamily: FONTE_CORPO, position: "relative", overflow: "hidden", background: "linear-gradient(165deg, #0a0e2e 0%, #060810 60%)" }}>
        <style>{KEYFRAMES_LANDING}</style>
        {glows}
        <div style={{ position: "relative", zIndex: 1, padding: "28px 20px 0" }}>
          {logoBlock}
          {headline}
        </div>
        <div style={{ position: "relative", zIndex: 1, overflow: "hidden", background: "#0b0b0f", borderTop: "1px solid rgba(255,255,255,0.06)", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 20px", margin: "24px 0 0" }}>
          {loginDecorGlow}
          {loginFormCard}
        </div>
        <div style={{ position: "relative", zIndex: 1, padding: "24px 20px 28px" }}>
          {tilesGrid}
          {marqueeWrap}
        </div>
      </div>
    );
  }

  // Desktop - layout original, inalterado: coluna marketing (flex 1.3) a
  // esquerda, coluna de login (440px) a direita, lado a lado.
  return (
    <div style={{ display: "flex", flexDirection: "row", minHeight: "100vh", color: "#e4e4e7", WebkitFontSmoothing: "antialiased", fontFamily: FONTE_CORPO }}>
      <style>{KEYFRAMES_LANDING}</style>
      <div style={{ flex: 1.3, position: "relative", overflow: "hidden", background: "linear-gradient(165deg, #0a0e2e 0%, #060810 60%)", padding: "40px 56px", display: "flex", flexDirection: "column" }}>
        {glows}
        {logoBlock}
        {headline}
        {tilesGrid}
        {marqueeWrap}
      </div>
      <div style={{ width: 440, background: "#0b0b0f", borderLeft: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", padding: 40, position: "relative", overflow: "hidden", boxSizing: "border-box" }}>
        {loginDecorGlow}
        {loginFormCard}
      </div>
    </div>
  );
}

// Tela "Criar Acesso" (primeiro acesso via link do e-mail de boas-vindas) -
// replica fielmente docs/criar_acesso_v1.html. Renderizada por Cliente.js
// quando ha' ?grupo=CODIGO na URL (ver Cliente(), ehCadastro).
export function TelaCriarAcesso({ codigoGrupo, login, senha, erro, aviso, carregando, onChangeLogin, onChangeSenha, onCadastrar }) {
  const campoLabel = { fontSize: 12, color: "#a8b0d8", marginBottom: 6, display: "block", fontWeight: 600 };
  const campoInput = { width: "100%", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: "12px 14px", color: "#fff", fontSize: 13.5, marginBottom: 18, fontFamily: FONTE_CORPO, outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ background: "#060608", color: "#e4e4e7", fontFamily: FONTE_CORPO, minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden", WebkitFontSmoothing: "antialiased" }}>
      <div style={{ position: "absolute", top: -120, left: "10%", width: 420, height: 420, background: "radial-gradient(circle, #4d94ff35 0%, transparent 70%)", filter: "blur(50px)", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: -120, right: "12%", width: 420, height: 420, background: "radial-gradient(circle, #8c5aff30 0%, transparent 70%)", filter: "blur(50px)", pointerEvents: "none" }} />
      <div style={{ width: "100%", maxWidth: 400, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 22, padding: "40px 36px", zIndex: 1, boxShadow: "0 0 60px rgba(77,148,255,0.08)", boxSizing: "border-box" }}>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: 24, fontWeight: 700, color: "#fff", textAlign: "center", marginBottom: 4 }}>atos<span style={{ color: "#6db2ff", textShadow: "0 0 16px #4d94ff" }}>.</span></div>
        <div style={{ fontSize: 13, color: "#9aa8d8", textAlign: "center", marginBottom: 24 }}>Crie seu login e senha</div>
        {erro && <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}
        {aviso && <div style={{ background: "rgba(0,255,170,0.12)", color: "#7dffce", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{aviso}</div>}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 7, fontSize: 12.5, color: "#8ec2ff", background: "rgba(77,148,255,0.08)", border: "1px solid rgba(77,148,255,0.25)", borderRadius: 10, padding: "10px 16px", marginBottom: 28 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4d94ff", boxShadow: "0 0 6px #4d94ff" }} />
          Cadastro para o grupo: <b style={{ color: "#fff" }}>{codigoGrupo}</b>
        </div>
        <label style={campoLabel}>Login</label>
        <input style={campoInput} value={login} onChange={e => onChangeLogin(e.target.value)} placeholder="Escolha seu login" onKeyDown={e => e.key === "Enter" && onCadastrar()} />
        <label style={campoLabel}>Senha</label>
        <input style={campoInput} type="password" value={senha} onChange={e => onChangeSenha(e.target.value)} placeholder="Crie uma senha segura" onKeyDown={e => e.key === "Enter" && onCadastrar()} />
        <button style={{ width: "100%", background: "linear-gradient(135deg, #4d94ff, #8c5aff)", border: "none", borderRadius: 10, padding: 14, color: "#fff", fontSize: 14, fontWeight: 600, boxShadow: "0 4px 20px rgba(77,148,255,0.3)", cursor: carregando ? "default" : "pointer", fontFamily: FONTE_CORPO }} onClick={onCadastrar} disabled={carregando}>
          {carregando ? "Aguarde..." : "Cadastrar"}
        </button>
      </div>
    </div>
  );
}

// Painel de download por status (tela "Ver processo") - exatamente UM bloco
// visivel por vez, conforme docs/ver_processo_cliente_*.html:
// aberto -> nada (nao renderiza); tramitacao -> Protocolo (+ download se
// arquivo_protocolo existir); exigencia -> Exigência (+ download se
// arquivo_exigencia existir); deferido -> "Aguardando Liberação", sem botao;
// finalizado -> "Registro Finalizado" com download sempre (arquivo_registro
// e' o que define o status finalizado, ver recalcular_status no backend).
export function PainelDownloadStatus({ processo, onBaixar }) {
  const status = (processo.status || "").toLowerCase();
  const cores = {
    tramitacao: { bg: "rgba(0,212,255,0.06)", borda: "rgba(0,212,255,0.3)", iconeBg: "rgba(0,212,255,0.15)", cor: "#00d4ff", grad: "linear-gradient(135deg, #00d4ff, #4d94ff)", sombra: "rgba(0,212,255,0.3)" },
    exigencia: { bg: "rgba(255,77,77,0.06)", borda: "rgba(255,77,77,0.3)", iconeBg: "rgba(255,77,77,0.15)", cor: "#ff4d4d", grad: "linear-gradient(135deg, #ff4d4d, #ff9f0a)", sombra: "rgba(255,77,77,0.3)" },
    deferido: { bg: "rgba(255,255,255,0.03)", borda: "rgba(255,255,255,0.1)", iconeBg: "rgba(255,255,255,0.06)", cor: "#8a90b8" },
    finalizado: { bg: "rgba(0,255,170,0.06)", borda: "rgba(0,255,170,0.3)", iconeBg: "rgba(0,255,170,0.15)", cor: "#00ffaa", grad: "linear-gradient(135deg, #00ffaa, #00e691)", sombra: "rgba(0,255,170,0.3)", textoBtn: "#0a0e14" },
  };
  if (status === "aberto" || status === "recebido" || !cores[status === "aprovado" ? "deferido" : status]) return null;
  const c = cores[status === "aprovado" ? "deferido" : status];

  let titulo, sub, tipo, temArquivo, textoBtn, icone;
  if (status === "tramitacao") {
    titulo = "Protocolo"; sub = processo.numero_protocolo || null; tipo = "protocolo";
    temArquivo = !!processo.arquivo_protocolo; textoBtn = "Baixar protocolo";
    icone = <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c.cor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" /></svg>;
  } else if (status === "exigencia") {
    titulo = "Exigência"; sub = null; tipo = "exigencia";
    temArquivo = !!processo.arquivo_exigencia; textoBtn = "Baixar exigência";
    icone = <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c.cor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" /></svg>;
  } else if (status === "deferido") {
    titulo = "Aguardando Liberação"; sub = "Aguardando a Junta Comercial disponibilizar o registro"; tipo = null;
    temArquivo = false; textoBtn = null;
    icone = <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c.cor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>;
  } else if (status === "finalizado") {
    titulo = "Registro Finalizado"; sub = null; tipo = "registro";
    temArquivo = true; textoBtn = "Baixar registro";
    icone = <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c.cor} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><path d="M22 4 12 14.01l-3-3" /></svg>;
  }

  return (
    <div style={{ borderRadius: 16, padding: "20px 24px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12, background: c.bg, border: `1px solid ${c.borda}`, fontFamily: FONTE_CORPO }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ width: 42, height: 42, borderRadius: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, background: c.iconeBg }}>{icone}</div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: "#fff", marginBottom: 2 }}>{titulo}</div>
          {sub && <div style={{ fontSize: 11.5, color: "#8a90b8" }}>{sub}</div>}
        </div>
      </div>
      {tipo && temArquivo ? (
        <button onClick={() => onBaixar(tipo)} style={{ display: "inline-flex", alignItems: "center", gap: 7, border: "none", color: c.textoBtn || "#fff", padding: "10px 18px", borderRadius: 9, fontSize: 12.5, fontWeight: 500, whiteSpace: "nowrap", background: c.grad, boxShadow: `0 4px 14px ${c.sombra}`, cursor: "pointer" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" /></svg>
          {textoBtn}
        </button>
      ) : status === "deferido" ? (
        <button disabled style={{ background: "rgba(255,255,255,0.06)", color: "#62666d", border: "none", padding: "10px 18px", borderRadius: 9, fontSize: 12.5, fontWeight: 500, whiteSpace: "nowrap" }}>Ainda não disponível</button>
      ) : null}
    </div>
  );
}
