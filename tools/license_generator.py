"""
Architect Tool: License Signature Generator for Lingua.
Use this to generate keys for clients after they pay via PayPal.
"""

import hmac
import hashlib

# MUST MATCH lingua/core/license.py
SECRET_SALT = b"Lingua_Sanctuary_Pro_Edition_2026_VRusu"

def generate_key(email: str, hwid: str) -> str:
    """Generate a HMAC-SHA256 signature for the given email and Machine ID."""
    payload = f"{email.strip().lower()}:{hwid.strip().upper()}".encode()
    sig = hmac.new(SECRET_SALT, payload, hashlib.sha256).hexdigest().upper()
    return sig

if __name__ == "__main__":
    print("-" * 40)
    print("LINGUA -- LICENSE ARCHITECT TOOL")
    print("-" * 40)
    
    email = input("Client Email: ").strip()
    hwid = input("Client Machine ID (HWID): ").strip()
    
    if email and hwid:
        key = generate_key(email, hwid)
        print("\n" + "=" * 40)
        print(f"FOR EMAIL: {email}")
        print(f"FOR HWID: {hwid}")
        print(f"SIGNATURE KEY: {key}")
        print("=" * 40)
        input("\nPress ENTER to close...")
    else:
        print("Error: Email and Machine ID are required.")
        input("\nPress ENTER to close...")
