"""
Settings Panel for Lingua standalone app.

Migrated from Calibre plugin setting.py (1744 LOC) — standalone version
with no Calibre dependencies. All config is read/written through
lingua.core.config.get_config().
"""

import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QPlainTextEdit, QTabWidget,
    QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QFormLayout, QFileDialog, QButtonGroup,
    QScrollArea, QFrame, QMessageBox, QColorDialog, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor, QIntValidator

from lingua.core.config import get_config
from lingua.engines import builtin_engines
from lingua.core.i18n import _
from lingua.core.license import LicenseManager
from lingua.core.translation import TRANSLATION_STYLES
from lingua.ui.widgets.tour_overlay import TourOverlay
from lingua.ui.widgets.tutorial_dialog import GoogleCloudTutorialDialog
from lingua.ui.widgets.gated_widgets import GatedCheck, GatedRadio, GatedButton, get_pro_icon_text, show_pro_required_dialog
from lingua.core.cache_importer import CacheImporter

class TestEngineDialog(QDialog):
    """Interactive dialog to test translation engine settings."""
    def __init__(self, parent, engine_name, config):
        super().__init__(parent)
        self.engine_name = engine_name
        self.config = config
        self.setWindowTitle(_('Test Translation Engine'))
        self.setMinimumSize(700, 550)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Input Area
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlainText("Hello World!")
        layout.addWidget(QLabel(_('Input Text:')))
        layout.addWidget(self.input_edit, 1)

        # Output Area
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setObjectName("testOutput")
        layout.addWidget(QLabel(_('Translation Result:')))
        layout.addWidget(self.output_edit, 1)

        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(10)
        
        self.src_lang = QComboBox()
        self.src_lang.setEditable(True)
        self.src_lang.addItems(['Auto', 'English', 'Romanian', 'French', 'German', 'Spanish', 'Italian', 'Chinese', 'Japanese', 'Korean', 'Russian'])
        
        self.tgt_lang = QComboBox()
        self.tgt_lang.setEditable(True)
        self.tgt_lang.addItems(['Romanian', 'English', 'French', 'German', 'Spanish', 'Italian', 'Chinese', 'Japanese', 'Korean', 'Russian'])
        
        # Defaults
        src_pref = self.config.get('source_lang', 'Auto')
        tgt_pref = self.config.get('target_lang', 'Romanian')
        self.src_lang.setCurrentText(src_pref)
        self.tgt_lang.setCurrentText(tgt_pref)

        self.translate_btn = QPushButton(_('Translate'))
        self.translate_btn.setObjectName("primary")
        self.translate_btn.setMinimumHeight(35)
        self.translate_btn.clicked.connect(self._do_test_translate)

        footer.addWidget(self.src_lang, 1)
        footer.addWidget(self.tgt_lang, 1)
        footer.addWidget(self.translate_btn)
        
        layout.addLayout(footer)

    def _do_test_translate(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QCursor
        from lingua.core.translation import get_engine_class

        self.translate_btn.setDisabled(True)
        self.translate_btn.setText("...")
        self.output_edit.setPlainText(_("Translating..."))
        self.setCursor(Qt.WaitCursor)

        try:
            # Use specific engine settings from current config
            engine_cls = get_engine_class(self.engine_name)
            translator = engine_cls() or engine_cls
            
            # Setup translator with current settings
            translator.set_source_lang(self.src_lang.currentText())
            translator.set_target_lang(self.tgt_lang.currentText())
            
            # Perform translation
            result = translator.translate(text)
            translated_text = "".join(result) if not isinstance(result, str) else result
            
            self.output_edit.setPlainText(translated_text.strip())
        except Exception as e:
            logging.exception("Engine test dialog failed")
            self.output_edit.setPlainText(f"ERROR:\n{str(e)}")
            QMessageBox.critical(self, _('Translation Error'), str(e))
        finally:
            self.translate_btn.setDisabled(False)
            self.translate_btn.setText(_('Translate'))
            self.unsetCursor()

class ModelFetcher(QThread):
    """Asynchronously fetches available models from the engine."""
    fetched = Signal(list)
    failed = Signal(str)

    def __init__(self, engine_name, api_key, proxy_uri=None):
        super().__init__()
        self.engine_name = engine_name
        self.api_key = api_key
        self.proxy_uri = proxy_uri

    def run(self):
        try:
            from lingua.core.translation import get_engine_class
            engine_cls = get_engine_class(self.engine_name)
            
            # Temporary instance to call get_models
            engine = engine_cls() or engine_cls
            engine.api_key = self.api_key
            engine.proxy_uri = self.proxy_uri
            
            models = engine.get_models()
            if models:
                self.fetched.emit(models)
            else:
                self.failed.emit(_("No models found."))
        except Exception as e:
            self.failed.emit(str(e))

class PromptArchitectDialog(QDialog):
    """Dialog to collect book context for AI prompt generation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('✨ AI Prompt Architect'))
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header = QLabel(_("Generate Custom Style Prompt"))
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #4ade80;")
        layout.addWidget(header)

        desc = QLabel(_("Provide details about your book to generate a highly specialized translation prompt."))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaa;")
        layout.addWidget(desc)

        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(_("e.g. The Great Gatsby"))
        
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText(_("e.g. F. Scott Fitzgerald"))

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setMaximumHeight(100)
        self.summary_edit.setPlaceholderText(_("Paste a blurb or short summary of the book's themes and style..."))

        self.tone_combo = QComboBox()
        self.tone_combo.addItems([
            _("Literary & Elegant"),
            _("Modern & Fast-Paced"),
            _("Academic & Precise"),
            _("Colloquial & Dialogue-Heavy"),
            _("Dark & Atmospheric"),
            _("Lighthearted & Humorous")
        ])

        form.addRow(_("Book Title:"), self.title_edit)
        form.addRow(_("Author:"), self.author_edit)
        form.addRow(_("Book Context:"), self.summary_edit)
        form.addRow(_("Target Tone:"), self.tone_combo)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.cancel_btn = QPushButton(_("Cancel"))
        self.generate_btn = QPushButton(_("Generate Instructions"))
        self.generate_btn.setObjectName("primary")
        self.generate_btn.setMinimumHeight(40)
        
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.generate_btn)
        layout.addLayout(btns)

        self.cancel_btn.clicked.connect(self.reject)
        self.generate_btn.clicked.connect(self.accept)

    def get_data(self):
        return {
            'title': self.title_edit.text().strip(),
            'author': self.author_edit.text().strip(),
            'summary': self.summary_edit.toPlainText().strip(),
            'tone': self.tone_combo.currentText()
        }

class ArchitectWorker(QThread):
    """Background worker to generate a prompt using the current LLM."""
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, engine_name, api_key, model, context):
        super().__init__()
        self.engine_name = engine_name
        self.api_key = api_key
        self.model = model
        self.context = context

    def run(self):
        try:
            from lingua.core.translation import get_engine_class
            engine_cls = get_engine_class(self.engine_name)
            engine = engine_cls() or engine_cls
            
            # Setup engine
            engine.api_key = self.api_key
            engine.set_source_lang('English')
            engine.set_target_lang('Romanian')
            if hasattr(engine, 'set_config'):
                engine.set_config({'model': self.model})
            
            # Construct Meta-Prompt
            meta_prompt = f"""You are an elite prompt engineer for literary translation. 
Based on these details, generate a specialized system instruction (systemPrompt) or style rule for an AI translator.
The target is to translate this specific book from <slang> to <tlang>.

BOOK DETAILS:
- Title: {self.context['title']}
- Author: {self.context['author']}
- Context/Summary: {self.context['summary']}
- Desired Tone: {self.context['tone']}

INSTRUCTIONS FOR YOU:
1. Identify the unique narrative voice, prose style, and linguistic nuances.
2. Specify the level of vocabulary (literary, technical, common).
3. Recommend how to treat idioms and cultural adaptations for this specific genre.
4. Output ONLY the instruction text that should be given to the AI. 
5. NO introduction ("Here is your prompt"), NO markdown backticks. Just the text.
"""
            # Perform "Translation" of the meta-prompt (simulating a chat completion)
            result = engine.translate(meta_prompt)
            prompt_text = "".join(result) if not isinstance(result, str) else result
            self.finished.emit(prompt_text.strip())
            
        except Exception as e:
            self.failed.emit(str(e))

class SettingsPanel(QWidget):
    """Full settings panel with 4 tabs: General, Engine, Content, Styles."""

    saved = Signal()  # emitted after successful save
    theme_changed = Signal(str) # Emitted immediately on theme combobox change
    load_legacy_project = Signal(str, str) # db_path, title

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._wrap_scroll(self._build_general()), _('General'))
        self.tabs.addTab(self._wrap_scroll(self._build_engine()), _('Engine'))
        self.tabs.addTab(self._wrap_scroll(self._build_content()), _('Content'))
        self.tabs.addTab(self._wrap_scroll(self._build_styles()), _('Styles'))
        self.maintenance_tab = self._wrap_scroll(self._build_maintenance())
        self.tabs.addTab(self.maintenance_tab, _('Maintenance'))
        self.tabs.setStyleSheet('QTabBar::tab { min-width: 100px; }')
        layout.addWidget(self.tabs)

        # Save button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(_('Save Settings'))
        save_btn.setObjectName('primary')
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_all)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ─── Helpers ─────────────────────────────────────────

    @staticmethod
    def _wrap_scroll(widget):
        """Wrap a widget in a QScrollArea."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    @staticmethod
    def _divider():
        d = QFrame()
        d.setFrameShape(QFrame.Shape.HLine)
        d.setFrameShadow(QFrame.Shadow.Sunken)
        return d

    # ─── Tab: General ────────────────────────────────────

    def _build_general(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # — Output Path —
        out_group = QGroupBox('Output Path')
        out_layout = QHBoxLayout(out_group)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText('Choose a path to store translated books')
        self.output_path.setText(self.config.get('output_path') or '')
        out_browse = QPushButton('Browse...')
        out_browse.clicked.connect(self._choose_output_path)
        out_layout.addWidget(self.output_path, 1)
        out_layout.addWidget(out_browse)
        layout.addWidget(out_group)

        # — App Theme & Language —
        theme_group = QGroupBox(_('Appearance'))
        theme_layout = QVBoxLayout(theme_group)
        
        # Theme Sub-row
        row_theme = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Sepia"])
        current_theme = self.config.get('theme', 'dark').capitalize()
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        
        theme_label = QLabel(_("Interface Theme:"))
        row_theme.addWidget(theme_label)
        row_theme.addWidget(self.theme_combo, 1)
        theme_layout.addLayout(row_theme)
        
        # Language Sub-row
        row_lang = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Romanian"])
        
        current_lang = self.config.get('app_language', 'en')
        if current_lang == 'ro':
            self.lang_combo.setCurrentText("Romanian")
        else:
            self.lang_combo.setCurrentText("English")
            
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        
        lang_label = QLabel(_("App Language:"))
        row_lang.addWidget(lang_label)
        row_lang.addWidget(self.lang_combo, 1)
        theme_layout.addLayout(row_lang)

        layout.addWidget(theme_group)

        # — Merge to Translate & Experimental —
        merge_group = QGroupBox('Merge to Translate & Experimental')
        merge_vlayout = QVBoxLayout(merge_group)
        
        # Row 1: Character merge
        merge_layout = QHBoxLayout()
        self.merge_enabled = QCheckBox('Enable Character Merge')
        self.merge_enabled.setChecked(self.config.get('merge_enabled'))
        self.merge_length = QSpinBox()
        self.merge_length.setRange(1, 99999)
        self.merge_length.setValue(self.config.get('merge_length'))
        merge_layout.addWidget(self.merge_enabled)
        merge_layout.addWidget(self.merge_length)
        merge_layout.addWidget(QLabel('characters per batch'))
        merge_layout.addStretch()
        merge_vlayout.addLayout(merge_layout)
        
        # Row 2: Smart HTML Merge
        self.smart_html_merge = GatedCheck('Smart Merge HTML Inline Tags (Preserves formatting context)', _('Smart HTML Merge'))
        self.smart_html_merge.setChecked(self.config.get('smart_html_merge', False))
        merge_vlayout.addWidget(self.smart_html_merge)
        
        layout.addWidget(merge_group)

        # — Chunking Method —
        chunk_group = QGroupBox('Chunking Method')
        chunk_layout = QVBoxLayout(chunk_group)
        btn_row = QHBoxLayout()
        self.chunk_standard = QRadioButton('Standard')
        self.chunk_merge = QRadioButton('Merge')
        self.chunk_chapter = GatedRadio('Chapter-Aware', _('Chapter-Aware Chunking'))
        self.chunk_per_file = GatedRadio('Per-File', _('Per-File Chunking'))
        for rb in (self.chunk_standard, self.chunk_merge,
                   self.chunk_chapter, self.chunk_per_file):
            btn_row.addWidget(rb)
        btn_row.addStretch()
        chunk_layout.addLayout(btn_row)
        desc = QLabel(
            'Standard: one paragraph at a time. '
            'Merge: combine paragraphs up to character limit. '
            'Chapter-Aware: respects chapter boundaries (15k max). '
            'Per-File: one chunk per XHTML file (30k max).')
        desc.setWordWrap(True)
        desc.setStyleSheet('color: #888; font-style: italic;')
        chunk_layout.addWidget(desc)
        # Spine order checkbox
        self.spine_order = QCheckBox(
            'Use EPUB spine order (reading order instead of alphabetical)')
        self.spine_order.setChecked(self.config.get('use_spine_order', False))
        chunk_layout.addWidget(self.spine_order)
        layout.addWidget(chunk_group)

        saved_chunking = self.config.get('chunking_method', 'standard')
        {'standard': self.chunk_standard, 'merge': self.chunk_merge,
         'chapter_aware': self.chunk_chapter, 'per_file': self.chunk_per_file
         }.get(saved_chunking, self.chunk_standard).setChecked(True)

        # — Translator Credit —
        credit_group = QGroupBox('Translator Credit')
        credit_layout = QHBoxLayout(credit_group)
        self.credit_enabled = QCheckBox('Enable')
        self.credit_enabled.setChecked(
            self.config.get('translator_credit_enabled'))
        self.credit_text = QLineEdit()
        self.credit_text.setText(self.config.get('translator_credit') or '')
        credit_layout.addWidget(self.credit_enabled)
        credit_layout.addWidget(self.credit_text, 1)
        layout.addWidget(credit_group)

        # — HTTP Proxy —
        proxy_group = QGroupBox('HTTP Proxy')
        proxy_layout = QHBoxLayout(proxy_group)
        self.proxy_enabled = QCheckBox('Enable')
        self.proxy_enabled.setChecked(self.config.get('proxy_enabled'))
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText('Host (127.0.0.1)')
        self.proxy_port = QLineEdit()
        self.proxy_port.setPlaceholderText('Port')
        self.proxy_port.setValidator(QIntValidator(0, 65535))
        self.proxy_port.setFixedWidth(80)
        proxy_layout.addWidget(self.proxy_enabled)
        proxy_layout.addWidget(self.proxy_host, 1)
        proxy_layout.addWidget(self.proxy_port)
        layout.addWidget(proxy_group)

        proxy_setting = self.config.get('proxy_setting') or []
        if len(proxy_setting) == 2:
            self.proxy_host.setText(str(proxy_setting[0]))
            self.proxy_port.setText(str(proxy_setting[1]))

        # — Misc row: Cache + Log + Notification —
        misc_row = QHBoxLayout()
        # Cache
        cache_group = QGroupBox('Cache')
        cache_layout = QHBoxLayout(cache_group)
        self.cache_enabled = QCheckBox('Enable')
        self.cache_enabled.setChecked(self.config.get('cache_enabled'))
        cache_layout.addWidget(self.cache_enabled)
        cache_layout.addStretch()
        misc_row.addWidget(cache_group, 1)
        # Log
        log_group = QGroupBox('Job Log')
        log_layout = QHBoxLayout(log_group)
        self.log_translation = QCheckBox('Show translation')
        self.log_translation.setChecked(
            self.config.get('log_translation', True))
        log_layout.addWidget(self.log_translation)
        misc_row.addWidget(log_group, 1)
        # Notification
        notif_group = QGroupBox('Notification')
        notif_layout = QHBoxLayout(notif_group)
        self.show_notification = QCheckBox('Enable')
        self.show_notification.setChecked(
            self.config.get('show_notification', True))
        notif_layout.addWidget(self.show_notification)
        misc_row.addWidget(notif_group, 1)
        layout.addLayout(misc_row)

        layout.addStretch()
        return page

    def _on_theme_changed(self, text):
        theme_val = text.lower()
        self.config.set('theme', theme_val)
        self.config.commit()
        
        # Emit signal to let MainWindow orchestrate the application-wide update
        self.theme_changed.emit(theme_val)

    def _on_language_changed(self, text):
        lang_val = 'ro' if text == 'Romanian' else 'en'
        self.config.set('app_language', lang_val)
        self.config.commit()
        
        QMessageBox.information(
            self,
            "Language Change",
            "Please restart Lingua to apply the new interface language."
        )

    def _choose_output_path(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.output_path.setText(path)

    # ─── Tab: Engine ─────────────────────────────────────

    def _build_engine(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # — Engine selector —
        engine_group = QGroupBox('Translation Engine')
        engine_layout = QHBoxLayout(engine_group)
        self.engine_combo = QComboBox()
        for engine_cls in builtin_engines:
            display_name = engine_cls.name
            is_pro_engine = any(x in engine_cls.name for x in ["Claude", "DeepL"])
            if is_pro_engine and not LicenseManager.is_pro():
                display_name = f"{display_name} 🔒"
            self.engine_combo.addItem(display_name, engine_cls.name)
        
        self._last_valid_engine_index = 0
        current = self.config.get('translate_engine')
        if current:
            idx = self.engine_combo.findData(current)
            if idx >= 0:
                self.engine_combo.setCurrentIndex(idx)
                self._last_valid_engine_index = idx
        engine_layout.addWidget(self.engine_combo, 1)
        self.engine_test_btn = QPushButton('Test')
        self.engine_test_btn.setFixedWidth(60)
        self.engine_test_btn.clicked.connect(self._test_engine)
        engine_layout.addWidget(self.engine_test_btn)
        layout.addWidget(engine_group)

        # — API Plan Tier —
        tier_group = QGroupBox('API Plan Tier')
        tier_layout = QVBoxLayout(tier_group)
        tier_btns = QHBoxLayout()
        self.tier_free = QRadioButton('Free Tier')
        self.tier_pro = QRadioButton('Pro Tier')
        tier_btns.addWidget(self.tier_free)
        tier_btns.addWidget(self.tier_pro)
        tier_btns.addStretch()
        tier_layout.addLayout(tier_btns)
        tier_desc = QLabel(
            'Free Tier: conservative rate limits. '
            'Pro Tier: faster translation (3-5 concurrent).')
        tier_desc.setWordWrap(True)
        tier_desc.setStyleSheet('color: #888; font-style: italic;')
        tier_layout.addWidget(tier_desc)
        layout.addWidget(tier_group)

        if self.config.get('api_plan_tier', 'free') == 'pro':
            self.tier_pro.setChecked(True)
        else:
            self.tier_free.setChecked(True)

        # — API Keys —
        keys_group_header = QHBoxLayout()
        keys_group_label = QLabel(_('API Keys'))
        keys_group_label.setStyleSheet("font-weight: bold;")
        keys_group_header.addWidget(keys_group_label)
        keys_group_header.addStretch()
        
        self.api_tutorial_btn = QPushButton("💡 " + _("Tutorial"))
        self.api_tutorial_btn.setFixedWidth(110)
        self.api_tutorial_btn.setStyleSheet("font-size: 11px; font-weight: bold; color: #4ade80; background: transparent; border: 1.5px solid #4ade80; border-radius: 6px; padding: 4px;")
        self.api_tutorial_btn.clicked.connect(self._show_api_tutorial)
        keys_group_header.addWidget(self.api_tutorial_btn)

        keys_group = QGroupBox()
        keys_group.setLayout(QVBoxLayout())
        keys_group.layout().addLayout(keys_group_header)
        keys_layout = keys_group.layout()
        self.api_keys = QPlainTextEdit()
        self.api_keys.setFixedHeight(100)
        self.api_keys.setPlaceholderText(
            'Enter API key(s) for the selected engine, one per line')
        keys_layout.addWidget(self.api_keys)
        auto_tip = QLabel('Tip: API keys will auto-switch if one is unavailable.')
        auto_tip.setStyleSheet('color: #888; font-style: italic;')
        auto_tip.setVisible(False)
        keys_layout.addWidget(auto_tip)
        self.api_keys.textChanged.connect(lambda: auto_tip.setVisible(
            len(self.api_keys.toPlainText().strip().split('\n')) > 1))
        layout.addWidget(keys_group)

        # Engine change handler connected after all widgets are built (below)

        # — Preferred Language —
        lang_group = QGroupBox('Preferred Language')
        lang_layout = QFormLayout(lang_group)
        self.source_lang = QComboBox()
        self.source_lang.setEditable(True)
        self.source_lang.addItems(['Auto', 'English', 'Romanian', 'French',
                                    'German', 'Spanish', 'Italian', 'Chinese',
                                    'Japanese', 'Korean', 'Russian'])
        self.target_lang = QComboBox()
        self.target_lang.setEditable(True)
        self.target_lang.addItems(['Romanian', 'English', 'French', 'German',
                                    'Spanish', 'Italian', 'Chinese',
                                    'Japanese', 'Korean', 'Russian'])
        lang_layout.addRow('Source Language', self.source_lang)
        lang_layout.addRow('Target Language', self.target_lang)
        layout.addWidget(lang_group)

        # Load saved languages
        saved_src = self.config.get('source_lang')
        saved_tgt = self.config.get('target_lang')
        if saved_src:
            self.source_lang.setCurrentText(saved_src)
        if saved_tgt:
            self.target_lang.setCurrentText(saved_tgt)

        # — HTTP Request —
        request_group = QGroupBox('HTTP Request')
        req_layout = QFormLayout(request_group)
        self.concurrency = QSpinBox()
        self.concurrency.setRange(0, 99)
        self.concurrency.setValue(
            self.config.get('concurrency_limit', 1))
        self.interval = QDoubleSpinBox()
        self.interval.setRange(0, 999)
        self.interval.setDecimals(1)
        self.interval.setValue(
            float(self.config.get('request_interval', 0.5)))
        self.attempts = QSpinBox()
        self.attempts.setRange(0, 99)
        self.attempts.setValue(
            self.config.get('request_attempt', 3))
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0, 999)
        self.timeout.setDecimals(1)
        self.timeout.setValue(
            float(self.config.get('request_timeout', 30.0)))
        req_layout.addRow(_('Concurrency limit'), self.concurrency)
        req_layout.addRow(_('Interval (seconds)'), self.interval)
        req_layout.addRow(_('Attempt times'), self.attempts)
        req_layout.addRow(_('Timeout (seconds)'), self.timeout)
        layout.addWidget(request_group)

        # — Abort Translation —
        abort_group = QGroupBox(_('Abort Translation'))
        abort_layout = QHBoxLayout(abort_group)
        self.max_errors = QSpinBox()
        self.max_errors.setRange(1, 999)
        self.max_errors.setValue(self.config.get('max_consecutive_errors', 10))
        abort_layout.addWidget(QLabel(_('Max errors')))
        abort_layout.addWidget(self.max_errors)
        abort_layout.addWidget(QLabel(_('The number of consecutive errors to abort translation.')))
        abort_layout.addStretch()
        layout.addWidget(abort_group)

        # — GenAI Fine-tuning —
        genai_group = QGroupBox('Fine-tuning (AI Engines)')
        genai_layout = QFormLayout(genai_group)
        self.genai_endpoint = QLineEdit()
        self.genai_endpoint.setPlaceholderText('API endpoint URL')
        genai_layout.addRow('Endpoint', self.genai_endpoint)
        self.genai_model = QComboBox()
        self.genai_model.setEditable(False)
        self.genai_model.setPlaceholderText(_('Model name'))
        
        self.model_refresh_btn = QPushButton(_('Refresh'))
        self.model_refresh_btn.setFixedWidth(70)
        self.model_refresh_btn.setVisible(False)
        self.model_refresh_btn.clicked.connect(self._on_refresh_models)
        
        model_row = QHBoxLayout()
        model_row.addWidget(self.genai_model, 1)
        model_row.addWidget(self.model_refresh_btn)
        genai_layout.addRow(_('Model'), model_row)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0, 2)
        self.temperature.setDecimals(1)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.4)
        genai_layout.addRow(_('Temperature'), self.temperature)
        
        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0, 1)
        self.top_p.setDecimals(1)
        self.top_p.setSingleStep(0.1)
        self.top_p.setValue(1.0)
        genai_layout.addRow(_('topP'), self.top_p)
        
        self.top_k = QSpinBox()
        self.top_k.setRange(1, 999)
        self.top_k.setValue(2)
        genai_layout.addRow(_('topK'), self.top_k)

        self.stream_enabled = QCheckBox(_('Enable streaming response'))
        genai_layout.addRow(_('Stream'), self.stream_enabled)
        layout.addWidget(genai_group)

        # Now safe to connect — all widgets exist
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        self._on_engine_changed()  # initial load

        layout.addStretch()
        return page

    def _show_api_tutorial(self):
        """Show the Google Cloud / Gemini API tutorial dialog."""
        dlg = GoogleCloudTutorialDialog(self)
        dlg.exec()

    def _on_engine_changed(self):
        """Load API keys and settings when engine selection changes."""
        engine_name = self.engine_combo.currentData()
        if not engine_name:
            return
            
        # Gating check
        is_pro_engine = any(x in engine_name for x in ["Claude", "DeepL"])
        if is_pro_engine and not LicenseManager.is_pro():
            show_pro_required_dialog(self.window(), _("Gated Engine"))
            # Revert to last valid index
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.engine_combo.setCurrentIndex(self._last_valid_engine_index))
            return

        self._last_valid_engine_index = self.engine_combo.currentIndex()
        prefs = self.config.get('engine_preferences') or {}
        engine_prefs = prefs.get(engine_name, {})
        # API keys
        api_key = engine_prefs.get('api_keys', '')
        if isinstance(api_key, list):
            api_key = '\n'.join(api_key)
        self.api_keys.setPlainText(api_key)
        # Populate model list from engine class
        from lingua.core.translation import get_engine_class
        try:
            engine_cls = get_engine_class(engine_name)
            if hasattr(engine_cls, 'models') and engine_cls.models:
                # Store current text to restore it after repopulating
                current_model = engine_prefs.get('model', '')
                self.genai_model.clear()
                self.genai_model.addItems(engine_cls.models)
                print(f"[DEBUG] Populated {engine_name} models: {engine_cls.models}")
                
                if current_model in engine_cls.models:
                    self.genai_model.setCurrentText(current_model)
                else:
                    # Default for Gemini Masterclass
                    if engine_name == 'Gemini':
                        self.genai_model.setCurrentText("gemini-2.5-flash-lite")
                    elif current_model:
                        self.genai_model.setCurrentText(current_model)
            else:
                self.genai_model.clear()
                model = engine_prefs.get('model', '')
                self.genai_model.setCurrentText(model)
        except Exception as e:
            print(f"[DEBUG] Failed to load models for {engine_name}: {e}")

        # Endpoint
        self.genai_endpoint.setText(engine_prefs.get('endpoint', ''))
        self.temperature.setValue(
            float(engine_prefs.get('temperature', 0.4)))
        self.top_p.setValue(
            float(engine_prefs.get('top_p', 1.0)))
        self.top_k.setValue(
            int(engine_prefs.get('top_k', 2)))
        self.stream_enabled.setChecked(
            engine_prefs.get('stream', True))

        # Show/hide refresh button (only for GenAI engines with get_models support)
        supports_refresh = False
        if engine_name == 'Gemini':
            supports_refresh = True
        self.model_refresh_btn.setVisible(supports_refresh)

        # Defaults for Gemini (Masterclass settings)
        if engine_name == 'Gemini':
            if not self.genai_endpoint.text():
                self.genai_endpoint.setText("https://generativelanguage.googleapis.com/v1beta/models")
            
            # If current model is not set or looks old, suggest the new flash-lite
            current_m = self.genai_model.currentText()
            if not current_m or current_m == "gemini-2.0-flash":
                self.genai_model.setCurrentText("gemini-2.5-flash-lite")

            # Force professional defaults (MASTERCLASS)
            # We overwrite if the values are at "amateur" or "default" levels
            if self.timeout.value() < 400.0:
                self.timeout.setValue(400.0)
            if self.interval.value() < 2.0:
                self.interval.setValue(2.0)
            if self.concurrency.value() != 1:
                self.concurrency.setValue(1)
            if self.max_errors.value() < 10:
                self.max_errors.setValue(10)
            if self.temperature.value() > 0.1:
                self.temperature.setValue(0.0)
            
            # Ensure the model is set if not already in the list
            if self.genai_model.currentIndex() < 0:
                self.genai_model.setCurrentText("gemini-2.5-flash-lite")

    def _test_engine(self):
        """Save current engine config and open interactive test dialog."""
        engine_name = self.engine_combo.currentData()
        if not engine_name:
            QMessageBox.warning(self, _('No Engine'), _('Please select an engine.'))
            return

        # 1. Update config with unsaved UI values (API keys, etc.)
        prefs = self.config.get('engine_preferences') or {}
        if engine_name not in prefs:
            prefs[engine_name] = {}
        
        api_text = self.api_keys.toPlainText().strip()
        api_list = [k.strip() for k in api_text.split('\n') if k.strip()]
        
        prefs[engine_name]['api_keys'] = api_list
        prefs[engine_name]['endpoint'] = self.genai_endpoint.text()
        prefs[engine_name]['model'] = self.genai_model.currentText()
        prefs[engine_name]['temperature'] = self.temperature.value()
        prefs[engine_name]['stream'] = self.stream_enabled.isChecked()
        
        self.config.set('engine_preferences', prefs)
        self.config.set('translate_engine', engine_name)
        self.config.commit()

        # 2. Open interactive test dialog
        dlg = TestEngineDialog(self, engine_name, self.config)
        dlg.exec()

    def _on_refresh_models(self):
        """Start async model fetcher."""
        engine_name = self.engine_combo.currentData()
        api_text = self.api_keys.toPlainText().strip().split('\n')[0]
        if not api_text:
            QMessageBox.warning(self, _('No API Key'), _('Please enter an API key first.'))
            return

        self.model_refresh_btn.setDisabled(True)
        self.model_refresh_btn.setText("...")
        
        proxy = self.config.get('proxy_setting') if self.config.get('proxy_enabled') else None
        
        self.fetcher = ModelFetcher(engine_name, api_text, proxy)
        self.fetcher.fetched.connect(self._on_models_fetched)
        self.fetcher.failed.connect(lambda msg: self._on_models_fetched([], msg))
        self.fetcher.start()

    def _on_models_fetched(self, models, error=None):
        """Update model combo with fetched results."""
        self.model_refresh_btn.setDisabled(False)
        self.model_refresh_btn.setText(_("Refresh"))
        
        if error:
            QMessageBox.critical(self, _('Fetch Error'), error)
            return
            
        if models:
            current = self.genai_model.currentText()
            self.genai_model.clear()
            self.genai_model.addItems(models)
            if current in models:
                self.genai_model.setCurrentText(current)
            elif "gemini-2.5-flash-lite" in models:
                self.genai_model.setCurrentText("gemini-2.5-flash-lite")
            
            QMessageBox.information(self, _('Success'), _('Model list updated.'))

    # ─── Tab: Maintenance ────────────────────────────────

    def _build_maintenance(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel(_('System Maintenance & Tools'))
        header.setObjectName('title') # Use the theme selector
        header.setStyleSheet('font-size: 18px; margin-bottom: 5px;')
        layout.addWidget(header)

        # Legacy Import Section
        import_group = QGroupBox(_('Legacy Cache Import (Calibre Plugin)'))
        import_layout = QVBoxLayout(import_group)
        
        import_desc = QLabel(_('Migrate your translation databases from the old Calibre plugin to Lingua.'))
        import_desc.setWordWrap(True)
        import_desc.setStyleSheet('color: #888; margin-bottom: 5px;')
        import_layout.addWidget(import_desc)
        
        # New Table for Legacy Caches
        self.legacy_table = QTableWidget(0, 4)
        self.legacy_table.setHorizontalHeaderLabels([_("Book Title"), _("File"), _("Size"), _("Action")])
        self.legacy_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.legacy_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.legacy_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.legacy_table.setFixedHeight(200)
        self.legacy_table.setStyleSheet("""
            QTableWidget { 
                background-color: #1e1e1e; 
                color: #e2e8f0; 
                border: 1px solid #333; 
                gridline-color: #333; 
            }
            QHeaderView::section { 
                background-color: #2d2d30; 
                color: #ffffff; 
                font-weight: bold; 
                padding: 4px; 
                border: 1px solid #3e3e42; 
            }
        """)
        import_layout.addWidget(self.legacy_table)

        self.scan_results = QLabel(_('Checking for legacy caches...'))
        self.scan_results.setStyleSheet('color: #ffaa00; font-style: italic;')
        import_layout.addWidget(self.scan_results)
        
        btn_row = QHBoxLayout()
        self.import_btn = GatedButton(_('Import Legacy Databases'), _('Legacy Cache Import'), self)
        self.import_btn.setObjectName('secondary')
        self.import_btn.setMinimumHeight(40)
        self.import_btn.clicked.connect(self._on_import_legacy_cache)
        btn_row.addWidget(self.import_btn)
        btn_row.addStretch()
        import_layout.addLayout(btn_row)
        
        layout.addWidget(import_group)
        
        # Diagnostics Section
        diag_group = QGroupBox(_('System Diagnostics'))
        diag_layout = QFormLayout(diag_group)
        
        from lingua.core.license import LicenseManager
        diag_layout.addRow(QLabel(_('Machine ID:')), QLabel(LicenseManager.get_machine_id()))
        diag_layout.addRow(QLabel(_('Pro Level:')), QLabel("Advanced" if LicenseManager.is_pro() else "Essential (Free)"))
        
        layout.addWidget(diag_group)

        layout.addStretch()
        
        # Start async scan for feedback
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._check_legacy_caches)
        
        return page

    def _check_legacy_caches(self):
        try:
            caches = CacheImporter.scan_legacy_caches()
            self.legacy_table.setRowCount(0)
            
            if caches:
                self.scan_results.setText(_('Found {n} legacy databases.').format(n=len(caches)))
                self.scan_results.setStyleSheet('color: #4ade80; font-weight: bold;')
                
                for i, cache in enumerate(caches):
                    self.legacy_table.insertRow(i)
                    self.legacy_table.setItem(i, 0, QTableWidgetItem(cache['title']))
                    self.legacy_table.setItem(i, 1, QTableWidgetItem(cache['filename']))
                    self.legacy_table.setItem(i, 2, QTableWidgetItem(cache['size']))
                    
                    load_btn = QPushButton(_("Load Project"))
                    load_btn.setStyleSheet("""
                        QPushButton { background-color: #2d2d30; color: #4ade80; border: 1px solid #4ade80; font-size: 10px; padding: 2px 8px; }
                        QPushButton:hover { background-color: #4ade80; color: #000; }
                    """)
                    db_path = cache['path']
                    db_title = cache['title']
                    load_btn.clicked.connect(lambda checked=False, p=db_path, t=db_title: self.load_legacy_project.emit(p, t))
                    self.legacy_table.setCellWidget(i, 3, load_btn)
            else:
                self.scan_results.setText(_('No legacy Calibre caches found in the standard location.'))
                self.scan_results.setStyleSheet('color: #888;')
        except Exception as e:
            logging.error(f"Legacy scan error: {e}")
            self.scan_results.setText(_('Error scanning legacy directory.'))

    def _on_import_legacy_cache(self):
        """Execute the migration with a progress dialog."""
        if not LicenseManager.is_pro():
            return # GatedButton handles this too
            
        from PySide6.QtWidgets import QProgressDialog
        progress = QProgressDialog(_("Migrating databases..."), _("Cancel"), 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        def update_progress(current, total):
            val = int((current / total) * 100)
            progress.setValue(val)
        
        try:
            count = CacheImporter.migrate_all(update_progress)
            progress.setValue(100)
            QMessageBox.information(self, _('Success'), _('Successfully migrated {n} databases to Lingua.').format(n=count))
        except Exception as e:
            QMessageBox.critical(self, _('Migration Failed'), str(e))

    # ─── Tab: Content ────────────────────────────────────

    def _build_content(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # — Translation Position —
        pos_group = QGroupBox('Translation Position')
        pos_layout = QHBoxLayout(pos_group)
        self.pos_below = QRadioButton('Below original')
        self.pos_above = QRadioButton('Above original')
        self.pos_replace = QRadioButton('Replace original')
        pos_group_btns = QButtonGroup(pos_group)
        for i, rb in enumerate((self.pos_below, self.pos_above,
                                 self.pos_replace)):
            pos_group_btns.addButton(rb, i)
            pos_layout.addWidget(rb)
        pos_layout.addStretch()
        layout.addWidget(pos_group)

        saved_pos = self.config.get('translation_position') or 'below'
        {'below': self.pos_below, 'above': self.pos_above,
         'only': self.pos_replace}.get(saved_pos, self.pos_below).setChecked(True)

        # — Column Gap —
        gap_group = QGroupBox('Column Gap')
        gap_layout = QFormLayout(gap_group)
        self.gap_type = QComboBox()
        self.gap_type.addItems(['percentage', 'space_count'])
        self.gap_value = QSpinBox()
        self.gap_value.setRange(0, 100)
        col_gap = self.config.get('column_gap') or {}
        self.gap_type.setCurrentText(col_gap.get('_type', 'percentage'))
        gap_key = col_gap.get('_type', 'percentage')
        self.gap_value.setValue(col_gap.get(gap_key, 10))
        gap_layout.addRow('Type', self.gap_type)
        gap_layout.addRow('Value', self.gap_value)
        layout.addWidget(gap_group)

        # — Colors —
        color_group = QGroupBox('Text Colors')
        color_layout = QFormLayout(color_group)
        self.original_color = QPushButton('Choose...')
        self.original_color.setFixedWidth(120)
        self._orig_color = self.config.get('original_color')
        self._update_color_btn(self.original_color, self._orig_color)
        self.original_color.clicked.connect(
            lambda: self._pick_color('original'))
        self.translation_color = QPushButton('Choose...')
        self.translation_color.setFixedWidth(120)
        self._trans_color = self.config.get('translation_color')
        self._update_color_btn(self.translation_color, self._trans_color)
        self.translation_color.clicked.connect(
            lambda: self._pick_color('translation'))
        color_layout.addRow('Original text color', self.original_color)
        color_layout.addRow('Translation text color', self.translation_color)
        layout.addWidget(color_group)

        # — Glossary —
        gloss_group = QGroupBox('Glossary')
        gloss_layout = QHBoxLayout(gloss_group)
        self.glossary_enabled = QCheckBox('Enable')
        self.glossary_enabled.setChecked(self.config.get('glossary_enabled'))
        self.glossary_path = QLineEdit()
        self.glossary_path.setPlaceholderText('Path to glossary text (.txt) file')
        self.glossary_path.setText(self.config.get('glossary_path') or '')
        gloss_browse = QPushButton('Browse...')
        gloss_browse.clicked.connect(self._choose_glossary)
        gloss_layout.addWidget(self.glossary_enabled)
        gloss_layout.addWidget(self.glossary_path, 1)
        gloss_layout.addWidget(gloss_browse)
        layout.addWidget(gloss_group)

        # — Filter Rules —
        filter_group = QGroupBox('Content Filter Rules')
        filter_layout = QVBoxLayout(filter_group)
        filter_desc = QLabel(
            'CSS selectors to ignore or reserve during translation. '
            'One rule per line.')
        filter_desc.setWordWrap(True)
        filter_desc.setStyleSheet('color: #888; font-style: italic;')
        filter_layout.addWidget(filter_desc)

        ignore_lbl = QLabel('Ignore rules:')
        self.ignore_rules = QPlainTextEdit()
        self.ignore_rules.setFixedHeight(60)
        self.ignore_rules.setPlainText(
            '\n'.join(self.config.get('ignore_rules') or []))
        filter_layout.addWidget(ignore_lbl)
        filter_layout.addWidget(self.ignore_rules)

        reserve_lbl = QLabel('Reserve rules (keep original):')
        self.reserve_rules = QPlainTextEdit()
        self.reserve_rules.setFixedHeight(60)
        self.reserve_rules.setPlainText(
            '\n'.join(self.config.get('reserve_rules') or []))
        filter_layout.addWidget(reserve_lbl)
        filter_layout.addWidget(self.reserve_rules)
        layout.addWidget(filter_group)

        layout.addStretch()
        return page

    def _pick_color(self, which):
        """Open a color dialog and update the corresponding button."""
        current = self._orig_color if which == 'original' else self._trans_color
        initial = QColor(current) if current else QColor(Qt.GlobalColor.white)
        color = QColorDialog.getColor(initial, self, f'Pick {which} text color')
        if color.isValid():
            hex_color = color.name()
            if which == 'original':
                self._orig_color = hex_color
                self._update_color_btn(self.original_color, hex_color)
            else:
                self._trans_color = hex_color
                self._update_color_btn(self.translation_color, hex_color)

    @staticmethod
    def _update_color_btn(btn, color_hex):
        if color_hex:
            btn.setStyleSheet(
                f'background-color: {color_hex}; color: white; '
                f'border: 1px solid #555; border-radius: 4px;')
            btn.setText(color_hex)
        else:
            btn.setText('Choose...')

    def _choose_glossary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Glossary',
            '', 'JSON Files (*.json);;All Files (*.*)')
        if path:
            self.glossary_path.setText(path)

    # ─── Tab: Styles ─────────────────────────────────────

    def _build_styles(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel(_('Translate Styles & Genre Fine-Tuning'))
        header.setObjectName('title')
        header.setStyleSheet('font-size: 18px; margin-bottom: 5px;')
        layout.addWidget(header)

        info = QLabel(
            _('Customize the translation prompts for each genre. Use <slang> and <tlang> as placeholders for source and target languages.'))
        info.setWordWrap(True)
        info.setStyleSheet('color: #888; margin-bottom: 10px;')
        layout.addWidget(info)

        # Genre Selection Row
        genre_row = QHBoxLayout()
        self.style_combo = QComboBox()
        # Map friendly names to internal keys from prompt_extensions.py
        self.genre_map = {_(k): v for k, v in TRANSLATION_STYLES.items()}
        self.style_combo.addItems(list(self.genre_map.keys()))
        self.style_combo.setFixedWidth(250)
        genre_row.addWidget(self.style_combo)

        # AI Architect Button (Pro)
        self.ai_gen_btn = GatedButton(_("✨ AI Generate"), _("AI Prompt Architect"), self)
        self.ai_gen_btn.setFixedHeight(30)
        self.ai_gen_btn.setObjectName("architectBtn")
        self.ai_gen_btn.clicked.connect(self._on_ai_generate_clicked)
        genre_row.addWidget(self.ai_gen_btn)

        genre_row.addStretch()
        layout.addLayout(genre_row)

        # Genre Description
        self.genre_desc = QLabel('')
        self.genre_desc.setStyleSheet('font-style: italic; color: #aaa; margin-bottom: 5px;')
        layout.addWidget(self.genre_desc)

        # Style Prompt Editor
        self.style_prompt = QPlainTextEdit()
        self.style_prompt.setMinimumHeight(150)
        self.style_prompt.setPlaceholderText(_('Enter custom system instructions for this genre...'))
        layout.addWidget(self.style_prompt)

        # Reset button
        reset_row = QHBoxLayout()
        reset_btn = QPushButton(_('Reset to Default'))
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self._reset_style_prompt)
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        layout.addLayout(reset_row)

        # Few-Shot Examples Section
        few_shot_group = QGroupBox(_('Few-Shot Examples (Optional)'))
        self.few_shot_layout = QVBoxLayout(few_shot_group)
        self.few_shot_container = QWidget()
        self.few_shot_list_layout = QVBoxLayout(self.few_shot_container)
        self.few_shot_list_layout.setContentsMargins(0, 0, 0, 0)
        self.few_shot_list_layout.setSpacing(10)
        self.few_shot_layout.addWidget(self.few_shot_container)

        add_example_btn = QPushButton(_('+ Add Example'))
        add_example_btn.setFixedWidth(150)
        add_example_btn.clicked.connect(lambda: self._add_few_shot_ui())
        self.few_shot_layout.addWidget(add_example_btn)
        layout.addWidget(few_shot_group)

        # Style Glossary Section
        glossary_group = QGroupBox(_('Style Glossary (Optional)'))
        glossary_vbox = QVBoxLayout(glossary_group)
        glossary_info = QLabel(_('Format: Term=Translation (one per line). Injected into systemInstruction for persistence.'))
        glossary_info.setStyleSheet('font-size: 11px; color: #777; font-style: italic;')
        glossary_vbox.addWidget(glossary_info)
        
        self.style_glossary = QPlainTextEdit()
        self.style_glossary.setMinimumHeight(100)
        self.style_glossary.setPlaceholderText('Hives=Stingării\nServicer=Servisant')
        glossary_vbox.addWidget(self.style_glossary)
        layout.addWidget(glossary_group)

        # Initial Load
        self.style_combo.currentTextChanged.connect(self._on_genre_changed)
        self._on_genre_changed(self.style_combo.currentText())

        layout.addStretch()
        return page

    def _on_genre_changed(self, genre_name):
        """Handle genre selection change."""
        internal_key = self.genre_map.get(genre_name, 'literary')
        
        # Descriptions map
        descriptions = {
            'literary': _('General literary translation for novels and fiction.'),
            'romance': _('Emotional, evocative language for romance novels.'),
            'thriller': _('Tense, punchy, and fast-paced style for action/spy thrillers.'),
            'historical': _('Formal, period-appropriate language for historical works.'),
            'scifi_philosophical': _('Precision and imaginative depth for Sci-Fi and speculative fiction.'),
            'business': _('Professional, concise corporate and economic terminology.'),
            'technical': _('Accurate technical terms and manual-style clarity.'),
            'self_help': _('Inspirational, direct, and accessible tone.'),
            'philosophy_theology': _('Deeply resonant, academic, and conceptually precise.'),
            'editing': _('Refining existing translations for flow and grammar.'),
        }
        self.genre_desc.setText(descriptions.get(internal_key, ''))
        
        # Load data
        self._load_style_data(internal_key)

    def _add_few_shot_ui(self, original='', translation=''):
        """Add a new few-shot example UI block."""
        block = QFrame()
        block.setFrameShape(QFrame.Shape.StyledPanel)
        block.setStyleSheet('background-color: #353538; border: 1px solid #444; border-radius: 6px; padding: 12px;')
        block_layout = QVBoxLayout(block)
        
        # Original
        orig_label = QLabel(_('Original:'))
        orig_label.setStyleSheet('font-weight: bold; color: #888;')
        block_layout.addWidget(orig_label)
        orig_edit = QPlainTextEdit()
        orig_edit.setPlainText(original)
        orig_edit.setPlaceholderText(_('Paste original text here...'))
        orig_edit.setMaximumHeight(80)
        block_layout.addWidget(orig_edit)
        
        # Translation
        trans_label = QLabel(_('Translation:'))
        trans_label.setStyleSheet('font-weight: bold; color: #888;')
        block_layout.addWidget(trans_label)
        trans_edit = QPlainTextEdit()
        trans_edit.setPlainText(translation)
        trans_edit.setPlaceholderText(_('Paste your perfect translation here...'))
        trans_edit.setMaximumHeight(80)
        block_layout.addWidget(trans_edit)
        
        # Remove button
        remove_btn = QPushButton(_('🗑 Remove'))
        remove_btn.setFixedWidth(80)
        remove_btn.setStyleSheet('background-color: #442222; color: #ff6666;')
        remove_btn.clicked.connect(lambda: self._remove_few_shot_ui(block))
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(remove_btn)
        block_layout.addLayout(btn_row)
        
        self.few_shot_list_layout.addWidget(block)
        return orig_edit, trans_edit

    def _remove_few_shot_ui(self, block):
        block.deleteLater()
        self.few_shot_list_layout.removeWidget(block)

    def _load_style_data(self, internal_key):
        """Load prompt, few-shots, and glossary for the genre."""
        # Clear existing few-shots
        for i in reversed(range(self.few_shot_list_layout.count())): 
            self.few_shot_list_layout.itemAt(i).widget().deleteLater()
            
        prefs = self.config.get('engine_preferences') or {}
        # We now store as a nested dict: { genre_key: { prompt: str, few_shots: list, glossary: str } }
        style_data_map = prefs.get('style_data', {})
        data = style_data_map.get(internal_key, {})
        
        self.style_prompt.setPlainText(data.get('prompt', ''))
        self.style_glossary.setPlainText(data.get('glossary', ''))
        
        few_shots = data.get('few_shots', [])
        for fs in few_shots:
            self._add_few_shot_ui(fs.get('original', ''), fs.get('translation', ''))

    def _reset_style_prompt(self):
        """Reset to hardcoded defaults from prompt_extensions."""
        from lingua.engines.prompt_extensions import STYLE_RULES
        genre_name = self.style_combo.currentText()
        internal_key = self.genre_map.get(genre_name, 'literary')
        
        default_prompt = STYLE_RULES.get(internal_key, '')
        self.style_prompt.setPlainText(default_prompt.strip())
        
        for i in reversed(range(self.few_shot_list_layout.count())): 
            self.few_shot_list_layout.itemAt(i).widget().deleteLater()

    def _on_ai_generate_clicked(self):
        """Handle AI prompt generation."""
        if not LicenseManager.is_pro():
            return # Handled by GatedButton

        # 1. Selection Engine Check
        engine_name = self.engine_combo.currentData()
        if engine_name not in ['Gemini', 'Claude', 'GPT-4o', 'GPT-4o-mini']:
            # Maybe restrict to LLM engines for better results
            pass

        # 2. Get Book Info
        dlg = PromptArchitectDialog(self)
        if not dlg.exec():
            return

        context = dlg.get_data()
        if not context['title']:
            QMessageBox.warning(self, _("Missing Info"), _("Please at least enter a book title."))
            return

        # 3. Setup Worker
        api_key = self.api_keys.toPlainText().strip().split('\n')[0]
        if not api_key:
            QMessageBox.warning(self, _("No API Key"), _("Please ensure you have an API key set for the selected engine."))
            return

        model = self.genai_model.currentText()
        
        self.ai_gen_btn.setDisabled(True)
        self.ai_gen_btn.setText(_("Architecting..."))
        
        self.architect_worker = ArchitectWorker(engine_name, api_key, model, context)
        self.architect_worker.finished.connect(self._on_architect_finished)
        self.architect_worker.failed.connect(self._on_architect_failed)
        self.architect_worker.start()

    def _on_architect_finished(self, prompt_text):
        self.ai_gen_btn.setDisabled(False)
        self.ai_gen_btn.setText(_("✨ AI Generate"))
        
        # Apply prompt to the current view
        if prompt_text:
            self.style_prompt.setPlainText(prompt_text)
            QMessageBox.information(self, _("Success"), _("AI has generated a new stylistic instruction for this book."))

    def _on_architect_failed(self, error):
        self.ai_gen_btn.setDisabled(False)
        self.ai_gen_btn.setText(_("✨ AI Generate"))
        QMessageBox.critical(self, _("Generation Error"), f"AI failed to generate prompt: {error}")

    # ─── Save All ────────────────────────────────────────

    def _save_all(self):
        """Collect values from all tabs and persist to config.json."""
        c = self.config

        # General tab
        c.set('output_path', self.output_path.text() or None)
        c.set('theme', self.theme_combo.currentText().lower())
        
        lang_val = 'ro' if self.lang_combo.currentText() == 'Romanian' else 'en'
        c.set('app_language', lang_val)
        
        c.set('merge_enabled', self.merge_enabled.isChecked())
        c.set('merge_length', self.merge_length.value())
        c.set('smart_html_merge', self.smart_html_merge.isChecked())
        # Chunking
        for method, rb in [('standard', self.chunk_standard),
                           ('merge', self.chunk_merge),
                           ('chapter_aware', self.chunk_chapter),
                           ('per_file', self.chunk_per_file)]:
            if rb.isChecked():
                c.set('chunking_method', method)
                break
        c.set('use_spine_order', self.spine_order.isChecked())
        c.set('translator_credit_enabled', self.credit_enabled.isChecked())
        c.set('translator_credit', self.credit_text.text())
        c.set('proxy_enabled', self.proxy_enabled.isChecked())
        proxy_host = self.proxy_host.text().strip()
        proxy_port = self.proxy_port.text().strip()
        if proxy_host and proxy_port:
            c.set('proxy_setting', [proxy_host, int(proxy_port)])
        c.set('cache_enabled', self.cache_enabled.isChecked())
        c.set('log_translation', self.log_translation.isChecked())
        c.set('show_notification', self.show_notification.isChecked())

        # Engine tab
        engine_name = self.engine_combo.currentData()
        c.set('translate_engine', engine_name)
        c.set('api_plan_tier', 'pro' if self.tier_pro.isChecked() else 'free')
        c.set('source_lang', self.source_lang.currentText())
        c.set('target_lang', self.target_lang.currentText())
        c.set('concurrency_limit', self.concurrency.value())
        c.set('request_interval', self.interval.value())
        c.set('request_attempt', self.attempts.value())
        c.set('request_timeout', self.timeout.value())

        # Save per-engine preferences
        prefs = c.get('engine_preferences') or {}
        if engine_name not in prefs:
            prefs[engine_name] = {}
        api_text = self.api_keys.toPlainText().strip()
        api_list = [k.strip() for k in api_text.split('\n') if k.strip()]
        prefs[engine_name]['api_keys'] = api_list
        prefs[engine_name]['endpoint'] = self.genai_endpoint.text()
        prefs[engine_name]['model'] = self.genai_model.currentText()
        prefs[engine_name]['temperature'] = self.temperature.value()
        prefs[engine_name]['top_p'] = self.top_p.value()
        prefs[engine_name]['top_k'] = self.top_k.value()
        prefs[engine_name]['stream'] = self.stream_enabled.isChecked()
        c.set('engine_preferences', prefs)
        c.set('max_consecutive_errors', self.max_errors.value())

        # Content tab
        for pos_key, rb in [('below', self.pos_below),
                            ('above', self.pos_above),
                            ('only', self.pos_replace)]:
            if rb.isChecked():
                c.set('translation_position', pos_key)
                break
        gap_type = self.gap_type.currentText()
        c.set('column_gap', {
            '_type': gap_type,
            gap_type: self.gap_value.value(),
        })
        c.set('original_color', self._orig_color)
        c.set('translation_color', self._trans_color)
        c.set('glossary_enabled', self.glossary_enabled.isChecked())
        c.set('glossary_path', self.glossary_path.text() or None)
        ignore = [r.strip() for r in self.ignore_rules.toPlainText().split('\n')
                  if r.strip()]
        c.set('ignore_rules', ignore)
        reserve = [r.strip() for r in self.reserve_rules.toPlainText().split('\n')
                   if r.strip()]
        c.set('reserve_rules', reserve)

        # Styles tab
        prefs = c.get('engine_preferences') or {}
        if 'style_data' not in prefs:
            prefs['style_data'] = {}
            
        genre_name = self.style_combo.currentText()
        internal_key = self.genre_map.get(genre_name, 'literary')
        
        # Collect few-shot examples
        few_shots = []
        for i in range(self.few_shot_list_layout.count()):
            widget = self.few_shot_list_layout.itemAt(i).widget()
            if widget:
                # Find the two QPlainTextEdit children
                edits = widget.findChildren(QPlainTextEdit)
                if len(edits) >= 2:
                    orig = edits[0].toPlainText().strip()
                    trans = edits[1].toPlainText().strip()
                    if orig and trans:
                        few_shots.append({'original': orig, 'translation': trans})
        
        prefs['style_data'][internal_key] = {
            'prompt': self.style_prompt.toPlainText().strip(),
            'few_shots': few_shots,
            'glossary': self.style_glossary.toPlainText().strip()
        }
        
        # Keep old style_prompts for backward compatibility (just the prompt)
        if 'style_prompts' not in prefs:
            prefs['style_prompts'] = {}
        prefs['style_prompts'][genre_name] = self.style_prompt.toPlainText().strip()
        
        c.set('engine_preferences', prefs)
        # Also set current style so the engine knows which one to use
        c.set('current_translation_style', internal_key)

        # Commit to disk
        c.commit()
        self.saved.emit()

        QMessageBox.information(self, 'Settings Saved',
                                'All settings have been saved successfully.')
