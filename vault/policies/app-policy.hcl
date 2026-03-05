# Minimal policy — FastAPI app role can only read DB secrets
path "secret/data/app/database" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

