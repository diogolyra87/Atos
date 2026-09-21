import { analisarDocumento, analisarLote } from "./analisarComEspera";

// axios falso: post responde a fila "posts", get responde a fila "gets" (Error = rejeita)
function fakeAxios({ posts = [], gets = [] }) {
  const chamadas = { post: [], get: [] };
  const fila = (lista, tipo) => (url, ...resto) => {
    chamadas[tipo].push([url, ...resto]);
    const proximo = lista.length > 1 ? lista.shift() : lista[0];
    if (proximo instanceof Error) return Promise.reject(proximo);
    return Promise.resolve({ data: proximo });
  };
  return { post: fila(posts, "post"), get: fila(gets, "get"), chamadas };
}

const semEspera = { intervaloMs: 0, dormirFn: () => Promise.resolve() };
const erroHttp = (status) => Object.assign(new Error("http " + status), { response: { status } });

describe("analisarDocumento", () => {
  test("resposta rapida passa direto, sem polling (comportamento de antes)", async () => {
    const ax = fakeAxios({ posts: [{ empresa: "ACME", tipo_ato: "AGE", processo_id: "MN-1" }] });
    const res = await analisarDocumento(ax, "form", undefined, semEspera);
    expect(res.data.empresa).toBe("ACME");
    expect(res.data.ja_criado).toBeUndefined();
    expect(ax.chamadas.get.length).toBe(0);
  });

  test("resposta 'processando' -> acompanha ate concluir e devolve ja_criado", async () => {
    const ax = fakeAxios({
      posts: [{ processando: true, processo_id: "MN-9" }],
      gets: [{ estado: "lendo" }, { estado: "lendo" }, { estado: "concluido", ja_criado: true, dados: { empresa: "NEO", tipo_ato: "AGOE" } }],
    });
    const espera = [];
    const res = await analisarDocumento(ax, "form", { headers: { "x-token": "t" } }, { ...semEspera, base: "/api", onEspera: (v) => espera.push(v) });
    expect(res.data).toMatchObject({ empresa: "NEO", tipo_ato: "AGOE", processo_id: "MN-9", ja_criado: true });
    expect(ax.chamadas.get[0][0]).toBe("/api/processos/MN-9/analise");
    expect(ax.chamadas.get[0][1]).toEqual({ headers: { "x-token": "t" } });
    expect(ax.chamadas.get.length).toBe(3);
    expect(espera).toEqual([true, false]); // liga a mensagem "lendo" e desliga no fim
  });

  test("falhou e cancelado viram erro com motivo e mensagem pronta", async () => {
    for (const estado of ["falhou", "cancelado"]) {
      const ax = fakeAxios({ posts: [{ processando: true, processo_id: "MN-2" }], gets: [{ estado }] });
      await expect(analisarDocumento(ax, "f", undefined, semEspera)).rejects.toMatchObject({ motivo: estado });
    }
  });

  test("falha de rede pontual no acompanhamento nao derruba; varias seguidas sim", async () => {
    const ok = fakeAxios({
      posts: [{ processando: true, processo_id: "MN-3" }],
      gets: [new Error("rede"), new Error("rede"), { estado: "concluido", ja_criado: true, dados: {} }],
    });
    // fila com Error nao repete o ultimo: monta explicitamente
    const res = await analisarDocumento(ok, "f", undefined, semEspera);
    expect(res.data.ja_criado).toBe(true);

    const ruim = fakeAxios({ posts: [{ processando: true, processo_id: "MN-4" }], gets: [new Error("rede")] });
    await expect(analisarDocumento(ruim, "f", undefined, semEspera)).rejects.toThrow("rede");
    expect(ruim.chamadas.get.length).toBe(5);
  });

  test("401/403 no acompanhamento nao insiste (sessao invalida)", async () => {
    const ax = fakeAxios({ posts: [{ processando: true, processo_id: "MN-5" }], gets: [erroHttp(401)] });
    await expect(analisarDocumento(ax, "f", undefined, semEspera)).rejects.toMatchObject({ response: { status: 401 } });
    expect(ax.chamadas.get.length).toBe(1);
  });

  test("passou do limite de tempo -> erro 'tempo_esgotado' que explica que o processo segue", async () => {
    const ax = fakeAxios({ posts: [{ processando: true, processo_id: "MN-6" }], gets: [{ estado: "lendo" }] });
    const e = await analisarDocumento(ax, "f", undefined, { ...semEspera, limiteMs: 30 }).catch((x) => x);
    expect(e.motivo).toBe("tempo_esgotado");
    expect(e.message).toMatch(/concluído automaticamente/);
  });

  test("onEspera desliga mesmo quando da erro", async () => {
    const ax = fakeAxios({ posts: [{ processando: true, processo_id: "MN-7" }], gets: [{ estado: "falhou" }] });
    const espera = [];
    await analisarDocumento(ax, "f", undefined, { ...semEspera, onEspera: (v) => espera.push(v) }).catch(() => {});
    expect(espera).toEqual([true, false]);
  });
});

describe("analisarLote", () => {
  test("resposta rapida passa direto", async () => {
    const ax = fakeAxios({ posts: [{ principais: [{ indice: 0 }], anexos: [] }] });
    const res = await analisarLote(ax, "f", undefined, semEspera);
    expect(res.data.principais.length).toBe(1);
    expect(ax.chamadas.get.length).toBe(0);
  });

  test("'processando' -> acompanha e devolve a estrutura de sempre", async () => {
    const resultado = { principais: [{ indice: 0, dados: { empresa: "X" } }], anexos: [{ indice: 1 }], multiplo: false };
    const ax = fakeAxios({
      posts: [{ processando: true, job_id: "LT-abc", processo_ids: ["MN-1", "MN-2"] }],
      gets: [{ estado: "lendo" }, { estado: "concluido", resultado }],
    });
    const res = await analisarLote(ax, "f", undefined, { ...semEspera, base: "" });
    expect(res.data).toEqual(resultado);
    expect(ax.chamadas.get[0][0]).toBe("/processos/analise-lote/LT-abc");
  });

  test("falhou e desconhecido (servico reiniciou) viram erro com motivo", async () => {
    for (const estado of ["falhou", "desconhecido"]) {
      const ax = fakeAxios({ posts: [{ processando: true, job_id: "LT-x" }], gets: [{ estado }] });
      await expect(analisarLote(ax, "f", undefined, semEspera)).rejects.toMatchObject({ motivo: estado });
    }
  });
});
