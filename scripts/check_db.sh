#!/bin/bash
DB="/root/atos/backend/mane.db"
BKP_DIR="/root/atos/backups"
ADMIN="diogo@realpublicidade.com.br"
if ! command -v sqlite3 >/dev/null 2>&1; then
    logger "atos-check: sqlite3 ausente, abortado"; exit 0
fi
if [ ! -f "$DB" ]; then
    logger "atos-check: banco ausente, abortado"; exit 0
fi
RES=$(sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null | tr -d '[:space:]')
if [ "$RES" = "ok" ]; then exit 0; fi
if [ -z "$RES" ]; then
    logger "atos-check: check vazio, sem acao"; exit 0
fi
DATA=$(date +%Y%m%d-%H%M%S)
cp "$DB" "/root/atos/CORROMPIDO-$DATA.db" 2>/dev/null
CRYPT_KEY=$(grep '^BACKUP_CRYPT_KEY=' /root/atos/.env | cut -d'=' -f2)
# procura o backup cifrado mais recente
ULTIMO_ENC=$(ls -t "$BKP_DIR"/mane-*.db.gz.enc 2>/dev/null | head -1)
ULTIMO_GZ=$(ls -t "$BKP_DIR"/mane-*.db.gz 2>/dev/null | head -1)
STATUS="SEM BACKUP - intervencao manual"
if [ -n "$ULTIMO_ENC" ] && [ -n "$CRYPT_KEY" ]; then
    openssl enc -d -aes-256-cbc -pbkdf2 -in "$ULTIMO_ENC" -pass pass:"$CRYPT_KEY" 2>/dev/null | gunzip -c > "$DB" 2>/dev/null
    if [ -s "$DB" ]; then
        systemctl restart atos-backend
        STATUS="RESTAURADO de $ULTIMO_ENC (cifrado)"
    fi
elif [ -n "$ULTIMO_GZ" ]; then
    gunzip -c "$ULTIMO_GZ" > "$DB"
    systemctl restart atos-backend
    STATUS="RESTAURADO de $ULTIMO_GZ"
fi
cd /root/atos/backend
/root/atos/venv/bin/python -c "
import sys; sys.path.insert(0,'/root/atos/backend')
from main import enviar_email
enviar_email('$ADMIN', '[ATOS] ALERTA: corrupcao no banco', 'Banco corrompido em $DATA. Check: $RES. Acao: $STATUS. Copia preservada em /root/atos/CORROMPIDO-$DATA.db')
" 2>&1
logger "atos-check: CORRUPCAO $DATA - $STATUS"
echo "$DATA: CORRUPCAO - $STATUS"
