/** @jest-environment jsdom */
// Integracao: monta o App REAL com uma sessao admin salva no localStorage e um
// adaptador do axios que responde 401 (ou outro status) a tudo. Prova que o
// interceptor do App.js (a) devolve o painel pro login com aviso quando o
// servidor invalida o token, e (b) NAO desloga por erro que nao e' de sessao.
//
// axios 1.x e' ESM e o Jest do CRA nao transforma node_modules - usa o build CJS.
jest.mock("axios", () => jest.requireActual("axios/dist/node/axios.cjs"));
// react-router-dom v7 usa "exports" do package.json, que o Jest 27 do CRA nao resolve.
// O painel so' usa useSearchParams (Cliente.js) e nao depende de rota pra este teste.
jest.mock("react-router-dom", () => ({ useSearchParams: () => [new URLSearchParams(), () => {}] }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// APIs de browser que o painel usa e o jsdom nao tem
window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
window.scrollTo = () => {};
global.ResizeObserver = global.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
global.IntersectionObserver = global.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };

const SESSAO = { token: "tok-velho", login: "diogo", nome: "Diogo", is_admin: true, papel: "admin", grupo_id: "g1" };

function montarApp(statusDasRespostas) {
  localStorage.clear();
  localStorage.setItem("atos_admin", JSON.stringify(SESSAO));
  // resetModules + require de TUDO junto (react, react-dom, axios, App): o App.js le o
  // localStorage e seta o header x-token no IMPORT, e react/react-dom precisam ser a
  // mesma copia (isolateModules so' no App gera duas copias de React)
  jest.resetModules();
  const React = require("react");
  const { createRoot } = require("react-dom/client");
  const axios = require("axios");
  const App = require("./App").default;
  const chamadas = [];
  axios.defaults.adapter = async (config) => {
    chamadas.push({ url: config.url, token: config.headers.get("x-token") });
    // AppPainel.carregar() (App.js, de 17/06) nao tem try/catch: se /processos ou /metricas
    // falharem, gera rejeicao sem tratamento e o Jest reprova o teste (comportamento antigo,
    // fora do escopo do interceptor). Essas duas respondem 200; TODAS as outras falham.
    if (config.url === "/processos" || config.url === "/metricas") {
      return { status: 200, statusText: "OK", data: config.url === "/processos" ? [] : {}, headers: {}, config };
    }
    const resp = { status: statusDasRespostas, statusText: "x", data: { detail: "x" }, headers: {}, config };
    throw new axios.AxiosError("falhou", "ERR_BAD_REQUEST", config, null, resp);
  };
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  return { axios, App, root, el, chamadas, act: React.act, createElement: React.createElement };
}

async function renderizarEEsperar({ App, root, act, createElement }) {
  await act(async () => {
    root.render(createElement(App));
  });
  // deixa as requisicoes do painel falharem e os setState do interceptor rodarem
  for (let i = 0; i < 5; i++) {
    await act(async () => { await new Promise((r) => setTimeout(r, 20)); });
  }
}

let erroConsole;
beforeEach(() => { erroConsole = jest.spyOn(console, "error").mockImplementation(() => {}); });
afterEach(() => { erroConsole.mockRestore(); document.body.innerHTML = ""; });

test("401 nas requisicoes do painel admin -> volta pro login com aviso e limpa a sessao", async () => {
  const ctx = montarApp(401);
  await renderizarEEsperar(ctx);

  // o painel realmente tentou carregar coisas com o token velho
  expect(ctx.chamadas.length).toBeGreaterThan(0);
  expect(ctx.chamadas.some((c) => c.token === "tok-velho")).toBe(true);

  expect(ctx.el.textContent).toContain("Sua sessao expirou. Entre novamente.");
  expect(ctx.el.textContent).toContain("Painel do Administrador"); // tela de login
  expect(localStorage.getItem("atos_admin")).toBeNull();
  expect(ctx.axios.defaults.headers.common["x-token"]).toBeUndefined();
});

test("erro 500 do servidor NAO desloga: sessao e painel continuam", async () => {
  const ctx = montarApp(500);
  await renderizarEEsperar(ctx);

  expect(ctx.chamadas.length).toBeGreaterThan(0);
  expect(ctx.el.textContent).not.toContain("Sua sessao expirou");
  expect(localStorage.getItem("atos_admin")).not.toBeNull();
  expect(ctx.axios.defaults.headers.common["x-token"]).toBe("tok-velho");
});
