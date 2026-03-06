#!/usr/bin/env bash
# =============================================================
# Run this every time Vault restarts.
# In production replace with AWS KMS / GCP KMS auto-unseal.
# =============================================================
set -euo pipefail

KEYS_FILE="./vault-keys.json"
VAULT="docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault-server vault"

SEALED=$($VAULT status -format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['sealed'])" || echo "true")

if [ "$SEALED" = "False" ] || [ "$SEALED" = "false" ]; then
  echo "Vault is already unsealed."
  exit 0
fi

echo "Unsealing Vault..."
KEY1=$(python3 -c "import json; print(json.load(open('$KEYS_FILE'))['unseal_keys_b64'][0])")
KEY2=$(python3 -c "import json; print(json.load(open('$KEYS_FILE'))['unseal_keys_b64'][1])")
$VAULT operator unseal $KEY1 > /dev/null
$VAULT operator unseal $KEY2 > /dev/null
echo "Vault unsealed."
