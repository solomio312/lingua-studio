"""
Smoke test for Lingua — macOS Build Verification.
This script checks if the core UI and application modules can be initialized 
on macOS without a full GUI environment (using offscreen platform).
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_smoke_test():
    print("🚀 Starting macOS Smoke Test...")
    
    try:
        # 1. Set QT to offscreen mode for CI environments
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        
        # 2. Test Core Imports
        print("📦 Testing core imports...")
        import lingua
        import lingua.core.config
        import lingua.core.cache
        from PySide6.QtWidgets import QApplication
        print(f"✅ Lingua version: {getattr(lingua, '__version__', '1.1.0')}")
        
        # 3. Test QApplication initialization
        print("🖥️ Initializing QApplication (offscreen)...")
        app = QApplication(sys.argv)
        print("✅ QApplication initialized successfully.")
        
        # 4. Test Workspace UI import (this triggers deep PySide6 imports)
        print("🧩 Testing UI component imports...")
        from lingua.ui.translation_workspace import TranslationWorkspace
        print("✅ UI components imported successfully.")
        
        print("\n✨ SMOKE TEST PASSED! The build integrity is confirmed for macOS.")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()
