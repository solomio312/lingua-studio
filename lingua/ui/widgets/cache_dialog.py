import os
import json
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QGroupBox, QComboBox, QLineEdit, QSizePolicy,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from lingua.core.config import get_config
from lingua.core.license import LicenseManager
from lingua.core.conversion import extract_item
from lingua.engines.gemini_cache import (
    GeminiCacheManager, save_cache_metadata, load_cache_metadata,
    delete_cache_metadata, estimate_cache_cost, estimate_session_cost,
    MIN_CACHE_TOKENS
)
from lingua.core.translation import get_translator, get_engine_class
from lingua.core.i18n import _

class CacheDialog(QDialog):
    """Dialog for creating and managing Gemini context caches.
    Adapted from original plugin GeminiCacheDialog.
    """

    def __init__(self, parent, epub_path, book_title, current_engine_name):
        super().__init__(parent)
        self.epub_path = epub_path
        self.book_title = book_title
        self.engine_name = current_engine_name
        self.config = get_config()
        
        if not LicenseManager.is_pro():
            QMessageBox.warning(self, _("Pro Feature"), _("The Context Cache Manager is a Pro-only feature."))
            # We delay the close to ensure dialog is fully initialized if needed, 
            # but since this is __init__ and we haven't exec'd yet, it's safer to flag or throw.
            # However, for QDialog, we can just block the UI.
            
        self.setWindowTitle(_('⚡ Gemini Context Cache Manager') + ("" if LicenseManager.is_pro() else " (PRO)"))
        self.setMinimumWidth(580)
        self.setMinimumHeight(520)
        self.setMinimumWidth(580)
        self.setMinimumHeight(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Info section ---
        info_label = QLabel(_(
            '<b>Context Caching</b> uploads your book text to Gemini servers '
            'so each translation chunk costs ~75% less on input tokens.<br>'
            '<i>Requires: versioned model (e.g. gemini-2.0-flash-001), '
            '≥32K tokens (~130K chars)</i>'))
        info_label.setWordWrap(True)
        info_label.setObjectName('subtitle')
        layout.addWidget(info_label)

        # --- Model + TTL row ---
        config_layout = QHBoxLayout()

        model_group = QGroupBox('Model (versioned)')
        model_inner = QHBoxLayout(model_group)
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.addItems([
            'gemini-2.0-flash-001',
            'gemini-1.5-flash-001',
            'gemini-1.5-pro-001',
            'gemini-2.0-flash-lite-preview-02-05',
        ])
        current_model = self.config.get('gemini_model', 'gemini-1.5-flash-001')
        self.model_input.setCurrentText(current_model)
        model_inner.addWidget(self.model_input)
        config_layout.addWidget(model_group, 3)

        ttl_group = QGroupBox('TTL (hours)')
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
        self.status_text.setObjectName('logConsole')
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(120)
        status_layout.addWidget(self.status_text)
        layout.addWidget(status_group)

        # --- Row 1: Dry Run + Create ---
        row1 = QHBoxLayout()
        self.dryrun_btn = QPushButton(_('🔢 Dry Run (Count Tokens)'))
        
        self.create_btn = QPushButton(_('📤 Create Cache'))
        self.create_btn.setObjectName('primary')
        
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

        # --- Row 3: DELETE ---
        self.delete_btn = QPushButton(_('🗑️  DELETE CACHE'))
        self.delete_btn.setObjectName('danger_btn')
        layout.addWidget(self.delete_btn)

        # --- Connections ---
        self.dryrun_btn.clicked.connect(self._on_dry_run)
        self.create_btn.clicked.connect(self._on_create_cache)
        self.check_btn.clicked.connect(self._on_check_status)
        self.extend_btn.clicked.connect(self._on_extend_ttl)
        self.delete_btn.clicked.connect(self._on_delete_cache)
        self.activate_btn.clicked.connect(self._on_activate_cache)
        self.deactivate_btn.clicked.connect(self._on_deactivate_cache)

        # Gating internal buttons as a second layer of defense
        if not LicenseManager.is_pro():
            for btn in [self.create_btn, self.dryrun_btn, self.extend_btn, self.activate_btn, self.delete_btn]:
                btn.setEnabled(False)
                btn.setToolTip(_("Pro license required to use this feature."))

        self._refresh_status()

    @Slot(str)
    def _log(self, message):
        self.status_text.appendPlainText(message)

    def _get_manager(self):
        # In Lingua, we get API key from config for the Gemini engine
        engine_prefs = self.config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        api_key = gemini_prefs.get('api_key', '')
        
        # Fallback to general engine if not specifically in Gemini prefs
        if not api_key:
            api_key = self.config.get('api_key', '')
            
        if not api_key:
            self._log('ERROR: No Gemini API key found. Configure it in Settings.')
            return None
            
        proxy_uri = self.config.get('proxy_uri', None)
        return GeminiCacheManager(api_key, proxy_uri)

    def _extract_text(self):
        """Extract all text from the book for caching context."""
        try:
            self._log('Extracting ebook items...')
            elements = extract_item(self.epub_path, 'epub', 'utf-8')
            if not elements:
                self._log('ERROR: No text found in EPUB.')
                return None, None
                
            text = '\n\n'.join([e.get_content() for e in elements if e.get_content().strip()])
            
            # Simple system instruction
            source_lang = self.config.get('source_lang', 'Auto')
            target_lang = self.config.get('target_lang', 'Romanian')
            
            instruction = f"Translate from {source_lang} to {target_lang}."
            # In a real scenario, we'd grab the full prompt from the engine configuration
            
            return text, instruction
        except Exception as e:
            self._log(f'ERROR: {str(e)}')
            return None, None

    def _refresh_status(self):
        self.status_text.clear()
        metadata = load_cache_metadata(self.epub_path)
        if metadata:
            self._log('Cache metadata found:')
            self._log(f'  - Name: {metadata.get("cache_name")}')
            self._log(f'  - Model: {metadata.get("model")}')
            self._log(f'  - Created: {metadata.get("created_at")}')
            self._log(f'  - Tokens: {metadata.get("token_count", 0):,}')
            self._log(f'  - TTL: {metadata.get("ttl_hours")}h')
            
            # Check if active
            engine_prefs = self.config.get('engine_preferences', {})
            gemini_prefs = engine_prefs.get('Gemini', {})
            active_name = gemini_prefs.get('cached_content_name', '')
            
            if active_name == metadata.get('cache_name'):
                self._log('\n✅ STATUS: ACTIVE for current translations.')
            else:
                self._log('\n⚠️ STATUS: INACTIVE (Cache exists but not used).')
        else:
            self._log('No context cache found for this book.')
            self._log('Run "Dry Run" to estimate size and cost.')

    def _on_dry_run(self):
        manager = self._get_manager()
        if not manager: return
        
        model = self.model_input.currentText().strip()
        self._log(f'\n--- Dry Run ({model}) ---')
        
        text, instr = self._extract_text()
        if not text: return
        
        try:
            self._log('Counting tokens via Gemini API...')
            tokens = manager.count_tokens(text, model, instr)
            self._log(f'Estimated Tokens: {tokens:,}')
            
            if tokens < MIN_CACHE_TOKENS:
                self._log(f'❌ BELOW MINIMUM ({MIN_CACHE_TOKENS}). Caching NOT allowed.')
            else:
                self._log(f'✅ READY for caching.')
                
            # Cost estimate
            cost = estimate_cache_cost(tokens, model, float(self.ttl_input.text() or 24))
            if cost:
                self._log(f'Approx storage cost: ${cost["storage_cost_total"]:.4f} total')
                self._log(f'Input token savings: {cost["discount_pct"]}%')
        except Exception as e:
            self._log(f'❌ Failed: {str(e)}')

    def _on_create_cache(self):
        manager = self._get_manager()
        if not manager: return
        
        model = self.model_input.currentText().strip()
        ttl = float(self.ttl_input.text() or 24)
        
        self._log(f'\n--- Creating Context Cache ({model}) ---')
        text, instr = self._extract_text()
        if not text: return
        
        try:
            display_name = f"Lingua_{self.book_title[:60]}"
            self._log('Uploading to Google servers (this may take a few minutes)...')
            result = manager.create_cache(text, instr, model, display_name, ttl)
            
            cache_name = result.get('name')
            token_count = result.get('usageMetadata', {}).get('totalTokenCount', 0)
            
            self._log(f'✅ Cache Created: {cache_name}')
            
            # Save metadata
            save_cache_metadata(self.epub_path, cache_name, model, display_name, ttl, token_count)
            self.config.set('gemini_model', model)
            self._refresh_status()
            QMessageBox.information(self, "Success", "Context cache created successfully.")
        except Exception as e:
            self._log(f'❌ Creation failed: {str(e)}')

    def _on_check_status(self):
        manager = self._get_manager()
        if not manager: return
        metadata = load_cache_metadata(self.epub_path)
        if not metadata: return
        
        self._log('\n--- Checking Server Status ---')
        valid, info = manager.is_cache_valid(metadata['cache_name'])
        if valid:
            self._log(f'✅ Server says: {info}')
        else:
            self._log(f'❌ Server says: {info}')

    def _on_extend_ttl(self):
        manager = self._get_manager()
        if not manager: return
        metadata = load_cache_metadata(self.epub_path)
        if not metadata: return
        
        ttl = float(self.ttl_input.text() or 24)
        try:
            manager.update_cache_ttl(metadata['cache_name'], ttl)
            self._log(f'✅ TTL extended to {ttl}h.')
            save_cache_metadata(self.epub_path, metadata['cache_name'], metadata['model'], 
                               metadata['display_name'], ttl, metadata.get('token_count', 0))
        except Exception as e:
            self._log(f'❌ Failed: {str(e)}')

    def _on_activate_cache(self):
        metadata = load_cache_metadata(self.epub_path)
        if not metadata:
            QMessageBox.warning(self, "Error", "No cache metadata found.")
            return
            
        # Update engine preferences to use this cache
        engine_prefs = self.config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        gemini_prefs['cached_content_name'] = metadata['cache_name']
        engine_prefs['Gemini'] = gemini_prefs
        self.config.set('engine_preferences', engine_prefs)
        
        self._log('\n✅ Cache ACTIVATED for the Gemini engine.')
        self._refresh_status()

    def _on_deactivate_cache(self):
        engine_prefs = self.config.get('engine_preferences', {})
        gemini_prefs = engine_prefs.get('Gemini', {})
        if 'cached_content_name' in gemini_prefs:
            del gemini_prefs['cached_content_name']
        engine_prefs['Gemini'] = gemini_prefs
        self.config.set('engine_preferences', engine_prefs)
        
        self._log('\n⛔ Cache DEACTIVATED.')
        self._refresh_status()

    def _on_delete_cache(self):
        manager = self._get_manager()
        if not manager: return
        metadata = load_cache_metadata(self.epub_path)
        if not metadata: return
        
        reply = QMessageBox.question(self, "Delete Cache", 
                                     "Are you sure you want to delete this cache from Google servers?\nCosts stop immediately.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                manager.delete_cache(metadata['cache_name'])
                delete_cache_metadata(self.epub_path)
                self._on_deactivate_cache()
                self._log('\n🗑️ Cache deleted from server and local metadata.')
                self._refresh_status()
            except Exception as e:
                self._log(f'❌ Deletion failed: {str(e)}')
