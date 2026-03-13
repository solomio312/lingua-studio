"""
Main application window for Lingua.
"""

import os
import sys
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QFileDialog, QStatusBar, QMessageBox, QScrollArea,
    QFrame, QGridLayout,
)
from PySide6.QtCore import Qt, QSize, QMimeData, QThread, Signal, QRect, QPoint
from PySide6.QtGui import QFont, QColor, QPalette, QAction, QDragEnterEvent, QDropEvent, QIcon

import lingua
from lingua.core.config import get_config
from lingua.ui.settings_panel import SettingsPanel
from lingua.ui.widgets.project_card import ProjectCard
from lingua.ui.translation_workspace import TranslationWorkspace
from lingua.core.i18n import _
from lingua.ui.widgets.tour_overlay import TourOverlay
from lingua.ui.widgets.tutorial_dialog import GoogleCloudTutorialDialog

class CoverLoader(QThread):
    """Asynchronously loads EPUB covers so the UI doesn't freeze."""
    cover_loaded = Signal(str, bytes)
    
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        
    def run(self):
        import ebooklib
        from ebooklib import epub
        import os
        
        for path in self.paths:
            if not os.path.exists(path):
                continue
            try:
                book = epub.read_epub(path, options={"ignore_ncx": True})
                cover_data = None
                # Primary: defined in epub
                for item in book.get_items_of_type(ebooklib.ITEM_COVER):
                    cover_data = item.get_content()
                    break
                # Fallback: image with right name
                if not cover_data:
                    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                        if 'cover' in item.get_name().lower():
                            cover_data = item.get_content()
                            break
                            
                if cover_data:
                    self.cover_loaded.emit(path, cover_data)
            except Exception:
                pass


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self):
        super().__init__()
        import lingua
        from lingua.core.license import LicenseManager
        title = f'Lingua -- Ebook Translation Studio v{lingua.__version__}'
        if LicenseManager.is_pro():
            title += f" [{_('PRO / Registered User')}]"
        self.setWindowTitle(title)
        self.resize(1100, 750) # Larger default for workspace comfort
        self.setMinimumSize(850, 600) # Ensure it doesn't get too squashed
        self.setAcceptDrops(True)

        # Set Window Icon
        from lingua.core.utils import get_resource_path
        icon_path = get_resource_path(os.path.join('lingua', 'resources', 'icon.png'))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.config = get_config()
        self._build_ui()
        self._build_menu()
        self._build_statusbar()
        self._setup_tour()

        # Trigger tour if first run
        if not self.config.get('tour_completed', False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self.start_guided_tour)

    def _build_ui(self):
        """Build the main layout with sidebar + stacked content."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setIconSize(QSize(20, 20))

        items = ['📚  Dashboard', '🔧  Settings', '📖  About', '❓  Help Manual']
        for label in items:
            item = QListWidgetItem(_(label) if label[3:] in ['Dashboard', 'Settings', 'About', 'Help Manual'] else label)
            # Re-mapping labels to actual i18n keys
            clean_label = label[3:]
            item.setText(f"{label[:3]} {_(clean_label)}")
            item.setSizeHint(QSize(180, 44))
            self.sidebar.addItem(item)

        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_nav_change)
        main_layout.addWidget(self.sidebar)

        # --- Content Stack ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard())
        self.settings_panel = SettingsPanel()
        self.settings_panel.theme_changed.connect(self._on_theme_changed)
        self.settings_panel.load_legacy_project.connect(self._on_load_legacy_project)
        self.stack.addWidget(self.settings_panel)
        self.stack.addWidget(self._build_about())
        self.stack.addWidget(self._build_help_manual())
        main_layout.addWidget(self.stack, stretch=1)

    def _build_dashboard(self):
        """Build the project dashboard with project cards grid."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        # Branded Header
        header_frame = QFrame()
        header_frame.setObjectName('headerFrame')
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        title = QLabel('Lingua')
        title.setObjectName('mainTitle')
        header_layout.addWidget(title)
        
        motto = QLabel(_('Designed for those for whom books are sanctuaries.'))
        motto.setObjectName('motto')
        header_layout.addWidget(motto)
        
        layout.addWidget(header_frame)
        layout.addSpacing(25)

        # Dedicated Drop Zone Header
        drop_frame = QFrame()
        drop_frame.setObjectName('dropFrame')
        drop_layout = QHBoxLayout(drop_frame)
        drop_layout.setContentsMargins(30, 30, 30, 30)
        
        drop_label = QLabel(_('📂 Drop an EPUB or Text Doc here to start translating'))
        drop_label.setObjectName('dropLabel')
        drop_label.setWordWrap(True)
        from PySide6.QtWidgets import QSizePolicy
        drop_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        drop_layout.addWidget(drop_label, 1)
        
        drop_layout.addStretch()
        
        new_btn = QPushButton(_('  Browse Files...  '))
        new_btn.setObjectName('primary')
        new_btn.setFixedHeight(44)
        new_btn.clicked.connect(self._new_project)
        drop_layout.addWidget(new_btn)
        
        layout.addWidget(drop_frame)
        layout.addSpacing(30)
        
        # Recent Projects Section
        recent_label = QLabel(_('Recent Projects'))
        recent_label.setObjectName('sectionHeader')
        layout.addWidget(recent_label)
        layout.addSpacing(10)

        # Project cards grid (scrollable)
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(16)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        cards_scroll.setWidget(self.cards_container)
        layout.addWidget(cards_scroll, 1)

        # Load recent projects
        self._load_recent_projects()

        return page

    def _on_theme_changed(self, theme_val):
        """Handle theme switch triggered from SettingsPanel."""
        from PySide6.QtWidgets import QApplication
        from lingua.ui.themes import ThemeManager
        app = QApplication.instance()
        if app:
            ThemeManager.apply_theme(app, theme_val)
            # Update dynamic HTML pages
            if hasattr(self, 'about_label'):
                self.about_label.setText(self._get_about_html(theme_val))
            if hasattr(self, 'help_label'):
                self.help_label.setText(self._get_help_html(theme_val))

    def _get_theme_content_style(self, theme_val=None):
        """Return a dict of colors for HTML views based on theme."""
        if not theme_val:
            theme_val = self.config.get('theme', 'dark').lower()
        else:
            theme_val = theme_val.lower()

        if theme_val == "sepia":
            return {
                "text": "#433422", "text_dim": "#7b6343", "header": "#8b5e3c",
                "card_bg": "#e9dec9", "card_border": "#dcc9af", "accent": "#8b5e3c",
                "vision_bg": "rgba(139, 94, 60, 0.08)", "vision_border": "rgba(139, 94, 60, 0.3)",
                "pre_bg": "#ede2cf", "hr": "#dcc9af"
            }
        elif theme_val == "light":
            return {
                "text": "#111827", "text_dim": "#4b5563", "header": "#2563eb",
                "card_bg": "#f9fafb", "card_border": "#d1d5db", "accent": "#2563eb",
                "vision_bg": "rgba(37, 99, 235, 0.05)", "vision_border": "rgba(37, 99, 235, 0.2)",
                "pre_bg": "#f3f4f6", "hr": "#e5e7eb"
            }
        else: # Dark
            return {
                "text": "#eee", "text_dim": "#888", "header": "#4ade80",
                "card_bg": "#252525", "card_border": "#333", "accent": "#4ade80",
                "vision_bg": "rgba(74, 222, 128, 0.05)", "vision_border": "rgba(74, 222, 128, 0.2)",
                "pre_bg": "#222", "hr": "#333"
            }

    def _rearrange_cards(self):
        if not hasattr(self, '_project_cards') or not self._project_cards:
            return
            
        # Calculate available width (Window - Sidebar - Margins - Scrollbar)
        available_width = self.width() - 200 - 80 - 20 
        card_width = 260 + 16 # Card width + spacing
        columns = max(1, available_width // card_width)
        
        # Avoid unnecessary relayouting
        if getattr(self, '_current_columns', 0) == columns:
            return
        self._current_columns = columns
        
        # Re-add items to grid
        for i, card in enumerate(self._project_cards):
            self.cards_grid.removeWidget(card)
            row, col = divmod(i, columns)
            self.cards_grid.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rearrange_cards()

    def _load_recent_projects(self):
        """Load recent projects from config and create cards."""
        self._project_cards = []
        recent = self.config.get('recent_projects') or []
        paths_to_load = []
        
        if recent:
            for i, project in enumerate(recent[:12]):  # max 12 cards
                path = project.get('path', '')
                if not os.path.exists(path):
                    continue
                paths_to_load.append(path)
                card = ProjectCard(
                    file_path=path,
                    title=project.get('title', ''),
                    author=project.get('author', ''),
                    progress=project.get('progress', 0),
                )
                card.clicked.connect(self._open_project)
                card.remove_requested.connect(self._remove_project)
                self._project_cards.append(card)
                
            self._rearrange_cards()
            
            # Start background cover loader
            self._cover_loader = CoverLoader(paths_to_load, self)
            self._cover_loader.cover_loaded.connect(self._on_cover_loaded)
            self._cover_loader.start()

    def _on_cover_loaded(self, file_path, cover_data):
        from PySide6.QtGui import QPixmap
        import PySide6.QtCore as QtCore
        for card in self._project_cards:
            if card.file_path == file_path:
                pix = QPixmap()
                pix.loadFromData(cover_data)
                card._og_pixmap = pix
                # Trigger a resize explicitly or just update the image manually
                scaled_pixmap = pix.scaled(
                    card.cover_label.width(), card.cover_label.height(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                card.cover_label.setPixmap(scaled_pixmap)
                break

    def _remove_project(self, file_path):
        """Remove a project from recent history."""
        recent = self.config.get('recent_projects') or []
        recent = [p for p in recent if p.get('path') != file_path]
        self.config.set('recent_projects', recent)
        self.config.commit()
        
        # Remove visually
        for card in list(self._project_cards):
            if card.file_path == file_path:
                self.cards_grid.removeWidget(card)
                self._project_cards.remove(card)
                card.deleteLater()
                break
        
        
        self._rearrange_cards()

    def _add_epub_project(self, file_path):
        """Extract EPUB metadata and add a project card."""
        title = os.path.splitext(os.path.basename(file_path))[0]
        author = ''
        cover_data = None

        try:
            import ebooklib
            from ebooklib import epub
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
            # Title
            meta_title = book.get_metadata('DC', 'title')
            if meta_title:
                title = meta_title[0][0]
            # Author
            meta_author = book.get_metadata('DC', 'creator')
            if meta_author:
                author = meta_author[0][0]
            # Cover image
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER:
                    cover_data = item.get_content()
                    break
            if not cover_data:
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        name = item.get_name().lower()
                        if 'cover' in name:
                            cover_data = item.get_content()
                            break
        except Exception as e:
            logging.warning(f'Could not read EPUB metadata: {e}')

        # Hide drop hint
        if hasattr(self, 'drop_hint'):
            self.drop_hint.setVisible(False)

        # Add card
        count = self.cards_grid.count()
        card = ProjectCard(
            file_path=file_path,
            title=title,
            author=author,
            progress=0,
            cover_data=cover_data,
        )
        card.clicked.connect(self._open_project)
        row, col = divmod(count, 3)
        self.cards_grid.addWidget(card, row, col)

        # Persist to recent projects
        recent = self.config.get('recent_projects') or []
        # Remove duplicates
        recent = [p for p in recent if p.get('path') != file_path]
        recent.insert(0, {
            'path': file_path,
            'title': title,
            'author': author,
            'progress': 0,
        })
        recent = recent[:20]  # keep max 20
        self.config.set('recent_projects', recent)
        self.config.commit()

        self.status_bar.showMessage(f'Loaded: {title} by {author}')

    def _open_project(self, file_path):
        """Open translation workspace for the given EPUB."""
        # Find title from recent projects
        title = os.path.basename(file_path)
        recent = self.config.get('recent_projects') or []
        for p in recent:
            if p.get('path') == file_path:
                title = p.get('title', title)
                break

        # Show Pre-Translation Setup Dialog
        from lingua.ui.setup_dialog import SetupTranslationDialog
        setup = SetupTranslationDialog(file_path, self)
        if not setup.exec():
            return # User cancelled setup

        workspace = TranslationWorkspace(file_path, title)
        workspace.back_requested.connect(self._back_to_dashboard)

        # Add to stack and switch
        idx = self.stack.addWidget(workspace)
        self.stack.setCurrentIndex(idx)
        self.sidebar.setVisible(False)
        self.status_bar.showMessage(f'Working on: {title}')

    def _back_to_dashboard(self):
        """Return from workspace to dashboard."""
        current = self.stack.currentWidget()
        self.stack.setCurrentIndex(0)  # dashboard
        self.sidebar.setVisible(True)
        self.sidebar.setCurrentRow(0)
        # Clean up workspace
        if isinstance(current, TranslationWorkspace):
            self.stack.removeWidget(current)
            current.deleteLater()
        self.status_bar.showMessage(f'Ready -- Lingua v{lingua.__version__}')

    def _on_load_legacy_project(self, db_path, title):
        """Handle legacy project loading from Maintenance tab."""
        # 1. Ensure it's in our local cache
        from lingua.core.config import CACHE_DIR
        target_dir = os.path.join(CACHE_DIR, 'translation_cache', 'cache')
        os.makedirs(target_dir, exist_ok=True)
        
        db_filename = os.path.basename(db_path)
        local_db_path = os.path.join(target_dir, db_filename)
        
        if not os.path.exists(local_db_path):
            try:
                import shutil
                shutil.copy2(db_path, local_db_path)
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, _("Import Error"), f"Could not copy database: {e}")
                return

        # 2. Try to find local EPUB (legacy plugin often keeps them side-by-side)
        epub_path = db_path.replace(".db", ".epub")
        if not os.path.exists(epub_path):
            epub_path = None

        review_mode = False
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        if not epub_path or not os.path.exists(epub_path):
            res = QMessageBox.question(
                self, _("EPUB Missing"),
                _("The source EPUB for this cache was not found automatically.\n\n"
                  "Would you like to select it manually?\n"
                  "(Selecting 'No' will open in Review Mode: read/edit only, no export)"),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if res == QMessageBox.Cancel:
                return
            elif res == QMessageBox.Yes:
                epub_path, _filter = QFileDialog.getOpenFileName(
                    self, _("Select Source EPUB"), "", "EPUB files (*.epub)"
                )
                if not epub_path:
                    return
            else:
                review_mode = True
                # In review mode, we use the DB filename as the "path" for UID derivation
                epub_path = local_db_path 

        # 3. Open Workspace
        # Note: We skip the Setup dialog for legacy imports as we assume they are already configured.
        workspace = TranslationWorkspace(epub_path, title, review_mode=review_mode)
        workspace.back_requested.connect(self._back_to_dashboard)

        # Add to stack and switch
        idx = self.stack.addWidget(workspace)
        self.stack.setCurrentIndex(idx)
        self.sidebar.setVisible(False)
        self.status_bar.showMessage(f'Working on: {title}' + (" [Review Mode]" if review_mode else ""))

    # ── Drag & Drop ──

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.epub'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.epub') and os.path.isfile(path):
                self._add_epub_project(path)
                # Switch to dashboard
                self.sidebar.setCurrentRow(0)
                self.stack.setCurrentIndex(0)
        event.acceptProposedAction()



    def _build_about(self):
        """About page with professional description."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel('📖 ' + _('About Lingua'))
        title.setObjectName('title')
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        self.about_label = QLabel(self._get_about_html())
        self.about_label.setWordWrap(True)
        self.about_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        content_layout.addWidget(self.about_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return page

    def _get_about_html(self, theme=None):
        import lingua
        style = self._get_theme_content_style(theme)
        is_ro = self.config.get('app_language', 'en') == 'ro'
        
        # Philosophical quote common to both
        quote_ro = 'Lingua nu este un simplu utilitar, ci o viziune. S-a născut din refuzul de a accepta mediocritatea traducerilor automate brute, căutând în schimb armonia dintre rigoarea algoritmului neural și sensibilitatea spiritului literar. Este un sanctuar digital pentru cei care cred că fiecare cuvânt merită să fie cântărit cu grijă, pentru ca esență operei să rămână nealterată prin migrarea între limbi.'
        quote_en = 'Lingua is not a simple utility, it is a vision. It was born from the refusal to accept the mediocrity of raw machine translations, seeking instead the harmony between neural algorithm rigor and literary spirit sensitivity. It is a digital sanctuary for those who believe every word deserves to be weighed with care, so that the essence of the work remains unaltered through its migration between languages.'
        
        quote = quote_ro if is_ro else quote_en
        title_tag = '🎯 ManuX Edition: Excelență Lingvistică' if is_ro else '🎯 ManuX Edition: Linguistic Excellence'
        
        # Cards data for the manual table layout
        cards = [
            {
                'title': '🔬 Inteligență Românească' if is_ro else '🔬 Linguistic Intelligence',
                'desc': ('Sistem complex de <b>1600+ linii</b> pentru detecția amicilor falși (<i>evidență ≠ evidence</i>) și a calcurilor.' if is_ro else 
                         'Complex system with <b>1600+ lines</b> for detecting false friends and linguistic calques.')
            },
            {
                'title': '📖 Master Glossary' if is_ro else '📖 Master Glossary',
                'desc': ('Consistență terminologică EN/ES/FR/IT → RO. Lingua urmărește automat termenii recurenți.' if is_ro else
                         'Terminological consistency across languages. Lingua automatically tracks recurring terms.')
            },
            {
                'title': '🎭 Stiluri Avansate' if is_ro else '🎭 Advanced Styles',
                'desc': ('De la registrul academic (Filozofie/Teologie) la cel literar fluid sau motivațional (Self-Help).' if is_ro else
                         'From academic register (Philosophy/Theology) to fluid literary or motivational style (Self-Help).')
            },
            {
                'title': '🧠 Chunking Inteligent' if is_ro else '🧠 Intelligent Chunking',
                'desc': ('Manipularea inteligentă a segmentelor pentru a respecta granițele paragrafelor din EPUB.' if is_ro else
                         'Intelligent segment handling to respect paragraph and chapter boundaries in EPUB files.')
            }
        ]

        # Use a table for the 2x2 grid since QLabel doesn't support CSS grid
        cards_html = f"""
        <table width="100%" cellspacing="15" cellpadding="0">
            <tr>
                <td width="50%" style="background: {style['card_bg']}; border: 1px solid {style['card_border']}; border-radius: 10px; padding: 20px;">
                    <b style="color: {style['accent']}; font-size: 16px;">{cards[0]['title']}</b><br>
                    <span style="font-size: 13px; color: {style['text']};">{cards[0]['desc']}</span>
                </td>
                <td width="50%" style="background: {style['card_bg']}; border: 1px solid {style['card_border']}; border-radius: 10px; padding: 20px;">
                    <b style="color: {style['accent']}; font-size: 16px;">{cards[1]['title']}</b><br>
                    <span style="font-size: 13px; color: {style['text']};">{cards[1]['desc']}</span>
                </td>
            </tr>
            <tr>
                <td width="50%" style="background: {style['card_bg']}; border: 1px solid {style['card_border']}; border-radius: 10px; padding: 20px;">
                    <b style="color: {style['accent']}; font-size: 16px;">{cards[2]['title']}</b><br>
                    <span style="font-size: 13px; color: {style['text']};">{cards[2]['desc']}</span>
                </td>
                <td width="50%" style="background: {style['card_bg']}; border: 1px solid {style['card_border']}; border-radius: 10px; padding: 20px;">
                    <b style="color: {style['accent']}; font-size: 16px;">{cards[3]['title']}</b><br>
                    <span style="font-size: 13px; color: {style['text']};">{cards[3]['desc']}</span>
                </td>
            </tr>
        </table>
        """

        from lingua.core.license import LicenseManager
        is_activated = LicenseManager.is_activated()
        
        reg_status = ""
        if is_activated:
            reg_date, exp_date, is_promo = LicenseManager.get_license_info()
            
            if is_promo:
                reg_status_text = 'EDIȚIE PROMO &bull; VALABILITATE 90 ZILE' if is_ro else 'PROMO EDITION &bull; 90 DAYS VALIDITY'
                main_badge_color = '#ffaa00' # Orange for promo
            else:
                reg_status_text = 'UTILIZATOR ÎNREGISTRAT &bull; VERSIUNE PRO' if is_ro else 'REGISTERED USER &bull; PRO VERSION'
                main_badge_color = style['accent']
                
            thanks_text = 'Vă mulțumim că folosiți acest program!' if is_ro else 'Thanks for using this program!'
            validity_info = f"Înregistrat la: {reg_date} &bull; Expiră la: {exp_date}" if is_ro else f"Registered on: {reg_date} &bull; Expires on: {exp_date}"
            
            reg_status = f"""
            <div style="background: {main_badge_color}; color: #000; padding: 15px; border-radius: 6px; text-align: center; margin-bottom: 25px; font-weight: bold; letter-spacing: 1px;">
                <div style="font-size: 16px;">{reg_status_text}</div>
                <div style="font-size: 11px; margin-top: 5px; opacity: 0.8; font-weight: normal;">{validity_info}</div>
            </div>
            <p style="text-align: center; color: {style['accent']}; font-weight: bold;">{thanks_text}</p>
            """

        footer_edition = 'STUDIO LINGUA &bull; EDIȚIE PROFESIONALĂ' if is_ro else 'LINGUA STUDIO &bull; PROFESSIONAL EDITION'
        footer_version = f'{"Versiune" if is_ro else "Version"}: {lingua.__version__} | {"Arhitect" if is_ro else "Architect"}: {lingua.__author__}'
        footer_quote = '"Creat pentru cei pentru care cărțile sunt sanctuare."' if is_ro else '"Created for those for whom books are sanctuaries."'

        return f"""
        <div style="font-family: 'Segoe UI', serif; color: {style['text']}; line-height: 1.7;">
            <div style="text-align: center; margin-bottom: 40px;">
                <h1 style="color: {style['header']}; font-weight: 200; font-size: 48px; margin-bottom: 5px; letter-spacing: 10px;">LINGUA</h1>
                <p style="font-size: 14px; color: {style['text_dim']}; margin-top: 0; letter-spacing: 5px;">THE ARCHITECTURE OF TRANSLATION</p>
            </div>

            <div style="background: {style['vision_bg']}; border: 1px solid {style['vision_border']}; border-left: 5px solid {style['accent']}; padding: 35px; margin-bottom: 50px; border-radius: 12px;">
                <p style="font-size: 16px; line-height: 1.9; color: {style['text']}; font-style: italic; margin: 0; text-align: justify; font-weight: 300;">
                    {quote}
                </p>
            </div>

            {reg_status}

            <h2 style="color: {style['header']}; font-size: 22px; margin-bottom: 25px;">{title_tag}</h2>
            {cards_html}

            <div style="border-top: 1px solid {style['hr']}; padding-top: 30px; margin-top: 50px; color: {style['text_dim']}; font-size: 13px; text-align: center;">
                <p style="margin: 3px 0; letter-spacing: 2px;">{footer_edition}</p>
                <p style="margin: 3px 0;">{footer_version}</p>
                <p style="margin: 25px 0; font-style: italic; color: {style['accent']};">{footer_quote}</p>
            </div>
        </div>
        """

    def _build_help_manual(self):
        """Help Manual page with usage scenarios."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel('❓ ' + _('Help Manual'))
        title.setObjectName('title')
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        self.help_label = QLabel(self._get_help_html())
        self.help_label.setWordWrap(True)
        self.help_label.setOpenExternalLinks(True)
        self.help_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        content_layout.addWidget(self.help_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        return page

    def _get_help_html(self, theme=None):
        style = self._get_theme_content_style(theme)
        is_ro = self.config.get('app_language', 'en') == 'ro'
        
        title = '🎓 Lingua Masterclass: Ghidul Traducătorului Expert' if is_ro else '🎓 Lingua Masterclass: Expert Translator Guide'
        
        setup_title = '🚀 0. Configurare Master (Quick Start)' if is_ro else '🚀 0. Master Setup (Quick Start)'
        setup_desc = ('Urmează acești pași pentru a debloca puterea maximă a Lingua:' if is_ro else 
                      'Follow these steps to unlock the full power of Lingua:')
        setup_google = ('<b>Google Free New:</b> Configurație zero-key (fără cont). Perfect pentru pornire rapidă.' if is_ro else
                        '<b>Google Free New:</b> Zero-key configuration. Perfect for an immediate start.')
        setup_gemini = ('<b>Gemini 2.5 Flash Lite:</b> Recomandarea noastră pentru bulk (viteză mare, cost mic). Obțineți cheia din Google AI Studio.' if is_ro else
                        '<b>Gemini 2.5 Flash Lite:</b> Our primary recommendation for bulk work (high speed). Get your key from Google AI Studio.')
        setup_neural = ('<b>Motoare Neuronale (Anthropic/OpenAI):</b> Utilizați <b>Claude 4.6 Sonnet</b> sau <b>GPT-4o</b> pentru literatură de înaltă precizie (necesită cheie API).' if is_ro else
                        '<b>Neural Powerhouses (Anthropic/OpenAI):</b> Use <b>Claude 4.6 Sonnet</b> or <b>GPT-4o</b> for high-precision literary translations (API key required).')
        setup_placeholders = ('<b>Deepl/Google:</b> Motoare neuronale clasice, ideale pentru traduceri factuale sau ca referință secundară.' if is_ro else
                            '<b>Deepl/Google:</b> Standard neural engines, perfect for factual translations or as a secondary reference.')
        setup_txt = ('<b>Glosar Local (.txt):</b> Incarcați un fisier text in Settings. Formatul recomandat este rând dublu (sursă, apoi țintă, separați prin linie goală):<br><code style="background: {style[\'pre_bg\']}; padding: 5px; display: block; margin-top: 5px;">Deus caritas est<br>Dumnezeu este iubire<br><br>Lux in tenebris<br>Lumină în întuneric</code>' if is_ro else
                    '<b>Local Glossary (.txt):</b> Upload a text file in Settings. The recommended format is double-line (source, then target, separated by a blank line):<br><code style="background: {style[\'pre_bg\']}; padding: 5px; display: block; margin-top: 5px;">Deus caritas est<br>Dumnezeu este iubire<br><br>Lux in tenebris<br>Lumină în întuneric</code>')
        
        engines_title = '⚙️ 1. Selecția Inteligentă a Motoarelor' if is_ro else '⚙️ 1. Intelligent Engine Selection'
        engines_flash = ('Economie și viteză brută pentru romane de consum.' if is_ro else 'Economy and raw speed for mass-market novels.')
        engines_high = ('Standardul de aur pentru literatură clasică și poezie.' if is_ro else 'The gold standard for classic literature and poetry.')
        
        glossary_title = '📖 2. Glosarul Dinamic și Anti-Literalism' if is_ro else '📖 2. Dynamic Glossary & Anti-Literalism'
        glossary_desc = ('Lingua nu traduce cuvânt cu cuvânt, ci context cu context:' if is_ro else 'Lingua translates context by context, not word by word:')
        glossary_own = ('Încărcați liste de termeni în Settings pentru consistența numelor.' if is_ro else 'Upload term lists in Settings to ensure name consistency.')
        glossary_friends = ('Sistemul previne automat erori precum <i>"actual"</i> (faptic/real).' if is_ro else 'The system automatically prevents errors like <i>"actual"</i> vs <i>"real"</i>.')
        
        workflow_title = '🛠️ 3. Fluxul de Lucru Profesional' if is_ro else '🛠️ 3. Professional Workflow'
        workflow_steps = [
            '<b>Audit:</b> Începeți prin a verifica numărul de segmente.' if is_ro else '<b>Audit:</b> Start by checking the number of segments.',
            '<b>Bulk:</b> Lansați traducerea automată pentru întreaga carte.' if is_ro else '<b>Bulk:</b> Launch automatic translation for the whole book.',
            '<b>Rafinare:</b> Folosiți filtrul <i>"Netraduse"</i> pentru zonele dificile.' if is_ro else '<b>Refinement:</b> Use the <i>"Untranslated"</i> filter for difficult areas.',
            '<b>Context:</b> Click-dreapta pentru a cere o a doua opinie de la un alt motor AI.' if is_ro else '<b>Context:</b> Right-click to ask for a second opinion from another AI engine.'
        ]
        
        alignment_title = '📐 4. Alinierea Manuală Avansată' if is_ro else '📐 4. Advanced Manual Alignment'
        alignment_drag = ('<b>Drag & Drop:</b> Mutați segmentele pentru a restaura echilibrul.' if is_ro else '<b>Drag & Drop:</b> Move segments to restore balance.')
        alignment_chunk = ('<b>Re-Chunk:</b> Tăiați paragrafele lungi pentru a ajuta AI-ul.' if is_ro else '<b>Re-Chunk:</b> Split long paragraphs to help the AI.')
        
        shortcuts_title = '⌨️ 5. Scurtături de Putere' if is_ro else '⌨️ 5. Power Shortcuts'
        shortcuts = [
            ('F2', 'Traduce instant rândul selectat' if is_ro else 'Translate selected row instantly'),
            ('Enter', 'Confirmă și trece la următorul rând' if is_ro else 'Confirm and go to next row'),
            ('Ctrl+F', 'Căutare rapidă în text' if is_ro else 'Quick search in text'),
            ('Ctrl+S', 'Salvare forțată a progresului' if is_ro else 'Force save progress')
        ]
        
        trouble_title = '🆘 6. Troubleshooting' if is_ro else '🆘 6. Troubleshooting'
        trouble_429 = ('<b>Erori 429:</b> Limita de rată atinsă. Așteptați 2-3 minute.' if is_ro else '<b>429 Errors:</b> Rate limit reached. Wait 2-3 minutes.')
        trouble_missing = ('<b>Text Lipsă:</b> Verificați filtrele din Workspace.' if is_ro else '<b>Missing Text:</b> Check filters in Workspace.')

        return f"""
        <div style="font-family: 'Segoe UI', serif; color: {style['text']}; line-height: 1.7;">
            <h1 style="color: {style['header']}; margin-bottom: 30px;">{title}</h1>
            
            <div style="background: {style['vision_bg']}; border: 1px solid {style['vision_border']}; padding: 20px; border-radius: 8px; margin-bottom: 35px;">
                <h2 style="color: {style['accent']}; margin-top: 0;">{setup_title}</h2>
                <p style="font-size: 14px;">{setup_desc}</p>
                <ul>
                    <li style="margin-bottom: 8px;">{setup_google}</li>
                    <li style="margin-bottom: 8px;">{setup_gemini}</li>
                    <li style="margin-bottom: 8px;">{setup_neural}</li>
                    <li style="margin-bottom: 8px;">{setup_placeholders}</li>
                    <li style="margin-bottom: 8px;">{setup_txt}</li>
                </ul>
            </div>

            <h2 style="color: {style['header']};">{engines_title}</h2>
            <ul>
                <li><b style="color: {style['accent']};">Flash Lite:</b> {engines_flash}</li>
                <li><b style="color: {style['accent']};">Claude 4.6 / GPT-4o:</b> {engines_high}</li>
            </ul>

            <h2 style="color: {style['header']};">{glossary_title}</h2>
            <p>{glossary_desc}</p>
            <ul>
                <li>{glossary_own}</li>
                <li>{glossary_friends}</li>
            </ul>

            <h2 style="color: {style['header']};">{workflow_title}</h2>
            <ol>
                <li>{workflow_steps[0]}</li>
                <li>{workflow_steps[1]}</li>
                <li>{workflow_steps[2]}</li>
                <li>{workflow_steps[3]}</li>
            </ol>

            <h2 style="color: {style['header']};">{alignment_title}</h2>
            <p>{"Dacă traducerile par decalate:" if is_ro else "If translations seem misaligned:"}</p>
            <ul>
                <li>{alignment_drag}</li>
                <li>{alignment_chunk}</li>
            </ul>

            <h2 style="color: {style['header']};">{shortcuts_title}</h2>
            <table style="width: 100%; border-collapse: collapse; color: {style['text']};">
                <tr style="border-bottom: 1px solid {style['hr']};"><td style="padding: 10px;"><b>{shortcuts[0][0]}</b></td><td>{shortcuts[0][1]}</td></tr>
                <tr style="border-bottom: 1px solid {style['hr']};"><td style="padding: 10px;"><b>{shortcuts[1][0]}</b></td><td>{shortcuts[1][1]}</td></tr>
                <tr style="border-bottom: 1px solid {style['hr']};"><td style="padding: 10px;"><b>{shortcuts[2][0]}</b></td><td>{shortcuts[2][1]}</td></tr>
                <tr style="border-bottom: 1px solid {style['hr']};"><td style="padding: 10px;"><b>{shortcuts[3][0]}</b></td><td>{shortcuts[3][1]}</td></tr>
            </table>

            <div style="margin-top: 40px; border-left: 4px solid #f44336; padding-left: 15px; background: rgba(244, 67, 54, 0.05);">
                <h2 style="color: #f44336; margin-top: 0;">{trouble_title}</h2>
                <p style="font-size: 14px;">
                    {trouble_429}<br>
                    {trouble_missing}
                </p>
            </div>
        </div>
        """


            














            



    def _build_menu(self):
        """Build menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')
        new_action = QAction('&New Project...', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        file_menu.addSeparator()
        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu('&Help')
        tour_action = QAction(_('Restart Guided Tour'), self)
        tour_action.triggered.connect(self.start_guided_tour)
        help_menu.addAction(tour_action)
        
        help_menu.addSeparator()
        about_action = QAction(_('About Lingua'), self)
        about_action.triggered.connect(lambda: self.sidebar.setCurrentRow(2))
        help_menu.addAction(about_action)

    def _setup_tour(self):
        """Define the steps for the interactive tour."""
        self.tour = TourOverlay(self)
        self.tour.finished.connect(self._on_tour_finished)
        
        def get_item_rect(index):
            item = self.sidebar.item(index)
            if not item: return QRect()
            rect = self.sidebar.visualItemRect(item)
            pos = self.sidebar.mapTo(self, rect.topLeft())
            return QRect(pos, rect.size())

        def target_settings_child(obj):
            if hasattr(obj, "mapTo"):
                pos = obj.mapTo(self, QPoint(0, 0))
                return QRect(pos, obj.size())
            return QRect()

        # 1. Dashboard
        self.tour.add_step(
            lambda: get_item_rect(0),
            _("Project Dashboard"),
            _("Manage your current books and see their status.")
        )
        
        # 2. Add Books
        def get_drop_frame():
            dashboard = self.stack.widget(0)
            from PySide6.QtWidgets import QFrame
            frame = dashboard.findChild(QFrame, "dropFrame")
            if frame:
                pos = frame.mapTo(self, QPoint(0, 0))
                return QRect(pos, frame.size())
            return dashboard.rect()
            
        self.tour.add_step(
            get_drop_frame,
            _("Add Your Books"),
            _("Drag and drop EPUB files here or use the 'Browse' button to start a new translation project.")
        )
        
        # 3. Settings Introduction
        self.tour.add_step(
            lambda: get_item_rect(1),
            _("Master Settings"),
            _("Configure Lingua for the best translation quality. Let's look inside!"),
            action=lambda: self.sidebar.setCurrentRow(1)
        )

        # --- TAB: GENERAL ---
        # 4. Themes & Language
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.theme_combo),
            _("General: Appearance"),
            _("Switch between Dark, Light, and Sepia themes. You can also change the interface language here."),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(0)
        )

        # 5. Smart HTML Merge
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.smart_html_merge),
            _("Smart HTML Merge"),
            _("Preserves formatting (bold, italics) by keeping HTML tags together. **Highly recommended** for ebooks to keep them looking original.")
        )

        # 6. Chunking Method
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.chunk_standard).adjusted(0, 0, 400, 0),
            _("Chunking Method"),
            _("How text is sent to the AI. \n\n"
              "• **Standard/Merge**: Best for **Google Free** (avoids 'too long' errors).\n"
              "• **Chapter-Aware**: Best for **Gemini/Claude** (max context, up to 15k chars).\n"
              "• **Per-File**: Best for complex formatting per XHTML file.")
        )

        # --- TAB: ENGINE ---
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.engine_combo),
            _("AI Engine Selection"),
            _("Select your 'brain'. \n\n"
              "• **Google Free**: Works in small chunks, no API key needed.\n"
              "• **Gemini / Claude / GPT**: Large Language Models (LLMs) that understand context and nuance."),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(1)
        )

        # 7b. Google Cloud Tutorial (NEW)
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.api_keys),
            _("Google Cloud & $300 Credit"),
            _("Did you know? Google offers **$300 free credit** for 3 months to use Gemini Pro. Click 'Next' to see the step-by-step tutorial on how to get your key!"),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(1)
        )
        
        # New Step triggered by Next to show the actual dialog
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.api_tutorial_btn),
            _("API Tutorial"),
            _("I've opened the tutorial window for you. You can also find it anytime by clicking the 💡 button."),
            action=lambda: self.settings_panel._show_api_tutorial()
        )

        # 8. Rate Limits (Concurrency & Interval)
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.concurrency).adjusted(0, 0, 300, 100),
            _("Stability vs Speed"),
            _("**Concurrency**: How many requests run at once. \n"
              "**Interval**: Wait time between requests. \n\n"
              "**Tip**: For Google Free, use 0.5s interval. For Gemini Pro, 1 concurrency is safer to avoid Rate Limits (429).")
        )

        # 9. Timeout
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.timeout),
            _("Timeout (Wait Time)"),
            _("LLMs like Gemini 1.5/2.5 Pro are deep thinkers and can take time. Increase this to **400s+** to avoid 'Gateway Timeout' during heavy translations.")
        )

        # --- TAB: CONTENT ---
        # 10. Position
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.pos_below).adjusted(0, 0, 300, 0),
            _("Translation Position"),
            _("Choose where the translation appears relative to the original text. You can even choose 'Replace' for a clean target-only ebook."),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(2)
        )

        # --- TAB: STYLES ---
        # 11. Genre & Style
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.style_combo),
            _("Styles & Narrative Voice"),
            _("Tell the AI what you're translating (e.g., Thriller, Sci-Fi). Each genre applies special rules for tone and address (like 'tu' vs 'dumneavoastră' in Romanian)."),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(3)
        )

        # 12. AI Prompt Architect
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.ai_gen_btn),
            _("✨ AI Prompt Architect"),
            _("A Professional feature! Provide the book title and author, and the AI will generate a **perfect, custom system prompt** specifically for that book's narrative voice.")
        )

        # --- TAB: MAINTENANCE ---
        # 13. Legacy Import
        self.tour.add_step(
            lambda: target_settings_child(self.settings_panel.import_btn),
            _("Maintenance: Migration"),
            _("If you used the Calibre plugin before, use this to import all your previous translations into Lingua. (Pro feature)"),
            action=lambda: self.settings_panel.tabs.setCurrentIndex(4)
        )

        # 14. Finished
        self.tour.add_step(
            lambda: get_item_rect(3),
            _("Expert Guide & Help"),
            _("You're ready! Check the Help tab for advanced shortcuts and troubleshooting tips. Happy translating!"),
            action=lambda: self.sidebar.setCurrentRow(3)
        )

    def start_guided_tour(self):
        """Start or restart the interactive tour."""
        self.sidebar.setCurrentRow(0) # Start from dashboard
        self.tour._apply_dialog_style() # Refresh style for current theme
        self.tour.start_tour()

    def _on_tour_finished(self):
        """Save tour completion state."""
        self.config.set('tour_completed', True)
        self.config.commit()

    def _build_statusbar(self):
        """Build status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready — Lingua v%s' % lingua.__version__)

    def _on_nav_change(self, index):
        """Handle sidebar navigation."""
        self.stack.setCurrentIndex(index)

    def _new_project(self):
        """Open file dialog to select an EPUB."""
        file_path, _filter = QFileDialog.getOpenFileName(
            self, _('Select Ebook'),
            os.path.expanduser('~'),
            'Ebook Files (*.epub);;All Files (*.*)'
        )
        if file_path:
            self._add_epub_project(file_path)
            self._open_project(file_path)
