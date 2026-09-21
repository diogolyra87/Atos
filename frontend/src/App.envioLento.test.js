/** @jest-environment jsdom */
// Integracao do fluxo que falhou em 21/09/2026: painel admin, envio de uma ata cuja leitura
// demora (OCR). Monta o App REAL e simula o servidor: POST /processos/analisar responde
// {processando: true}; o acompanhamento diz "lendo" e depois "concluido, ja_criado".
//
// Prova, ponta a ponta na tela:
// - o painel NAO cai em erro (era o 504) e mostra a mensagem "Lendo o documento..."
// - o painel NAO chama POST /processos de novo (o servidor ja concluiu; chamar duplicaria)
// - ao terminar, o painel recarrega a lista sozinho e avisa "1 processo(s) criado(s)"
// - com processo "Processando" na lista, a lista se atualiza sozinha (sem recarregar a pagina)
//
// axios 1.x e' ESM e o Jest do CRA nao transforma node_modules - usa o build CJS.
jest.mock("axios", () => jest.requireActual("axios/dist/node/axios.cjs"));
jest.mock("react-router-dom", () => ({ useSearchParams: () => [new URLSearchParams(), () => {}] }));
// o helper REAL, so' com o intervalo de acompanhamento encurtado pro teste nao levar minutos
jest.mock("./analisarComEspera", () => {
  const real = jest.requireActual("./analisarComEspera");
  const rapido = (o) => ({ ...(o || {}), intervaloMs: 10 });
  return {
    ...real,
    analisarDocumento: (ax, f, c, o) => real.analisarDocumento(ax, f, c, rapido(o)),
    analisarLote: (ax, f, c, o) => real.analisarLote(ax, f, c, rapido(o)),
  };
});

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
window.scrollTo = () => {};
global.ResizeObserver = global.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
global.IntersectionObserver = global.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };

const SESSAO = { token: "tok-admin", login: "diogo", nome: "Diogo", is_admin: true, papel: "admin", grupo_id: "g1" };
const PROCESSO_PRONTO = {
  id: "MN-1", empresa: "NEOENERGIA DISTRIBUIÇÃO BRASÍLIA S.A.", cnpj: "07.522.669/0001-92", uf: "DF",
  tipo_ato: "AGOE", identificador_ato: "AGOE 29/04/2026", status: "aberto", criado_em: "2026-09-21 11:02:57",
};
const PROCESSO_LENDO = { ...PROCESSO_PRONTO, empresa: "", cnpj: "", uf: "", tipo_ato: "", identificador_ato: "", status: "pendente_processamento" };

async function esperarAte(act, cond, ms = 8000) {
  const fim = Date.now() + ms;
  while (Date.now() < fim && !cond()) {
    await act(async () => { await new Promise((r) => setTimeout(r, 25)); });
  }
  return cond();
}

function montar({ listaInicial = [], estadosAnalise = [] } = {}) {
  localStorage.clear();
  localStorage.setItem("atos_admin", JSON.stringify(SESSAO));
  jest.resetModules();
  const React = require("react");
  const { createRoot } = require("react-dom/client");
  const axios = require("axios");
  const App = require("./App").default;

  const sim = { lista: listaInicial, posts: [], gets: [], alertas: [], cargasLista: 0, analiseIdx: 0 };
  window.alert = (m) => sim.alertas.push(String(m));
  axios.defaults.adapter = async (config) => {
    const url = config.url;
    const metodo = (config.method || "get").toLowerCase();
    sim.gets.push(metodo + " " + url);
    const ok = (data) => ({ status: 200, statusText: "OK", data, headers: {}, config });
    if (metodo === "post") {
      sim.posts.push(url);
      if (url === "/processos/analisar") return ok({ processando: true, processo_id: "MN-1", empresa: "", tipo_ato: "" });
      return ok({ id: "MN-1" });
    }
    if (url === "/processos") { sim.cargasLista++; return ok(sim.lista); }
    if (url === "/metricas") return ok({});
    if (url === "/grupos") return ok([{ id: "g1", nome: "Neoenergia", codigo: "COD1" }]);
    if (url === "/processos/MN-1/analise") {
      const est = estadosAnalise[Math.min(sim.analiseIdx++, estadosAnalise.length - 1)] || { estado: "lendo" };
      if (est.estado === "concluido") sim.lista = [PROCESSO_PRONTO];
      return ok(est);
    }
    if (url === "/fluxo/ativo") return ok(null);
    return ok([]);
  };
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  return { React, root, App, el, sim, axios, act: React.act };
}

let erroConsole;
beforeEach(() => { erroConsole = jest.spyOn(console, "error").mockImplementation(() => {}); });
afterEach(() => { erroConsole.mockRestore(); document.body.innerHTML = ""; });

test("envio lento no admin: acompanha, nao cria de novo, mostra a mensagem e recarrega a lista", async () => {
  const ctx = montar({
    estadosAnalise: [
      { estado: "lendo" }, { estado: "lendo" },
      { estado: "concluido", ja_criado: true, dados: { empresa: PROCESSO_PRONTO.empresa, tipo_ato: "AGOE" } },
    ],
  });
  const { act, root, App, React, el, sim } = ctx;
  await act(async () => { root.render(React.createElement(App)); });
  await esperarAte(act, () => el.querySelector("select") && el.querySelectorAll("select option").length > 1);

  // escolhe o cliente (grupo) e "seleciona" um PDF
  const select = el.querySelector("select");
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set.call(select, "COD1");
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const entrada = Array.from(el.querySelectorAll('input[type="file"]')).find((i) => i.getAttribute("accept") === "application/pdf");
  expect(entrada).toBeTruthy();
  const arquivo = new File(["%PDF-1.4 x"], "NDB AG0E 29 04 2026.pdf", { type: "application/pdf" });
  Object.defineProperty(entrada, "files", { value: [arquivo], configurable: true });
  await act(async () => { entrada.dispatchEvent(new Event("change", { bubbles: true })); });

  // a mensagem de leitura demorada aparece enquanto o servidor le
  const viuMensagem = await esperarAte(act, () => el.textContent.includes("Lendo o documento (OCR)"), 4000);
  expect(viuMensagem).toBe(true);

  // termina: alerta de conclusao
  expect(await esperarAte(act, () => sim.alertas.some((a) => a.includes("1 processo(s) criado(s)")))).toBe(true);

  // 1 upload, NENHUM POST /processos (o servidor concluiu sozinho)
  expect(sim.posts).toEqual(["/processos/analisar"]);
  // acompanhou ate concluir
  expect(sim.gets.filter((g) => g === "get /processos/MN-1/analise").length).toBe(3);
  // recarregou a lista e o processo pronto aparece
  expect(await esperarAte(act, () => el.textContent.includes("NEOENERGIA DISTRIBUIÇÃO BRASÍLIA S.A."))).toBe(true);
});

test("lista com processo 'Processando' se atualiza sozinha quando o servidor conclui", async () => {
  const ctx = montar({ listaInicial: [PROCESSO_LENDO] });
  const { act, root, App, React, el, sim } = ctx;
  await act(async () => { root.render(React.createElement(App)); });

  await esperarAte(act, () => sim.cargasLista >= 1);
  const cargasAntes = sim.cargasLista;
  expect(el.textContent).not.toContain("NEOENERGIA DISTRIBUIÇÃO BRASÍLIA S.A.");

  // o servidor termina a leitura em segundo plano...
  sim.lista = [PROCESSO_PRONTO];
  // ...e a tela recarrega sozinha (intervalo de 6s), sem ninguem mexer
  const atualizou = await esperarAte(act, () => el.textContent.includes("NEOENERGIA DISTRIBUIÇÃO BRASÍLIA S.A."), 12000);
  expect(atualizou).toBe(true);
  expect(sim.cargasLista).toBeGreaterThan(cargasAntes);
}, 30000);

test("sem processo 'Processando' a lista NAO fica recarregando sozinha", async () => {
  const ctx = montar({ listaInicial: [PROCESSO_PRONTO] });
  const { act, root, App, React, sim } = ctx;
  await act(async () => { root.render(React.createElement(App)); });
  await esperarAte(act, () => sim.cargasLista >= 1);
  const cargas = sim.cargasLista;
  await act(async () => { await new Promise((r) => setTimeout(r, 7000)); });
  expect(sim.cargasLista).toBe(cargas);
}, 30000);
