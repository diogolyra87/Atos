import { sessaoExpirou } from "./sessaoExpirada";

// Formato do erro do axios 1.x: error.config.headers e' um AxiosHeaders (tem .get);
// o helper tambem aceita objeto simples.
function erro(status, { url = "/processos", token = "tok-admin", comGet = true } = {}) {
  const headersObj = token === null ? {} : { "x-token": token };
  const headers = comGet
    ? { get: (k) => headersObj[k.toLowerCase()], ...headersObj }
    : headersObj;
  return { response: status === undefined ? undefined : { status }, config: { url, headers } };
}

describe("sessaoExpirou", () => {
  test("401 numa requisicao autenticada com o token da sessao atual = expirou", () => {
    expect(sessaoExpirou(erro(401), "tok-admin")).toBe(true);
    expect(sessaoExpirou(erro(401, { comGet: false }), "tok-admin")).toBe(true);
  });

  test("outros status nao encerram a sessao", () => {
    for (const s of [400, 403, 404, 422, 429, 500, 502]) {
      expect(sessaoExpirou(erro(s), "tok-admin")).toBe(false);
    }
  });

  test("erro de rede (sem response) nao encerra a sessao", () => {
    expect(sessaoExpirou(erro(undefined), "tok-admin")).toBe(false);
    expect(sessaoExpirou(new Error("Network Error"), "tok-admin")).toBe(false);
    expect(sessaoExpirou(null, "tok-admin")).toBe(false);
  });

  test("sem sessao ativa nao faz nada (resposta atrasada depois de sair)", () => {
    expect(sessaoExpirou(erro(401), null)).toBe(false);
    expect(sessaoExpirou(erro(401), undefined)).toBe(false);
    expect(sessaoExpirou(erro(401), "")).toBe(false);
  });

  test("401 de OUTRO token nao desloga o admin (ex: portal do cliente na mesma aba)", () => {
    expect(sessaoExpirou(erro(401, { token: "tok-cliente" }), "tok-admin")).toBe(false);
  });

  test("401 sem token na requisicao nao desloga", () => {
    expect(sessaoExpirou(erro(401, { token: null }), "tok-admin")).toBe(false);
  });

  test("401 de login, verificacao 2FA e logout e' credencial errada / ja deslogado, nao sessao expirada", () => {
    for (const url of ["/login", "/login/verificar", "/logout", "/login?x=1"]) {
      expect(sessaoExpirou(erro(401, { url }), "tok-admin")).toBe(false);
    }
  });

  test("rotas parecidas com login NAO sao excecao", () => {
    for (const url of ["/processos", "/usuarios/login-historico", "/grupos/logout-todos-x", "/api/processos/123"]) {
      expect(sessaoExpirou(erro(401, { url }), "tok-admin")).toBe(true);
    }
  });
});
