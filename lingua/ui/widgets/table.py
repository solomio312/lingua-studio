"""
Professional Workspace Table for Translation.
Migrated from the Calibre plugin components/table.py.
Provides advanced filtering, context menus, and visual alignment diagnostics.
"""

from PySide6.QtWidgets import (
    QTableWidget, QHeaderView, QMenu, QAbstractItemView, QTableWidgetItem,
    QMessageBox, QFrame, QVBoxLayout, QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QColor, QBrush, QCursor

from lingua.core.translation import get_engine_class
from lingua.core.i18n import _
from lingua.core.license import LicenseManager
from .alignment_dialog import AlignmentDialog
from .gated_widgets import show_pro_required_dialog



class HoverPopup(QFrame):
    """Scrollable tooltip-like popup for long original text."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setObjectName('hoverPopup')
        self.setFixedWidth(450)
        self.setFixedHeight(180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.text_display = QPlainTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFrameStyle(QFrame.Shape.NoFrame)
        self.text_display.setObjectName('logConsole') # Reuse the dark styling
        layout.addWidget(self.text_display)
        
        self.setWindowOpacity(0.96)

    def set_content(self, text):
        self.text_display.setPlainText(text)
        self.text_display.verticalScrollBar().setValue(0)

class WorkspaceTable(QTableWidget):
    """Advanced table for managing translated paragraphs."""
    
    # Emits when a row is manually selected by user
    row_selected = Signal(int)
    # Emits paragraphs that need translation from the context menu
    translate_requested = Signal(list)
    # Emits paragraphs to merge
    merge_requested = Signal(list)
    # Emits a paragraph to split
    split_requested = Signal(object)
    # Emits a paragraph to align manually
    align_requested = Signal(object)
    # Emits rows to delete
    delete_requested = Signal(list)
    # Emits when a row is double-clicked
    row_double_clicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paragraphs = []
        self._setup_ui()
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.cellDoubleClicked.connect(lambda r, c: self.row_double_clicked.emit(r))
        
        # Hover logic
        self.setMouseTracking(True)
        self.hover_popup = HoverPopup()
        self.hover_popup.hide()
        self.last_hovered_row = -1
        
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_hover_popup)
        self.current_hover_pos = QPoint()
        
    def _setup_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['#', 'Original', 'Chars', 'Engine', 'Language', 'Status'])
        self.verticalHeader().setVisible(False) # Hide the default row numbers
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 40)
        self.setColumnWidth(2, 60)
        self.setColumnWidth(3, 110)
        self.setColumnWidth(4, 90)
        self.setColumnWidth(5, 100)
        
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        
        # Table styles are now handled globally by ThemeManager

    def populate(self, paragraphs):
        """Populate the table with paragraphs."""
        self.paragraphs = paragraphs
        self.setRowCount(len(paragraphs))
        
        for i, paragraph in enumerate(paragraphs):
            paragraph.row = i
            
            # Row number
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 0, num_item)
            
            # Original text
            orig_item = QTableWidgetItem()
            orig_item.setData(Qt.ItemDataRole.UserRole, paragraph)
            self.setItem(i, 1, orig_item)
            
            # Translation text (Hidden but kept in memory for side panel)
            # We don't create an item for column 2 anymore if we want to follow exactly the image
            # Wait, the column count is 6, so: 0=#, 1=Orig, 2=Chars, 3=Engine, 4=Lang, 5=Status
            
            # Chars
            chars_item = QTableWidgetItem()
            chars_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 2, chars_item)
            
            # Engine
            eng_item = QTableWidgetItem()
            eng_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 3, eng_item)
            
            # Language
            lang_item = QTableWidgetItem()
            lang_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 4, lang_item)
            
            # Status
            status_item = QTableWidgetItem()
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 5, status_item)
            
            self.update_row(i)

    def update_row(self, row_index):
        """Update display values and evaluate alignment/diagnostics for a row."""
        if row_index >= len(self.paragraphs): return
        p = self.paragraphs[row_index]
        
        orig_text = p.original.replace('\n', ' ') if p.original else ''
        
        # 1. Original
        self.item(row_index, 1).setText(orig_text)
        
        # 2. Chars
        char_count = len(orig_text)
        chars_item = self.item(row_index, 2)
        chars_item.setText(str(char_count))
        
        # Recommendation for short segments
        if char_count < 150:
            chars_item.setForeground(QColor(255, 140, 0)) # Orange
            tip = _("Small segment detected (< 150 chars).\nRecommendation: Use 'Google Free New' for speed/quality balance.")
            chars_item.setToolTip(tip)
        else:
            chars_item.setForeground(QBrush(Qt.BrushStyle.NoBrush).color()) # Reset to default
            chars_item.setToolTip("")
        
        # 3. Engine
        engine_name = getattr(p, 'engine_name', '') or ''
        # Strip long names for UI beauty
        disp_engine = engine_name.replace('(Free)', '').replace('Translate', '').strip()
        self.item(row_index, 3).setText(disp_engine)
        
        # 4. Language
        target_lang = getattr(p, 'target_lang', '') or ''
        self.item(row_index, 4).setText(target_lang)
        
        # 5. Determine Status
        temp_status = getattr(p, '_temp_status', '').lower()
        if p.translation:
            status = 'Done'
        elif p.error:
            status = 'Error'
        elif temp_status:
            # Capitalize status (e.g. translating -> Translating)
            status = temp_status.capitalize()
            if status == 'Translating': status = 'Translating...'
        else:
            status = 'Pending'
            
        self.item(row_index, 5).setText(status)
        
        # Reset colors
        self._set_row_background(row_index, QBrush(Qt.BrushStyle.NoBrush), "")
        self.item(row_index, 5).setForeground(QColor(128, 128, 128)) # Default
        
        if p.error:
            self._set_row_background(row_index, QBrush(QColor(100, 0, 0, 150)), p.error)
            self.item(row_index, 5).setForeground(QColor(255, 100, 100))
        elif status == 'Translating...':
            self._set_row_background(row_index, QBrush(QColor(0, 50, 100, 150)), "Translating...")
            self.item(row_index, 5).setForeground(QColor(100, 150, 255))
        elif p.translation:
            self.item(row_index, 5).setForeground(QColor(100, 255, 100))
            self._check_alignment(p, row_index)

    def _check_alignment(self, paragraph, row_index):
        """Check segment alignment logic and style row."""
        # Use default engine if none was saved
        engine_name = paragraph.engine_name if paragraph.engine_name else None
        engine = get_engine_class(engine_name)
        if not engine:
            return
            
        separator = getattr(engine, 'separator', '\n\n')
        if paragraph.is_alignment(separator):
            # All good, now check incomplete
            details = paragraph.alignment_details(separator)
            if details['missing'] or details['suspicious']:
                bg = QBrush(QColor(200, 100, 0, 80)) # Orange
                self._set_row_background(row_index, bg, _("⚠️ Traducerea are segmente lipsă sau suspicios de scurte."))
            else:
                paragraph.aligned = True
        else:
            paragraph.aligned = False
            details = paragraph.alignment_details(separator)
            bg = QBrush(QColor(150, 150, 0, 80)) # Yellowish for misalignment
            tip = _("⚠️ Misaligned: {orig} originals vs {trans} translations.").format(orig=details['orig_count'], trans=details['trans_count'])
            self._set_row_background(row_index, bg, tip)

    def _set_row_background(self, row, brush, tooltip=''):
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(brush)
                # Note: We use our custom hover popup for the Original column,
                # but keep the status tooltip for others.
                if col != 1 and tooltip:
                    item.setToolTip(tooltip)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        self.hover_popup.hide()
        self.last_hovered_row = -1
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        """Track mouse for hover-to-view original text."""
        pos = event.pos()
        item = self.itemAt(pos)
        
        if item and item.column() == 1: # Original column
            row = item.row()
            if row != self.last_hovered_row:
                self.last_hovered_row = row
                self.current_hover_pos = event.globalPosition().toPoint()
                self.hover_timer.start(300) # 300ms delay to avoid flickering
        else:
            self.hover_timer.stop()
            self.hover_popup.hide()
            self.last_hovered_row = -1
            
        super().mouseMoveEvent(event)

    def _show_hover_popup(self):
        row = self.last_hovered_row
        if row != -1 and row < len(self.paragraphs):
            p = self.paragraphs[row]
            if p and p.original:
                self.hover_popup.set_content(p.original)
                # Position popup near cursor but offset to avoid blocking usage
                self.hover_popup.move(self.current_hover_pos.x() + 25, self.current_hover_pos.y() + 15)
                self.hover_popup.show()

    def _on_selection_changed(self):
        selected = self.selectedItems()
        print(f"DEBUG TABLE: selection changed, items: {len(selected)}", flush=True)
        if selected:
            # Always base the row dynamically
            self.row_selected.emit(selected[0].row())
        else:
            self.row_selected.emit(-1)
            
    def get_selected_paragraphs(self):
        rows = list(set([item.row() for item in self.selectedItems()]))
        rows.sort()
        return [self.paragraphs[r] for r in rows if r < len(self.paragraphs)]

    def contextMenuEvent(self, event):
        """Handle right-click context menu with advanced operations."""
        menu = QMenu(self)
        
        selected = self.get_selected_paragraphs()
        if not selected:
            return

        # 1. Translation Actions
        menu.addAction(_('🔄 Translate Selected Rows'), self._emit_translate)
        
        # 2. Structure Actions
        menu.addSeparator()
        if len(selected) > 1:
            menu.addAction(_('🔗 Merge {n} Rows').format(n=len(selected)), self._emit_merge)
        if len(selected) == 1:
            menu.addAction(_('✂️ Split Current Row'), self._emit_split)

        # 3. Alignment Actions (for translated rows)
        translated = [p for p in selected if p.translation]
        if translated:
            menu.addSeparator()
            if len(translated) == 1:
                p = translated[0]
                
                align_text = _('📐 Manual Alignment...')
                if not LicenseManager.is_pro():
                    align_text += " 🔒"
                
                menu.addAction(align_text, lambda: self._on_manual_align_clicked(p))
                menu.addAction(_('🔍 Alignment Details'), lambda: self._show_alignment_details(p))
                menu.addAction(_('⚡ Auto-Align (Proportional Split)'), lambda: self._auto_split_paragraph(p))
            
            menu.addAction(_('✅ Mark as Verified'), self._emit_verify)

        # 4. Management
        menu.addSeparator()
        menu.addAction(_('🗑️ Șterge rândurile selectate'), self._emit_delete)

        menu.exec(event.globalPos())

    def _on_manual_align_clicked(self, p):
        """Handle manual alignment click with Pro gating."""
        if not LicenseManager.is_pro():
            show_pro_required_dialog(self.window(), _("Manual Alignment"))
            return
        self._emit_align(p)

    def _show_alignment_details(self, p):
        """Show a diagnostic popup with segment comparison."""
        engine = get_engine_class(getattr(p, 'engine_name', None))
        sep = getattr(engine, 'separator', '\n\n')
        details = p.alignment_details(sep)
        
        msg = f"<b>Sumar Aliniament:</b><br>"
        msg += f"- Segmente Originale: {details['orig_count']}<br>"
        msg += f"- Segmente Traduse: {details['trans_count']}<br><br>"
        
        if details['orig_count'] == details['trans_count']:
            msg += _("<font color='green'>✅ Aliniat perfect.</font>")
        else:
            msg += _("<font color='red'>❌ Dezaliniat.</font>")
            
        if details['missing']:
            msg += f"<br><br><font color='#fbbf24'>{_('⚠️ Segmente Goale')}: {len(details['missing'])} (ex: {', '.join(map(str, [m+1 for m in details['missing'][:3]]))}...)</font>"
            
        QMessageBox.information(self, _("🔍 Alignment Details"), msg)

    def _auto_split_paragraph(self, p):
        """Attempt to split translation proportionally to match original segments."""
        import re
        engine = get_engine_class(getattr(p, 'engine_name', None))
        sep = getattr(engine, 'separator', '\n\n')
        
        text = p.translation.strip()
        # Collapse multi-newlines to single split point for logic
        raw_text = re.sub(r'\n\n+', '\n', text)
        
        pattern = re.compile(re.escape(sep))
        orig_parts = pattern.split(p.original.strip())
        target_count = len(orig_parts)
        
        if target_count <= 1: return
        
        # Proportional split logic
        sentences = re.split(r'(?<=[.!?…])\s+', text)
        orig_lens = [len(pt.strip()) for pt in orig_parts]
        total_orig = sum(orig_lens) or 1
        
        new_parts = []
        if len(sentences) >= target_count:
            idx = 0
            for i in range(target_count):
                alloc = max(1, round((orig_lens[i]/total_orig) * len(sentences)))
                new_parts.append(" ".join(sentences[idx:idx+alloc]))
                idx += alloc
        else:
            words = text.split()
            idx = 0
            if len(words) >= target_count:
                for i in range(target_count):
                    alloc = max(1, round((orig_lens[i]/total_orig) * len(words)))
                    new_parts.append(" ".join(words[idx:idx+alloc]))
                    idx += alloc
                    
        if len(new_parts) == target_count:
            p.translation = sep.join(new_parts)
            p.aligned = True
            self.update_row(p.row)
            QMessageBox.information(self, "Auto-Split", _("Translation was automatically aligned via proportional distribution."))
        else:
            QMessageBox.warning(self, "Auto-Split", _("Automatic alignment failed. Insufficient punctuation or words."))

    def _emit_translate(self):
        self.translate_requested.emit(self.get_selected_paragraphs())
        
    def _emit_merge(self):
        selected = self.get_selected_paragraphs()
        if len(selected) > 1:
            self.merge_requested.emit(selected)
        
    def _emit_split(self):
        selected = self.get_selected_paragraphs()
        if len(selected) == 1:
            self.split_requested.emit(selected[0])

    def _emit_align(self, p):
        self.align_requested.emit(p)

    def _emit_delete(self):
        selected = self.get_selected_paragraphs()
        if not selected: return
        
        msg = _("Are you sure you want to delete the {n} selected rows?\nThis action cannot be undone.").format(n=len(selected))
        reply = QMessageBox.question(self, _("Delete Rows"), msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(selected)

    def _emit_verify(self):
        """Mark selected paragraphs as aligned/verified manually."""
        for p in self.get_selected_paragraphs():
            p.aligned = True
            p.error = None
            self.update_row(p.row)
