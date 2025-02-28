import os
from typing import Optional
from solders.keypair import Keypair
from cryptography.fernet import Fernet
import base64

class WalletManager:
    """
    Secure wallet management for Solana trading
    
    Supports multiple methods of key storage and retrieval:
    1. Environment Variable
    2. Encrypted File Storage
    3. Runtime Key Injection
    """
    
    @staticmethod
    def validate_base58_key(key: str) -> bool:
        """
        Validate if the provided string is a valid Base58 encoded private key
        
        Args:
            key (str): Private key in Base58 format
        
        Returns:
            bool: Whether the key is valid
        """
        try:
            # Attempt to create a Keypair from the key
            Keypair.from_base58_string(key)
            return True
        except Exception:
            return False
    
    @classmethod
    def from_env(cls) -> Optional[Keypair]:
        """
        Retrieve keypair from environment variable
        
        Returns:
            Optional[Keypair]: Solana keypair or None
        """
        priv_key = os.getenv("PUMP_FUN_PRIVATE_KEY", "")
        if not priv_key or priv_key == "your_base58_private_key_here":
            return None
        
        if not cls.validate_base58_key(priv_key):
            raise ValueError("Invalid Base58 private key format")
        
        return Keypair.from_base58_string(priv_key)
    
    @classmethod
    def encrypt_key(cls, key: str, encryption_key: Optional[bytes] = None) -> str:
        """
        Encrypt a private key for secure storage
        
        Args:
            key (str): Base58 private key
            encryption_key (Optional[bytes]): Optional encryption key
        
        Returns:
            str: Encrypted key
        """
        if not cls.validate_base58_key(key):
            raise ValueError("Invalid Base58 private key")
        
        # Generate or use provided encryption key
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        
        f = Fernet(encryption_key)
        encrypted_key = f.encrypt(key.encode())
        
        # Return base64 encoded encrypted key and encryption key
        return base64.b64encode(encrypted_key).decode()
    
    @classmethod
    def decrypt_key(cls, encrypted_key: str, encryption_key: bytes) -> str:
        """
        Decrypt a private key
        
        Args:
            encrypted_key (str): Base64 encoded encrypted key
            encryption_key (bytes): Encryption key
        
        Returns:
            str: Decrypted Base58 private key
        """
        f = Fernet(encryption_key)
        decrypted_key = f.decrypt(base64.b64decode(encrypted_key)).decode()
        
        if not cls.validate_base58_key(decrypted_key):
            raise ValueError("Decryption resulted in an invalid key")
        
        return decrypted_key

    @classmethod
    def from_encrypted_file(cls, file_path: str, encryption_key: bytes) -> Optional[Keypair]:
        """
        Load keypair from an encrypted file
        
        Args:
            file_path (str): Path to encrypted key file
            encryption_key (bytes): Decryption key
        
        Returns:
            Optional[Keypair]: Solana keypair or None
        """
        try:
            with open(file_path, 'r') as f:
                encrypted_key = f.read().strip()
            
            decrypted_key = cls.decrypt_key(encrypted_key, encryption_key)
            return Keypair.from_base58_string(decrypted_key)
        except Exception as e:
            print(f"Error loading encrypted key: {e}")
            return None

    @classmethod
    def save_encrypted_key(cls, key: str, file_path: str, encryption_key: Optional[bytes] = None) -> bytes:
        """
        Save an encrypted private key to a file
        
        Args:
            key (str): Base58 private key
            file_path (str): Path to save encrypted key
            encryption_key (Optional[bytes]): Optional encryption key
        
        Returns:
            bytes: Encryption key used
        """
        if not cls.validate_base58_key(key):
            raise ValueError("Invalid Base58 private key")
        
        # Generate or use provided encryption key
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        
        encrypted_key = cls.encrypt_key(key, encryption_key)
        
        with open(file_path, 'w') as f:
            f.write(encrypted_key)
        
        return encryption_key
