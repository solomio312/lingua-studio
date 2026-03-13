"""
Project card widget for the Dashboard.

Shows a card for a recent/loaded EPUB project with:
- Book title and author
- Cover image thumbnail (if available)
- Translation progress indicator
- Click to open project
"""

import os

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QFont

from lingua.core.i18n import _


class ProjectCard(QFrame):
    """A clickable card representing an EPUB project."""

    clicked = Signal(str)  # emits the file path
    remove_requested = Signal(str) # emits the file path to remove

    def __init__(self, file_path, title='', author='',
                 progress=0, cover_data=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setObjectName('projectCard')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(180)
        self.setMaximumWidth(400)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.setToolTip(_("Loading statistics..."))
        self._build_ui(title, author, progress, cover_data)

    def _build_ui(self, title, author, progress, cover_data):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Cover image container
        self.cover_label = QLabel()
        self.cover_label.setObjectName("coverImage")
        self.cover_label.setMinimumSize(120, 120)
        self.cover_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Store original pixmap to resample on resize
        self._og_pixmap = None
        if cover_data:
            pix = QPixmap()
            pix.loadFromData(cover_data)
            self._og_pixmap = pix
        else:
            self.cover_label.setText('No Cover')
            self.cover_label.setObjectName('subtitle')
                
        layout.addWidget(self.cover_label, 1)

        # Title
        title_text = title or os.path.basename(self.file_path)
        title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName('title')
        
        # Proper truncation (2 lines max approx)
        metrics = title_label.fontMetrics()
        elided_text = metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, 228 * 2)
        title_label.setText(elided_text)
        title_label.setWordWrap(True)
        title_label.setFixedHeight(40)
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_label)

        # Author
        if author:
            author_label = QLabel(author)
            author_label.setObjectName('subtitle')
            layout.addWidget(author_label)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(progress)
        progress_bar.setFixedHeight(6)
        progress_bar.setTextVisible(False)
        layout.addWidget(progress_bar)

        layout.addStretch()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Dynamically scale cover to fit new width while keeping aspect ratio
        if self._og_pixmap and not self._og_pixmap.isNull():
            target_width = self.cover_label.width()
            target_height = self.cover_label.height()
            scaled_pixmap = self._og_pixmap.scaled(
                target_width, target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.cover_label.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = QMenu(self)
        
        remove_act = QAction(_("❌ Remove from History"), self)
        remove_act.triggered.connect(lambda: self.remove_requested.emit(self.file_path))
        menu.addAction(remove_act)
        menu.exec(event.globalPos())

    def enterEvent(self, event):
        if self.toolTip() == _("Loading statistics..."):
            self._generate_tooltip()
        super().enterEvent(event)

    def _generate_tooltip(self):
        from lingua.core.cache import TranslationCache, get_cache
        import os
        import glob
        import sqlite3
        
        try:
            target_title = os.path.basename(self.file_path)
            best_cache_id = None
            best_mtime = 0
            
            # Find the most recently modified database for this book title
            if os.path.exists(TranslationCache.cache_path):
                for db_path in glob.glob(os.path.join(TranslationCache.cache_path, '*.db')):
                    cid = os.path.splitext(os.path.basename(db_path))[0]
                    try:
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        cur.execute("SELECT value FROM info WHERE key='title'")
                        title_res = cur.fetchone()
                        conn.close()
                        
                        if title_res and title_res[0] == target_title:
                            mtime = os.path.getmtime(db_path)
                            if mtime > best_mtime:
                                best_mtime = mtime
                                best_cache_id = cid
                    except Exception:
                        pass
            
            if not best_cache_id:
                self.setToolTip(_("New project. No statistics extracted yet."))
                return

            cache = get_cache(best_cache_id)
            cursor = cache.connection.cursor()
            
            # Progress stats
            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN translation IS NOT NULL AND translation != '' THEN 1 ELSE 0 END) FROM cache WHERE NOT ignored")
            res = cursor.fetchone()
            if not res or res[0] == 0:
                self.setToolTip(_("New project. DB exists but is empty."))
                return
                
            total_p = res[0] or 0
            trans_p = res[1] or 0
            percentage = int((trans_p / total_p) * 100) if total_p > 0 else 0
            
            # Overall chars
            cursor.execute("SELECT SUM(LENGTH(original)), SUM(LENGTH(translation)) FROM cache WHERE NOT ignored")
            chars_res = cursor.fetchone()
            total_orig_chars = chars_res[0] or 0
            total_trans_chars = chars_res[1] or 0

            # Engine stats & Cost
            cursor.execute("SELECT engine_name, SUM(LENGTH(original)), SUM(LENGTH(translation)) FROM cache WHERE translation IS NOT NULL AND translation != '' GROUP BY engine_name")
            engine_stats = cursor.fetchall()

            # Find unaligned rows (basic metric: different number of <br> or paragraphs)
            # A simple SQL approach is length minus length without \n, but let's just do a fetch for unaligned.
            # Actually, doing it via length diff of replace('\n') is standard SQL count of newlines.
            cursor.execute("""
                SELECT COUNT(*) FROM cache 
                WHERE translation IS NOT NULL AND translation != '' AND NOT ignored
                AND (LENGTH(original) - LENGTH(REPLACE(original, char(10), ''))) != 
                    (LENGTH(translation) - LENGTH(REPLACE(translation, char(10), '')))
            """)
            unaligned_count = cursor.fetchone()[0] or 0
            
            lines = [f"<div style='background-color:#2a2c33; color:#eee; padding:8px; border-radius: 4px; font-size: 11px;'>"]
            lines.append(f"<b style='color:#648cff; font-size: 13px;'>{os.path.basename(self.file_path)}</b><hr style='border: 1px solid #444;'>")
            
            lines.append(f"📊 <b>Progres Traducere:</b> {percentage}% ({trans_p} / {total_p} segmente)<br>")
            lines.append(f"✍️ <b>Caractere (Generale):</b> {total_orig_chars:,} Src / {total_trans_chars:,} Trans<br>")
            
            if unaligned_count > 0:
                lines.append(f"⚠️ <b>" + _("Segmente Nealiniate:") + f"</b> <span style='color: #fbbf24;'><b>{unaligned_count}</b> " + _("row(s) have unequal paragraphs") + "</span><br>")
            else:
                lines.append(f"✅ <b>" + _("Segmente Nealiniate:") + "</b> " + _("0 rows found") + "<br>")
            
            total_cost = 0.0
            if engine_stats:
                lines.append("<br><b>Mecanisme Folosite:</b><br>")
                for engine, orig_len, trans_len in engine_stats:
                    orig_len = orig_len or 0
                    trans_len = trans_len or 0
                    engine_name = engine or "Unknown API"
                    
                    # Cost Estimate (Gemini 1.5/2.5 Flash reference)
                    tok_in = orig_len / 4.0
                    tok_out = trans_len / 4.0
                    cost = (tok_in / 1_000_000 * 0.075) + (tok_out / 1_000_000 * 0.30)
                    total_cost += cost
                    
                    lines.append(f"• <i>{engine_name}</i>: {orig_len:,} -> {trans_len:,} caractere<br>")
            
            if total_cost > 0:
                lines.append(f"<br>💰 <b>Cost Estimat (Gemini Flash):</b> ${total_cost:.4f}")
                
            lines.append("</div>")
            self.setToolTip("".join(lines))
        except Exception as e:
            self.setToolTip(_("Project statistics cannot be loaded."))

