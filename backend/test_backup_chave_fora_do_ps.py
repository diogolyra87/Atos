"""Teste de que a chave de criptografia do backup NAO vai na linha de comando
(auditoria de seguranca 18/09/2026, item "chave de criptografia do backup
visivel via ps aux durante o cron").

Antes: `openssl enc ... -pass pass:"$CRYPT_KEY"` - argumento de processo, lido
por qualquer usuario local via `ps aux` / /proc/PID/cmdline enquanto o
openssl roda. Agora: `printf ... "$CRYPT_KEY" | openssl ... -pass stdin` (printf e' builtin do
bash: nao existe processo externo com a chave no argv).
Vale pros dois lados: cifragem (scripts/backup_db.sh) e decifragem na
restauracao automatica (scripts/check_db.sh).

Como testa:
- roda o backup_db.sh DE VERDADE (bash + gzip + openssl), com os caminhos
  /root/atos reescritos pra um diretorio temporario
- uma funcao de shell `openssl` grava os argumentos que recebeu (= o que o
  `ps` mostraria) e repassa pro openssl real
- `rclone` e `sqlite3` sao substituidos por stubs: o script real faz
  `rclone copy/delete gdrive:ATOS_Backups/` - o teste NUNCA pode falar com o
  Drive de verdade
- confere que a chave nao aparece nos argumentos, e que o arquivo cifrado
  ainda decifra com o formato antigo (`-pass pass:CHAVE`), ou seja, backups
  antigos e restauracao manual seguem compativeis
- check_db.sh nao da' pra rodar inteiro (restart de servico, e-mail, sqlite3),
  entao a linha de decifragem e' extraida do proprio script e executada

Rodar com: python -m unittest test_backup_chave_fora_do_ps -v
"""

import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_BACKUP = os.path.join(RAIZ, "scripts", "backup_db.sh")
SCRIPT_CHECK = os.path.join(RAIZ, "scripts", "check_db.sh")

# chave com espaco, $, aspas simples e duplas: exercita o quoting do here-string
# (sem '=': o script le a chave com `cut -d= -f2`, que corta no segundo '=')
CHAVE = "chave com espaco $HOME 'aspas' \"dupla\" #x"


def _achar_bash():
    if os.name == "nt":
        # no Windows, "bash" no PATH pode ser o WSL - o teste precisa do Git Bash
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                cand = os.path.join(base, "Git", "bin", "bash.exe")
                if os.path.exists(cand):
                    return cand
    return shutil.which("bash")


BASH = _achar_bash()


def _posix(caminho):
    return caminho.replace("\\", "/")


def _ferramentas_ok():
    if not BASH:
        return False
    r = subprocess.run([BASH, "-c", "command -v openssl gzip gunzip"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.count("\n") >= 3


@unittest.skipUnless(_ferramentas_ok(), "precisa de bash + openssl + gzip")
class TestChaveDoBackupForaDoPs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="atos_bkp_teste_")
        self.raiz = _posix(self.tmp) + "/atos"
        os.makedirs(os.path.join(self.tmp, "atos", "backend"))
        os.makedirs(os.path.join(self.tmp, "stubs"))

        # banco sqlite valido, pequeno
        self.db_path = os.path.join(self.tmp, "atos", "backend", "mane.db")
        con = sqlite3.connect(self.db_path)
        con.execute("CREATE TABLE t (x TEXT)")
        con.execute("INSERT INTO t VALUES ('dado-que-precisa-sobreviver-ao-backup')")
        con.commit()
        con.close()
        with open(self.db_path, "rb") as f:
            self.db_bytes = f.read()

        with open(os.path.join(self.tmp, "atos", ".env"), "w", encoding="utf-8", newline="\n") as f:
            f.write("OUTRA=1\nBACKUP_CRYPT_KEY=" + CHAVE + "\n")

        self.log_openssl = os.path.join(self.tmp, "openssl_argv.log")
        self.log_rclone = os.path.join(self.tmp, "rclone_calls.log")
        self._stub("rclone", '#!/bin/bash\nprintf \'%s\\n\' "$*" >> "$SHIM_LOG_RCLONE"\nexit 0\n')
        # sqlite3 falso que falha -> o script cai no `|| cp` (mesmo caminho quando sqlite3 nao existe)
        self._stub("sqlite3", "#!/bin/bash\nexit 1\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stub(self, nome, conteudo):
        p = os.path.join(self.tmp, "stubs", nome)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)
        os.chmod(p, 0o755)

    def _env(self):
        env = dict(os.environ)
        env["PATH"] = os.path.join(self.tmp, "stubs") + os.pathsep + env.get("PATH", "")
        env["SHIM_LOG_OPENSSL"] = _posix(self.log_openssl)
        env["SHIM_LOG_RCLONE"] = _posix(self.log_rclone)
        return env

    # funcao de shell que registra o argv do openssl (= o que o ps mostraria) e repassa
    # pro openssl de verdade. Funcao e nao stub no PATH: o PATH do Git Bash poe
    # /mingw64/bin na frente dos stubs.
    FUNC_OPENSSL = 'openssl() { printf "%s\\n" "$*" >> "$SHIM_LOG_OPENSSL"; command openssl "$@"; }; '

    def _script_reescrito(self, caminho, nome):
        with open(caminho, encoding="utf-8", newline="") as f:
            txt = f.read()
        txt = txt.replace("/root/atos", self.raiz)
        # seguranca do teste: nada pode apontar pro caminho real de producao
        self.assertNotIn("/root", txt)
        dest = os.path.join(self.tmp, nome)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        return dest

    def _rodar_backup(self):
        script = self._script_reescrito(SCRIPT_BACKUP, "backup_db.sh")
        # `.` (source) e nao subprocesso: a funcao openssl so' vale na mesma shell
        r = subprocess.run(
            [BASH, "-c", self.FUNC_OPENSSL + '. "$1"', "_", _posix(script)],
            capture_output=True, text=True, env=self._env(), timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        enc = [f for f in os.listdir(os.path.join(self.tmp, "atos", "backups")) if f.endswith(".gz.enc")]
        self.assertEqual(len(enc), 1, os.listdir(os.path.join(self.tmp, "atos", "backups")))
        return os.path.join(self.tmp, "atos", "backups", enc[0])

    def _argv_do_openssl(self):
        with open(self.log_openssl, encoding="utf-8") as f:
            return f.read()

    def test_cifragem_nao_poe_a_chave_na_linha_de_comando(self):
        self._rodar_backup()
        argv = self._argv_do_openssl()

        self.assertIn("aes-256-cbc", argv)  # o shim de fato interceptou a chamada
        self.assertNotIn("pass:", argv)
        for pedaco in ("chave", "espaco", "aspas", "dupla"):
            self.assertNotIn(pedaco, argv, "pedaco da chave apareceu na linha de comando do openssl")

    def test_arquivo_cifrado_decifra_com_o_formato_antigo_e_bate_com_o_banco(self):
        # compatibilidade: restauracao manual usa `-pass pass:CHAVE` e backups
        # antigos foram feitos assim - o novo formato tem que ser identico
        enc = self._rodar_backup()
        env = dict(os.environ, CHAVE=CHAVE)
        r = subprocess.run(
            [BASH, "-c", 'openssl enc -d -aes-256-cbc -pbkdf2 -in "$1" -pass pass:"$CHAVE" | gunzip -c', "_", _posix(enc)],
            capture_output=True, env=env, timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, self.db_bytes)

    def test_nao_sobra_backup_em_claro_e_o_drive_nunca_e_tocado_de_verdade(self):
        self._rodar_backup()
        pasta = os.path.join(self.tmp, "atos", "backups")
        self.assertEqual([f for f in os.listdir(pasta) if f.endswith(".gz")], [])
        # o rclone que rodou foi o stub (o teste nunca pode falar com o Drive real)
        with open(self.log_rclone, encoding="utf-8") as f:
            chamadas = f.read()
        self.assertIn("copy", chamadas)
        self.assertIn("gdrive:ATOS_Backups/", chamadas)

    def test_decifragem_do_check_db_usa_stdin_e_restaura_o_backup_novo(self):
        enc = self._rodar_backup()

        with open(SCRIPT_CHECK, encoding="utf-8", newline="") as f:
            texto = f.read()
        self.assertNotIn("pass:", texto)  # nenhum "-pass pass:" sobrando (o "stdin" nao tem dois pontos)
        linhas = [l for l in texto.replace("\r\n", "\n").split("\n") if "openssl enc -d" in l]
        self.assertEqual(len(linhas), 1, linhas)
        linha = linhas[0].strip()
        self.assertIn("-pass stdin", linha)

        # executa A LINHA REAL do check_db.sh (com $DB apontando pra um arquivo temporario)
        restaurado = os.path.join(self.tmp, "restaurado.db")
        env = self._env()
        env.update(CRYPT_KEY=CHAVE, ULTIMO_ENC=_posix(enc), DB=_posix(restaurado))
        r = subprocess.run([BASH, "-c", self.FUNC_OPENSSL + linha], capture_output=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(restaurado, "rb") as f:
            self.assertEqual(f.read(), self.db_bytes)

        # e tambem sem a chave na linha de comando
        self.assertNotIn("pass:", self._argv_do_openssl())

    def test_scripts_nao_usam_mais_pass_pass_em_lugar_nenhum(self):
        for caminho in (SCRIPT_BACKUP, SCRIPT_CHECK):
            with open(caminho, encoding="utf-8") as f:
                codigo = [l for l in f.read().splitlines() if not l.strip().startswith("#")]
            self.assertFalse(
                any(re.search(r"-pass\s+pass:", l) for l in codigo),
                "linha de codigo ainda passa a chave por -pass pass: em " + os.path.basename(caminho),
            )


if __name__ == "__main__":
    unittest.main()
