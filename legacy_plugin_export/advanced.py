import time
import subprocess
import os
from types import MethodType

from qt.core import (
    Qt, QObject, QDialog, QGroupBox, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QPushButton, QSplitter, QLabel, QThread, QLineEdit,
    QGridLayout, QProgressBar, pyqtSignal, pyqtSlot, QPixmap, QEvent,
    QStackedWidget, QSpacerItem, QTabWidget, QCheckBox,
    QComboBox, QSizePolicy, QTimer, QSpinBox)
from calibre.constants import __version__

from . import EbookTranslator
from .lib.utils import uid, traceback_error
from .lib.config import get_config
from .lib.encodings import encoding_list
from .lib.cache import Paragraph, get_cache
from .lib.translation import get_engine_class, get_translator, get_translation
from .lib.element import get_element_handler
from .lib.conversion import extract_item, extra_formats
from .engines.openai import ChatgptTranslate, ChatgptBatchTranslate
from .engines.custom import CustomTranslate
from .engines.google import GeminiTranslate
from .engines.gemini_cache import (
    GeminiCacheManager, save_cache_metadata, load_cache_metadata,
    delete_cache_metadata, estimate_cache_cost, estimate_session_cost)
from .components import (
    EngineList, Footer, SourceLang, TargetLang, InputFormat, OutputFormat,
    AlertMessage, AdvancedTranslationTable, StatusColor, TranslationStatus,
    set_shortcut, ChatgptBatchTranslationManager, DynamicGlossaryExportDialog)
from .components.editor import CodeEditor, TranslationEditor, TranslationCompareDialog, SourceTextEditor


load_translations()


class EditorWorker(QObject):
    start = pyqtSignal((str,), (str, object))
    show = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self.start[str].connect(self.show_message)
        self.start[str, object].connect(self.show_message)

    @pyqtSlot(str)
    @pyqtSlot(str, object)
    def show_message(self, message, callback=None):
        time.sleep(0.01)
        self.show.emit(message)
        time.sleep(1)
        self.show.emit('')
        callback and callback()
        self.finished.emit()


class PreparationWorker(QObject):
    start = pyqtSignal()
    progress = pyqtSignal(int)
    progress_message = pyqtSignal(str)
    progress_detail = pyqtSignal(str)
    close = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, engine_class, ebook):
        QObject.__init__(self)
        self.engine_class = engine_class
        self.ebook = ebook

        self.on_working = False
        self.canceled = False

        self.start.connect(self.prepare_ebook_data)

    def clean_cache(self, cache):
        cache.is_fresh() and cache.destroy()
        self.on_working = False
        self.close.emit(1)

    def set_canceled(self, canceled):
        self.canceled = canceled

    # def cancel(self):
    #     return self.thread().isInterruptionRequested()

    @pyqtSlot()
    def prepare_ebook_data(self):
        self.on_working = True
        input_path = self.ebook.get_input_path()
        
        config = get_config()
        chunking_method = config.get('chunking_method', 'standard')

        element_handler = get_element_handler(
            self.engine_class.placeholder, self.engine_class.separator,
            self.ebook.target_direction, chunking_method)
        merge_length = str(element_handler.get_merge_length())
        encoding = ''
        if self.ebook.encoding.lower() != 'utf-8':
            encoding = self.ebook.encoding.lower()
        # Added 'norm_v1' to invalidate old caches and use new normalizer
        cache_id = uid(
            input_path + self.engine_class.name + self.ebook.target_lang
            + merge_length + encoding + chunking_method + 'norm_v1')
        cache = get_cache(cache_id)

        if cache.is_fresh() or not cache.is_persistence():
            self.progress_detail.emit(
                'Start processing the ebook: %s' % self.ebook.title)
            cache.set_info('title', self.ebook.title)
            cache.set_info('engine_name', self.engine_class.name)
            cache.set_info('target_lang', self.ebook.target_lang)
            cache.set_info('merge_length', merge_length)
            cache.set_info('plugin_version', EbookTranslator.__version__)
            cache.set_info('calibre_version', __version__)
            # --------------------------
            a = time.time()
            # --------------------------
            self.progress_message.emit(_('Extracting ebook content...'))
            try:
                elements = extract_item(
                    input_path, self.ebook.input_format, self.ebook.encoding,
                    self.progress_detail.emit)
            except Exception:
                self.progress_message.emit(
                    _('Failed to extract ebook content'))
                self.progress_detail.emit('\n' + traceback_error())
                self.progress.emit(100)
                self.clean_cache(cache)
                return
            if self.canceled:
                self.clean_cache(cache)
                return
            self.progress.emit(30)
            b = time.time()
            self.progress_detail.emit('extracting timing: %s' % (b - a))
            if self.canceled:
                self.clean_cache(cache)
                return
            # --------------------------
            self.progress_message.emit(_('Filtering ebook content...'))
            original_group = element_handler.prepare_original(elements)
            self.progress.emit(80)
            c = time.time()
            self.progress_detail.emit('filtering timing: %s' % (c - b))
            if self.canceled:
                self.clean_cache(cache)
                return
            # --------------------------
            self.progress_message.emit(_('Preparing user interface...'))
            cache.save(original_group)
            self.progress.emit(100)
            d = time.time()
            self.progress_detail.emit('cache timing: %s' % (d - c))
            if self.canceled:
                self.clean_cache(cache)
                return
        else:
            self.progress_detail.emit(
                'Loading data from cache and preparing user interface...')
            time.sleep(0.1)

        self.finished.emit(cache_id)
        self.on_working = False


class TranslationWorker(QObject):
    start = pyqtSignal()
    close = pyqtSignal(int)
    finished = pyqtSignal()
    translate = pyqtSignal(list, bool)
    logging = pyqtSignal(str, bool)
    # error = pyqtSignal(str, str, str)
    streaming = pyqtSignal(object)
    callback = pyqtSignal(object)

    def __init__(self, engine_class, ebook):
        QObject.__init__(self)
        self.source_lang = ebook.source_lang
        self.target_lang = ebook.target_lang
        self.engine_class = engine_class

        self.on_working = False
        self.canceled = False
        self.need_close = False
        self.session_dynamic_glossary = None  # Persistent glossary for session
        self.translate.connect(self.translate_paragraphs)
        # self.finished.connect(lambda: self.set_canceled(False))

    def set_session_dynamic_glossary(self, glossary):
        """Set session-level dynamic glossary for accumulation across batches."""
        self.session_dynamic_glossary = glossary

    def set_source_lang(self, lang):
        self.source_lang = lang

    def set_target_lang(self, lang):
        self.target_lang = lang

    def set_engine_class(self, engine_class):
        self.engine_class = engine_class

    def set_canceled(self, canceled):
        self.canceled = canceled

    def cancel_request(self):
        return self.canceled

    def set_need_close(self, need_close):
        self.need_close = need_close

    @pyqtSlot(list, bool)
    def translate_paragraphs(self, paragraphs=[], fresh=False):
        """:fresh: retranslate all paragraphs."""
        self.on_working = True
        self.start.emit()
        translator = get_translator(self.engine_class)
        translator.set_source_lang(self.source_lang)
        translator.set_target_lang(self.target_lang)
        translation = get_translation(translator)
        translation.set_fresh(fresh)
        translation.set_logging(
            lambda text, error=False: self.logging.emit(text, error))
        translation.set_streaming(self.streaming.emit)
        translation.set_callback(self.callback.emit)
        translation.set_cancel_request(self.cancel_request)
        
        # Use session glossary if available (persists across batches)
        if self.session_dynamic_glossary:
            translation.set_dynamic_glossary(self.session_dynamic_glossary)
        
        translation.handle(paragraphs)
        
        self.on_working = False
        self.finished.emit()
        if self.need_close:
            time.sleep(0.5)
            self.close.emit(0)


class CreateTranslationProject(QDialog):
    start_translation = pyqtSignal(object)

    def __init__(self, parent, ebook):
        QDialog.__init__(self, parent)
        self.ebook = ebook

        layout = QVBoxLayout(self)
        self.choose_format = self.layout_format()

        self.start_button = QPushButton(_('&Start'))
        # self.start_button.setStyleSheet(
        #     'padding:0;height:48;font-size:20px;color:royalblue;'
        #     'text-transform:uppercase;')
        self.start_button.clicked.connect(self.show_advanced)

        layout.addWidget(self.choose_format)
        layout.addWidget(self.start_button)

    def layout_format(self):
        engine_class = get_engine_class()
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        input_group = QGroupBox(_('Input Format'))
        input_layout = QGridLayout(input_group)
        input_format = InputFormat(self.ebook.files.keys())
        # input_format.setFixedWidth(150)
        input_layout.addWidget(input_format)
        layout.addWidget(input_group, 0, 0, 1, 3)

        output_group = QGroupBox(_('Output Format'))
        output_layout = QGridLayout(output_group)
        output_format = OutputFormat()
        # output_format.setFixedWidth(150)
        output_layout.addWidget(output_format)
        layout.addWidget(output_group, 0, 3, 1, 3)

        source_group = QGroupBox(_('Source Language'))
        source_layout = QVBoxLayout(source_group)
        source_lang = SourceLang()
        source_lang.setFixedWidth(150)
        source_layout.addWidget(source_lang)
        layout.addWidget(source_group, 1, 0, 1, 2)

        target_group = QGroupBox(_('Target Language'))
        target_layout = QVBoxLayout(target_group)
        target_lang = TargetLang()
        target_lang.setFixedWidth(150)
        target_layout.addWidget(target_lang)
        layout.addWidget(target_group, 1, 2, 1, 2)

        source_lang.refresh.emit(
            engine_class.lang_codes.get('source'),
            engine_class.config.get('source_lang'),
            not issubclass(engine_class, CustomTranslate))

        target_lang.refresh.emit(
            engine_class.lang_codes.get('target'),
            engine_class.config.get('target_lang'))

        def change_input_format(_format):
            self.ebook.set_input_format(_format)
        change_input_format(input_format.currentText())
        input_format.currentTextChanged.connect(change_input_format)

        def change_output_format(_format):
            if self.ebook.is_extra_format():
                output_format.lock_format(self.ebook.input_format)
            self.ebook.set_output_format(_format)
        change_output_format(output_format.currentText())
        output_format.currentTextChanged.connect(change_output_format)

        def change_source_lang(lang):
            self.ebook.set_source_lang(lang)
        change_source_lang(source_lang.currentText())
        source_lang.currentTextChanged.connect(change_source_lang)

        def change_target_lang(lang):
            self.ebook.set_target_lang(lang)
        change_target_lang(target_lang.currentText())
        target_lang.currentTextChanged.connect(change_target_lang)

        if self.ebook.input_format in extra_formats.keys():
            encoding_group = QGroupBox(_('Encoding'))
            encoding_layout = QVBoxLayout(encoding_group)
            encoding_select = QComboBox()
            encoding_select.setFixedWidth(150)
            encoding_select.addItems(encoding_list)
            encoding_layout.addWidget(encoding_select)
            layout.addWidget(encoding_group, 1, 4, 1, 2)

            def change_encoding(encoding):
                self.ebook.set_encoding(encoding)
            encoding_select.currentTextChanged.connect(change_encoding)
        else:
            direction_group = QGroupBox(_('Target Directionality'))
            direction_layout = QVBoxLayout(direction_group)
            direction_list = QComboBox()
            direction_list.setFixedWidth(150)
            direction_list.addItem(_('Auto'), 'auto')
            direction_list.addItem(_('Left to Right'), 'ltr')
            direction_list.addItem(_('Right to Left'), 'rtl')
            direction_layout.addWidget(direction_list)
            layout.addWidget(direction_group, 1, 4, 1, 2)

            def change_direction(_index):
                _direction = direction_list.itemData(_index)
                self.ebook.set_target_direction(_direction)
            direction_list.currentIndexChanged.connect(change_direction)

            engine_target_lange_codes = engine_class.lang_codes.get('target')
            if engine_target_lange_codes is not None and \
                    self.ebook.target_lang in engine_target_lange_codes:
                target_lang_code = engine_target_lange_codes[
                    self.ebook.target_lang]
                direction = engine_class.get_lang_directionality(
                    target_lang_code)
                index = direction_list.findData(direction)
                direction_list.setCurrentIndex(index)

        return widget

    @pyqtSlot()
    def show_advanced(self):
        self.done(0)
        self.start_translation.emit(self.ebook)


class GeminiCacheDialog(QDialog):
    """Dialog for creating and managing Gemini context caches.

    Enhancements:
    - Dry Run: count tokens before creating (free API call)
    - Cost estimator: show $/hour storage, savings per request
    - Prominent red Delete button
    - Auto-cleanup prompt on 100% translation
    """

    def __init__(self, parent, ebook, current_engine):
        QDialog.__init__(self, parent)
        self.ebook = ebook
        self.current_engine = current_engine
        self.config = get_config()
        self.alert = AlertMessage(self)
        self.setWindowTitle(_('⚡ Gemini Context Cache Manager'))
        self.setMinimumWidth(580)
        self.setMinimumHeight(480)

        layout = QVBoxLayout(self)

        # --- Info section ---
        info_label = QLabel(
            _('<b>Context Caching</b> uploads your book text to Gemini servers '
              'so each translation chunk costs ~75% less on input tokens.<br>'
              '<i>Requires: versioned model (e.g. gemini-2.5-flash-001), '
              '≥32K tokens (~130K chars)</i>'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # --- Model + TTL row ---
        config_layout = QHBoxLayout()

        model_group = QGroupBox(_('Model (versioned)'))
        model_inner = QHBoxLayout(model_group)
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_input.addItems([
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-2.5-flash-001',
            'gemini-2.5-flash-lite-001',
            'gemini-2.0-flash-lite-preview-02-05',
            'gemini-1.5-flash',
        ])
        current_model = self.config.get('gemini_model', '')
        if current_model:
            self.model_input.setCurrentText(current_model)
        else:
            self.model_input.setCurrentText('gemini-2.5-flash')
        
        model_inner.addWidget(self.model_input)
        config_layout.addWidget(model_group, 3)

        ttl_group = QGroupBox(_('TTL (hours)'))
        ttl_inner = QHBoxLayout(ttl_group)
        self.ttl_input = QLineEdit()
        self.ttl_input.setText('24')
        self.ttl_input.setMaximumWidth(80)
        ttl_inner.addWidget(self.ttl_input)
        config_layout.addWidget(ttl_group, 1)

        layout.addLayout(config_layout)

        # --- Status display ---
        status_group = QGroupBox(_('Cache Status & Cost'))
        status_layout = QVBoxLayout(status_group)
        self.status_text = QPlainTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(160)
        status_layout.addWidget(self.status_text)
        layout.addWidget(status_group)

        # --- Row 1: Dry Run + Create ---
        row1 = QHBoxLayout()
        self.dryrun_btn = QPushButton(_('🔢 Dry Run (Count Tokens)'))
        self.dryrun_btn.setToolTip(
            _('Count tokens and estimate costs WITHOUT creating a cache. Free API call.'))
        self.create_btn = QPushButton(_('📤 Create Cache'))
        row1.addWidget(self.dryrun_btn)
        row1.addWidget(self.create_btn)
        layout.addLayout(row1)

        # --- Row 2: Check + Extend + Activate/Deactivate ---
        row2 = QHBoxLayout()
        self.check_btn = QPushButton(_('🔍 Check'))
        self.extend_btn = QPushButton(_('⏰ Extend TTL'))
        self.activate_btn = QPushButton(_('✅ Activate'))
        self.deactivate_btn = QPushButton(_('⛔ Deactivate'))
        row2.addWidget(self.check_btn)
        row2.addWidget(self.extend_btn)
        row2.addWidget(self.activate_btn)
        row2.addWidget(self.deactivate_btn)
        layout.addLayout(row2)

        # --- Row 3: DELETE — prominent red button ---
        delete_layout = QHBoxLayout()
        self.delete_btn = QPushButton(
            _('🗑️  DELETE CACHE  (stops billing immediately)'))
        self.delete_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #dc3545;'
            '  color: white;'
            '  font-weight: bold;'
            '  font-size: 13px;'
            '  padding: 8px 16px;'
            '  border-radius: 4px;'
            '  border: none;'
            '}'
            'QPushButton:hover {'
            '  background-color: #c82333;'
            '}'
            'QPushButton:pressed {'
            '  background-color: #a71d2a;'
            '}')
        self.delete_btn.setMinimumHeight(40)
        delete_layout.addWidget(self.delete_btn)
        layout.addLayout(delete_layout)

        # --- Connections ---
        self.dryrun_btn.clicked.connect(self.dry_run)
        self.create_btn.clicked.connect(self.create_cache)
        self.check_btn.clicked.connect(self.check_status)
        self.extend_btn.clicked.connect(self.extend_ttl)
        self.delete_btn.clicked.connect(self.delete_cache)
        self.activate_btn.clicked.connect(self.activate_cache)
        self.deactivate_btn.clicked.connect(self.deactivate_cache)

        # Initial status check
        self._refresh_status()

    def _log(self, message):
        self.status_text.appendPlainText(message)

    def _get_api_key(self):
        """Get Gemini API key from engine config."""
        engine_config = self.config.get('engine_preferences', {})
        gemini_prefs = engine_config.get('Gemini', {})
        api_key = gemini_prefs.get('api_key', '')
        if not api_key:
            try:
                translator = get_translator(self.current_engine)
                api_key = getattr(translator, 'api_key', '')
            except Exception:
                pass
        return api_key

    def _get_manager(self):
        api_key = self._get_api_key()
        if not api_key:
            self._log('ERROR: No Gemini API key found. Configure it first.')
            return None
        proxy_uri = self.config.get('proxy_uri', None)
        return GeminiCacheManager(api_key, proxy_uri)

    def _extract_book_text(self):
        """Extract all text from the book. Returns (book_text, system_instruction) or (None, None)."""
        try:
            book_path = self.ebook.get_input_path()
            elements = extract_item(
                book_path, self.ebook.input_format, self.ebook.encoding)
            if not elements:
                self._log('ERROR: No elements extracted from book.')
                return None, None

            book_text = '\n\n'.join(
                [e.get_content() for e in elements if e.get_content().strip()])

            self._log(f'Extracted {len(book_text):,} chars from '
                      f'{len(elements)} elements')
        except Exception as e:
            self._log(f'ERROR extracting book: {str(e)}')
            return None, None

        # Build system instruction
        try:
            from .engines.google import gemini_prompt_extension
            translator = get_translator(self.current_engine)
            translator.set_source_lang(self.ebook.source_lang)
            translator.set_target_lang(self.ebook.target_lang)

            system_instruction = getattr(translator, 'prompt', '')
            if system_instruction:
                system_instruction = system_instruction.replace(
                    '<tlang>', self.ebook.target_lang)
                system_instruction = system_instruction.replace(
                    '<slang>', self.ebook.source_lang)

            ext = gemini_prompt_extension.get(self.ebook.target_lang, '')
            if ext:
                system_instruction += '\n\n' + ext
        except Exception as e:
            system_instruction = (
                f'Translate from {self.ebook.source_lang} '
                f'to {self.ebook.target_lang}.')
            self._log(f'Fallback instruction: {str(e)}')

        return book_text, system_instruction

    def _show_cost_estimate(self, token_count, model):
        """Display cost estimate with output costs and session total."""
        ttl = float(self.ttl_input.text().strip() or '24')
        costs = estimate_cache_cost(token_count, model, ttl)

        if costs:
            # Deprecation warning
            if costs.get('deprecated'):
                self._log(f'\n⚠️ WARNING: {model} is DEPRECATED (EOL: 2026-03-31)')
                self._log('   Consider gemini-2.5-flash or gemini-2.5-flash-lite')

            self._log(f'\n💰 Cost Estimate ({model}):')
            self._log(f'   Storage:  ${costs["storage_cost_per_hour"]:.4f}/hour '
                      f'(${costs["storage_cost_total"]:.2f} total for {ttl}h)')
            self._log(f'   Input:    ${costs["input_cost_normal"]:.4f} normal → '
                      f'${costs["input_cost_cached"]:.4f} cached '
                      f'({costs["discount_pct"]}% off)')
            self._log(f'   Output:   ${costs["output_per_1m"]:.2f}/1M tokens')
            self._log(f'   Savings:  ${costs["savings_per_request"]:.4f}/request on input')

            # Session total
            session = estimate_session_cost(token_count, model, ttl)
            if session:
                self._log(f'\n📊 Session Total (estimated {ttl}h):')
                self._log(f'   Creation:  ${session["creation_cost"]:.4f}')
                self._log(f'   Storage:   ${session["storage_cost"]:.4f}')
                self._log(f'   Output:    ${session["output_cost"]:.2f} '
                          f'(~{token_count:,} output tokens)')
                self._log(f'   ─────────────────────')
                self._log(f'   TOTAL:     ${session["total_with_cache"]:.2f}')
        else:
            self._log(f'\n⚠️ Pricing unknown for model "{model}"')

    def _refresh_status(self):
        """Check if there's an existing cache for this book."""
        self.status_text.clear()
        book_path = self.ebook.get_input_path()
        metadata = load_cache_metadata(book_path)

        if metadata:
            self._log(f'Cache metadata found:')
            self._log(f'  Name: {metadata.get("cache_name", "N/A")}')
            self._log(f'  Model: {metadata.get("model", "N/A")}')
            self._log(f'  Created: {metadata.get("created_at", "N/A")}')
            tokens = metadata.get('token_count', 0)
            self._log(f'  Tokens: {tokens:,}')
            self._log(f'  TTL: {metadata.get("ttl_hours", 0)}h')

            # Show ongoing cost
            if tokens > 0:
                self._show_cost_estimate(
                    tokens, metadata.get('model', ''))

            # Check if currently activated
            engine_prefs = self.config.get('engine_preferences', {})
            gemini_prefs = engine_prefs.get('Gemini', {})
            active_cache = gemini_prefs.get('cached_content_name', '')
            if active_cache == metadata.get('cache_name'):
                self._log('\n✅ Cache is ACTIVE for translation')
            else:
                self._log('\n⚠️ Cache exists but is NOT activated')
        else:
            self._log('No cache found for this book.')
            self._log(f'Book: {self.ebook.title}')
            self._log('Use "🔢 Dry Run" to check token count and cost first.')

    def dry_run(self):
        """Count tokens and estimate costs WITHOUT creating a cache.

        Uses the free countTokens API endpoint.
        """
        manager = self._get_manager()
        if not manager:
            return

        model = self.model_input.currentText().strip()
        if not model:
            self.alert.pop(_('Enter a model name first.'), 'warning')
            return

        self._log('\n--- 🔢 Dry Run ---')
        self._log('Extracting book text...')

        from qt.core import QApplication
        QApplication.processEvents()

        book_text, system_instruction = self._extract_book_text()
        if not book_text:
            return

        self._log(f'Counting tokens via API (free call)...')
        QApplication.processEvents()

        try:
            token_count = manager.count_tokens(
                book_text, model, system_instruction)

            self._log(f'\n📊 Token Count: {token_count:,}')

            # Check minimum
            from .engines.gemini_cache import MIN_CACHE_TOKENS
            if token_count < MIN_CACHE_TOKENS:
                self._log(f'⚠️ Below minimum! Need ≥{MIN_CACHE_TOKENS:,} tokens.')
                self._log(f'   Short by {MIN_CACHE_TOKENS - token_count:,} tokens.')
            else:
                self._log(f'✅ Above minimum ({MIN_CACHE_TOKENS:,}) — caching viable!')

            self._show_cost_estimate(token_count, model)

        except Exception as e:
            self._log(f'❌ Token counting failed: {str(e)}')

    def create_cache(self):
        """Create a new context cache by uploading the book text."""
        manager = self._get_manager()
        if not manager:
            return

        model = self.model_input.currentText().strip()
        if not model:
            self.alert.pop(_('Please enter a versioned model name.'), 'warning')
            return

        try:
            ttl_hours = float(self.ttl_input.text().strip())
        except ValueError:
            self.alert.pop(_('TTL must be a number.'), 'warning')
            return

        self._log('\n--- Creating Cache ---')
        self._log(f'Model: {model}  |  TTL: {ttl_hours}h')

        from qt.core import QApplication

        book_text, system_instruction = self._extract_book_text()
        if not book_text:
            return

        display_name = f'BookTranslation_{self.ebook.title[:80]}'
        self._log(f'Uploading {len(book_text):,} chars to Gemini...')
        QApplication.processEvents()

        try:
            result = manager.create_cache(
                book_text=book_text,
                system_instruction=system_instruction,
                model=model,
                display_name=display_name,
                ttl_hours=ttl_hours
            )

            cache_name = result.get('name', '')
            token_count = result.get('usageMetadata', {}).get(
                'totalTokenCount', 0)

            self._log(f'\n✅ Cache created!')
            self._log(f'  Name: {cache_name}')
            self._log(f'  Tokens: {token_count:,}')

            # Show cost
            self._show_cost_estimate(token_count, model)

            # Save metadata
            book_path = self.ebook.get_input_path()
            save_cache_metadata(
                book_path, cache_name, model, display_name,
                ttl_hours, token_count)
            self._log('  Metadata saved.')

        except Exception as e:
            self._log(f'\n❌ Cache creation FAILED: {str(e)}')

    def check_status(self):
        """Check if the server-side cache is still alive."""
        manager = self._get_manager()
        if not manager:
            return

        book_path = self.ebook.get_input_path()
        metadata = load_cache_metadata(book_path)
        if not metadata:
            self._log('\nNo cache metadata found. Create a cache first.')
            return

        cache_name = metadata.get('cache_name', '')
        self._log(f'\n--- Checking: {cache_name} ---')

        is_valid, info = manager.is_cache_valid(cache_name)
        if is_valid:
            self._log(f'✅ {info}')
        else:
            self._log(f'❌ {info}')

    def extend_ttl(self):
        """Extend the TTL of an existing cache."""
        manager = self._get_manager()
        if not manager:
            return

        book_path = self.ebook.get_input_path()
        metadata = load_cache_metadata(book_path)
        if not metadata:
            self._log('\nNo cache to extend.')
            return

        try:
            ttl_hours = float(self.ttl_input.text().strip())
        except ValueError:
            self.alert.pop(_('TTL must be a number.'), 'warning')
            return

        cache_name = metadata.get('cache_name', '')
        self._log(f'\nExtending TTL to {ttl_hours}h...')

        try:
            manager.update_cache_ttl(cache_name, ttl_hours)
            self._log('✅ TTL extended.')

            save_cache_metadata(
                book_path, metadata['cache_name'], metadata['model'],
                metadata['display_name'], ttl_hours,
                metadata.get('token_count', 0))
        except Exception as e:
            self._log(f'❌ ERROR: {str(e)}')

    def delete_cache(self):
        """Delete the cache from Gemini servers and local metadata."""
        if self.alert.ask(
                _('Delete cache from Gemini servers?\n'
                  'This stops billing immediately.')) != 'yes':
            return

        manager = self._get_manager()
        if not manager:
            return

        book_path = self.ebook.get_input_path()
        metadata = load_cache_metadata(book_path)
        if not metadata:
            self._log('\nNo cache to delete.')
            return

        cache_name = metadata.get('cache_name', '')
        self._log(f'\nDeleting cache: {cache_name}...')

        try:
            manager.delete_cache(cache_name)
            delete_cache_metadata(book_path)
            self._log('✅ Cache deleted — billing stopped.')
            self.deactivate_cache()
        except Exception as e:
            self._log(f'❌ ERROR: {str(e)}')
            delete_cache_metadata(book_path)
            self._log('Local metadata removed anyway.')

    def activate_cache(self):
        """Set the cache as active for translation."""
        book_path = self.ebook.get_input_path()
        metadata = load_cache_metadata(book_path)
        if not metadata:
            self._log('\nNo cache to activate. Create one first.')
            return

        cache_name = metadata.get('cache_name', '')
        engine_prefs = self.config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        gemini_prefs['cached_content_name'] = cache_name
        engine_prefs['Gemini'] = gemini_prefs
        self.config.update(engine_preferences=engine_prefs)
        self.config.commit()

        self._log(f'\n✅ Cache ACTIVATED: {cache_name}')
        self._log('Input token costs reduced by ~75%!')

    def deactivate_cache(self):
        """Remove the cache reference from engine preferences."""
        engine_prefs = self.config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        if 'cached_content_name' in gemini_prefs:
            del gemini_prefs['cached_content_name']
            engine_prefs['Gemini'] = gemini_prefs
            self.config.update(engine_preferences=engine_prefs)
            self.config.commit()
            self._log('\nCache DEACTIVATED. Normal costs apply.')
        else:
            self._log('\nCache was not active.')

    @staticmethod
    def prompt_cleanup(parent, ebook):
        """Prompt user to delete cache after 100% translation.

        Call this from the translation-complete handler.
        Returns True if user chose to delete.
        """
        book_path = ebook.get_input_path()
        metadata = load_cache_metadata(book_path)
        if not metadata:
            return False

        config = get_config()
        engine_prefs = config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        active_cache = gemini_prefs.get('cached_content_name', '')

        if not active_cache:
            return False

        alert = AlertMessage(parent)
        answer = alert.ask(
            _('Translation complete! 🎉\n\n'
              'A context cache is still active and '
              'incurring storage costs.\n\n'
              'Delete the cache now to stop billing?'))

        if answer == 'yes':
            try:
                api_key = gemini_prefs.get('api_key', '')
                if api_key:
                    proxy = config.get('proxy_uri', None)
                    manager = GeminiCacheManager(api_key, proxy)
                    manager.delete_cache(active_cache)
                delete_cache_metadata(book_path)

                # Deactivate
                del gemini_prefs['cached_content_name']
                engine_prefs['Gemini'] = gemini_prefs
                config.update(engine_preferences=engine_prefs)
                config.commit()
                return True
            except Exception:
                pass

        return False


class AdvancedTranslation(QDialog):
    paragraph_sig = pyqtSignal(object)
    ebook_title = pyqtSignal()
    progress_bar = pyqtSignal()
    batch_translation = pyqtSignal()

    preparation_thread = QThread()
    trans_thread = QThread()
    editor_thread = QThread()

    def __init__(self, parent, icon, worker, ebook):
        QDialog.__init__(self, parent)
        self.api = parent.current_db.new_api
        self.icon = icon
        self.worker = worker
        self.ebook = ebook
        self.config = get_config()
        self.alert = AlertMessage(self)
        self.footer = Footer()
        # self.error = JobError(self)
        self.current_engine = get_engine_class()
        self.cache = None
        self.merge_enabled = False

        self.progress_step = 0
        self.translate_all = False
        
        # Session-level dynamic glossary (persists across batch translations)
        from .lib.dynamic_glossary import DynamicGlossary
        self.session_dynamic_glossary = DynamicGlossary()

        self.editor_worker = EditorWorker()
        self.editor_worker.moveToThread(self.editor_thread)
        self.editor_thread.finished.connect(self.editor_worker.deleteLater)
        self.editor_thread.start()

        self.trans_worker = TranslationWorker(self.current_engine, self.ebook)
        self.trans_worker.close.connect(self.done)
        self.trans_worker.set_session_dynamic_glossary(self.session_dynamic_glossary)
        self.trans_worker.moveToThread(self.trans_thread)
        self.trans_thread.finished.connect(self.trans_worker.deleteLater)
        self.trans_thread.start()

        self.preparation_worker = PreparationWorker(
            self.current_engine, self.ebook)
        self.preparation_worker.close.connect(self.done)
        self.preparation_worker.moveToThread(self.preparation_thread)
        self.preparation_thread.finished.connect(
            self.preparation_worker.deleteLater)
        self.preparation_thread.start()

        layout = QVBoxLayout(self)

        self.waiting = self.layout_progress()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.waiting)
        layout.addWidget(self.stack)
        layout.addWidget(self.footer)

        def working_status():
            self.logging_text.clear()
            self.errors_text.clear()
        self.trans_worker.start.connect(working_status)

        self.trans_worker.logging.connect(
            lambda text, error: self.errors_text.appendPlainText(text)
            if error else self.logging_text.appendPlainText(text))

        def working_finished():
            if self.translate_all and not self.trans_worker.cancel_request():
                failures = len(self.table.get_selected_paragraphs(True, True))
                if failures > 0:
                    message = _(
                        'Failed to translate {} paragraph(s), '
                        'Would you like to retry?')
                    if self.alert.ask(message.format(failures)) == 'yes':
                        self.translate_all_paragraphs()
                        return
                else:
                    self.alert.pop(_('Translation completed.'))
                    
                    # Auto-cleanup: prompt user to delete cache after 100%
                    GeminiCacheDialog.prompt_cleanup(self, self.ebook)
                    
                    # Show dynamic glossary export dialog if terms detected
                    self.show_dynamic_glossary_export()
                    
                    # Check if shutdown is requested
                    if hasattr(self, 'shutdown_checkbox') and self.shutdown_checkbox.isChecked():
                        self.show_shutdown_countdown()
            self.trans_worker.set_canceled(False)
            self.translate_all = False
        self.trans_worker.finished.connect(working_finished)

        # self.trans_worker.error.connect(
        #     lambda title, reason, detail: self.error.show_error(
        #         title, _('Failed') + ': ' + reason, det_msg=detail))

        def prepare_table_layout(cache_id):
            self.cache = get_cache(cache_id)
            self.merge_enabled = int(self.cache.get_info('merge_length')) > 0
            paragraphs = self.cache.all_paragraphs()
            if len(paragraphs) < 1:
                self.alert.pop(
                    _('There is no content that needs to be translated.'),
                    'warning')
                self.done(0)
                return
            self.table = AdvancedTranslationTable(self, paragraphs)
            self.panel = self.layout_panel()
            self.stack.addWidget(self.panel)
            self.stack.setCurrentWidget(self.panel)
            self.table.setFocus(Qt.OtherFocusReason)
        self.preparation_worker.finished.connect(prepare_table_layout)
        self.preparation_worker.start.emit()

    def layout_progress(self):
        widget = QWidget()
        layout = QGridLayout(widget)

        try:
            cover_image = self.api.cover(self.ebook.id, as_pixmap=True)
        except Exception:
            cover_image = QPixmap(self.api.cover(self.ebook.id, as_image=True))
        if cover_image.isNull():
            cover_image = QPixmap(I('default_cover.png'))
        cover_image = cover_image.scaledToHeight(
            480, Qt.TransformationMode.SmoothTransformation)

        cover = QLabel()
        cover.setAlignment(Qt.AlignCenter)
        cover.setPixmap(cover_image)

        title = QLabel()
        title.setMaximumWidth(cover_image.width())
        title.setText(title.fontMetrics().elidedText(
            self.ebook.title, Qt.ElideRight, title.width()))
        title.setToolTip(self.ebook.title)

        progress_bar = QProgressBar()
        progress_bar.setFormat('')
        progress_bar.setValue(0)
        # progress_bar.setFixedWidth(300)
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(0)

        def show_progress(value):
            if progress_bar.maximum() == 0:
                progress_bar.setMaximum(100)
            progress_bar.setValue(value)
        self.preparation_worker.progress.connect(show_progress)

        label = QLabel(_('Loading ebook data, please wait...'))
        label.setAlignment(Qt.AlignCenter)
        self.preparation_worker.progress_message.connect(label.setText)

        detail = QPlainTextEdit()
        detail.setReadOnly(True)
        self.preparation_worker.progress_detail.connect(detail.appendPlainText)

        layout.addWidget(cover, 0, 0)
        layout.addWidget(title, 1, 0)
        layout.addItem(QSpacerItem(0, 20), 2, 0, 1, 3)
        layout.addWidget(progress_bar, 3, 0)
        layout.addWidget(label, 4, 0)
        layout.addItem(QSpacerItem(0, 0), 5, 0, 1, 3)
        layout.addItem(QSpacerItem(10, 0), 0, 1, 6, 1)
        layout.addWidget(detail, 0, 2, 6, 1)
        # layout.setRowStretch(0, 1)
        layout.setRowStretch(2, 1)
        layout.setColumnStretch(2, 1)
        # layout.setColumnStretch(2, 1)

        return widget

    def layout_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        review_index = tabs.addTab(self.layout_review(), _('Review'))
        log_index = tabs.addTab(self.layout_log(), _('Log'))
        errors_index = tabs.addTab(self.layout_errors(), _('Errors'))
        tabs.setStyleSheet('QTabBar::tab {min-width:120px;}')

        self.trans_worker.start.connect(
            lambda: (self.translate_all or self.table.selected_count() > 1)
            and tabs.setCurrentIndex(log_index))
        self.trans_worker.finished.connect(
            lambda: tabs.setCurrentIndex(
                errors_index if self.errors_text.toPlainText()
                and len(self.table.get_selected_paragraphs(True, True)) > 0
                else review_index))
        splitter = QSplitter()
        splitter.addWidget(self.layout_table())
        splitter.addWidget(tabs)
        splitter.setSizes([int(splitter.width() / 2)] * 2)

        layout.addWidget(self.layout_control())
        layout.addWidget(splitter, 1)

        return widget

    def layout_filter(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        categories = QComboBox()
        categories.addItem(_('All'), 'all')
        if self.merge_enabled:
            categories.addItem(_('Non-aligned'), 'non_aligned')
            categories.addItem(_('⚠️ Incomplete'), 'incomplete')
        categories.addItem(_('Translated'), 'translated')
        categories.addItem(_('Untranslated'), 'untranslated')

        content_types = QComboBox()
        content_types.addItem(_('Original Text'), 'original_text')
        content_types.addItem(_('Original Code'), 'original_code')
        content_types.addItem(_('Translation Text'), 'translation_text')

        search_input = QLineEdit()
        search_input.setPlaceholderText(_('keyword for filtering'))
        set_shortcut(
            search_input, 'search', search_input.setFocus,
            search_input.placeholderText())

        reset_button = QPushButton(_('Reset'))
        reset_button.setVisible(False)

        def filter_table_items(index):
            self.table.show_all_rows()
            category = categories.itemData(index)
            if category == 'non_aligned':
                self.table.hide_by_paragraphs(self.table.aligned_paragraphs())
            elif category == 'incomplete':
                self.table.hide_by_paragraphs(
                    self.table.complete_paragraphs())
            elif category == 'translated':
                self.table.hide_by_paragraphs(
                    self.table.untranslated_paragraphs())
            elif category == 'untranslated':
                self.table.hide_by_paragraphs(
                    self.table.translated_paragraphs())

        def filter_by_category(index):
            reset_button.setVisible(index != 0)
            filter_table_items(index)
            self.table.show_by_text(
                search_input.text(), content_types.currentData())
        categories.currentIndexChanged.connect(filter_by_category)

        def filter_by_content_type(index):
            reset_button.setVisible(index != 0)
            filter_table_items(categories.currentIndex())
            self.table.show_by_text(
                search_input.text(), content_types.itemData(index))
        content_types.currentIndexChanged.connect(filter_by_content_type)

        def filter_by_keyword(text):
            reset_button.setVisible(text != '')
            filter_table_items(categories.currentIndex())
            self.table.show_by_text(text, content_types.currentData())
        search_input.textChanged.connect(filter_by_keyword)

        def reset_filter_criteria():
            categories.setCurrentIndex(0)
            content_types.setCurrentIndex(0)
            search_input.clear()
            reset_button.setVisible(False)
        reset_button.clicked.connect(reset_filter_criteria)

        # def reset_filter():
        #     filter_table_items(categories.currentIndex())
        #     self.table.show_by_text(search_input.text())
        # self.editor_worker.finished.connect(reset_filter)
        # self.trans_worker.finished.connect(reset_filter)

        layout.addWidget(categories)
        layout.addWidget(content_types)
        layout.addWidget(search_input)
        layout.addWidget(reset_button)

        return widget

    def layout_table(self):
        widget = QWidget()
        widget.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        progress_bar = QProgressBar()
        progress_bar.setMaximum(100000000)
        progress_bar.setVisible(False)

        def write_progress():
            value = progress_bar.value() + self.progress_step
            if value > progress_bar.maximum():
                value = progress_bar.maximum()
            progress_bar.setValue(value)
        self.progress_bar.connect(write_progress)

        paragraph_count = QLabel()
        non_aligned_paragraph_count = QLabel()
        non_aligned_paragraph_count.setVisible(False)

        counter = QWidget()
        counter_layout = QHBoxLayout(counter)
        counter_layout.setContentsMargins(0, 0, 0, 0)
        counter_layout.setSpacing(0)
        counter_layout.addWidget(paragraph_count)
        counter_layout.addWidget(non_aligned_paragraph_count)
        counter_layout.addStretch(1)
        self.footer.layout().insertWidget(0, counter)

        def get_paragraph_count(select_all=True):
            item_count = char_count = 0
            paragraphs = self.table.get_selected_paragraphs(
                select_all=select_all)
            for paragraph in paragraphs:
                item_count += 1
                char_count += len(paragraph.original)
            return (item_count, char_count)
        all_item_count, all_char_count = get_paragraph_count(True)

        def item_selection_changed():
            item_count, char_count = get_paragraph_count(False)
            total = '%s/%s' % (item_count, all_item_count)
            parts = '%s/%s' % (char_count, all_char_count)
            paragraph_count.setText(
                _('Total items: {}').format(total) + ' · '
                + _('Character count: {}').format(parts))
        item_selection_changed()
        self.table.itemSelectionChanged.connect(item_selection_changed)

        if self.merge_enabled:
            non_aligned_paragraph_count.setVisible(True)

            def show_none_aligned_count():
                non_aligned_paragraph_count.setText(
                    ' · ' + _('Non-aligned items: {}')
                    .format(self.table.non_aligned_count))
            show_none_aligned_count()
            self.table.row.connect(show_none_aligned_count)

        filter_widget = self.layout_filter()

        layout.addWidget(filter_widget)
        layout.addWidget(self.table, 1)
        layout.addWidget(progress_bar)
        layout.addWidget(self.layout_table_control())

        def working_start():
            if self.translate_all or self.table.selected_count() > 1:
                filter_widget.setVisible(False)
                progress_bar.setValue(0)
                progress_bar.setVisible(True)
                counter.setVisible(False)
        self.trans_worker.start.connect(working_start)

        def working_end():
            filter_widget.setVisible(True)
            progress_bar.setVisible(False)
            counter.setVisible(True)
        self.trans_worker.finished.connect(working_end)

        return widget

    def layout_table_control(self):
        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(4)

        # --- Row 1: Standard action buttons ---
        buttons_row = QWidget()
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        delete_button = QPushButton(_('Delete'))
        delete_button.setToolTip(delete_button.text() + ' [Del]')
        
        # Dynamic glossary view button
        view_terms_button = QPushButton(_('📊 Detected Terms'))
        view_terms_button.setToolTip(_('View and export detected recurring terms'))
        view_terms_button.clicked.connect(self.show_dynamic_glossary_export)
        
        batch_translation = QPushButton(
            ' %s (%s)' % (_('Batch Translation'), _('Beta')))
        translate_all = QPushButton('  %s  ' % _('Translate All'))
        translate_selected = QPushButton('  %s  ' % _('Translate Selected'))

        delete_button.clicked.connect(self.table.delete_selected_rows)
        translate_all.clicked.connect(self.translate_all_paragraphs)
        translate_selected.clicked.connect(self.translate_selected_paragraph)

        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(view_terms_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(batch_translation)
        buttons_layout.addWidget(translate_all)
        buttons_layout.addWidget(translate_selected)

        action_layout.addWidget(buttons_row)

        # --- Row 2: Re-Chunk Panel ---
        rechunk_panel = QGroupBox(_('🔄 Re-Chunk Selected Rows'))
        rechunk_panel.setStyleSheet(
            'QGroupBox { font-weight: bold; border: 1px solid #888; '
            'border-radius: 4px; margin-top: 6px; padding-top: 14px; }'
            'QGroupBox::title { subcontrol-origin: margin; left: 10px; '
            'padding: 0 4px; }')
        rechunk_layout = QHBoxLayout(rechunk_panel)
        rechunk_layout.setContentsMargins(8, 4, 8, 4)

        # Merge button
        merge_button = QPushButton(_('🔗 Merge Selected'))
        merge_button.setToolTip(
            _('Merge 2-5 selected rows into a single row. '
              'Step 1 of re-chunking.'))
        merge_button.clicked.connect(self.merge_selected_rows)

        # Separator
        sep_label = QLabel('│')
        sep_label.setStyleSheet('color: #888; font-size: 16px;')

        # Re-Split controls
        method_label = QLabel(_('Split method:'))
        self.rechunk_method = QComboBox()
        self.rechunk_method.addItem(_('Merge (custom chars)'), 'merge')
        self.rechunk_method.addItem(_('Content Aware'), 'chapter_aware')
        self.rechunk_method.addItem(_('Per File'), 'per_file')
        self.rechunk_method.setMaximumWidth(180)

        chars_label = QLabel(_('Max chars:'))
        self.rechunk_chars = QSpinBox()
        self.rechunk_chars.setRange(2000, 30000)
        self.rechunk_chars.setSingleStep(1000)
        self.rechunk_chars.setValue(
            int(self.config.get('merge_length', 13000) or 13000))
        self.rechunk_chars.setMaximumWidth(100)

        def on_method_changed(index):
            method = self.rechunk_method.itemData(index)
            chars_enabled = (method == 'merge')
            self.rechunk_chars.setEnabled(chars_enabled)
            chars_label.setEnabled(chars_enabled)
        self.rechunk_method.currentIndexChanged.connect(on_method_changed)

        resplit_button = QPushButton(_('🔄 Re-Split & Translate'))
        resplit_button.setToolTip(
            _('Re-split the selected row with chosen method, '
              'then auto-translate the new rows. Step 2 of re-chunking.'))
        resplit_button.clicked.connect(self.resplit_selected_row)

        rechunk_layout.addWidget(merge_button)
        rechunk_layout.addWidget(sep_label)
        rechunk_layout.addWidget(method_label)
        rechunk_layout.addWidget(self.rechunk_method)
        rechunk_layout.addWidget(chars_label)
        rechunk_layout.addWidget(self.rechunk_chars)
        rechunk_layout.addStretch(1)
        rechunk_layout.addWidget(resplit_button)

        rechunk_panel.setVisible(False)  # Hidden by default
        action_layout.addWidget(rechunk_panel)

        stop_widget = QWidget()
        stop_layout = QHBoxLayout(stop_widget)
        stop_layout.setContentsMargins(0, 0, 0, 0)
        # stop_layout.addStretch(1)
        stop_button = QPushButton(_('Stop'))
        stop_layout.addWidget(stop_button)

        delete_button.setDisabled(True)
        translate_selected.setDisabled(True)

        self.batch_translation.connect(
            lambda: batch_translation.setVisible(
                self.current_engine == ChatgptTranslate))
        self.batch_translation.emit()

        def start_batch_translation():
            translator = get_translator(self.current_engine)
            translator.set_source_lang(self.ebook.source_lang)
            translator.set_target_lang(self.ebook.target_lang)
            batch_translator = ChatgptBatchTranslate(translator)
            batch = ChatgptBatchTranslationManager(
                batch_translator, self.cache, self.table, self)
            batch.exec_()
        batch_translation.clicked.connect(start_batch_translation)

        def item_selection_changed():
            count = self.table.selected_count()
            disabled = count < 1
            delete_button.setDisabled(disabled)
            translate_selected.setDisabled(disabled)

            # Re-chunk panel visibility
            if self.merge_enabled:
                # Show merge when 2-5 rows selected
                merge_button.setEnabled(2 <= count <= 5)
                merge_button.setText(
                    _('🔗 Merge Selected ({})').format(count)
                    if count >= 2 else _('🔗 Merge Selected'))

                # Show re-split when exactly 1 row selected with long text
                selected = self.table.get_selected_paragraphs()
                can_resplit = (count == 1 and selected
                              and len(selected[0].original) > 2000)
                resplit_button.setEnabled(can_resplit)

                # Show panel if any re-chunk action is possible
                rechunk_panel.setVisible(
                    (2 <= count <= 5) or can_resplit)
            else:
                rechunk_panel.setVisible(False)

        item_selection_changed()
        self.table.itemSelectionChanged.connect(item_selection_changed)

        def stop_translation():
            action = self.alert.ask(
                _('Are you sure you want to stop the translation progress?'))
            if action != 'yes':
                return
            stop_button.setDisabled(True)
            stop_button.setText(_('Stopping...'))
            self.trans_worker.set_canceled(True)
        stop_button.clicked.connect(stop_translation)

        def terminate_finished():
            stop_button.setDisabled(False)
            stop_button.setText(_('Stop'))
            self.paragraph_sig.emit(self.table.current_paragraph())
        self.trans_worker.finished.connect(terminate_finished)

        stack = QStackedWidget()
        stack.addWidget(action_widget)
        stack.addWidget(stop_widget)

        def working_start():
            stack.setCurrentWidget(stop_widget)
            action_widget.setDisabled(True)
        self.trans_worker.start.connect(working_start)

        def working_finished():
            stack.setCurrentWidget(action_widget)
            action_widget.setDisabled(False)
        self.trans_worker.finished.connect(working_finished)

        return stack

    def layout_control(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        cache_group = QGroupBox(_('Cache Status'))
        cache_layout = QVBoxLayout(cache_group)
        cache_status = QLabel(
            _('Enabled') if self.cache.is_persistence() else _('Disabled'))
        cache_status.setAlignment(Qt.AlignCenter)
        cache_status.setStyleSheet(
            'border-radius:2px;color:white;background-color:%s;'
            % ('green' if self.cache.is_persistence() else 'grey'))
        cache_layout.addWidget(cache_status)

        engine_group = QGroupBox(_('Translation Engine'))
        engine_layout = QVBoxLayout(engine_group)
        engine_list = EngineList(self.current_engine.name)
        engine_list.setMaximumWidth(150)
        engine_layout.addWidget(engine_list)

        source_group = QGroupBox(_('Source Language'))
        source_layout = QVBoxLayout(source_group)
        source_lang = SourceLang()
        source_lang.setMaximumWidth(150)
        source_layout.addWidget(source_lang)

        target_group = QGroupBox(_('Target Language'))
        target_layout = QVBoxLayout(target_group)
        target_lang = TargetLang()
        target_lang.setMaximumWidth(150)
        target_layout.addWidget(target_lang)

        title_group = QGroupBox(_('Custom Ebook Title'))
        title_layout = QHBoxLayout(title_group)
        custom_title = QCheckBox()
        ebook_title = QLineEdit()
        ebook_title.setToolTip(
            _('By default, title metadata will be translated.'))
        ebook_title.setText(self.ebook.title)
        ebook_title.setCursorPosition(0)
        ebook_title.setDisabled(True)
        title_layout.addWidget(custom_title)
        title_layout.addWidget(ebook_title)

        def enable_custom_title(checked):
            ebook_title.setDisabled(not checked)
            self.ebook.set_custom_title(
                ebook_title.text() if checked else None)
            if checked:
                ebook_title.setFocus(Qt.MouseFocusReason)
        custom_title.stateChanged.connect(enable_custom_title)

        def change_ebook_title():
            if ebook_title.text() == '':
                ebook_title.undo()
            self.ebook.set_custom_title(ebook_title.text())
        ebook_title.editingFinished.connect(change_ebook_title)

        # if self.config.get('to_library'):
        #     ebook_title.setDisabled(True)
        #     ebook_title.setToolTip(_(
        #         "The ebook's filename is automatically managed by Calibre "
        #         'according to metadata since the output path is set to '
        #         'Calibre Library.'))
        # ebook_title.textChanged.connect(self.ebook.set_custom_title)

        output_group = QGroupBox(_('Output Ebook'))
        output_layout = QHBoxLayout(output_group)
        output_button = QPushButton(_('Output'))
        output_format = OutputFormat()
        output_layout.addWidget(output_format)
        output_layout.addWidget(output_button)

        # Translation Style selector
        style_group = QGroupBox(_('Translation Style'))
        style_layout = QVBoxLayout(style_group)
        self.style_selector = QComboBox()
        self.style_selector.setMaximumWidth(180)
        self.style_selector.addItem(_('Literary (Fiction)'), 'literary')
        self.style_selector.addItem(_('Romance'), 'romance')
        self.style_selector.addItem(_('Thriller / Suspense'), 'thriller')
        self.style_selector.addItem(_('Historical Fiction'), 'historical')
        self.style_selector.addItem(_('Sci-Fi / Philosophical'), 'scifi_philosophical')
        self.style_selector.addItem(_('Business / Economy'), 'business')
        self.style_selector.addItem(_('Technical / Non-fiction'), 'technical')
        self.style_selector.addItem(_('Self-Help'), 'self_help')
        self.style_selector.addItem(_('Philosophy / Theology'), 'philosophy_theology')
        self.style_selector.addItem(_('Editing / Correcting'), 'editing')
        style_layout.addWidget(self.style_selector)
        
        # Set current style from config
        current_style = self.config.get('current_translation_style', 'literary')
        print(f"[STYLE DEBUG] Advanced Mode opened - loading style from config: '{current_style}'")
        for i in range(self.style_selector.count()):
            if self.style_selector.itemData(i) == current_style:
                self.style_selector.setCurrentIndex(i)
                break
        
        def change_translation_style(index):
            style = self.style_selector.itemData(index)
            print(f"[STYLE DEBUG] Style changed in Advanced Mode dropdown: '{style}'")
            self.config.update(current_translation_style=style)
            self.config.commit()  # Save to disk so translation engine reads it
            print(f"[STYLE DEBUG] Config saved with current_translation_style='{style}'")
        self.style_selector.currentIndexChanged.connect(change_translation_style)
        
        # Trigger initial style set on dialog open
        initial_index = self.style_selector.currentIndex()
        if initial_index >= 0:
            change_translation_style(initial_index)

        # Shutdown PC option
        shutdown_group = QGroupBox(_('After Completion'))
        shutdown_layout = QVBoxLayout(shutdown_group)
        self.shutdown_checkbox = QCheckBox(_('Shutdown PC when done'))
        self.shutdown_checkbox.setChecked(False)
        shutdown_layout.addWidget(self.shutdown_checkbox)

        # --- Gemini Context Cache button ---
        cache_btn_group = QGroupBox(_('Context Cache'))
        cache_btn_layout = QVBoxLayout(cache_btn_group)
        context_cache_btn = QPushButton(_('⚡ Manage'))
        context_cache_btn.setToolTip(
            _('Manage Gemini context cache to reduce API costs by ~75%'))
        context_cache_btn.setMaximumWidth(120)
        cache_btn_layout.addWidget(context_cache_btn)

        def open_cache_dialog():
            dialog = GeminiCacheDialog(self, self.ebook, self.current_engine)
            dialog.exec_()
        context_cache_btn.clicked.connect(open_cache_dialog)

        # Show cache button only for Gemini engines
        def update_cache_btn_visibility():
            is_gemini = issubclass(self.current_engine, GeminiTranslate)
            cache_btn_group.setVisible(is_gemini)
        update_cache_btn_visibility()

        layout.addWidget(cache_group)
        layout.addWidget(engine_group)
        layout.addWidget(source_group)
        layout.addWidget(target_group)
        layout.addWidget(style_group)
        layout.addWidget(cache_btn_group)
        layout.addWidget(title_group, 1)
        layout.addWidget(shutdown_group)
        layout.addWidget(output_group)

        source_lang.currentTextChanged.connect(
            self.trans_worker.set_source_lang)
        target_lang.currentTextChanged.connect(
            self.trans_worker.set_target_lang)

        def refresh_languages():
            source_lang.refresh.emit(
                self.current_engine.lang_codes.get('source'),
                self.ebook.source_lang,
                not isinstance(self.current_engine, CustomTranslate))
            target_lang.refresh.emit(
                self.current_engine.lang_codes.get('target'),
                self.ebook.target_lang)
        refresh_languages()
        self.ebook.set_source_lang(source_lang.currentText())

        def choose_engine(index):
            engine_name = engine_list.itemData(index)
            self.current_engine = get_engine_class(engine_name)
            self.trans_worker.set_engine_class(self.current_engine)
            self.batch_translation.emit()
            refresh_languages()
            update_cache_btn_visibility()
        engine_list.currentIndexChanged.connect(choose_engine)

        output_format.setCurrentText(self.ebook.output_format)

        def change_output_format(format):
            if self.ebook.is_extra_format():
                output_format.lock_format(self.ebook.input_format)
            self.ebook.set_output_format(format)
        change_output_format(output_format.currentText())
        output_format.currentTextChanged.connect(change_output_format)

        def output_ebook():
            if len(self.table.findItems(_('Translated'), Qt.MatchExactly)) < 1:
                self.alert.pop(_('The ebook has not been translated yet.'))
                return
            if self.table.non_aligned_count > 0:
                message = _(
                    'The number of lines in some translation units differs '
                    'between the original text and the translated text. Are '
                    'you sure you want to output without checking alignment?')
                if self.alert.ask(message) != 'yes':
                    return
            lang_code = self.current_engine.get_iso639_target_code(
                self.ebook.target_lang)
            self.ebook.set_lang_code(lang_code)
            self.worker.translate_ebook(self.ebook, cache_only=True)
            self.done(1)
        output_button.clicked.connect(output_ebook)

        def working_start():
            self.translate_all and widget.setVisible(False)
            widget.setDisabled(True)
        self.trans_worker.start.connect(working_start)

        def working_finished():
            widget.setVisible(True)
            widget.setDisabled(False)
        self.trans_worker.finished.connect(working_finished)

        return widget

    def layout_review(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        splitter = QSplitter(Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)
        raw_text = CodeEditor()
        raw_text.setReadOnly(True)
        original_text = SourceTextEditor(self)
        original_text.setTranslationCallback(self.translate_selected_with_engine)
        original_text.setReadOnly(True)
        translation_text = TranslationEditor(self)
        translation_text.setTranslationCallback(self.translate_selected_with_engine)
        self.translation_text_editor = translation_text  # Store reference for callback
        if self.ebook.target_direction == 'rtl':
            translation_text.setLayoutDirection(Qt.RightToLeft)
            document = translation_text.document()
            option = document.defaultTextOption()
            option.setAlignment(Qt.AlignRight)
            document.setDefaultTextOption(option)
        translation_text.setPlaceholderText(_('No translation yet'))
        splitter.addWidget(raw_text)
        splitter.addWidget(original_text)
        splitter.addWidget(translation_text)
        splitter.setSizes([0] + [int(splitter.height() / 2)] * 2)

        def synchronizeScrollbars(editors):
            for editor in editors:
                for other_editor in editors:
                    if editor != other_editor:
                        editor.verticalScrollBar().valueChanged.connect(
                            other_editor.verticalScrollBar().setValue)
        synchronizeScrollbars((raw_text, original_text, translation_text))

        translation_text.cursorPositionChanged.connect(
            translation_text.ensureCursorVisible)

        def refresh_translation(paragraph):
            # TODO: check - why/how can "paragraph" be None and what should we do in such case?
            if paragraph is not None:
                raw_text.setPlainText(paragraph.raw.strip())
                original_text.setPlainText(paragraph.original.strip())
                translation_text.setPlainText(paragraph.translation)

        self.paragraph_sig.connect(refresh_translation)

        self.trans_worker.start.connect(
            lambda: translation_text.setReadOnly(True))
        self.trans_worker.finished.connect(
            lambda: translation_text.setReadOnly(False))

        # default_flag = translation_text.textInteractionFlags()

        # def disable_translation_text():
        #     if self.trans_worker.on_working:
        #         translation_text.setTextInteractionFlags(Qt.TextEditable)
        #         end = getattr(QTextCursor.MoveOperation, 'End', None) \
        #             or QTextCursor.End
        #         translation_text.moveCursor(end)
        #     else:
        #         translation_text.setTextInteractionFlags(default_flag)
        # translation_text.cursorPositionChanged.connect(
        #     disable_translation_text)

        def auto_open_close_splitter():
            if splitter.sizes()[0] > 0:
                sizes = [0] + [int(splitter.height() / 2)] * 2
            else:
                sizes = [int(splitter.height() / 3)] * 3
            splitter.setSizes(sizes)

        self.install_widget_event(
            splitter, splitter.handle(1), QEvent.MouseButtonDblClick,
            auto_open_close_splitter)

        self.table.itemDoubleClicked.connect(
            lambda item: auto_open_close_splitter())

        control = QWidget()
        control_layout = QHBoxLayout(control)
        control_layout.setContentsMargins(0, 0, 0, 0)

        self.trans_worker.start.connect(
            lambda: control.setVisible(False))
        self.trans_worker.finished.connect(
            lambda: control.setVisible(True))

        save_status = QLabel()
        save_button = QPushButton(_('&Save'))
        save_button.setDisabled(True)

        status_indicator = TranslationStatus()

        # Block replacement checkbox - allows pasting text with different paragraph structure
        self.block_replacement_checkbox = QCheckBox(_('Allow block replacement'))
        self.block_replacement_checkbox.setToolTip(
            _('When enabled, pasted text replaces the segment without checking paragraph alignment. '
              'Use when pasting corrected text with different paragraph structure.'))

        control_layout.addWidget(status_indicator)
        control_layout.addWidget(self.block_replacement_checkbox)
        control_layout.addStretch(1)
        control_layout.addWidget(save_status)
        control_layout.addWidget(save_button)

        layout.addWidget(splitter)
        layout.addWidget(control)

        def update_translation_status(row):
            paragraph = self.table.paragraph(row)
            if paragraph is None:
                return
            if not paragraph.translation:
                if paragraph.error is not None:
                    status_indicator.set_color(
                        StatusColor('red'), paragraph.error)
                else:
                    status_indicator.set_color(StatusColor('gray'))
            elif not paragraph.aligned and self.merge_enabled:
                status_indicator.set_color(
                    StatusColor('yellow'), )
            elif getattr(paragraph, 'incomplete', False) and self.merge_enabled:
                status_indicator.set_color(
                    StatusColor('orange'),
                    _('Some translation segments are empty or suspiciously short'))
            else:
                status_indicator.set_color(StatusColor('green'))
        self.table.row.connect(update_translation_status)

        def change_selected_item():
            if self.trans_worker.on_working:
                return
            paragraph = self.table.current_paragraph()
            if paragraph is None:
                return
            self.paragraph_sig.emit(paragraph)
            self.table.row.emit(paragraph.row)
        self.table.setCurrentItem(self.table.item(0, 0))
        change_selected_item()
        self.table.itemSelectionChanged.connect(change_selected_item)

        def translation_callback(paragraph):
            self.table.row.emit(paragraph.row)
            self.paragraph_sig.emit(paragraph)
            self.cache.update_paragraph(paragraph)
            self.progress_bar.emit()
        self.trans_worker.callback.connect(translation_callback)

        def streaming_translation(data):
            if data == '':
                translation_text.clear()
            elif isinstance(data, Paragraph):
                self.table.setCurrentItem(self.table.item(data.row, 0))
            else:
                translation_text.insertPlainText(data)
        self.trans_worker.streaming.connect(streaming_translation)

        def modify_translation():
            if self.trans_worker.on_working and \
                    self.table.selected_count() > 1:
                return

            paragraph = self.table.current_paragraph()

            # TODO: check - why/how can "paragraph" be None and what should we
            # do in such case?
            if paragraph is not None:
                translation = translation_text.toPlainText()
                save_button.setDisabled(
                    translation == (paragraph.translation or ''))

        translation_text.textChanged.connect(modify_translation)

        self.editor_worker.show.connect(save_status.setText)

        def save_translation():
            paragraph = self.table.current_paragraph()

            # TODO: check - why/how can "paragraph" be None and what should we
            # do in such case?
            if paragraph is not None:
                save_button.setDisabled(True)
                translation = translation_text.toPlainText()
                paragraph.translation = translation
                paragraph.engine_name = self.current_engine.name
                paragraph.target_lang = self.ebook.target_lang
                
                # Block replacement mode: mark as aligned to skip validation
                if self.block_replacement_checkbox.isChecked():
                    paragraph.aligned = True
                    paragraph.error = None  # Clear any previous error
                
                self.table.row.emit(paragraph.row)
                self.cache.update_paragraph(paragraph)
                translation_text.setFocus(Qt.OtherFocusReason)
                self.editor_worker.start[str].emit(
                    _('Your changes have been saved.'))

        save_button.clicked.connect(save_translation)
        set_shortcut(save_button, 'save', save_translation, save_button.text())

        return widget

    def layout_log(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.logging_text = QPlainTextEdit()
        self.logging_text.setPlaceholderText(_('Translation log'))
        self.logging_text.setReadOnly(True)
        layout.addWidget(self.logging_text)

        return widget

    def layout_errors(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.errors_text = QPlainTextEdit()
        self.errors_text.setPlaceholderText(_('Error log'))
        self.errors_text.setReadOnly(True)
        layout.addWidget(self.errors_text)

        return widget

    def get_progress_step(self, total):
        return int(round(100.0 / (total or 1), 100) * 1000000)

    def translate_selected_with_engine(self, selected_text, engine_name):
        """Translate selected text using specified engine and show comparison dialog."""
        if not selected_text or self.trans_worker.on_working:
            return
        
        try:
            # Get the engine class by name
            engine_class = get_engine_class(engine_name)
            translator = get_translator(engine_class)
            translator.set_source_lang(self.ebook.source_lang)
            translator.set_target_lang(self.ebook.target_lang)
            
            # DEBUG: Log which engine is being used
            print(f"[DEBUG] Requested engine: {engine_name}")
            print(f"[DEBUG] Engine class: {engine_class}")
            print(f"[DEBUG] Engine class name: {engine_class.name}")
            print(f"[DEBUG] Translator type: {type(translator)}")
            print(f"[DEBUG] Translator endpoint: {getattr(translator, 'endpoint', 'N/A')}")
            
            # Perform translation
            result = translator.translate(selected_text)
            
            # Handle generator (streaming) or string result
            from types import GeneratorType
            if isinstance(result, GeneratorType):
                # Consume the generator to get the full text
                translated_text = ''.join(result)
            else:
                translated_text = result
            
            # DEBUG: Show result type
            print(f"[DEBUG] Result type: {type(result)}")
            print(f"[DEBUG] Translated text (first 100 chars): {translated_text[:100] if translated_text else 'EMPTY'}...")
            
            if translated_text:
                # Open comparison dialog with original and translated text  
                # Include engine class info in displayed name
                display_engine = f"{engine_name} ({engine_class.name})"
                dialog = TranslationCompareDialog(
                    parent=self,
                    original_text=selected_text,
                    translated_text=translated_text,
                    engine_name=display_engine
                )
                # Use show() instead of exec_() for non-modal dialog
                # This allows user to interact with main window while dialog is open
                dialog.show()
            else:
                self.alert.pop(_('No translation returned'), 'warning')
        except Exception as e:
            import traceback
            print(f"[DEBUG] Translation error: {traceback.format_exc()}")
            self.alert.pop(_('Translation error: {}').format(str(e)), 'warning')

    def translate_all_paragraphs(self):
        """Translate the untranslated paragraphs when at least one is selected.
        Otherwise, retranslate all paragraphs regardless of prior translation.
        """
        paragraphs = self.table.get_selected_paragraphs(True, True)
        is_fresh = len(paragraphs) < 1
        if is_fresh:
            paragraphs = self.table.get_selected_paragraphs(False, True)
        self.progress_step = self.get_progress_step(len(paragraphs))
        if not self.translate_all:
            message = _(
                'Are you sure you want to translate all {:n} paragraphs?')
            if self.alert.ask(message.format(len(paragraphs))) != 'yes':
                return
        self.translate_all = True
        self.trans_worker.translate.emit(paragraphs, is_fresh)

    def translate_selected_paragraph(self):
        paragraphs = self.table.get_selected_paragraphs()
        # Consider selecting all paragraphs as translating all.
        if len(paragraphs) == self.table.rowCount():
            self.translate_all_paragraphs()
        else:
            self.progress_step = self.get_progress_step(len(paragraphs))
            self.trans_worker.translate.emit(paragraphs, True)

    def merge_selected_rows(self):
        """Step 1: Merge 2-5 selected rows into one combined row."""
        if self.trans_worker.on_working:
            return

        paragraphs = self.table.get_selected_paragraphs()
        if len(paragraphs) < 2 or len(paragraphs) > 5:
            self.alert.pop(
                _('Select 2-5 rows to merge.'), 'warning')
            return

        # Warn about losing translations
        has_translations = any(p.translation for p in paragraphs)
        if has_translations:
            message = _(
                'Merging will discard existing translations for {} rows. '
                'Continue?')
            if self.alert.ask(message.format(len(paragraphs))) != 'yes':
                return

        # Use the engine separator for merging
        separator = getattr(self.current_engine, 'separator', '\n\n')
        result = self.table.merge_rows(paragraphs, separator)
        if result is None:
            return

        merged_paragraph, old_ids = result

        # Sync cache: delete old entries, add merged
        self.cache.replace_paragraphs(
            old_ids, [merged_paragraph])

        # Refresh the review panel
        self.paragraph_sig.emit(merged_paragraph)

        self.alert.pop(
            _('Merged {} rows into 1. Select it and use Re-Split '
              'to split with a different method.').format(len(paragraphs)))

    def resplit_selected_row(self):
        """Step 2: Re-split a single (merged) row with a different chunking method.

        Uses direct text splitting instead of the ElementHandler pipeline,
        because the handler treats each HTML element as atomic and can't
        split within a single element.
        """
        if self.trans_worker.on_working:
            return

        paragraphs = self.table.get_selected_paragraphs()
        if len(paragraphs) != 1:
            self.alert.pop(
                _('Select exactly 1 row to re-split.'), 'warning')
            return

        paragraph = paragraphs[0]
        merge_length = self.rechunk_chars.value()

        if len(paragraph.original) <= merge_length:
            self.alert.pop(
                _('Row is already under {} chars ({} chars). '
                  'No split needed.').format(
                    merge_length, len(paragraph.original)), 'info')
            return

        # Confirm
        method_name = self.rechunk_method.currentText()
        message = _(
            'Re-split this row ({} chars) into chunks of ~{} chars '
            'using "{}" method? Any existing translation will be lost.')
        if self.alert.ask(
                message.format(
                    len(paragraph.original), merge_length, method_name)
                ) != 'yes':
            return

        try:
            from .lib.utils import uid
            from .lib.cache import Paragraph
            import re

            text = paragraph.original
            raw = paragraph.raw

            # --- Direct text splitting ---
            # Strategy: split at natural boundaries (paragraph breaks,
            # then sentence endings) respecting merge_length.

            # Step 1: Split text into atomic segments (paragraphs)
            # Try double-newline first, then single newline
            segments = re.split(r'\n\s*\n', text)
            if len(segments) < 2:
                segments = text.split('\n')
            if len(segments) < 2:
                # Last resort: split at sentence boundaries
                segments = re.split(r'(?<=[.!?])\s+', text)
            if len(segments) < 2:
                # Absolute fallback: hard split at merge_length
                segments = []
                for i in range(0, len(text), merge_length):
                    segments.append(text[i:i + merge_length])

            # Step 2: Group segments into chunks respecting merge_length
            chunks = []
            current_chunk = []
            current_length = 0

            for segment in segments:
                seg_len = len(segment)
                if current_length + seg_len > merge_length and current_chunk:
                    # Flush current chunk
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [segment]
                    current_length = seg_len
                else:
                    current_chunk.append(segment)
                    current_length += seg_len

            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))

            # If only 1 chunk produced (e.g. one giant paragraph),
            # force-split at sentence boundaries within it
            if len(chunks) == 1 and len(chunks[0]) > merge_length:
                big_text = chunks[0]
                chunks = []
                sentences = re.split(r'(?<=[.!?])\s+', big_text)
                current_chunk = []
                current_length = 0
                for sentence in sentences:
                    s_len = len(sentence)
                    if current_length + s_len > merge_length and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = [sentence]
                        current_length = s_len
                    else:
                        current_chunk.append(sentence)
                        current_length += s_len
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

            # Still just 1? Hard character split as last resort
            if len(chunks) == 1 and len(chunks[0]) > merge_length:
                big_text = chunks[0]
                chunks = []
                for i in range(0, len(big_text), merge_length):
                    chunks.append(big_text[i:i + merge_length])

            # Step 3: Similarly split the raw HTML
            # If raw == original (plain text), use the same chunks
            # Otherwise, try to split raw by the same paragraph breaks
            raw_chunks = []
            if raw.strip() == text.strip() or '<' not in raw:
                raw_chunks = chunks[:]
            else:
                # For HTML raw, split similarly by double-newlines
                raw_segments = re.split(r'\n\s*\n', raw)
                if len(raw_segments) == len(segments):
                    # Perfect alignment — group raw_segments the same way
                    idx = 0
                    for chunk_text in chunks:
                        # Count how many segments this chunk consumed
                        count = chunk_text.count('\n\n') + 1
                        raw_chunk = '\n\n'.join(
                            raw_segments[idx:idx + count])
                        raw_chunks.append(raw_chunk)
                        idx += count
                else:
                    # Can't align — just use original text as raw
                    raw_chunks = chunks[:]

            # Step 4: Create Paragraph objects
            base_id = paragraph.id * 100
            new_paragraphs = []
            for i, (chunk, raw_chunk) in enumerate(
                    zip(chunks, raw_chunks)):
                new_id = base_id + i
                new_md5 = uid('%s%s' % (new_id, chunk))
                new_p = Paragraph(
                    id=new_id, md5=new_md5, raw=raw_chunk,
                    original=chunk, ignored=False,
                    attributes=paragraph.attributes,
                    page=paragraph.page)
                new_paragraphs.append(new_p)

            if len(new_paragraphs) < 2:
                self.alert.pop(
                    _('Could not split the text further. '
                      'Try a smaller character limit.'), 'warning')
                return

            # Replace in table
            position_row = paragraph.row
            old_id = paragraph.id
            self.table.replace_rows(
                position_row, paragraph, new_paragraphs)

            # Sync cache
            self.cache.replace_paragraphs(
                [old_id], new_paragraphs)

            # Refresh review panel
            if new_paragraphs:
                self.paragraph_sig.emit(new_paragraphs[0])

            # Report sizes
            sizes = ', '.join(
                str(len(p.original)) for p in new_paragraphs)
            self.alert.pop(
                _('Re-split into {} rows ({}). '
                  'Starting translation...').format(
                    len(new_paragraphs), sizes))

            # Auto-translate new rows
            self.progress_step = self.get_progress_step(
                len(new_paragraphs))
            self.trans_worker.translate.emit(new_paragraphs, True)

        except Exception as e:
            import traceback
            print(f'[RECHUNK ERROR] {traceback.format_exc()}')
            self.alert.pop(
                _('Re-split error: {}').format(str(e)), 'warning')

    def install_widget_event(
            self, source, target, action, callback, stop=False):
        def eventFilter(self, object, event):
            event.type() == action and callback()
            return stop
        source.eventFilter = MethodType(eventFilter, source)
        target.installEventFilter(source)

    def terminate_preparework(self):
        if self.preparation_worker.on_working:
            if self.preparation_worker.canceled:
                return False
            action = self.alert.ask(
                _('Are you sure you want to cancel the preparation progress?'))
            if action != 'yes':
                return False
            self.preparation_worker.set_canceled(True)
            self.preparation_worker.progress_message.emit('Canceling...')
            return False
        return True

    def terminate_translation(self):
        if self.trans_worker.on_working:
            action = self.alert.ask(
                _('Are you sure you want to cancel the translation progress?'))
            if action != 'yes':
                return False
            self.trans_worker.set_need_close(True)
            self.trans_worker.set_canceled(True)
            return False
        return True

    def show_shutdown_countdown(self):
        """Show a 60-second countdown dialog before shutting down the PC."""
        from qt.core import QMessageBox
        
        self.shutdown_canceled = False
        self.shutdown_seconds = 60
        
        # Create countdown dialog
        self.shutdown_dialog = QMessageBox(self)
        self.shutdown_dialog.setWindowTitle(_('Shutdown Countdown'))
        self.shutdown_dialog.setText(_('PC will shutdown in {} seconds...\n\nClick Cancel to abort.').format(self.shutdown_seconds))
        self.shutdown_dialog.setStandardButtons(QMessageBox.Cancel)
        self.shutdown_dialog.setIcon(QMessageBox.Warning)
        
        # Create timer
        self.shutdown_timer = QTimer()
        
        def update_countdown():
            self.shutdown_seconds -= 1
            if self.shutdown_seconds <= 0:
                self.shutdown_timer.stop()
                self.shutdown_dialog.accept()
                self.execute_shutdown()
            else:
                self.shutdown_dialog.setText(_('PC will shutdown in {} seconds...\n\nClick Cancel to abort.').format(self.shutdown_seconds))
        
        self.shutdown_timer.timeout.connect(update_countdown)
        self.shutdown_timer.start(1000)  # Update every second
        
        # Show dialog and handle cancel
        result = self.shutdown_dialog.exec_()
        if result == QMessageBox.Cancel:
            self.shutdown_timer.stop()
            self.shutdown_canceled = True
            self.alert.pop(_('Shutdown canceled.'))

    def show_dynamic_glossary_export(self):
        """Show export dialog if dynamic glossary has terms."""
        try:
            dg = self.session_dynamic_glossary
            if not dg:
                self.alert.pop(_('No dynamic glossary available.'), 'warning')
                return
            
            stats = dg.get_stats()
            if stats['total_unique_terms'] < 1:
                self.alert.pop(_('No terms detected yet. Translate some text first.'), 'info')
                return
            
            if stats['high_frequency_terms'] < 1:
                self.alert.pop(
                    _('Detected {} terms, but none appear 3+ times yet.').format(
                        stats['total_unique_terms']), 'info')
                return
            
            # Get master glossary path from config
            master_path = self.config.get(
                'glossary_path', 
                'glossary_master_ro.json'
            )
            
            # Show export dialog
            dialog = DynamicGlossaryExportDialog(dg, master_path, self)
            if dialog.exec_() == QDialog.DialogCode.Accepted:
                result = dialog.get_export_result()
                if result and result['added'] > 0:
                    self.alert.pop(
                        _('Exported {} terms to master glossary.').format(result['added']))
                elif result and result['skipped'] > 0:
                    self.alert.pop(
                        _('All {} terms already exist in glossary.').format(result['skipped']),
                        'warning')
        except Exception as e:
            self.alert.pop(_('Error showing glossary: {}').format(str(e)), 'error')

    def execute_shutdown(self):
        """Execute the system shutdown command."""
        import sys
        if sys.platform == 'win32':
            subprocess.call(['shutdown', '/s', '/t', '0'])
        elif sys.platform == 'darwin':
            subprocess.call(['osascript', '-e', 'tell app "System Events" to shut down'])
        else:  # Linux
            subprocess.call(['shutdown', '-h', 'now'])

    def done(self, result):
        if not self.terminate_preparework():
            return
        if not self.terminate_translation():
            return
        # self.preparation_thread.requestInterruption()
        self.preparation_thread.quit()
        self.preparation_thread.wait()
        self.trans_thread.quit()
        self.trans_thread.wait()
        self.editor_thread.quit()
        self.editor_thread.wait()
        if self.cache is not None:
            if self.cache.is_persistence():
                self.cache.close()
            elif result == 0:
                self.cache.destroy()
        QDialog.done(self, result)
