import re
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QScrollArea, QWidget, QPushButton, QSplitter, QFrame, QSizePolicy,
    QGridLayout, QApplication, QListWidget, QListWidgetItem, QAbstractItemView,
    QMenu
)
from PySide6.QtCore import Qt, Signal, Slot, QSize, QPropertyAnimation, QPoint, QEasingCurve
from PySide6.QtGui import QCursor, QColor, QAction

from lingua.core.translation import get_translator
from lingua.core.config import get_config
from lingua.core.i18n import _

class HoverSegmentWidget(QFrame):
    """
    A segment widget that provides a 'Piano Effect' (slight horizontal shift) on hover.
    Used for both original and translation segments.
    """
    text_changed = Signal()
    copy_requested = Signal(object)
    translate_requested = Signal(object)

    def __init__(self, text, is_original=True, translator=None, parent=None):
        super().__init__(parent)
        self.is_original = is_original
        self.translator = translator
        self.setObjectName('segmentWidget')
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Style for the widget container
        self.setStyleSheet("""
            #segmentWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 4px;
                margin: 2px;
            }
            #segmentWidget:hover {
                background-color: #2a2a2a;
                border: 1px solid #3b82f6;
            }
            QPlainTextEdit {
                background: transparent;
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.editor = QPlainTextEdit(text)
        self.editor.setPlaceholderText(_("Segment gol..."))
        if is_original:
            self.editor.setReadOnly(True)
            self.editor.setStyleSheet("color: #d1d1d1;")
        else:
            self.editor.setStyleSheet("color: #ffffff;")
            self.editor.textChanged.connect(lambda: self.text_changed.emit())

        # Granular Controls for Translation segments
        self.controls = QWidget()
        ctrl_layout = QHBoxLayout(self.controls)
        ctrl_layout.setContentsMargins(0, 5, 0, 0)
        ctrl_layout.setSpacing(5)

        if not is_original:
            self.btn_copy = QPushButton("→")
            self.btn_copy.setToolTip(_("Copy corresponding original here"))
            self.btn_copy.setFixedWidth(30)
            self.btn_copy.setStyleSheet("font-size: 10px; padding: 2px;")
            
            self.btn_trans = QPushButton("🌐")
            self.btn_trans.setToolTip(_("Traduce acest segment"))
            self.btn_trans.setFixedWidth(30)
            self.btn_trans.setStyleSheet("font-size: 10px; padding: 2px;")
            self.btn_trans.setEnabled(self.translator is not None)

            self.btn_copy.clicked.connect(self._on_copy_request)
            self.btn_trans.clicked.connect(self._on_translate)

            ctrl_layout.addStretch()
            ctrl_layout.addWidget(self.btn_copy)
            ctrl_layout.addWidget(self.btn_trans)
        
        layout.addWidget(self.editor)
        layout.addWidget(self.controls)
        
        # Hover Animation (Piano Effect)
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._original_pos = None

    def enterEvent(self, event):
        if self._original_pos is None:
            self._original_pos = self.pos()
        
        # Shift slightly right for original, slightly left for translation
        offset = 5 if self.is_original else -5
        self._anim.stop()
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(self._original_pos.x() + offset, self._original_pos.y()))
        self._anim.start()
        # Do not consume the event, let it pass to parent to allow dragging
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._original_pos is not None:
            self._anim.stop()
            self._anim.setStartValue(self.pos())
            self._anim.setEndValue(self._original_pos)
            self._anim.start()
        super().leaveEvent(event)

    def text(self):
        return self.editor.toPlainText().strip()

    def set_text(self, text):
        self.editor.setPlainText(text)

    def _on_copy_request(self):
        self.copy_requested.emit(self)

    def _on_translate(self):
        self.translate_requested.emit(self)

class AlignmentDialog(QDialog):
    """
    Advanced interactive alignment dialog with 'Piano Effect' and dual-column reordering.
    """
    def __init__(self, parent, paragraph, separator, cache=None, translator=None):
        super().__init__(parent)
        self.paragraph = paragraph
        self.separator = separator
        self.cache = cache
        self.translator = translator
        
        self.setWindowTitle(_('📐 Interactive Alignment (Dual-Pane)'))
        self.setMinimumSize(1000, 800)

        pattern = re.compile(re.escape(separator))
        self.orig_parts = pattern.split(paragraph.original.strip()) if paragraph.original else []
        self.trans_parts = pattern.split(paragraph.translation.strip()) if paragraph.translation else []

        # Pad to ensure UI looks balanced
        while len(self.trans_parts) < len(self.orig_parts):
            self.trans_parts.append('')
        
        self._build_ui()
        self._sync_scrollbars()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header Status
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3b82f6;")
        main_layout.addWidget(self.status_label)

        # Main Splitter for the two columns
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Original List
        self.orig_list = QListWidget()
        self.orig_list.setObjectName('origList')
        self.orig_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.orig_list.setSpacing(5)
        self.orig_list.setDragEnabled(False) # Typically originals don't move
        self.orig_list.setStyleSheet("QListWidget { background-color: #121212; border: none; padding: 10px; }")
        
        # Right: Translation List (Reorderable)
        self.trans_list = QListWidget()
        self.trans_list.setObjectName('transList')
        self.trans_list.setDragEnabled(True)
        self.trans_list.setAcceptDrops(True)
        self.trans_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.trans_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.trans_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.trans_list.setSpacing(5)
        self.trans_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trans_list.customContextMenuRequested.connect(self._on_trans_context_menu)
        self.trans_list.setStyleSheet("QListWidget { background-color: #121212; border: none; padding: 10px; }")
        
        # Connect internal drop update if needed
        self.trans_list.model().rowsMoved.connect(lambda: self._update_status())

        # Labels for columns
        col_header = QHBoxLayout()
        lbl_orig = QLabel(_("ORIGINAL"))
        lbl_orig.setStyleSheet("font-weight: bold; color: #a1a1aa; letter-spacing: 1px;")
        lbl_trans = QLabel(_("TRANSLATION (Drag&Drop Reorder)"))
        lbl_trans.setStyleSheet("font-weight: bold; color: #a1a1aa; letter-spacing: 1px;")
        
        col_header.addWidget(lbl_orig, 1)
        col_header.addSpacing(20)
        col_header.addWidget(lbl_trans, 1)
        main_layout.addLayout(col_header)

        # Populate
        self._populate_list(self.orig_list, self.orig_parts, is_original=True)
        self._populate_list(self.trans_list, self.trans_parts, is_original=False)

        self.splitter.addWidget(self.orig_list)
        self.splitter.addWidget(self.trans_list)
        main_layout.addWidget(self.splitter, 1)

        # Footer Actions (Bulk)
        bulk_layout = QHBoxLayout()
        bulk_layout.setSpacing(8)
        
        btn_auto = QPushButton(_("🔄 Proportional Distribution"))
        btn_auto.clicked.connect(self._auto_distribute)
        
        btn_copy_all = QPushButton(_("→→ Copy All"))
        btn_copy_all.clicked.connect(self._copy_all)
        
        btn_trans_all = QPushButton(_("🌐 Translate All"))
        btn_trans_all.setEnabled(self.translator is not None)
        btn_trans_all.clicked.connect(self._translate_all)
        
        bulk_layout.addWidget(btn_auto)
        bulk_layout.addWidget(btn_copy_all)
        bulk_layout.addWidget(btn_trans_all)
        bulk_layout.addStretch()
        
        main_layout.addLayout(bulk_layout)

        # Footer Actions (Edit)
        footer = QHBoxLayout()
        footer.setSpacing(10)
        
        btn_merge = QPushButton(_("🔗 Merge Selected"))
        btn_merge.setObjectName("secondary")
        btn_merge.clicked.connect(self._merge_selected_trans)
        
        btn_insert = QPushButton(_("➕ Alignment Row (Empty)"))
        btn_insert.clicked.connect(lambda: self._insert_empty_row())

        btn_delete = QPushButton(_("🗑 Delete"))
        btn_delete.setObjectName("danger_btn")
        btn_delete.clicked.connect(self._delete_selected_trans)
        
        footer.addWidget(btn_merge)
        footer.addWidget(btn_insert)
        footer.addWidget(btn_delete)
        footer.addStretch()
        
        btn_cancel = QPushButton(_("Cancel"))
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton(_("💾 Save"))
        btn_save.setObjectName("primary")
        btn_save.setMinimumWidth(120)
        btn_save.clicked.connect(self._save)
        
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_save)
        
        main_layout.addLayout(footer)
        self._update_status()

    def _populate_list(self, list_widget, items, is_original):
        list_widget.clear()
        for text in items:
            widget = HoverSegmentWidget(text, is_original=is_original, translator=self.translator)
            if not is_original:
                widget.text_changed.connect(self._update_status)
                widget.copy_requested.connect(self._copy_single_original)
                widget.translate_requested.connect(self._translate_single_segment)
            
            item = QListWidgetItem(list_widget)
            item.setSizeHint(QSize(0, 140))
            list_widget.addItem(item)
            list_widget.setItemWidget(item, widget)

    def _sync_scrollbars(self):
        """Synchronize vertical scrolling between the two columns."""
        sb_orig = self.orig_list.verticalScrollBar()
        sb_trans = self.trans_list.verticalScrollBar()
        
        sb_orig.valueChanged.connect(sb_trans.setValue)
        sb_trans.valueChanged.connect(sb_orig.setValue)

    def _update_status(self):
        orig_count = self.orig_list.count()
        trans_count = self.trans_list.count()
        
        if orig_count == trans_count:
            self.status_label.setText(_("✅ Perfect alignment: {n} segments.").format(n=orig_count))
            self.status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
        else:
            self.status_label.setText(_("⚠️ Misaligned: {orig} originals vs {trans} translations.").format(orig=orig_count, trans=trans_count))
            self.status_label.setStyleSheet("color: #fbbf24; font-weight: bold;")

    def _on_trans_context_menu(self, pos):
        menu = QMenu(self)
        merge_act = QAction(_("🔗 Merge selected"), self)
        merge_act.triggered.connect(self._merge_selected_trans)
        
        del_act = QAction(_("🗑 Delete segment(s)"), self)
        del_act.triggered.connect(self._delete_selected_trans)
        
        ins_act = QAction(_("➕ Insert empty row above"), self)
        ins_act.triggered.connect(lambda: self._insert_empty_row(self.trans_list.currentRow()))

        menu.addAction(ins_act)
        menu.addAction(merge_act)
        menu.addSeparator()
        menu.addAction(del_act)
        menu.exec(self.trans_list.mapToGlobal(pos))

    def _merge_selected_trans(self):
        selected_items = self.trans_list.selectedItems()
        if len(selected_items) < 2:
            return
            
        # Get indices and items to merge
        indices = sorted([self.trans_list.row(it) for it in selected_items])
        texts = []
        for idx in indices:
            widget = self.trans_list.itemWidget(self.trans_list.item(idx))
            if widget:
                texts.append(widget.text())
        
        merged_text = " ".join(texts)
        
        # Keep the first item, remove others
        first_idx = indices[0]
        first_widget = self.trans_list.itemWidget(self.trans_list.item(first_idx))
        if first_widget:
            first_widget.set_text(merged_text)
            
        # Remove others in reverse order
        for idx in reversed(indices[1:]):
            self.trans_list.takeItem(idx)
            
        self._update_status()

    def _insert_empty_row(self, index=-1):
        if index == -1:
            index = self.trans_list.count()
            
        widget = HoverSegmentWidget("", is_original=False, translator=self.translator)
        widget.text_changed.connect(self._update_status)
        
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 140))
        self.trans_list.insertItem(index, item)
        self.trans_list.setItemWidget(item, widget)
        self._update_status()

    def _delete_selected_trans(self):
        selected = self.trans_list.selectedItems()
        if not selected: return
        
        for item in selected:
            self.trans_list.takeItem(self.trans_list.row(item))
        self._update_status()

    def _save(self):
        sep = self.separator
        
        # Collect originals
        orig_segments = []
        for i in range(self.orig_list.count()):
            w = self.orig_list.itemWidget(self.orig_list.item(i))
            if w: orig_segments.append(w.text())
            
        # Collect translations
        trans_segments = []
        for i in range(self.trans_list.count()):
            w = self.trans_list.itemWidget(self.trans_list.item(i))
            if w: trans_segments.append(w.text())
            
        self.paragraph.original = sep.join(orig_segments)
        self.paragraph.translation = sep.join(trans_segments)
        self.paragraph.aligned = (len(orig_segments) == len(trans_segments))
        self.paragraph.error = None
        
        if self.cache:
            self.cache.update_paragraph(self.paragraph)
            
        self.accept()

    def _copy_single_original(self, widget):
        row = self.trans_list.row(self.trans_list.itemAt(widget.pos()))
        # This is not very precise. Let's find by looking through items.
        for i in range(self.trans_list.count()):
            if self.trans_list.itemWidget(self.trans_list.item(i)) == widget:
                # Found the row. Match with orig_list if it exists.
                if i < self.orig_list.count():
                    orig_w = self.orig_list.itemWidget(self.orig_list.item(i))
                    if orig_w:
                        widget.set_text(orig_w.text())
                break

    def _translate_single_segment(self, widget):
        for i in range(self.trans_list.count()):
            if self.trans_list.itemWidget(self.trans_list.item(i)) == widget:
                if i < self.orig_list.count():
                    orig_w = self.orig_list.itemWidget(self.orig_list.item(i))
                    if orig_w:
                        text = orig_w.text()
                        if not text: return
                        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                        try:
                            result = self.translator.translate(text)
                            translated = "".join(result) if not isinstance(result, str) else result
                            widget.set_text(translated.strip())
                        except Exception as e:
                            widget.set_text(f"ERROR: {str(e)}")
                        finally:
                            QApplication.restoreOverrideCursor()
                break

    def _copy_all(self):
        """Copy all originals to their corresponding translation slots."""
        count = min(self.orig_list.count(), self.trans_list.count())
        for i in range(count):
            orig_w = self.orig_list.itemWidget(self.orig_list.item(i))
            trans_w = self.trans_list.itemWidget(self.trans_list.item(i))
            if orig_w and trans_w:
                trans_w.set_text(orig_w.text())

    def _translate_all(self):
        """Translate all segments using the current engine."""
        if not self.translator: return
        count = min(self.orig_list.count(), self.trans_list.count())
        for i in range(count):
            trans_w = self.trans_list.itemWidget(self.trans_list.item(i))
            if trans_w:
                self._translate_single_segment(trans_w)

    def _auto_distribute(self):
        """Proportional re-distribution of all combined translation text."""
        all_text_parts = []
        for i in range(self.trans_list.count()):
            widget = self.trans_list.itemWidget(self.trans_list.item(i))
            if widget:
                t = widget.text()
                if t: all_text_parts.append(t)
        
        all_trans_text = " ".join(all_text_parts)
        if not all_trans_text: return
        
        sentences = re.split(r'(?<=[.!?…])\s+', all_trans_text)
        target_count = self.orig_list.count()
        
        orig_lens = []
        for i in range(target_count):
            widget = self.orig_list.itemWidget(self.orig_list.item(i))
            orig_lens.append(len(widget.text()) if widget else 1)
            
        total_orig = sum(orig_lens) or 1
        
        # Ensure trans list matches orig count
        while self.trans_list.count() < target_count:
            self._insert_empty_row()
        while self.trans_list.count() > target_count:
            self.trans_list.takeItem(self.trans_list.count() - 1)

        if len(sentences) >= target_count:
            idx = 0
            for i in range(target_count):
                widget = self.trans_list.itemWidget(self.trans_list.item(i))
                alloc = max(1, round((orig_lens[i]/total_orig) * len(sentences)))
                widget.set_text(" ".join(sentences[idx:idx+alloc]))
                idx += alloc
        else:
            words = all_trans_text.split()
            idx = 0
            for i in range(target_count):
                widget = self.trans_list.itemWidget(self.trans_list.item(i))
                alloc = max(1, round((orig_lens[i]/total_orig) * len(words)))
                widget.set_text(" ".join(words[idx:idx+alloc]))
                idx += alloc
