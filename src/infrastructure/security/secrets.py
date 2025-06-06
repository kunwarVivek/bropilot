"""
Secure credential management system.

This module provides secure storage, retrieval, and management of sensitive
credentials and secrets with support for multiple backends.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
from pathlib import Path

from core.interfaces import IConfigurationManager
from core.exceptions import ConfigurationError, SecurityError


class ISecretsManager(ABC):
    """Interface for secrets management."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key."""
        pass
    
    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """Store a secret."""
        pass
    
    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    def list_secrets(self) -> list[str]:
        """List all secret keys."""
        pass


class EnvironmentSecretsManager(ISecretsManager):
    """Secrets manager that uses environment variables."""
    
    def __init__(self, prefix: str = ""):
        """Initialize with optional prefix for environment variables."""
        self.prefix = prefix
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from environment variables."""
        env_key = f"{self.prefix}{key}" if self.prefix else key
        return os.getenv(env_key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Set an environment variable (runtime only)."""
        env_key = f"{self.prefix}{key}" if self.prefix else key
        os.environ[env_key] = value
    
    def delete_secret(self, key: str) -> bool:
        """Delete an environment variable."""
        env_key = f"{self.prefix}{key}" if self.prefix else key
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False
    
    def list_secrets(self) -> list[str]:
        """List all environment variables with the prefix."""
        if not self.prefix:
            return list(os.environ.keys())
        
        prefix_len = len(self.prefix)
        return [
            key[prefix_len:] for key in os.environ.keys() 
            if key.startswith(self.prefix)
        ]


class KeyringSecretsManager(ISecretsManager):
    """Secrets manager that uses the system keyring."""
    
    def __init__(self, service_name: str = "browser-automation-framework"):
        """Initialize with service name for keyring."""
        self.service_name = service_name
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from the system keyring."""
        try:
            return keyring.get_password(self.service_name, key)
        except Exception as e:
            raise SecurityError(f"Failed to retrieve secret from keyring: {e}")
    
    def set_secret(self, key: str, value: str) -> None:
        """Store a secret in the system keyring."""
        try:
            keyring.set_password(self.service_name, key, value)
        except Exception as e:
            raise SecurityError(f"Failed to store secret in keyring: {e}")
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from the system keyring."""
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception as e:
            raise SecurityError(f"Failed to delete secret from keyring: {e}")
    
    def list_secrets(self) -> list[str]:
        """List all secrets (not supported by keyring interface)."""
        # Keyring doesn't provide a way to list all keys
        # This would need to be implemented with a separate index
        raise NotImplementedError("Keyring backend doesn't support listing secrets")


class FileSecretsManager(ISecretsManager):
    """Secrets manager that uses encrypted files."""
    
    def __init__(self, secrets_file: str = ".secrets", master_key: Optional[str] = None):
        """Initialize with secrets file path and optional master key."""
        self.secrets_file = Path(secrets_file)
        self.master_key = master_key or os.getenv("SECRETS_MASTER_KEY")
        
        if not self.master_key:
            raise ConfigurationError("Master key required for file-based secrets")
        
        self._fernet = self._create_fernet(self.master_key)
        self._secrets_cache = None
    
    def _create_fernet(self, master_key: str) -> Fernet:
        """Create Fernet encryption instance from master key."""
        # Derive a key from the master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'browser_automation_salt',  # In production, use a random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def _load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets from file."""
        if self._secrets_cache is not None:
            return self._secrets_cache
        
        if not self.secrets_file.exists():
            self._secrets_cache = {}
            return self._secrets_cache
        
        try:
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                self._secrets_cache = {}
                return self._secrets_cache
            
            decrypted_data = self._fernet.decrypt(encrypted_data)
            self._secrets_cache = json.loads(decrypted_data.decode())
            return self._secrets_cache
            
        except Exception as e:
            raise SecurityError(f"Failed to load secrets file: {e}")
    
    def _save_secrets(self, secrets: Dict[str, str]) -> None:
        """Encrypt and save secrets to file."""
        try:
            # Ensure directory exists
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Encrypt and save
            data = json.dumps(secrets).encode()
            encrypted_data = self._fernet.encrypt(data)
            
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Update cache
            self._secrets_cache = secrets.copy()
            
        except Exception as e:
            raise SecurityError(f"Failed to save secrets file: {e}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from the encrypted file."""
        secrets = self._load_secrets()
        return secrets.get(key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Store a secret in the encrypted file."""
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from the encrypted file."""
        secrets = self._load_secrets()
        if key in secrets:
            del secrets[key]
            self._save_secrets(secrets)
            return True
        return False
    
    def list_secrets(self) -> list[str]:
        """List all secret keys."""
        secrets = self._load_secrets()
        return list(secrets.keys())


class CompositeSecretsManager(ISecretsManager):
    """Secrets manager that tries multiple backends in order."""
    
    def __init__(self, managers: list[ISecretsManager]):
        """Initialize with list of secrets managers in priority order."""
        if not managers:
            raise ConfigurationError("At least one secrets manager required")
        self.managers = managers
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from the first available backend."""
        for manager in self.managers:
            try:
                secret = manager.get_secret(key)
                if secret is not None:
                    return secret
            except Exception:
                # Try next manager
                continue
        return None
    
    def set_secret(self, key: str, value: str) -> None:
        """Store a secret in the first available backend."""
        for manager in self.managers:
            try:
                manager.set_secret(key, value)
                return
            except Exception:
                # Try next manager
                continue
        raise SecurityError("Failed to store secret in any backend")
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from all backends."""
        deleted = False
        for manager in self.managers:
            try:
                if manager.delete_secret(key):
                    deleted = True
            except Exception:
                # Continue with other managers
                continue
        return deleted
    
    def list_secrets(self) -> list[str]:
        """List all secrets from all backends."""
        all_keys = set()
        for manager in self.managers:
            try:
                keys = manager.list_secrets()
                all_keys.update(keys)
            except Exception:
                # Continue with other managers
                continue
        return list(all_keys)


class SecretsManagerFactory:
    """Factory for creating secrets managers."""
    
    @staticmethod
    def create_secrets_manager(
        backend: str = "environment",
        **kwargs
    ) -> ISecretsManager:
        """Create a secrets manager based on backend type."""
        
        if backend == "environment":
            return EnvironmentSecretsManager(kwargs.get("prefix", ""))
        
        elif backend == "keyring":
            return KeyringSecretsManager(
                kwargs.get("service_name", "browser-automation-framework")
            )
        
        elif backend == "file":
            return FileSecretsManager(
                kwargs.get("secrets_file", ".secrets"),
                kwargs.get("master_key")
            )
        
        elif backend == "composite":
            # Create composite manager with multiple backends
            backends = kwargs.get("backends", ["environment", "keyring"])
            managers = []
            
            for backend_name in backends:
                try:
                    manager = SecretsManagerFactory.create_secrets_manager(
                        backend_name, **kwargs
                    )
                    managers.append(manager)
                except Exception:
                    # Skip backends that can't be initialized
                    continue
            
            if not managers:
                raise ConfigurationError("No secrets managers could be initialized")
            
            return CompositeSecretsManager(managers)
        
        else:
            raise ConfigurationError(f"Unknown secrets backend: {backend}")


class CredentialManager:
    """High-level credential management with automatic fallbacks."""
    
    def __init__(self, secrets_manager: Optional[ISecretsManager] = None):
        """Initialize with optional secrets manager."""
        if secrets_manager is None:
            # Create default composite manager
            secrets_manager = SecretsManagerFactory.create_secrets_manager(
                "composite",
                backends=["environment", "keyring", "file"]
            )
        
        self.secrets_manager = secrets_manager
    
    def get_credential(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a credential with fallback to default."""
        try:
            value = self.secrets_manager.get_secret(key)
            return value if value is not None else default
        except Exception:
            return default
    
    def set_credential(self, key: str, value: str) -> None:
        """Set a credential."""
        self.secrets_manager.set_secret(key, value)
    
    def delete_credential(self, key: str) -> bool:
        """Delete a credential."""
        return self.secrets_manager.delete_secret(key)
    
    def get_database_credentials(self) -> Dict[str, str]:
        """Get database connection credentials."""
        return {
            "host": self.get_credential("DATABASE_HOST", "localhost"),
            "port": self.get_credential("DATABASE_PORT", "5432"),
            "name": self.get_credential("DATABASE_NAME", "browser_automation"),
            "user": self.get_credential("DATABASE_USER", "postgres"),
            "password": self.get_credential("DATABASE_PASSWORD", "")
        }
    
    def get_llm_credentials(self) -> Dict[str, str]:
        """Get LLM API credentials."""
        return {
            "gemini_api_key": self.get_credential("GEMINI_API_KEY", ""),
            "openai_api_key": self.get_credential("OPENAI_API_KEY", ""),
            "anthropic_api_key": self.get_credential("ANTHROPIC_API_KEY", "")
        }
    
    def get_task_credentials(self) -> Dict[str, str]:
        """Get task execution credentials."""
        return {
            "login_email": self.get_credential("LOGIN_EMAIL", ""),
            "login_password": self.get_credential("LOGIN_PASSWORD", "")
        }
    
    def validate_required_credentials(self, required_keys: list[str]) -> None:
        """Validate that all required credentials are available."""
        missing = []
        
        for key in required_keys:
            if not self.get_credential(key):
                missing.append(key)
        
        if missing:
            raise ConfigurationError(
                f"Missing required credentials: {', '.join(missing)}"
            )


# Global credential manager instance
credential_manager = CredentialManager()
