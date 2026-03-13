import hmac
import hashlib
import sys

# The private salt must match the one in lingua/core/license.py
SECRET_SALT = b"Lingua_Sanctuary_Pro_Edition_2026_VRusu"

def generate_keys(email, hwid):
    email_clean = email.strip().lower()
    hwid_clean = hwid.strip().upper()
    
    # Standard (1 year)
    payload_std = f"{email_clean}:{hwid_clean}".encode()
    key_std = hmac.new(SECRET_SALT, payload_std, hashlib.sha256).hexdigest().upper()
    
    # Promo (3 months)
    payload_promo = f"PROMO:{email_clean}:{hwid_clean}".encode()
    key_promo = hmac.new(SECRET_SALT, payload_promo, hashlib.sha256).hexdigest().upper()
    
    return key_std, key_promo

if __name__ == "__main__":
    print("-" * 50)
    print("LINGUA LICENSE GENERATOR")
    print("-" * 50)
    
    # Check if arguments are provided, otherwise ask
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        hwid = sys.argv[2]
    else:
        email = input("User Email: ").strip()
        hwid = input("Machine ID (HWID): ").strip()
        
    if not email or not hwid:
        print("Error: Email and Machine ID are required.")
        sys.exit(1)
        
    std_key, promo_key = generate_keys(email, hwid)
    
    print(f"\nResults for {email} on {hwid}:")
    print(f"Standard (1 Year): {std_key}")
    print(f"Promo (3 Months):  {promo_key}")
    print("-" * 50)
