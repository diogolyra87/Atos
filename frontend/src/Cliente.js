import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";

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
  const [modo, setModo] = useState(codigoGrupo ? "cadastro" : "login");
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [carregando, setCarregando] = useState(false);
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
      setModo("login"); setSenha(""); setAviso("Cadastro realizado! Faça login para entrar.");
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
      salvarSessao(res.data);
    } catch (e) {
      if (e.response && e.response.status === 401) setErro("Login ou senha inválidos.");
      else setErro("Erro ao conectar.");
    }
    setCarregando(false);
  }

  if (sessao) return <Painel sessao={sessao} onSair={limparSessao} />;

  const ehCadastro = modo === "cadastro";
  const s = estilos();
  return (
    <>
      <div style={s.wrap}>
        <div style={s.card}>
          <div style={s.logo}>Mané</div>
          <div style={s.sub}>{ehCadastro ? "Criar acesso" : "Área do cliente"}</div>
          {erro && <div style={s.erro}>{erro}</div>}
          {aviso && <div style={s.aviso}>{aviso}</div>}
          {ehCadastro && codigoGrupo && <div style={s.grupoBox}>Cadastro para o grupo: <strong>{codigoGrupo}</strong></div>}
          <label style={s.label}>Login</label>
          <input style={s.input} value={login} onChange={e => setLogin(e.target.value)}
            onKeyDown={e => e.key === "Enter" && (ehCadastro ? cadastrar() : entrar())} />
          <label style={s.label}>Senha</label>
          <input style={s.input} type="password" value={senha} onChange={e => setSenha(e.target.value)}
            onKeyDown={e => e.key === "Enter" && (ehCadastro ? cadastrar() : entrar())} />
          <button style={s.btn} onClick={ehCadastro ? cadastrar : entrar} disabled={carregando}>
            {carregando ? "Aguarde..." : (ehCadastro ? "Cadastrar" : "Entrar")}
          </button>
        </div>
      </div>
    </>
  );
}

export function Painel({ sessao, onSair }) {
  const [processos, setProcessos] = useState([]);
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
  const ufsDisponiveis = [...new Set(processos.map(p => p.uf).filter(Boolean))].sort();
  const atosDisponiveis = [...new Set(processos.map(p => abreviarAto(p.identificador_ato, "").split(" ")[0]).filter(Boolean))].sort();
  const processosFiltrados = processos.filter(p => {
    if (fBusca && !(p.empresa || "").toLowerCase().includes(fBusca.toLowerCase())) return false;
    if (fUf && p.uf !== fUf) return false;
    if (fStatus && p.status !== fStatus) return false;
    if (fAto && abreviarAto(p.identificador_ato, "").split(" ")[0] !== fAto) return false;
    return true;
  });
  const s = estilos();
  useEffect(() => { carregar(); }, []);
  async function carregar() {
    setCarregando(true); setErro("");
    try {
      const res = await axios.get(`${API}/processos`, { headers: { "x-token": sessao.token } });
      setProcessos(res.data);
    } catch (e) {
      if (e.response && e.response.status === 401) { onSair(); return; }
      setErro("Erro ao carregar processos.");
    }
    setCarregando(false);
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
  async function processarArquivos(fileList) {
    const arquivos = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (arquivos.length === 0) { alert("Nenhum PDF encontrado na pasta."); return; }
    setSubindo(true);
    setProgresso({ feitos: 0, total: arquivos.length, erros: 0 });
    let feitos = 0, erros = 0;
    for (const arq of arquivos) {
      try {
        const fd1 = new FormData();
        fd1.append("arquivo", arq);
        const ana = await axios.post(`${API}/processos/analisar`, fd1, { headers: { "x-token": sessao.token } });
        const dados = ana.data || {};
        const fd2 = new FormData();
        fd2.append("arquivo", arq);
        fd2.append("dados", JSON.stringify(dados));
        await axios.post(`${API}/processos`, fd2, { headers: { "x-token": sessao.token } });
        feitos++;
      } catch (e) {
        erros++;
      }
      setProgresso({ feitos, total: arquivos.length, erros });
    }
    setSubindo(false);
    await carregar();
    alert(`Concluido: ${feitos} processo(s) criado(s)${erros ? `, ${erros} com erro` : ""}.`);
  }
  function clicarStatus(p) {
    if (p.status === "exigencia") setExigenciaAberta(p);
    else if (p.status === "aprovado") baixar(p.id, "registro", (p.empresa || "registro").replace(/[^a-zA-Z0-9]/g, "_"));
    else setDocsAbertos(p);
  }
  return (
    <>
      <div style={s.appCliente}>
        <aside style={s.sidebar}>
          <div style={s.brandBox}>
            <div style={s.logoSide}>atos<span style={{ color: "#d85a30" }}>.</span></div>
            <div style={s.tagSide}>Gestão Societária</div>
          </div>
          <nav style={s.navBox}>
            <button style={s.navItem(tela === "processos")} onClick={() => setTela("processos")}>Processos</button>
            <button style={s.navItem(tela === "relatorios")} onClick={() => setTela("relatorios")}>Relatorios</button>
          </nav>
          <div style={s.sideFoot}>
            <div style={s.sideGrupo}>{sessao.grupo}</div>
            <button style={{ ...s.btnSair, marginTop: 10, alignSelf: "flex-start" }} onClick={onSair}>Sair</button>
          </div>
        </aside>
        <main style={s.mainCliente}>
          {tela === "processos" ? (
            <div style={s.conteudo}>
              <div style={s.h1}>Meus Processos</div>
              <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
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
                  <option value="tramitacao">Tramitacao</option>
                  <option value="exigencia">Exigencia</option>
                  <option value="aprovado">Deferido</option>
                </select>
                {(fBusca || fUf || fAto || fStatus) && (
                  <button onClick={() => { setFBusca(""); setFUf(""); setFAto(""); setFStatus(""); }}
                    style={{ padding: "9px 14px", border: "none", borderRadius: 8, fontSize: 13, background: "#eceae2", color: "#6b6c66", cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>Limpar</button>
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
                    const lerEntry = (entry) => {
                      if (entry.isFile) {
                        pendentes++;
                        entry.file(f => { arquivos.push(f); pendentes--; if (pendentes === 0) processarArquivos(arquivos); });
                      } else if (entry.isDirectory) {
                        const reader = entry.createReader();
                        reader.readEntries(ents => { ents.forEach(lerEntry); });
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
                style={{ border: "1.5px dashed #2d6a70", borderRadius: 12, padding: "20px", marginBottom: 18, background: "#fbfaf6", textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#6b6c66", marginBottom: 12 }}>
                  {subindo
                    ? `Enviando... ${progresso.feitos} de ${progresso.total}${progresso.erros ? ` (${progresso.erros} com erro)` : ""}`
                    : ""}
                </div>
                <div style={{ display: "inline-flex", gap: 10 }}>
                  <label style={{ display: "inline-block", cursor: subindo ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "#1f4d52", color: "#fff", borderRadius: 8, padding: "9px 18px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: subindo ? 0.6 : 1 }}>
                      {subindo ? "Enviando..." : "Selecionar Arquivos"}
                    </span>
                    <input type="file" accept="application/pdf" multiple style={{ display: "none" }}
                      disabled={subindo}
                      onChange={e => processarArquivos(e.target.files)} />
                  </label>
                  <label style={{ display: "inline-block", cursor: subindo ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "transparent", color: "#1f4d52", border: "0.5px solid #1f4d52", borderRadius: 8, padding: "9px 18px", fontSize: 13, fontFamily: "'Inter', sans-serif", opacity: subindo ? 0.6 : 1 }}>
                      Selecionar Pastas
                    </span>
                    <input type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
                      disabled={subindo}
                      onChange={e => processarArquivos(e.target.files)} />
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
                    {processosFiltrados.map(p => (
                      <div key={p.id} style={s.row}>
                        <div>
                          <div style={s.empresa}>{p.empresa}</div>
                          <div style={s.metaEmp}>{p.cnpj}{p.nire ? ` · NIRE ${p.nire}` : ""}</div>
                        </div>
                        <div style={s.cell}>{p.uf || "—"}</div>
                        <div style={s.cell}>{abreviarAto(p.identificador_ato, p.data_ata)}</div>
                        <div style={{ ...s.cell, fontFamily: "monospace", fontSize: 11 }}>{p.numero_protocolo ? p.numero_protocolo.replace(/\D/g, "") : "—"}</div>
                        <div>
                          <span onClick={() => clicarStatus(p)}
                            style={{ ...s.badge, background: (STATUS_CONFIG[p.status]?.bg||"#f1f5f9"), color: (STATUS_CONFIG[p.status]?.color||"#475569"),
                              cursor: "pointer" }}>
                            {STATUS_CONFIG[p.status]?.label || p.status}
                            {p.status === "exigencia" ? " ›" : " ↓"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
            </div>
          ) : (
            <div style={s.conteudo}>
              <div style={s.h1}>Relatorios</div>
              <div style={{ fontSize: 13, color: "#6b6c66", marginBottom: 20 }}>Gere uma planilha dos seus processos por situacao. Baixe agora; o envio por email estara disponivel em breve.</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
                {[
                  { st: "todos", lb: "Todos os Processos" },
                  { st: "aprovado", lb: "Atos Deferidos" },
                  { st: "exigencia", lb: "Atos em Exigência" },
                  { st: "tramitacao", lb: "Atos em Tramitação" },
                  { st: "recebido", lb: "Atos Abertos" },
                ].map(r => (
                  <div key={r.st} style={{ background: "#fff", border: "0.5px solid #e6e0d2", borderRadius: 12, padding: 18 }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: "#23282a", marginBottom: 14 }}>{r.lb}</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => baixarRelatorio(r.st)} style={{ flex: 1, background: "#1f4d52", color: "#fff", border: "none", borderRadius: 8, padding: "9px 12px", fontSize: 13, cursor: "pointer", fontFamily: "'Inter', sans-serif" }}>Baixar planilha</button>
                      <button disabled title="Disponivel em breve" style={{ background: "#eceae2", color: "#a8a395", border: "none", borderRadius: 8, padding: "9px 12px", fontSize: 13, cursor: "not-allowed", fontFamily: "'Inter', sans-serif" }}>Enviar email</button>
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
              <div style={s.modalBtns}>
                <button style={s.btnFechar} onClick={() => setDocsAbertos(null)}>Fechar</button>
              </div>
            </div>
          </div>
        );
      })()}
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
    appCliente: { display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh", fontFamily: "'Inter', sans-serif", background: "#f4f2ec" },
    sidebar: { background: "#1f4d52", display: "flex", flexDirection: "column" },
    brandBox: { margin: "20px 18px 10px", padding: "16px 18px", background: "#f4f2ec", borderRadius: 12 },
    logoSide: { fontFamily: "'Inter', sans-serif", fontSize: 30, fontWeight: 800, color: "#16151a", letterSpacing: -1.5, lineHeight: 1 },
    tagSide: { fontSize: 11, color: "#6b6c66", marginTop: 4 },
    navBox: { padding: "18px 16px", flex: 1, display: "flex", flexDirection: "column", gap: 4 },
    navItem: (ativo) => ({ display: "block", width: "100%", textAlign: "left", padding: "11px 14px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 14, fontWeight: 500, fontFamily: "'Inter', sans-serif", color: ativo ? "#fff" : "#aecaca", background: ativo ? "rgba(255,255,255,0.13)" : "transparent" }),
    sideFoot: { padding: "18px 24px", borderTop: "1px solid rgba(255,255,255,0.10)", display: "flex", flexDirection: "column", alignItems: "flex-start" },
    sideGrupo: { fontSize: 13, color: "#fff", fontWeight: 500 },
    sideLogin: { fontSize: 12, color: "#8fb0b0", marginBottom: 10 },
    mainCliente: { overflowY: "auto" },
    wrap: { minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#23282a", fontFamily: "'Inter', sans-serif" },
    card: { background: "#fff", borderRadius: 12, padding: 36, width: 340, boxShadow: "0 10px 40px rgba(0,0,0,0.3)" },
    logo: { fontFamily: "'DM Serif Display', serif", fontSize: 52, color: "#1f4d52", textAlign: "center", lineHeight: 1 },
    sub: { textAlign: "center", fontSize: 13, color: "#64748b", marginBottom: 24 },
    label: { fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" },
    input: { width: "100%", padding: "10px 12px", border: "0.5px solid #cbd5e1", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box" },
    btn: { width: "100%", background: "#1f4d52", color: "#fff", border: "none", padding: "11px", borderRadius: 8, fontSize: 14, cursor: "pointer", marginTop: 4 },
    erro: { background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 },
    aviso: { background: "#dcfce7", color: "#166534", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 },
    grupoBox: { background: "#e8efee", color: "#1f4d52", borderRadius: 8, padding: "8px 12px", fontSize: 12, marginBottom: 14, textAlign: "center" },
    btnSair: { background: "none", border: "0.5px solid #334155", color: "#94a3b8", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" },
    conteudo: { padding: 28, maxWidth: 920, margin: "0 auto" },
    h1: { fontSize: 18, fontWeight: 500, color: "#23282a", marginBottom: 18 },
    vazio: { background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, padding: "40px 16px", textAlign: "center", color: "#94a3b8", fontSize: 14 },
    tabela: { background: "#fff", border: "0.5px solid #e2e8f0", borderRadius: 12, overflow: "hidden" },
    thead: { display: "grid", gridTemplateColumns: "2.5fr 0.5fr 1.3fr 1.2fr 1fr", padding: "10px 16px", background: "#f1f5f9", borderBottom: "0.5px solid #e2e8f0" },
    th: { fontSize: 11, fontWeight: 500, color: "#64748b" },
    row: { display: "grid", gridTemplateColumns: "2.5fr 0.5fr 1.3fr 1.2fr 1fr", padding: "13px 16px", borderBottom: "0.5px solid #f1f5f9", alignItems: "center" },
    empresa: { fontSize: 13, fontWeight: 500, color: "#23282a" },
    metaEmp: { fontFamily: "monospace", fontSize: 11, color: "#94a3b8", marginTop: 2 },
    cell: { fontSize: 12, color: "#475569" },
    badge: { display: "inline-block", padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 500 },
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 },
    modal: { background: "#fff", borderRadius: 12, padding: 28, width: 480, maxHeight: "80vh", overflowY: "auto" },
    modalTitle: { fontSize: 16, fontWeight: 500, color: "#23282a", marginBottom: 16 },
    exigTexto: { background: "#fef2f2", border: "0.5px solid #fecaca", borderRadius: 8, padding: 14, fontSize: 14, color: "#7f1d1d", lineHeight: 1.5, marginBottom: 18, whiteSpace: "pre-wrap" },
    modalBtns: { display: "flex", gap: 10, justifyContent: "flex-end" },
    btnDl: { background: "#e8efee", color: "#1f4d52", border: "0.5px solid #c5d8d5", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer" },
    btnFechar: { background: "#1f4d52", color: "#fff", border: "none", borderRadius: 8, padding: "8px 18px", fontSize: 13, cursor: "pointer" },
  };
}