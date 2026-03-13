from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QFrame, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from lingua.core.i18n import _
from lingua.core.config import get_config

class GoogleCloudTutorialDialog(QDialog):
    """
    A detailed, scrollable tutorial dialog for setting up Google Cloud 
    and obtaining an API key with the $300 free credit.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.is_ro = self.config.get('app_language', 'en') == 'ro'
        
        self.setWindowTitle(_("Google Cloud & Gemini API Tutorial"))
        self.resize(740, 850)
        self._set_dialog_style()
        self._build_ui()

    def _set_dialog_style(self):
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

        # Header
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

        # Content Content
        if self.is_ro:
            # --- ROMANIAN VERSION (as provided by user) ---
            intro_text = (
                "Google Cloud (care integrează Google AI Studio și Vertex AI) oferă noilor utilizatori un credit gratuit de 300$, "
                "valabil timp de 90 de zile (3 luni), pe care îl poți folosi pentru a apela modelele de inteligență artificială "
                "(precum Gemini) prin API.<br><br>"
                "Iată un tutorial scurt, pas cu pas, pentru a obține cheia API și a activa acest credit:"
            )
            
            # Step 1
            content_layout.addWidget(self._create_section_title("Pasul 1: Activarea contului și a creditului de 300$"))
            step1_text = (
                "1. Accesează <b>Google Cloud Console</b> și conectează-te cu adresa ta de Gmail.<br><br>"
                "2. În partea de sus a ecranului (sau accesând secțiunea Vertex AI), vei observa un banner care te invită să activezi "
                "perioada de probă gratuită (<b>„Free trial of $300 credit”</b>). Apasă pe butonul <b>Start Free</b>.<br><br>"
                "3. Urmează pașii de pe ecran și introdu datele solicitate. Va fi necesar să adaugi un <b>card bancar</b> pentru "
                "verificarea identității, însă nu vei fi taxat automat după terminarea creditului de 300$ sau la expirarea celor 90 de zile, "
                "decât dacă decizi manual să faci upgrade la un cont plătit."
            )

            # Step 2
            content_layout.addWidget(self._create_section_title("Pasul 2: Generarea cheii API în AI Studio"))
            step2_text = (
                "1. După ce ai activat contul de facturare (Billing Account) cu suma gratuită, accesează direct platforma <b>Google AI Studio</b>.<br><br>"
                "2. În meniul principal, caută și selectează opțiunea <b>Get API Key</b> (sau secțiunea API Keys).<br><br>"
                "3. Apasă pe butonul <b>Create API Key</b>.<br><br>"
                "4. Sistemul te va pune să alegi un proiect Google Cloud. Selectează proiectul nou creat la Pasul 1 (cel care beneficiază de creditul de 300$).<br><br>"
                "5. Copiază cheia API generată (un șir lung de caractere). Aceasta este gata de a fi integrată în codul sau aplicațiile tale."
            )
            
            note_text = (
                "<b>Notă:</b> Google AI Studio oferă și un nivel gratuit permanent (Free Tier) care nu consumă bani, dar are limite stricte de utilizare "
                "(de exemplu, un număr limitat de cereri pe minut). Atunci când asociezi cheia API cu proiectul tău Cloud care are facturarea activată, "
                "vei ridica aceste limite și vei începe să consumi automat din acel credit promoțional de 300$."
            )
        else:
            # --- ENGLISH VERSION ---
            intro_text = (
                "Google Cloud (which integrates Google AI Studio and Vertex AI) offers new users a free $300 credit, "
                "valid for 90 days (3 months), which you can use to call high-quality AI models (like Gemini) via API.<br><br>"
                "Here is a short, step-by-step tutorial to get your API key and activate this credit:"
            )
            
            # Step 1
            content_layout.addWidget(self._create_section_title("Step 1: Activate Account & $300 Credit"))
            step1_text = (
                "1. Access <b>Google Cloud Console</b> and sign in with your Gmail address.<br><br>"
                "2. At the top of the screen (or in the Vertex AI section), you'll see a banner inviting you to activate "
                "your free trial (<b>'Free trial of $300 credit'</b>). Click the <b>Start Free</b> button.<br><br>"
                "3. Follow the on-screen steps and enter the required details. You'll need to add a <b>bank card</b> for "
                "identity verification, but you won't be charged automatically after the $300 credit ends or the 90 days expire, "
                "unless you manually choose to upgrade to a paid account."
            )

            # Step 2
            content_layout.addWidget(self._create_section_title("Step 2: Generate API Key in AI Studio"))
            step2_text = (
                "1. Once you've activated your Billing Account with the free credit, go directly to <b>Google AI Studio</b>.<br><br>"
                "2. In the main menu, find and select <b>Get API Key</b>.<br><br>"
                "3. Click the <b>Create API Key</b> button.<br><br>"
                "4. The system will ask you to choose a Google Cloud project. Select the project you just created in Step 1.<br><br>"
                "5. Copy the generated API key. It's now ready to be used in your applications."
            )
            
            note_text = (
                "<b>Note:</b> Google AI Studio also offers a permanent Free Tier that doesn't cost money but has strict usage limits. "
                "When you link your API key to your Cloud project with billing enabled, you lift these limits and automatically "
                "start consuming from that $300 promotional credit."
            )

        # Apply common UI construction
        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        intro.setStyleSheet("font-size: 15px; line-height: 1.8; font-weight: 300;")
        content_layout.addWidget(intro)

        step1 = QLabel(step1_text)
        step1.setWordWrap(True)
        step1.setTextFormat(Qt.RichText)
        content_layout.addWidget(step1)

        step2 = QLabel(step2_text)
        step2.setWordWrap(True)
        step2.setTextFormat(Qt.RichText)
        content_layout.addWidget(step2)

        note = QLabel(note_text)
        note.setWordWrap(True)
        note.setTextFormat(Qt.RichText)
        note.setStyleSheet("font-size: 13px; color: #888; background-color: #1e1e1e; padding: 15px; border-radius: 8px;")
        content_layout.addWidget(note)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: #16161a; border-top: 1px solid #333; padding: 25px;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.addStretch()
        
        btn_text = "Am înțeles!" if self.is_ro else "Got it!"
        got_it = QPushButton(btn_text)
        got_it.setMinimumWidth(180)
        got_it.setFixedHeight(45)
        # Use more robust styling and ensure color is readable
        got_it.setCursor(Qt.PointingHandCursor)
        got_it.setStyleSheet("""
            QPushButton {
                background-color: #4ade80;
                color: #000000;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #63ee9a;
            }
        """)
        got_it.clicked.connect(self.accept)
        footer_layout.addWidget(got_it)
        layout.addWidget(footer)

    def _create_section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; border-bottom: 1px solid #444; padding-bottom: 5px;")
        return lbl

class OllamaSetupDialog(QDialog):
    """
    Step-by-step tutorial for setting up Ollama. Properly localized and tuned.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Ollama Local AI Setup Guide"))
        self.resize(650, 750)
        self._set_dialog_style()
        self._build_ui()

    def _set_dialog_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #121212; }
            QLabel { background-color: transparent; color: #e2e8f0; }
            QScrollArea { background-color: #121212; border: none; }
            QWidget#tutorialContent { background-color: #121212; }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2e1a, stop:1 #163e16);
            border-bottom: 3px solid #4ade80;
            min-height: 80px;
        """)
        header_layout = QHBoxLayout(header)
        title = QLabel(_("Ollama Local AI Guide"))
        title.setStyleSheet("color: #4ade80; font-size: 22px; font-weight: bold; padding: 10px 20px;")
        header_layout.addWidget(title)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet("background: transparent; color: #888; font-size: 22px; border: none;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)

        # Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("tutorialContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(25)

        intro = QLabel(_("Ollama allows you to run AI models on your own computer. It is free, private, and powerful."))
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 15px; color: #cbd5e1;")
        content_layout.addWidget(intro)

        # Step 1
        content_layout.addWidget(self._create_section_title(_("Step 1: Installation")))
        step1 = QLabel(_("1. Download and install Ollama from <b>ollama.com</b>.\n2. Start the app. You should see the Ollama icon in your System Tray."))
        step1.setWordWrap(True)
        step1.setTextFormat(Qt.RichText)
        content_layout.addWidget(step1)

        # Step 2
        content_layout.addWidget(self._create_section_title(_("Step 2: Pull a Model")))
        step2 = QLabel(_("Open a terminal (PowerShell or CMD) and run the command for your preferred model. We recommend <b>Aya</b> for great results in multiple languages including Romanian."))
        step2.setWordWrap(True)
        step2.setTextFormat(Qt.RichText)
        content_layout.addWidget(step2)

        # Commands Area
        commands = [
            ("aya:8b", "ollama pull aya:8b", _("Recommended for Translations")),
            ("llama3:8b", "ollama pull llama3:8b", _("Balanced and Fast")),
            ("mistral", "ollama pull mistral", _("Solid Alternative"))
        ]

        for name, cmd, desc in commands:
            cmd_box = QFrame()
            cmd_box.setStyleSheet("background: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 10px;")
            cmd_layout = QHBoxLayout(cmd_box)
            
            info_layout = QVBoxLayout()
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setTextFormat(Qt.RichText)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("font-size: 11px; color: #888;")
            info_layout.addWidget(name_lbl)
            info_layout.addWidget(desc_lbl)
            cmd_layout.addLayout(info_layout, 1)
            
            copy_btn = QPushButton(_("Copy Command"))
            copy_btn.setStyleSheet("background: #2d2d30; color: #4ade80; border: 1px solid #4ade80; font-size: 11px; padding: 5px 10px;")
            copy_btn.clicked.connect(lambda ch, c=cmd: self._copy_to_clipboard(c))
            cmd_layout.addWidget(copy_btn)
            content_layout.addWidget(cmd_box)

        # Step 3
        content_layout.addWidget(self._create_section_title(_("Step 3: Connect in Lingua")))
        step3 = QLabel(_("1. Go to the **Engine** tab in Settings.\n2. Choose **Ollama** from the list.\n3. Click the **Refresh** button next to 'Model'.\n4. Select your downloaded model."))
        step3.setWordWrap(True)
        content_layout.addWidget(step3)

        # Step 4: Auto-Tuning
        content_layout.addWidget(self._create_section_title(_("Smart Auto-Tuning")))
        tuning_box = QFrame()
        tuning_box.setStyleSheet("background: palette(window); border: 1px solid palette(mid); border-radius: 8px; padding: 15px;")
        tuning_layout = QVBoxLayout(tuning_box)
        
        tuning_desc = QLabel(_("When you select Ollama, Lingua automatically optimizes itself:"))
        tuning_desc.setStyleSheet("font-weight: bold; color: #4ade80;")
        tuning_layout.addWidget(tuning_desc)
        
        features = [
            (_("Merge Mode"), _("Combines paragraphs for maximum throughput and speed.")),
            (_("12,000 Chars"), _("Optimal batch size for the 8k context window of local models.")),
            (_("Concurrency: 1"), _("Prevents hardware overloading and ensures stable inference.")),
            (_("2m Timeout"), _("Safety buffer for complex segments on local hardware."))
        ]
        
        for f_title, f_desc in features:
            f_lbl = QLabel(f"• <b>{f_title}</b>: {f_desc}")
            f_lbl.setWordWrap(True)
            f_lbl.setTextFormat(Qt.RichText)
            f_lbl.setObjectName("subtitle")
            f_lbl.setStyleSheet("margin-left: 10px;")
            tuning_layout.addWidget(f_lbl)
            
        content_layout.addWidget(tuning_box)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: #16161a; border-top: 1px solid #333; padding: 25px;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.addStretch()
        btn = QPushButton(_("Got it!"))
        btn.setStyleSheet("background-color: #4ade80; color: #000; font-weight: bold; border-radius: 6px; min-width: 150px; height: 40px;")
        btn.clicked.connect(self.accept)
        footer_layout.addWidget(btn)
        layout.addWidget(footer)

    def _create_section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; border-bottom: 1px solid #444; padding-bottom: 5px;")
        return lbl

    def _copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)
        sender = self.sender()
        if sender:
            old_text = sender.text()
            sender.setText(_("Copied! ✅"))
            QTimer.singleShot(1500, lambda: sender.setText(old_text))
