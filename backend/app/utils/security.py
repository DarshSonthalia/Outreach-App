"""
Utility functions for encryption and security.
OAuth tokens are encrypted at rest using Fernet symmetric encryption.
"""
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Optional, Tuple, Dict, Any
import logging
import json

from app.config import settings
import hashlib

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token encryption - initialized lazily
_fernet: Optional[Fernet] = None

logger = logging.getLogger(__name__)


def get_fernet() -> Fernet:
    """Get Fernet instance for token encryption."""
    global _fernet
    if _fernet is None:
        # Fix B1: Use OAUTH_TOKEN_ENC_KEY (config maps from env)
        key = settings.oauth_encryption_key
        if key == "CHANGE-THIS-IN-PRODUCTION" or not key:
            logger.warning("Using default encryption key - DO NOT USE IN PRODUCTION")
            key = Fernet.generate_key().decode()
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Invalid encryption key format: {e}")
            raise ValueError("OAUTH_TOKEN_ENC_KEY must be a valid Fernet key")
    return _fernet


# ===========================================
# PASSWORD HASHING
# ===========================================

def hash_password(password: str) -> str:
    """
    Hash a password for storage.
    
    Fix: BCrypt has a hard limit of 72 bytes.
    We hash the password with SHA-256 first (giving 64 hex chars)
    to allow passwords of any length.
    """
    # Pre-hash with SHA-256. 
    # Use first 32 chars (128-bit) to strictly satisfy bcrypt limit
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()[:32]
    return pwd_context.hash(password_hash)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Pre-hash for consistency
    password_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()[:32]
    return pwd_context.verify(password_hash, hashed_password)



# ===========================================
# JWT TOKENS
# ===========================================

def create_access_token(user_id: int) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[int]:
    """
    Decode and validate a JWT access token.
    Returns user_id if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None


# ===========================================
# OAUTH TOKEN ENCRYPTION
# ===========================================

def encrypt_token(token: str) -> bytes:
    """
    Encrypt an OAuth token for storage.
    NEVER log the raw token.
    """
    if not token:
        return b""
    fernet = get_fernet()
    return fernet.encrypt(token.encode())


def decrypt_token(encrypted_token: bytes) -> str:
    """
    Decrypt an OAuth token for use.
    NEVER log the decrypted token.
    """
    if not encrypted_token:
        return ""
    fernet = get_fernet()
    try:
        return fernet.decrypt(encrypted_token).decode()
    except InvalidToken:
        logger.error("Failed to decrypt token - key may have changed")
        return ""


def encrypt_oauth_tokens(access_token: str, refresh_token: str) -> Tuple[bytes, bytes]:
    """Encrypt both OAuth tokens."""
    return encrypt_token(access_token), encrypt_token(refresh_token)


def decrypt_oauth_tokens(
    access_token_encrypted: bytes, 
    refresh_token_encrypted: bytes
) -> Tuple[str, str]:
    """Decrypt both OAuth tokens."""
    return decrypt_token(access_token_encrypted), decrypt_token(refresh_token_encrypted)


# ===========================================
# Fix B1: JSON ENCRYPTION FOR TOKEN BLOBS
# ===========================================

def encrypt_json(data: Dict[str, Any]) -> bytes:
    """
    Encrypt a JSON-serializable dict for storage.
    Useful for storing entire token blobs.
    NEVER log the raw data.
    """
    fernet = get_fernet()
    json_str = json.dumps(data)
    return fernet.encrypt(json_str.encode())


def decrypt_json(encrypted_data: bytes) -> Optional[Dict[str, Any]]:
    """
    Decrypt encrypted JSON data.
    Returns None if decryption fails.
    NEVER log the decrypted data.
    """
    if not encrypted_data:
        return None
    fernet = get_fernet()
    try:
        json_str = fernet.decrypt(encrypted_data).decode()
        return json.loads(json_str)
    except (InvalidToken, json.JSONDecodeError) as e:
        logger.error(f"Failed to decrypt JSON: {type(e).__name__}")
        return None

