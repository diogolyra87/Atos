import { useState, useEffect } from "react";
import axios from "axios";
import { Painel as PainelCliente } from "./Cliente";

const API = "";

const STATUS_CONFIG = {
  recebido: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  tramitacao: { label: "Tramitação", bg: "#f0e0cb", color: "#8a5818" },
  exigencia: { label: "Exigência", bg: "#f0dcd5", color: "#a8492a" },
  aprovado: { label: "Deferido", bg: "#d5e3df", color: "#1f4d52" },
};

function abreviarAto(texto, data) {
  const t = (texto || "").toUpperCase();
  const d = data ? ` ${(data || "").replace(/\//g, ".")}` : "";
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
          <button onClick={criar} disabled={criando} style={{ background: "#1f4d52", color: "#fff", border: "none", padding: "11px 22px", borderRadius: 8, fontSize: 14, cursor: "pointer" }}>{criando ? "Criando e enviando..." : "Criar grupo"}</button>
        </div>
      </div>
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
    if (fStatus && p.status !== fStatus) return false;
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
    sidebar: { width: 220, background: "#1f4d52", display: "flex", flexDirection: "column", padding: "24px 16px", gap: 8 },
    logo: { fontFamily: "'Inter', sans-serif", fontSize: 30, fontWeight: 800, color: "#16151a", letterSpacing: -1.5, lineHeight: 1 },
    nav: (ativo) => ({ display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8, color: ativo ? "#fff" : "#aecaca", background: ativo ? "rgba(255,255,255,0.13)" : "transparent", cursor: "pointer", fontSize: 13, border: "none", width: "100%", textAlign: "left" }),
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
    btnVer: { background: "none", border: "0.5px solid #e2e8f0", borderRadius: 6, padding: "5px 10px", fontSize: 11, color: "#1f4d52", cursor: "pointer" },
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

  function DetalheProcesso({ p }) {
    const eventos = JSON.parse(p.eventos || "[]");
    const checklist = JSON.parse(p.checklist || "[]");
    const [numProtocolo, setNumProtocolo] = useState(p.numero_protocolo || "");
    const [salvandoProt, setSalvandoProt] = useState(false);

    const [textoExig, setTextoExig] = useState(p.texto_exigencia || "");
    const [arqExig, setArqExig] = useState(null);
    const [salvandoExig, setSalvandoExig] = useState(false);

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
          <button style={s.btnSecondary} onClick={() => setProcessoSelecionado(null)}>← Voltar</button>
        </div>

        {p.requer_cpl && (
          <div style={s.alerta}>
            ⚠ CPL necessária — alteração de endereço ou objeto social requer Consulta Prévia de Local na Prefeitura antes de qualquer protocolo.
          </div>
        )}

        <div style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>Alterar status:</div>
        <div style={s.statusRow}>
          {Object.entries(STATUS_CONFIG).map(([key, val]) => (
            <button key={key} style={s.btnStatus(p.status === key)} onClick={() => atualizarStatus(p.id, key)}>
              {val.label}
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
            {p.exigencia_ativa && (
              <button style={{ ...s.btnSecondary, borderColor: "#86efac", color: "#166534" }} onClick={exigenciaCumprida}>
                ✓ Exigência cumprida
              </button>
            )}
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
              {arquivo
                ? <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span style={s.uploadOk}>✓ Anexado</span>
                    <button onClick={() => baixarArquivo(p.id, tipo, (p.empresa||"documento").replace(/[^a-zA-Z0-9]/g,"_"))}
                      style={{ background: "transparent", border: "0.5px solid #1f4d52", color: "#1f4d52", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>↓ Baixar</button>
                  </span>
                : <label style={{ cursor: "pointer" }}>
                    <span style={s.uploadPend}>+ Anexar</span>
                    <input type="file" style={{ display: "none" }} onChange={e => uploadArquivo(p.id, tipo, e.target.files[0])} />
                  </label>
              }
            </div>
          ))}
        </div>

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
            <div style={s.logo}>atos<span style={{ color: "#d85a30" }}>.</span></div>
            <div style={{ fontSize: 11, color: "#6b6c66", marginTop: 4 }}>Gestão Societária</div>
          </div>
          {[
            { key: "processos", icon: "⊞", label: "Processos" },
            { key: "atas", icon: "⊡", label: "Atas recebidas" },
            { key: "cobrancas", icon: "◈", label: "Cobranças" },
            { key: "relatorios", icon: "▦", label: "Relatórios" },
            { key: "grupos", icon: "◉", label: "Grupos" },
          ].map(({ key, icon, label }) => (
            <button key={key} style={s.nav(tela === key)} onClick={() => { setTela(key); setProcessoSelecionado(null); }}>
              {icon} {label}
            </button>
          ))}
          <div style={{ marginTop: "auto", padding: "12px 16px" }}>
            <button onClick={onSair} style={{ width: "100%", background: "transparent", border: "0.5px solid rgba(255,255,255,0.25)", color: "#aecaca", borderRadius: 8, padding: "9px 10px", fontSize: 13, cursor: "pointer" }}>Sair</button>
          </div>
        </div>

        <div style={s.main}>
          {tela === "grupos" ? (
            <TelaGrupos />
          ) : processoSelecionado ? (
            <DetalheProcesso p={processoSelecionado} />
          ) : (
            <>
              <div style={s.topbar}>
                <h1 style={s.h1}>Processos</h1>
                <button style={s.btnPrimary} onClick={() => setModalNovo(true)}>+ Novo processo</button>
              </div>

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
                  <div style={{ ...s.metricValue, color: "#1f4d52" }}>{metricas.aprovado || 0}</div>

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
                        entry.file(f => { arquivos.push(f); pendentes--; if (pendentes === 0) processarArquivosAdmin(arquivos); });
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
                    style={{ padding: "9px 10px", border: "0.5px solid #1f4d52", borderRadius: 8, fontSize: 13, background: "#fff", cursor: "pointer", color: "#1f4d52", fontWeight: 500 }}>
                    <option value="">Grupo Empresarial</option>
                    {grupos.map(g => <option key={g.id} value={g.codigo}>{g.nome}</option>)}
                  </select>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "#1f4d52", color: "#fff", borderRadius: 8, padding: "9px 16px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: (upSubindo||!upGrupo) ? 0.5 : 1 }}>
                      Selecionar Arquivos
                    </span>
                    <input type="file" accept="application/pdf" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarArquivosAdmin(e.target.files)} />
                  </label>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "transparent", color: "#1f4d52", border: "0.5px solid #1f4d52", borderRadius: 8, padding: "9px 16px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: (upSubindo||!upGrupo) ? 0.5 : 1 }}>
                      Selecionar Pasta
                    </span>
                    <input type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarArquivosAdmin(e.target.files)} />
                  </label>
                  {upSubindo && <span style={{ fontSize: 13, color: "#1f4d52" }}>Enviando {upProg.feitos} de {upProg.total}{upProg.erros ? ` (${upProg.erros} erro)` : ""}...</span>}
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
                  <option value="recebido">Aberto</option>
                  <option value="tramitacao">Tramitação</option>
                  <option value="exigencia">Exigência</option>
                  <option value="aprovado">Deferido</option>
                </select>
                <select value={fGrupo} onChange={e => setFGrupo(e.target.value)} style={{ padding: "9px 10px", border: "0.5px solid #1f4d52", borderRadius: 8, fontSize: 13, background: "#f4f2ec", cursor: "pointer", color: "#1f4d52", fontWeight: 500 }}>
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
                    <div style={s.cell}>{abreviarAto(p.identificador_ato, p.data_ata)}</div>
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
                  ✓ Documento analisado pelo Mané
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

  async function entrar() {
    setErro("");
    if (!login || !senha) { setErro("Preencha login e senha."); return; }
    setCarregando(true);
    try {
      const r = await axios.post(`${API}/login`, { login, senha });
      axios.defaults.headers.common["x-token"] = r.data.token;
      localStorage.setItem("atos_admin", JSON.stringify(r.data));
      setSessao(r.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Login ou senha invalidos.");
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
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#23282a", fontFamily: "Inter, sans-serif" }}>
      <div style={{ background: "#fff", borderRadius: 12, padding: 36, width: 340, boxShadow: "0 10px 40px rgba(0,0,0,0.3)" }}>
        <div style={{ fontSize: 30, fontWeight: 800, color: "#16151a", letterSpacing: -1.5, textAlign: "center" }}>atos<span style={{ color: "#d85a30" }}>.</span></div>
        <div style={{ textAlign: "center", fontSize: 13, color: "#64748b", marginBottom: 24 }}>Acesso ao sistema</div>
        {erro && <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}
        <label style={{ fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" }}>Login</label>
        <input style={{ width: "100%", padding: "10px 12px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box" }} value={login} onChange={e => setLogin(e.target.value)} onKeyDown={e => e.key === "Enter" && entrar()} />
        <label style={{ fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" }}>Senha</label>
        <input style={{ width: "100%", padding: "10px 12px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box" }} type="password" value={senha} onChange={e => setSenha(e.target.value)} onKeyDown={e => e.key === "Enter" && entrar()} />
        <button style={{ width: "100%", background: "#1f4d52", color: "#fff", border: "none", padding: "11px", borderRadius: 8, fontSize: 14, cursor: "pointer", marginTop: 4 }} onClick={entrar} disabled={carregando}>{carregando ? "Aguarde..." : "Entrar"}</button>
      </div>
    </div>
  );
}
