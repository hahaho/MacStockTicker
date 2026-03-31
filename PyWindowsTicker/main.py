import sys
import json
import os
import urllib.request
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QRect, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QCursor

CONFIG_FILE = "config.json"
INDEX_SYMBOLS = ["sh000001", "sz399001", "sz399006"]

class MarqueeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = "跑马灯模式"
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_offset)
        self.timer.start(30) # ~33fps
        self.setFixedHeight(30)
        self.label = QLabel(self)
        self.label.setStyleSheet("color: white; font-size: 13px; font-weight: 500; background: transparent;")
        self.label.setText(self.text)
        self.label.adjustSize()
        
        # Allow mouse events to pass through for window dragging
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
    def set_text(self, text):
        self.text = text
        self.label.setText(self.text)
        self.label.adjustSize()
        
    def update_offset(self):
        if not self.isVisible() or self.label.width() <= 0:
            return
        
        self.offset -= 1
        # If the label has moved completely out of view to the left
        if self.offset < -self.label.width():
            self.offset = self.width() # Start from the right edge
            
        self.label.move(self.offset, (self.height() - self.label.height()) // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adjust vertical position of label on resize
        self.label.move(self.label.x(), (self.height() - self.label.height()) // 2)


class FetchThread(QThread):
    data_fetched = pyqtSignal(str)

    def __init__(self, symbols):
        super().__init__()
        self.symbols = symbols

    def run(self):
        try:
            url = f"http://hq.sinajs.cn/list={','.join(self.symbols)}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=5) as response:
                content = response.read().decode('gbk')
                self.data_fetched.emit(content)
        except Exception as e:
            print("Fetch error:", e)

class IndexCard(QFrame):
    def __init__(self, symbol, name, current, change_pct, change_amt, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: #E0E0E0; font-size: 12px; background: transparent;")
        
        color = "#ff4c4c" if change_pct > 0 else "#33cc33" if change_pct < 0 else "white"
        sign = "+" if change_pct > 0 else ""
        
        self.price_label = QLabel(f"{current:.2f}")
        self.price_label.setAlignment(Qt.AlignCenter)
        self.price_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px; background: transparent;")
        
        self.change_label = QLabel(f"{sign}{change_pct:.2f}%")
        self.change_label.setAlignment(Qt.AlignCenter)
        self.change_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.price_label)
        layout.addWidget(self.change_label)

    def update_data(self, current, change_pct, change_amt):
        color = "#ff4c4c" if change_pct > 0 else "#33cc33" if change_pct < 0 else "white"
        sign = "+" if change_pct > 0 else ""
        self.price_label.setText(f"{current:.2f}")
        self.price_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px; background: transparent;")
        self.change_label.setText(f"{sign}{change_pct:.2f}%")
        self.change_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

class StockCard(QFrame):
    delete_clicked = pyqtSignal(str)

    def __init__(self, symbol, name, current, change_pct, change_amt, high, low, open_p, volume, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                margin-bottom: 6px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.setMinimumHeight(70)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top row
        top_layout = QHBoxLayout()
        name_label = QLabel(f"{name} ({symbol[2:]})")
        name_label.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 13px; background: transparent;")
        
        color = "#ff4c4c" if change_pct > 0 else "#33cc33" if change_pct < 0 else "white"
        sign = "+" if change_pct > 0 else ""
        
        self.price_label = QLabel(f"{current:.2f}")
        self.price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.price_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px; background: transparent;")
        
        self.change_label = QLabel(f"{sign}{change_pct:.2f}%  {sign}{change_amt:.2f}")
        self.change_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.change_label.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent;")
        
        top_layout.addWidget(name_label, 1)
        
        price_box = QVBoxLayout()
        price_box.setSpacing(0)
        price_box.addWidget(self.price_label)
        price_box.addWidget(self.change_label)
        top_layout.addLayout(price_box, 1)
        
        # Bottom row
        bot_layout = QHBoxLayout()
        self.high_widget, self.high_label = self._make_info_widget("高", f"{high:.2f}", "#ff4c4c")
        self.low_widget, self.low_label = self._make_info_widget("低", f"{low:.2f}", "#33cc33")
        self.open_widget, self.open_label = self._make_info_widget("开", f"{open_p:.2f}", "white")
        
        vol_str = f"{volume/10000:.1f}万" if volume < 100000000 else f"{volume/100000000:.2f}亿"
        self.vol_widget, self.vol_label = self._make_info_widget("量", vol_str, "white")
        
        bot_layout.addWidget(self.high_widget)
        bot_layout.addWidget(self.low_widget)
        bot_layout.addWidget(self.open_widget)
        bot_layout.addWidget(self.vol_widget, alignment=Qt.AlignRight)

        layout.addLayout(top_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); margin: 0px; padding: 0px; max-height: 1px;")
        layout.addWidget(line)
        
        layout.addLayout(bot_layout)

        # Delete button
        self.del_btn = QPushButton("×", self)
        self.del_btn.setFixedSize(18, 18)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.6); color: #ff4c4c; border-radius: 9px; font-weight: bold; padding-bottom: 2px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(255,76,76,0.9); color: white; }
        """)
        self.del_btn.hide()
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.symbol))

    def _make_info_widget(self, label, val, color):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(4)
        
        name_lbl = QLabel(f"<font color='#888888'>{label}</font>")
        val_lbl = QLabel(f"<font color='{color}'>{val}</font>")
        
        l.addWidget(name_lbl)
        l.addWidget(val_lbl)
        w.setStyleSheet("font-size: 11px; background: transparent;")
        return w, val_lbl

    def update_data(self, current, change_pct, change_amt, high, low, open_p, volume):
        color = "#ff4c4c" if change_pct > 0 else "#33cc33" if change_pct < 0 else "white"
        sign = "+" if change_pct > 0 else ""
        
        self.price_label.setText(f"{current:.2f}")
        self.price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.price_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px; background: transparent;")
        
        self.change_label.setText(f"{sign}{change_pct:.2f}%  {sign}{change_amt:.2f}")
        self.change_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.change_label.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent;")
        
        self.high_label.setText(f"<font color='#ff4c4c'>{high:.2f}</font>")
        self.low_label.setText(f"<font color='#33cc33'>{low:.2f}</font>")
        self.open_label.setText(f"<font color='white'>{open_p:.2f}</font>")
        
        vol_str = f"{volume/10000:.1f}万" if volume < 100000000 else f"{volume/100000000:.2f}亿"
        self.vol_label.setText(f"<font color='white'>{vol_str}</font>")

    def enterEvent(self, event):
        self.del_btn.move(self.width() - 18, 2)
        self.del_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.del_btn.hide()
        super().leaveEvent(event)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.symbols = []
        self.is_minimized = False
        self.drag_pos = None
        self.fetch_thread = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.load_config()
        if not self.symbols:
            # 默认添加贵州茅台和平安银行
            self.symbols = ["sh600519", "sz000001"]
            self.save_config()
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_data)
        self.timer.start(5000)
        
        # Initial position
        screen = QApplication.primaryScreen().geometry()
        if self.is_minimized:
            self.move(screen.left() + (screen.width() - 800) // 2, screen.top())
        else:
            self.move(screen.left() + screen.width() - self.width() - 20, screen.top() + screen.height() - self.height() - 60)
        
        # 延迟请求，确保界面渲染完成后再发网络请求
        QTimer.singleShot(100, self.fetch_data)

    def init_ui(self):
        self.setFixedSize(350, 500)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Background frame
        self.bg_frame = QFrame(self)
        self.bg_frame.setStyleSheet("""
            QFrame#BgFrame {
                background-color: rgba(30, 30, 32, 217);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        self.bg_frame.setObjectName("BgFrame")
        self.bg_layout = QVBoxLayout(self.bg_frame)
        self.bg_layout.setContentsMargins(14, 14, 14, 14)

        # --- Expanded View ---
        self.expanded_widget = QWidget()
        exp_layout = QVBoxLayout(self.expanded_widget)
        exp_layout.setContentsMargins(0,0,0,0)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)
        title = QLabel("实时监控")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        # Minimize button (custom line)
        min_btn = QPushButton()
        min_btn.setFixedSize(24, 24)
        min_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        
        # custom paint for min button
        def paintEvent_min(e):
            painter = QPainter(min_btn)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor("#88ffffff") if not min_btn.underMouse() else QColor("white"), 2)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(6, 12, 18, 12)
        min_btn.paintEvent = paintEvent_min
        
        min_btn.clicked.connect(self.minimize_view)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #ccff4c4c; font-size: 20px; font-weight: bold; border: none; } QPushButton:hover { color: #ff4c4c; }")
        close_btn.clicked.connect(QApplication.quit)
        
        header.addWidget(min_btn)
        header.addWidget(close_btn)
        exp_layout.addLayout(header)

        # Indices Layout
        self.indices_layout = QHBoxLayout()
        self.indices_layout.setContentsMargins(0, 0, 0, 10)
        self.indices_layout.setSpacing(6)
        exp_layout.addLayout(self.indices_layout)

        # Input
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 10)
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入6位代码 (如 600519)")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: rgba(0,0,0,0.4); 
                color: white; 
                border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 6px; 
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255,255,255,0.3); 
            }
        """)
        self.input_box.returnPressed.connect(self.add_stock)
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 30)
        add_btn.setStyleSheet("QPushButton { background: transparent; color: white; font-size: 22px; border: none; margin-bottom: 2px;} QPushButton:hover { color: #aaa; }")
        add_btn.clicked.connect(self.add_stock)
        
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(add_btn)
        exp_layout.addLayout(input_layout)

        # Scroll Area for Stocks
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; } 
            QWidget#ScrollContent { background: transparent; }
        """)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.stocks_widget = QWidget()
        self.stocks_widget.setObjectName("ScrollContent")
        self.stocks_layout = QVBoxLayout(self.stocks_widget)
        self.stocks_layout.setContentsMargins(0,0,0,0)
        self.stocks_layout.setSpacing(8)
        self.stocks_layout.addStretch()
        self.scroll.setWidget(self.stocks_widget)
        
        exp_layout.addWidget(self.scroll)
        self.bg_layout.addWidget(self.expanded_widget)

        # --- Minimized View ---
        self.minimized_widget = QWidget()
        min_layout = QHBoxLayout(self.minimized_widget)
        min_layout.setContentsMargins(10,0,10,0)
        
        max_btn = QPushButton("+")
        max_btn.setFixedSize(24, 24)
        max_btn.setStyleSheet("QPushButton { background: transparent; color: #88ffffff; font-size: 18px; font-weight: bold; border: none; } QPushButton:hover { color: white; }")
        max_btn.clicked.connect(self.maximize_view)
        
        self.marquee_widget = MarqueeWidget()
        
        min_close = QPushButton("×")
        min_close.setFixedSize(24, 24)
        min_close.setStyleSheet("QPushButton { background: transparent; color: #ccff4c4c; font-size: 20px; font-weight: bold; border: none; } QPushButton:hover { color: #ff4c4c; }")
        min_close.clicked.connect(QApplication.quit)
        
        min_layout.addWidget(max_btn)
        min_layout.addWidget(self.marquee_widget, 1)
        min_layout.addWidget(min_close)
        
        self.bg_layout.addWidget(self.minimized_widget)
        self.minimized_widget.hide()

        self.main_layout.addWidget(self.bg_frame)
        
        if self.is_minimized:
            self.minimize_view(animate=False)

    def normalize_symbol(self, s):
        s = s.strip().lower()
        if s.startswith(('sh', 'sz')) and len(s) == 8 and s[2:].isdigit():
            return s
        if len(s) == 6 and s.isdigit():
            return f"sh{s}" if s.startswith(('6','9','5', '7')) else f"sz{s}"
        return None

    def add_stock(self):
        s = self.normalize_symbol(self.input_box.text())
        self.input_box.clear()
        if s and s not in self.symbols and s not in INDEX_SYMBOLS:
            self.symbols.append(s)
            self.save_config()
            self.fetch_data()

    def remove_stock(self, symbol):
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            self.save_config()
            self.fetch_data()

    def fetch_data(self):
        if self.fetch_thread and self.fetch_thread.isRunning():
            return
        all_sym = INDEX_SYMBOLS + self.symbols
        self.fetch_thread = FetchThread(all_sym)
        self.fetch_thread.data_fetched.connect(self.update_ui)
        self.fetch_thread.start()

    def update_ui(self, content):
        # 清理掉不再监控的股票卡片
        lines = [line for line in content.split('\n') if '="' in line]
        fetched_symbols = [line.split('="')[0].split('_')[-1] for line in lines]
        
        # 移除不在 fetched_symbols 中的
        for i in reversed(range(self.stocks_layout.count() - 1)):
            item = self.stocks_layout.itemAt(i)
            if item and item.widget() and item.widget().symbol not in fetched_symbols:
                w = item.widget()
                self.stocks_layout.removeWidget(w)
                w.deleteLater()
                
        marquee_texts = []
        
        for line in lines:
            parts = line.split('="')
            sym = parts[0].split('_')[-1]
            data = parts[1].strip('";').split(',')
            if len(data) < 32: continue
            
            name = data[0]
            open_p = float(data[1])
            yest_p = float(data[2])
            current = float(data[3])
            high = float(data[4])
            low = float(data[5])
            volume = float(data[8])
            
            if yest_p == 0: continue
            change_amt = current - yest_p
            change_pct = (change_amt / yest_p) * 100
            
            color = "#ff4c4c" if change_pct > 0 else "#33cc33" if change_pct < 0 else "white"
            sign = "+" if change_pct > 0 else ""
            marquee_texts.append(f"<font color='white'>{name}</font> <font color='{color}'>{current:.2f} {sign}{change_pct:.2f}%</font>")
            
            if sym in INDEX_SYMBOLS:
                found = False
                for i in range(self.indices_layout.count()):
                    item = self.indices_layout.itemAt(i)
                    if item and item.widget() and getattr(item.widget(), 'symbol', None) == sym:
                        item.widget().update_data(current, change_pct, change_amt)
                        found = True
                        break
                if not found:
                    card = IndexCard(sym, name, current, change_pct, change_amt)
                    self.indices_layout.addWidget(card)
            else:
                found = False
                for i in range(self.stocks_layout.count() - 1):
                    item = self.stocks_layout.itemAt(i)
                    if item and item.widget() and getattr(item.widget(), 'symbol', None) == sym:
                        item.widget().update_data(current, change_pct, change_amt, high, low, open_p, volume)
                        found = True
                        break
                        
                if not found:
                    card = StockCard(sym, name, current, change_pct, change_amt, high, low, open_p, volume)
                    card.delete_clicked.connect(self.remove_stock)
                    self.stocks_layout.insertWidget(self.stocks_layout.count() - 1, card)
                
        self.marquee_widget.set_text("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(marquee_texts))

    def minimize_view(self, animate=True):
        self.is_minimized = True
        self.save_config()
        self.expanded_widget.hide()
        self.minimized_widget.show()
        self.bg_frame.setStyleSheet("QFrame#BgFrame { background-color: rgba(20, 20, 20, 230); border-radius: 20px; }")
        self.bg_layout.setContentsMargins(14, 0, 14, 0)
        
        target_w, target_h = 800, 40
        if animate:
            self.do_animation(target_w, target_h)
        else:
            self.setFixedSize(target_w, target_h)
            # Ensure proper positioning when starting minimized
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.left() + (screen.width() - target_w) // 2, screen.top())

    def maximize_view(self):
        self.is_minimized = False
        self.save_config()
        self.minimized_widget.hide()
        self.expanded_widget.show()
        self.bg_frame.setStyleSheet("QFrame#BgFrame { background-color: rgba(30, 30, 32, 217); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 30); }")
        self.bg_layout.setContentsMargins(14, 14, 14, 14)
        
        self.do_animation(350, 500)

    def do_animation(self, target_w, target_h):
        # Stop existing animation if any
        if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.Running:
            self.anim.stop()

        current_geometry = self.geometry()
        screen = QApplication.primaryScreen().geometry()
        
        if self.is_minimized:
            # Minimized: Top Center
            new_x = screen.left() + (screen.width() - target_w) // 2
            new_y = screen.top()
        else:
            # Expanded: Bottom Right
            new_x = screen.left() + screen.width() - target_w - 20
            new_y = screen.top() + screen.height() - target_h - 60
        
        end_rect = QRect(new_x, new_y, target_w, target_h)
        
        # Boundary protection
        if end_rect.left() < screen.left(): end_rect.moveLeft(screen.left())
        if end_rect.top() < screen.top(): end_rect.moveTop(screen.top())
        if end_rect.right() > screen.right(): end_rect.moveRight(screen.right())
        if end_rect.bottom() > screen.bottom(): end_rect.moveBottom(screen.bottom())
        
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250) # 略微放慢让动画更平滑
        self.anim.setStartValue(current_geometry)
        self.anim.setEndValue(end_rect)
        self.anim.setEasingCurve(QEasingCurve.OutCubic) # 缓出，末尾减速更自然
        
        # Unlock fixed size during animation
        self.setMinimumSize(1, 1)
        self.setMaximumSize(9999, 9999)
        
        # 核心修复：防止缩放时内部控件到处乱跑或文字重叠折行
        # 在动画期间，强制固定内部 ExpandedWidget 的宽度，让它的布局保持在 350 尺寸下不被压缩
        self.expanded_widget.setFixedWidth(350 - 28) # 350减去左右margin 14*2
        
        # Set fixed size after animation finishes
        def on_finished():
            self.setFixedSize(target_w, target_h)
            # 动画结束后解除宽度限制
            self.expanded_widget.setMinimumWidth(0)
            self.expanded_widget.setMaximumWidth(9999)
            
        # Ensure we only connect once or disconnect old ones
        try: self.anim.finished.disconnect() 
        except: pass
        self.anim.finished.connect(on_finished)
        
        self.anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    raw_symbols = data.get("symbols", [])
                    # Filter out invalid symbols from previous configs
                    self.symbols = [s for s in raw_symbols if isinstance(s, str) and s.startswith(('sh', 'sz')) and len(s) == 8]
                    self.is_minimized = data.get("is_minimized", False)
            except: pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"symbols": self.symbols, "is_minimized": self.is_minimized}, f)
        except: pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 9))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
