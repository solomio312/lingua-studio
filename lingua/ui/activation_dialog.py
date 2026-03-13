"""
Activation Dialog for Lingua.
Provides a premium UI for license entry and verification.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDesktopServices, QIcon
from lingua.core.i18n import _
from lingua.core.license import LicenseManager

class ActivationDialog(QDialog):
    """Premium activation screen for commercial licenses."""
    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Lingua -- System Activation'))
        self.setFixedWidth(650)
        self.setFixedHeight(500)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header Section
        header = QLabel('Lingua')
        header.setObjectName('mainTitle')
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        motto = QLabel(_('Designed for those for whom books are sanctuaries.'))
        motto.setObjectName('motto')
        motto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(motto)

        layout.addSpacing(10)

        # Instructions
        instr = QLabel(_('To activate your professional license, please enter your email and the signature key provided by the architect.'))
        instr.setWordWrap(True)
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setStyleSheet('color: #aaa; font-size: 13px;')
        layout.addWidget(instr)

        # Input Fields
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(_('Your Email Address (e.g. client@yahoo.ro)'))
        self.email_input.setMinimumHeight(40)
        layout.addWidget(self.email_input)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(_('License Signature Key'))
        self.key_input.setMinimumHeight(40)
        layout.addWidget(self.key_input)

        # HWID Display Row
        hwid_layout = QHBoxLayout()
        hwid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hwid_layout.setSpacing(10)

        hwid = LicenseManager.get_machine_id()
        self.hwid_label = QLabel(f"Machine ID: {hwid}")
        self.hwid_label.setStyleSheet('color: #ff5555; font-size: 13px; font-weight: bold; font-family: monospace;')
        self.hwid_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hwid_layout.addWidget(self.hwid_label)

        copy_btn = QPushButton(_('Copy'))
        copy_btn.setFixedWidth(50)
        copy_btn.setStyleSheet('font-size: 10px; padding: 2px;')
        copy_btn.clicked.connect(self._on_copy_hwid)
        hwid_layout.addWidget(copy_btn)

        layout.addLayout(hwid_layout)

        layout.addSpacing(10)

        # Trial Status Label
        self.trial_label = QLabel("")
        self.trial_label.setStyleSheet('color: #ffaa00; font-size: 13px; font-weight: bold;')
        self.trial_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.trial_label)

        # Buttons
        btn_layout = QHBoxLayout()
        
        buy_btn = QPushButton(_('Get License / Support'))
        buy_btn.setObjectName('secondary')
        buy_btn.setMinimumHeight(40)
        buy_btn.clicked.connect(self._on_buy)
        btn_layout.addWidget(buy_btn)

        self.trial_btn = QPushButton(_('Continue with Trial'))
        self.trial_btn.setObjectName('secondary')
        self.trial_btn.setMinimumHeight(40)
        self.trial_btn.clicked.connect(self.reject) # reject will just close and proceed in our main loop
        btn_layout.addWidget(self.trial_btn)

        activate_btn = QPushButton(_('   Activate Now   '))
        activate_btn.setObjectName('primary')
        activate_btn.setMinimumHeight(40)
        activate_btn.clicked.connect(self._on_activate)
        btn_layout.addWidget(activate_btn)

        layout.addLayout(btn_layout)
        
        self._update_trial_status()

    def _update_trial_status(self):
        """Show remaining trial days and toggle trial button."""
        is_expired, remaining = LicenseManager.get_trial_info()
        
        if is_expired:
            self.trial_label.setText(_("Trial period has expired. Please activate to continue."))
            self.trial_label.setStyleSheet('color: #ff5555; font-size: 13px; font-weight: bold;')
            self.trial_btn.setVisible(False)
        else:
            self.trial_label.setText(_("Trial Period: {n} days remaining").format(n=remaining))
            self.trial_btn.setVisible(True)
    def _on_buy(self):
        # Instructions for PayPal or external link
        msg = QMessageBox(self)
        msg.setWindowTitle(_("How to Get a License"))
        msg.setText(_("<b>Manual PayPal Activation:</b><br><br>"
                     "1. Send the payment to <b>solomio312@gmail.com</b> (PayPal).<br>"
                     "2. Include your <b>Email</b> and <b>Machine ID</b> in the notes.<br>"
                     "3. You will receive your unique Signature Key via email within <b>24-48 hours</b>."))
        msg.exec()

    def _on_copy_hwid(self):
        hwid = LicenseManager.get_machine_id()
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(hwid)
        # Subtle feedback
        self.hwid_label.setText(f"Machine ID: {hwid} ({_('Copied!')})")
        self.hwid_label.setStyleSheet('color: #4ade80; font-size: 13px; font-weight: bold; font-family: monospace;')
        from PySide6.QtCore import QTimer
        def reset():
            self.hwid_label.setText(f"Machine ID: {hwid}")
            self.hwid_label.setStyleSheet('color: #ff5555; font-size: 13px; font-weight: bold; font-family: monospace;')
        QTimer.singleShot(2000, reset)

    def _on_activate(self):
        email = self.email_input.text().strip()
        key = self.key_input.text().strip()

        is_valid, duration = LicenseManager.verify_license(email, key)
        if is_valid:
            LicenseManager.save_license(email, key, duration)
            msg = _("Lingua has been successfully activated (Pro Version). Welcome to the sanctuary!") if duration > 300 \
                  else _("Lingua has been successfully activated (Promo Edition). Welcome to the sanctuary!")
            QMessageBox.information(self, _("Success"), msg)
            self.accept()
        else:
            QMessageBox.critical(self, _("Error"), _("Invalid license key or email. Please check your spelling and Machine ID."))
