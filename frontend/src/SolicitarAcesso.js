import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FONTE_TITULO, FONTE_CORPO, useBreakpoint } from "./components/Compartilhados";

// Etapa 1 de 2 do auto-cadastro (rota /solicitar-acesso) - so' coleta nome
// e email; a escolha do plano acontece na proxima tela (EscolhaPlano.js),
// que e' quem de fato chama POST /solicitar-acesso.
export default function SolicitarAcesso() {
  const navigate = useNavigate();
  const bp = useBreakpoint();
  const mobile = bp === "mobile";
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [erro, setErro] = useState("");

  function continuar() {
    setErro("");
    if (!nome.trim() || !email.trim()) { setErro("Preencha nome e email."); return; }
    if (!email.includes("@") || !email.split("@").pop().includes(".")) { setErro("Informe um email válido."); return; }
    navigate("/solicitar-acesso/plano", { state: { nome: nome.trim(), email: email.trim().toLowerCase() } });
  }

  const s = {
    campoLabel: { fontSize: 12, color: "#a8b0d8", marginBottom: 6, display: "block", fontWeight: 600, fontFamily: FONTE_CORPO },
    campoInput: { width: "100%", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: "12px 14px", color: "#fff", fontSize: 13.5, marginBottom: 16, fontFamily: FONTE_CORPO, outline: "none", boxSizing: "border-box" },
  };

  return (
    <div style={{ minHeight: "100vh", background: "#060608", color: "#e4e4e7", fontFamily: FONTE_CORPO, display: "flex", alignItems: "center", justifyContent: "center", padding: mobile ? 20 : 40, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: -120, left: "10%", width: 420, height: 420, background: "radial-gradient(circle, #00d4ff30 0%, transparent 70%)", filter: "blur(50px)", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: -120, right: "12%", width: 420, height: 420, background: "radial-gradient(circle, #8c5aff28 0%, transparent 70%)", filter: "blur(50px)", pointerEvents: "none" }} />

      <div style={{ width: "100%", maxWidth: 400, background: "rgba(255,255,255,0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, padding: mobile ? "28px 24px" : "36px", zIndex: 1, boxShadow: "0 0 60px rgba(0,212,255,0.08)", boxSizing: "border-box" }}>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 2 }}>atos<span style={{ color: "#6db2ff" }}>.</span></div>
        <div style={{ fontSize: 11, color: "#9aa8d8", marginBottom: 4 }}>Gestão Societária</div>
        <div style={{ fontSize: 11, color: "#00d4ff", fontWeight: 700, letterSpacing: 0.5, marginTop: 18, marginBottom: 8 }}>ETAPA 1 DE 2</div>
        <div style={{ fontFamily: FONTE_TITULO, fontSize: 19, fontWeight: 700, color: "#fff", marginBottom: 6 }}>Criar sua conta</div>
        <div style={{ fontSize: 13, color: "#8a90b8", marginBottom: 26, lineHeight: 1.5 }}>
          Para advogados, contadores e paralegais que querem organizar seus processos societários.
        </div>

        {erro && <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff9494", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}

        <label style={s.campoLabel}>Nome completo</label>
        <input style={s.campoInput} type="text" placeholder="Seu nome" value={nome} onChange={e => setNome(e.target.value)} onKeyDown={e => e.key === "Enter" && continuar()} />

        <label style={s.campoLabel}>E-mail</label>
        <input style={s.campoInput} type="text" placeholder="seu@email.com" value={email} onChange={e => setEmail(e.target.value)} onKeyDown={e => e.key === "Enter" && continuar()} />

        <button
          onClick={continuar}
          style={{ width: "100%", background: "linear-gradient(135deg, #00d4ff, #4d94ff)", border: "none", borderRadius: 10, padding: 14, color: "#061018", fontSize: 14, fontWeight: 700, boxShadow: "0 4px 20px rgba(0,212,255,0.3)", cursor: "pointer", marginTop: 4, fontFamily: FONTE_CORPO }}>
          Continuar
        </button>
        <div onClick={() => navigate("/")} style={{ textAlign: "center", fontSize: 12, color: "#6db2ff", marginTop: 18, cursor: "pointer" }}>
          Já tem conta? Entrar
        </div>
      </div>
    </div>
  );
}
