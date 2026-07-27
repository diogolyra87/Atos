export const STATUS_CONFIG = {
  recebido: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  aberto: { label: "Aberto", bg: "#eceae2", color: "#6b6c66" },
  tramitacao: { label: "Tramitação", bg: "#f0e0cb", color: "#8a5818" },
  exigencia: { label: "Exigência", bg: "#f0dcd5", color: "#a8492a" },
  deferido: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  aprovado: { label: "Deferido", bg: "#d5e3df", color: "#2563eb" },
  finalizado: { label: "Finalizado", bg: "#cfe8d8", color: "#15803d" },
};

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
                {new Date(ev.criado_em).toLocaleString("pt-BR")}
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
