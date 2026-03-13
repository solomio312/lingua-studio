
import sys
import os
import json

# Add project root to sys.path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from lingua.engines.google import GoogleFreeTranslateNew

def test_google_new():
    engine = GoogleFreeTranslateNew()
    engine.set_source_lang('Auto')
    engine.set_target_lang('Romanian')
    
    test_text = "This is a long test paragraph intended to verify if the Google Free New engine can handle larger payloads without failing or being blocked by the server. It should be long enough to potentially trigger URL length limits or other server-side restrictions if they exist. " * 5
    print(f"Testing with {len(test_text)} characters.")
    
    try:
        result = engine.translate(test_text)
        print("SUCCESS!")
        print(f"Translation: {result[:100]}...")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_new()
