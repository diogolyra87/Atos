// Decide se um erro de axios significa "a sessao do painel expirou ou foi
// invalidada no servidor" (401 numa requisicao autenticada com o token da
// sessao atual). Usado pelo interceptor global do App.js.
//
// Por que existe: desde o logout real + token com hash (auditoria de seguranca
// 18/09/2026) o servidor pode invalidar um token de uma hora pra outra. Sem
// isso o painel admin ficava preso em "Erro ao carregar" ate alguem clicar em
// Sair (so o portal do cliente tratava 401).
//
// Regras (todas precisam valer):
// - status 401
// - a requisicao levou o MESMO token da sessao admin atual. Isso evita deslogar
//   o admin por causa de um 401 de outra origem (ex: portal do cliente aberto na
//   mesma aba/navegador, que manda o proprio token explicito) e evita reagir a
//   uma resposta atrasada de uma sessao que ja foi encerrada
// - nao e' /login, /login/verificar nem /logout: la o 401 e' "credencial/codigo
//   errado" ou "ja deslogado", nao sessao expirada
export function sessaoExpirou(error, tokenSessao) {
  if (!error || !error.response || error.response.status !== 401) return false;
  if (!tokenSessao) return false;
  const cfg = error.config || {};
  if (/\/(login|logout)(\/|\?|$)/.test(cfg.url || "")) return false;
  const h = cfg.headers;
  const tokenReq = h && (typeof h.get === "function" ? h.get("x-token") : h["x-token"]);
  return tokenReq === tokenSessao;
}
