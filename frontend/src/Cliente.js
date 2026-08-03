import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { STATUS_CONFIG, formatarDataExtenso, FluxoDoDiaCardEscuro, AtividadeRecenteEscura, BotaoIatos, IatosChat, subtituloProcesso, SidebarAtos, IconeProcessos, IconeRelatorios, DonutStatusCard, TelaLogin, TelaCriarAcesso, PainelDownloadStatus, FONTE_CORPO, FONTE_TITULO } from "./components/Compartilhados";

const API = "";

function abreviarAto(texto, data) {
  const t = (texto || "").toUpperCase();
  const d = data ? ` ${(data || "").replace(/\//g, ".")}` : "";
  let m = t.match(/(\d+)\s*[ªº°]?\s*ALTERA[ÇC][ÃA]O\s+CONTRATUAL/);
  if (m) return `${m[1]}ª ALTERAÇÃO`;
  m = t.match(/ADITAMENTO.*?(\d+)\s*[ªº°]?\s*EMISS[ÃA]O\s+DE\s+DEB[ÊE]NTURES/);
  if (m) return `Aditamento ${m[1]}ª Emissão`;
  m = t.match(/(\d+)\s*[ªº°]?\s*\(?[A-ZÀ-Ú]*\)?\s*EMISS[ÃA]O\s+DE\s+DEB[ÊE]NTURES/);
  if (m) return `${m[1]}ª EMISSÃO DE DEBÊNTURES${d}`;
  if (t.includes("DEBENTURISTAS")) return `AGD${d}`;
  if (t.includes("ORDIN") && t.includes("EXTRAORDIN")) return `AGOE${d}`;
  if (t.includes("EXTRAORDIN")) return `AGE${d}`;
  if (t.includes("ORDIN") && t.includes("ASSEMBLEIA")) return `AGO${d}`;
  if (t.includes("REUNI") && (t.includes("SÓCIOS") || t.includes("SOCIOS"))) return `ARS${d}`;
  if (t.includes("CONSELHO DE ADMINISTRA")) return `RCA${d}`;
  const curto = (texto || "").length > 38 ? (texto || "").slice(0, 38) + "…" : (texto || "—");
  return curto;
}

export default function Cliente() {
  const [params] = useSearchParams();
  const codigoGrupo = params.get("grupo") || "";
  const modo = codigoGrupo ? "cadastro" : "login"; // nunca muda em runtime (setModo nunca era chamado) - simplificado de useState pra constante derivada
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [etapa, setEtapa] = useState(1);
  const [codigo, setCodigo] = useState("");
  const [sessao, setSessao] = useState(() => {
    try { const s = localStorage.getItem("mane_sessao"); return s ? JSON.parse(s) : null; } catch { return null; }
  });

  function salvarSessao(d) { try { localStorage.setItem("mane_sessao", JSON.stringify(d)); } catch {} setSessao(d); }
  function limparSessao() { try { localStorage.removeItem("mane_sessao"); } catch {} setSessao(null); setSenha(""); }

  async function cadastrar() {
    setErro(""); setAviso("");
    if (!login || !senha) { setErro("Preencha login e senha."); return; }
    if (senha.length < 6) { setErro("A senha deve ter pelo menos 6 caracteres."); return; }
    setCarregando(true);
    try {
      await axios.post(`${API}/cadastro`, { codigo_grupo: codigoGrupo, login, senha });
            const resLogin = await axios.post(`${API}/login`, { login, senha });
      if (resLogin.data && resLogin.data.requer_2fa) { setEtapa(2); setCarregando(false); return; }
      salvarSessao(resLogin.data);
    } catch (e) {
      const dd = e.response && e.response.data && e.response.data.detail;
      setErro(dd ? dd : "Erro ao cadastrar.");
    }
    setCarregando(false);
  }

  async function entrar() {
    setErro(""); setAviso("");
    if (!login || !senha) { setErro("Preencha login e senha."); return; }
    setCarregando(true);
    try {
      const res = await axios.post(`${API}/login`, { login, senha });
      if (res.data && res.data.requer_2fa) { setEtapa(2); setCarregando(false); return; }
      salvarSessao(res.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Login ou senha inválidos.");
      else setErro("Erro ao conectar.");
    }
    setCarregando(false);
  }

  async function verificarCodigo() {
    setErro(""); setAviso("");
    if (!codigo) { setErro("Digite o codigo recebido por e-mail."); return; }
    setCarregando(true);
    try {
      const res = await axios.post(`${API}/login/verificar`, { login, codigo });
      salvarSessao(res.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Codigo invalido ou expirado.");
      else setErro("Erro ao conectar.");
    }
    setCarregando(false);
  }
  if (sessao) return <Painel sessao={sessao} onSair={limparSessao} />;

  const ehCadastro = modo === "cadastro";
  if (ehCadastro) {
    return (
      <TelaCriarAcesso
        codigoGrupo={codigoGrupo}
        login={login} senha={senha}
        erro={erro} aviso={aviso} carregando={carregando}
        onChangeLogin={setLogin} onChangeSenha={setSenha}
        onCadastrar={cadastrar}
      />
    );
  }
  return (
    <TelaLogin
      subtitulo="Área do cliente"
      erro={erro} aviso={aviso} etapa={etapa} carregando={carregando}
      login={login} senha={senha} codigo={codigo}
      onChangeLogin={setLogin} onChangeSenha={setSenha} onChangeCodigo={setCodigo}
      onEntrar={entrar} onVerificarCodigo={verificarCodigo}
      onVoltarEtapa={() => { setEtapa(1); setCodigo(""); setErro(""); }}
    />
  );
}

function ChatProcessoCliente({ processoId, token }) {
  const [aberto, setAberto] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  async function carregarMsgs() {
    try { const r = await axios.get(`${API}/processos/${processoId}/mensagens`, { headers: { "x-token": token } }); setMsgs(r.data || []); } catch (e) {}
  }
  useEffect(() => {
    if (!aberto) return;
    carregarMsgs();
    const _t = setInterval(carregarMsgs, 5000);
    return () => clearInterval(_t);
    /* eslint-disable-next-line */
  }, [aberto]);
  async function enviar() {
    const t = texto.trim();
    if (!t) return;
    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("dados", JSON.stringify({ texto: t }));
      await axios.post(`${API}/processos/${processoId}/mensagens`, fd, { headers: { "x-token": token, "Content-Type": "multipart/form-data" } });
      setTexto("");
      await carregarMsgs();
    } catch (e) { alert("Nao foi possivel enviar a mensagem."); }
    setEnviando(false);
  }
  return (
    <div style={{ marginTop: 16, marginBottom: 8 }}>
      <button onClick={() => setAberto(a => !a)}
        style={{ width: "100%", textAlign: "left", background: "#eff6ff", border: "0.5px solid #bfdbfe", borderRadius: 10, padding: "12px 16px", cursor: "pointer", fontSize: 14, fontWeight: 600, color: "#1e40af", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>Duvidas sobre o Processo?</span>
        <span style={{ fontSize: 12, fontWeight: 400, color: "#2563eb" }}>{aberto ? "fechar ▲" : `abrir ▼${msgs.length ? ` (${msgs.length})` : ""}`}</span>
      </button>
      {aberto && (
        <div style={{ border: "0.5px solid #e2e8f0", borderTop: "none", borderRadius: "0 0 10px 10px", padding: 14, background: "#fff" }}>
          <div style={{ maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
            {msgs.length === 0 ? (
              <div style={{ fontSize: 13, color: "#94a3b8", textAlign: "center", padding: 12 }}>Nenhuma mensagem ainda. Escreva a primeira.</div>
            ) : msgs.map(mm => {
              const meu = mm.autor_tipo === "cliente";
              return (
                <div key={mm.id} style={{ alignSelf: meu ? "flex-end" : "flex-start", maxWidth: "80%", background: meu ? "#dbeafe" : "#f1f5f9", borderRadius: 10, padding: "8px 12px" }}>
                  <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>
                    {mm.autor_tipo === "admin" ? "Equipe Atos" : mm.autor_login}{mm.criado_em ? ` · ${new Date(mm.criado_em).toLocaleString("pt-BR")}` : ""}
                  </div>
                  <div style={{ fontSize: 13, color: "#23282a", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{mm.texto}</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <textarea value={texto} onChange={e => setTexto(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }}
              placeholder="Escreva sua mensagem..."
              style={{ flex: 1, minHeight: 40, maxHeight: 120, padding: "8px 12px", border: "0.5px solid #e2e8f0", borderRadius: 8, fontSize: 13, outline: "none", resize: "vertical", fontFamily: "sans-serif" }} />
            <button onClick={enviar} disabled={enviando}
              style={{ background: "#1e40af", color: "#fff", border: "none", padding: "10px 18px", borderRadius: 8, fontSize: 13, cursor: "pointer", height: 40 }}>
              {enviando ? "..." : "Enviar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DetalheProcessoCliente({ p, sessao, onVoltar }) {
  const [anexos, setAnexos] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [iatosAberto, setIatosAberto] = useState(false);

  async function carregarAnexos() {
    try {
      const r = await axios.get(API + "/processos/" + p.id + "/anexos", { headers: { "x-token": sessao.token } });
      setAnexos(r.data || []);
    } catch (e) { /* silencioso */ }
  }
  useEffect(() => { carregarAnexos(); /* eslint-disable-next-line */ }, []);

  async function enviarAnexo(arquivo) {
    if (!arquivo) return;
    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("arquivo", arquivo);
      await axios.post(API + "/processos/" + p.id + "/anexos", fd, { headers: { "x-token": sessao.token, "Content-Type": "multipart/form-data" } });
      await carregarAnexos();
    } catch (e) { alert("Nao foi possivel enviar o anexo."); }
    setEnviando(false);
  }

  async function baixarAnexo(anexoId, nome) {
    try {
      const res = await axios.get(API + "/anexos/" + anexoId + "/download", { headers: { "x-token": sessao.token }, responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = nome || "anexo";
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) { alert("Nao foi possivel baixar o anexo."); }
  }

  async function baixarDocumento(tipo) {
    try {
      const res = await axios.get(API + "/download/" + p.id + "/" + tipo, { headers: { "x-token": sessao.token }, responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = (p.empresa || tipo).replace(/[^a-zA-Z0-9]/g, "_") + "_" + tipo + ".pdf";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert("Nao foi possivel baixar o documento."); }
  }

  const statusAtual = (p.status === "aprovado") ? "deferido" : (p.status === "recebido" ? "aberto" : p.status);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <button onClick={onVoltar} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#d4d4d8", padding: "8px 16px", borderRadius: 8, fontSize: 12.5, display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontFamily: FONTE_CORPO }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
          Voltar
        </button>
        <BotaoIatos processo={p} onAbrir={() => setIatosAberto(true)} />
      </div>
      {iatosAberto && <IatosChat processo={p} token={sessao.token} onFechar={() => setIatosAberto(false)} />}

      <div style={{ background: "radial-gradient(circle at 8% 0%, #1a1470 0%, #0e0e14 55%)", border: "1px solid rgba(140,90,255,0.35)", borderRadius: 20, padding: "24px 28px", marginBottom: 16 }}>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 4 }}>{p.empresa}</div>
        <div style={{ fontSize: 12, color: "#8a90b8" }}>CNPJ {p.cnpj} · NIRE {p.nire}</div>
        <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
          {["aberto", "tramitacao", "exigencia", "deferido", "finalizado"].map((key) => {
            const ativo = statusAtual === key;
            return (
              <span key={key} style={{
                padding: "7px 16px", borderRadius: 20, fontSize: 12,
                border: ativo ? "1px solid rgba(255,159,10,0.4)" : "1px solid rgba(255,255,255,0.1)",
                background: ativo ? "rgba(255,159,10,0.15)" : "transparent",
                color: ativo ? "#ff9f0a" : "#71717a",
                boxShadow: ativo ? "0 0 14px rgba(255,159,10,0.15)" : "none",
              }}>
                {STATUS_CONFIG[key] ? STATUS_CONFIG[key].label : key}
              </span>
            );
          })}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 18, padding: "26px 28px", marginBottom: 16 }}>
        <div>
          <div style={{ marginBottom: 20 }}><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Tipo de ato</div><div style={{ fontSize: 14, color: "#e4e4e7", fontWeight: 500 }}>{p.tipo_ato}</div></div>
          <div style={{ marginBottom: 20 }}><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Data do ato</div><div style={{ fontSize: 14, color: "#e4e4e7", fontWeight: 500 }}>{p.data_ata}{p.hora_ata ? " — " + p.hora_ata : ""}</div></div>
          <div><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Recebido em</div><div style={{ fontSize: 14, color: "#e4e4e7", fontWeight: 500 }}>{p.data_recebimento ? new Date(p.data_recebimento).toLocaleDateString("pt-BR") : "-"}</div></div>
        </div>
        <div>
          <div style={{ marginBottom: 20 }}><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Identificador</div><div style={{ fontSize: 14, color: "#e4e4e7", fontWeight: 500 }}>{p.identificador_ato}</div></div>
          <div style={{ marginBottom: 20 }}><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Protocolo</div><div style={{ fontSize: 14, color: p.numero_protocolo ? "#e4e4e7" : "#71717a", fontWeight: 500 }}>{p.numero_protocolo || "—"}</div></div>
          <div><div style={{ fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Processo criado em</div><div style={{ fontSize: 14, color: "#e4e4e7", fontWeight: 500 }}>{p.criado_em ? new Date(p.criado_em).toLocaleString("pt-BR") : "-"}</div></div>
        </div>
      </div>

      <PainelDownloadStatus processo={p} onBaixar={baixarDocumento} />

      <div style={{ background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 18, padding: "24px 28px" }}>
        <div style={{ fontSize: 13, color: "#a8b0d8", marginBottom: 14, fontWeight: 500 }}>Anexos</div>
        {anexos.length === 0 ? (
          <div style={{ fontSize: 12.5, color: "#62666d", marginBottom: 16 }}>Nenhum anexo enviado ainda.</div>
        ) : (
          <div style={{ marginBottom: 16 }}>
            {anexos.map(a => (
              <div key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ fontSize: 13, color: "#d4d4d8" }}>{a.nome_original}</span>
                <button onClick={() => baixarAnexo(a.id, a.nome_original)}
                  style={{ background: "transparent", border: "1px solid rgba(77,148,255,0.4)", color: "#8ec2ff", borderRadius: 6, padding: "4px 10px", fontSize: 12, cursor: "pointer", fontFamily: FONTE_CORPO }}>
                  Baixar
                </button>
              </div>
            ))}
          </div>
        )}
        <label style={{ cursor: enviando ? "default" : "pointer" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 18px", background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", borderRadius: 9, fontSize: 13, fontWeight: 500, fontFamily: FONTE_CORPO, boxShadow: "0 4px 16px rgba(77,148,255,0.3)", opacity: enviando ? 0.6 : 1 }}>
            {enviando ? "Enviando..." : "Anexar arquivo"}
          </span>
          <input type="file" style={{ display: "none" }} disabled={enviando} onChange={e => enviarAnexo(e.target.files[0])} />
        </label>
      </div>
    </div>
  );
}
export function Painel({ sessao, onSair }) {
  const [processos, setProcessos] = useState([]);
  const [metricas, setMetricas] = useState({});
  const [fluxoAtivo, setFluxoAtivo] = useState(null);
  const [eventosRecentes, setEventosRecentes] = useState([]);
  const [processoSelecionado, setProcessoSelecionado] = useState(null);
  const [iatosAberto, setIatosAberto] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [exigenciaAberta, setExigenciaAberta] = useState(null);
  const [docsAbertos, setDocsAbertos] = useState(null);
  const [subindo, setSubindo] = useState(false);
  const [progresso, setProgresso] = useState({ feitos: 0, total: 0, erros: 0 });
  const [tela, setTela] = useState("processos");
  const [fBusca, setFBusca] = useState("");
  const [fUf, setFUf] = useState("");
  const [fAto, setFAto] = useState("");
  const [fStatus, setFStatus] = useState("");
  // Precisa viver aqui (no componente estavel Painel), nao dentro de
  // ListaProcessosAgrupada: essa funcao e recriada a cada render de Painel()
  // (esta definida no corpo dele), entao um useState local nela reiniciava
  // pra {} (tudo aberto) a cada atualizacao de estado do componente pai -
  // era por isso que uma secao recolhida "voltava a abrir sozinha".
  const [gruposFechados, setGruposFechados] = useState({});
  const ufsDisponiveis = [...new Set(processos.map(p => p.uf).filter(Boolean))].sort();
  const atosDisponiveis = [...new Set(processos.map(p => abreviarAto(p.identificador_ato, "").split(" ")[0]).filter(Boolean))].sort();
  const processosFiltrados = processos.filter(p => {
    if (fBusca && !(p.empresa || "").toLowerCase().includes(fBusca.toLowerCase())) return false;
    if (fUf && p.uf !== fUf) return false;
    if (fStatus) {
      const sin = { aberto: ["aberto","recebido"], deferido: ["deferido","aprovado"] };
      const aceitos = sin[fStatus] || [fStatus];
      if (!aceitos.includes((p.status || "").toLowerCase())) return false;
    }
    if (fAto && abreviarAto(p.identificador_ato, "").split(" ")[0] !== fAto) return false;
    return true;
  });
  const s = estilos();
  useEffect(() => { carregar(); }, []);

  useEffect(() => {
    async function carregarFluxo() {
      try {
        const r = await axios.get(`${API}/fluxo/ativo`, { headers: { "x-token": sessao.token } });
        setFluxoAtivo(r.data || null);
      } catch (e) {}
    }
    carregarFluxo();
    const _t = setInterval(carregarFluxo, 5000);
    return () => clearInterval(_t);
    /* eslint-disable-next-line */
  }, []);

  useEffect(() => {
    async function carregarEventos() {
      try {
        const r = await axios.get(`${API}/eventos/recentes`, { headers: { "x-token": sessao.token }, params: { limit: 5 } });
        setEventosRecentes(r.data || []);
      } catch (e) {}
    }
    carregarEventos();
    const _t = setInterval(carregarEventos, 5000);
    return () => clearInterval(_t);
    /* eslint-disable-next-line */
  }, []);
  async function carregar() {
    setCarregando(true); setErro("");
    let listaAtualizada = null;
    try {
      const res = await axios.get(`${API}/processos`, { headers: { "x-token": sessao.token } });
      setProcessos(res.data);
      listaAtualizada = res.data;
      const m = await axios.get(API + "/metricas", { headers: { "x-token": sessao.token } });
      setMetricas(m.data);
    } catch (e) {
      if (e.response && e.response.status === 401) { onSair(); return; }
      setErro("Erro ao carregar processos.");
    }
    setCarregando(false);
    return listaAtualizada;
  }
  async function baixar(processoId, tipo, nomeBase) {
    try {
      const res = await axios.get(`${API}/download/${processoId}/${tipo}`, {
        headers: { "x-token": sessao.token }, responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = `${nomeBase}_${tipo}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert("Nao foi possivel baixar este arquivo."); }
  }
  async function baixarRelatorio(status) {
    try {
      const res = await axios.get(`${API}/relatorio?status=${status}`, {
        headers: { "x-token": sessao.token }, responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = `relatorio_${status}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert("Nao foi possivel gerar o relatorio."); }
  }
  function agruparPorPasta(arquivos) {
    const grupos = {};
    for (const f of arquivos) {
      const rel = f.webkitRelativePath || f._relPath || f.name;
      const partes = rel.split("/");
      partes.pop();
      const chave = partes.join("/") || "(raiz)";
      if (!grupos[chave]) grupos[chave] = [];
      grupos[chave].push(f);
    }
    return grupos;
  }

  async function processarGrupoPasta(arquivos, extras) {
    extras = extras || [];
    const fdA = new FormData();
    arquivos.forEach(a => fdA.append("arquivos", a));
    const res = await axios.post(`${API}/processos/analisar-pasta-multi`, fdA, { headers: { "x-token": sessao.token } });
    const r = res.data || {};
    const principais = r.principais || [];
    const anexosGrupo = (r.anexos || []).map(ax => arquivos[ax.indice]).concat(extras);
    let criados = 0, anexosOk = 0, anexosErro = 0;
    for (const principal of principais) {
      const dados = principal.dados || {};
      if (!principal.tipo_sugerido) {
        const ok = window.confirm("AVISO\n\nDocumento Sem Valor Societario!\n\nPossivel Anexo ou Documento Complementar!\n\n(" + principal.nome + ")\n\nDeseja Seguir Com a Insercao?");
        if (!ok) { continue; }
        dados.uf = "";
        if (!dados.empresa) { dados.empresa = "Documento desconhecido"; dados.identificador_ato = "Documento desconhecido - " + (sessao.login || sessao.usuario || ""); }
      }
      if (r.confirmacao_pendente) { dados.confirmacao_pendente = true; dados.tipo_ato_sugerido = principal.tipo_sugerido || ""; }
      const segueDup = await checarDup(dados);
      if (!segueDup) { continue; }
      const fd2 = new FormData();
      fd2.append("arquivo", arquivos[principal.indice]);
      fd2.append("dados", JSON.stringify(dados));
      const criado = await axios.post(`${API}/processos`, fd2, { headers: { "x-token": sessao.token } });
      const novoId = criado.data && (criado.data.id || criado.data.processo_id);
      criados++;
      if (novoId) {
        for (const arqAnexo of anexosGrupo) {
          try {
            const fda = new FormData();
            fda.append("arquivo", arqAnexo);
            fda.append("descricao", "");
            await axios.post(`${API}/processos/${novoId}/anexos`, fda, { headers: { "x-token": sessao.token } });
            anexosOk++;
          } catch (e) { anexosErro++; }
        }
      }
    }
    return { criados, anexosOk, anexosErro };
  }

  async function processarPasta(fileList) {
    const arquivos = Array.from(fileList).filter(f => {
      const n = f.name.toLowerCase();
      return n.endsWith(".pdf") || n.endsWith(".docx") || n.endsWith(".png") || n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".xml") || n.endsWith(".txt");
    });
    if (arquivos.length === 0) { alert("Nenhum arquivo valido na pasta."); return; }
    if (arquivos.length === 1) { return processarArquivos(fileList); }
    const grupos = agruparPorPasta(arquivos);
    let chaves = Object.keys(grupos);
    let extrasDaRaiz = [];
    const temSubpastas = chaves.some(k => k !== "(raiz)");
    if (temSubpastas && grupos["(raiz)"]) {
      const raizArquivos = grupos["(raiz)"];
      try {
        const fdR = new FormData();
        raizArquivos.forEach(a => fdR.append("arquivos", a));
        const resR = await axios.post(`${API}/processos/analisar-pasta-multi`, fdR, { headers: { "x-token": sessao.token } });
        const rR = resR.data || {};
        const principaisRaiz = rR.principais || [];
        const anexosRaiz = rR.anexos || [];
        extrasDaRaiz = anexosRaiz.map(ax => raizArquivos[ax.indice]);
        if (principaisRaiz.length > 0) {
          grupos["(raiz-principal)"] = principaisRaiz.map(pr => raizArquivos[pr.indice]);
        }
      } catch (e) {
        extrasDaRaiz = grupos["(raiz)"];
      }
      delete grupos["(raiz)"];
      chaves = Object.keys(grupos);
    }
    setSubindo(true);
    setProgresso({ feitos: 0, total: chaves.length, erros: 0 });
    let totalCriados = 0, totalAnexosOk = 0, totalAnexosErro = 0, gruposErro = 0;
    for (let i = 0; i < chaves.length; i++) {
      try {
        const extras = chaves[i] === "(raiz-principal)" ? [] : extrasDaRaiz;
        const res = await processarGrupoPasta(grupos[chaves[i]], extras);
        totalCriados += res.criados;
        totalAnexosOk += res.anexosOk;
        totalAnexosErro += res.anexosErro;
      } catch (e) {
        gruposErro++;
      }
      setProgresso({ feitos: i + 1, total: chaves.length, erros: gruposErro });
    }
    setSubindo(false);
    await carregar();
    alert(`Concluido: ${totalCriados} processo(s) criado(s) em ${chaves.length} pasta(s). Anexos: ${totalAnexosOk}${totalAnexosErro ? ` (${totalAnexosErro} falharam)` : ""}.${gruposErro ? ` ${gruposErro} pasta(s) com erro.` : ""}`);
  }
  async function checarDup(dados) {
    try {
      const params = {
        empresa: dados.empresa || "", tipo_ato: dados.tipo_ato || "",
        data_ata: dados.data_ata || "", hora_ata: dados.hora_ata || "",
        identificador_ato: dados.identificador_ato || "",
      };
      const r = await axios.get(`${API}/processos/checar-duplicidade`, { params, headers: { "x-token": sessao.token } });
      if (r.data && r.data.duplicado) {
        return window.confirm("Possivel Duplicidade de Atos!\n\nDeseja seguir com a insercao?");
      }
      return true;
    } catch (e) { return true; }
  }
  async function processarArquivos(fileList) {
    const arquivos = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (arquivos.length === 0) { alert("Nenhum PDF encontrado na pasta."); return; }
    setSubindo(true);
    setProgresso({ feitos: 0, total: arquivos.length, erros: 0 });
    let feitos = 0, erros = 0, ultimoProcessoId = null;
    for (const arq of arquivos) {
      try {
        const fd1 = new FormData();
        fd1.append("arquivo", arq);
        const ana = await axios.post(`${API}/processos/analisar`, fd1, { headers: { "x-token": sessao.token } });
        const dados = ana.data || {};
        const segue = await checarDup(dados);
        if (!segue) { continue; }
        const fd2 = new FormData();
        fd2.append("arquivo", arq);
        fd2.append("dados", JSON.stringify(dados));
        const criado = await axios.post(`${API}/processos`, fd2, { headers: { "x-token": sessao.token } });
        ultimoProcessoId = criado.data && (criado.data.id || criado.data.processo_id);
        feitos++;
      } catch (e) {
        erros++;
      }
      setProgresso({ feitos, total: arquivos.length, erros });
    }
    setSubindo(false);
    const listaAtualizada = await carregar();
    alert(`Concluido: ${feitos} processo(s) criado(s)${erros ? `, ${erros} com erro` : ""}.`);
    // Se so' um processo foi criado (fluxo mais comum: inserir um ato por vez), abre
    // direto o modal de documentos dele, ja com o botao do iatos. disponivel ali.
    if (feitos === 1 && ultimoProcessoId && listaAtualizada) {
      const novo = listaAtualizada.find(p => p.id === ultimoProcessoId);
      if (novo) setDocsAbertos(novo);
    }
  }
  function clicarStatus(p) {
    if (p.status === "exigencia") setExigenciaAberta(p);
    else if (p.status === "aprovado" || p.status === "finalizado" || p.status === "deferido") baixar(p.id, "registro", (p.empresa || "registro").replace(/[^a-zA-Z0-9]/g, "_"));
    else setDocsAbertos(p);
  }
  function ListaProcessosAgrupada() {
    const grupos = processosFiltrados.reduce((acc, p) => {
      const chave = (p.criado_em || "").slice(0, 10) || "sem-data";
      if (!acc[chave]) acc[chave] = [];
      acc[chave].push(p);
      return acc;
    }, {});

    const chaves = Object.keys(grupos).sort((a, b) => {
      if (a === "sem-data") return 1;
      if (b === "sem-data") return -1;
      return a < b ? 1 : -1;
    });

    return (
      <>
        {chaves.map(chave => {
          const itens = grupos[chave];
          const label = chave === "sem-data" ? "Data inválida" : `Processos abertos em ${formatarDataExtenso(chave)}`;
          const aberto = !gruposFechados[chave];
          return (
            <div key={chave}>
              <div
                onClick={() => setGruposFechados(g => ({ ...g, [chave]: aberto }))}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                  padding: "10px 16px",
                  background: "rgba(255,255,255,0.02)",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#c4c8e4",
                }}
              >
                <span style={{ fontSize: 11, color: "#94a3b8" }}>{aberto ? "▾" : "▸"}</span>
                {label}
                <span style={{ fontSize: 11, color: "#94a3b8", fontWeight: 400 }}>({itens.length})</span>
              </div>
              {aberto && itens.map(p => (
                <div key={p.id} style={s.row}>
                  <div>
                    <div style={s.empresa}>{p.empresa}</div>
                    <div style={s.metaEmp}>{subtituloProcesso(p)}</div>
                  </div>
                  <div style={s.cell}>{p.uf || "—"}</div>
                  <div style={s.cell}>{abreviarAto(p.identificador_ato, p.data_ata)}</div>
                  <div style={{ ...s.cell, fontFamily: "monospace", fontSize: 11 }}>{p.numero_protocolo ? p.numero_protocolo.replace(/\D/g, "") : "—"}</div>
                  <div>
                    <span onClick={() => clicarStatus(p)}
                      style={{ ...s.badge, background: (STATUS_CONFIG[p.status]?.bg||"rgba(255,255,255,0.06)"), color: (STATUS_CONFIG[p.status]?.color||"#d4d4d8"),
                        border: `1px solid ${STATUS_CONFIG[p.status]?.borda || "rgba(255,255,255,0.15)"}`, cursor: "pointer" }}>
                      {STATUS_CONFIG[p.status]?.label || p.status}
                      {p.status === "exigencia" ? " ›" : " ↓"}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button onClick={() => setProcessoSelecionado(p)}
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)", color: "#d4d4d8", borderRadius: 8, padding: "9px 16px", fontSize: 12, cursor: "pointer", fontFamily: FONTE_CORPO }}>
                      Ver processo
                    </button>
                    <BotaoIatos processo={p} onAbrir={setIatosAberto} />
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </>
    );
  }

  return (
    <>
      <div style={s.appCliente}>
        <SidebarAtos
          onLogoClick={() => { setTela("processos"); setProcessoSelecionado(null); }}
          rodape={<div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#8ec2ff", background: "rgba(77,148,255,0.08)", border: "1px solid rgba(77,148,255,0.25)", borderRadius: 6, padding: "4px 10px", marginTop: 8 }}><span style={{ width: 5, height: 5, borderRadius: "50%", background: "#4d94ff", boxShadow: "0 0 6px #4d94ff" }} />{sessao.grupo}</div>}
          itens={[
            { label: "Processos", ativo: tela === "processos" && !processoSelecionado, icone: <IconeProcessos />, onClick: () => { setTela("processos"); setProcessoSelecionado(null); } },
            { label: "Relatórios", ativo: tela === "relatorios", icone: <IconeRelatorios />, onClick: () => { setTela("relatorios"); setProcessoSelecionado(null); } },
          ]}
        />
        <main style={s.mainCliente}>
          <div style={s.topBar}>
            <button style={s.btnSair} onClick={onSair}>Sair</button>
          </div>
          {processoSelecionado ? (
            <div style={s.conteudo}>
              <DetalheProcessoCliente p={processoSelecionado} sessao={sessao} onVoltar={() => setProcessoSelecionado(null)} />
            </div>
          ) : tela === "processos" ? (
            <div style={s.conteudo}>
              <DonutStatusCard titulo="Meus Processos" metricas={metricas} onClickStatus={setFStatus} idPrefix="dc" />
              {(fluxoAtivo || eventosRecentes.length > 0) && (
                <div style={{ display: "grid", gridTemplateColumns: fluxoAtivo ? "1fr 1fr" : "1fr", gap: 16, marginBottom: 16 }}>
                  {fluxoAtivo && <FluxoDoDiaCardEscuro fluxo={fluxoAtivo} />}
                  <AtividadeRecenteEscura eventos={eventosRecentes} />
                </div>
              )}
              <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
                <input value={fBusca} onChange={e => setFBusca(e.target.value)} placeholder="Buscar empresa..."
                  style={{ flex: "1 1 200px", minWidth: 160, padding: "9px 12px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, outline: "none", color: "#fff", fontFamily: FONTE_CORPO }} />
                <select value={fUf} onChange={e => setFUf(e.target.value)} style={s.filtro}>
                  <option value="">UF: todas</option>
                  {ufsDisponiveis.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
                <select value={fAto} onChange={e => setFAto(e.target.value)} style={s.filtro}>
                  <option value="">Ato: todos</option>
                  {atosDisponiveis.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
                <select value={fStatus} onChange={e => setFStatus(e.target.value)} style={s.filtro}>
                  <option value="">Status: todos</option>
                  <option value="aberto">Aberto</option>
                  <option value="tramitacao">Tramitacao</option>
                  <option value="exigencia">Exigencia</option>
                  <option value="deferido">Deferido</option>
                  <option value="finalizado">Finalizado</option>
                </select>
                {(fBusca || fUf || fAto || fStatus) && (
                  <button onClick={() => { setFBusca(""); setFUf(""); setFAto(""); setFStatus(""); }}
                    style={{ padding: "9px 14px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, background: "rgba(255,255,255,0.05)", color: "#d4d4d8", cursor: "pointer", fontFamily: FONTE_CORPO }}>Limpar</button>
                )}
              </div>
              <div
                onDragOver={e => { e.preventDefault(); }}
                onDrop={e => {
                  e.preventDefault();
                  const items = e.dataTransfer.items;
                  if (items && items.length && items[0].webkitGetAsEntry) {
                    const arquivos = [];
                    let pendentes = 0;
                    let lendoDiretorios = 0;
                    const finalizarSeVazio = () => { if (pendentes === 0 && lendoDiretorios === 0) processarPasta(arquivos); };
                    const lerDiretorioCompleto = (dirEntry, callback) => {
                      const reader = dirEntry.createReader();
                      let todos = [];
                      const lerLote = () => { reader.readEntries(ents => { if (ents.length === 0) { callback(todos); return; } todos = todos.concat(ents); lerLote(); }); };
                      lerLote();
                    };
                    const lerEntry = (entry) => {
                      if (entry.isFile) {
                        pendentes++;
                        entry.file(f => {
                          const rel = (entry.fullPath || ("/" + f.name)).replace(/^\//, "");
                          try { Object.defineProperty(f, "webkitRelativePath", { value: rel, configurable: true }); } catch (err) { f._relPath = rel; }
                          arquivos.push(f); pendentes--; finalizarSeVazio();
                        });
                      } else if (entry.isDirectory) {
                        lendoDiretorios++;
                        lerDiretorioCompleto(entry, (ents) => { lendoDiretorios--; ents.forEach(lerEntry); finalizarSeVazio(); });
                      }
                    };
                    for (let i = 0; i < items.length; i++) {
                      const entry = items[i].webkitGetAsEntry();
                      if (entry) lerEntry(entry);
                    }
                  } else {
                    processarArquivos(e.dataTransfer.files);
                  }
                }}
                style={{ border: "1.5px dashed rgba(77,148,255,0.35)", borderRadius: 18, padding: "28px", marginBottom: 18, background: "rgba(255,255,255,0.03)", textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#8a90b8", marginBottom: 12 }}>
                  {subindo
                    ? `Enviando... ${progresso.feitos} de ${progresso.total}${progresso.erros ? ` (${progresso.erros} com erro)` : ""}`
                    : "Arraste um processo aqui ou selecione arquivos e pastas do seu computador"}
                </div>
                <div style={{ display: "inline-flex", gap: 10 }}>
                  <label style={{ display: "inline-block", cursor: subindo ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", borderRadius: 9, padding: "9px 18px", fontSize: 12.5, fontFamily: FONTE_CORPO, opacity: subindo ? 0.6 : 1, boxShadow: "0 4px 16px rgba(77,148,255,0.3)" }}>
                      {subindo ? "Enviando..." : "Arquivos"}
                    </span>
                    <input type="file" accept="application/pdf" multiple style={{ display: "none" }}
                      disabled={subindo}
                      onChange={e => processarArquivos(e.target.files)} />
                  </label>
                  <label style={{ display: "inline-block", cursor: subindo ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", borderRadius: 9, padding: "9px 18px", fontSize: 12.5, fontFamily: FONTE_CORPO, opacity: subindo ? 0.6 : 1, boxShadow: "0 4px 16px rgba(77,148,255,0.3)" }}>
                      Pastas
                    </span>
                    <input type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
                      disabled={subindo}
                      onChange={e => processarPasta(e.target.files)} />
                  </label>
                </div>
              </div>
              {carregando ? <div style={s.vazio}>Carregando...</div>
                : erro ? <div style={s.erro}>{erro}</div>
                : processos.length === 0 ? <div style={s.vazio}>Nenhum processo disponivel no momento.</div>
                : (
                  <div style={s.tabela}>
                    <div style={s.thead}>
                      {["Empresa", "UF", "Ato", "Protocolo", "Status"].map((h, i) => <div key={i} style={s.th}>{h}</div>)}
                    </div>
                    <ListaProcessosAgrupada />
                  </div>
                )}
            </div>
          ) : (
            <div style={s.conteudo}>
              <div style={s.h1}>Relatórios</div>
              <div style={{ fontSize: 13, color: "#8a90b8", marginBottom: 20 }}>Gere uma planilha dos seus processos por situacao. Baixe agora; o envio por email estara disponivel em breve.</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
                {[
                  { st: "todos", lb: "Todos os Processos" },
                  { st: "aprovado", lb: "Atos Deferidos" },
                  { st: "exigencia", lb: "Atos em Exigência" },
                  { st: "tramitacao", lb: "Atos em Tramitação" },
                  { st: "recebido", lb: "Atos Abertos" },
                ].map(r => (
                  <div key={r.st} style={{ background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: 18 }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: "#fff", marginBottom: 14 }}>{r.lb}</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => baixarRelatorio(r.st)} style={{ flex: 1, background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", border: "none", borderRadius: 8, padding: "9px 12px", fontSize: 13, cursor: "pointer", fontFamily: FONTE_CORPO }}>Baixar planilha</button>
                      <button disabled title="Disponivel em breve" style={{ background: "rgba(255,255,255,0.05)", color: "#62666d", border: "none", borderRadius: 8, padding: "9px 12px", fontSize: 13, cursor: "not-allowed", fontFamily: FONTE_CORPO }}>Enviar email</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
      {docsAbertos && (() => {
        const docs = [
          { campo: "arquivo_ata", tipo: "ata", label: "Ata" },
          { campo: "arquivo_protocolo", tipo: "protocolo", label: "Protocolo" },
          { campo: "arquivo_registro", tipo: "registro", label: "Registro aprovado" },
          { campo: "arquivo_nd", tipo: "nd", label: "Nota de debito" },
          { campo: "arquivo_nf", tipo: "nf", label: "Nota fiscal" },
        ].filter(d => docsAbertos[d.campo]);
        return (
          <div style={s.overlay} onClick={() => setDocsAbertos(null)}>
            <div style={s.modal} onClick={e => e.stopPropagation()}>
              <div style={s.modalTitle}>Documentos — {docsAbertos.empresa}</div>
              {docs.length === 0 ? (
                <div style={s.exigTexto}>Nenhum documento disponivel ainda. Assim que houver, aparecera aqui para download.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
                  {docs.map(d => (
                    <button key={d.tipo} style={s.btnDl}
                      onClick={() => baixar(docsAbertos.id, d.tipo, (docsAbertos.empresa||"documento").replace(/[^a-zA-Z0-9]/g,"_"))}>
                      ↓ Download
                    </button>
                  ))}
                </div>
              )}
              <div style={{ marginTop: 16, marginBottom: 8 }}>
                <BotaoIatos processo={docsAbertos} onAbrir={setIatosAberto} />
              </div>
              <ChatProcessoCliente processoId={docsAbertos.id} token={sessao.token} />
              <div style={s.modalBtns}>
                <button style={s.btnFechar} onClick={() => setDocsAbertos(null)}>Fechar</button>
              </div>
            </div>
          </div>
        );
      })()}
      {iatosAberto && <IatosChat processo={iatosAberto} token={sessao.token} onFechar={() => setIatosAberto(null)} />}
      {exigenciaAberta && (
        <div style={s.overlay} onClick={() => setExigenciaAberta(null)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalTitle}>Exigencia — {exigenciaAberta.empresa}</div>
            <div style={s.exigTexto}>{exigenciaAberta.texto_exigencia || "Sem texto de exigencia."}</div>
            <div style={s.modalBtns}>
              {exigenciaAberta.arquivo_exigencia && (
                <button style={s.btnDl} onClick={() => baixar(exigenciaAberta.id, "exigencia", (exigenciaAberta.empresa||"exigencia").replace(/[^a-zA-Z0-9]/g,"_"))}>
                  ↓ Baixar PDF da exigencia
                </button>
              )}
              <button style={s.btnFechar} onClick={() => setExigenciaAberta(null)}>Fechar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function estilos() {
  return {
    appCliente: { display: "flex", minHeight: "100vh", fontFamily: FONTE_CORPO, background: "#060608", color: "#e4e4e7", WebkitFontSmoothing: "antialiased" },
    mainCliente: { flex: 1, padding: "32px 40px", overflowY: "auto" },
    topBar: { display: "flex", justifyContent: "flex-end", alignItems: "center", marginBottom: 20 },
    btnSair: { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", color: "#d4d4d8", borderRadius: 24, padding: "6px 16px", fontSize: 12.5, cursor: "pointer", fontFamily: FONTE_CORPO },
    conteudo: {},
    h1: { fontFamily: FONTE_TITULO, fontSize: 24, fontWeight: 700, color: "#fff", marginBottom: 18 },
    filtro: { padding: "9px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11.5, background: "rgba(255,255,255,0.05)", cursor: "pointer", color: "#d4d4d8", fontFamily: FONTE_CORPO },
    erro: { background: "rgba(255,77,77,0.12)", color: "#ff9494", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 },
    aviso: { background: "rgba(0,255,170,0.1)", color: "#7dffce", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 },
    vazio: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "40px 16px", textAlign: "center", color: "#62666d", fontSize: 14 },
    tabela: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 18, overflow: "hidden" },
    thead: { display: "grid", gridTemplateColumns: "2.5fr 0.5fr 1.3fr 1.2fr 1fr", padding: "10px 20px", background: "rgba(255,255,255,0.02)", borderBottom: "1px solid rgba(255,255,255,0.06)" },
    th: { fontSize: 10.5, fontWeight: 500, color: "#62666d", textTransform: "uppercase", letterSpacing: 0.4 },
    row: { display: "grid", gridTemplateColumns: "2.2fr 0.5fr 1.2fr 1fr 0.9fr 0.9fr", padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.04)", alignItems: "center" },
    empresa: { fontSize: 13.5, fontWeight: 600, color: "#fff", margin: "0 0 3px" },
    metaEmp: { fontSize: 11, color: "#71717a", margin: 0 },
    cell: { fontSize: 13, color: "#d4d4d8" },
    badge: { display: "inline-block", padding: "4px 11px", borderRadius: 20, fontSize: 11 },
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 },
    modal: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: 28, width: 480, maxHeight: "80vh", overflowY: "auto", color: "#e4e4e7" },
    modalTitle: { fontFamily: FONTE_TITULO, fontSize: 16, fontWeight: 700, color: "#fff", marginBottom: 16 },
    exigTexto: { background: "rgba(255,77,77,0.08)", border: "1px solid rgba(255,77,77,0.25)", borderRadius: 8, padding: 14, fontSize: 14, color: "#ffb4b4", lineHeight: 1.5, marginBottom: 18, whiteSpace: "pre-wrap" },
    modalBtns: { display: "flex", gap: 10, justifyContent: "flex-end" },
    btnDl: { background: "rgba(77,148,255,0.1)", color: "#8ec2ff", border: "1px solid rgba(77,148,255,0.3)", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer", fontFamily: FONTE_CORPO },
    btnFechar: { background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", border: "none", borderRadius: 8, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontFamily: FONTE_CORPO },
  };
}