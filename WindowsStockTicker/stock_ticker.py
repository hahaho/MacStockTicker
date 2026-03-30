import sys
import json
import os
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QRect
from PyQt5.QtGui import QColor, QPainter, QCursor, QPen

# --------------------------
# Config Manager
# --------------------------
class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        self.default_symbols = ["sh600519", "sh601318", "sz000858", "sh600036"]
        self.index_symbols = ["sh000001", "sz399001", "sz399006"]
        self.symbols = self.load_symbols()
        self.is_minimized = self.load_state()

    def load_symbols(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return data.get("symbols", self.default_symbols)
            except:
                pass
        return self.default_symbols

    def save_symbols(self):
        data = {"symbols": self.symbols, "is_minimized": self.is_minimized}
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def load_state(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return data.get("is_minimized", False)
            except:
                pass
        return False

    def save_state(self, is_minimized):
        self.is_minimized = is_minimized
        self.save_symbols()

# --------------------------
# Data Models
# --------------------------
class StockInfo:
    def __init__(self, symbol, data_parts):
        self.symbol = symbol
        self.name = data_parts[0]
        self.open = float(data_parts[1])
        self.last_close = float(data_parts[2])
        self.price = float(data_parts[3])
        self.high = float(data_parts[4])
        self.low = float(data_parts[5])
        self.volume = float(data_parts[8])
        self.time = data_parts[31]

    @property
    def change(self):
        return self.price - self.last_close

    @property
    def percent_change(self):
        return (self.change / self.last_close * 100) if self.last_close != 0 else 0.0

    @property
    def color(self):
        if self.change > 0: return "#ff4c4c" # Red
        if self.change < 0: return "#33cc33" # Green
        return "#ffffff"

    @property
    def formatted_volume(self):
        if self.volume > 100000000:
            return f"{self.volume / 100000000:.2f}亿"
        elif self.volume > 10000:
            return f"{self.volume / 10000:.2f}万"
        return str(int(self.volume))

# --------------------------
# UI Components
# --------------------------
class MarqueeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stocks = []
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scroll)
        
        self.container = QWidget(self)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(30)
        self.container.move(0, 0)

    def update_data(self, stocks):
        self.stocks = stocks
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not stocks: return

        # Double items for seamless loop
        for _ in range(2):
            for stock in stocks:
                text = f"<span style='font-size:14px; font-weight:bold; color:white;'>{stock.name}</span> " \
                       f"<span style='font-size:14px; font-weight:600; font-family:Consolas; color:{stock.color};'>{stock.price:.2f}</span> " \
                       f"<span style='font-size:14px; font-family:Consolas; color:{stock.color};'>{stock.change:+.2f}%</span>"
                label = QLabel(text)
                self.layout.addWidget(label)
        
        self.container.adjustSize()
        self.timer.start(20)

    def scroll(self):
        if self.container.width() == 0: return
        self.offset -= 1
        half_width = self.container.width() / 2
        if abs(self.offset) >= half_width:
            self.offset = 0
        self.container.move(int(self.offset), 0)

class IndexRowWidget(QFrame):
    def __init__(self, stock):
        super().__init__()
        self.stock = stock
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2)
        
        name_lbl = QLabel(self.stock.name)
        name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        name_lbl.setAlignment(Qt.AlignCenter)
        
        price_lbl = QLabel(f"{self.stock.price:.2f}")
        price_lbl.setStyleSheet(f"color: {self.stock.color}; font-weight: bold; font-size: 14px; font-family: Consolas;")
        price_lbl.setAlignment(Qt.AlignCenter)
        
        pct_lbl = QLabel(f"{self.stock.percent_change:+.2f}%")
        pct_lbl.setStyleSheet(f"color: {self.stock.color}; font-size: 10px; font-family: Consolas;")
        pct_lbl.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(name_lbl)
        layout.addWidget(price_lbl)
        layout.addWidget(pct_lbl)

class StockItemWidget(QFrame):
    on_delete = pyqtSignal(str)

    def __init__(self, stock):
        super().__init__()
        self.stock = stock
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            StockItemWidget {
                background-color: rgba(0, 0, 0, 76);
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # Top row
        top_layout = QHBoxLayout()
        
        name_layout = QVBoxLayout()
        name_layout.setSpacing(0)
        name_label = QLabel(self.stock.name)
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        symbol_label = QLabel(self.stock.symbol.upper())
        symbol_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; background: transparent;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(symbol_label)

        price_layout = QVBoxLayout()
        price_layout.setSpacing(0)
        price_label = QLabel(f"{self.stock.price:.2f}")
        price_label.setStyleSheet(f"color: {self.stock.color}; font-weight: bold; font-size: 18px; background: transparent; font-family: Consolas;")
        price_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
        change_label = QLabel(f"{self.stock.change:+.2f}  {self.stock.percent_change:+.2f}%")
        change_label.setStyleSheet(f"color: {self.stock.color}; font-size: 11px; background: transparent; font-family: Consolas;")
        change_label.setAlignment(Qt.AlignRight)
        
        price_layout.addWidget(price_label)
        price_layout.addWidget(change_label)

        top_layout.addLayout(name_layout)
        top_layout.addStretch()
        top_layout.addLayout(price_layout)

        # Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,50);")
        line.setFixedHeight(1)

        # Bottom row
        bottom_layout = QHBoxLayout()
        def add_indicator(label, value, color="white"):
            lbl = QLabel(f"<span style='color:rgba(255,255,255,150)'>{label}</span> <span style='color:{color}'>{value}</span>")
            lbl.setStyleSheet("font-size: 10px; background: transparent;")
            bottom_layout.addWidget(lbl)
            bottom_layout.addStretch()

        add_indicator("高", f"{self.stock.high:.2f}", "#ff4c4c")
        add_indicator("低", f"{self.stock.low:.2f}", "#33cc33")
        add_indicator("开", f"{self.stock.open:.2f}")
        
        lbl_vol = QLabel(f"<span style='color:rgba(255,255,255,150)'>量</span> <span style='color:white'>{self.stock.formatted_volume}</span>")
        lbl_vol.setStyleSheet("font-size: 10px; background: transparent;")
        bottom_layout.addWidget(lbl_vol)

        layout.addLayout(top_layout)
        layout.addWidget(line)
        layout.addLayout(bottom_layout)

        # Delete Button (Hidden by default)
        self.del_btn = QPushButton("×", self)
        self.del_btn.setFixedSize(20, 20)
        self.del_btn.setStyleSheet("QPushButton { background-color: rgba(0,0,0,128); color: #ff4c4c; border-radius: 10px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: rgba(0,0,0,200); }")
        self.del_btn.clicked.connect(lambda: self.on_delete.emit(self.stock.symbol))
        self.del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.del_btn.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.del_btn.move(self.width() - 25, 10)

    def enterEvent(self, event):
        self.del_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.del_btn.hide()
        super().leaveEvent(event)

# --------------------------
# Main Window
# --------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.all_stocks = []
        self.indices = []
        self.stocks = []
        self.drag_pos = None
        
        self.init_ui()
        self.setup_timer()
        self.fetch_data()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Expanded View ---
        self.expanded_widget = QWidget()
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(14, 14, 14, 14)
        expanded_layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(2)
        title = QLabel("实时监控")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 15px;")
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 9px;")
        header_vbox.addWidget(title)
        header_vbox.addWidget(self.time_label)
        
        header_layout.addLayout(header_vbox)
        header_layout.addStretch()
        
        min_btn = QPushButton("▬")
        min_btn.setFixedSize(24, 24)
        min_btn.setStyleSheet("color: rgba(255,255,255,200); background: transparent; font-weight: bold; font-size: 12px;")
        min_btn.setCursor(QCursor(Qt.PointingHandCursor))
        min_btn.clicked.connect(lambda: self.toggle_mode(True))
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("color: rgba(255,76,76,200); background: transparent; font-size: 18px; font-weight: bold;")
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(min_btn)
        header_layout.addWidget(close_btn)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入代码 (如 600519)")
        self.input_field.setStyleSheet("background-color: rgba(0,0,0,102); color: white; border: none; border-radius: 6px; padding: 6px; font-size: 12px;")
        self.input_field.returnPressed.connect(self.add_stock)
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setStyleSheet("color: white; background: transparent; font-size: 18px; font-weight: bold;")
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.clicked.connect(self.add_stock)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(add_btn)

        # Market Indices Container
        self.indices_frame = QFrame()
        self.indices_frame.setStyleSheet("QFrame { background-color: rgba(0,0,0,76); border-radius: 10px; }")
        self.indices_layout = QHBoxLayout(self.indices_frame)
        self.indices_layout.setContentsMargins(5, 5, 5, 5)
        self.indices_layout.setSpacing(0)

        # Scroll Area for Stocks
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.stocks_layout = QVBoxLayout(self.scroll_content)
        self.stocks_layout.setContentsMargins(0, 0, 0, 0)
        self.stocks_layout.setSpacing(8)
        self.stocks_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)

        expanded_layout.addLayout(header_layout)
        expanded_layout.addLayout(input_layout)
        expanded_layout.addWidget(self.indices_frame)
        expanded_layout.addWidget(self.scroll_area)

        # --- Minimized View (Marquee) ---
        self.minimized_widget = QWidget()
        minimized_layout = QHBoxLayout(self.minimized_widget)
        minimized_layout.setContentsMargins(10, 0, 10, 0)
        
        exp_btn = QPushButton("+")
        exp_btn.setFixedSize(24, 24)
        exp_btn.setStyleSheet("color: rgba(255,255,255,200); background: transparent; font-weight: bold; font-size: 16px;")
        exp_btn.setCursor(QCursor(Qt.PointingHandCursor))
        exp_btn.clicked.connect(lambda: self.toggle_mode(False))
        
        self.marquee = MarqueeWidget()
        
        m_close_btn = QPushButton("×")
        m_close_btn.setFixedSize(24, 24)
        m_close_btn.setStyleSheet("color: rgba(255,76,76,200); background: transparent; font-weight: bold; font-size: 18px;")
        m_close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        m_close_btn.clicked.connect(self.close)

        minimized_layout.addWidget(exp_btn)
        minimized_layout.addWidget(self.marquee, 1)
        minimized_layout.addWidget(m_close_btn)

        self.main_layout.addWidget(self.expanded_widget)
        self.main_layout.addWidget(self.minimized_widget)

        self.toggle_mode(self.config.is_minimized, animate=False)

    def toggle_mode(self, is_minimized, animate=True):
        self.config.save_state(is_minimized)
        
        start_rect = self.geometry()
        
        if is_minimized:
            self.expanded_widget.hide()
            self.minimized_widget.show()
            target_width, target_height = 800, 40
        else:
            self.expanded_widget.show()
            self.minimized_widget.hide()
            target_width, target_height = 280, 500

        end_rect = QRect(start_rect.right() - target_width + 1, 
                         start_rect.bottom() - target_height + 1, 
                         target_width, target_height)

        if animate:
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(300)
            self.anim.setStartValue(start_rect)
            self.anim.setEndValue(end_rect)
            self.anim.start()
        else:
            self.setGeometry(end_rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw translucent background simulating Mac's HUD material
        bg_color = QColor(30, 30, 32, 200) if not self.config.is_minimized else QColor(20, 20, 20, 220)
        radius = 16 if not self.config.is_minimized else 20
        
        painter.setBrush(bg_color)
        
        # White stroke with 0.15 opacity
        pen = QPen(QColor(255, 255, 255, 38))
        pen.setWidth(1)
        painter.setPen(pen)
        
        painter.drawRoundedRect(self.rect().adjusted(0,0,-1,-1), radius, radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_data)
        self.timer.start(5000)

    def normalize_symbol(self, s):
        s = s.strip().lower()
        if len(s) == 6 and s.isdigit():
            return f"sh{s}" if s.startswith(('6', '9', '5')) else f"sz{s}"
        return s

    def add_stock(self):
        symbol = self.input_field.text()
        self.input_field.clear()
        self.input_field.clearFocus()
        if not symbol: return
        
        normalized = self.normalize_symbol(symbol)
        if normalized not in self.config.symbols and normalized not in self.config.index_symbols:
            self.config.symbols.append(normalized)
            self.config.save_symbols()
            self.fetch_data()

    def remove_stock(self, symbol):
        if symbol in self.config.symbols:
            self.config.symbols.remove(symbol)
            self.config.save_symbols()
            self.fetch_data()

    def fetch_data(self):
        symbols = self.config.index_symbols + self.config.symbols
        url = f"http://hq.sinajs.cn/list={','.join(symbols)}"
        headers = {"Referer": "http://finance.sina.com.cn"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=3)
            resp.encoding = 'gbk'
            self.parse_data(resp.text)
        except Exception as e:
            pass

    def parse_data(self, text):
        new_stocks = []
        new_indices = []
        valid_symbols = []

        for line in text.strip().split('\n'):
            if '="' not in line: continue
            prefix, data_str = line.split('="')
            symbol = prefix.split('hq_str_')[-1]
            data_str = data_str.rstrip('";')
            parts = data_str.split(',')
            
            if len(parts) >= 32 and parts[0].strip():
                info = StockInfo(symbol, parts)
                valid_symbols.append(symbol)
                if symbol in self.config.index_symbols:
                    new_indices.append(info)
                else:
                    new_stocks.append(info)

        if len(new_stocks) != len(self.config.symbols):
            self.config.symbols = [s for s in self.config.symbols if s in valid_symbols]
            self.config.save_symbols()

        self.indices = new_indices
        self.stocks = new_stocks
        self.all_stocks = new_indices + new_stocks
        self.update_ui()

    def update_ui(self):
        if self.all_stocks:
            self.time_label.setText(f"更新: {self.all_stocks[0].time}")
            
        if self.config.is_minimized:
            self.marquee.update_data(self.all_stocks)
        else:
            # Update Indices (Top block)
            if not self.indices:
                self.indices_frame.hide()
            else:
                self.indices_frame.show()
                # Clear old indices
                while self.indices_layout.count():
                    item = self.indices_layout.takeAt(0)
                    if item.widget(): item.widget().deleteLater()
                
                for i, index_stock in enumerate(self.indices):
                    self.indices_layout.addWidget(IndexRowWidget(index_stock))
                    # Add divider
                    if i < len(self.indices) - 1:
                        line = QFrame()
                        line.setFrameShape(QFrame.VLine)
                        line.setStyleSheet("background-color: rgba(255,255,255,50);")
                        line.setFixedWidth(1)
                        self.indices_layout.addWidget(line)

            # Update Stocks (Scroll block)
            while self.stocks_layout.count() > 1: # keep stretch
                item = self.stocks_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            for stock in self.stocks:
                widget = StockItemWidget(stock)
                widget.on_delete.connect(self.remove_stock)
                self.stocks_layout.insertWidget(self.stocks_layout.count() - 1, widget)

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    
    window = MainWindow()
    window.show()
    
    screen = app.primaryScreen().geometry()
    window.move(screen.width() - window.width() - 20, screen.height() - window.height() - 60)
    
    sys.exit(app.exec_())