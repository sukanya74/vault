# HashiCorp Vault Initialization Example

This repository demonstrates the **structure of the JSON output generated when initializing a HashiCorp Vault server**.

When running the Vault initialization command:

```bash
vault operator init -format=json
```

Vault returns a JSON document containing **unseal keys and a root token** required to operate the Vault instance.

⚠️ **Important:**
The example shown in this repository contains **dummy placeholder values only**.
Real Vault keys and tokens must **never be stored in source control systems like GitHub**.

---

# Example Vault Initialization Output

```json
{
  "unseal_keys_b64": [
    "BASE64_KEY_EXAMPLE_1",
    "BASE64_KEY_EXAMPLE_2",
    "BASE64_KEY_EXAMPLE_3"
  ],
  "unseal_keys_hex": [
    "HEX_KEY_EXAMPLE_1",
    "HEX_KEY_EXAMPLE_2",
    "HEX_KEY_EXAMPLE_3"
  ],
  "unseal_shares": 3,
  "unseal_threshold": 2,
  "recovery_keys_b64": [],
  "recovery_keys_hex": [],
  "recovery_keys_shares": 0,
  "recovery_keys_threshold": 0,
  "root_token": "ROOT_TOKEN_EXAMPLE"
}
```

---

# Field Explanation

### unseal_keys_b64

Base64-encoded unseal keys generated during initialization.

### unseal_keys_hex

Hexadecimal versions of the same unseal keys.

### unseal_shares

Total number of unseal key shares generated.

### unseal_threshold

Minimum number of key shares required to unseal the Vault.

Example:

```
shares = 3
threshold = 2
```

Vault requires **any 2 of the 3 keys** to unseal.

### recovery_keys

Used only in **Auto-Unseal configurations**.

### root_token

Initial administrative token used to authenticate to Vault after initialization.

---

# Typical Vault Initialization Workflow

1️⃣ Initialize Vault

```bash
vault operator init
```

2️⃣ Save the keys securely (password manager / secret storage)

3️⃣ Unseal Vault

```bash
vault operator unseal
```

Repeat until threshold is reached.

4️⃣ Login using root token

```bash
vault login
```

---

# Security Best Practices

Never store these in Git repositories:

* `vault-keys.json`
* `.env`
* private keys
* tokens

Always store secrets in secure locations such as:

* HashiCorp Vault itself
* encrypted password managers
* secure key management systems

---

# Example .gitignore

To prevent accidental commits:

```
vault-keys.json
*.env
secrets.yaml
```

---

# Disclaimer

This repository contains **example data only** for demonstration purposes.
No real credentials are included.

