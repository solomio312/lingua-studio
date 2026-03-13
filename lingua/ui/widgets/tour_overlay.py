from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QRect, QPoint, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QRegion, QBrush, QPen, QFontMetrics
from lingua.core.config import get_config

class TourOverlay(QWidget):
    """
    A transparent overlay that draws a darken layer with a transparent 'hole' 
    (spotlight) over a target widget.
    """
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # Steps data: [(target_widget_func, title, description)]
        self.steps = []
        self.current_step = -1
        
        self._spotlight_rect = QRect()
        
        # Build Dialog
        self.dialog = QFrame(self)
        self.dialog.setObjectName("tourDialog")
        # Wider dialog to accommodate detailed Romanian descriptions
        self.dialog.setFixedWidth(420)
        self.dialog.setStyleSheet("""
            #tourDialog {
                background: #2d2d2d;
                border: 1px solid #4ade80;
                border-radius: 12px;
            }
            QLabel#tourTitle {
                color: #4ade80;
                font-weight: bold;
                font-size: 16px;
            }
            QLabel#tourDesc {
                color: #ddd;
                font-size: 13px;
            }
            QPushButton#tourNext {
                background: #4ade80;
                color: #1a1a1a;
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton#tourClose {
                background: transparent;
                color: #888;
                border: none;
            }
        """)
        
        diag_layout = QVBoxLayout(self.dialog)
        diag_layout.setSpacing(15)
        diag_layout.setContentsMargins(20, 20, 20, 20)
        # This is CRITICAL: it forces the dialog widget to follow the layout's size hint
        diag_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        
        # Apply theme-aware styling
        self._apply_dialog_style()
        
        header = QHBoxLayout()
        self.title_label = QLabel("Step Title")
        self.title_label.setObjectName("tourTitle")
        header.addWidget(self.title_label)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("tourClose")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.hide_tour)
        header.addWidget(self.close_btn)
        diag_layout.addLayout(header)
        
        self.desc_label = QLabel("Description goes here...")
        self.desc_label.setObjectName("tourDesc")
        self.desc_label.setWordWrap(True)
        diag_layout.addWidget(self.desc_label)
        
        footer = QHBoxLayout()
        self.step_label = QLabel("1 / 5")
        self.step_label.setStyleSheet("color: #666; font-size: 11px;")
        footer.addWidget(self.step_label)
        
        footer.addStretch()
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("tourNext")
        self.next_btn.clicked.connect(self.next_step)
        footer.addWidget(self.next_btn)
        
        diag_layout.addLayout(footer)
        
        self.hide()

    def _apply_dialog_style(self):
        """Update dialog colors based on current app theme."""
        config = get_config()
        theme = config.get('theme', 'dark').lower()
        
        # We want the dialog to ALWAYS be readable. 
        # In Dark mode: dark background, neon accent.
        # In Sepia/Light: warmer background, readable dark text.
        
        if theme == "sepia":
            bg, border, title, text, btn_bg, btn_text = "#e9dec9", "#8b5e3c", "#5d3f28", "#433422", "#8b5e3c", "#ffffff"
        elif theme == "light":
            bg, border, title, text, btn_bg, btn_text = "#ffffff", "#d1d5db", "#2563eb", "#111827", "#2563eb", "#ffffff"
        else: # Dark
            bg, border, title, text, btn_bg, btn_text = "#2d2d2d", "#4ade80", "#4ade80", "#dddddd", "#4ade80", "#1a1a1a"
            
        self.dialog.setStyleSheet(f"""
            #tourDialog {{
                background: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
            QLabel#tourTitle {{
                color: {title};
                font-weight: bold;
                font-size: 16px;
                background: transparent;
            }}
            QLabel#tourDesc {{
                color: {text};
                font-size: 13px;
                background: transparent;
            }}
            QPushButton#tourNext {{
                background: {btn_bg};
                color: {btn_text};
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
            }}
            QPushButton#tourClose {{
                background: transparent;
                color: {text};
                border: none;
                font-size: 16px;
            }}
        """)

    def add_step(self, widget_func, title, description, action=None):
        """widget_func should return the QWidget to highlight or a QRect.
        action is an optional callable to run before showing the step (e.g. switch tabs)."""
        self.steps.append((widget_func, title, description, action))

    def start_tour(self):
        if not self.steps:
            return
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.show()
        self.setGeometry(self.parent().rect())
        self.current_step = 0
        self.update_step()

    def next_step(self):
        self.current_step += 1
        if self.current_step >= len(self.steps):
            self.hide_tour()
        else:
            self.update_step()

    def hide_tour(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()
        self.finished.emit()

    def update_step(self):
        widget_func, title, desc, action = self.steps[self.current_step]
        if action:
            action()
            
        self.title_label.setText(title)
        self.desc_label.setText(desc)
        self.step_label.setText(f"{self.current_step + 1} / {len(self.steps)}")
        
        # Force the dialog to resize to fit the new text before positioning
        self.dialog.adjustSize()
        
        if self.current_step == len(self.steps) - 1:
            self.next_btn.setText("Finish")
        else:
            self.next_btn.setText("Next")
            
        # Determine spotlight rect
        target = widget_func()
        if isinstance(target, QWidget):
            # Map widget coordinates to overlay
            pos = target.mapTo(self.parent(), QPoint(0, 0))
            self._spotlight_rect = QRect(pos, target.size())
        elif isinstance(target, QRect):
            self._spotlight_rect = target
        else:
            self._spotlight_rect = QRect()
            
        # Animate spotlight expansion (padding)
        self._spotlight_rect = self._spotlight_rect.adjusted(-10, -10, 10, 10)
        
        # Position dialog near spotlight
        self.position_dialog()
        self.update()

    def position_dialog(self):
        # Calculate ideal position relative to the spotlight
        # Priority: Right of, then Left of, then Below, then Above.
        
        # Right of
        x = self._spotlight_rect.right() + 25
        y = self._spotlight_rect.center().y() - self.dialog.height() // 2
        
        # Check if fits on right
        if x + self.dialog.width() > self.width() - 20:
            # Try Left
            x = self._spotlight_rect.left() - self.dialog.width() - 25
            if x < 20:
                # Try Below
                x = max(20, self._spotlight_rect.center().x() - self.dialog.width() // 2)
                y = self._spotlight_rect.bottom() + 25
                if y + self.dialog.height() > self.height() - 20:
                    # Final fallback: Above
                    y = self._spotlight_rect.top() - self.dialog.height() - 25
        
        # Clamp to screen
        x = max(20, min(self.width() - self.dialog.width() - 20, x))
        y = max(20, min(self.height() - self.dialog.height() - 20, y))
            
        self.dialog.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw dark semi-transparent overlay
        overlay_color = QColor(0, 0, 0, 180)
        
        # We use a path to draw a "hole" in the overlay
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(self.rect()) # Full screen
        
        # The "hole" - Rounded Rect looks better for UI elements
        hole_path = QPainterPath()
        hole_path.addRoundedRect(self._spotlight_rect, 15, 15)
        
        # Subtract hole from full screen
        final_path = path.subtracted(hole_path)
        
        painter.fillPath(final_path, QBrush(overlay_color))
        
        # Draw a subtle glow around the hole
        painter.setPen(QPen(QColor(74, 222, 128, 200), 2))
        painter.drawRoundedRect(self._spotlight_rect, 15, 15)

    def resizeEvent(self, event):
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
