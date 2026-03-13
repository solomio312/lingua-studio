import os
import glob
import sqlite3
import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QBrush

from lingua.core.i18n import _
from lingua.core.cache import TranslationCache
from lingua.core.utils import size_by_unit


class NumericTableWidgetItem(QTableWidgetItem):
    """Custom item for numeric and date sorting."""
    def __init__(self, text, sort_val):
        super().__init__(text)
        self.sort_val = sort_val

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_val < other.sort_val
        return super().__lt__(other)


class LocalCacheDialog(QDialog):
    """Dialog for managing local SQLite translation caches (*.db)."""

    def __init__(self, parent=None, active_cache_id=None):
        super().__init__(parent)
        self.setWindowTitle(_('📁 Local Translation DB Cache Manager'))
        self.resize(800, 500)
        self.cache_dir = TranslationCache.cache_path
        self.active_cache_id = active_cache_id
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
        
        # Sorting
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        
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

        # Disable sorting while loading to prevent performance lag
        self.table.setSortingEnabled(False)
        
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
            display_name = cache_id
            method_info = ""
            conn = None
            try:
                # Open read-only connection to avoid locking issues
                uri = f"file:{path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                cursor = conn.cursor()
                
                # Check for book title
                try:
                    cursor.execute("SELECT value FROM info WHERE key='title'")
                    title_row = cursor.fetchone()
                    if title_row and title_row[0]:
                        display_name = title_row[0]
                except: pass

                # Check for chunking method
                try:
                    cursor.execute("SELECT value FROM info WHERE key='chunking_method'")
                    c_row = cursor.fetchone()
                    cursor.execute("SELECT value FROM info WHERE key='merge_length'")
                    m_row = cursor.fetchone()
                    if c_row:
                        method_info = f"Method: {c_row[0]}"
                        if m_row: method_info += f" ({m_row[0]} chars)"
                except: pass

                # Try to get row count
                cursor.execute("SELECT COUNT(*) FROM cache")
                count = cursor.fetchone()[0]
                
                # Check translated
                cursor.execute("SELECT COUNT(*) FROM cache WHERE translation IS NOT NULL AND translation != ''")
                translated = cursor.fetchone()[0]
                
                segments = f"{translated}/{count}"
            except sqlite3.Error:
                segments = "Error reading"
            except Exception:
                pass # E.g., table doesn't exist yet
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                # Explicitly delete references
                del cursor
                del conn
                import gc
                gc.collect()

            # Create items with custom sorting
            item_name = QTableWidgetItem(display_name)
            item_name.setToolTip(f"ID: {cache_id}")
            
            item_size = NumericTableWidgetItem(size_str, size_bytes)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_date = NumericTableWidgetItem(mod_date, mtime)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_segs = QTableWidgetItem(segments)
            item_segs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if method_info:
                item_segs.setToolTip(method_info)
            
            item_path = QTableWidgetItem(path)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
            self.table.setItem(row, 2, item_date)
            self.table.setItem(row, 3, item_segs)
            self.table.setItem(row, 4, item_path)

            # Highlight active cache
            if self.active_cache_id and cache_id == self.active_cache_id:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it:
                        it.setBackground(QBrush(QColor(40, 60, 40)))
                        it.setForeground(QBrush(QColor(100, 255, 100)))
                        it.setToolTip(_("ACTIVE: This cache is currently in use by the open project and cannot be deleted."))
        
        # Re-enable sorting
        self.table.setSortingEnabled(True)
        # Sort by date descending by default
        self.table.sortItems(2, Qt.SortOrder.DescendingOrder)

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
                # Safety check: Is this the active cache?
                name_item = self.table.item(row, 0)
                path_item = self.table.item(row, 4)
                
                if name_item and self.active_cache_id:
                    # The name item tooltip or some other property could store the ID if display_name is title
                    # But we can reconstruct ID from path filename if needed.
                    filename = os.path.basename(path_item.text())
                    cid = os.path.splitext(filename)[0]
                    if cid == self.active_cache_id:
                        QMessageBox.warning(self, _("Locked Resource"), _("The cache for the currently open book ('{0}') cannot be deleted while the project is active.\n\nPlease close the project first.").format(name_item.text()))
                        continue

                if path_item:
                    file_path = path_item.text()
                    try:
                        # Before deleting, run garbage collector to release any lingering handles
                        import gc
                        import time
                        gc.collect()
                        
                        # Handle Windows locks: wait a tiny bit if needed
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except OSError:
                                time.sleep(0.1) # Brief pause
                                gc.collect()
                                os.remove(file_path) # Retry once
                        
                        deleted_count += 1
                        
                        # Also attempt to delete WAL/SHM temporary files if they exist
                        wal_path = file_path + "-wal"
                        shm_path = file_path + "-shm"
                        if os.path.exists(wal_path): 
                            try: os.remove(wal_path)
                            except: pass
                        if os.path.exists(shm_path): 
                            try: os.remove(shm_path)
                            except: pass
                            
                    except OSError as e:
                        QMessageBox.critical(self, _("Error"), _("Failed to delete {0}:\n{1}").format(os.path.basename(file_path), str(e)))

            self.load_data()
            QMessageBox.information(self, _("Success"), _("Successfully deleted {0} cache database(s).").format(deleted_count))
