import { useState, useEffect } from "react";
import axios from "axios";
import { Painel as PainelCliente } from "./Cliente";
import { STATUS_CONFIG, formatarDataExtenso, BotaoIatos, IatosChat, subtituloProcesso, SidebarAtos, IconeProcessos, IconeGrupos, IconeAprendizado, DonutStatusCard, TelaLogin, FONTE_CORPO, FONTE_TITULO, FluxoDoDiaCardEscuro, AtividadeRecenteEscura, useBreakpoint } from "./components/Compartilhados";

const API = "";

// Mantido em sincronia manual com TIPOS_ATO_VALIDOS em backend/main.py
const TIPOS_ATO_OPCOES = ["AGO", "AGE", "AGOE", "RCA", "ARD", "ARS", "Alteração Contratual"];

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

// Componente proprio (fora de AppPainel) para o poll de fluxo/eventos: assim
// o tick de 5s so re-renderiza este pedaco, sem recriar DetalheProcesso nem
// ChatProcesso (que sao definidos dentro de AppPainel e perdiam estado local
// - secao fechava e texto digitado sumia sozinho - toda vez que AppPainel
// re-renderizava por causa desse poll).
function ExtraFluxoEAtividade() {
  const [fluxosAtivos, setFluxosAtivos] = useState([]);
  const [eventosRecentes, setEventosRecentes] = useState([]);

  useEffect(() => {
    async function carregarFluxos() {
      try {
        const r = await axios.get(`${API}/fluxo/ativo`);
        setFluxosAtivos(Array.isArray(r.data) ? r.data : []);
      } catch (e) {}
    }
    carregarFluxos();
    const _t = setInterval(carregarFluxos, 5000);
    return () => clearInterval(_t);
  }, []);

  useEffect(() => {
    async function carregarEventos() {
      try {
        const r = await axios.get(`${API}/eventos/recentes`, { params: { limit: 5 } });
        setEventosRecentes(r.data || []);
      } catch (e) {}
    }
    carregarEventos();
    const _t = setInterval(carregarEventos, 5000);
    return () => clearInterval(_t);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%" }}>
      {fluxosAtivos.length > 0 && fluxosAtivos.map(f => <FluxoDoDiaCardEscuro key={f.grupo_id} fluxo={f} />)}
      <AtividadeRecenteEscura eventos={eventosRecentes} />
    </div>
  );
}

function AppPainel({ onSair, sessao }) {
  const bp = useBreakpoint();
  const mobile = bp === "mobile";
  const ehOperador = sessao && sessao.papel === "operador" && !sessao.is_admin;
  const [processos, setProcessos] = useState([]);
  const [metricas, setMetricas] = useState({});
  const [tela, setTela] = useState("processos");
  const [processoSelecionado, setProcessoSelecionado] = useState(null);
  const [iatosAberto, setIatosAberto] = useState(null);
  const [modalNovo, setModalNovo] = useState(false);
  const [fBusca, setFBusca] = useState("");
  const [fUf, setFUf] = useState("");
  const [fAto, setFAto] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fGrupo, setFGrupo] = useState("");
  const [grupos, setGrupos] = useState([]);
  // Precisa viver aqui (no componente estavel), nao dentro de
  // ListaProcessosAgrupada: essa funcao e recriada a cada render de
  // AppPainel() (esta definida no corpo dele), entao um useState local nela
  // reiniciava pra {} (tudo aberto) a cada atualizacao de estado do
  // componente pai - era por isso que uma secao recolhida "voltava a abrir
  // sozinha" (mesmo bug corrigido em Cliente.js).
  const [gruposFechados, setGruposFechados] = useState({});
  const [upGrupo, setUpGrupo] = useState("");
  const [upSubindo, setUpSubindo] = useState(false);
  const [upProg, setUpProg] = useState({ feitos: 0, total: 0, erros: 0 });
  useEffect(() => { axios.get(`${API}/grupos`).then(r => setGrupos(r.data)).catch(() => {}); }, []);



  const ufsDisponiveis = [...new Set(processos.map(p => p.uf).filter(Boolean))].sort();
  const atosDisponiveis = [...new Set(processos.map(p => abreviarAto(p.identificador_ato, "").split(" ")[0]).filter(Boolean))].sort();
  // Nome do grupo (cliente) por grupo_id, pra busca por texto tambem achar
  // pelo nome do cliente/holding, nao so' pela razao social da empresa do
  // processo - um grupo pode ter varias empresas/subsidiarias com nomes
  // bem diferentes do nome do cliente (ex: PROFARMA tem 8 razoes sociais
  // distintas, so' 2 contem "PROFARMA" no nome; buscar "profarma" escondia
  // os outros 6 processos do mesmo cliente sem nenhum erro - achado no
  // incidente de 01/09/2026, processo MN-20260825145626-E8DC/Drogaria
  // Cipriano Santa Rosa).
  const nomeGrupoPorId = Object.fromEntries(grupos.map(g => [g.id, (g.nome || "").toLowerCase()]));
  const processosFiltrados = processos.filter(p => {
    if (fBusca) {
      const termo = fBusca.toLowerCase();
      const casaEmpresa = (p.empresa || "").toLowerCase().includes(termo);
      const casaGrupo = (nomeGrupoPorId[p.grupo_id] || "").includes(termo);
      if (!casaEmpresa && !casaGrupo) return false;
    }
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

  async function processarGrupoPastaAdmin(arquivos, extras) {
    extras = extras || [];
    const fdA = new FormData();
    arquivos.forEach(a => fdA.append("arquivos", a));
    fdA.append("codigo_grupo", upGrupo);
    const res = await axios.post(`${API}/processos/analisar-pasta-multi`, fdA);
    const r = res.data || {};
    const principais = r.principais || [];
    const anexosGrupo = (r.anexos || []).map(ax => arquivos[ax.indice]).concat(extras);
    let criados = 0, anexosOk = 0, anexosErro = 0;
    for (const principal of principais) {
      const dados = principal.dados || {};
      dados.codigo_grupo = upGrupo;
      if (!principal.tipo_sugerido) {
        const ok = window.confirm("AVISO\n\nDocumento Sem Valor Societario!\n\nPossivel Anexo ou Documento Complementar!\n\n(" + principal.nome + ")\n\nDeseja Seguir Com a Insercao?");
        if (!ok) { continue; }
        dados.uf = "";
        if (!dados.empresa) { dados.empresa = "Documento desconhecido"; dados.identificador_ato = "Documento desconhecido"; }
      }
      if (r.confirmacao_pendente) { dados.confirmacao_pendente = true; dados.tipo_ato_sugerido = principal.tipo_sugerido || ""; }
      const segueDup = await checarDup(dados);
      if (!segueDup) { continue; }
      const fd2 = new FormData();
      fd2.append("arquivo", arquivos[principal.indice]);
      fd2.append("dados", JSON.stringify(dados));
      const criado = await axios.post(`${API}/processos`, fd2);
      const novoId = criado.data && (criado.data.id || criado.data.processo_id);
      criados++;
      if (novoId) {
        for (const arqAnexo of anexosGrupo) {
          try {
            const fda = new FormData();
            fda.append("arquivo", arqAnexo);
            fda.append("descricao", "");
            await axios.post(`${API}/processos/${novoId}/anexos`, fda, { headers: { "Content-Type": "multipart/form-data" } });
            anexosOk++;
          } catch (e) { anexosErro++; }
        }
      }
    }
    return { criados, anexosOk, anexosErro };
  }

  async function processarPastaAdmin(fileList) {
    if (!upGrupo) { alert("Selecione o cliente antes de subir os arquivos."); return; }
    const arquivos = Array.from(fileList).filter(f => {
      const n = f.name.toLowerCase();
      return n.endsWith(".pdf") || n.endsWith(".docx") || n.endsWith(".png") || n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".xml") || n.endsWith(".txt");
    });
    if (arquivos.length === 0) { alert("Nenhum arquivo valido na pasta."); return; }
    if (arquivos.length === 1) { return processarArquivosAdmin(fileList); }
    const grupos = agruparPorPasta(arquivos);
    let chaves = Object.keys(grupos);
    let extrasDaRaiz = [];
    const temSubpastas = chaves.some(k => k !== "(raiz)");
    if (temSubpastas && grupos["(raiz)"]) {
      const raizArquivos = grupos["(raiz)"];
      try {
        const fdR = new FormData();
        raizArquivos.forEach(a => fdR.append("arquivos", a));
        fdR.append("pre_classificacao", "true");
        const resR = await axios.post(`${API}/processos/analisar-pasta-multi`, fdR);
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
    setUpSubindo(true);
    setUpProg({ feitos: 0, total: chaves.length, erros: 0 });
    let totalCriados = 0, totalAnexosOk = 0, totalAnexosErro = 0, gruposErro = 0;
    for (let i = 0; i < chaves.length; i++) {
      try {
        const extras = chaves[i] === "(raiz-principal)" ? [] : extrasDaRaiz;
        const res = await processarGrupoPastaAdmin(grupos[chaves[i]], extras);
        totalCriados += res.criados;
        totalAnexosOk += res.anexosOk;
        totalAnexosErro += res.anexosErro;
      } catch (e) {
        gruposErro++;
      }
      setUpProg({ feitos: i + 1, total: chaves.length, erros: gruposErro });
    }
    setUpSubindo(false);
    carregar();
    alert(`Concluido: ${totalCriados} processo(s) criado(s) em ${chaves.length} pasta(s). Anexos: ${totalAnexosOk}${totalAnexosErro ? ` (${totalAnexosErro} falharam)` : ""}.${gruposErro ? ` ${gruposErro} pasta(s) com erro.` : ""}`);
  }
  async function checarDup(dados) {
    if (dados.duplicado_envelope) {
      return window.confirm("ATENÇÃO: este documento tem o mesmo Envelope DocuSign de um processo já existente (" + (dados.processo_id_existente || "") + ").\n\nQuase certamente é o mesmo ato enviado de novo.\n\nDeseja seguir com a inserção mesmo assim?");
    }
    try {
      const params = {
        empresa: dados.empresa || "", tipo_ato: dados.tipo_ato || "",
        data_ata: dados.data_ata || "", hora_ata: dados.hora_ata || "",
        identificador_ato: dados.identificador_ato || "",
        excluir_processo_id: dados.processo_id || "",
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
        fd1.append("codigo_grupo", upGrupo);
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
  const s = {
    layout: { display: "flex", minHeight: "100vh", fontFamily: FONTE_CORPO, background: "#060608", color: "#e4e4e7", WebkitFontSmoothing: "antialiased" },
    main: { flex: 1, minWidth: 0, padding: mobile ? "16px" : "32px 40px", overflowY: "auto" },
    topBar: { display: "flex", justifyContent: "flex-end", alignItems: "center", marginBottom: 20 },
    btnSair: { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", color: "#d4d4d8", borderRadius: 24, padding: "6px 16px", fontSize: 12.5, cursor: "pointer", fontFamily: FONTE_CORPO },
    topbar: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 },
    h1: { fontFamily: FONTE_TITULO, fontSize: 24, fontWeight: 700, color: "#fff", margin: 0 },
    btnPrimary: { background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", border: "none", padding: "9px 18px", borderRadius: 9, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, boxShadow: "0 4px 16px rgba(77,148,255,0.3)", fontFamily: FONTE_CORPO },
    filtro: { padding: "9px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11.5, background: "rgba(255,255,255,0.05)", cursor: "pointer", color: "#d4d4d8", fontFamily: FONTE_CORPO },
    tableWrap: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 18, overflow: "hidden" },
    tableScroll: { overflowX: "auto" },
    // Ultima coluna precisa caber o botao "Ver" + o BotaoIatos inteiro (icone +
    // "iatos." + "Posso ajudar?") - 70px (herdado de uma versao anterior sem
    // esse botao) cortava o iatos. na borda direita da tabela. minWidth no
    // container junto com tableScroll (overflow-x) garante que nunca aperta
    // a ponto de cortar, mesmo em telas menores (scroll horizontal em vez de
    // corte, conforme pedido).
    tableHead: { display: "grid", gridTemplateColumns: "2.2fr 0.5fr 1.2fr 1fr 0.9fr 290px", padding: "10px 20px", background: "rgba(255,255,255,0.02)", borderBottom: "1px solid rgba(255,255,255,0.06)", minWidth: 900 },
    th: { fontSize: 10.5, fontWeight: 500, color: "#62666d", textTransform: "uppercase", letterSpacing: 0.4 },
    row: { display: "grid", gridTemplateColumns: "2.2fr 0.5fr 1.2fr 1fr 0.9fr 290px", padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.04)", alignItems: "center", cursor: "pointer", minWidth: 900 },
    company: { fontSize: 13.5, fontWeight: 600, color: "#fff", margin: "0 0 3px" },
    cnpj: { fontSize: 11, color: "#71717a", margin: 0 },
    cell: { fontSize: 13, color: "#d4d4d8" },
    badge: (status) => ({ display: "inline-block", padding: "4px 11px", borderRadius: 20, fontSize: 11, background: STATUS_CONFIG[status]?.bg || "rgba(255,255,255,0.06)", color: STATUS_CONFIG[status]?.color || "#d4d4d8", border: `1px solid ${STATUS_CONFIG[status]?.borda || "rgba(255,255,255,0.15)"}` }),
    // Badge de email_status (ver notificar_cliente_processo em main.py) -
    // so aparece quando o processo NAO seguiu o caminho normal de aviso ao
    // cliente (suprimido de proposito, ou tentou e falhou). Antes da
    // supressao de SP de 30/07/2026 ficar visivel aqui, nao havia nenhum
    // jeito de saber pelo painel que um processo estava com aviso pendente.
    badgeEmail: (tipo) => ({ display: "inline-block", padding: "3px 9px", borderRadius: 20, fontSize: 10.5, marginLeft: 6, background: tipo === "falhou" ? "rgba(255,69,58,0.12)" : "rgba(255,159,10,0.12)", color: tipo === "falhou" ? "#ff6b60" : "#ffc266", border: `1px solid ${tipo === "falhou" ? "rgba(255,69,58,0.3)" : "rgba(255,159,10,0.3)"}` }),
    btnVer: { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 8, padding: "9px 16px", fontSize: 12, color: "#d4d4d8", cursor: "pointer", fontFamily: FONTE_CORPO },
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 },
    modal: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: 28, width: 560, maxHeight: "80vh", overflowY: "auto", color: "#e4e4e7" },
    modalTitle: { fontFamily: FONTE_TITULO, fontSize: 16, fontWeight: 700, color: "#fff", marginBottom: 20 },
    campo: { marginBottom: 14 },
    label: { fontSize: 12, color: "#a8b0d8", marginBottom: 4, display: "block" },
    input: { width: "100%", padding: "8px 12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, fontSize: 13, outline: "none", background: "rgba(255,255,255,0.05)", color: "#fff", boxSizing: "border-box" },
    btnRow: { display: "flex", gap: 10, marginTop: 20, justifyContent: "flex-end" },
    btnSecondary: { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "9px 18px", fontSize: 13, cursor: "pointer", color: "#d4d4d8", fontFamily: FONTE_CORPO },
    detalhe: { background: "#0e0e14", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: mobile ? 16 : 24 },
    detalheHeader: { display: "flex", flexDirection: mobile ? "column" : "row", gap: mobile ? 12 : 0, justifyContent: "space-between", alignItems: mobile ? "stretch" : "flex-start", marginBottom: 20 },
    detalheTitle: { fontFamily: FONTE_TITULO, fontSize: 18, fontWeight: 700, color: "#fff" },
    detalheGrid: { display: "grid", gridTemplateColumns: mobile ? "1fr" : "1fr 1fr", gap: 16, marginBottom: 20 },
    detalheItem: { background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 12 },
    detalheItemLabel: { fontSize: 10.5, color: "#71717a", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 },
    detalheItemValue: { fontSize: 13, color: "#e4e4e7", fontWeight: 500 },
    alerta: { background: "rgba(255,159,10,0.1)", border: "1px solid rgba(255,159,10,0.3)", borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: "#ffc266" },
    statusRow: { display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" },
    btnStatus: (ativo) => ({ padding: "7px 16px", borderRadius: 20, fontSize: 12, cursor: "pointer", border: ativo ? "1px solid rgba(255,159,10,0.4)" : "1px solid rgba(255,255,255,0.1)", background: ativo ? "rgba(255,159,10,0.15)" : "transparent", color: ativo ? "#ff9f0a" : "#71717a", boxShadow: ativo ? "0 0 14px rgba(255,159,10,0.15)" : "none" }),
    uploadRow: { display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 },
    uploadItem: { display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "10px 14px" },
    uploadLabel: { fontSize: 13, color: "#a8b0d8" },
    uploadOk: { fontSize: 12, color: "#00e691", background: "rgba(0,255,170,0.12)", padding: "3px 10px", borderRadius: 20 },
    uploadPend: { fontSize: 12, color: "#8a90b8", background: "rgba(255,255,255,0.06)", padding: "3px 10px", borderRadius: 20 },
    checklist: { background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 14, marginBottom: 16 },
    checkItem: { fontSize: 13, color: "#c4c8e4", padding: "4px 0", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 8 },
  };

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
                <span style={{ fontSize: 11, color: "#62666d" }}>{aberto ? "▾" : "▸"}</span>
                {label}
                <span style={{ fontSize: 11, color: "#62666d", fontWeight: 400 }}>({itens.length})</span>
              </div>
              {aberto && itens.map(p => mobile ? (
                // Mobile: tabela vira card empilhado - mesmo dado, layout vertical.
                <div key={p.id} onClick={() => setProcessoSelecionado(p)}
                  style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.04)", display: "flex", flexDirection: "column", gap: 10, cursor: "pointer" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                    <div>
                      <div style={s.company}>{p.empresa}</div>
                      <div style={s.cnpj}>{subtituloProcesso(p)}</div>
                    </div>
                    <span style={{ ...s.badge(p.status), flexShrink: 0 }}>{STATUS_CONFIG[p.status]?.label || p.status}</span>
                  </div>
                  {(p.email_status === "pendente_revisao" || p.email_status === "falhou") && (
                    <span style={s.badgeEmail(p.email_status)}>{p.email_status === "falhou" ? "E-mail ao cliente: falhou" : "E-mail ao cliente pendente"}</span>
                  )}
                  <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#8a90b8" }}>
                    <span>UF: <span style={{ color: "#d4d4d8" }}>{p.uf || "—"}</span></span>
                    <span>Protocolo: <span style={{ color: "#d4d4d8", fontFamily: "monospace" }}>{p.numero_protocolo || "—"}</span></span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button style={{ ...s.btnVer, flex: 1 }} onClick={e => { e.stopPropagation(); setProcessoSelecionado(p); }}>Ver</button>
                    <div onClick={e => e.stopPropagation()}><BotaoIatos processo={p} onAbrir={setIatosAberto} /></div>
                  </div>
                </div>
              ) : (
                <div key={p.id} style={s.row} onClick={() => setProcessoSelecionado(p)}>
                  <div>
                    <div style={s.company}>{p.empresa}</div>
                    <div style={s.cnpj}>{subtituloProcesso(p)}</div>
                  </div>
                  <div style={{ ...s.cell, fontWeight: 500 }}>{p.uf || "—"}</div>
                  <div style={s.cell}>{abreviarAto(p.identificador_ato, p.data_ata, p.hora_ata)}</div>
                  <div style={{ ...s.cell, fontFamily: "monospace", fontSize: 11 }}>{p.numero_protocolo || "—"}</div>
                  <div>
                    <span style={s.badge(p.status)}>{STATUS_CONFIG[p.status]?.label || p.status}</span>
                    {(p.email_status === "pendente_revisao" || p.email_status === "falhou") && (
                      <span style={s.badgeEmail(p.email_status)}>{p.email_status === "falhou" ? "E-mail: falhou" : "E-mail pendente"}</span>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <button style={s.btnVer} onClick={e => { e.stopPropagation(); setProcessoSelecionado(p); }}>Ver</button>
                    <div onClick={e => e.stopPropagation()}><BotaoIatos processo={p} onAbrir={setIatosAberto} /></div>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </>
    );
  }

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
    const camposEdicaoIniciais = () => ({
      tipo_ato: p.tipo_ato || "",
      identificador_ato: p.identificador_ato || "",
      empresa: p.empresa || "",
      uf: p.uf || "",
      numero_protocolo: p.numero_protocolo || "",
      data_ata: p.data_ata || "",
      hora_ata: p.hora_ata || "",
    });
    const [editandoDados, setEditandoDados] = useState(false);
    const [formEdicao, setFormEdicao] = useState(camposEdicaoIniciais);
    const [salvandoEdicao, setSalvandoEdicao] = useState(false);
    const [erroEdicao, setErroEdicao] = useState("");
    function iniciarEdicaoDados() {
      setFormEdicao(camposEdicaoIniciais());
      setErroEdicao("");
      setEditandoDados(true);
    }
    function cancelarEdicaoDados() {
      setErroEdicao("");
      setEditandoDados(false);
    }
    async function salvarEdicaoDados() {
      setSalvandoEdicao(true);
      setErroEdicao("");
      try {
        await axios.patch(`${API}/processos/${p.id}`, formEdicao);
        setProcessoSelecionado({ ...processoSelecionado, ...formEdicao });
        setNumProtocolo(formEdicao.numero_protocolo);
        setEditandoDados(false);
        carregar();
      } catch (e) {
        setErroEdicao((e.response && e.response.data && e.response.data.detail) || "Erro ao salvar as alterações.");
      }
      setSalvandoEdicao(false);
    }
    async function uploadProtocoloLocal(tipo, arquivo) {
      const form = new FormData();
      form.append("arquivo", arquivo);
      try {
        const resp = await axios.post(API + "/processos/" + p.id + "/upload/" + tipo, form);
        setAnexados(a => ({ ...a, [tipo]: true }));
        if (tipo === "protocolo" && resp.data && resp.data.numero_protocolo) {
          setNumProtocolo(resp.data.numero_protocolo);
        }
        const mensagensSucesso = {
          protocolo: "Protocolo inserido com sucesso! O processo foi movido para Tramitação.",
          registro: "Registro inserido com sucesso! O processo foi Finalizado.",
          nd: "Nota de Débito inserida com sucesso.",
          nf: "Nota Fiscal inserida com sucesso.",
          ata: "Ata atualizada com sucesso.",
        };
        alert(mensagensSucesso[tipo] || "Arquivo inserido com sucesso.");
        if (tipo === "protocolo" || tipo === "registro") {
          // Muda o status do processo (tramitacao/finalizado) - volta pra tela
          // inicial em vez de tentar sincronizar o estado local, garantindo
          // que a lista/detalhe reflitam o status novo imediatamente.
          setProcessoSelecionado(null);
        }
        carregar();
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
    const [baixandoZip, setBaixandoZip] = useState(false);
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
    async function baixarTodosAnexos() {
      setBaixandoZip(true);
      try {
        const res = await axios.get(`${API}/processos/${p.id}/anexos/zip`, { responseType: "blob" });
        const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/zip" }));
        const a = document.createElement("a");
        a.href = url; a.download = `anexos_processo_${p.id}.zip`;
        document.body.appendChild(a); a.click(); a.remove();
        window.URL.revokeObjectURL(url);
      } catch (e) { alert("Nao foi possivel baixar o ZIP de anexos."); }
      setBaixandoZip(false);
    }

    async function registrarExigencia() {
      setSalvandoExig(true);
      try {
        const form = new FormData();
        form.append("texto", textoExig);
        if (arqExig) form.append("arquivo", arqExig);
        await axios.post(`${API}/processos/${p.id}/exigencia`, form);
        alert("Exigência registrada com sucesso! O processo foi atualizado.");
        setProcessoSelecionado(null);
        carregar();
      } catch (e) {
        alert("Erro ao registrar exigência.");
        setSalvandoExig(false);
      }
    }

    async function exigenciaCumprida() {
      try {
        await axios.post(`${API}/processos/${p.id}/exigencia/cumprida`);
        alert("Exigência marcada como cumprida! O status do processo foi atualizado.");
        setProcessoSelecionado(null);
        carregar();
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
        alert("Protocolo inserido com sucesso! O processo foi movido para Tramitação.");
        setProcessoSelecionado(null);
        carregar();
      } catch (e) {
        alert("Erro ao salvar o número do protocolo.");
        setSalvandoProt(false);
      }
    }
    async function excluirProtocolo() {
      if (!window.confirm("Tem certeza que deseja excluir o protocolo deste processo? O processo voltara para o status Aberto.")) return;
      setSalvandoProt(true);
      try {
        await axios.patch(`${API}/processos/${p.id}`, { numero_protocolo: "", arquivo_protocolo: null });
        setNumProtocolo("");
        if (processoSelecionado?.id === p.id) {
          const res = await axios.get(`${API}/processos/${p.id}`);
          setProcessoSelecionado(res.data);
        }
        carregar();
      } catch (e) {
        alert("Erro ao excluir o protocolo.");
      }
      setSalvandoProt(false);
    }

    return (
      <div style={s.detalhe}>
        <div style={s.detalheHeader}>
          <div>
            <div style={s.detalheTitle}>{p.empresa}</div>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#71717a", marginTop: 4 }}>
              CNPJ {p.cnpj} · NIRE {p.nire} · {p.id}
            </div>
          </div>
          <button style={s.btnSecondary} onClick={() => setProcessoSelecionado(null)}>← Voltar</button> {!ehOperador && (
            <button style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", border: "1px solid rgba(255,77,77,0.3)", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer", marginLeft: 8, fontFamily: FONTE_CORPO }} onClick={excluirProcesso}>Excluir Processo</button>
          )}
        </div>

        {p.requer_cpl && (
          <div style={s.alerta}>
            ⚠ CPL necessária — alteração de endereço ou objeto social requer Consulta Prévia de Local na Prefeitura antes de qualquer protocolo.
          </div>
        )}

        <div style={{ fontSize: 13, color: "#8a90b8", marginBottom: 12 }}>Alterar status:</div>
        <div style={s.statusRow}>
          {["aberto","tramitacao","exigencia","deferido","finalizado"].map((key) => (
            <button key={key} style={s.btnStatus(p.status === key)} onClick={() => atualizarStatus(p.id, key)}>
              {STATUS_CONFIG[key].label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: "#fff" }}>Dados do processo</div>
          {!editandoDados && (
            <button style={s.btnSecondary} onClick={iniciarEdicaoDados}>✎ Editar</button>
          )}
        </div>
        {erroEdicao && (
          <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 6, padding: "6px 10px", fontSize: 12, marginBottom: 10 }}>
            {erroEdicao}
          </div>
        )}
        {editandoDados ? (
          <div style={s.detalheGrid}>
            <div>
              <label style={s.label}>Tipo de ato</label>
              <select style={s.input} value={formEdicao.tipo_ato} onChange={e => setFormEdicao(f => ({ ...f, tipo_ato: e.target.value }))}>
                <option value="">—</option>
                {TIPOS_ATO_OPCOES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label style={s.label}>Identificador</label>
              <input style={s.input} value={formEdicao.identificador_ato} onChange={e => setFormEdicao(f => ({ ...f, identificador_ato: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Empresa</label>
              <input style={s.input} value={formEdicao.empresa} onChange={e => setFormEdicao(f => ({ ...f, empresa: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>UF</label>
              <input style={s.input} value={formEdicao.uf} onChange={e => setFormEdicao(f => ({ ...f, uf: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Protocolo</label>
              <input style={s.input} value={formEdicao.numero_protocolo} onChange={e => setFormEdicao(f => ({ ...f, numero_protocolo: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Data da ata</label>
              <input style={s.input} value={formEdicao.data_ata} onChange={e => setFormEdicao(f => ({ ...f, data_ata: e.target.value }))} placeholder="dd/mm/aaaa" />
            </div>
            <div>
              <label style={s.label}>Hora da ata</label>
              <input style={s.input} value={formEdicao.hora_ata} onChange={e => setFormEdicao(f => ({ ...f, hora_ata: e.target.value }))} placeholder="hh:mm" />
            </div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
              <button style={s.btnPrimary} onClick={salvarEdicaoDados} disabled={salvandoEdicao}>{salvandoEdicao ? "Salvando..." : "Salvar"}</button>
              <button style={s.btnSecondary} onClick={cancelarEdicaoDados} disabled={salvandoEdicao}>Cancelar</button>
            </div>
          </div>
        ) : (
          <div style={s.detalheGrid}>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Tipo de ato</div><div style={s.detalheItemValue}>{p.tipo_ato}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Identificador</div><div style={s.detalheItemValue}>{p.identificador_ato}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Empresa</div><div style={s.detalheItemValue}>{p.empresa}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>UF</div><div style={s.detalheItemValue}>{p.uf || "—"}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Data da ata</div><div style={s.detalheItemValue}>{p.data_ata} {p.hora_ata && `· ${p.hora_ata}`}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Tipo de sociedade</div><div style={s.detalheItemValue}>{p.tipo_sociedade}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Recebido em</div><div style={s.detalheItemValue}>{new Date(p.data_recebimento).toLocaleDateString("pt-BR")}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Processo criado em</div><div style={s.detalheItemValue}>{p.criado_em ? new Date(p.criado_em).toLocaleString("pt-BR") : "—"}</div></div>
            <div style={s.detalheItem}><div style={s.detalheItemLabel}>Protocolo</div><div style={s.detalheItemValue}>{p.numero_protocolo || "—"}</div></div>
          </div>
        )}

        {eventos.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#fff", marginBottom: 8 }}>Eventos identificados</div>
            <div style={s.checklist}>
              {eventos.map((e, i) => <div key={i} style={s.checkItem}>• {e}</div>)}
            </div>
          </div>
        )}

        {checklist.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#fff", marginBottom: 8 }}>Checklist de documentos</div>
            <div style={s.checklist}>
              {checklist.map((c, i) => <div key={i} style={s.checkItem}>☐ {c}</div>)}
            </div>
          </div>
        )}

        <div style={{ fontSize: 13, fontWeight: 500, color: "#fff", marginBottom: 8 }}>Exigência</div>
        <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 14, marginBottom: 16 }}>
          {p.exigencia_ativa && (
            <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 6, padding: "6px 10px", fontSize: 12, marginBottom: 10 }}>
              ⚠ Exigência ativa — o processo está em Exigência.
            </div>
          )}
          <label style={s.label}>Texto da exigência</label>
          <textarea style={{ ...s.input, minHeight: 70, resize: "vertical", fontFamily: FONTE_CORPO }}
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
              <button style={{ ...s.btnSecondary, borderColor: "rgba(0,255,170,0.35)", color: "#7dffce" }} onClick={exigenciaCumprida}>
                ✓ Exigência cumprida
              </button>
              <button style={{ ...s.btnSecondary, borderColor: "rgba(255,159,10,0.35)", color: "#ffc266" }} onClick={exigenciaAguardandoCliente}>
                Exigência Aguardando Cliente
              </button>
            </>)}
          </div>
        </div>

        <div style={{ fontSize: 13, fontWeight: 500, color: "#fff", marginBottom: 8 }}>Arquivos</div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label style={s.label}>Número do protocolo</label>
            <input style={s.input} value={numProtocolo} onChange={e => setNumProtocolo(e.target.value)}
              placeholder="Digite o número do protocolo" />
          </div>
          <button style={{ ...s.btnPrimary, height: 38 }} onClick={salvarProtocolo} disabled={salvandoProt}>
            {salvandoProt ? "Salvando..." : "Salvar"}
          </button>
          <button style={{ ...s.btnSecondary, height: 38, borderColor: "rgba(255,77,77,0.4)", color: "#ff9494" }} onClick={excluirProtocolo} disabled={salvandoProt}>
            Excluir protocolo
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
                      style={{ background: "transparent", border: "1px solid rgba(77,148,255,0.4)", color: "#8ec2ff", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: FONTE_CORPO }}>↓ Baixar</button>
                    { tipo === "protocolo" && (
                      <label style={{ cursor: "pointer" }}>
                        <span style={{ ...s.uploadPend, fontSize: 11 }}>Trocar</span>
                        <input type="file" style={{ display: "none" }} onChange={e => uploadProtocoloLocal(tipo, e.target.files[0])} />
                      </label>
                    )}
                  </span>
                : <label style={{ cursor: "pointer" }}>
                    <span style={s.uploadPend}>+ Anexar</span>
                    <input type="file" style={{ display: "none" }} onChange={e => uploadProtocoloLocal(tipo, e.target.files[0])} />
                  </label>
              }
            </div>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: "#fff" }}>
            Anexos <span style={{ fontSize: 12, color: "#62666d", fontWeight: 400 }}>({anexos.length})</span>
          </div>
          {anexos.length > 0 && (
            <button onClick={baixarTodosAnexos} disabled={baixandoZip}
              style={{ background: "transparent", border: "1px solid rgba(77,148,255,0.4)", color: "#8ec2ff", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: baixandoZip ? "not-allowed" : "pointer", fontFamily: FONTE_CORPO, opacity: baixandoZip ? 0.6 : 1 }}>
              {baixandoZip ? "Gerando ZIP..." : "↓ Baixar Todos os Anexos"}
            </button>
          )}
        </div>
        <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 14, marginBottom: 16 }}>
          {anexos.length === 0 ? (
            <div style={{ fontSize: 13, color: "#62666d", marginBottom: 12 }}>Nenhum anexo enviado ainda.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
              {anexos.map(ax => (
                <div key={ax.id} style={{ ...s.uploadItem, alignItems: "flex-start" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: "#e4e4e7", fontWeight: 500, wordBreak: "break-word" }}>
                      {ax.nome_original || "anexo"}
                    </div>
                    {ax.descricao && (
                      <div style={{ fontSize: 12, color: "#8a90b8", marginTop: 2 }}>{ax.descricao}</div>
                    )}
                    <div style={{ fontSize: 11, color: "#62666d", marginTop: 2 }}>
                      Enviado por {ax.enviado_por || "\u2014"}
                      {ax.criado_em && ` \u00b7 ${new Date(ax.criado_em).toLocaleDateString("pt-BR")}`}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0, marginLeft: 10 }}>
                    <button onClick={() => baixarAnexo(ax.id, ax.nome_original)}
                      style={{ background: "transparent", border: "1px solid rgba(77,148,255,0.4)", color: "#8ec2ff", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: FONTE_CORPO }}>\u2193 Baixar</button>
                    <button onClick={() => excluirAnexo(ax.id)}
                      style={{ background: "transparent", border: "1px solid rgba(255,255,255,0.1)", color: "#ff9494", borderRadius: 6, padding: "3px 10px", fontSize: 11, cursor: "pointer", fontFamily: FONTE_CORPO }}>Excluir</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12 }}>
            <input style={{ ...s.input, flex: "1 1 200px", minWidth: 160 }} value={descAnexo}
              onChange={e => setDescAnexo(e.target.value)} placeholder="Descrição (opcional): ex. procuração, RG..." />
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

        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <BotaoIatos processo={p} onAbrir={setIatosAberto} />
        </div>
        <ChatProcesso processoId={p.id} />
        {p.observacoes && (
          <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 12, fontSize: 13, color: "#c4c8e4" }}>
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

      <div style={{ ...s.layout, flexDirection: mobile ? "column" : "row" }}>
        <SidebarAtos
          onLogoClick={() => { setTela("processos"); setProcessoSelecionado(null); }}
          rodape={<div style={{ display: "inline-block", fontSize: 9.5, fontWeight: 700, color: "#6db2ff", background: "rgba(77,148,255,0.12)", border: "1px solid rgba(77,148,255,0.35)", borderRadius: 4, padding: "2px 7px", marginTop: 8, letterSpacing: 0.5 }}>ADMINISTRADOR</div>}
          itens={[
            { label: "Processos", ativo: tela === "processos" && !processoSelecionado, icone: <IconeProcessos />, onClick: () => { setTela("processos"); setProcessoSelecionado(null); } },
            { label: "Grupos", ativo: tela === "grupos", icone: <IconeGrupos />, onClick: () => { setTela("grupos"); setProcessoSelecionado(null); } },
            ...(ehOperador ? [] : [{ label: "Aprendizado", ativo: tela === "aprendizado", icone: <IconeAprendizado />, onClick: () => { setTela("aprendizado"); setProcessoSelecionado(null); } }]),
            { label: "Atas recebidas", disabled: true },
            { label: "Cobranças", disabled: true },
          ]}
        />

        <div style={s.main}>
          <div style={s.topBar}>
            <button style={s.btnSair} onClick={onSair}>Sair</button>
          </div>
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
              <DonutStatusCard titulo="Todos os Processos" metricas={metricas} onClickStatus={setFStatus} statusAtivo={fStatus} idPrefix="da" grande
                extra={<ExtraFluxoEAtividade />} />

              <div
                onDragOver={e => { e.preventDefault(); }}
                onDrop={e => {
                  e.preventDefault();
                  if (!upGrupo) { alert("Selecione o cliente antes de subir."); return; }
                  const items = e.dataTransfer.items;
                  if (items && items.length && items[0].webkitGetAsEntry) {
                    const arquivos = [];
                    let pendentes = 0;
                    let lendoDiretorios = 0;
                    const finalizarSeVazio = () => { if (pendentes === 0 && lendoDiretorios === 0) processarPastaAdmin(arquivos); };
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
                  } else { processarArquivosAdmin(e.dataTransfer.files); }
                }}
                style={{ border: "1.5px dashed rgba(77,148,255,0.35)", borderRadius: 18, padding: "28px", marginBottom: 18, background: "rgba(255,255,255,0.03)" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
                  <select value={upGrupo} onChange={e => setUpGrupo(e.target.value)} disabled={upSubindo} style={s.filtro}>
                    <option value="">Grupo Empresarial</option>
                    {grupos.map(g => <option key={g.id} value={g.codigo}>{g.nome}</option>)}
                  </select>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", borderRadius: 9, padding: "9px 16px", fontSize: 12.5, fontFamily: FONTE_CORPO, opacity: (upSubindo||!upGrupo) ? 0.5 : 1, boxShadow: "0 4px 16px rgba(77,148,255,0.3)" }}>
                      Arquivos
                    </span>
                    <input type="file" accept="application/pdf" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarArquivosAdmin(e.target.files)} />
                  </label>
                  <label style={{ display: "inline-block", cursor: (upSubindo||!upGrupo) ? "not-allowed" : "pointer" }}>
                    <span style={{ background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", borderRadius: 9, padding: "9px 16px", fontSize: 12.5, fontFamily: FONTE_CORPO, opacity: (upSubindo||!upGrupo) ? 0.5 : 1, boxShadow: "0 4px 16px rgba(77,148,255,0.3)" }}>
                      Pastas
                    </span>
                    <input type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
                      disabled={upSubindo||!upGrupo} onChange={e => processarPastaAdmin(e.target.files)} />
                  </label>
                  {upSubindo && <span style={{ fontSize: 13, color: "#8ec2ff" }}>Enviando {upProg.feitos} de {upProg.total}{upProg.erros ? ` (${upProg.erros} erro)` : ""}...</span>}
                </div>
              </div>
              <div style={{ fontSize: 13, color: "#a8b0d8", marginBottom: 12, fontWeight: 500 }}>Processos recentes</div>
              <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
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
                  <option value="tramitacao">Tramitação</option>
                  <option value="exigencia">Exigência</option>
                  <option value="deferido">Deferido</option>
                  <option value="finalizado">Finalizado</option>
                </select>
                <select value={fGrupo} onChange={e => setFGrupo(e.target.value)} style={s.filtro}>
                  <option value="">Cliente: todos</option>
                  {grupos.map(g => <option key={g.id} value={g.id}>{g.nome}</option>)}
                </select>
                {(fBusca || fUf || fAto || fStatus || fGrupo) && (
                  <button onClick={() => { setFBusca(""); setFUf(""); setFAto(""); setFStatus(""); setFGrupo(""); }}
                    style={{ padding: "9px 14px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, background: "rgba(255,255,255,0.05)", color: "#d4d4d8", cursor: "pointer", fontFamily: FONTE_CORPO }}>Limpar</button>
                )}
              </div>

              <div style={s.tableWrap}>
                <div style={mobile ? {} : s.tableScroll}>
                  {!mobile && (
                    <div style={s.tableHead}>
                      {["Empresa", "UF", "Ato", "Protocolo", "Status", ""].map((h, i) => (
                        <div key={i} style={s.th}>{h}</div>
                      ))}
                    </div>
                  )}
                  {processos.length === 0 ? (
                    <div style={{ padding: "32px 16px", textAlign: "center", color: "#62666d", fontSize: 13 }}>
                      Nenhum processo ainda. Clique em "Novo processo" para começar.
                    </div>
                  ) : <ListaProcessosAgrupada />}
                </div>
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
                <div style={{ background: "rgba(255,255,255,0.03)", border: "2px dashed rgba(77,148,255,0.35)", borderRadius: 10, padding: 32, textAlign: "center", marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: "#8a90b8", marginBottom: 12 }}>
                    {analisando ? "Analisando documento..." : "Arraste ou selecione a ata para análise automática"}
                  </div>
                  {!analisando && (
                    <label style={{ cursor: "pointer" }}>
                      <span style={{ background: "linear-gradient(135deg, #4d94ff, #8c5aff)", color: "#fff", padding: "8px 20px", borderRadius: 8, fontSize: 13 }}>
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
                <div style={{ background: "rgba(0,255,170,0.1)", border: "1px solid rgba(0,255,170,0.3)", borderRadius: 8, padding: 10, marginBottom: 16, fontSize: 13, color: "#7dffce" }}>
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
      {iatosAberto && <IatosChat processo={iatosAberto} token={sessao.token} onFechar={() => setIatosAberto(null)} />}
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
    if (sessao.is_admin || sessao.papel === "operador") return <AppPainel onSair={sair} sessao={sessao} />;
    return <PainelCliente sessao={sessao} onSair={sair} />;
  }

  return (
    <TelaLogin
      subtitulo="Painel do Administrador"
      erro={erro} etapa={etapa} carregando={carregando}
      login={login} senha={senha} codigo={codigo}
      onChangeLogin={setLogin} onChangeSenha={setSenha} onChangeCodigo={setCodigo}
      onEntrar={entrar} onVerificarCodigo={verificarCodigo}
      onVoltarEtapa={() => { setEtapa(1); setCodigo(""); setErro(""); }}
    />
  );
}

