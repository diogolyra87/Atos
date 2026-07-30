import React, { useState, useEffect } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";

const API = "";

function senhaFraca(senha) {
  if (senha.length < 8) return "A senha deve ter pelo menos 8 caracteres.";
  if (!/[a-zA-Z]/.test(senha) || !/[0-9]/.test(senha)) return "A senha deve ter letras e números.";
  return null;
}

export default function CriarSenha() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";

  const [estado, setEstado] = useState("carregando"); // carregando | valido | invalido | expirado | sucesso
  const [nome, setNome] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!token) { setEstado("invalido"); return; }
    axios.get(`${API}/convite/${token}`)
      .then(r => { setNome(r.data.nome || ""); setEstado("valido"); })
      .catch(e => {
        if (e.response && e.response.status === 410) setEstado("expirado");
        else setEstado("invalido");
      });
  }, [token]);

  async function confirmarSenha() {
    setErro("");
    const problema = senhaFraca(senha);
    if (problema) { setErro(problema); return; }
    if (senha !== confirmar) { setErro("As senhas não coincidem."); return; }
    setEnviando(true);
    try {
      await axios.post(`${API}/convite/definir-senha`, { token, senha });
      setEstado("sucesso");
    } catch (e) {
      if (e.response && e.response.status === 410) setEstado("expirado");
      else if (e.response && e.response.status === 404) setEstado("invalido");
      else setErro((e.response && e.response.data && e.response.data.detail) || "Erro ao definir senha.");
    }
    setEnviando(false);
  }

  const s = {
    input: { width: "100%", padding: "11px 13px", border: "0.5px solid #d9d5ea", borderRadius: 8, fontSize: 14, outline: "none", marginBottom: 14, boxSizing: "border-box", background: "#fbfaff" },
    label: { fontSize: 12, color: "#7a7790", marginBottom: 4, display: "block" },
    botao: { width: "100%", background: "linear-gradient(135deg,#2563eb,#2dd4bf)", color: "#fff", border: "none", padding: "12px", borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4 },
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(180deg,#dff3f0 0%,#7fd0d8 38%,#3b82f6 72%,#1e3a8a 100%)", fontFamily: "Inter, sans-serif", padding: 16 }}>
      <div style={{ background: "#fff", borderRadius: 16, padding: 32, width: "100%", maxWidth: 380, boxShadow: "0 10px 50px rgba(20,10,50,0.45)", boxSizing: "border-box" }}>
        <div style={{ fontSize: 34, fontWeight: 800, color: "#111111", fontFamily: "AtosBrand", letterSpacing: -1.5, textAlign: "center" }}>atos<span style={{ color: "#2d6cdf" }}>.</span></div>
        <div style={{ textAlign: "center", fontSize: 13, color: "#7a7790", marginBottom: 24 }}>Gestão Societária</div>

        {estado === "carregando" && (
          <div style={{ textAlign: "center", color: "#7a7790", fontSize: 13 }}>Verificando convite...</div>
        )}

        {estado === "invalido" && (
          <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "12px 14px", fontSize: 13 }}>
            Este link de convite é inválido ou já foi utilizado. Peça um novo convite ao administrador.
          </div>
        )}

        {estado === "expirado" && (
          <div style={{ background: "#fef3c7", color: "#92400e", borderRadius: 8, padding: "12px 14px", fontSize: 13 }}>
            Este link de convite expirou. Peça ao administrador para gerar um novo convite.
          </div>
        )}

        {estado === "sucesso" && (
          <div style={{ background: "#dcfce7", color: "#166534", borderRadius: 8, padding: "12px 14px", fontSize: 13 }}>
            Senha definida com sucesso! Você já pode fazer login normalmente.
          </div>
        )}

        {estado === "valido" && (
          <>
            <div style={{ textAlign: "center", fontSize: 14, color: "#23282a", marginBottom: 18 }}>
              Olá, {nome}! Defina sua senha de acesso.
            </div>
            {erro && <div style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 14 }}>{erro}</div>}
            <label style={s.label}>Nova senha</label>
            <input style={s.input} type="password" value={senha} onChange={e => setSenha(e.target.value)} />
            <label style={s.label}>Confirmar senha</label>
            <input style={s.input} type="password" value={confirmar} onChange={e => setConfirmar(e.target.value)} onKeyDown={e => e.key === "Enter" && confirmarSenha()} />
            <div style={{ fontSize: 11, color: "#a09dba", marginBottom: 14 }}>Mínimo de 8 caracteres, com letras e números.</div>
            <button style={s.botao} onClick={confirmarSenha} disabled={enviando}>{enviando ? "Aguarde..." : "Definir senha"}</button>
          </>
        )}
      </div>
    </div>
  );
}
