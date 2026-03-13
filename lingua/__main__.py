"""Entry point for `python -m lingua`."""

import sys


def main():
    import os
    import sys
    
    # Ensure the parent of the 'lingua' package is in the path
    # and prioritized over other 'lingua' versions.
    lingua_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if lingua_root not in sys.path:
        sys.path.insert(0, lingua_root)
    
    import lingua
    print(f"DEBUG APP: Loaded lingua from {lingua.__file__}")
    
    from PySide6.QtWidgets import QApplication
    from lingua.ui.main_window import MainWindow
    from lingua.ui.themes import ThemeManager
    from lingua.core.license import LicenseManager
    from lingua.ui.activation_dialog import ActivationDialog
    from lingua.core.config import get_config

    app = QApplication(sys.argv)
    app.setApplicationName('Lingua')
    app.setApplicationVersion('1.0.0-alpha')
    app.setOrganizationName('ManuX')
    
    config = get_config()
    # Apply theme
    ThemeManager.apply_theme(app, config.get('theme', 'dark'))

    # License Activation & Trial Guard (Phase 22 & 23)
    if not LicenseManager.is_activated():
        is_expired, remaining = LicenseManager.get_trial_info()
        
        # We always show the dialog if not activated, 
        # but the "Continue" button behavior is handled inside ActivationDialog.
        activation = ActivationDialog()
        result = activation.exec()
        
        # If the user didn't activate (Accepted) 
        # and either the trial is expired or they closed the dialog without "Continue Trial" (rejection logic)
        if result != ActivationDialog.DialogCode.Accepted:
            if is_expired:
                sys.exit(0)
            # If not expired, they might have clicked "Continue with Trial" (which we mapped to reject() for simplicity)
            # or just closed the window. We'll allow entry for now if still in trial.

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
