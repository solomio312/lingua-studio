from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from lingua.core.i18n import _

class GoogleCloudTutorialDialog(QDialog):
    """
    A detailed, scrollable tutorial dialog for setting up Google Cloud 
    and obtaining an API key with the $300 free credit.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Google Cloud & Gemini API Tutorial"))
        self.resize(700, 800)
        self._set_dialog_style()
        self._build_ui()

    def _set_dialog_style(self):
        # Force the dialog to have a dark background and ensure labels are transparent/readable
        # This prevents global themes from injecting beige backgrounds or dark text
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                background-color: transparent;
                color: #e2e8f0;
            }
            QScrollArea {
                background-color: #121212;
                border: none;
            }
            QWidget#tutorialContent {
                background-color: #121212;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header - Forced Dark and Vibrant
        header = QFrame()
        header.setObjectName("tutorialHeader")
        header.setStyleSheet("""
            #tutorialHeader {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1a2e, stop:1 #16213e);
                border-bottom: 3px solid #4ade80;
                min-height: 80px;
            }
            QLabel {
                color: #4ade80;
                font-size: 22px;
                font-weight: bold;
                padding: 10px 20px;
            }
        """)
        header_layout = QHBoxLayout(header)
        title = QLabel(_("Google Cloud & Gemini API Guide"))
        header_layout.addWidget(title)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                font-size: 22px;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content.setObjectName("tutorialContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(25)

        # Intro
        intro_text = _(
            "Google Cloud (integrated with Google AI Studio and Vertex AI) offers new users a **free credit of $300**, "
            "valid for **90 days** (3 months), which you can use to call the highest-quality AI models (like Gemini 1.5/2.5 Pro) via API."
        )
        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 15px; line-height: 1.8; font-weight: 300;")
        content_layout.addWidget(intro)

        # Step 1
        content_layout.addWidget(self._create_section_title(_("Step 1: Activate Account & $300 Credit")))
        step1_text = _(
            "1. Access **Google Cloud Console** and log in with your Gmail address.\n\n"
            "2. At the top of the screen (or in the 'Vertex AI' section), you will see a banner for the "
            "**'Free trial of $300 credit'**. Click **'Start Free'**.\n\n"
            "3. Follow the identity verification steps. You will need a card, but you **will not be automatically charged** "
            "when the credit or timeframe expires. You only pay if you manually upgrade later."
        )
        step1 = QLabel(step1_text)
        step1.setWordWrap(True)
        step1.setStyleSheet("color: #cbd5e1; font-size: 14px; line-height: 1.8;")
        content_layout.addWidget(step1)

        # Step 2
        content_layout.addWidget(self._create_section_title(_("Step 2: Generate API Key in AI Studio")))
        step2_text = _(
            "1. Once your Billing Account is active, go directly to **Google AI Studio** (aistudio.google.com).\n\n"
            "2. Select **'Get API Key'** from the sidebar.\n\n"
            "3. Click **'Create API Key'**. \n\n"
            "4. **Crucial:** Select the **Google Cloud Project** created in Step 1 (the one with the $300 credit).\n\n"
            "5. Copy the generated key. It's ready to use in Lingua!"
        )
        step2 = QLabel(step2_text)
        step2.setWordWrap(True)
        step2.setStyleSheet("color: #cbd5e1; font-size: 14px; line-height: 1.8;")
        content_layout.addWidget(step2)

        # Important Note
        note_box = QFrame()
        note_box.setStyleSheet("background: #1e1e1e; border: 1px solid #333; border-left: 5px solid #4ade80; padding: 20px; border-radius: 8px;")
        note_layout = QVBoxLayout(note_box)
        note_title = QLabel(_("💡 Pro Tip: Free Tier vs Billing"))
        note_title.setStyleSheet("color: #4ade80; font-weight: bold; border: none; padding: 0; font-size: 15px;")
        note_layout.addWidget(note_title)
        
        note_text = _(
            "Google AI Studio has a permanent 'Free Tier', but it has strict rate limits (e.g., 2-15 requests per minute). "
            "By associating your key with a Cloud Project that has billing enabled (even the free $300 one), "
            "you lift these limits and can translate much faster using the promotional credit."
        )
        note_lbl = QLabel(note_text)
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; border: none; padding: 0; line-height: 1.6;")
        note_layout.addWidget(note_lbl)
        content_layout.addWidget(note_box)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: #16161a; border-top: 1px solid #333; padding: 25px;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.addStretch()
        
        got_it = QPushButton(_("Got it, let's go!"))
        got_it.setMinimumWidth(220)
        got_it.setFixedHeight(45)
        got_it.setStyleSheet("""
            QPushButton {
                background-color: #4ade80;
                color: #000000;
                font-size: 14px;
                font-weight: 800;
                border: 2px solid #22c55e;
                border-radius: 8px;
                padding: 0 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #22c55e;
                border-color: #16a34a;
            }
            QPushButton:pressed {
                background-color: #16a34a;
                margin-top: 2px;
            }
        """)
        got_it.setCursor(Qt.PointingHandCursor)
        got_it.clicked.connect(self.accept)
        footer_layout.addWidget(got_it)
        layout.addWidget(footer)

    def _create_section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            border-bottom: 1px solid #444;
            padding-bottom: 8px;
            margin-top: 10px;
        """)
        return lbl
