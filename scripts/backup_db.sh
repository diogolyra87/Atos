#!/bin/bash
# Backup do banco ATOS com rotacao + criptografia AES-256
ORIGEM="/root/atos/backend/mane.db"
DESTINO="/root/atos/backups"
mkdir -p "$DESTINO"
DATA=$(date +%Y%m%d-%H%M)
ARQ="$DESTINO/mane-$DATA.db"

# le a chave de criptografia do .env
CRYPT_KEY=$(grep '^BACKUP_CRYPT_KEY=' /root/atos/.env | cut -d'=' -f2)

# backup consistente do sqlite (mesmo com banco em uso)
sqlite3 "$ORIGEM" ".backup '$ARQ'" 2>/dev/null || cp "$ORIGEM" "$ARQ"

# compacta
gzip -f "$ARQ"

# cifra o .gz com AES-256 -> gera .gz.enc e remove o .gz aberto
if [ -n "$CRYPT_KEY" ]; then
  # -pass stdin (e nao "-pass pass:$CRYPT_KEY"): argumento de linha de comando aparece em
  # `ps aux` pra qualquer usuario local durante a cifragem. A chave entra pelo stdin via printf
  # (builtin do bash - nao e' um processo externo, entao nao existe argv com a chave em lugar
  # nenhum). Mesmo formato de saida - backups antigos e a restauracao manual com
  # "-pass pass:CHAVE" continuam compativeis.
  printf '%s\n' "$CRYPT_KEY" | openssl enc -aes-256-cbc -pbkdf2 -salt -in "$ARQ.gz" -out "$ARQ.gz.enc" -pass stdin && rm -f "$ARQ.gz"
  FINAL="$ARQ.gz.enc"
else
  echo "$(date): AVISO - sem chave de cripto, backup nao cifrado" >> /root/atos/backups/rclone.log
  FINAL="$ARQ.gz"
fi

# remove backups locais com mais de 7 dias
find "$DESTINO" -name "mane-*.db.gz*" -mtime +7 -delete

# envia a copia cifrada para o Google Drive
rclone copy "$FINAL" gdrive:ATOS_Backups/ 2>>/root/atos/backups/rclone.log && echo "$(date): enviado ao Drive (cifrado)" >> /root/atos/backups/rclone.log

# remove backups antigos do Drive (mantem 30 dias)
rclone delete gdrive:ATOS_Backups/ --min-age 30d 2>>/root/atos/backups/rclone.log

echo "$(date): backup ok -> $FINAL"
