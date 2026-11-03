"""
SYNORA Cryptographic Security & Session Authentication Module
Provides HMAC-SHA256 session token generation and verification to guarantee that
user and session identities come from authenticated server-side context and cannot
be freely spoofed or forged by untrusted clients.
"""

import hmac
import hashlib
import time
import json
import base64
from typing import Optional, Tuple, Dict, Any
from backend.config import settings

# Server-side signing secret
_SERVER_SECRET = getattr(settings, "SECRET_KEY", None) or "synora-hardened-session-signing-secret-key-2026"

def generate_session_token(
    session_id: str,
    user_id: str = "default_user",
    ttl_seconds: int = 86400,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 session token.
    Token format: base64(payload).hex_hmac_signature
    """
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "issued_at": time.time(),
        "expires_at": time.time() + ttl_seconds,
        "meta": metadata or {}
    }
    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8')
    
    signature = hmac.new(
        _SERVER_SECRET.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"

def verify_session_token(token: str) -> Optional[Tuple[str, str]]:
    """
    Cryptographically verifies the authenticity and freshness of a session token.
    Returns (session_id, user_id) if valid and not expired, or None if invalid/forged/expired.
    """
    if not token or "." not in token:
        return None
    
    parts = token.split(".")
    if len(parts) != 2:
        return None
    
    payload_b64, signature = parts
    
    expected_sig = hmac.new(
        _SERVER_SECRET.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(signature, expected_sig):
        return None
    
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
        payload = json.loads(payload_json)
        
        expires_at = payload.get("expires_at", 0)
        if time.time() > expires_at:
            return None
            
        session_id = payload.get("session_id")
        user_id = payload.get("user_id", "default_user")
        
        if not session_id:
            return None
            
        return session_id, user_id
    except Exception:
        return None

