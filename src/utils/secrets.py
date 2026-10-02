"""
Secret Management Engine for KBM Tender Scout.
Strictly adheres to Section 3: Read credentials only at runtime, never log or persist secrets.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Automatically load local .env if present
load_dotenv()

class SecretManager:
    """Manages secure runtime retrieval of credentials without risk of leakage."""

    @staticmethod
    def get_secret(secret_name: str) -> Optional[str]:
        """
        Retrieves a secret by its environment/vault variable name.
        Never logs or prints the retrieved value.
        """
        if not secret_name:
            return None
        val = os.getenv(secret_name)
        if val is not None:
            val = val.strip()
            return val if val else None
        return None

    @staticmethod
    def mask_string(val: Optional[str]) -> str:
        """Returns a masked representation safe for logs (e.g. '***' or 'us***12')."""
        if not val:
            return "[EMPTY]"
        if len(val) <= 4:
            return "****"
        return f"{val[:2]}****{val[-2:]}"

    @classmethod
    def has_secret(cls, secret_name: str) -> bool:
        """Checks if a secret is configured without exposing its contents."""
        val = cls.get_secret(secret_name)
        return val is not None and len(val) > 0
