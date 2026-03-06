#!/usr/bin/env bash
# =============================================================
# PHASE 1 — Run ONCE by the operator to bootstrap Vault.
# This script is never run by any container or agent.
#
# What it does:
#   1. Initializes Vault (generates unseal keys + root token)
#   2. Unseals Vault
#   3. Enables KV-v2 secrets engine
#   4. Writes DB secrets
#   5. Creates policy
#   6. Enables AppRole auth + creates role
#   7. Saves role_id and secret_id to ./agent/
#      (so Vault Agent can use them in Phase 2)
# =============================================================
set -euo pipefail

VAULT="docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault-server vault"
KEYS_FILE="./vault-keys.json"
AGENT_DIR="./agent"

# --- Check Vault is reachable ---
echo "[1/7] Waiting for Vault server to be reachable..."
until docker exec vault-server wget -qO- http://127.0.0.1:8200/v1/sys/health > /dev/null 2>&1; do
  sleep 2; printf ".";
done
echo " ready."

# --- Initialize ---
echo "[2/7] Initializing Vault..."
$VAULT operator init -key-shares=3 -key-threshold=2 -format=json > $KEYS_FILE
echo "      Saved to $KEYS_FILE — KEEP THIS SECURE, never commit to git."

# --- Unseal ---
echo "[3/7] Unsealing Vault..."
KEY1=$(python3 -c "import json; print(json.load(open('$KEYS_FILE'))['unseal_keys_b64'][0])")
KEY2=$(python3 -c "import json; print(json.load(open('$KEYS_FILE'))['unseal_keys_b64'][1])")
$VAULT operator unseal $KEY1 > /dev/null
$VAULT operator unseal $KEY2 > /dev/null
echo "      Unsealed."

# --- Login ---
ROOT_TOKEN=$(python3 -c "import json; print(json.load(open('$KEYS_FILE'))['root_token'])")
VAULT_AUTH="docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=$ROOT_TOKEN vault-server vault"

# --- Enable KV-v2 ---
echo "[4/7] Enabling KV-v2 secrets engine..."
$VAULT_AUTH secrets enable -path=secret kv-v2
echo "      Done."

# --- Write secrets ---
echo "[5/7] Writing database secrets..."
DB_USER="${DB_USERNAME:-appuser}"
DB_PASS="${DB_PASSWORD:-StrongPass123}"
$VAULT_AUTH kv put secret/app/database \
  username="$DB_USER" \
  password="$DB_PASS" \
  connection_string="postgresql://$DB_USER:$DB_PASS@postgres:5432/appdb"
echo "      Written to secret/app/database."

# --- Write policy ---
echo "[6/7] Writing app policy..."
$VAULT_AUTH policy write app-policy /vault/policies/app-policy.hcl
echo "      Done."

# --- Enable AppRole + create role ---
echo "[7/7] Setting up AppRole and saving credentials for Vault Agent..."
$VAULT_AUTH auth enable approle
$VAULT_AUTH write auth/approle/role/fastapi-role \
  token_policies="app-policy" \
  token_ttl="1h" \
  token_max_ttl="4h"

# Save role_id and secret_id for Vault Agent (Phase 2)
$VAULT_AUTH read -field=role_id auth/approle/role/fastapi-role/role-id > $AGENT_DIR/role_id
$VAULT_AUTH write -field=secret_id -f auth/approle/role/fastapi-role/secret-id > $AGENT_DIR/secret_id
echo "      role_id  -> $AGENT_DIR/role_id"
echo "      secret_id -> $AGENT_DIR/secret_id"

echo ""
echo "============================================================"
echo " Bootstrap complete. Vault is ready."
echo " From now on just run:"
echo "   docker compose -f vault-compose.yml up -d"
echo "   bash unseal.sh"
echo "============================================================"
