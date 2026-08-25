import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { FONTE_TITULO, FONTE_CORPO, useBreakpoint } from "./components/Compartilhados";
import { PLANOS } from "./planosConfig";

const API = "";

// Etapa 2 de 2 do auto-cadastro (rota /solicitar-acesso/plano) - escolhe o
// plano (hoje so' o Free tem acao de verdade; Pro/Premium mostram "EM BREVE"
// vindo de PLANOS, ver planosConfig.js) e, ao confirmar o Free, chama
// POST /solicitar-acesso e mostra a tela de confirmacao ("verifique seu
// email") no lugar do card de planos, sem trocar de rota.
export default function EscolhaPlano() {
  const navigate = useNavigate();
  const location = useLocation();
  const bp = useBreakpoint();
  const mobile = bp === "mobile";

  const nome = location.state && location.state.nome;
  const email = location.state && location.state.email;

  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [confirmado, setConfirmado] = useState(false);

  useEffect(() => {
    if (!nome || !email) navigate("/solicitar-acesso", { replace: true });
    /* eslint-disable-next-line */
  }, []);

  if (!nome || !email) return null;

  async function escolherPlano(plano) {
    if (!plano.ativo || plano.id !== "free") return; // Pro/Premium: sem fluxo de pagamento ainda
    setErro(""); setEnviando(true);
    try {
      await axios.post(`${API}/solicitar-acesso`, { nome, email });
      setConfirmado(true);
    } catch (e) {
      setErro((e.response && e.response.data && e.response.data.detail) || "Erro ao concluir cadastro.");
    }
    setEnviando(false);
  }

  if (confirmado) {
    return (
      <div style={{ minHeight: "100vh", background: "#060608", color: "#e4e4e7", fontFamily: FONTE_CORPO, display: "flex", alignItems: "center", justifyContent: "center", padding: mobile ? 20 : 40, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: -120, left: "10%", width: 420, height: 420, background: "radial-gradient(circle, #00e69130 0%, transparent 70%)", filter: "blur(50px)", pointerEvents: "none" }} />
        <div style={{ width: "100%", maxWidth: 400, background: "rgba(255,255,255,0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, padding: mobile ? "32px 24px" : "40px 36px", zIndex: 1, textAlign: "center", boxShadow: "0 0 60px rgba(0,230,145,0.1)", boxSizing: "border-box" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: "rgba(0,230,145,0.12)", border: "1.5px solid #00e691", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#00e691" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
          </div>
          <div style={{ fontFamily: FONTE_TITULO, fontSize: 19, fontWeight: 700, color: "#fff", marginBottom: 10 }}>Verifique seu email</div>
          <div style={{ fontSize: 13.5, color: "#8a90b8", lineHeight: 1.6, marginBottom: 6 }}>
            Enviamos um link para <span style={{ color: "#00d4ff", fontWeight: 600 }}>{email}</span> para você criar sua senha e começar a usar o Atos.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#060608", color: "#e4e4e7", fontFamily: FONTE_CORPO, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: mobile ? "20px 16px" : 40, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: -120, left: "15%", width: 480, height: 480, background: "radial-gradient(circle, #00d4ff25 0%, transparent 70%)", filter: "blur(55px)", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: -120, right: "15%", width: 480, height: 480, background: "radial-gradient(circle, #8c5aff22 0%, transparent 70%)", filter: "blur(55px)", pointerEvents: "none" }} />

      <div style={{ fontFamily: FONTE_TITULO, fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 2, zIndex: 1 }}>atos<span style={{ color: "#6db2ff" }}>.</span></div>
      <div style={{ fontSize: 11, color: "#9aa8d8", marginBottom: 4, zIndex: 1 }}>Gestão Societária</div>
      <div style={{ fontSize: 11, color: "#00d4ff", fontWeight: 700, letterSpacing: 0.5, marginTop: 18, marginBottom: 8, zIndex: 1 }}>ETAPA 2 DE 2</div>
      <div style={{ fontFamily: FONTE_TITULO, fontSize: 24, fontWeight: 700, color: "#fff", marginBottom: 8, zIndex: 1, textAlign: "center" }}>Escolha seu plano</div>

      {erro && <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 16, zIndex: 1 }}>{erro}</div>}

      <div style={{
        display: "flex", gap: 16, zIndex: 1, justifyContent: "center",
        flexDirection: mobile ? "column" : "row", flexWrap: mobile ? "nowrap" : "nowrap",
        width: mobile ? "100%" : "auto", maxWidth: mobile ? 360 : "none", marginTop: 20,
      }}>
        {PLANOS.map(plano => {
          const bloqueado = !plano.ativo;
          return (
            <div key={plano.id} style={{
              width: mobile ? "100%" : 220, boxSizing: "border-box",
              background: "rgba(255,255,255,0.03)", backdropFilter: "blur(20px)", borderRadius: 18,
              padding: "24px 20px", display: "flex", flexDirection: "column",
              border: bloqueado ? "1px solid rgba(255,255,255,0.08)" : "1.5px solid #00d4ff",
              boxShadow: bloqueado ? "none" : "0 0 40px rgba(0,212,255,0.15)",
              opacity: bloqueado ? 0.55 : 1,
            }}>
              {plano.emBreve && (
                <div style={{ display: "inline-block", fontSize: 9.5, fontWeight: 700, color: "#8a90b8", background: "rgba(255,255,255,0.06)", borderRadius: 20, padding: "3px 10px", marginBottom: 14, letterSpacing: 0.3, alignSelf: "flex-start" }}>
                  EM BREVE
                </div>
              )}
              <div style={{ fontFamily: FONTE_TITULO, fontSize: 17, fontWeight: 700, color: "#fff", marginBottom: 4 }}>{plano.nome}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: bloqueado ? "#6a6a72" : "#00d4ff", marginBottom: 4 }}>
                {plano.preco || "—"} <small style={{ fontSize: 12, fontWeight: 400, color: "#8a90b8" }}>{plano.precoSufixo}</small>
              </div>
              <ul style={{ listStyle: "none", margin: "14px 0 22px", padding: 0, flex: 1 }}>
                {plano.features.map((f, i) => {
                  const incluido = !bloqueado && f.incluido;
                  return (
                    <li key={i} style={{ fontSize: 12.5, color: incluido ? "#c4c8e4" : "#5a5a62", padding: "6px 0", display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ color: incluido ? "#00e691" : "#5a5a62", flexShrink: 0, marginTop: 1 }}>{incluido ? "✓" : "✕"}</span>
                      {f.texto}
                    </li>
                  );
                })}
              </ul>
              <button
                onClick={() => escolherPlano(plano)}
                disabled={bloqueado || enviando}
                style={{
                  width: "100%", border: "none", borderRadius: 10, padding: 12, fontSize: 13.5, fontWeight: 700,
                  fontFamily: FONTE_CORPO, cursor: bloqueado ? "not-allowed" : "pointer",
                  background: bloqueado ? "rgba(255,255,255,0.05)" : "linear-gradient(135deg, #00d4ff, #4d94ff)",
                  color: bloqueado ? "#6a6a72" : "#061018",
                  boxShadow: bloqueado ? "none" : "0 4px 16px rgba(0,212,255,0.3)",
                }}>
                {bloqueado ? plano.botaoLabel : (enviando ? "Aguarde..." : plano.botaoLabel)}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
