"""
Gated UI components for Pro/Free version differentiation.
Provides decorators and helper functions to add "Padlock" icons and 
redirect users to activation if they try to access Pro features.
"""

from PySide6.QtWidgets import QMessageBox, QPushButton, QCheckBox, QRadioButton, QComboBox
from PySide6.QtGui import QIcon, QAction
from lingua.core.license import LicenseManager
from lingua.core.i18n import _
from lingua.core.utils import get_resource_path
import os

def show_pro_required_dialog(parent, feature_name):
    """Show a friendly dialog explaining that a Pro license is required."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(_("Pro Version Required"))
    msg.setText(f"<b>{feature_name}</b> " + _("is only available in the Pro version of Lingua."))
    msg.setInformativeText(_("Would you like to activate your license now to unlock all premium features?"))
    msg.setIcon(QMessageBox.Information)
    
    activate_btn = msg.addButton(_("Activate Pro"), QMessageBox.AcceptRole)
    cancel_btn = msg.addButton(_("Maybe Later"), QMessageBox.RejectRole)
    
    msg.exec()
    
    if msg.clickedButton() == activate_btn:
        # We need to trigger the activation dialog. 
        # Since we don't have direct access to MainWindow here easily, 
        # we can emit a signal or call a global handler if available.
        # For now, we'll just show the about/activation info.
        from lingua.ui.activation_dialog import ActivationDialog
        dlg = ActivationDialog(parent)
        dlg.exec()

def get_pro_icon_text(text):
    """Add a padlock emoji to the text if not Pro."""
    if not LicenseManager.is_pro():
        return f"{text} 🔒"
    return text

class GatedCheck(QCheckBox):
    """A checkbox that prompts for Pro if clicked while in Free mode."""
    def __init__(self, text, feature_name, parent=None):
        super().__init__(text, parent)
        self.feature_name = feature_name
        self._pro_text = text # Store original text
        self.update_ui()
        
    def update_ui(self):
        self.setText(get_pro_icon_text(self._pro_text))
        
    def mousePressEvent(self, event):
        if not LicenseManager.is_pro():
            show_pro_required_dialog(self.window(), self.feature_name)
            return # Block toggle
        super().mousePressEvent(event)

class GatedRadio(QRadioButton):
    """A radio button that prompts for Pro if clicked while in Free mode."""
    def __init__(self, text, feature_name, parent=None):
        super().__init__(text, parent)
        self.feature_name = feature_name
        self._pro_text = text
        self.update_ui()
        
    def update_ui(self):
        self.setText(get_pro_icon_text(self._pro_text))
        
    def mousePressEvent(self, event):
        if not LicenseManager.is_pro():
            show_pro_required_dialog(self.window(), self.feature_name)
            return # Block toggle
        super().mousePressEvent(event)


class GatedButton(QPushButton):
    """A button that prompts for Pro if clicked while in Free mode."""

    def __init__(self, text, feature_name, parent=None):
        super().__init__(text, parent)
        self.feature_name = feature_name
        self._pro_text = text
        self.update_ui()

    def update_ui(self):
        self.setText(get_pro_icon_text(self._pro_text))

    def mousePressEvent(self, event):
        if not LicenseManager.is_pro():
            show_pro_required_dialog(self.window(), self.feature_name)
            return  # Block click
        super().mousePressEvent(event)
