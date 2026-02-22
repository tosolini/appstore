"""Encryption for API keys and sensitive configurations"""

import os
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption/decryption of sensitive values"""
    
    def __init__(self, master_key: str = None):
        """
        Initialize the encryption manager.
        
        Args:
            master_key: Master key for decoding. If None, uses env var ENCRYPTION_KEY, .encryption_key file or generates one.
        """
        if master_key is None:
            # 1. Read from env var
            master_key = os.getenv('ENCRYPTION_KEY')
            
            # 2. If not in env, read from persistent file
            if not master_key:
                key_file = Path('/app/data/.encryption_key')
                if key_file.exists():
                    with open(key_file, 'r') as f:
                        master_key = f.read().strip()
                    logger.info("Encryption key loaded from file")
            
            # 3. If still not there, generate and save
            if not master_key:
                logger.warning("ENCRYPTION_KEY not found. Generating and persisting new key...")
                master_key = Fernet.generate_key().decode()
                
                # Salva in file per persistence
                try:
                    key_file = Path('/app/data/.encryption_key')
                    key_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(key_file, 'w') as f:
                        f.write(master_key)
                    # Restrizioni di permessi (solo lettura per owner)
                    os.chmod(key_file, 0o600)
                    logger.info("Encryption key generated and saved to /app/data/.encryption_key")
                except Exception as e:
                    logger.error(f"Could not save encryption key to file: {e}")
                
                os.environ['ENCRYPTION_KEY'] = master_key
        
        # Configura il cipher
        try:
            self.key = master_key.encode() if isinstance(master_key, str) else master_key
            # Valida che sia una chiave Fernet corretta
            Fernet(self.key)
            self.cipher = Fernet(self.key)
            logger.info("Encryption manager initialized successfully")
        except Exception as e:
            logger.warning(f"Invalid encryption key format: {e}. Generating new key...")
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)
            os.environ['ENCRYPTION_KEY'] = self.key.decode()
    
    def encrypt(self, plaintext: str) -> str:
        """
        Cripta un valore in chiaro.
        
        Args:
            plaintext: Valore da crittare
            
        Returns:
            Stringa con dati crittati (base64 encoded)
        """
        if not plaintext:
            return None
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decripta un valore crittato.
        
        Args:
            encrypted_text: Stringa crittata (base64 encoded)
            
        Returns:
            Valore in chiaro
        """
        if not encrypted_text:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            plaintext = self.cipher.decrypt(encrypted_bytes).decode()
            return plaintext
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise


# Singleton instance
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Ottieni l'instance singleton del EncryptionManager"""
    global _encryption_manager
    
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    
    return _encryption_manager


def encrypt_value(value: str) -> str:
    """Funzione di convenience per crittare un valore"""
    manager = get_encryption_manager()
    return manager.encrypt(value)


def decrypt_value(encrypted: str) -> str:
    """Funzione di convenience per decrittare un valore"""
    manager = get_encryption_manager()
    return manager.decrypt(encrypted)
