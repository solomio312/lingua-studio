"""
Translation Workspace — main translation view with paragraph table.

Shows extracted EPUB paragraphs in a two-column table (original + translation)
with status indicators and translation controls.
"""

import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QAbstractItemView, QMessageBox, QFrame, QSplitter, QComboBox, QLineEdit,
    QCheckBox, QGroupBox, QSpinBox, QSpacerItem, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QUrl, QTimer, QEvent
from PySide6.QtGui import QColor, QFont, QAction, QDesktopServices, QIcon

from lingua.core.config import get_config
from lingua.core.conversion import extract_book
from lingua.ui.workers import TranslationWorker, ExportWorker
from lingua.ui.widgets.editor import SourceTextEditor, TranslationEditor, CodeEditor
from lingua.ui.widgets.table import WorkspaceTable
from lingua.ui.widgets.cache_dialog import CacheDialog
from lingua.core.i18n import _ as _tr
from lingua.ui.widgets.gated_widgets import GatedButton, get_pro_icon_text, show_pro_required_dialog
from lingua.core.license import LicenseManager
from lingua.core.translation import get_engine_class, get_translator, TRANSLATION_STYLES


from lingua.core.utils import uid
from lingua.core.cache import get_cache
from lingua.core.element import get_element_handler, get_page_elements
from lingua.core.conversion import extract_epub_pages
from lingua.core.config import get_config, CACHE_DIR
from lingua.core.translation import get_engine_class, get_translator
import lingua

class ExtractionWorker(QObject):
    """Worker to extract EPUB paragraphs in a background thread."""
    finished = Signal(object)   # emits a dict with context
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, epub_path):
        super().__init__()
        self.epub_path = epub_path

    def run(self):
        try:
            print(f"DEBUG WORKER: ExtractionWorker starting for {self.epub_path}")
            self.progress.emit('Extracting paragraphs...')
            
            config = get_config()
            source_lang = config.get('source_lang', 'Auto')
            target_lang = config.get('target_lang', 'Romanian')
            chunking_method = config.get('chunking_method', 'standard')
            engine_name = config.get('translate_engine', 'Google(Free)New')
            
            engine_class = get_engine_class(engine_name)
            translator = get_translator(engine_class)
            
            # Create Element Handler
            element_handler = get_element_handler(
                translator.placeholder, translator.separator, 'ltr', chunking_method)
            element_handler.set_translation_lang(
                translator.get_iso639_target_code(target_lang))

            merge_length = str(element_handler.get_merge_length())
            cache_id = uid(
                self.epub_path + translator.name + target_lang + merge_length 
                + 'utf-8' + chunking_method + 'norm_v1')
            
            cache = get_cache(cache_id)
            cache.set_info('title', os.path.basename(self.epub_path))
            cache.set_info('engine_name', translator.name)
            cache.set_info('target_lang', target_lang)
            cache.set_info('merge_length', merge_length)
            cache.set_info('chunking_method', chunking_method)
            cache.set_info('app_version', getattr(lingua, '__version__', '1.0.0'))

            # 1. Essential Extraction (needed for book metadata/images regardless of cache)
            pages, spine_hrefs, book = extract_epub_pages(self.epub_path)
            
            # 2. Check if cache is already populated
            paragraphs = cache.all_paragraphs()
            
            if paragraphs:
                print(f"DEBUG WORKER: Cache already populated with {len(paragraphs)} items. skipping element extraction.")
            else:
                # 3. Full Extraction and Chunking (only if cache is empty)
                self.progress.emit('Performing full text extraction...')
                spine_order = spine_hrefs if config.get('use_spine_order', False) else None
                elements = list(get_page_elements(pages, spine_order))
                
                # Prepare originals and save to cache
                original_group = element_handler.prepare_original(elements)
                
                # We NO LONGER call cache.clear() here. 
                # cache.save() handles intelligent merging/updating.
                cache.save(original_group)
                paragraphs = cache.all_paragraphs()

            print(f"DEBUG WORKER: Extraction done. Found {len(paragraphs)} paragraphs.")
            
            context = {
                'book': book,
                'pages': pages,
                'element_handler': element_handler,
                'cache': cache,
                'paragraphs': paragraphs
            }
            self.finished.emit(context)
        except Exception as e:
            print(f"DEBUG WORKER: Extraction ERROR: {e}")
            import traceback
            traceback.print_exc()
            logging.exception('Extraction failed')
            self.error.emit(str(e))


# Status colors
STATUS_COLORS = {
    'untranslated': QColor(80, 80, 90),
    'translating': QColor(100, 140, 255),
    'done': QColor(70, 180, 100),
    'error': QColor(220, 80, 80),
    'cached': QColor(140, 120, 200),
}


class TranslationWorkspace(QWidget):
    """Translation workspace showing original/translation paragraph table."""

    back_requested = Signal()  # go back to dashboard

    def __init__(self, epub_path, title='', parent=None, review_mode=False):
        super().__init__(parent)
        self.epub_path = epub_path
        self.review_mode = review_mode
        self.book_title = title or (os.path.basename(epub_path) if epub_path != "REVIEW_MODE" else "Legacy Cache")
        self.elements = []
        self.config = get_config()
        self._threads = [] # Keep references to background threads to prevent GC crash
        self._workers = [] # Keep references to workers to prevent GC crash

        # Determine uid from path or filename
        if self.review_mode:
            self.uid = os.path.splitext(os.path.basename(epub_path))[0]
        else:
            self.uid = uid(self.epub_path)

        self._build_ui()
        
        if self.review_mode:
            self._load_from_cache()
        else:
            self._start_extraction()

    def resizeEvent(self, event):
        """Dynamic adjustments on resize."""
        super().resizeEvent(event)
        
        # Scale title font based on width
        w = self.width()
        if w < 1000:
            size = max(14, int(18 * (w / 1000)))
            self.title_label.setStyleSheet(f"font-size: {size}px; font-weight: bold;")
        else:
            self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

    def _create_control_group(self, label_text, widget):
        """Creates a modern field group with a label and a widget."""
        group = QFrame()
        group.setObjectName('settingsGroup')
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 4, 8, 4) # Tighter density
        group_layout.setSpacing(4)
        
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Centered for 3D card luck
        
        # Consistent height for widgets
        widget.setMinimumHeight(24) # Slightly smaller to fit
        widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        
        group_layout.addWidget(label)
        group_layout.addWidget(widget)
        group_layout.addStretch()
        return group

    def _build_ui(self):
        # Styles handled by ThemeManager at application level
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # -----------------------------------------------------------------
        # 1. Slim Header (Back + Title)
        # -----------------------------------------------------------------
        header = QHBoxLayout()
        back_btn = QPushButton(_tr('Back'))
        back_btn.setFixedWidth(70)
        back_btn.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px;")
        back_btn.setToolTip(_tr("Return to the main screen (dashboard)"))
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        self.title_label = QLabel(self.book_title)
        self.title_label.setObjectName('title')
        header.addWidget(self.title_label, 1)

        self.status_label = QLabel(_tr('Ready'))
        self.status_label.setObjectName('subtitle')
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # -----------------------------------------------------------------
        # 2. Advanced Settings Toolbar (Grouped)
        # -----------------------------------------------------------------
        settings_bar = QFrame()
        settings_bar.setObjectName('settingsBar')
        settings_bar.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 4px; min-height: 22px; }") 
        settings_layout = QHBoxLayout(settings_bar)
        settings_layout.setContentsMargins(8, 8, 8, 8)
        settings_layout.setSpacing(12)

        # A. Cache Status
        self.cache_btn = QPushButton(_tr("Enabled"))
        self.cache_btn.setObjectName("enabled_btn")
        self.cache_btn.setMinimumWidth(80)
        self.cache_btn.setCheckable(True)
        self.cache_btn.setChecked(self.config.get('cache_enabled', True))
        self._update_cache_btn_style()
        self.cache_btn.clicked.connect(self._on_cache_toggle)
        self.cache_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cache_btn.customContextMenuRequested.connect(self._on_cache_context_menu)
        settings_layout.addWidget(self._create_control_group(_tr("Cache Status:"), self.cache_btn))

        # B. Translation Engine
        self.engine_selector = QComboBox()
        self.engine_selector.setToolTip(_tr("Choose the translation engine (e.g. Google, Gemini, DeepL)"))
        from lingua.engines import builtin_engines
        for eng in builtin_engines:
            self.engine_selector.addItem(eng.name, eng.name)
        
        current_eng = self.config.get('translate_engine', 'Google(Free)New')
        idx = self.engine_selector.findData(current_eng)
        if idx >= 0: self.engine_selector.setCurrentIndex(idx)
        self.engine_selector.currentIndexChanged.connect(lambda i: self.config.set('translate_engine', self.engine_selector.itemData(i)))
        settings_layout.addWidget(self._create_control_group(_tr("Translation Engine:"), self.engine_selector))

        # C. Source Language
        self.src_lang_selector = QComboBox()
        self.src_lang_selector.setToolTip(_tr("Original language of the book (Auto detect recommended)"))
        self.src_lang_selector.setEditable(False)
        langs = ["Auto detect", "English", "Romanian", "French", "German", "Spanish", "Italian", "Chinese", "Japanese", "Korean", "Russian", "Portuguese", "Dutch", "Greek", "Turkish"]
        self.src_lang_selector.addItems(langs)
        src_val = self.config.get('source_lang', 'Auto detect')
        idx = self.src_lang_selector.findText(src_val)
        if idx >= 0: self.src_lang_selector.setCurrentIndex(idx)
        self.src_lang_selector.currentIndexChanged.connect(lambda i: self.config.set('source_lang', self.src_lang_selector.currentText()))
        settings_layout.addWidget(self._create_control_group(_tr("Source.Lang:"), self.src_lang_selector))

        # D. Target Language
        self.tgt_lang_selector = QComboBox()
        self.tgt_lang_selector.setToolTip(_tr("Language you want to translate the book into"))
        self.tgt_lang_selector.setEditable(False)
        self.tgt_lang_selector.addItems(langs[1:]) # Skip "Auto"
        idx = self.tgt_lang_selector.findText(self.config.get('target_lang', 'Romanian'))
        if idx >= 0: self.tgt_lang_selector.setCurrentIndex(idx)
        self.tgt_lang_selector.currentIndexChanged.connect(lambda i: self.config.set('target_lang', self.tgt_lang_selector.currentText()))
        settings_layout.addWidget(self._create_control_group(_tr("Target.Lang:"), self.tgt_lang_selector))

        # E. Translation Style
        self.style_selector = QComboBox()
        self.style_selector.setToolTip(_tr("Select the stylistic tone for translation (Literary, Technical, etc.)"))
        self.style_map = {_tr(k): v for k, v in TRANSLATION_STYLES.items()}
        self.style_selector.addItems(list(self.style_map.keys()))
        
        # Load current style (convert internal key back to friendly name if needed)
        current_internal = self.config.get('current_translation_style', 'literary')
        friendly_styles = {v: k for k, v in self.style_map.items()}
        current_friendly = friendly_styles.get(current_internal, _tr('Literary (Fiction)'))
        
        idx = self.style_selector.findText(current_friendly)
        if idx >= 0: self.style_selector.setCurrentIndex(idx)
        self.style_selector.currentIndexChanged.connect(self._on_style_changed)
        settings_layout.addWidget(self._create_control_group(_tr("Translation Style:"), self.style_selector))

        # F. Context Cache
        ctx_text = "⚡ " + _tr("Prompt Cache")
        ctx_btn = GatedButton(ctx_text, _tr("Gemini Context Cache"), self)
        ctx_btn.setMinimumWidth(110)
        ctx_btn.setToolTip(_tr("Manage memory/context for Gemini (Pro Feature)"))
        ctx_btn.clicked.connect(self._on_manage_context_cache)
        settings_layout.addWidget(self._create_control_group(_tr("API Cache"), ctx_btn))


        # G. Custom Ebook Title
        title_container = QWidget()
        title_row = QHBoxLayout(title_container)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)
        
        self.custom_title_enabled = QCheckBox()
        self.custom_title_enabled.setToolTip(_tr("Check to use a custom title in the exported EPUB file"))
        self.custom_title_enabled.setFixedWidth(24)
        self.custom_title_input = QLineEdit()
        self.custom_title_input.setToolTip(_tr("Enter the desired title for the translated book"))
        self.custom_title_input.setPlaceholderText(_tr("Enter custom title..."))
        self.custom_title_input.setText(self.book_title or "")
        self.custom_title_input.setMinimumWidth(150)
        
        title_row.addWidget(self.custom_title_enabled)
        title_row.addWidget(self.custom_title_input)
        
        settings_layout.addWidget(self._create_control_group(_tr("Custom Ebook Title (Optional):"), title_container))

        # H. After Completion
        after_box = QCheckBox(_tr("Shutdown PC when done"))
        after_box.setToolTip(_tr("Check to automatically shut down the computer after export is done"))
        after_box.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        settings_layout.addWidget(self._create_control_group(_tr("After Completion"), after_box))

        # I. Output Ebook
        output_box = QHBoxLayout()
        output_box.setSpacing(4)
        self.format_selector = QComboBox()
        self.format_selector.setToolTip(_tr("Choose the final export format (EPUB, PDF etc.)"))
        self.format_selector.addItems(["EPUB", "SRT", "TXT", "DOCX", "PDF", "AZW3", "MOBI"])
        self.format_selector.setMinimumWidth(65)
        self.export_btn = QPushButton(_tr("Output"))
        self.export_btn.setObjectName("output_btn")
        self.export_btn.setMinimumWidth(80)
        self.export_btn.setToolTip(_tr("Exportă cartea tradusă în formatul selectat (ex: EPUB)"))
        self.export_btn.clicked.connect(self._on_export_clicked)
        output_box.addWidget(self.format_selector)
        output_box.addWidget(self.export_btn)
        
        out_container = QWidget()
        out_container.setLayout(output_box)
        settings_layout.addWidget(self._create_control_group(_tr("Output"), out_container))

        settings_layout.addStretch()
        
        # WRAP IN SCROLL AREA (Responsive Fix - Phase 12)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setObjectName('settingsScroll')
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(settings_bar)
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Arrows indicate scroll now
        self.settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setFixedHeight(95)
        
        # Scroll Indicators (Phase 26) - Styled Arrows
        scroll_indicator_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: #888;
                font-size: 18px;
                padding: 0px;
                min-width: 24px;
            }
            QPushButton:hover { color: #fff; }
            QPushButton:disabled { color: #333; }
        """
        
        WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
        RES_PATH = f"{WORKSPACE_DIR}/resources"
        
        self.scroll_left_btn = QPushButton()
        self.scroll_left_btn.setIcon(QIcon(f"{RES_PATH}/chevron_left.svg"))
        self.scroll_left_btn.setStyleSheet(scroll_indicator_style)
        self.scroll_left_btn.setFixedWidth(24)
        self.scroll_left_btn.setVisible(False)
        self.scroll_left_btn.clicked.connect(lambda: self._scroll_settings(-200))

        self.scroll_right_btn = QPushButton()
        self.scroll_right_btn.setIcon(QIcon(f"{RES_PATH}/chevron_right.svg"))
        self.scroll_right_btn.setStyleSheet(scroll_indicator_style)
        self.scroll_right_btn.setFixedWidth(24)
        self.scroll_right_btn.setVisible(False)
        self.scroll_right_btn.clicked.connect(lambda: self._scroll_settings(200))

        scroll_layout = QHBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        scroll_layout.addWidget(self.scroll_left_btn)
        scroll_layout.addWidget(self.settings_scroll, 1)
        scroll_layout.addWidget(self.scroll_right_btn)
        
        self.settings_scroll.horizontalScrollBar().valueChanged.connect(self._update_scroll_buttons)
        # Also check on resize
        self.settings_scroll.installEventFilter(self)
        
        layout.addLayout(scroll_layout)

        # Trigger initial check
        QTimer.singleShot(100, self._update_scroll_buttons)

        # -----------------------------------------------------------------
        # 3. Intermediate Toolbar (Translate Options, Progress, Filter)
        # -----------------------------------------------------------------
        inter_bar = QHBoxLayout()
        inter_bar.setSpacing(12)
        
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        self.translate_btn = QPushButton(_tr('Translate Options ▾'))
        self.translate_btn.setObjectName('primary')
        self.translate_btn.setToolTip(_tr("Global options to start mass translation"))
        self.translate_btn.setFixedHeight(30)
        self.translate_btn.setFixedWidth(170)
        
        menu = QMenu(self.translate_btn)
        act_all = QAction(_tr("📚 Translate All Untranslated"), self)
        act_all.triggered.connect(lambda: self._start_translation(mode='all'))
        menu.addAction(act_all)
        act_sel = QAction(_tr("✅ Translate Selected"), self)
        act_sel.triggered.connect(lambda: self._start_translation(mode='selected'))
        menu.addAction(act_sel)
        act_one = QAction(_tr("⏬ Translate From Current"), self)
        act_one.triggered.connect(lambda: self._start_translation(mode='from_current'))
        menu.addAction(act_one)
        self.translate_btn.setMenu(menu)
        inter_bar.addWidget(self.translate_btn)

        self.stop_btn = QPushButton(_tr('Stop Translation'))
        self.stop_btn.setObjectName('danger_btn')
        self.stop_btn.setToolTip(_tr("Immediately stop the active translation process"))
        self.stop_btn.setFixedHeight(30)
        self.stop_btn.setMinimumWidth(120) # Increased width to prevent truncation ('rans)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_translation)
        inter_bar.addWidget(self.stop_btn)

        # Search/Filter Row (Moved to the left per user request)
        self.filter_category = QComboBox()
        self.filter_category.setToolTip(_tr("Filter displayed rows by status"))
        self.filter_category.addItem(_tr('All'), 'all')
        self.filter_category.addItem(_tr('Untranslated'), 'untranslated')
        self.filter_category.addItem(_tr('Translated'), 'translated')
        self.filter_category.addItem(_tr('Errors/Issues'), 'non_aligned')
        self.filter_category.currentIndexChanged.connect(self._apply_filters)
        self.filter_category.setFixedWidth(120)
        
        self.search_input = QLineEdit()
        self.search_input.setToolTip(_tr("Search specific text in original or translated rows"))
        self.search_input.setPlaceholderText(_tr('Search...'))
        self.search_input.setFixedWidth(150)
        self.search_input.textChanged.connect(self._apply_filters)
        
        inter_bar.addWidget(self.filter_category)
        inter_bar.addWidget(self.search_input)

        # Progress bar (Now middle-right, stretching)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #27272a; border-radius: 2px; border: none; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 2px; }
        """)
        inter_bar.addWidget(self.progress, 1)

        # Count label stays at the far right
        self.count_label = QLabel('0 paragraphs')
        self.count_label.setStyleSheet('color: #71717a; font-size: 11px;')
        inter_bar.addWidget(self.count_label)
        
        layout.addLayout(inter_bar)

        # Main Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # -----------------------------------------------------------------
        # Left Pane (Table + Toolbar)
        # -----------------------------------------------------------------
        table_pane = QWidget()
        table_pane.setMinimumWidth(250) # Allow shrinking
        table_layout = QVBoxLayout(table_pane)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(4)
        
        self.table = WorkspaceTable(self)
        table_layout.addWidget(self.table, 1)
        
        table_toolbar = QHBoxLayout()
        self.btn_delete = QPushButton("🗑 " + _tr("Delete"))
        self.btn_delete.setObjectName('danger_btn')
        self.btn_delete.setStyleSheet("font-size: 10px; padding: 2px 4px;")
        self.btn_delete.setToolTip(_tr("Delete selected rows (Irreversible operation in table)"))
        self.btn_detected_terms = QPushButton("🏷 " + _tr("Detected Terms"))
        self.btn_detected_terms.setStyleSheet("font-size: 10px; padding: 2px 4px;")
        self.btn_detected_terms.setToolTip(_tr("Show detected terms associated with selection for glossary"))
        
        table_toolbar.addWidget(self.btn_delete)
        table_toolbar.addWidget(self.btn_detected_terms)
        table_toolbar.addStretch()
        
        # Add the existing translation buttons here? User wanted them here.
        # But we already have them at the top. I'll just add the ones they explicitly asked for at the bottom.
        # Actually I will move self.translate_btn here! Let me do that later.
        table_layout.addLayout(table_toolbar)
        self.main_splitter.addWidget(table_pane)

        # -----------------------------------------------------------------
        # Right Pane (Tabs)
        # -----------------------------------------------------------------
        from PySide6.QtWidgets import QTabWidget, QPlainTextEdit, QSizePolicy
        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName('workspaceTabs')
        self.right_tabs.setMinimumWidth(250) # Allow shrinking
        self.right_tabs.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # TAB 1: Review (Editors + Toolbar)
        editor_pane = QWidget()
        editor_layout = QVBoxLayout(editor_pane)
        editor_layout.setContentsMargins(4, 4, 4, 4)
        editor_layout.setSpacing(4)
        
        # --- Phase 8: Re-Chunk Panel (Moved to Review Tab for visibility) ---
        self.rechunk_panel = QGroupBox(_tr('🔄 Re-Chunk Selected Rows'))
        self.rechunk_panel.setObjectName('rechunkPanel')
        # Allow the panel to shrink
        self.rechunk_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        rechunk_layout = QVBoxLayout(self.rechunk_panel)
        rechunk_layout.setContentsMargins(6, 4, 6, 4)
        rechunk_layout.setSpacing(4)
        
        top_row = QHBoxLayout()
        bottom_row = QHBoxLayout()

        self.btn_rechunk_merge = QPushButton(_tr('🔗 Merge Selected'))
        self.btn_rechunk_merge.setObjectName('output_btn')
        self.btn_rechunk_merge.setToolTip(_tr('Merge 2-5 selected rows into one.'))
        self.btn_rechunk_merge.clicked.connect(self._on_rechunk_merge)
        self.btn_rechunk_merge.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self.btn_rechunk_merge)
        
        # Add stretch between the two main action buttons
        top_row.addStretch()

        self.btn_rechunk_resplit = QPushButton(_tr('🔄 Re-Split & Translate'))
        self.btn_rechunk_resplit.setObjectName('output_btn')
        self.btn_rechunk_resplit.setToolTip(_tr('Re-split the selected row and re-translate the new chunks.'))
        self.btn_rechunk_resplit.clicked.connect(self._on_rechunk_resplit)
        self.btn_rechunk_resplit.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self.btn_rechunk_resplit)
        
        # Bottom row for split configuration
        bottom_row.addStretch()

        lbl_method = QLabel(_tr('Split method:'))
        lbl_method.setObjectName('subtitle')
        lbl_method.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        bottom_row.addWidget(lbl_method)
        
        self.rechunk_method = QComboBox()
        self.rechunk_method.addItem('Merge (custom chars)', 'merge')
        self.rechunk_method.addItem('Content Aware', 'chapter_aware')
        self.rechunk_method.addItem('Per File', 'per_file')
        self.rechunk_method.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        bottom_row.addWidget(self.rechunk_method)

        lbl_chars = QLabel(_tr('Max chars:'))
        lbl_chars.setObjectName('subtitle')
        lbl_chars.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        bottom_row.addWidget(lbl_chars)
        
        self.rechunk_chars = QSpinBox()
        self.rechunk_chars.setRange(2000, 30000)
        self.rechunk_chars.setSingleStep(1000)
        self.rechunk_chars.setValue(13000)
        self.rechunk_chars.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        bottom_row.addWidget(self.rechunk_chars)

        rechunk_layout.addLayout(top_row)
        rechunk_layout.addLayout(bottom_row)

        self.rechunk_panel.hide() # Hidden by default to save vertical space
        editor_layout.addWidget(self.rechunk_panel)

        self.editor_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 0. Raw HTML Text
        self.raw_text = CodeEditor()
        self.raw_text.setReadOnly(True)
        self.raw_text.setPlaceholderText(_tr('HTML Code/Raw Source...'))
        self.editor_splitter.addWidget(self.raw_text)
        self.raw_text.hide()
        
        # 1. Original Text
        self.original_text = SourceTextEditor(self)
        self.original_text.setReadOnly(True)
        self.original_text.setPlaceholderText(_tr('Select a row to see the original text...'))
        self.editor_splitter.addWidget(self.original_text)
        
        # 2. Translation Text
        self.translation_text = TranslationEditor(self)
        self.translation_text.setPlaceholderText(_tr('Select a row to edit the translation...'))
        self.editor_splitter.addWidget(self.translation_text)
        
        # 3. Alignment Report (CP11.e)
        self.alignment_report = QPlainTextEdit()
        self.alignment_report.setReadOnly(True)
        self.alignment_report.setPlaceholderText(_tr('Alignment report...'))
        self.alignment_report.setObjectName('logConsole')
        self.editor_splitter.addWidget(self.alignment_report)
        self.alignment_report.hide() # Hidden by default per user request
        
        editor_layout.addWidget(self.editor_splitter, 1)
        
        # Editor Toolbar
        from PySide6.QtWidgets import QRadioButton
        editor_toolbar = QHBoxLayout()
        self.radio_untranslated = QRadioButton(_tr("Untranslated"))
        self.radio_untranslated.setEnabled(False) # Indicator
        self.check_allow_block = QCheckBox(_tr("Allow block replacement"))
        self.check_allow_block.setToolTip(_tr("If checked, overwrites all text during massive operations"))
        self.btn_save = QPushButton(_tr("Save"))
        self.btn_save.setToolTip(_tr("Forcibly save manual changes in translated text"))
        
        self.btn_toggle_rechunk = QPushButton(_tr("🛠 Unelte Aliniere"))
        self.btn_toggle_rechunk.setCheckable(True)
        self.btn_toggle_rechunk.setToolTip(_tr("Show/Hide the merge and split panel (Merge/Split)"))
        self.btn_toggle_rechunk.clicked.connect(self._on_toggle_rechunk)
        
        editor_toolbar.addWidget(self.radio_untranslated)
        editor_toolbar.addWidget(self.check_allow_block)
        editor_toolbar.addStretch()
        editor_toolbar.addWidget(self.btn_toggle_rechunk)
        editor_toolbar.addWidget(self.btn_save)
        
        editor_layout.addLayout(editor_toolbar)
        self.right_tabs.addTab(editor_pane, _tr("Review"))
        
        # TAB 2: Log
        log_pane = QWidget()
        log_layout = QVBoxLayout(log_pane)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_text_edit = QPlainTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setObjectName('logConsole')
        log_layout.addWidget(self.log_text_edit)
        self.right_tabs.addTab(log_pane, _tr("Log"))
        
        # TAB 3: Errors
        error_pane = QWidget()
        error_layout = QVBoxLayout(error_pane)
        error_layout.setContentsMargins(0, 0, 0, 0)
        self.error_text_edit = QPlainTextEdit()
        self.error_text_edit.setReadOnly(True)
        self.error_text_edit.setObjectName('errorConsole')
        error_layout.addWidget(self.error_text_edit)
        self.right_tabs.addTab(error_pane, _tr("Errors"))
        
        self.main_splitter.addWidget(self.right_tabs)
        
        # Set Splitter proportions and flexibility
        self.main_splitter.setOpaqueResize(True)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setSizes([450, 550])
        
        self.editor_splitter.setOpaqueResize(True)
        self.editor_splitter.setChildrenCollapsible(False)
        self.editor_splitter.setSizes([150, 200, 200, 100])
        
        layout.addWidget(self.main_splitter, 1)

        # -----------------------------------------------------------------
        # Global Footer
        # -----------------------------------------------------------------
        global_footer = QHBoxLayout()
        self.footer_stats = QLabel("Total items: 0/0 · Character count: 0/0 · Non-aligned items: 0")
        self.footer_stats.setObjectName('subtitle')
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #3b82f6; font-size: 11px; margin-left: 10px;")
        
        global_footer.addWidget(self.footer_stats)
        global_footer.addWidget(self.status_label)
        global_footer.addStretch()
        
        author_label = QLabel('<span style="color:crimson;">♥</span> By ManuX')
        author_label.setObjectName('subtitle')
        global_footer.addWidget(author_label)
        
        layout.addLayout(global_footer)
        
        # Connect signals for Split View Editors
        self.table.row_selected.connect(self._on_table_selection_changed)
        self.table.row_double_clicked.connect(self._on_row_double_clicked) # Renamed handler
        self.table.translate_requested.connect(self._on_translate_requested)
        self.table.merge_requested.connect(self._on_merge_requested)
        self.table.split_requested.connect(self._on_split_requested)
        self.table.align_requested.connect(self._on_align_requested) # New signal
        self.table.delete_requested.connect(self._on_delete_requested) # New signal
        
        # Synchronize scrollbars
        self.original_text.verticalScrollBar().valueChanged.connect(
            self.translation_text.verticalScrollBar().setValue)
        self.translation_text.verticalScrollBar().valueChanged.connect(
            self.original_text.verticalScrollBar().setValue)
            
        self.raw_text.verticalScrollBar().valueChanged.connect(
            self.original_text.verticalScrollBar().setValue)
        self.original_text.verticalScrollBar().valueChanged.connect(
            self.raw_text.verticalScrollBar().setValue)
            
        # Connect text changes to auto-save
        self.translation_text.textChanged.connect(self._on_translation_edited)

        # Connect Context Menu Translation Callbacks (Phase 14)
        self.original_text.setTranslationCallback(self._on_editor_translate)
        self.translation_text.setTranslationCallback(self._on_editor_translate)

    def _update_cache_btn_style(self):
        """Update the appearance of the cache button based on its state."""
        if self.cache_btn.isChecked():
            self.cache_btn.setText("Enabled")
            self.cache_btn.setObjectName("enabled_btn")
        else:
            self.cache_btn.setText("Disabled")
            self.cache_btn.setObjectName("")
        
        # Force re-evaluation of the stylesheet matches
        self.cache_btn.style().unpolish(self.cache_btn)
        self.cache_btn.style().polish(self.cache_btn)

    def _on_cache_toggle(self):
        """Toggle the cache setting in config."""
        enabled = self.cache_btn.isChecked()
        self.config.set('cache_enabled', enabled)
        self._update_cache_btn_style()
        self.status_label.setText(f"Cache {'enabled' if enabled else 'disabled'}")

    def _on_cache_context_menu(self, pos):
        """Show context menu for cache button."""
        menu = QMenu(self)
        open_action = QAction("📂 Open Cache Folder", self)
        open_action.triggered.connect(self._open_cache_folder)
        menu.addAction(open_action)
        menu.exec_(self.cache_btn.mapToGlobal(pos))

    def _open_cache_folder(self):
        """Open the system cache directory in file explorer."""
        if os.path.exists(CACHE_DIR):
            QDesktopServices.openUrl(QUrl.fromLocalFile(CACHE_DIR))
        else:
            QMessageBox.warning(self, _tr("Attention"), f"Directorul de cache nu există: {CACHE_DIR}")

    def _on_manage_context_cache(self):
        """Show a dialog for managing session/context cache."""
        engine_name = self.engine_selector.currentText()
        dlg = CacheDialog(self, self.epub_path, self.book_title, engine_name)
        dlg.exec_()
        

    def _on_toggle_rechunk(self):
        """Hide/Show the re-chunk groupbox panel and the alignment report."""
        show = self.btn_toggle_rechunk.isChecked()
        self.rechunk_panel.setVisible(show)
        self.alignment_report.setVisible(show)
        if show:
            self.btn_toggle_rechunk.setText(_tr("🛠 Ascunde Unelte"))
            # Adjust splitter to give some space to the report
            self.editor_splitter.setSizes([200, 200, 100])
        else:
            self.btn_toggle_rechunk.setText(_tr("🛠 Unelte Aliniere"))


    def _on_style_changed(self):
        """Save the chosen translation style to config."""
        friendly_text = self.style_selector.currentText()
        internal_key = self.style_map.get(friendly_text, 'literary')
        self.config.set('current_translation_style', internal_key)
        self.status_label.setText(_tr('Style changed: {0}').format(friendly_text))

    def _apply_filters(self):
        """Filter table rows based on category and search text."""
        category = self.filter_category.currentData()
        keyword = self.search_input.text().lower()
        
        # Batch hide/show rows for performance
        for i, p in enumerate(self.elements):
            cat_match = True
            if category == 'untranslated':
                cat_match = not p.translation
            elif category == 'translated':
                cat_match = bool(p.translation)
            elif category == 'non_aligned':
                # Aligned could be False. Or incomplete could be True. We treat both as issues.
                aligned = getattr(p, 'aligned', True)
                incomplete = getattr(p, 'incomplete', False)
                cat_match = bool(p.translation) and (not aligned or incomplete)
                
            key_match = True
            if keyword:
                orig = (p.original or '').lower()
                trans = (p.translation or '').lower()
                key_match = keyword in orig or keyword in trans
                
            self.table.setRowHidden(i, not (cat_match and key_match))

    def _load_from_cache(self):
        """Populate the table directly from cache (Review Mode)."""
        from lingua.core.cache import get_cache
        self.cache = get_cache(self.uid)
        
        paragraphs = self.cache.all_paragraphs(include_ignored=True)
        
        # Mock context for _on_extraction_done
        context = {
            'paragraphs': paragraphs,
            'cache': self.cache,
            'book': None,
            'pages': [],
            'element_handler': None
        }
        self._on_extraction_done(context)
        
        # Override ready status
        self.status_label.setText(_tr("Review Mode (No EPUB)"))
        self.status_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        self.export_btn.setDisabled(True)
        self.export_btn.setToolTip(_tr("Export is disabled in Review Mode (source EPUB missing)"))

    def _start_extraction(self):
        """Extract EPUB in background thread."""
        thread = QThread(self)
        self._threads.append(thread)
        
        worker = ExtractionWorker(self.epub_path)
        self._workers.append(worker)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_extraction_done)
        worker.error.connect(self._on_extraction_error)
        
        # Cleanup
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(thread.deleteLater)

        self.status_label.setText(_tr('Extracting...'))
        thread.start()

    def _on_extraction_done(self, context):
        """Called when ExtractionWorker finishes paragraph extraction."""
        print(f"DEBUG UI: _on_extraction_done received. Items: {len(context.get('paragraphs', []))}", flush=True)
        self.status_label.setText(_tr('Ready'))
        self.context = context
        self.book = context.get('book')
        self.pages = context.get('pages')
        self.element_handler = context.get('element_handler')
        self.cache = context.get('cache')
        self.elements = context.get('paragraphs', [])
        
        self.table.populate(self.elements)

        self.count_label.setText(f'{len(self.elements)} paragraphs')
        self.status_label.setText('Ready')
        self.translate_btn.setEnabled(True)
        self.export_btn.setEnabled(not self.review_mode)
        self.progress.setValue(0)
        self._apply_filters()
        self._update_footer_stats()

    def _on_extraction_error(self, error_msg):
        self.status_label.setText(_tr('Extraction failed'))
        self.error_text_edit.appendPlainText(f"EXTRACTION ERROR:\n{error_msg}\n")
        QMessageBox.critical(self, _tr('Extraction Error'), error_msg)

    def _start_translation(self, mode='all'):
        """Start or Resume translation via background TranslationWorker."""
        print(f"DEBUG APP: _start_translation called with mode={mode}", flush=True)
        # Determine which elements to translate based on mode
        if mode == 'all':
            untranslated = [p for p in self.elements if not p.translation and not p.ignored]
        elif mode == 'selected':
            selected_rows = list(set([item.row() for item in self.table.selectedItems()]))
            selected_rows.sort()
            untranslated = [self.elements[r] for r in selected_rows if r < len(self.elements) and not self.elements[r].translation and not self.elements[r].ignored]
            if not selected_rows:
                print("DEBUG APP: No selected rows", flush=True)
                QMessageBox.warning(self, _tr("Attention"), _tr("No rows selected for translation!"))
                return
        elif mode == 'from_current':
            current_row = self.table.currentRow()
            if current_row < 0:
                print("DEBUG APP: No current row", flush=True)
                QMessageBox.warning(self, _tr("Attention"), _tr("No starting row selected!"))
                return
            untranslated = [p for p in self.elements[current_row:] if not p.translation and not p.ignored]
        else:
            untranslated = []

        if not untranslated:
            print("DEBUG APP: Untranslated array is empty!", flush=True)
            QMessageBox.information(self, _tr("Translation"), _tr("All paragraphs in selection are already translated!"))
            return
            
        print(f"DEBUG APP: Found {len(untranslated)} items. Starting worker thread!", flush=True)

        # 1. UI Setup
        self.translate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText(_tr('Translating {n} items...').format(n=len(untranslated)))
        
        # Auto-switch to Log tab so user sees what is happening
        self.right_tabs.setCurrentIndex(1)
        
        # We want the progress bar to reflect ONLY the remaining chunk
        print(f"DEBUG UI: _start_translation initiating mode={mode} for {len(untranslated)} items", flush=True)
        self.progress.setRange(0, len(untranslated))
        self.progress.setValue(0)

        # 2. Re-read preferred engine from config safely
        engine_name = self.config.get('translate_engine', 'Google(Free)')
        
        # 3. Create the background Thread and Worker
        thread = QThread(self)
        self._threads.append(thread)
        
        worker = TranslationWorker(
            elements=untranslated, 
            engine_name=engine_name,
            source_lang=self.config.get('source_lang', 'Auto'),
            target_lang=self.config.get('target_lang', 'Romanian')
        )
        # Store worker reference to prevent GC and for signaling
        self.trans_worker = worker 
        self._workers.append(worker)
        worker.moveToThread(thread)

        # 4. Connect Signals (Worker -> UI)
        thread.started.connect(worker.run)
        
        worker.progress_updated.connect(self._on_trans_progress)
        worker.row_completed.connect(self._on_row_completed)
        worker.error_occurred.connect(self._on_trans_error)
        worker.log_message.connect(self._on_trans_log_message)
        
        # Cleanup
        worker.finished.connect(self._on_trans_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(thread.deleteLater)

        # 5. Start Execution
        thread.start()

    def _on_trans_log_message(self, msg):
        """Append log messages from background worker to the Log tab."""
        print(f"DEBUG UI: Received Log Signal: {msg[:100]}...", flush=True)
        self.log_text_edit.appendPlainText(msg)

    def _on_trans_progress(self, current, total):
        """Update progress bar safely from main thread."""
        self.progress.setValue(current)

    def _on_row_completed(self, paragraph, status):
        """Update a specific row in the table when translation arrives from background."""
        print(f"DEBUG UI: _on_row_completed received for paragraph.id={paragraph.id}, status={status}", flush=True)
        p = paragraph
        
        # Guard removed: we allow updates from any worker (batch or ad-hoc)
        
        if status == 'done' or status == 'cached':
            p.aligned = True
            p.error = None
            if hasattr(self, 'cache') and self.cache:
                self.cache.update_paragraph(p)
        elif status == 'error':
            p.aligned = False

        # Delegate UI repaint to WorkspaceTable on EVERY status change
        absolute_row = getattr(p, 'row', -1)
        if absolute_row != -1:
            self.table.update_row(absolute_row)
            
            # Live update Editor if the currently selected row finished translating
            if self.table.currentRow() == absolute_row:
                self.translation_text.blockSignals(True)
                self.translation_text.setPlainText(p.translation or '')
                self._update_alignment_report(p)
                self.translation_text.blockSignals(False)

                # Auto-scroll gently to keep progress visible
                if absolute_row % 3 == 0:
                    item = self.table.item(absolute_row, 2)
                    if item:
                        self.table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_trans_error(self, error_msg):
        """Handle worker errors."""
        self.error_text_edit.appendPlainText(f"TRANSLATION ERROR:\n{error_msg}\n")
        QMessageBox.critical(self, 'Translation Error', error_msg)

    def _on_trans_finished(self):
        """Reset buttons when processing is complete or cancelled."""
        self.stop_btn.setEnabled(False)
        self.translate_btn.setEnabled(True)
        self.status_label.setText(_tr('Stopping...') if getattr(self, 'trans_worker', None) and self.trans_worker._is_canceled else _tr('Ready'))
        self.export_btn.setEnabled(True)

    def _stop_translation(self):
        """Stop translation by sending cancel signal to background worker."""
        self.status_label.setText('Stopping gracefully...')
        self.stop_btn.setEnabled(False)
        if hasattr(self, 'trans_worker'):
            self.trans_worker.cancel()

    def _on_export_clicked(self):
        """Handle output button click — generic for multiple formats."""
        try:
            if not hasattr(self, 'cache') or not self.cache:
                QMessageBox.warning(self, _tr("Error"), _tr("Cache is not active. Cannot export."))
                return

            selected_format = self.format_selector.currentText().upper().strip()

            # 1. Check for supported formats
            allowed_formats = ["EPUB", "SRT", "TXT", "DOCX", "PDF", "AZW3", "MOBI"]
            if selected_format not in allowed_formats:
                QMessageBox.information(
                    self, _tr("Format Not Supported"),
                    _tr("Export to {fmt} is not implemented yet.").format(fmt=selected_format)
                )
                return

            # 2. Prepare default filename
            try:
                from lingua.core.conversion import sanitize_file_name
                import os
                
                base_title = getattr(self, 'book_title', 'unknown')
                epub_path = getattr(self, 'epub_path', '')
                
                if hasattr(self, 'custom_title_enabled') and self.custom_title_enabled.isChecked():
                    base_title = self.custom_title_input.text()
                
                clean_title = sanitize_file_name(base_title)
                target_ext = selected_format.lower()
                default_name = f"{os.path.splitext(clean_title)[0]}_{self.config.get('target_lang', 'ro')}.{target_ext}"
                
                # 3. Determine save location (Automated if configured)
                from PySide6.QtWidgets import QFileDialog
                config_path = self.config.get('output_path')
                
                if config_path and os.path.isdir(config_path):
                    # Automated export to pre-configured folder
                    output_path = os.path.join(config_path, default_name)
                else:
                    # Fallback to dialog (using non-native to avoid Windows hangs)
                    suggested_dir = os.path.dirname(epub_path) if epub_path else os.path.expanduser("~")
                    suggested_path = os.path.join(suggested_dir, default_name)
                    filter_str = f"{selected_format} Files (*.{target_ext})"
                    
                    output_path, _ext_filter = QFileDialog.getSaveFileName(
                        self, 
                        _tr("Save Translated {fmt}").format(fmt=selected_format), 
                        suggested_path, 
                        filter_str,
                        options=QFileDialog.DontUseNativeDialog
                    )
            except Exception as e:
                QMessageBox.critical(self, _tr("Export Error"), _tr("Failed to prepare export: {err}").format(err=str(e)))
                return

            if not output_path:
                return  # User cancelled

            # Lock UI
            self.export_btn.setEnabled(False)
            self.translate_btn.setEnabled(False)
            self.status_label.setText(_tr('Exporting {fmt}...').format(fmt=selected_format))
            self.progress.setValue(0)

            # Start Export Worker
            thread = QThread(self)
            self._threads.append(thread)
            
            worker = ExportWorker(self.epub_path, output_path, self.cache, format=selected_format)
            self._workers.append(worker)
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            
            # Connect Progress & Signals
            def update_progress(pct, msg):
                self.progress.setValue(pct)
                self.status_label.setText(msg)
                
            worker.progress.connect(update_progress)
            worker.error.connect(self._on_export_error)
            worker.finished.connect(self._on_export_done)
            
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)

            thread.start()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Critical Error", f"App crash prevented. Error: {e}")

    def _on_export_error(self, error_msg):
        self.export_btn.setEnabled(True)
        self.translate_btn.setEnabled(True)
        self.status_label.setText(_tr('Export Failed'))
        self.error_text_edit.appendPlainText(f"EXPORT ERROR:\n{error_msg}\n")
        QMessageBox.critical(self, _tr('Export Error'), _tr("An error occurred while generating the file:") + f"\n\n{error_msg}")

    def _on_export_done(self, output_path):
        self.export_btn.setEnabled(True)
        self.translate_btn.setEnabled(True)
        self.status_label.setText(_tr('Export Complete'))
        self.progress.setValue(100)
        
        from PySide6.QtWidgets import QMessageBox
        from lingua.core.utils import open_path
        
        msg = _tr("The book has been successfully exported to:") + f"\n{output_path}\n\n" + _tr("Do you want to open the translated archive now?")
        reply = QMessageBox.question(
            self, _tr('Export Finished'), msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            open_path(output_path)

    def _on_row_double_clicked(self, row):
        """Toggle raw HTML editor visibility on double click."""
        if self.raw_text.isVisible():
            self.raw_text.hide()
        else:
            self.raw_text.show()
            # Restore relative sizes
            self.editor_splitter.setSizes([150, 200, 200])

    def _on_table_selection_changed(self, row):
        """Update the side editors when a row is selected in the table."""
        # Stop any ongoing translation auto-save from triggering
        self.translation_text.blockSignals(True)
        
        paragraphs = self.table.get_selected_paragraphs()
        count = len(paragraphs)
        
        # Dynamic Visibility for Re-Chunk Panel (Phase 8)
        # Increased limit for merge to be more permissive (e.g. 50 chunks)
        can_merge = 2 <= count <= 50
        orig_len = 0
        if count == 1 and paragraphs[0].original:
            orig_len = len(paragraphs[0].original)
        
        # Lowered threshold for split to 500 chars
        can_split = count == 1 and orig_len > 500
        
        # Dynamic Visibility (Phase 8): 
        # Respect the toggle button state (user requested hidden by default)
        self.rechunk_panel.setVisible(self.btn_toggle_rechunk.isChecked())
        
        if can_merge:
            self.btn_rechunk_merge.setEnabled(True)
            text_merge = _tr('🔗 Merge Selected')
            self.btn_rechunk_merge.setText(f'{text_merge} ({count})')
            self.btn_rechunk_resplit.setEnabled(False)
            self.rechunk_method.setEnabled(False)
            self.rechunk_chars.setEnabled(False)
        elif can_split:
            self.btn_rechunk_merge.setEnabled(False)
            self.btn_rechunk_merge.setText(_tr('🔗 Merge Selected'))
            self.btn_rechunk_resplit.setEnabled(True)
            self.rechunk_method.setEnabled(True)
            self.rechunk_chars.setEnabled(True)
        else:
            self.btn_rechunk_merge.setEnabled(False)
            self.btn_rechunk_merge.setText(_tr('🔗 Merge Selected'))
            self.btn_rechunk_resplit.setEnabled(False)
            self.rechunk_method.setEnabled(False)
            self.rechunk_chars.setEnabled(False)

        if row < 0 or row >= len(self.elements):
            self.raw_text.clear()
            self.original_text.clear()
            self.translation_text.clear()
            self.alignment_report.clear()
            self.translation_text.blockSignals(False)
            return
            
        p = self.elements[row]
        self.raw_text.setPlainText(p.raw or p.original or '')
        self.original_text.setPlainText(p.original or '')
        self.translation_text.setPlainText(p.translation or '')
        self.translation_text.current_paragraph = p # Reference for auto-save
        
        # Determine status indicator (Red for error, Yellow for alignment)
        if p.translation:
            self.radio_untranslated.setChecked(False)
        else:
            self.radio_untranslated.setChecked(True)
            
        self._update_alignment_report(p)
        self.translation_text.blockSignals(False)

    def _update_alignment_report(self, p):
        """Update the alignment report text area for the given paragraph."""
        if not p.translation:
            self.alignment_report.setPlainText(_tr("Status: Untranslated"))
            return
            
        # Get engine separator from config or default
        engine_name = p.engine_name or self.config.get('translate_engine', 'Google(Free)New')
        from lingua.core.translation import get_engine_class
        engine_class = get_engine_class(engine_name)
        separator = getattr(engine_class, 'separator', '\n\n')
        
        details = p.alignment_details(separator)
        lines = []
        lines.append(_tr("🔍 ALIGNMENT REPORT (Row {n})").format(n=p.row + 1))
        lines.append("-" * 30)
        lines.append(_tr("Status: ✅ Aligned") if details['aligned'] else _tr("Status: ⚠️ Not Aligned"))
        lines.append(_tr("Original Segments:") + f" {details['orig_count']}")
        lines.append(_tr("Translated Segments:") + f" {details['trans_count']}")
        
        if details['missing']:
            lines.append(_tr("❌ Missing segments (index):") + f" {', '.join(map(str, details['missing']))}")
        if details['suspicious']:
            lines.append(_tr("🧐 Suspiciously short segments (index):") + f" {', '.join(map(str, details['suspicious']))}")
            
        self.alignment_report.setPlainText("\n".join(lines))

    def _on_translate_requested(self, paragraphs):
        """Perform ad-hoc translation on specific paragraphs."""
        engine_name = self.config.get('translate_engine', 'Google(Free)')
        thread = QThread(self)
        self._threads.append(thread)
        
        worker = TranslationWorker(
            elements=paragraphs, 
            engine_name=engine_name,
            source_lang=self.config.get('source_lang', 'Auto'),
            target_lang=self.config.get('target_lang', 'Romanian')
        )
        self.trans_worker = worker # Set reference so UI knows we are active
        self._workers.append(worker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        
        worker.progress_updated.connect(self._on_trans_progress)
        worker.row_completed.connect(self._on_row_completed)
        worker.error_occurred.connect(self._on_trans_error)
        worker.log_message.connect(self._on_trans_log_message)
        
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(thread.deleteLater)

        # UI statuses
        self.progress.setRange(0, len(paragraphs))
        self.progress.setValue(0)
        self.status_label.setText(_tr('Translating {n} items...').format(n=len(paragraphs)))
        thread.start()

    # Combined single handler for split

    def _on_align_requested(self, paragraph):
        """Open the alignment dialog for manual segment-level mapping."""
        if not LicenseManager.is_pro():
            show_pro_required_dialog(self, _tr("Manual Alignment"))
            return

        from lingua.core.translation import get_engine_class, get_translator
        from lingua.ui.widgets.alignment_dialog import AlignmentDialog

        engine_name = getattr(paragraph, 'engine_name', self.engine_selector.currentText())
        engine = get_engine_class(engine_name)
        sep = getattr(engine, 'separator', '\n\n')
        
        # Create a transient translator for per-segment actions
        translator = None
        try:
            translator = get_translator()
            translator.set_source_lang(self.config.get('source_lang', 'Auto'))
            translator.set_target_lang(self.config.get('target_lang', 'Romanian'))
        except Exception: pass
            
        dlg = AlignmentDialog(self, paragraph, sep, cache=self.cache, translator=translator)
        if dlg.exec_():
            self.table.update_row(paragraph.row)
            self.status_label.setText(_tr("Alignment saved for row {n}").format(n=paragraph.row + 1))

    def _on_delete_requested(self, paragraphs):
        """Delete selected paragraphs from the workspace and cache."""
        for p in paragraphs:
            if p in self.elements:
                self.elements.remove(p)
                # Mark as ignored in cache if possible
                if self.cache:
                    p.ignored = True
                    self.cache.update_paragraph(p)
        
        # Re-populate table to reflect changes
        self.table.populate(self.elements)
        self.status_label.setText(_tr("Deleted {n} rows.").format(n=len(paragraphs)))

    def _on_merge_requested(self, paragraphs):
        """Merge selected paragraphs into one."""
        if len(paragraphs) < 2: return
        
        if not hasattr(self, 'cache') or not self.cache:
            QMessageBox.warning(self, _tr("Error"), _tr("Cache is not active. Cannot export.")) # Using existing key
            return

        paragraphs.sort(key=lambda p: p.row)
        
        separator = '\n\n'
        combined_original = separator.join(p.original or '' for p in paragraphs)
        combined_raw = separator.join(p.raw or p.original or '' for p in paragraphs)
        
        trans_texts = [p.translation for p in paragraphs if p.translation]
        combined_trans = separator.join(trans_texts) if trans_texts else None
        
        # Base ID off the max ID to prevent collisions
        new_id = max(p.id for p in paragraphs) + 1000
        new_md5 = uid(f"{new_id}{combined_original}")
        
        from lingua.core.cache import Paragraph
        merged = Paragraph(
            id=new_id, 
            md5=new_md5, 
            raw=combined_raw,
            original=combined_original, 
            ignored=False,
            attributes=paragraphs[0].attributes, 
            page=paragraphs[0].page
        )
        merged.translation = combined_trans
        merged.aligned = True
        merged.error = None
        
        # Safe replacement in DB
        old_ids = [p.id for p in paragraphs]
        self.cache.replace_paragraphs(old_ids, [merged])
        
        # Replace in memory
        first_idx = paragraphs[0].row
        for p in reversed(paragraphs):
            if p.row < len(self.elements):
                del self.elements[p.row]
            
        self.elements.insert(first_idx, merged)
        
        # Reflect in UI
        self.table.populate(self.elements)
        self.table.selectRow(first_idx)
        self.count_label.setText(f'{len(self.elements)} paragraphs')

    def _on_split_requested(self, paragraph):
        """Split a row automatically by newline."""
        if not hasattr(self, 'cache') or not self.cache: return
        
        if '\n' in (paragraph.original or ''):
            orig_parts = paragraph.original.split('\n')
            raw_parts = paragraph.raw.split('\n') if paragraph.raw and '\n' in paragraph.raw else orig_parts
            
            msg = _tr("I split the row into {n} segments (by newline). Translation must be redone on new chunks.").format(n=len(orig_parts))
            QMessageBox.information(self, _tr("Split Performed"), msg)
            
            new_paragraphs = []
            from lingua.core.cache import Paragraph
            base_id = paragraph.id
            
            for i, (orig, raw) in enumerate(zip(orig_parts, raw_parts)):
                if not orig.strip(): continue
                nid = base_id + i + 10000
                nmd5 = uid(f"{nid}{orig}")
                # Creates a clean paragraph with no translation so we can re-translate
                np = Paragraph(id=nid, md5=nmd5, raw=raw, original=orig, page=paragraph.page, attributes=paragraph.attributes)
                new_paragraphs.append(np)
                
            if new_paragraphs:
                self.cache.replace_paragraphs([paragraph.id], new_paragraphs)
                
                idx = paragraph.row
                del self.elements[idx]
                for p in reversed(new_paragraphs):
                    self.elements.insert(idx, p)
                    
                self.table.populate(self.elements)
                self.table.selectRow(idx)
                self.count_label.setText(f'{len(self.elements)} paragraphs')
        else:
            QMessageBox.warning(self, _tr("Split Impossible"), _tr("This paragraph does not contain line breaks (Enter). Manual split will be added later."))

    def _on_translation_edited(self):
        """Auto-save user edits from the right panel to the paragraph and cache."""
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.elements):
            p = self.elements[current_row]
            
            # Verify we are editing the currently selected paragraph
            if self.translation_text.current_paragraph == p:
                new_text = self.translation_text.toPlainText()
                
                # Check if text actually changed (avoids loop)
                if new_text != p.translation:
                    p.translation = new_text
                    p.aligned = True
                    p.error = None
                    
                    # Update cache DB
                    if hasattr(self, 'cache') and self.cache:
                        self.cache.update_paragraph(p)
                        
                    # Repaint row via WorkspaceTable safely
                    self.table.blockSignals(True)
                    self.table.update_row(current_row)
                    self.table.blockSignals(False)

    def _update_footer_stats(self):
        """Update the bottom global footer with translation statistics."""
        if not hasattr(self, 'elements'): return
        
        total_rows = len(self.elements)
        current_row = self.table.currentRow() + 1 if self.table.currentRow() >= 0 else 0
        
        tot_chars = sum(len(p.original or '') for p in self.elements)
        trans_chars = sum(len(p.original or '') for p in self.elements if p.translation)
        
        non_aligned = sum(1 for p in self.elements if p.translation and (not getattr(p, 'aligned', True) or getattr(p, 'incomplete', False)))
        
        self.footer_stats.setText(f"Total items: {current_row}/{total_rows} · Character count: {trans_chars}/{tot_chars} · Non-aligned items: {non_aligned}")

    # -----------------------------------------------------------------
    # Re-Chunking Methods (Phase 8)
    # -----------------------------------------------------------------
    def _on_rechunk_merge(self):
        """Combine 2-5 selected rows into a single one."""
        selected = self.table.get_selected_paragraphs()
        if len(selected) < 2: return
        
        msg = _tr("Are you sure you want to merge the {n} selected rows? The translation will be concatenated.").format(n=len(selected))
        reply = QMessageBox.question(self, _tr("Merge selected"), msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._on_merge_requested(selected)
            self.status_label.setText(_tr("Rows merged successfully."))

    def _on_rechunk_resplit(self):
        """Split a single long row into multiple ones."""
        paragraphs = self.table.get_selected_paragraphs()
        if len(paragraphs) != 1: return
        
        p = paragraphs[0]
        max_chars = self.rechunk_chars.value()
        method = self.rechunk_method.currentData()
        
        import re
        text = p.original
        raw = p.raw or text
        
        # Simple robust split logic (ported from advanced.py)
        segments = re.split(r'\n\s*\n', text)
        if len(segments) < 2: segments = text.split('\n')
        if len(segments) < 2: segments = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        curr = []
        curr_len = 0
        for seg in segments:
            if curr_len + len(seg) > max_chars and curr:
                chunks.append('\n\n'.join(curr))
                curr = [seg]
                curr_len = len(seg)
            else:
                curr.append(seg)
                curr_len += len(seg)
        if curr: chunks.append('\n\n'.join(curr))
        
        if len(chunks) <= 1:
            QMessageBox.information(self, _tr("Split Requested"), _tr("No splitting was necessary (text is already small)."))
            return
            
        new_paragraphs = []
        from lingua.core.cache import Paragraph
        for i, chunk in enumerate(chunks):
            nid = p.id + i + 20000
            nmd5 = uid(f"{nid}{chunk}")
            np = Paragraph(id=nid, md5=nmd5, raw=chunk, original=chunk, page=p.page, attributes=p.attributes)
            new_paragraphs.append(np)
            
        if self.cache:
            self.cache.replace_paragraphs([p.id], new_paragraphs)
            
        idx = p.row
        del self.elements[idx]
        for item in reversed(new_paragraphs):
            self.elements.insert(idx, item)
            
        self.table.populate(self.elements)
        self.table.selectRow(idx)
        self.status_label.setText(_tr("Row re-split into {n} chunks.").format(n=len(chunks)))

    def _on_editor_translate(self, text, engine_name):
        """Handle ad-hoc translation from editor context menus."""
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QApplication
        from lingua.core.translation import get_engine_class
        from lingua.ui.widgets.editor import TranslationCompareDialog
        
        # 1. UI Feedback
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.status_label.setText(f"Translating selection with {engine_name}...")
        
        try:
            # 2. Setup Translator
            engine_cls = get_engine_class(engine_name)
            translator = engine_cls()
            
            # Use current config for languages
            source_lang = self.config.get('source_lang', 'Auto')
            target_lang = self.config.get('target_lang', 'Romanian')
            
            translator.set_source_lang(source_lang)
            translator.set_target_lang(target_lang)
            
            # 3. Perform Translation
            result = translator.translate(text)
            translated_text = "".join(result) if not isinstance(result, str) else result
            
            # 4. Show Result in Comparison Dialog
            dlg = TranslationCompareDialog(
                self, 
                original_text=text, 
                translated_text=translated_text.strip(), 
                engine_name=engine_name
            )
            dlg.applied.connect(self._on_context_translation_applied)
            QApplication.restoreOverrideCursor()
            dlg.show() # Non-modal
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.error_text_edit.appendPlainText(f"CONTEXT TRANSLATE ERROR ({engine_name}):\n{str(e)}\n")
            QMessageBox.critical(self, _tr('Translation Error'), _tr("An error occurred during quick translation:") + f"\n\n{str(e)}")
        finally:
            self.status_label.setText("Ready")

    def _on_context_translation_applied(self, translated_text):
        """Handle 'Apply' action from TranslationCompareDialog."""
        p = getattr(self.translation_text, 'current_paragraph', None)
        if not p:
            # Fallback to current table row if editor reference is lost
            row = self.table.currentRow()
            if 0 <= row < len(self.elements):
                p = self.elements[row]

        if p:
            p.translation = translated_text
            p.aligned = True
            p.engine_name = self.engine_selector.currentText()
            
            # Update cache
            if self.cache:
                self.cache.update_paragraph(p)
                
            # Update Table UI
            self.table.update_row(p.row)
            
            # Update Editor UI
            self.translation_text.blockSignals(True)
            self.translation_text.setPlainText(translated_text)
            self.translation_text.blockSignals(False)
            
            self._update_alignment_report(p)
            self.status_label.setText(_tr("Translation applied to row {n}").format(n=p.row + 1))

    def _scroll_settings(self, delta):
        """Scroll the settings bar horizontally."""
        bar = self.settings_scroll.horizontalScrollBar()
        bar.setValue(bar.value() + delta)

    def _update_scroll_buttons(self):
        """Show/hide arrows based on scroll position and content width."""
        try:
            bar = self.settings_scroll.horizontalScrollBar()
            self.scroll_left_btn.setVisible(bar.value() > 0)
            self.scroll_right_btn.setVisible(bar.value() < bar.maximum())
        except:
            pass

    def cleanup(self):
        """Release resources, stop threads, and close database connections."""
        import gc
        import logging
        try:
            # Stop any running workers
            for worker in self._workers:
                if hasattr(worker, 'stop'):
                    worker.stop()
            
            # Close database connection explicitly
            if hasattr(self, 'cache') and self.cache:
                self.cache.close()
                self.cache = None
            
            # Wait for threads to finish
            for thread in self._threads:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(500)
                    if thread.isRunning():
                        thread.terminate() # Hard stop if needed

            # Clear references
            self._workers = []
            self._threads = []
            
            # Force garbage collection to release file handles
            gc.collect()
            
        except Exception as e:
            logging.error(f"Error during workspace cleanup: {e}")

    def closeEvent(self, event):
        """Ensure cleanup is called when the widget is closed."""
        self.cleanup()
        super().closeEvent(event)

    def eventFilter(self, watched, event):
        """Watch for resize events on the scroll area to update button visibility."""
        if watched == self.settings_scroll and event.type() == QEvent.Resize:
            QTimer.singleShot(50, self._update_scroll_buttons)
        return super().eventFilter(watched, event)
