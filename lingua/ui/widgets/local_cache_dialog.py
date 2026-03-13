import os
import glob
import sqlite3
import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt

from lingua.core.i18n import _
from lingua.core.cache import TranslationCache
from lingua.core.utils import size_by_unit


class LocalCacheDialog(QDialog):
    """Dialog for managing local SQLite translation caches (*.db)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('📁 Local Translation DB Cache Manager'))
        self.resize(800, 500)
        self.cache_dir = TranslationCache.cache_path
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header Info
        header_text = _("Manage your local translation memory. These databases store the extracted text and translations for your EPUBs.")
        info_label = QLabel(header_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            _("Cache ID / Book"), _("Size"), _("Last Modified"), _("Segments"), _("File Path")
        ])
        
        # Table Styling
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(4, True) # Hide path column, keep data for deletion
        
        layout.addWidget(self.table)

        # Bottom Controls
        bottom_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton(_("Refresh"))
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self.load_data)
        
        self.delete_btn = QPushButton(_("🗑️ Delete Selected"))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a1a1a;
                color: #ff8888;
                border: 1px solid #7a2a2a;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7a2a2a;
                color: #ffaaaa;
            }
        """)
        self.delete_btn.clicked.connect(self._delete_selected)
        
        self.close_btn = QPushButton(_("Close"))
        self.close_btn.setFixedWidth(100)
        self.close_btn.clicked.connect(self.accept)

        bottom_layout.addWidget(self.refresh_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.delete_btn)
        bottom_layout.addWidget(self.close_btn)

        layout.addLayout(bottom_layout)

    def load_data(self):
        """Scan the cache directory for .db files and populate the table."""
        self.table.setRowCount(0)
        
        if not os.path.exists(self.cache_dir):
            return

        db_files = glob.glob(os.path.join(self.cache_dir, '*.db'))
        self.table.setRowCount(len(db_files))

        for row, path in enumerate(db_files):
            # 1. Cache ID / Name (Filename without extension by default)
            filename = os.path.basename(path)
            cache_id = os.path.splitext(filename)[0]
            
            # 2. File Size
            size_bytes = os.path.getsize(path)
            size_str = size_by_unit(size_bytes)
            
            # 3. Last Modified Date
            mtime = os.path.getmtime(path)
            mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

            # 4. Attempt to read metadata/counts from DB
            segments = "Unknown"
            try:
                # Open read-only connection to avoid locking issues
                uri = f"file:{path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                cursor = conn.cursor()
                
                # Try to get row count
                cursor.execute("SELECT COUNT(*) FROM cache")
                count = cursor.fetchone()[0]
                
                # Check translated
                cursor.execute("SELECT COUNT(*) FROM cache WHERE translation IS NOT NULL AND translation != ''")
                translated = cursor.fetchone()[0]
                
                segments = f"{translated}/{count}"
                
                # Optional: If you ever save book title in `info` table, read it here
                # cursor.execute("SELECT value FROM info WHERE key='title'")
                # title_row = cursor.fetchone()
                # if title_row: cache_id = title_row[0]
                
                conn.close()
            except sqlite3.Error:
                segments = "Error reading"
            except Exception:
                pass # E.g., table doesn't exist yet

            # Create items
            item_name = QTableWidgetItem(cache_id)
            item_name.setToolTip(cache_id)
            
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_date = QTableWidgetItem(mod_date)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_segs = QTableWidgetItem(segments)
            item_segs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_path = QTableWidgetItem(path)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
            self.table.setItem(row, 2, item_date)
            self.table.setItem(row, 3, item_segs)
            self.table.setItem(row, 4, item_path)

    def _delete_selected(self):
        """Delete selected cache .db files from disk."""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, _("No Selection"), _("Please select at least one cache file to delete."))
            return

        reply = QMessageBox.question(
            self,
            _("Confirm Deletion"),
            _("Are you sure you want to permanently delete the selected {0} local translation cache(s)?\n\nThis will wipe the translation memory for those books.").format(len(selected_rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for row in selected_rows:
                path_item = self.table.item(row, 4)
                if path_item:
                    file_path = path_item.text()
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        
                        # Also attempt to delete WAL/SHM temporary files if they exist
                        wal_path = file_path + "-wal"
                        shm_path = file_path + "-shm"
                        if os.path.exists(wal_path): os.remove(wal_path)
                        if os.path.exists(shm_path): os.remove(shm_path)
                            
                    except OSError as e:
                        QMessageBox.critical(self, _("Error"), _("Failed to delete {0}:\n{1}").format(os.path.basename(file_path), str(e)))

            self.load_data()
            QMessageBox.information(self, _("Success"), _("Successfully deleted {0} cache database(s).").format(deleted_count))
