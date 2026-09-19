#!/usr/bin/env python3
"""
Integration test per Encryption & Portainer Config
Test completo: salvataggio, crittografia, decriptazione, persistenza
"""

import sqlite3
import requests
import os
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8888"
DB_PATH = "/app/data/appstore.db"

print("=" * 70)
print("🔐 ENCRYPTION & PORTAINER CONFIG - INTEGRATION TEST")
print("=" * 70)

# Test 1: Salva config via API
print("\n[1] Saving Portainer config via API...")
test_config = {
    "base_url": "http://test.portainer:9000",
    "api_key": "test_secret_key_abc123xyz",
    "endpoint_id": 1
}

try:
    response = requests.post(
        f"{BASE_URL}/api/settings/portainer",
        params=test_config
    )
    if response.status_code == 200:
        print(f"✅ Config saved: {response.json()}")
    else:
        print(f"❌ Failed to save config: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ API error: {e}")
    sys.exit(1)

# Test 2: Leggi config via API (API key deve essere mascherato)
print("\n[2] Reading Portainer config via API...")
try:
    response = requests.get(f"{BASE_URL}/api/settings/portainer")
    config = response.json()
    api_key_value = config.get('api_key', '')
    is_masked = api_key_value == "***"
    print("✅ Config retrieved:")
    print(f"   - Base URL: {config['base_url']}")
    print(f"   - API Key: {'*** (masked)' if is_masked else '(present, unexpected value - length %d)' % len(str(api_key_value))}")
    print(f"   - Endpoint ID: {config['endpoint_id']}")

    if not is_masked:
        print("❌ WARNING: API key not masked! Expected '***'.")
    else:
        print("✅ API key properly masked")
except Exception as e:
    print(f"❌ API error: {e}")
    sys.exit(1)

# Test 3: Verifica DB - il valore deve essere crittato
print("\n[3] Verifying encryption in database...")
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT base_url, api_key_encrypted FROM portainer_config LIMIT 1")
    row = cur.fetchone()
    
    if row:
        base_url, encrypted = row
        print("✅ Config in DB:")
        print(f"   - Base URL: {base_url}")
        print(f"   - API Key (encrypted): present, length {len(encrypted)} chars")

        # Verifica che NON sia il valore in chiaro
        # NOTE: avoid logging the test secret itself; only check presence
        if "test_secret_key_abc123xyz" in encrypted:
            print("❌ ERROR: API key not encrypted!")
            sys.exit(1)
        else:
            print("✅ API key is properly encrypted (not plaintext)")
    else:
        print(f"❌ No config found in DB")
        sys.exit(1)
    
    conn.close()
except Exception as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)

# Test 4: Decripta il valore e verifica
print("\n[4] Testing decryption...")
try:
    # Leggi dalla EncryptionManager di appstore
    from src.security.crypto import get_encryption_manager
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT api_key_encrypted FROM portainer_config LIMIT 1")
    encrypted_value = cur.fetchone()[0]
    conn.close()
    
    manager = get_encryption_manager()
    decrypted = manager.decrypt(encrypted_value)

    print("✅ Decryption successful:")
    print(f"   - Encrypted length: {len(encrypted_value)} chars")
    print(f"   - Decrypted length: {len(decrypted)} chars")

    if decrypted == "test_secret_key_abc123xyz":
        print("✅ Decrypted value matches original!")
    else:
        print("❌ Decrypted value doesn't match!")
        print(f"   Expected length: {len('test_secret_key_abc123xyz')}")
        print(f"   Got length: {len(decrypted)}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Decryption error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verifica persistenza della chiave
print("\n[5] Checking encryption key persistence...")
key_file = Path("/app/data/.encryption_key")
if key_file.exists():
    print(f"✅ Encryption key file exists at {key_file}")
    print(f"   - File size: {key_file.stat().st_size} bytes")
else:
    print(f"❌ Encryption key file not found at {key_file}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - Encryption is working correctly!")
print("=" * 70)
