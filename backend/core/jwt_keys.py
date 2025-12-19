"""
JWT Key Management for RSA-based token signing and JWKS endpoint.

This module provides:
- RSA key pair generation and management
- JWKS (JSON Web Key Set) endpoint support
- RS256 token signing and verification
"""

import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Get the base directory (where the backend package is)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class JWTKeyManager:
    """
    Manages RSA key pairs for JWT signing and provides JWKS endpoint data.

    Keys are stored in PEM format and can be:
    - Generated automatically on first run
    - Loaded from environment variables
    - Loaded from files
    """

    _instance: Optional["JWTKeyManager"] = None
    _private_key: Optional[rsa.RSAPrivateKey] = None
    _public_key: Optional[rsa.RSAPublicKey] = None
    _key_id: Optional[str] = None

    def __new__(cls) -> "JWTKeyManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._private_key is None:
            self._load_or_generate_keys()

    def _load_or_generate_keys(self) -> None:
        """Load existing keys or generate new ones."""
        # Try loading from environment variables first
        private_key_pem = os.getenv("JWT_PRIVATE_KEY")
        public_key_pem = os.getenv("JWT_PUBLIC_KEY")

        if private_key_pem and public_key_pem:
            self._load_keys_from_pem(private_key_pem, public_key_pem)
            return

        # Try loading from files - use /app/keys in Docker or local keys dir
        # Check for Docker environment first (writable location)
        if os.path.exists("/app") and os.access("/app", os.W_OK):
            keys_dir = Path("/app/keys")
        else:
            keys_dir = BASE_DIR / "keys"

        private_key_path = keys_dir / "jwt_private.pem"
        public_key_path = keys_dir / "jwt_public.pem"

        if private_key_path.exists() and public_key_path.exists():
            self._load_keys_from_files(private_key_path, public_key_path)
            return

        # Generate new keys
        self._generate_keys()

        # Try to save keys to files for persistence (may fail in read-only containers)
        try:
            keys_dir.mkdir(parents=True, exist_ok=True)
            self._save_keys_to_files(private_key_path, public_key_path)
        except PermissionError:
            # In read-only containers, keys will be regenerated on restart
            # For production, use environment variables JWT_PRIVATE_KEY and JWT_PUBLIC_KEY
            import logging

            logging.warning(
                "Could not save JWT keys to disk. Keys will be regenerated on restart. "
                "For production, set JWT_PRIVATE_KEY and JWT_PUBLIC_KEY environment variables."
            )

    def _load_keys_from_pem(self, private_pem: str, public_pem: str) -> None:
        """Load keys from PEM-encoded strings."""
        # Handle newlines that might be escaped in env vars
        private_pem = private_pem.replace("\\n", "\n")
        public_pem = public_pem.replace("\\n", "\n")

        self._private_key = serialization.load_pem_private_key(
            private_pem.encode(), password=None, backend=default_backend()
        )
        self._public_key = serialization.load_pem_public_key(
            public_pem.encode(), backend=default_backend()
        )
        self._generate_key_id()

    def _load_keys_from_files(self, private_path: Path, public_path: Path) -> None:
        """Load keys from PEM files."""
        with open(private_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        with open(public_path, "rb") as f:
            self._public_key = serialization.load_pem_public_key(
                f.read(), backend=default_backend()
            )

        self._generate_key_id()

    def _generate_keys(self) -> None:
        """Generate a new RSA key pair."""
        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
        self._generate_key_id()

    def _save_keys_to_files(self, private_path: Path, public_path: Path) -> None:
        """Save keys to PEM files."""
        # Save private key
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(private_path, "wb") as f:
            f.write(private_pem)

        # Set restrictive permissions on private key
        os.chmod(private_path, 0o600)

        # Save public key
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with open(public_path, "wb") as f:
            f.write(public_pem)

    def _generate_key_id(self) -> None:
        """Generate a key ID based on the public key thumbprint."""
        # Get the public key in DER format
        public_der = self._public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        # Create SHA-256 thumbprint
        thumbprint = hashlib.sha256(public_der).digest()
        # Base64url encode (first 8 bytes for shorter ID)
        self._key_id = base64.urlsafe_b64encode(thumbprint[:8]).decode().rstrip("=")

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        """Get the private key for signing."""
        return self._private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        """Get the public key for verification."""
        return self._public_key

    @property
    def key_id(self) -> str:
        """Get the key ID (kid)."""
        return self._key_id

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get the JSON Web Key Set (JWKS) containing the public key.

        Returns:
            JWKS document with the public key in JWK format
        """
        # Get the public key numbers
        public_numbers = self._public_key.public_numbers()

        # Convert to base64url-encoded strings
        def int_to_base64url(n: int, length: int) -> str:
            """Convert integer to base64url-encoded string."""
            data = n.to_bytes(length, byteorder="big")
            return base64.urlsafe_b64encode(data).decode().rstrip("=")

        # RSA modulus (n) - 256 bytes for 2048-bit key
        n = int_to_base64url(public_numbers.n, 256)
        # RSA exponent (e) - typically 3 bytes for 65537
        e = int_to_base64url(public_numbers.e, 3)

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self._key_id,
                    "n": n,
                    "e": e,
                }
            ]
        }

    def get_openid_configuration(self, issuer: str) -> Dict[str, Any]:
        """
        Get the OpenID Connect discovery document.

        Args:
            issuer: The issuer URL (e.g., https://api.example.com)

        Returns:
            OpenID Connect configuration document
        """
        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/api/v1/auth/authorize",
            "token_endpoint": f"{issuer}/api/v1/auth/token",
            "userinfo_endpoint": f"{issuer}/api/v1/auth/userinfo",
            "jwks_uri": f"{issuer}/.well-known/jwks.json",
            "response_types_supported": ["code", "token"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": ["openid", "profile", "email"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "claims_supported": [
                "sub",
                "iss",
                "aud",
                "exp",
                "iat",
                "name",
                "email",
                "given_name",
                "family_name",
                "org_id",
                "roles",
            ],
        }


# Global instance
jwt_key_manager = JWTKeyManager()
