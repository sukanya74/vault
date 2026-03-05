vault {
  address = "http://vault:8200"
  retry {
    num_retries = 10
  }
}

auto_auth {
  method "approle" {
    config = {
      role_id_file_path                   = "/vault/agent/role_id"
      secret_id_file_path                 = "/vault/agent/secret_id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/vault/secrets/sink_token"
      mode = 0644
    }
  }
}

template {
  source      = "/vault/agent/template.ctmpl"
  destination = "/vault/secrets/app.env"
  perms       = 0644
  command     = "sh -c 'echo reloaded > /vault/secrets/.reload_signal || true'"
}

template {
  contents    = "ready"
  destination = "/vault/secrets/.ready"
  perms       = 0644
}
