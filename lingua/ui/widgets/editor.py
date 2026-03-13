"""
Professional Translation Editors for Split View.
Migrated from the Calibre plugin components/editor.py.
Provides syntax-highlighting-like line numbers and context menu translation actions.
"""

from PySide6.QtWidgets import (
    QWidget, QPlainTextEdit, QTextEdit, QMenu, QDialog, QSplitter,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
)
from PySide6.QtGui import QColor, QTextFormat, QCursor, QPainter, QPaintEvent
from PySide6.QtCore import Qt, QSize

from lingua.core.i18n import _


class TranslationCompareDialog(QDialog):
    """Dialog showing original text and translation side by side (vertically split).
    Non-modal to allow interaction with the main window."""
    
    def __init__(self, parent=None, original_text='', translated_text='', engine_name=''):
        super().__init__(parent)
        self.setWindowTitle(_('🔁 Compare Translation'))
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        # Make dialog non-modal so user can interact with main window
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Clean up when closed
        
        layout = QVBoxLayout(self)
        
        # Header with engine info
        header = QLabel(_('📝 Engine: {name}').format(name=engine_name))
        header.setStyleSheet('font-weight: bold; font-size: 12px; padding: 5px;')
        layout.addWidget(header)
        
        # Splitter with two text panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Original text panel
        original_container = QWidget()
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_label = QLabel(_('📖 Original Text:'))
        original_label.setStyleSheet('font-weight: bold; color: #555;')
        original_layout.addWidget(original_label)
        
        self.original_editor = QPlainTextEdit()
        self.original_editor.setPlainText(original_text)
        self.original_editor.setReadOnly(True)
        self.original_editor.setStyleSheet(
            'background-color: #22242a; border: 1px solid #333; padding: 5px; color: #dcdee4;')
        original_layout.addWidget(self.original_editor)
        splitter.addWidget(original_container)
        
        # Translation text panel
        translation_container = QWidget()
        translation_layout = QVBoxLayout(translation_container)
        translation_layout.setContentsMargins(0, 0, 0, 0)
        translation_label = QLabel(_('🌐 Translation:'))
        translation_label.setStyleSheet('font-weight: bold; color: #648cff;')
        translation_layout.addWidget(translation_label)
        
        self.translation_editor = QPlainTextEdit()
        self.translation_editor.setPlainText(translated_text)
        self.translation_editor.setReadOnly(False)  # Editable for manual corrections
        self.translation_editor.setStyleSheet(
            'background-color: #1a1b20; border: 1px solid #648cff; padding: 5px; color: #dcdee4;')
        translation_layout.addWidget(self.translation_editor)
        splitter.addWidget(translation_container)
        
        # Equal sizes for both panels
        splitter.setSizes([250, 250])
        layout.addWidget(splitter, 1)
        
        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        copy_button = QPushButton(_('📋 Copy Translation'))
        copy_button.clicked.connect(self.copy_translation)
        button_layout.addWidget(copy_button)
        
        close_button = QPushButton(_('✖ Close'))
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def copy_translation(self):
        """Copy translation text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.translation_editor.toPlainText())
    
    def get_translation(self):
        """Return the (possibly edited) translation text."""
        return self.translation_editor.toPlainText()


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1b20;
                color: #dcdee4;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        
        from PySide6.QtWidgets import QSizePolicy
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

    def lineNumberAreaWidth(self):
        digits = 1
        count = self.blockCount()
        while count >= 10:
            count //= 10
            digits += 1
        return self.fontMetrics().horizontalAdvance('9') * digits + 10

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.lineNumberArea.setGeometry(
            rect.left(), rect.top(), self.lineNumberAreaWidth(), rect.height())

    def lineNumberAreaPaintEvent(self, event: QPaintEvent):
        painter = QPainter(self.lineNumberArea)
        try:
            painter.fillRect(event.rect(), QColor(34, 36, 42))  # #22242a equivalent
            block = self.firstVisibleBlock()
            blockNumber = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(
                self.contentOffset()).top()
            bottom = top + self.blockBoundingGeometry(block).height()

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = str(blockNumber + 1)
                    painter.setPen(QColor(100, 100, 110))
                    painter.drawText(
                        0, int(top), self.lineNumberArea.width() - 5,
                        self.fontMetrics().height(),
                        Qt.AlignmentFlag.AlignRight, number)

                block = block.next()
                top = bottom
                bottom += self.blockBoundingGeometry(block).height()
                blockNumber += 1
        finally:
            painter.end()

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(
                0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly() and self.toPlainText() != '':
            selection = QTextEdit.ExtraSelection()

            lineColor = QColor(100, 140, 255, 40) # Soft blue highlight
            selection.format.setBackground(lineColor)
            selection.format.setProperty(
                QTextFormat.Property.FullWidthSelection, True)

            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()

            extraSelections.append(selection)

        self.setExtraSelections(extraSelections)


class LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


# Available free translation engines
FREE_ENGINES = [
    ('🤖 Gemini', 'Gemini'),
    ('🌐 Google (Free) New', 'Google(Free)New'),
    ('🌐 Google (Free) Old', 'Google(Free)'),
    ('🔷 Microsoft Edge (Free)', 'MicrosoftEdge(Free)'),
    ('🔵 DeepL (Free)', 'DeepL(Free)'),
]


class SourceTextEditor(CodeEditor):
    """CodeEditor for original/source text with translation context menu options."""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_dialog = parent
        self.translate_callback = None
    
    def setTranslationCallback(self, callback):
        """Set the callback function for translation."""
        self.translate_callback = callback
    
    def contextMenuEvent(self, event):
        """Override to add translation options to the context menu."""
        menu = self.createStandardContextMenu()
        
        # Only add translation options if there's selected text and a callback
        if self.textCursor().hasSelection() and self.translate_callback:
            menu.addSeparator()
            # Qt uses \u2029 (paragraph separator) instead of \n - convert it back
            selected_text = self.textCursor().selectedText().replace('\u2029', '\n')
            
            # Add submenu for translation engines
            translate_menu = menu.addMenu(_("🔄 Translate with..."))
            
            for label, engine_name in FREE_ENGINES:
                action = translate_menu.addAction(label)
                # Use default argument to capture engine_name properly in closure
                action.triggered.connect(
                    lambda checked, txt=selected_text, eng=engine_name: 
                    self.translate_callback(txt, eng))
        
        menu.exec(event.globalPos())


class TranslationEditor(CodeEditor):
    """CodeEditor with translation context menu options."""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_dialog = parent
        self.translate_callback = None
        self.current_paragraph = None
    
    def setTranslationCallback(self, callback):
        """Set the callback function for translation."""
        self.translate_callback = callback
    
    def setParagraph(self, paragraph):
        """Set the current paragraph being displayed."""
        self.current_paragraph = paragraph
    
    def contextMenuEvent(self, event):
        """Override to add translation options to the context menu."""
        menu = self.createStandardContextMenu()
        
        # Only add translation options if there's selected text and a callback
        if self.textCursor().hasSelection() and self.translate_callback:
            menu.addSeparator()
            # Qt uses \u2029 (paragraph separator) instead of \n - convert it back
            selected_text = self.textCursor().selectedText().replace('\u2029', '\n')
            
            # Add submenu for translation engines
            translate_menu = menu.addMenu(_("🔄 Translate with..."))
            
            for label, engine_name in FREE_ENGINES:
                action = translate_menu.addAction(label)
                # Use default argument to capture engine_name properly in closure
                action.triggered.connect(
                    lambda checked, txt=selected_text, eng=engine_name: 
                    self.translate_callback(txt, eng))
        
        menu.exec(event.globalPos())
