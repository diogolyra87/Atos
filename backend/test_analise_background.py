"""Testes da analise de upload em segundo plano (21/09/2026).

Contexto do incidente: ata NDB AGOE (17 paginas, fonte sem ToUnicode). A leitura
(cid-soup -> OCR) levou ~6m40s, o nginx cortou o request aos 180s (504), a tela
nunca recebeu os dados e o processo ficou preso em 'pendente_processamento'.

Garantias cobertas:
- leitura rapida (dentro da janela): resposta IDENTICA a de antes; quem conclui e' a tela
- leitura lenta: responde NA HORA {"processando": True}, e o SERVIDOR conclui o processo
  sozinho quando a leitura termina (status 'aberto', dados gravados, pos-criacao disparado 1x)
- GET /processos/{id}/analise acompanha (lendo -> concluido), respeita permissao de grupo
- tela antiga tentando concluir um processo que o servidor assumiu: ignorada (sem sobrescrever
  com campos vazios, sem duplicar e-mails/alertas)
- processo excluido no meio da leitura: resultado descartado, sem excecao/500
- leitura que quebra: falha_processamento + alerta, sem concluir
- suspeita de duplicidade na conclusao automatica: confirmacao_pendente + nota, nunca bloqueia
- resgate periodico: com dados -> conclui; vazio -> retoma a leitura do arquivo (1 vez);
  ja retomado e vazio -> falha_processamento; recente ou com job ativo -> nao mexe

Roda contra sqlite em memoria e diretorio de uploads temporario (nao toca mane.db nem uploads/).
Rodar com: python -m unittest test_analise_background -v
"""

import os
import shutil
import tempfile
import threading
import time
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, Usuario, Processo, Evento

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)

import main  # noqa: E402  (import apos criar o schema de teste)
from main import app, get_db, hash_token_sessao  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)

DADOS_IA = {
    "empresa": "neoenergia distribuicao brasilia s.a.", "cnpj": "07.522.669/0001-92", "nire": "53.300.007.811",
    "uf": "DF", "uf_destino_transferencia": "", "tipo_sociedade": "SA", "tipo_ato": "AGOE",
    "identificador_ato": "AGOE 29/04/2026", "data_ata": "29/04/2026", "hora_ata": "", "email_cliente": "",
    "eventos": ["aprovacao de contas"], "requer_cpl": False, "checklist": [], "observacoes": "",
}
TEXTO_OK = "NDB AGOE 001/26 NEOENERGIA DISTRIBUICAO BRASILIA S.A. " * 5  # > 50 chars


def _criar_usuario(db, login, grupo_id, is_admin=False):
    tok = "tok-" + uuid.uuid4().hex
    u = Usuario(
        id=str(uuid.uuid4()), login=login, senha_hash="x", grupo_id=grupo_id,
        token=hash_token_sessao(tok), token_criado_em=datetime.now(),
        is_admin=is_admin, papel="admin" if is_admin else "cliente",
    )
    db.add(u)
    db.commit()
    u.token_puro = tok
    return u


def _esperar(cond, timeout=6.0):
    fim = time.time() + timeout
    while time.time() < fim:
        if cond():
            return True
        time.sleep(0.05)
    return False


class Base_(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="atos_uploads_teste_")
        self.db = TestingSessionLocal()
        # banco em memoria e' compartilhado entre os testes (StaticPool): limpa pra um teste
        # nao enxergar processos pendentes/duplicados deixados pelo anterior
        self.db.query(Evento).delete()
        self.db.query(Processo).delete()
        self.db.commit()
        self.grupo = "grupo-" + uuid.uuid4().hex[:6]
        self.cliente = _criar_usuario(self.db, "cli_" + uuid.uuid4().hex[:6], self.grupo)
        self.outro = _criar_usuario(self.db, "out_" + uuid.uuid4().hex[:6], "grupo-outro-" + uuid.uuid4().hex[:6])
        self.admin = _criar_usuario(self.db, "adm_" + uuid.uuid4().hex[:6], "grupo-adm", is_admin=True)

        self.pos = MagicMock()          # _pos_criacao_processo_thread
        self.telegram = MagicMock()
        self.liberar = threading.Event()  # a "leitura" so' termina quando o teste libera
        self.leitura_iniciada = threading.Event()
        self.texto = TEXTO_OK
        self.erro_leitura = None

        def _extrair(conteudo, nome):
            self.leitura_iniciada.set()
            self.liberar.wait(timeout=15)
            if self.erro_leitura:
                raise self.erro_leitura
            return self.texto

        self.patches = [
            patch.object(main, "UPLOADS_DIR", self.tmp),
            patch.object(main, "ANALISE_ESPERA_SEG", 0.6),
            patch.object(main, "_extrair_texto_bytes", _extrair),
            patch.object(main, "analisar_ata_ia", lambda texto: dict(DADOS_IA)),
            patch.object(main, "_pos_criacao_processo_thread", self.pos),
            patch.object(main, "notificar_telegram", self.telegram),
            patch("database.SessionLocal", TestingSessionLocal),
        ]
        for p in self.patches:
            p.start()
        main._ANALISES.clear()

    def tearDown(self):
        self.liberar.set()
        for p in reversed(self.patches):
            p.stop()
        main._ANALISES.clear()
        self.db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _h(self, u):
        return {"x-token": u.token_puro}

    def _upload(self, u=None, nome="ata.pdf"):
        u = u or self.cliente
        return client.post(
            "/processos/analisar",
            files={"arquivo": (nome, b"%PDF-1.4 conteudo", "application/pdf")},
            headers=self._h(u),
        )

    def _proc(self, pid):
        self.db.expire_all()
        return self.db.query(Processo).filter(Processo.id == pid).first()

    def _pendente(self, idade_min, com_dados=False, com_arquivo=False, obs=""):
        pid = "MN-RESGATE-" + uuid.uuid4().hex[:6].upper()
        nome = pid + "_ata.pdf"
        if com_arquivo:
            with open(os.path.join(self.tmp, nome), "wb") as f:
                f.write(b"%PDF-1.4 arquivo em uploads")
        p = Processo(
            id=pid, empresa="ACME S.A." if com_dados else "", cnpj="", tipo_ato="AGE" if com_dados else "",
            data_ata="01/01/2026" if com_dados else "", status="pendente_processamento",
            arquivo_ata=nome, grupo_id=self.grupo, observacoes=obs,
            criado_em=datetime.now() - timedelta(minutes=idade_min),
        )
        self.db.add(p)
        self.db.commit()
        return pid


class TestLeituraRapida(Base_):
    def test_dentro_da_janela_resposta_identica_a_de_antes(self):
        self.liberar.set()  # leitura instantanea
        resp = self._upload()
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertNotIn("processando", d)
        self.assertEqual(d["tipo_ato"], "AGOE")
        self.assertEqual(d["identificador_ato"], "AGOE 29/04/2026")
        self.assertIn("processo_id", d)
        self.assertEqual(d["texto_extraido"], TEXTO_OK)
        self.assertFalse(d["leitura_parcial"])

    def test_rapida_grava_dados_mas_quem_conclui_e_a_tela(self):
        self.liberar.set()
        d = self._upload().json()
        p = self._proc(d["processo_id"])
        self.assertEqual(p.empresa, "NEOENERGIA DISTRIBUICAO BRASILIA S.A.")
        self.assertEqual(p.status, "pendente_processamento")  # a tela confirma via POST /processos
        self.assertFalse(main._analise_assumida_pelo_servidor(d["processo_id"]))
        self.pos.assert_not_called()


class TestLeituraLenta(Base_):
    def test_responde_na_hora_com_processando_sem_esperar_a_leitura(self):
        t0 = time.time()
        resp = self._upload()
        dur = time.time() - t0
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d["processando"])
        self.assertTrue(d["processo_id"].startswith("MN-"))
        self.assertLess(dur, 5, "o request nao pode ficar preso ate a leitura acabar")
        # o processo ja existe (insert garantido), vazio e pendente
        p = self._proc(d["processo_id"])
        self.assertEqual(p.status, "pendente_processamento")
        self.assertEqual(p.empresa, "")

    def test_servidor_conclui_sozinho_quando_a_leitura_termina(self):
        pid = self._upload().json()["processo_id"]
        self.assertTrue(self.leitura_iniciada.wait(3))
        self.assertTrue(main._analise_assumida_pelo_servidor(pid))

        self.liberar.set()  # a leitura demorada finalmente termina
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "aberto"), "servidor nao concluiu o processo")
        p = self._proc(pid)
        self.assertEqual(p.empresa, "NEOENERGIA DISTRIBUICAO BRASILIA S.A.")
        self.assertEqual(p.cnpj, "07.522.669/0001-92")
        self.assertEqual(p.uf, "DF")
        self.assertEqual(p.tipo_ato, "AGOE")
        self.assertEqual(p.data_ata, "29/04/2026")
        self.assertEqual(p.texto_documento_extraido, TEXTO_OK)
        self.assertTrue(_esperar(lambda: self.pos.call_count == 1), "pos-criacao (e-mails/alertas) deveria disparar 1x")
        self.assertEqual(self.pos.call_args[0][0], pid)

    def test_acompanhamento_lendo_e_depois_concluido(self):
        pid = self._upload().json()["processo_id"]
        r1 = client.get(f"/processos/{pid}/analise", headers=self._h(self.cliente)).json()
        self.assertEqual(r1["estado"], "lendo")

        self.liberar.set()
        self.assertTrue(_esperar(lambda: client.get(f"/processos/{pid}/analise", headers=self._h(self.cliente)).json()["estado"] == "concluido"))
        r2 = client.get(f"/processos/{pid}/analise", headers=self._h(self.cliente)).json()
        self.assertTrue(r2["ja_criado"])
        self.assertEqual(r2["dados"]["tipo_ato"], "AGOE")

    def test_acompanhamento_respeita_permissao_de_grupo(self):
        pid = self._upload().json()["processo_id"]
        self.assertEqual(client.get(f"/processos/{pid}/analise", headers=self._h(self.outro)).status_code, 403)
        self.assertEqual(client.get(f"/processos/{pid}/analise", headers=self._h(self.admin)).status_code, 200)
        self.assertEqual(client.get(f"/processos/{pid}/analise").status_code, 401)

    def test_acompanhamento_de_processo_inexistente_e_cancelado(self):
        r = client.get("/processos/MN-00000000000000-XXXX/analise", headers=self._h(self.admin)).json()
        self.assertEqual(r["estado"], "cancelado")


class TestTelaAntigaNaoDuplica(Base_):
    def _post_processos(self, pid, dados):
        import json
        info = dict(dados)
        info["processo_id"] = pid
        return client.post("/processos", data={"dados": json.dumps(info)}, headers=self._h(self.cliente))

    def test_tela_antiga_tentando_concluir_enquanto_le_e_ignorada(self):
        pid = self._upload().json()["processo_id"]
        # tela de antes do deploy nao entende "processando": manda os campos VAZIOS da resposta
        resp = self._post_processos(pid, {"empresa": "", "tipo_ato": "", "data_ata": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("processando"))
        p = self._proc(pid)
        self.assertEqual(p.status, "pendente_processamento")  # nao virou 'aberto' com campos vazios
        self.pos.assert_not_called()

        self.liberar.set()
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "aberto"))
        self.assertEqual(self._proc(pid).tipo_ato, "AGOE")  # dados reais, nao sobrescritos por vazio

    def test_tela_tentando_concluir_depois_que_o_servidor_ja_concluiu_nao_duplica(self):
        pid = self._upload().json()["processo_id"]
        self.liberar.set()
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "aberto"))
        self.assertTrue(_esperar(lambda: self.pos.call_count == 1))

        resp = self._post_processos(pid, DADOS_IA)
        self.assertEqual(resp.status_code, 200)
        time.sleep(0.3)
        self.assertEqual(self.pos.call_count, 1, "pos-criacao nao pode disparar de novo")


class TestExclusaoEFalhas(Base_):
    def test_processo_excluido_no_meio_da_leitura_descarta_sem_erro(self):
        pid = self._upload().json()["processo_id"]
        self.assertTrue(self.leitura_iniciada.wait(3))
        r = client.delete(f"/processos/{pid}", headers=self._h(self.admin))
        self.assertEqual(r.status_code, 200)

        self.liberar.set()  # a leitura termina DEPOIS da exclusao
        self.assertTrue(_esperar(lambda: main._ANALISES[pid]["estado"] == "cancelado"))
        self.assertIsNone(self._proc(pid))
        self.pos.assert_not_called()
        self.assertEqual(client.get(f"/processos/{pid}/analise", headers=self._h(self.admin)).json()["estado"], "cancelado")

    def test_leitura_que_quebra_marca_falha_e_alerta_sem_concluir(self):
        self.erro_leitura = RuntimeError("tesseract explodiu")
        pid = self._upload().json()["processo_id"]
        self.liberar.set()
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "falha_processamento"))
        self.assertIn("tesseract explodiu", self._proc(pid).observacoes)
        self.assertTrue(self.telegram.called, "operador precisa ser alertado")
        self.pos.assert_not_called()
        self.assertEqual(client.get(f"/processos/{pid}/analise", headers=self._h(self.admin)).json()["estado"], "falhou")

    def test_leitura_que_quebra_dentro_da_janela_devolve_campos_vazios_como_antes(self):
        self.erro_leitura = RuntimeError("falhou rapido")
        self.liberar.set()
        d = self._upload().json()
        self.assertNotIn("processando", d)
        self.assertTrue(d["leitura_parcial"])
        self.assertEqual(d["empresa"], "")
        self.assertEqual(self._proc(d["processo_id"]).status, "falha_processamento")


class TestDuplicidadeNaConclusaoAutomatica(Base_):
    def test_suspeita_de_duplicata_vira_confirmacao_pendente_nao_bloqueia(self):
        existente = Processo(
            id="MN-EXISTENTE-0001", empresa="NEOENERGIA DISTRIBUICAO BRASILIA S.A.", cnpj="07.522.669/0001-92",
            tipo_ato="AGOE", identificador_ato="AGOE 29/04/2026", data_ata="29/04/2026", status="aberto",
            grupo_id=self.grupo,
        )
        self.db.add(existente)
        self.db.commit()

        pid = self._upload().json()["processo_id"]
        self.liberar.set()
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "aberto"))  # NAO bloqueia
        p = self._proc(pid)
        self.assertTrue(p.confirmacao_pendente)
        self.assertIn("MN-EXISTENTE-0001", p.observacoes)


class TestResgate(Base_):
    def test_com_dados_e_esquecido_ha_muito_tempo_conclui(self):
        pid = self._pendente(idade_min=60, com_dados=True)
        n = main._resgatar_pendentes_esquecidos()
        self.assertEqual(n, 1)
        self.assertEqual(self._proc(pid).status, "aberto")
        self.assertTrue(_esperar(lambda: self.pos.call_count == 1))

    def test_recente_nao_e_tocado(self):
        pid = self._pendente(idade_min=2, com_dados=True)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 0)
        self.assertEqual(self._proc(pid).status, "pendente_processamento")

    def test_com_job_ativo_nao_e_tocado(self):
        pid = self._pendente(idade_min=60, com_dados=True)
        main._analise_registrar(pid, None)  # leitura em andamento
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 0)
        self.assertEqual(self._proc(pid).status, "pendente_processamento")

    def test_vazio_retoma_a_leitura_do_arquivo_uma_vez_e_conclui(self):
        pid = self._pendente(idade_min=60, com_arquivo=True)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 1)
        # enquanto a leitura retomada roda, a marca impede uma segunda retomada
        self.assertTrue(self.leitura_iniciada.wait(3))
        self.assertIn(main._MARCA_REPROCESSADO, self._proc(pid).observacoes)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 0, "job ativo: nao pode retomar de novo")

        self.liberar.set()
        self.assertTrue(_esperar(lambda: self._proc(pid).status == "aberto"), "leitura retomada deveria concluir")
        self.assertEqual(self._proc(pid).tipo_ato, "AGOE")

    def test_vazio_ja_retomado_sem_resultado_vira_falha_com_alerta(self):
        pid = self._pendente(idade_min=60, com_arquivo=True, obs=main._MARCA_REPROCESSADO)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 1)
        self.assertEqual(self._proc(pid).status, "falha_processamento")
        self.assertTrue(self.telegram.called)

    def test_vazio_sem_arquivo_vira_falha(self):
        pid = self._pendente(idade_min=60, com_arquivo=False)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 1)
        self.assertEqual(self._proc(pid).status, "falha_processamento")

    def test_varredura_de_subida_so_retoma_vazios_e_deixa_os_com_dados(self):
        vazio = self._pendente(idade_min=1, com_arquivo=True)
        com_dados = self._pendente(idade_min=1, com_dados=True)
        self.liberar.set()
        n = main._resgatar_pendentes_esquecidos(idade_min=0, so_vazios=True)
        self.assertEqual(n, 1)
        self.assertTrue(_esperar(lambda: self._proc(vazio).status == "aberto"))
        self.assertEqual(self._proc(com_dados).status, "pendente_processamento")


class TestLote(Base_):
    """analisar-pasta-multi: mesma ideia, mas a tela continua concluindo cada processo (ha
    confirmacoes humanas no fluxo de pasta) - so' acompanha o job por GET /analise-lote."""

    def setUp(self):
        super().setUp()
        self.classificador_erro = None

        def _classificar(candidatos):
            if self.classificador_erro:
                raise self.classificador_erro
            # o primeiro arquivo e' a ata principal; o resto vira anexo
            return {c["indice"]: {"principal": c["indice"] == 0} for c in candidatos}

        for pt in (
            patch.object(main, "_classificar_lote_ia", _classificar),
            patch.object(main, "_tentar_extrair_protocolo", lambda *a, **k: None),
        ):
            pt.start()
            self.patches.append(pt)

    def _upload_lote(self, nomes=("ata.pdf", "anexo1.pdf"), u=None, **form):
        u = u or self.cliente
        files = [("arquivos", (n, b"%PDF-1.4 " + n.encode(), "application/pdf")) for n in nomes]
        return client.post("/processos/analisar-pasta-multi", files=files, data=form, headers=self._h(u))

    def test_lote_rapido_devolve_a_estrutura_de_sempre_e_poda_o_anexo(self):
        self.liberar.set()
        resp = self._upload_lote()
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertNotIn("processando", d)
        self.assertEqual(len(d["principais"]), 1)
        self.assertEqual(len(d["anexos"]), 1)
        pid = d["principais"][0]["dados"]["processo_id"]
        self.assertEqual(self._proc(pid).tipo_ato, "AGOE")
        # so' o principal sobrevive; o pendente do anexo foi podado
        self.assertEqual(self.db.query(Processo).count(), 1)

    def test_lote_lento_responde_na_hora_e_a_tela_acompanha(self):
        t0 = time.time()
        resp = self._upload_lote()
        self.assertLess(time.time() - t0, 5)
        d = resp.json()
        self.assertTrue(d["processando"])
        self.assertTrue(d["job_id"].startswith("LT-"))
        self.assertEqual(len(d["processo_ids"]), 2)
        # os pendentes JA existem (insert garantido), vazios
        for pid in d["processo_ids"]:
            self.assertEqual(self._proc(pid).status, "pendente_processamento")

        h = self._h(self.cliente)
        self.assertEqual(client.get(f"/processos/analise-lote/{d['job_id']}", headers=h).json()["estado"], "lendo")

        self.liberar.set()
        self.assertTrue(_esperar(lambda: client.get(f"/processos/analise-lote/{d['job_id']}", headers=h).json()["estado"] == "concluido"))
        r = client.get(f"/processos/analise-lote/{d['job_id']}", headers=h).json()["resultado"]
        self.assertEqual(len(r["principais"]), 1)
        self.assertEqual(r["principais"][0]["dados"]["tipo_ato"], "AGOE")
        self.assertEqual(len(r["anexos"]), 1)
        self.assertEqual(self.db.query(Processo).count(), 1, "anexo deveria ter sido podado")

    def test_acompanhamento_do_lote_respeita_dono_e_admin(self):
        job_id = self._upload_lote().json()["job_id"]
        self.assertEqual(client.get(f"/processos/analise-lote/{job_id}", headers=self._h(self.outro)).status_code, 403)
        self.assertEqual(client.get(f"/processos/analise-lote/{job_id}", headers=self._h(self.admin)).status_code, 200)
        self.assertEqual(client.get(f"/processos/analise-lote/{job_id}").status_code, 401)
        self.assertEqual(client.get("/processos/analise-lote/LT-naoexiste", headers=self._h(self.admin)).json()["estado"], "desconhecido")

    def test_job_do_lote_que_quebra_marca_pendentes_como_falha_e_alerta(self):
        self.classificador_erro = RuntimeError("classificador fora do ar")
        d = self._upload_lote().json()
        self.assertTrue(d["processando"])
        self.liberar.set()
        self.assertTrue(_esperar(lambda: client.get(f"/processos/analise-lote/{d['job_id']}", headers=self._h(self.cliente)).json()["estado"] == "falhou"))
        for pid in d["processo_ids"]:
            self.assertEqual(self._proc(pid).status, "falha_processamento")
        self.assertTrue(self.telegram.called)

    def test_lote_que_quebra_dentro_da_janela_devolve_500_como_antes(self):
        self.classificador_erro = RuntimeError("classificador fora do ar")
        self.liberar.set()
        self.assertEqual(self._upload_lote().status_code, 500)

    def test_pre_classificacao_nao_cria_pendentes(self):
        self.liberar.set()
        d = self._upload_lote(pre_classificacao="true").json()
        self.assertNotIn("processando", d)
        self.assertEqual(self.db.query(Processo).count(), 0)


class TestResgateRespeitaLote(Base_):
    def _pendente_de_lote(self, com_dados):
        pid = self._pendente(idade_min=60, com_dados=com_dados, com_arquivo=True)
        from database import Evento
        self.db.add(Evento(id=str(uuid.uuid4()), processo_id=pid, grupo_id=self.grupo, tipo="ata_recebida",
                           descricao="Arquivo recebido em lote, processando..."))
        self.db.commit()
        return pid

    def test_vazio_de_lote_nao_e_retomado_isolado_vira_falha(self):
        pid = self._pendente_de_lote(com_dados=False)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 1)
        p = self._proc(pid)
        self.assertEqual(p.status, "falha_processamento")
        self.assertNotIn(main._MARCA_REPROCESSADO, p.observacoes)  # nao chegou a retomar
        self.assertFalse(self.leitura_iniciada.is_set())

    def test_de_lote_com_dados_e_concluido_normalmente(self):
        pid = self._pendente_de_lote(com_dados=True)
        self.assertEqual(main._resgatar_pendentes_esquecidos(), 1)
        self.assertEqual(self._proc(pid).status, "aberto")


if __name__ == "__main__":
    unittest.main()
