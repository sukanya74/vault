ui        = true
log_level  = "info"
log_format = "json"
disable_mlock = true

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-node-1"
}

api_addr     = "http://vault:8200"
cluster_addr = "http://vault:8201"

