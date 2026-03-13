"""
Core license validation for Lingua.
Uses HMAC-SHA256 signatures for serverless, offline validation.
"""

import hmac
import hashlib
import uuid
import platform
import os
import time
from datetime import datetime, timedelta
from lingua.core.config import get_config

# IMPORTANT: This is the Public/Shared secret used to verify signatures.
# In a true Masterclass setup, you'd use RSA/Ed25519, but for zero-dependency HMAC is robust.
# Keep this exact string private!
SECRET_SALT = b"Lingua_Sanctuary_Pro_Edition_2026_VRusu"

class LicenseManager:
    """Manages application activation and verification."""

    @staticmethod
    def get_machine_id():
        """Generate a unique ID for this hardware to prevent license sharing."""
        try:
            # Use mac address as a base for HWID
            node = uuid.getnode()
            return hashlib.sha256(f"{node}-{platform.node()}-{os.getlogin()}".encode()).hexdigest()[:12].upper()
        except Exception:
            return "UNKNOWN_HWID"

    @staticmethod
    def verify_license(email: str, license_key: str) -> tuple[bool, int]:
        """
        Verify if the license_key is a valid HMAC signature.
        Supports:
        - Standard (1 year): HMAC(SECRET_SALT, email + HWID)
        - Promo (3 months): HMAC(SECRET_SALT, "PROMO:" + email + HWID)
        Returns: (is_valid, duration_days)
        """
        if not email or not license_key:
            return False, 0
            
        hwid = LicenseManager.get_machine_id()
        email_clean = email.strip().lower()
        key_clean = license_key.strip().upper()
        
        # 1. Try Standard (365 days)
        payload_std = f"{email_clean}:{hwid}".encode()
        expected_std = hmac.new(SECRET_SALT, payload_std, hashlib.sha256).hexdigest().upper()
        if hmac.compare_digest(expected_std, key_clean):
            return True, 365
            
        # 2. Try Promo (90 days)
        payload_promo = f"PROMO:{email_clean}:{hwid}".encode()
        expected_promo = hmac.new(SECRET_SALT, payload_promo, hashlib.sha256).hexdigest().upper()
        if hmac.compare_digest(expected_promo, key_clean):
            return True, 90
            
        return False, 0

    @staticmethod
    def is_activated() -> bool:
        """Check if a valid, non-expired license is already stored."""
        config = get_config()
        email = config.get("license_email")
        key = config.get("license_key")
        activation_date = config.get("license_date")
        
        if not email or not key:
            return False
            
        is_valid, duration = LicenseManager.verify_license(email, key)
        if not is_valid:
            return False
            
        # Check for expiration using stored OR detected duration
        stored_duration = config.get("license_duration", duration)
        if activation_date:
            start_date = datetime.fromtimestamp(activation_date)
            expiry_date = start_date + timedelta(days=stored_duration)
            if datetime.now() >= expiry_date:
                return False
                
        return True

    @staticmethod
    def is_pro() -> bool:
        """Pro functionality is enabled for activated users."""
        return LicenseManager.is_activated()

    @staticmethod
    def get_trial_info():
        """
        Check the trial status and return (is_expired, remaining_days).
        Trial lasts 14 days from the first run.
        """
        config = get_config()
        first_run = config.get("trial_first_run")
        
        if not first_run:
            # First time ever running the app
            first_run = int(time.time())
            config.set("trial_first_run", first_run)
            config.commit()
            
        start_date = datetime.fromtimestamp(first_run)
        expiry_date = start_date + timedelta(days=14)
        now = datetime.now()
        
        remaining = (expiry_date - now).days
        is_expired = now >= expiry_date
        
        return is_expired, max(0, remaining)

    @staticmethod
    def save_license(email: str, key: str, duration: int = 365):
        """Persist the license details, activation date and duration to the config."""
        config = get_config()
        config.set("license_email", email.strip().lower())
        config.set("license_key", key.strip().upper())
        config.set("license_date", int(time.time()))
        config.set("license_duration", duration)
        config.commit()

    @staticmethod
    def get_license_info():
        """Return (activated_on, expires_on, is_promo) info."""
        config = get_config()
        activation_date = config.get("license_date")
        duration = config.get("license_duration", 365)
        
        if not activation_date:
            return None, None, False
            
        start_date = datetime.fromtimestamp(activation_date)
        expiry_date = start_date + timedelta(days=duration)
        
        fmt = "%d.%m.%Y"
        is_promo = duration < 300 # Rough check for promo vs annual
        return start_date.strftime(fmt), expiry_date.strftime(fmt), is_promo
