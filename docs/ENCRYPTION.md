# 🔐 Encryption & Security

## Overview

The system implements **end-to-end encryption** for sensitive configurations (Portainer API keys). It uses the `cryptography` library with **Fernet** (AES-128-CBC) to guarantee:

- ✅ **Confidentiality**: API keys are encrypted before being saved to the database
- ✅ **Integrity**: Encrypted data cannot be modified without invalidating the signature
- ✅ **Persistence**: The encryption key is saved to disk and reloaded on restart

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│ API Settings Endpoint (/api/settings/)  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ EncryptionManager (src/security/crypto) │
│  - encrypt(plaintext) → encrypted_text  │
│  - decrypt(encrypted_text) → plaintext  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ SQLAlchemy PortainerConfig Model        │
│  - api_key @property (smart get/set)    │
│  - api_key_encrypted (DB column)        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ SQLite Database & .encryption_key File  │
│  - appstore.db (data encrypted)         │
│  - .encryption_key (key persisted)      │
└─────────────────────────────────────────┘
```

### Save Flow

```
User → POST /api/settings/portainer
       ├─ base_url: "http://portainer:9000"
       ├─ api_key: "secret_key_123"
       └─ endpoint_id: 1
         │
         ▼
API Handler
├─ URL Validation
├─ EncryptionManager.encrypt("secret_key_123")
│  └─ Returns: "Z0FBQUFBQnBtZHhtU3pM..." (base64)
│
├─ PortainerConfig.api_key = "secret_key_123"
│  └─ @setter automatically calls encrypt()
│
└─ DB.commit()
   └─ Saves to portainer_config.api_key_encrypted
```

### Read Flow

```
User → GET /api/settings/portainer
       │
       ▼
API Handler
├─ Query DB → PortainerConfig
│  └─ api_key_encrypted: "Z0FBQUFBQnBtZHhtU3pM..."
│
├─ PortainerConfig.api_key @getter
│  ├─ EncryptionManager.decrypt("Z0FBQUFBQnBtZHhtU3pM...")
│  └─ Returns: "secret_key_123"
│
└─ Response (api_key masked as "***")
```

## Encryption Key Management

### Initialization

The key is managed with this priority:

1. **Environment variable** `ENCRYPTION_KEY`
   ```bash
   docker run -e ENCRYPTION_KEY="<fernet_key>" container-appstore:latest
   ```

2. **Persistent file** `/app/data/.encryption_key`
   - Auto-generated on first startup if not present
   - Saved with restricted permissions (`600`)
   - Reloaded on container restart

3. **Automatic generation**
   - If neither of the above, generates a new Fernet key
   - Saves it to the `.encryption_key` file

### Lifecycle

```
Container Start
    │
    ▼
EncryptionManager.__init__()
    │
    ├─ Read env var ENCRYPTION_KEY?
    │  └─ Yes → Use that
    │
    ├─ Otherwise read file ~/.encryption_key?
    │  └─ Yes → Use that
    │
    ├─ Otherwise generate new key
    │  └─ Save to /app/data/.encryption_key
    │
    └─ Initialize Fernet cipher
       └─ Ready for encrypt/decrypt
```

**Important**: With a Docker volume at `/app/data`, the key persists between restarts:

```bash
# Save key in container
docker run -v my_data:/app/data container-appstore:latest

# Restart: Reads the same key from /app/data/.encryption_key
docker restart my_container
```

## Implementation in Models

### PortainerConfig Model

```python
class PortainerConfig(Base):
    __tablename__ = "portainer_config"
    
    # Storage column (encrypted)
    api_key_encrypted = Column(Text, nullable=False)
    
    # Property: handles encryption/decryption automatically
    @property
    def api_key(self) -> str:
        """Decrypts and returns the API key"""
        if not self.api_key_encrypted:
            return None
        cipher = get_encryption_manager()
        return cipher.decrypt(self.api_key_encrypted)
    
    @api_key.setter
    def api_key(self, plaintext: str):
        """Encrypts and saves the API key"""
        if plaintext:
            cipher = get_encryption_manager()
            self.api_key_encrypted = cipher.encrypt(plaintext)
        else:
            self.api_key_encrypted = None
```

**Usage**:
```python
# Saving
config = PortainerConfig()
config.api_key = "secret"  # Uses @setter → encrypts automatically
db.add(config)
db.commit()

# Reading
config = db.query(PortainerConfig).first()
print(config.api_key)  # Uses @getter → decrypts automatically
```

## Security

### ✅ Strengths

1. **Fernet (AES-128-CBC)**: Industry standard
2. **Signature verification**: Detects tampering
3. **Key file with 600 permissions**: Only owner can read
4. **API key masked in response**: Doesn't expose sensitive data
5. **Key persistence**: Docker volume ensures consistency

### ⚠️ Production Considerations

1. **Key Management**: In production, use:
   - HashiCorp Vault
   - AWS KMS
   - Azure Key Vault
   - TLS certificates for transport

2. **Key Rotation**: Implement periodic key rotation mechanism

3. **Audit Logging**: Track access to encrypted data

4. **Volume Permissions**: Ensure `/app/data` is readable only by the container

5. **Backups**: Protect backups of encrypted data

## Testing

### Encryption Test

```bash
# Verify that the value in DB is encrypted
docker exec container-appstore-test sqlite3 /app/data/appstore.db \
  "SELECT api_key_encrypted FROM portainer_config LIMIT 1"

# Output: Z0FBQUFBQnBtZHhtU3pMdFZBVVdoWmFhSGxaa1lE...
# (Not the plaintext value)
```

### Persistence Test

```bash
# 1. Save config
curl -X POST "http://localhost:8000/api/settings/portainer?base_url=...&api_key=secret&endpoint_id=1"

# 2. Restart container
docker restart container-appstore

# 3. Verify it's still available
curl http://localhost:8000/api/settings/portainer
# Output: {"api_key": "***", ...}  ✅ Config still present
```

### Decryption Test

```bash
# Verify that decryption works correctly
docker exec container-appstore-test python3 << 'EOF'
from src.security.crypto import get_encryption_manager
import sqlite3

conn = sqlite3.connect('/app/data/appstore.db')
cur = conn.cursor()
cur.execute('SELECT api_key_encrypted FROM portainer_config')
encrypted = cur.fetchone()[0]

manager = get_encryption_manager()
decrypted = manager.decrypt(encrypted)
print(f"Decrypted: {decrypted}")  # Shows the plaintext value

conn.close()
EOF
```

## Configuration

### For Development

```bash
# Use auto-generated key (saved in volume)
docker run -v my_data:/app/data container-appstore:latest
```

### For Production

```bash
# Generate a Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: jrPH8v0cJH1j4ZK...

# Pass as env var
docker run -e ENCRYPTION_KEY="jrPH8v0cJH1j4ZK..." \
           -v /secure/path:/app/data \
           container-appstore:latest

# Or save in .env file
echo "ENCRYPTION_KEY=jrPH8v0cJH1j4ZK..." > .env
docker run --env-file .env container-appstore:latest
```

## API Endpoints

### GET `/api/settings/portainer`

Returns config with API key **masked**.

```json
{
  "mode": "mock",
  "base_url": "http://portainer:9000",
  "endpoint_id": 1,
  "is_configured": true,
  "last_validated": "2026-02-21T17:30:00",
  "api_key": "***"
}
```

### POST `/api/settings/portainer`

Saves config and encrypts the API key in the database.

**Parameters**:
- `base_url` (string, required)
- `api_key` (string, required, encrypted automatically)
- `endpoint_id` (int, optional, default=1)

**Response**:
```json
{
  "status": "success",
  "message": "Configuration saved and validated",
  "base_url": "http://portainer:9000",
  "is_configured": true
}
```

## See Also

- [src/security/crypto.py](../src/security/crypto.py) - Implementation
- [src/db/models.py](../src/db/models.py) - PortainerConfig model
- [src/main.py](../src/main.py) - API endpoints

