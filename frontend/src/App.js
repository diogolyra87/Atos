import { useState, useEffect } from "react";
import axios from "axios";
import { Painel as PainelCliente } from "./Cliente";

const API = "";

const STATUS_CONFIG = {
  recebido: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  aberto: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  tramitacao: { label: "Tramitação", bg: "#f0e0cb", color: "#8a5818" },
  exigencia: { label: "Exigência", bg: "#f0dcd5", color: "#a8492a" },
  deferido: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  aprovado: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  finalizado: { label: "Finalizado", bg: "#cfe8d8", color: "#15803d" },
};

function abreviarAto(texto, data, hora) {
  const t = (texto || "").toUpperCase();
  const _dt = data ? `${(data || "").replace(/\//g, ".")}` : "";
  const _hr = hora ? ` (${hora} HRS)` : "";
  const d = _dt ? ` ${_dt}${_hr}` : "";
  // Alteracao contratual: "Nª ALTERAÇÃO" (sem data)
  let m = t.match(/(\d+)\s*[ªº°]?\s*ALTERA[ÇC][ÃA]O\s+CONTRATUAL/);
  if (m) return `${m[1]}ª ALTERAÇÃO`;
  // Aditamento a Nª emissao de debentures (numero da emissao, sem data)
  m = t.match(/ADITAMENTO.*?(\d+)\s*[ªº°]?\s*EMISS[ÃA]O\s+DE\s+DEB[ÊE]NTURES/);
  if (m) return `Aditamento ${m[1]}ª Emissão`;
  // Nª emissao de debentures
  m = t.match(/(\d+)\s*[ªº°]?\s*\(?[A-ZÀ-Ú]*\)?\s*EMISS[ÃA]O\s+DE\s+DEB[ÊE]NTURES/);
  if (m) return `${m[1]}ª EMISSÃO DE DEBÊNTURES${d}`;
  // Assembleia geral de debenturistas
  if (t.includes("DEBENTURISTAS")) return `AGD${d}`;
  // Assembleia geral ordinaria E extraordinaria
  if (t.includes("ORDIN") && t.includes("EXTRAORDIN")) return `AGOE${d}`;
  // Assembleia geral extraordinaria
  if (t.includes("EXTRAORDIN")) return `AGE${d}`;
  // Assembleia geral ordinaria
  if (t.includes("ORDIN") && t.includes("ASSEMBLEIA")) return `AGO${d}`;
  // Ata de reuniao de socios
  if (t.includes("REUNI") && (t.includes("SÓCIOS") || t.includes("SOCIOS"))) return `ARS${d}`;
  // Conselho de administracao (reuniao ou ata) -> RCA
  if (t.includes("CONSELHO DE ADMINISTRA")) return `RCA${d}`;
  // fallback: texto encurtado
  const curto = (texto || "").length > 38 ? (texto || "").slice(0, 38) + "…" : (texto || "—");
  return curto;
}

function TelaGrupos() {
  const [nome, setNome] = useState("");
  const [emails, setEmails] = useState([""]);
  const [criando, setCriando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");

  function mudarEmail(i, valor) {
    const novos = [...emails];
    novos[i] = valor;
    setEmails(novos);
  }
  function adicionarEmail() {
    setEmails([...emails, ""]);
  }
  function removerEmail(i) {
    if (emails.length === 1) return;
    setEmails(emails.filter((_, idx) => idx !== i));
  }

  async function criar() {
    setErro(""); setResultado(null);
    const nomeT = nome.trim();
    const emailsT = emails.map(e => e.trim()).filter(e => e);
    if (!nomeT) { setErro("Informe o nome do grupo."); return; }
    if (emailsT.length === 0) { setErro("Informe ao menos um email."); return; }
    setCriando(true);
    try {
      const r = await axios.post(`${API}/grupos/criar`, { nome: nomeT, emails: emailsT });
      setResultado(r.data);
      setNome(""); setEmails([""]);
    } catch (e) {
      setErro(e.response && e.response.data && e.response.data.detail ? e.response.data.detail : "Erro ao criar grupo.");
    }
    setCriando(false);
  }

  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: "#16151a", margin: 0 }}>Grupos empresariais</h1>
      </div>
      <div style={{ maxWidth: 560, background: "#fff", borderRadius: 12, padding: 28, border: "0.5px solid #e2e8f0" }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: "#16151a", marginBottom: 4 }}>Criar novo grupo</div>
        <div style={{ fontSize: 13, color: "#64748b", marginBottom: 20 }}>O sistema enviara automaticamente o convite de acesso para os emails cadastrados.</div>

        {erro && <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}

        {resultado && (
          <div style={{ background: "#dcfce7", color: "#166534", borderRadius: 8, padding: "12px 14px", fontSize: 13, marginBottom: 14 }}>
            <div><b>Grupo "{resultado.grupo}" criado!</b></div>
            <div style={{ marginTop: 4 }}>Codigo: {resultado.codigo}</div>
            {resultado.emails_enviados && resultado.emails_enviados.length > 0 && (
              <div style={{ marginTop: 6 }}>Convite enviado para: {resultado.emails_enviados.join(", ")}</div>
            )}
            {resultado.emails_falharam && resultado.emails_falharam.length > 0 && (
              <div style={{ marginTop: 6, color: "#991b1b" }}>Falhou o envio para: {resultado.emails_falharam.join(", ")}</div>
            )}
          </div>
        )}

        <label style={{ fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" }}>Nome do grupo</label>
        <input style={{ width: "100%", padding: "10px 12px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 18, boxSizing: "border-box" }} value={nome} onChange={e => setNome(e.target.value)} placeholder="Ex: Enel Green Power" />

        <label style={{ fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" }}>Emails do grupo</label>
        {emails.map((em, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input style={{ flex: 1, padding: "10px 12px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" }} type="email" value={em} onChange={e => mudarEmail(i, e.target.value)} placeholder="email@empresa.com" />
            {emails.length > 1 && (
              <button onClick={() => removerEmail(i)} style={{ background: "#f1f5f9", border: "0.5px solid #cbd5e1", borderRadius: 8, padding: "0 12px", cursor: "pointer", color: "#64748b", fontSize: 16 }}>−</button>
            )}
          </div>
        ))}
        <button onClick={adicionarEmail} style={{ background: "transparent", border: "0.5px dashed #94a3b8", borderRadius: 8, padding: "8px 12px", cursor: "pointer", color: "#475569", fontSize: 13, marginBottom: 20 }}>+ Adicionar outro email</button>

        <div>
          <button onClick={criar} disabled={criando} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "11px 22px", borderRadius: 8, fontSize: 14, cursor: "pointer" }}>{criando ? "Criando e enviando..." : "Criar grupo"}</button>
        </div>
      </div>
    </>
  );
}

function TelaAprendizado() {
  const [regras, setRegras] = useState([]);
  const [carregando, setCarregando] = useState(true);
  async function carregarRegras() {
    setCarregando(true);
    try { const r = await axios.get(`${API}/aprendizado/regras`); setRegras(r.data || []); } catch (e) {}
    setCarregando(false);
  }
  useEffect(() => { carregarRegras(); /* eslint-disable-next-line */ }, []);
  async function apagar(id) {
    if (!window.confirm("Remover esta regra aprendida?")) return;
    try { await axios.delete(`${API}/aprendizado/regras/${id}`); await carregarRegras(); } catch (e) { alert("Erro ao remover."); }
  }
  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: "#16151a", margin: 0 }}>Aprendizado do sistema</h1>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
          Regras que o sistema aprendeu com suas confirmacoes. Quanto maior o peso, mais vezes foi confirmada.
        </div>
      </div>
      {carregando ? (
        <div style={{ color: "#94a3b8", fontSize: 13 }}>Carregando...</div>
      ) : regras.length === 0 ? (
        <div style={{ background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, padding: 28, color: "#64748b", fontSize: 13 }}>
          Nenhuma regra aprendida ainda. Conforme voce confirma e corrige os avisos, o sistema aprende e as regras aparecem aqui.
        </div>
      ) : (
        <div style={{ background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1.3fr 0.6fr 70px", padding: "10px 16px", background: "#f1f5f9", borderBottom: "0.5px solid #e2e8f0" }}>
            {["Padrao", "Classificacao", "Tipo correto", "Peso", ""].map((h, i) => (
              <div key={i} style={{ fontSize: 11, fontWeight: 500, color: "#64748b" }}>{h}</div>
            ))}
          </div>
          {regras.map(r => (
            <div key={r.id} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1.3fr 0.6fr 70px", padding: "12px 16px", borderBottom: "0.5px solid #f1f5f9", alignItems: "center" }}>
              <div style={{ fontSize: 13, color: "#23282a", wordBreak: "break-word" }}>{r.padrao}</div>
              <div style={{ fontSize: 12, color: "#475569" }}>{r.classificacao || "—"}</div>
              <div style={{ fontSize: 12, color: "#475569" }}>{r.tipo_correto || "—"}</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#1e40af" }}>{r.peso}</div>
              <div>
                <button onClick={() => apagar(r.id)} style={{ background: "transparent", border: "0.5px solid #e2e8f0", color: "#b91c1c", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}>Apagar</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function AppPainel({ onSair }) {
  const [processos, setProcessos] = useState([]);
  const [metricas, setMetricas] = useState({});
  const [tela, setTela] = useState("processos");
  const [processoSelecionado, setProcessoSelecionado] = useState(null);
  const [modalNovo, setModalNovo] = useState(false);
  const [fBusca, setFBusca] = useState("");
  const [fUf, setFUf] = useState("");
  const [fAto, setFAto] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fGrupo, setFGrupo] = useState("");
  const [grupos, setGrupos] = useState([]);
  const [upGrupo, setUpGrupo] = useState("");
  const [upSubindo, setUpSubindo] = useState(false);
  const [upProg, setUpProg] = useState({ feitos: 0, total: 0, erros: 0 });
  useEffect(() => { axios.get(`${API}/grupos`).then(r => setGrupos(r.data)).catch(() => {}); }, []);



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
    if (fGrupo && p.grupo_id !== fGrupo) return false;
    if (fAto && abreviarAto(p.identificador_ato, "").split(" ")[0] !== fAto) return false;
    return true;
  });
  const [analisando, setAnalisando] = useState(false);
  const [dadosAnalise, setDadosAnalise] = useState(null);
  const [arquivoSelecionado, setArquivoSelecionado] = useState(null);

  useEffect(() => { carregar(); }, []);

  async function carregar() {
    const [p, m] = await Promise.all([
      axios.get(`${API}/processos`),
      axios.get(`${API}/metricas`)
    ]);
    setProcessos(p.data);
    setMetricas(m.data);
  }

  async function analisarArquivo(arquivo) {
    setAnalisando(true);
    setArquivoSelecionado(arquivo);
    try {
      const form = new FormData();
      form.append("arquivo", arquivo);
      const res = await axios.post(`${API}/processos/analisar`, form);
      setDadosAnalise(res.data);
    } catch (e) {
      alert("Erro ao analisar documento.");
    }
    setAnalisando(false);
  }

  async function criarProcesso() {
    if (!dadosAnalise) return;
    try {
      const segueDup = await checarDup(dadosAnalise);
      if (!segueDup) return;
      const form = new FormData();
      if (arquivoSelecionado) form.append("arquivo", arquivoSelecionado);
      form.append("dados", JSON.stringify(dadosAnalise));
      await axios.post(`${API}/processos`, form);
      setModalNovo(false);
      setDadosAnalise(null);
      setArquivoSelecionado(null);
      carregar();
    } catch (e) {
      alert("Erro ao criar processo.");
    }
  }

  async function atualizarStatus(id, status) {
    await axios.patch(`${API}/processos/${id}`, { status });
    carregar();
    if (processoSelecionado?.id === id) {
      setProcessoSelecionado({ ...processoSelecionado, status });
    }
  }

  async function baixarArquivo(id, tipo, nomeBase) {
    try {
      const res = await axios.get(`${API}/download/${id}/${tipo}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = `${nomeBase}_${tipo}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert("Nao foi possivel baixar este arquivo."); }
  }
  async function processarPastaAdmin(fileList) {
    if (!upGrupo) { alert("Selecione o cliente antes de subir os arquivos."); return; }
    const arquivos = Array.from(fileList).filter(f => {
      const n = f.name.toLowerCase();
      return n.endsWith(".pdf") || n.endsWith(".docx") || n.endsWith(".png") || n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".xml") || n.endsWith(".txt");
    });
    if (arquivos.length === 0) { alert("Nenhum arquivo valido na pasta."); return; }
    if (arquivos.length === 1) { return processarArquivosAdmin(fileList); }
    setUpSubindo(true);
    setUpProg({ feitos: 0, total: 1, erros: 0 });
    try {
      const fdA = new FormData();
      arquivos.forEach(a => fdA.append("arquivos", a));
      const res = await axios.post(`${API}/processos/analisar-pasta`, fdA);
      const r = res.data || {};
      const principal = r.principal || {};
      const idxPrincipal = principal.indice;
      const dados = principal.dados || {};
      dados.codigo_grupo = upGrupo;
      if (!principal.tipo_sugerido) {
        const ok = window.confirm("AVISO\n\nDocumento Sem Valor Societario!\n\nPossivel Anexo ou Documento Complementar!\n\nDeseja Seguir Com a Insercao?");
        if (!ok) { setUpSubindo(false); return; }
        dados.uf = "";
        if (!dados.empresa) { dados.empresa = "Documento desconhecido"; dados.identificador_ato = "Documento desconhecido"; }
      }
      if (r.confirmacao_pendente) { dados.confirmacao_pendente = true; dados.tipo_ato_sugerido = principal.tipo_sugerido || ""; }
      const segueDup = await checarDup(dados);
      if (!segueDup) { setUpSubindo(false); return; }
      const arqPrincipal = arquivos[idxPrincipal];
      const fd2 = new FormData();
      fd2.append("arquivo", arqPrincipal);
      fd2.append("dados", JSON.stringify(dados));
      const criado = await axios.post(`${API}/processos`, fd2);
      const novoId = criado.data && (criado.data.id || criado.data.processo_id);
      let anexErros = 0;
      if (novoId && Array.isArray(r.anexos)) {
        for (const ax of r.anexos) {
          try {
            const fda = new FormData();
            fda.append("arquivo", arquivos[ax.indice]);
            fda.append("descricao", "");
            await axios.post(`${API}/processos/${novoId}/anexos`, fda, { headers: { "Content-Type": "multipart/form-data" } });
          } catch (e) { anexErros++; }
        }
      }
      setUpProg({ feitos: 1, total: 1, erros: 0 });
      setUpSubindo(false);
      carregar();
      alert(`Processo criado. Principal: ${principal.nome}. Anexos: ${(r.anexos||[]).length - anexErros}${anexErros ? ` (${anexErros} falharam)` : ""}.`);
    } catch (e) {
      setUpSubindo(false);
      alert("Erro ao processar a pasta.");
    }
  }
  async function checarDup(dados) {
    try {
      const params = {
        empresa: dados.empresa || "", tipo_ato: dados.tipo_ato || "",
        data_ata: dados.data_ata || "", hora_ata: dados.hora_ata || "",
        identificador_ato: dados.identificador_ato || "",
      };
      const r = await axios.get(`${API}/processos/checar-duplicidade`, { params });
      if (r.data && r.data.duplicado) {
        return window.confirm("Possivel Duplicidade de Atos!\n\nDeseja seguir com a insercao?");
      }
      return true;
    } catch (e) { return true; }
  }
  async function processarArquivosAdmin(fileList) {
    if (!upGrupo) { alert("Selecione o cliente antes de subir os arquivos."); return; }
    const arquivos = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (arquivos.length === 0) { alert("Nenhum PDF encontrado."); return; }
    setUpSubindo(true);
    setUpProg({ feitos: 0, total: arquivos.length, erros: 0 });
    let feitos = 0, erros = 0;
    for (const arq of arquivos) {
      try {
        const fd1 = new FormData();
        fd1.append("arquivo", arq);
        const ana = await axios.post(`${API}/processos/analisar`, fd1);
        const dados = ana.data || {};
        dados.codigo_grupo = upGrupo;
        const segue = await checarDup(dados);
        if (!segue) { continue; }
        const fd2 = new FormData();
        fd2.append("arquivo", arq);
        fd2.append("dados", JSON.stringify(dados));
        await axios.post(`${API}/processos`, fd2);
        feitos++;
      } catch (e) { erros++; }
      setUpProg({ feitos, total: arquivos.length, erros });
    }
    setUpSubindo(false);
    carregar();
    alert(`Concluido: ${feitos} processo(s) criado(s)${erros ? `, ${erros} com erro` : ""}.`);
  }
  async function uploadArquivo(id, tipo, arquivo) {
    const form = new FormData();
    form.append("arquivo", arquivo);
    await axios.post(`${API}/processos/${id}/upload/${tipo}`, form);
    carregar();
  }

  const s = {
    layout: { display: "flex", minHeight: "100vh", fontFamily: "'Inter', sans-serif" },
    sidebar: { width: 220, background: "linear-gradient(165deg,#0e2a6e,#2563eb)", display: "flex", flexDirection: "column", padding: "24px 16px", gap: 8 },
    logo: { fontFamily: "'Inter', sans-serif", fontSize: 30, fontWeight: 800, color: "#16151a", letterSpacing: -1.5, lineHeight: 1 },
    nav: (ativo) => ({ display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8, color: ativo ? "#fff" : "#cfe8f0", background: ativo ? "rgba(255,255,255,0.13)" : "transparent", cursor: "pointer", fontSize: 13, border: "none", width: "100%", textAlign: "left" }),
    main: { flex: 1, background: "#f8fafc", padding: 28 },
    topbar: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 },
    h1: { fontSize: 18, fontWeight: 500, color: "#23282a", margin: 0 },
    btnPrimary: { background: "#1e40af", color: "#fff", border: "none", padding: "9px 18px", borderRadius: 8, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 },
    metrics: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 24 },
    metricCard: { background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 10, padding: 16 },
    metricLabel: { fontSize: 12, color: "#64748b", marginBottom: 6 },
    metricValue: { fontFamily: "'DM Serif Display', serif", fontSize: 40, fontWeight: 400, color: "#23282a", lineHeight: 1 },
    metricSub: { fontSize: 11, color: "#94a3b8", marginTop: 2 },
    tableWrap: { background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, overflow: "hidden" },
    tableHead: { display: "grid", gridTemplateColumns: "2.5fr 0.5fr 1.3fr 1.2fr 1fr 70px", padding: "10px 16px", background: "#f1f5f9", borderBottom: "0.5px solid #e2e8f0" },
    th: { fontSize: 11, fontWeight: 500, color: "#64748b" },
    row: { display: "grid", gridTemplateColumns: "2.5fr 0.5fr 1.3fr 1.2fr 1fr 70px", padding: "13px 16px", borderBottom: "0.5px solid #f1f5f9", alignItems: "center", cursor: "pointer" },
    company: { fontSize: 13, fontWeight: 500, color: "#23282a" },
    cnpj: { fontFamily: "monospace", fontSize: 11, color: "#94a3b8", marginTop: 2 },
    cell: { fontSize: 12, color: "#475569" },
    badge: (status) => ({ display: "inline-block", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500, background: STATUS_CONFIG[status]?.bg || "#f1f5f9", color: STATUS_CONFIG[status]?.color || "#475569" }),
    btnVer: { background: "none", border: "0.5px solid #e2e8f0", borderRadius: 6, padding: "5px 10px", fontSize: 11, color: "#2563eb", cursor: "pointer" },
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 },
    modal: { background: "#fff", borderRadius: 12, padding: 28, width: 560, maxHeight: "80vh", overflowY: "auto" },
    modalTitle: { fontSize: 16, fontWeight: 500, color: "#23282a", marginBottom: 20 },
    campo: { marginBottom: 14 },
    label: { fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" },
    input: { width: "100%", padding: "8px 12px", border: "0.5px solid #e2e8f0", borderRadius: 8, fontSize: 13, outline: "none" },
    btnRow: { display: "flex", gap: 10, marginTop: 20, justifyContent: "flex-end" },
    btnSecondary: { background: "none", border: "0.5px solid #e2e8f0", borderRadius: 8, padding: "9px 18px", fontSize: 13, cursor: "pointer", color: "#475569" },
    detalhe: { background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, padding: 24 },
    detalheHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
    detalheTitle: { fontSize: 18, fontWeight: 500, color: "#23282a" },
    detalheGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 },
    detalheItem: { background: "#f8fafc", borderRadius: 8, padding: 12 },
    detalheItemLabel: { fontSize: 11, color: "#94a3b8", marginBottom: 4 },
    detalheItemValue: { fontSize: 13, color: "#23282a", fontWeight: 500 },
    alerta: { background: "#fef3c7", border: "0.5px solid #fbbf24", borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: "#92400e" },
    statusRow: { display: "flex", gap: 8, marginBottom: 20 },
    btnStatus: (ativo) => ({ padding: "6px 14px", borderRadius: 20, fontSize: 12, cursor: "pointer", border: ativo ? "2px solid #1e40af" : "0.5px solid #e2e8f0", background: ativo ? "#dbeafe" : "#fff", color: ativo ? "#1e40af" : "#475569", fontWeight: ativo ? 500 : 400 }),
    uploadRow: { display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 },
    uploadItem: { display: "flex", alignItems: "center", justifyContent: "space-between", background: "#f8fafc", borderRadius: 8, padding: "10px 14px" },
    uploadLabel: { fontSize: 13, color: "#475569" },
    uploadOk: { fontSize: 12, color: "#166534", background: "#dcfce7", padding: "3px 10px", borderRadius: 20 },
    uploadPend: { fontSize: 12, color: "#475569", background: "#f1f5f9", padding: "3px 10px", borderRadius: 20 },
    checklist: { background: "#f8fafc", borderRadius: 8, padding: 14, marginBottom: 16 },
    checkItem: { fontSize: 13, color: "#475569", padding: "4px 0", borderBottom: "0.5px solid #e2e8f0", display: "flex", alignItems: "center", gap: 8 },
  };

  function BannerPendencias() {
    const [pend, setPend] = useState([]);
    const [tipos, setTipos] = useState({});
    const TIPOS = [
      "Contrato Social","Alteracao Contratual","Ata de Reuniao/Assembleia de Socios",
      "Distrato/Dissolucao/Liquidacao","Estatuto Social","Ata de Assembleia Geral de Constituicao",
      "Ata de AGO","Ata de AGE","Ata de Reuniao do Conselho de Administracao",
      "Ata de Reuniao de Diretoria","Escritura de Emissao de Debentures",
      "Boletim/Lista/Carta de Subscricao","Ata de Assembleia Geral",
    ];
    async function carregarPend() {
      try { const r = await axios.get(`${API}/processos/pendentes`); setPend(r.data || []); } catch (e) {}
    }
    useEffect(() => { carregarPend(); /* eslint-disable-next-line */ }, []);
    async function confirmar(id) {
      const tipo = tipos[id] || "";
      try {
        const fd = new FormData();
        fd.append("dados", JSON.stringify({ tipo_ato: tipo }));
        await axios.post(`${API}/processos/${id}/confirmar-tipo`, fd, { headers: { "Content-Type": "multipart/form-data" } });
        // aprendizado: grava a correcao como regra (identificador + tipo)
        const proc = pend.find(x => x.id === id);
        const ident = proc && (proc.identificador_ato || "");
        if (ident || tipo) {
          try {
            const fdA = new FormData();
            fdA.append("dados", JSON.stringify({ padrao: ident || tipo, classificacao: "principal", tipo_correto: tipo, origem: "confirmacao_adm" }));
            await axios.post(`${API}/aprendizado/registrar`, fdA, { headers: { "Content-Type": "multipart/form-data" } });
          } catch (e) { /* aprendizado nao bloqueia a confirmacao */ }
        }
        await carregarPend();
        carregar();
      } catch (e) { alert("Erro ao confirmar o tipo."); }
    }
    if (pend.length === 0) return null;
    return (
      <div style={{ background: "#fef3c7", border: "0.5px solid #fbbf24", borderRadius: 10, padding: 16, marginBottom: 18 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#92400e", marginBottom: 4 }}>
          {pend.length} processo(s) aguardando confirmacao do tipo de documento
        </div>
        <div style={{ fontSize: 12, color: "#92400e", marginBottom: 12 }}>
          O sistema nao teve certeza do documento principal. Confirme ou corrija o tipo de ato.
        </div>
        {pend.map(p => (
          <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", background: "#fff", borderRadius: 8, padding: "8px 12px", marginBottom: 8 }}>
            <div style={{ flex: "1 1 200px", minWidth: 160 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a" }}>{p.empresa || "Documento desconhecido"}</div>
              <div style={{ fontSize: 11, color: "#94a3b8" }}>
                Sugestao: {p.tipo_ato_sugerido || p.tipo_ato || "—"}{p.data_ata ? ` · ${p.data_ata}` : ""}
              </div>
            </div>
            <select value={tipos[p.id] || p.tipo_ato_sugerido || ""} onChange={e => setTipos(t => ({ ...t, [p.id]: e.target.value }))}
              style={{ padding: "8px 10px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#475569" }}>
              <option value="">Selecione o tipo...</option>
              {TIPOS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={() => confirmar(p.id)}
              style={{ background: "#1e40af", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>Confirmar</button>
          </div>
        ))}
      </div>
    );
  }

  function ChatProcesso({ processoId }) {
    const [aberto, setAberto] = useState(false);
    const [msgs, setMsgs] = useState([]);
    const [texto, setTexto] = useState("");
    const [enviando, setEnviando] = useState(false);
    async function carregarMsgs() {
      try { const r = await axios.get(`${API}/processos/${processoId}/mensagens`); setMsgs(r.data || []); } catch (e) {}
    }
    useEffect(() => { if (aberto) carregarMsgs(); /* eslint-disable-next-line */ }, [aberto]);
    async function enviar() {
      const t = texto.trim();
      if (!t) return;
      setEnviando(true);
      try {
        const fd = new FormData();
        fd.append("dados", JSON.stringify({ texto: t }));
        await axios.post(`${API}/processos/${processoId}/mensagens`, fd, { headers: { "Content-Type": "multipart/form-data" } });
        setTexto("");
        await carregarMsgs();
      } catch (e) { alert("Nao foi possivel enviar a mensagem."); }
      setEnviando(false);
    }
    return (
      <div style={{ marginTop: 20, marginBottom: 16 }}>
        <button onClick={() => setAberto(a => !a)}
          style={{ width: "100%", textAlign: "left", background: "#eff6ff", border: "0.5px solid #bfdbfe", borderRadius: 10, padding: "12px 16px", cursor: "pointer", fontSize: 14, fontWeight: 600, color: "#1e40af", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>Duvidas sobre o Processo?</span>
          <span style={{ fontSize: 12, fontWeight: 400, color: "#2563eb" }}>{aberto ? "fechar ▲" : `abrir ▼${msgs.length ? ` (${msgs.length})` : ""}`}</span>
        </button>
        {aberto && (
          <div style={{ border: "0.5px solid #e2e8f0", borderTop: "none", borderRadius: "0 0 10px 10px", padding: 14, background: "#fff" }}>
            <div style={{ maxHeight: 320, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
              {msgs.length === 0 ? (
                <div style={{ fontSize: 13, color: "#94a3b8", textAlign: "center", padding: 12 }}>Nenhuma mensagem ainda. Escreva a primeira.</div>
              ) : msgs.map(mm => {
                const meu = mm.autor_tipo === "admin";
                return (
                  <div key={mm.id} style={{ alignSelf: meu ? "flex-end" : "flex-start", maxWidth: "80%", background: meu ? "#dbeafe" : "#f1f5f9", borderRadius: 10, padding: "8px 12px" }}>
                    <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>
                      {mm.autor_login}{mm.criado_em ? ` · ${new Date(mm.criado_em).toLocaleString("pt-BR")}` : ""}
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
                style={{ flex: 1, minHeight: 40, maxHeight: 120, padding: "8px 12px", border: "0.5px solid #e2e8f0", borderRadius: 8, fontSize: 13, outline: "none", resize: "vertical", fontFamily: "'Inter', sans-serif" }} />
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

  function DetalheProcesso({ p }) {
    const eventos = JSON.parse(p.eventos || "[]");
    const checklist = JSON.parse(p.checklist || "[]");
    const [numProtocolo, setNumProtocolo] = useState(p.numero_protocolo || "");
    const [salvandoProt, setSalvandoProt] = useState(false);
    const [anexados, setAnexados] = useState({});
    async function uploadProtocoloLocal(tipo, arquivo) {
      const form = new FormData();
      form.append("arquivo", arquivo);
      try {
        const resp = await axios.post(API + "/processos/" + p.id + "/upload/" + tipo, form);
        setAnexados(a => ({ ...a, [tipo]: true }));
        if (tipo === "protocolo" && resp.data && resp.data.numero_protocolo) {
          setNumProtocolo(resp.data.numero_protocolo);
        }
      } catch (e) {
        alert("Erro ao anexar o arquivo.");
      }
    }

    const [textoExig, setTextoExig] = useState(p.texto_exigencia || "");
    const [arqExig, setArqExig] = useState(null);
    const [salvandoExig, setSalvandoExig] = useState(false);
    const [anexos, setAnexos] = useState([]);
    const [enviandoAnexo, setEnviandoAnexo] = useState(false);
    const [descAnexo, setDescAnexo] = useState("");
    async function carregarAnexos() {
      try {
        const r = await axios.get(`${API}/processos/${p.id}/anexos`);
        setAnexos(r.data || []);
      } catch (e) { /* silencioso */ }
    }
    useEffect(() => { carregarAnexos(); /* eslint-disable-next-line */ }, []);
    async function enviarAnexo(arquivo) {
      if (!arquivo) return;
      setEnviandoAnexo(true);
      try {
        const fd = new FormData();
        fd.append("arquivo", arquivo);
        fd.append("descricao", descAnexo || "");
        await axios.post(`${API}/processos/${p.id}/anexos`, fd, { headers: { "Content-Type": "multipart/form-data" } });
        setDescAnexo("");
        await carregarAnexos();
      } catch (e) { alert("Nao foi possivel enviar o anexo."); }
      setEnviandoAnexo(false);
    }
    async function baixarAnexo(anexoId, nome) {
      try {
        const res = await axios.get(`${API}/anexos/${anexoId}/download`, { responseType: "blob" });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement("a");
        a.href = url; a.download = nome || "anexo";
        document.body.appendChild(a); a.click(); a.remove();
      } catch (e) { alert("Nao foi possivel baixar o anexo."); }
    }
    async function excluirAnexo(anexoId) {
      if (!window.confirm("Remover este anexo?")) return;
      try {
        await axios.delete(`${API}/anexos/${anexoId}`);
        await carregarAnexos();
      } catch (e) { alert("Nao foi possivel remover o anexo."); }
    }

    async function registrarExigencia() {
      setSalvandoExig(true);
      try {
        const form = new FormData();
        form.append("texto", textoExig);
        if (arqExig) form.append("arquivo", arqExig);
        await axios.post(`${API}/processos/${p.id}/exigencia`, form);
        carregar();
        if (processoSelecionado?.id === p.id) {
          const res = await axios.get(`${API}/processos/${p.id}`);
          setProcessoSelecionado(res.data);
        }
      } catch (e) {
        alert("Erro ao registrar exigência.");
      }
      setSalvandoExig(false);
    }

    async function exigenciaCumprida() {
      try {
        await axios.post(`${API}/processos/${p.id}/exigencia/cumprida`);
        carregar();
        if (processoSelecionado?.id === p.id) {
          const res = await axios.get(`${API}/processos/${p.id}`);
          setProcessoSelecionado(res.data);
        }
      } catch (e) {
        alert("Erro ao marcar exigência como cumprida.");
      }
}
async function excluirProcesso() {
      if (!window.confirm("Tem certeza que deseja EXCLUIR este processo? Esta acao nao pode ser desfeita.")) return;
      try {
        await axios.delete(`${API}/processos/${p.id}`);
        setProcessoSelecionado(null);
        carregar();
      } catch (e) {
        alert("Erro ao excluir o processo.");
      }
    }
        async function exigenciaAguardandoCliente() {
      try {
        await axios.post(`${API}/processos/${p.id}/exigencia/aguardando-cliente`);
        alert("Marcado como aguardando o cliente. Alertas passam a ser a cada 7 dias.");
        carregar();
        if (processoSelecionado?.id === p.id) {
          const res = await axios.get(`${API}/processos/${p.id}`);
          setProcessoSelecionado(res.data);
        }
      } catch (e) {
        alert("Erro ao marcar como aguardando cliente.");
      }
    }
    async function salvarProtocolo() {
      setSalvandoProt(true);
      try {
        await axios.patch(`${API}/processos/${p.id}`, { numero_protocolo: numProtocolo });
        if (processoSelecionado?.id === p.id) {
          setProcessoSelecionado({ ...processoSelecionado, numero_protocolo: numProtocolo });
        }
        carregar();
      } catch (e) {
        alert("Erro ao salvar o número do protocolo.");
      }
      setSalvandoProt(false);
    }

    return (
      <div style={s.detalhe}>
        <div style={s.detalheHeader}>
          <div>
            <div style={s.detalheTitle}>{p.empresa}</div>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
              {p.cnpj} · NIRE {p.nire} · {p.id}
            </div>
          </div>
          <button style={s.btnSecondary} onClick={() => setProcessoSelecionado(null)}>← Voltar</button> <button style={{ background: "#b91c1c", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer", marginLeft: 8 }} onClick={excluirProcesso}>Excluir Processo</button>
        </div>

        {p.requer_cpl && (
          <div style={s.alerta}>
            ⚠ CPL necessária — alteração de endereço ou objeto social requer Consulta Prévia de Local na Prefeitura antes de qualquer protocolo.
          </div>
        )}

        <div style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>Alterar status:</div>
        <div style={s.statusRow}>
          {["aberto","tramitacao","exigencia","deferido","finalizado"].map((key) => (
            <button key={key} style={s.btnStatus(p.status === key)} onClick={() => atualizarStatus(p.id, key)}>
              {STATUS_CONFIG[key].label}
            </button>
          ))}
        </div>

        <div style={s.detalheGrid}>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Tipo de ato</div><div style={s.detalheItemValue}>{p.tipo_ato}</div></div>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Identificador</div><div style={s.detalheItemValue}>{p.identificador_ato}</div></div>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Data da ata</div><div style={s.detalheItemValue}>{p.data_ata} {p.hora_ata && `· ${p.hora_ata}`}</div></div>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Tipo de sociedade</div><div style={s.detalheItemValue}>{p.tipo_sociedade}</div></div>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Recebido em</div><div style={s.detalheItemValue}>{new Date(p.data_recebimento).toLocaleDateString("pt-BR")}</div></div>
          <div style={s.detalheItem}><div style={s.detalheItemLabel}>Protocolo</div><div style={s.detalheItemValue}>{p.numero_protocolo || "—"}</div></div>
        </div>

        {eventos.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a", marginBottom: 8 }}>Eventos identificados</div>
            <div style={s.checklist}>
              {eventos.map((e, i) => <div key={i} style={s.checkItem}>• {e}</div>)}
            </div>
          </div>
        )}

        {checklist.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a", marginBottom: 8 }}>Checklist de documentos</div>
            <div style={s.checklist}>
              {checklist.map((c, i) => <div key={i} style={s.checkItem}>☐ {c}</div>)}
            </div>
          </div>
        )}

        <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a", marginBottom: 8 }}>Exigência</div>
        <div style={{ background: "#f8fafc", borderRadius: 8, padding: 14, marginBottom: 16 }}>
          {p.exigencia_ativa && (
            <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 6, padding: "6px 10px", fontSize: 12, marginBottom: 10 }}>
              ⚠ Exigência ativa — o processo está em Exigência.
            </div>
          )}
          <label style={s.label}>Texto da exigência</label>
          <textarea style={{ ...s.input, minHeight: 70, resize: "vertical", fontFamily: "'Inter', sans-serif" }}
            value={textoExig} onChange={e => setTextoExig(e.target.value)}
            placeholder="Descreva a exigência..." />
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
            <label style={{ cursor: "pointer" }}>
              <span style={s.uploadPend}>{arqExig ? `📎 ${arqExig.name}` : (p.arquivo_exigencia ? "✓ PDF anexado — trocar" : "+ Anexar PDF da exigência")}</span>
              <input type="file" accept=".pdf" style={{ display: "none" }} onChange={e => setArqExig(e.target.files[0])} />
            </label>
            <button style={s.btnPrimary} onClick={registrarExigencia} disabled={salvandoExig}>
              {salvandoExig ? "Salvando..." : "Registrar exigência"}
            </button>
            {p.exigencia_ativa && (<>
              <button style={{ ...s.btnSecondary, borderColor: "#86efac", color: "#166534" }} onClick={exigenciaCumprida}>
                ✓ Exigência cumprida
              </button>
              <button style={{ ...s.btnSecondary, borderColor: "#fbbf24", color: "#92400e" }} onClick={exigenciaAguardandoCliente}>
                Exigência Aguardando Cliente
              </button>
            </>)}
          </div>
        </div>

        <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a", marginBottom: 8 }}>Arquivos</div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label style={s.label}>Número do protocolo</label>
            <input style={s.input} value={numProtocolo} onChange={e => setNumProtocolo(e.target.value)}
              placeholder="Digite o número do protocolo" />
          </div>
          <button style={{ ...s.btnPrimary, height: 38 }} onClick={salvarProtocolo} disabled={salvandoProt}>
            {salvandoProt ? "Salvando..." : "Salvar"}
          </button>
        </div>
        <div style={s.uploadRow}>
          {[
            { tipo: "ata", label: "Ata", arquivo: p.arquivo_ata },
            { tipo: "protocolo", label: "Protocolo", arquivo: p.arquivo_protocolo },
            { tipo: "registro", label: "Registro aprovado", arquivo: p.arquivo_registro },
            { tipo: "nd", label: "Nota de débito", arquivo: p.arquivo_nd },
            { tipo: "nf", label: "Nota fiscal", arquivo: p.arquivo_nf },
          ].map(({ tipo, label, arquivo }) => (
            <div key={tipo} style={s.uploadItem}>
              <span style={s.uploadLabel}>{label}</span>
              {(arquivo || anexados[tipo])
                ? <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span style={s.uploadOk}>✓ Anexado</span>
                    <button onClick={() => baixarArquivo(p.id, tipo, (p.empresa||"documento").replace(/[^a-zA-Z0-9]/g,"_"))}
                      style={{ background: "transparent", border: "0.5px solid #2563eb", color: "#2563eb", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>↓ Baixar</button>
                  </span>
                : <label style={{ cursor: "pointer" }}>
                    <span style={s.uploadPend}>+ Anexar</span>
                    <input type="file" style={{ display: "none" }} onChange={e => uploadProtocoloLocal(tipo, e.target.files[0])} />
                  </label>
              }
            </div>
          ))}
        </div>

        <div style={{ fontSize: 13, fontWeight: 500, color: "#23282a", marginTop: 24, marginBottom: 8 }}>
          Anexos <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 400 }}>({anexos.length})</span>
        </div>
        <div style={{ background: "#f8fafc", borderRadius: 8, padding: 14, marginBottom: 16 }}>
          {anexos.length === 0 ? (
            <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>Nenhum anexo enviado ainda.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
              {anexos.map(ax => (
                <div key={ax.id} style={{ ...s.uploadItem, alignItems: "flex-start" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: "#23282a", fontWeight: 500, wordBreak: "break-word" }}>
                      {ax.nome_original || "anexo"}
                    </div>
                    {ax.descricao && (
                      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{ax.descricao}</div>
                    )}
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                      Enviado por {ax.enviado_por || "\u2014"}
                      {ax.criado_em && ` \u00b7 ${new Date(ax.criado_em).toLocaleDateString("pt-BR")}`}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0, marginLeft: 10 }}>
                    <button onClick={() => baixarAnexo(ax.id, ax.nome_original)}
                      style={{ background: "transparent", border: "0.5px solid #2563eb", color: "#2563eb", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>\u2193 Baixar</button>
                    <button onClick={() => excluirAnexo(ax.id)}
                      style={{ background: "transparent", border: "0.5px solid #e2e8f0", color: "#b91c1c", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>Excluir</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", borderTop: "0.5px solid #e2e8f0", paddingTop: 12 }}>
            <input style={{ ...s.input, flex: "1 1 200px", minWidth: 160 }} value={descAnexo}
              onChange={e => setDescAnexo(e.target.value)} placeholder="Descri\u00e7\u00e3o (opcional): ex. procura\u00e7\u00e3o, RG..." />
            <label style={{ cursor: enviandoAnexo ? "not-allowed" : "pointer" }}>
              <span style={{ ...s.uploadPend, opacity: enviandoAnexo ? 0.5 : 1 }}>
                {enviandoAnexo ? "Enviando..." : "+ Enviar anexo"}
              </span>
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.xml,.txt" style={{ display: "none" }}
                disabled={enviandoAnexo}
                onChange={e => { if (e.target.files[0]) { enviarAnexo(e.target.files[0]); e.target.value = ""; } }} />
            </label>
          </div>
        </div>

        <ChatProcesso processoId={p.id} />
        {p.observacoes && (
          <div style={{ background: "#f8fafc", borderRadius: 8, padding: 12, fontSize: 13, color: "#475569" }}>
            <strong>Observações:</strong> {p.observacoes}
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />

      <div style={s.layout}>
        <div style={s.sidebar}>
          <div style={{ margin: "20px 16px 14px", padding: "16px 18px", background: "#f4f2ec", borderRadius: 12 }}>
            <div style={{ ...s.logo, cursor: "pointer" }} onClick={() => { setTela("processos"); setProcessoSelecionado(null); }}>atos<span style={{ color: "#d85a30" }}>.</span></div>
            <div style={{ fontSize: 11, color: "#6b6c66", marginTop: 4 }}>Gestão Societária</div>
          </div>
          {[
            { key: "processos", icon: "⊞", label: "Processos" },
            { key: "atas", icon: "⊡", label: "Atas recebidas" },
            { key: "cobrancas", icon: "◈", label: "Cobranças" },
            { key: "relatorios", icon: "▦", label: "Relatórios" },
            { key: "grupos", icon: "◉", label: "Grupos" },
            { key: "aprendizado", icon: "◈", label: "Aprendizado" },
          ].map(({ key, icon, label }) => (
            <button key={key} style={s.nav(tela === key)} onClick={() => { setTela(key); setProcessoSelecionado(null); }}>
              {icon} {label}
            </button>
          ))}
          <div style={{ marginTop: "auto", padding: "12px 16px" }}>
            <button onClick={onSair} style={{ width: "100%", background: "transparent", border: "0.5px solid rgba(255,255,255,0.25)", color: "#cecbf6", borderRadius: 8, padding: "9px 10px", fontSize: 13, cursor: "pointer" }}>Sair</button>
          </div>
        </div>

        <div style={s.main}>
          {tela === "aprendizado" ? (
            <TelaAprendizado />
          ) : tela === "grupos" ? (
            <TelaGrupos />
          ) : processoSelecionado ? (
            <DetalheProcesso p={processoSelecionado} />
          ) : (
            <>
              <div style={s.topbar}>
                <h1 style={s.h1}>Processos</h1>
                <button style={s.btnPrimary} onClick={() => setModalNovo(true)}>+ Novo processo</button>
              </div>

              <BannerPendencias />
              <div style={s.metrics}>
                <div style={s.metricCard}>
                  <div style={s.metricLabel}>Total</div>
                  <div style={s.metricValue}>{metricas.total || 0}</div>

                </div>
                <div style={s.metricCard}>
                  <div style={s.metricLabel}>Em tramitação</div>
                  <div style={{ ...s.metricValue, color: "#c98a4b" }}>{metricas.tramitacao || 0}</div>

                </div>
                <div style={s.metricCard}>
                  <div style={s.metricLabel}>Com exigência</div>
                  <div style={{ ...s.metricValue, color: "#a8492a" }}>{metricas.exigencia || 0}</div>

                </div>
                <div style={s.metricCard}>
                  <div style={s.metricLabel}>Deferidos</div>
                  <div style={{ ...s.metricValue, color: "#2563eb" }}>{metricas.deferido || 0}</div>

                </div>
                <div style={s.metricCard}>
                  <div style={s.metricLabel}>Finalizados</div>
                  <div style={{ ...s.metricValue, color: "#15803d" }}>{metricas.finalizado || 0}</div>
                </div>
              </div>

              <div
                onDragOver={e => { e.preventDefault(); }}
                onDrop={e => {
                  e.preventDefault();
                  if (!upGrupo) { alert("Selecione o cliente antes de subir."); return; }
                  const items = e.dataTransfer.items;
                  if (items && items.length && items[0].webkitGetAsEntry) {
                    const arquivos = [];
                    let pendentes = 0;
                    const lerEntry = (entry) => {
                      if (entry.isFile) {
                        pendentes++;
                        entry.file(f => { arquivos.push(f); pendentes--; if (pendentes === 0) processarPastaAdmin(arquivos); });
                      } else if (entry.isDirectory) {
                        const reader = entry.createReader();
                        reader.readEntries(ents => { ents.forEach(lerEntry); });
                      }
                    };
                    for (let i = 0; i < items.length; i++) {
                      const entry = items[i].webkitGetAsEntry();
                      if (entry) lerEntry(entry);
                    }
                  } else { processarArquivosAdmin(e.dataTransfer.files); }
                }}
                style={{ border: "1.5px dashed #2d6a70", borderRadius: 12, padding: "18px", marginBottom: 18, background: "#fbfaf6" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
                  <select value={upGrupo} onChange={e => setUpGrupo(e.target.value)} disabled={upSubindo}
                    style={{ padding: "9px 10px", border: "0.5px solid #2563eb", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#2563eb", fontWeight: 500 }}>
                    <option value="">Grupo Empresarial</option>
                    {grupos.map(g => <option key={g.id} value={g.codigo}>{g.nome}</option>)}
                  </select>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "#2563eb", color: "#fff", borderRadius: 8, padding: "9px 16px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: (upSubindo||!upGrupo) ? 0.5 : 1 }}>
                      Selecionar Arquivos
                    </span>
                    <input type="file" accept="application/pdf" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarArquivosAdmin(e.target.files)} />
                  </label>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "transparent", color: "#2563eb", border: "0.5px solid #2563eb", borderRadius: 8, padding: "9px 16px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: (upSubindo||!upGrupo) ? 0.5 : 1 }}>
                      Selecionar Pasta
                    </span>
                    <input type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarPastaAdmin(e.target.files)} />
                  </label>
                  {upSubindo && <span style={{ fontSize: 13, color: "#2563eb" }}>Enviando {upProg.feitos} de {upProg.total}{upProg.erros ? ` (${upProg.erros} erro)` : ""}...</span>}
                </div>
              </div>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#23282a", marginBottom: 12 }}>Processos recentes</div>
              <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
                <input value={fBusca} onChange={e => setFBusca(e.target.value)} placeholder="Buscar empresa..."
                  style={{ flex: "1 1 200px", minWidth: 160, padding: "9px 12px", border: "0.5px solid #e6e0d2", borderRadius: 8, fontSize: 13, outline: "none", fontFamily: "'Inter', sans-serif" }} />
                <select value={fUf} onChange={e => setFUf(e.target.value)} style={{ padding: "9px 10px", border: "0.5px solid #e6e0d2", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#475569" }}>
                  <option value="">UF: todas</option>
                  {ufsDisponiveis.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
                <select value={fAto} onChange={e => setFAto(e.target.value)} style={{ padding: "9px 10px", border: "0.5px solid #e6e0d2", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#475569" }}>
                  <option value="">Ato: todos</option>
                  {atosDisponiveis.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
                <select value={fStatus} onChange={e => setFStatus(e.target.value)} style={{ padding: "9px 10px", border: "0.5px solid #e6e0d2", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#475569" }}>
                  <option value="">Status: todos</option>
                  <option value="aberto">Aberto</option>
                  <option value="tramitacao">Tramitação</option>
                  <option value="exigencia">Exigência</option>
                  <option value="deferido">Deferido</option>
                  <option value="finalizado">Finalizado</option>
                </select>
                <select value={fGrupo} onChange={e => setFGrupo(e.target.value)} style={{ padding: "9px 10px", border: "0.5px solid #2563eb", borderRadius: 8, fontSize: 13, background: "#f4f2ec", cursor: "pointer", color: "#2563eb", fontWeight: 500 }}>
                  <option value="">Cliente: todos</option>
                  {grupos.map(g => <option key={g.id} value={g.id}>{g.nome}</option>)}
                </select>
                {(fBusca || fUf || fAto || fStatus || fGrupo) && (
                  <button onClick={() => { setFBusca(""); setFUf(""); setFAto(""); setFStatus(""); setFGrupo(""); }}
                    style={{ padding: "9px 14px", border: "none", borderRadius: 8, fontSize: 13, background: "#eceae2", color: "#6b6c66", cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>Limpar</button>
                )}
              </div>

              <div style={s.tableWrap}>
                <div style={s.tableHead}>
                  {["Empresa", "UF", "Ato", "Protocolo", "Status", ""].map((h, i) => (
                    <div key={i} style={s.th}>{h}</div>
                  ))}
                </div>
                {processos.length === 0 ? (
                  <div style={{ padding: "32px 16px", textAlign: "center", color: "#94a3b8", fontSize: 13 }}>
                    Nenhum processo ainda. Clique em "Novo processo" para começar.
                  </div>
                ) : processosFiltrados.map(p => (
                  <div key={p.id} style={s.row} onClick={() => setProcessoSelecionado(p)}>
                    <div>
                      <div style={s.company}>{p.empresa}</div>
                      <div style={s.cnpj}>{p.cnpj} · NIRE {p.nire}</div>
                    </div>
                    <div style={{ ...s.cell, fontWeight: 500, color: "#475569" }}>{p.uf || "—"}</div>
                    <div style={s.cell}>{abreviarAto(p.identificador_ato, p.data_ata, p.hora_ata)}</div>
                    <div style={{ ...s.cell, fontFamily: "monospace", fontSize: 11 }}>{p.numero_protocolo ? p.numero_protocolo.replace(/\D/g, "") : "—"}</div>
                    <div><span style={s.badge(p.status)}>{STATUS_CONFIG[p.status]?.label || p.status}</span></div>
                    <div><button style={s.btnVer} onClick={e => { e.stopPropagation(); setProcessoSelecionado(p); }}>Ver</button></div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {modalNovo && (
        <div style={s.overlay} onClick={() => setModalNovo(false)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalTitle}>Novo processo</div>

            {!dadosAnalise ? (
              <div>
                <div style={{ background: "#f8fafc", border: "2px dashed #e2e8f0", borderRadius: 10, padding: 32, textAlign: "center", marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>
                    {analisando ? "Analisando documento..." : "Arraste ou selecione a ata para análise automática"}
                  </div>
                  {!analisando && (
                    <label style={{ cursor: "pointer" }}>
                      <span style={{ background: "#1e40af", color: "#fff", padding: "8px 20px", borderRadius: 8, fontSize: 13 }}>
                        Selecionar arquivo
                      </span>
                      <input type="file" accept=".pdf,.docx,.doc" style={{ display: "none" }}
                        onChange={e => analisarArquivo(e.target.files[0])} />
                    </label>
                  )}
                </div>
              </div>
            ) : (
              <div>
                <div style={{ background: "#dcfce7", border: "0.5px solid #86efac", borderRadius: 8, padding: 10, marginBottom: 16, fontSize: 13, color: "#166534" }}>
                  ✓ Documento analisado pelo Atos
                </div>

                {dadosAnalise.requer_cpl && (
                  <div style={s.alerta}>⚠ CPL necessária antes do protocolo</div>
                )}

                {[
                  { key: "empresa", label: "Empresa" },
                  { key: "cnpj", label: "CNPJ" },
                  { key: "nire", label: "NIRE" },
                  { key: "tipo_ato", label: "Tipo de ato" },
                  { key: "identificador_ato", label: "Identificador" },
                  { key: "data_ata", label: "Data da ata" },
                  { key: "hora_ata", label: "Horário" },
                  { key: "email_cliente", label: "Email do cliente" },
                ].map(({ key, label }) => (
                  <div key={key} style={s.campo}>
                    <label style={s.label}>{label}</label>
                    <input style={s.input} value={dadosAnalise[key] || ""} onChange={e => setDadosAnalise({ ...dadosAnalise, [key]: e.target.value })} />
                  </div>
                ))}

                <div style={s.btnRow}>
                  <button style={s.btnSecondary} onClick={() => { setDadosAnalise(null); setArquivoSelecionado(null); }}>← Refazer</button>
                  <button style={s.btnPrimary} onClick={criarProcesso}>Criar processo</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}


// ===== Portao de login do administrador =====
function getSessaoAdmin() {
  try {
    const s = localStorage.getItem("atos_admin");
    return s ? JSON.parse(s) : null;
  } catch (e) { return null; }
}

const _sa = getSessaoAdmin();
if (_sa && _sa.token) {
  axios.defaults.headers.common["x-token"] = _sa.token;
}

export default function App() {
  const [sessao, setSessao] = useState(getSessaoAdmin());
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [etapa, setEtapa] = useState(1);
  const [codigo, setCodigo] = useState("");

  async function entrar() {
    setErro("");
    if (!login || !senha) { setErro("Preencha login e senha."); return; }
    setCarregando(true);
    try {
      const r = await axios.post(`${API}/login`, { login, senha });
      if (r.data && r.data.requer_2fa) {
        setEtapa(2);
        setCarregando(false);
        return;
      }
      axios.defaults.headers.common["x-token"] = r.data.token;
      localStorage.setItem("atos_admin", JSON.stringify(r.data));
      setSessao(r.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Login ou senha invalidos.");
      else setErro("Erro ao conectar.");
    }
    setCarregando(false);
  }

  async function verificarCodigo() {
    setErro("");
    if (!codigo) { setErro("Digite o codigo recebido por e-mail."); return; }
    setCarregando(true);
    try {
      const r = await axios.post(`${API}/login/verificar`, { login, codigo });
      axios.defaults.headers.common["x-token"] = r.data.token;
      localStorage.setItem("atos_admin", JSON.stringify(r.data));
      setSessao(r.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Codigo invalido ou expirado.");
      else setErro("Erro ao conectar.");
    }
    setCarregando(false);
  }
  function sair() {
    localStorage.removeItem("atos_admin");
    delete axios.defaults.headers.common["x-token"];
    setSessao(null);
    setSenha("");
  }

  if (sessao && sessao.token) {
    if (sessao.is_admin) return <AppPainel onSair={sair} />;
    return <PainelCliente sessao={sessao} onSair={sair} />;
  }

  return (
    <>
      <style>{`
        @keyframes atosWaveMove { 0% { transform: translate(0,0) rotate(0deg); } 50% { transform: translate(-3%,2%) rotate(5deg); } 100% { transform: translate(0,0) rotate(0deg); } }
        @keyframes atosSplashOut { 0%,62% { opacity:1; visibility:visible; } 80%,100% { opacity:0; visibility:hidden; } }
        @keyframes atosLogoIn { 0%,6% { opacity:0; transform: translateY(16px); } 26%,60% { opacity:1; transform: translateY(0); } 76%,100% { opacity:0; transform: translateY(-8px); } }
        @keyframes atosSubIn { 0%,28% { opacity:0; transform: translateY(10px); } 44%,60% { opacity:1; transform: translateY(0); } 76%,100% { opacity:0; transform: translateY(-6px); } }
        @keyframes atosFormIn { 0%,66% { opacity:0; transform: translateY(12px); } 86%,100% { opacity:1; transform: translateY(0); } }
        .atos-splash { position:fixed; inset:0; z-index:50; background:linear-gradient(180deg,#dff3f0 0%,#7fd0d8 38%,#3b82f6 72%,#1e3a8a 100%); display:flex; flex-direction:column; align-items:center; justify-content:center; animation: atosSplashOut 3s ease-in-out forwards; pointer-events:none; }
        .atos-splash-wave { position:absolute; top:-35%; left:-30%; width:80%; height:130%; filter:blur(24px); border-radius:45%; background: radial-gradient(circle at 30% 30%, #2dd4bf, transparent 60%), radial-gradient(circle at 60% 60%, #3b82f6, transparent 55%); animation: atosWaveMove 9s ease-in-out infinite; }
        .atos-splash-logo { position:relative; z-index:2; margin:0; font-size:68px; font-weight:800; color:#111; line-height:1; letter-spacing:-2px; animation: atosLogoIn 3s ease-in-out forwards; }
        .atos-splash-sub { position:relative; z-index:2; margin:12px 0 0; font-size:22px; color:#163a6b; letter-spacing:0.5px; animation: atosSubIn 3s ease-in-out forwards; }
        .atos-login-card { animation: atosFormIn 3s ease-in-out forwards; }
        .atos-bgwave { position:absolute; top:-50%; left:-20%; width:70%; height:120%; filter:blur(40px); border-radius:45%; background: radial-gradient(circle at 40% 40%, rgba(45,212,191,0.45), transparent 62%), radial-gradient(circle at 60% 60%, rgba(59,130,246,0.4), transparent 55%); pointer-events:none; }
      `}</style>
      <div className="atos-splash">
        <div className="atos-splash-wave"></div>
        <div className="atos-splash-logo">atos<span style={{ color: "#d85a30" }}>.</span></div>
        <div className="atos-splash-sub">Gestão Societária</div>
      </div>
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(180deg,#dff3f0 0%,#7fd0d8 38%,#3b82f6 72%,#1e3a8a 100%)", fontFamily: "Inter, sans-serif", position: "relative", overflow: "hidden", padding: "16px" }}>
        <div className="atos-bgwave"></div>
        <div className="atos-login-card" style={{ background: "#fff", borderRadius: 16, padding: 32, width: "100%", maxWidth: 360, boxShadow: "0 10px 50px rgba(20,10,50,0.45)", position: "relative", zIndex: 2, boxSizing: "border-box" }}>
          <div style={{ fontSize: 34, fontWeight: 800, color: "#111111", letterSpacing: -1.5, textAlign: "center" }}>atos<span style={{ color: "#d85a30" }}>.</span></div>
          <div style={{ textAlign: "center", fontSize: 13, color: "#7a7790", marginBottom: 4 }}>Gestão Societária</div>
          <div style={{ textAlign: "center", fontSize: 12, color: "#a09dba", marginBottom: 24 }}>Painel do Administrador</div>
          {erro && <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}
          {etapa === 1 && (<>
          <label style={{ fontSize: 12, color: "#7a7790", marginBottom: 4, display: "block" }}>Login</label>
          <input style={{ width: "100%", padding: "11px 13px", border: "0.5px solid #d9d5ea", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box", background: "#fbfaff" }} value={login} onChange={e => setLogin(e.target.value)} onKeyDown={e => e.key === "Enter" && entrar()} />
          <label style={{ fontSize: 12, color: "#7a7790", marginBottom: 4, display: "block" }}>Senha</label>
          <input style={{ width: "100%", padding: "11px 13px", border: "0.5px solid #d9d5ea", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box", background: "#fbfaff" }} type="password" value={senha} onChange={e => setSenha(e.target.value)} onKeyDown={e => e.key === "Enter" && entrar()} />
          <button style={{ width: "100%", background: "linear-gradient(135deg,#2563eb,#2dd4bf)", color: "#fff", border: "none", padding: "12px", borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4 }} onClick={entrar} disabled={carregando}>{carregando ? "Aguarde..." : "Entrar"}</button></>)}
          {etapa === 2 && (<>
          <div style={{ fontSize: 13, color: "#7a7790", marginBottom: 12 }}>Enviamos um codigo para o seu e-mail. Digite-o abaixo para entrar.</div>
          <label style={{ fontSize: 12, color: "#7a7790", marginBottom: 4, display: "block" }}>Codigo de acesso</label>
          <input style={{ width: "100%", padding: "11px 13px", border: "0.5px solid #d9d5ea", borderRadius: 8, fontSize: 18, letterSpacing: 4, textAlign: "center", outline: "none", marginBottom: 14, boxSizing: "border-box", background: "#fbfaff" }} value={codigo} onChange={e => setCodigo(e.target.value)} onKeyDown={e => e.key === "Enter" && verificarCodigo()} maxLength={6} />
          <button style={{ width: "100%", background: "linear-gradient(135deg,#2563eb,#2dd4bf)", color: "#fff", border: "none", padding: "12px", borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4 }} onClick={verificarCodigo} disabled={carregando}>{carregando ? "Aguarde..." : "Verificar codigo"}</button>
          <button style={{ width: "100%", background: "transparent", color: "#7a7790", border: "none", padding: "10px", fontSize: 13, cursor: "pointer", marginTop: 8 }} onClick={() => { setEtapa(1); setCodigo(""); setErro(""); }}>Voltar</button>
          </>)}
        </div>
      </div>
    </>
  );
}

