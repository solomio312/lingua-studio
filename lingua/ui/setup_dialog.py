import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from lingua.core.config import get_config
from lingua.core.i18n import _

class SetupTranslationDialog(QDialog):
    """Dialog shown before opening a book to configure translation settings."""

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.config = get_config()
        self.setWindowTitle(_("Project Configuration"))
        self.setMinimumWidth(400)
        
        self.accepted_config = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Row 1: Input and Output Formats
        fmt_layout = QHBoxLayout()
        
        in_group = QVBoxLayout()
        in_label = QLabel(_("Input Format"))
        in_label.setObjectName('subtitle')
        self.input_format = QComboBox()
        self.input_format.addItems(["EPUB", "DOCX", "TXT", "SRT", "HTML", "PDF", "MOBI", "AZW3"])
        self.input_format.setCurrentText("EPUB")
        self.input_format.setMinimumHeight(32)
        in_group.addWidget(in_label)
        in_group.addWidget(self.input_format)
        
        out_group = QVBoxLayout()
        out_label = QLabel(_("Output Format"))
        out_label.setObjectName('subtitle')
        self.output_format = QComboBox()
        self.output_format.addItems(["EPUB", "DOCX", "TXT", "SRT", "HTML", "PDF", "MOBI", "AZW3"])
        self.output_format.setCurrentText("EPUB")
        self.output_format.setMinimumHeight(32)
        out_group.addWidget(out_label)
        out_group.addWidget(self.output_format)
        
        fmt_layout.addLayout(in_group)
        fmt_layout.addSpacing(20)
        fmt_layout.addLayout(out_group)
        layout.addLayout(fmt_layout)
        
        layout.addSpacing(10)
        
        # Row 2: Languages and Directionality
        lang_layout = QHBoxLayout()
        
        src_group = QVBoxLayout()
        src_label = QLabel(_("Source Language"))
        src_label.setObjectName('subtitle')
        self.source_lang = QComboBox()
        self.source_lang.addItems(["Auto detect", "English", "French", "German", "Spanish", "Italian", "Romanian", "Russian", "Chinese", "Japanese"])
        # Map Auto back to Auto detect if needed
        curr_src = self.config.get('source_lang', 'Auto detect')
        self.source_lang.setCurrentText(curr_src if curr_src != 'Auto' else 'Auto detect')
        self.source_lang.setMinimumHeight(32)
        src_group.addWidget(src_label)
        src_group.addWidget(self.source_lang)
        
        tgt_group = QVBoxLayout()
        tgt_label = QLabel(_("Target Language"))
        tgt_label.setObjectName('subtitle')
        self.target_lang = QComboBox()
        self.target_lang.addItems(["Romanian", "English", "French", "German", "Spanish", "Italian", "Russian", "Chinese", "Japanese"])
        self.target_lang.setCurrentText(self.config.get('target_lang', 'Romanian'))
        self.target_lang.setMinimumHeight(32)
        tgt_group.addWidget(tgt_label)
        tgt_group.addWidget(self.target_lang)
        
        dir_group = QVBoxLayout()
        dir_label = QLabel(_("Target Directionality"))
        dir_label.setObjectName('subtitle')
        self.direction = QComboBox()
        self.direction.addItems(["Auto", "Left to Right (LTR)", "Right to Left (RTL)"])
        self.direction.setCurrentText(self.config.get('target_direction', 'Auto'))
        self.direction.setMinimumHeight(32)
        dir_group.addWidget(dir_label)
        dir_group.addWidget(self.direction)
        
        lang_layout.addLayout(src_group)
        lang_layout.addSpacing(10)
        lang_layout.addLayout(tgt_group)
        lang_layout.addSpacing(10)
        lang_layout.addLayout(dir_group)
        layout.addLayout(lang_layout)
        
        layout.addSpacing(20)
        
        # Row 3: Start Button
        self.start_btn = QPushButton(_("Start"))
        self.start_btn.setObjectName('primary')
        self.start_btn.setMinimumHeight(36)
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)

    def _on_start(self):
        # Save to config
        src = self.source_lang.currentText()
        if src == 'Auto detect': src = 'Auto'
        
        self.config.update(source_lang=src)
        self.config.update(target_lang=self.target_lang.currentText())
        self.config.update(target_direction=self.direction.currentText())
        self.config.commit()
        
        self.accepted_config = True
        self.accept()
