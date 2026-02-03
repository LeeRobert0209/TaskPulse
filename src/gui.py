from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QLineEdit, QApplication, QSystemTrayIcon, QMenu,
                               QTabWidget, QCheckBox, QPushButton, QListWidget, QHBoxLayout,
                               QSlider, QGroupBox, QGridLayout, QScrollArea, QComboBox, 
                               QFrame, QSizePolicy, QCompleter, QMessageBox, QStackedWidget)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QTime, QRect, QSize, QPoint, QStringListModel, QEvent
from PySide6.QtGui import QIcon, QAction, QPainter, QColor, QBrush, QPen, QFont, QPainterPath
from datetime import datetime, timedelta
from .config import APP_NAME, APP_ICON_PATH
from .data_manager import DataManager
from .utils import set_autostart



class HeatmapFullWidget(QWidget):
    def __init__(self, data_manager, year):
        super().__init__()
        self.data_manager = data_manager
        self.year = year
        self.grid_items = [] 
        self.setMouseTracking(True)
        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setStyleSheet("background: transparent;")
        
        # Style constants - Smaller to fit width 380px
        self.cell_size = 10 
        self.spacing = 2
        self.margin_top = 25  
        self.margin_left = 30 # For Mon/Wed/Fri labels
        self.block_gap_y = 20 # Gap between H1 and H2
        
        # Colors 
        self.colors = [
            "#ebedf0", # 0
            "#9be9a8", # 1
            "#40c463", # 2
            "#30a14e", # 3
            "#216e39", # 4+
        ]
        
        # Dimensions
        # Width: 27 weeks * (10+2) = 324 + 30 margin = 354 < 380. Good.
        # Height: 2 blocks * (7*(10+2) + 25 margin_top) + gap + legend
        # Block Height = 25 + 7*12 = 109
        # Total Height = 109 + 20 + 109 + 30 (legend) = ~270
        self.setMinimumHeight(300)

    def paintEvent(self, event):
        self.grid_items = []
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        stats = self.data_manager.get_daily_stats()
        
        # Weekday labels font
        painter.setPen(QColor("#767676"))
        font = painter.font()
        font.setPointSize(8) # Chinese fits well in 8-9
        painter.setFont(font)
        
        # Function to draw a block
        def draw_block(start_week, end_week, offset_y):
            # Draw Weekday Labels (Chinese)
            labels_y = offset_y + self.margin_top
            painter.drawText(0, labels_y + 1 * 12 + 10, "周一")
            painter.drawText(0, labels_y + 3 * 12 + 10, "周三")
            painter.drawText(0, labels_y + 5 * 12 + 10, "周五")
            
            # Start Date Calculation
            jan1 = datetime(self.year, 1, 1)
            # Find the Monday of the week containing Jan 1
            # jan1.weekday(): 0=Mon, ... 6=Sun
            # If Jan 1 is Mon(0), start is Jan 1.
            # If Jan 1 is Sun(6), start is Dec 26.
            base_start_date = jan1 - timedelta(days=jan1.weekday())
            
            # Draw Month Labels logic vars
            current_month = -1
            
            for col_idx, week_num in enumerate(range(start_week, end_week)):
                col_date = base_start_date + timedelta(weeks=week_num)
                
                # Draw Month Label
                # Check if this column starts a new month
                if col_date.month != current_month:
                     # Only draw if valid month and MATCHES THE CURRENT YEAR
                     # avoiding "Dec" from previous year appearing at start
                     if 1 <= col_date.month <= 12 and col_date.year == self.year:
                         current_month = col_date.month
                         # Use Chinese month format
                         month_name = f"{current_month}月"
                         x_m = self.margin_left + col_idx * (self.cell_size + self.spacing)
                         
                         # RESTORE PEN! It might be NoPen from rectangle drawing
                         painter.setPen(QColor("#767676"))
                         painter.drawText(x_m, offset_y + 15, month_name)
                
                for row in range(7):
                    day_date = col_date + timedelta(days=row)
                    date_str = day_date.strftime("%Y-%m-%d")
                    count = stats.get(date_str, 0)
                    
                    if count == 0: c_idx = 0
                    elif count <= 1: c_idx = 1
                    elif count <= 3: c_idx = 2
                    elif count <= 5: c_idx = 3
                    else: c_idx = 4
                    
                    bg_color = QColor(self.colors[c_idx])
                    
                    x = self.margin_left + col_idx * (self.cell_size + self.spacing)
                    y = offset_y + self.margin_top + row * (self.cell_size + self.spacing)
                    
                    rect = QRect(x, y, self.cell_size, self.cell_size)
                    self.grid_items.append((rect, f"{date_str}\n完成: {count}"))
                    
                    painter.setBrush(QBrush(bg_color))
                    painter.setPen(Qt.NoPen)
                    
                    # Faded if not current year
                    if day_date.year != self.year:
                        bg_color.setAlpha(100) 
                        painter.setBrush(QBrush(bg_color))
                        
                    painter.drawRoundedRect(rect, 2, 2)
                    
                    if date_str == datetime.now().strftime("%Y-%m-%d"):
                        painter.setBrush(Qt.NoBrush)
                        painter.setPen(QPen(QColor("#000000"), 1))
                        painter.drawRoundedRect(rect.adjusted(-1,-1,1,1), 2, 2)
                        painter.setPen(Qt.NoPen) # Reset

        # Split 53 weeks into 2 blocks: 27 weeks (H1) and 26 weeks (H2)
        # Block 1: Weeks 0-27
        draw_block(0, 27, 0)
        
        # Block 2: Weeks 27-53
        block1_h = self.margin_top + 7 * (self.cell_size + self.spacing)
        draw_block(27, 53, block1_h + self.block_gap_y)
        
        # Draw Legend (Bottom Right)
        ly = block1_h + self.block_gap_y + block1_h + 10
        # Wait, calculate exact Y
        # Y2 = block1_h + gap
        # H2 = block1_h
        # End Y = Y2 + H2
        end_y = 2 * block1_h + self.block_gap_y
        
        lx = self.width() - 100 # Approx right aligned
        ly = end_y 
        
        painter.setPen(QColor("#767676"))
        painter.drawText(lx, ly + 9, "Less")
        lx += 25
        for i, color in enumerate(self.colors):
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(lx + i*(self.cell_size+2), ly, self.cell_size, self.cell_size, 2, 2)
        lx += 5 * (self.cell_size + 2) + 5
        painter.setPen(QColor("#767676"))
        painter.drawText(lx, ly + 9, "More")

    def mouseMoveEvent(self, event):
        pos = event.pos()
        for rect, text in self.grid_items:
            if rect.contains(pos):
                if self.toolTip() != text:
                    self.setToolTip(text)
                return
        self.setToolTip("")


class TagStatsWidget(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        # self.setMinimumHeight(120) # Removed fixed height constraint
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        # Define palette for top tags
        self.palette = [
            "#3e75c3", # Blue
            "#40c463", # Green
            "#f9a01b", # Orange
            "#d9534f", # Red
            "#a2a2a2"  # Gray for others
        ]
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 10) # Reduced top margin
        layout.setSpacing(5)
        
        # Title
        title = QLabel("常用标签")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        layout.addWidget(title)
        
        # Ratio Bar Canvas
        self.bar_canvas = QWidget()
        self.bar_canvas.setFixedHeight(12) # Slim bar
        self.bar_canvas.setMouseTracking(True)
        # We need custom paint for the bar
        self.bar_canvas.paintEvent = self.paint_bar
        self.bar_canvas.mouseMoveEvent = self.on_bar_mouse_move
        layout.addWidget(self.bar_canvas)
        
        # Top List Container
        self.list_container = QWidget()
        self.list_layout = QGridLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 5, 0, 0)
        self.list_layout.setSpacing(4) # Gap between items
        layout.addWidget(self.list_container)
        
        self.bar_rects = [] # Store rects for hover detection
        self.cached_stats = [] 

    def update_data(self):
        # Update using REAL data
        self.cached_stats = self.data_manager.get_tag_stats()
        
        self.bar_canvas.update()
        self.update_list()
        
    def paint_bar(self, event):
        self.bar_rects = []
        painter = QPainter(self.bar_canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Full width rounded rect background
        w = self.bar_canvas.width()
        h = self.bar_canvas.height()
        
        if not self.cached_stats:
            painter.setBrush(QBrush(QColor("#ebedf0")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, 6, 6)
            return
            
        total = sum(c for n, c in self.cached_stats)
        if total == 0: return

        x_cursor = 0
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 6, 6)
        painter.setClipPath(path)
        
        # Extended palette for bar
        bar_palette = [
            "#3e75c3", "#40c463", "#f9a01b", "#d9534f", "#9c27b0", "#00bcd4"
        ]
        
        top_n_bar = self.cached_stats[:6]
        others_count = total - sum(c for n, c in top_n_bar)
        
        display_items = []
        for i, (name, count) in enumerate(top_n_bar):
             color = bar_palette[i]
             display_items.append((name, count, color))
             
        if others_count > 0:
             display_items.append(("其他", others_count, "#a2a2a2"))
             
        for name, count, color_hex in display_items:
            ratio = count / total
            seg_w = w * ratio
            
            rect = QRect(int(x_cursor), 0, int(seg_w + 1), h)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(rect)
            
            self.bar_rects.append((rect, f"{name}: {count}次 ({ratio:.1%})"))
            x_cursor += seg_w

    def on_bar_mouse_move(self, event):
        pos = event.pos()
        for rect, text in self.bar_rects:
            if rect.contains(pos):
                if self.bar_canvas.toolTip() != text:
                    self.bar_canvas.setToolTip(text)
                return
        self.bar_canvas.setToolTip("")

    def update_list(self):
        # Clear old items in grid
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not self.cached_stats:
             lbl = QLabel("暂无数据 (完成专注任务后自动生成)")
             lbl.setStyleSheet("color: #999; font-size: 12px;")
             self.list_layout.addWidget(lbl, 0, 0)
             return
             
        # Show Top 10
        top_n = self.cached_stats[:10]
        
        # Simple palette cycle for dots
        colors = [
            "#3e75c3", "#40c463", "#f9a01b", "#d9534f", "#9c27b0", "#00bcd4",
            "#e91e63", "#2196f3", "#009688", "#cddc39", "#ffeb3b", "#ff9800",
            "#795548", "#9e9e9e", "#607d8b", "#3f51b5", "#673ab7", "#4caf50"
        ]
        
        for i, (name, count) in enumerate(top_n):
            # 2 columns layout
            # Row-major: 0,1 in row 0; 2,3 in row 1...
            col = i % 2 
            row = i // 2
            
            # Container for the cell
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(5)
            
            # Color Dot
            color = colors[i % len(colors)]
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            cell_layout.addWidget(dot)
            
            # Name
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #444; font-size: 12px;")
            cell_layout.addWidget(name_lbl)
            
            cell_layout.addStretch()
            
            # Count
            count_lbl = QLabel(f"{count}")
            count_lbl.setStyleSheet("color: #888; font-size: 11px;")
            cell_layout.addWidget(count_lbl)
            
            self.list_layout.addWidget(cell_widget, row, col)


class ContributionPanel(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.year = datetime.now().year
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # 1. Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 0)
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Year Selector
        self.year_combo = QComboBox()
        current_year = datetime.now().year
        # List years from current down to 2024 or based on data
        # For now static is fine or scan data
        # Let's verify stats data for years? 
        # Scan stats keys for years
        stats = self.data_manager.get_daily_stats()
        years = set()
        years.add(current_year)
        if stats:
            for dStr in stats.keys():
                try:
                    y = int(dStr.split('-')[0])
                    years.add(y)
                except: pass
        
        sorted_years = sorted(list(years), reverse=True)
        for y in sorted_years:
            self.year_combo.addItem(str(y), y)
            
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        header_layout.addWidget(self.year_combo)
        
        layout.addLayout(header_layout)
        
        # 2. Main Content (Labels + Grid)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 5, 10, 10)
        
        self.heatmap = HeatmapFullWidget(self.data_manager, self.year)
        content_layout.addWidget(self.heatmap)
        
        layout.addLayout(content_layout)
        
        self.tag_stats = TagStatsWidget(self.data_manager)
        layout.addWidget(self.tag_stats)
        
        self.tag_stats.update_data() # Initial load
        self.update_stats_label()

    def on_year_changed(self, index):
        year = int(self.year_combo.currentData())
        self.year = year
        self.heatmap.year = year
        self.heatmap.update()
        self.update_stats_label()
        
    def  update_stats_label(self):
        stats = self.data_manager.get_daily_stats()
        # Count only for selected year
        count = 0
        for d_str, c in stats.items():
            if d_str.startswith(str(self.year)):
                count += c
        self.title_label.setText(f"{self.year} 年累计坚持: {count} 次")
        
    def update(self):
        super().update()
        self.heatmap.update()
        if hasattr(self, 'tag_stats'):
            self.tag_stats.update_data()
        self.update_stats_label()



class TaskItemWidget(QWidget):
    def __init__(self, title, time_info, countdown_text, is_finished=False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Col 1: Title (Flex 2)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.title_label, 2)
        
        # Col 2: Time Info (Flex 2)
        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-size: 12px; color: #666; font-family: Consolas, monospace;")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label, 2)
        
        # Col 3: Countdown (Flex 1)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 14px; font-family: Consolas, monospace; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.status_label, 1)
        
        self.update_content(title, time_info, countdown_text, is_finished)

    def update_content(self, title, time_info, countdown_text, is_finished, bg_color="white"):
        # Update Content
        if is_finished:
             self.title_label.setText(f"✅ {title}")
        else:
             self.title_label.setText(f"⏳ {title}")
             
        self.time_label.setText(time_info)
        self.status_label.setText(countdown_text)
        
        # Style
        if is_finished:
            # Finished overrides the bg_color argument usually
            self.setStyleSheet(".TaskItemWidget { background-color: #d4edda; border-radius: 4px; }")
            self.status_label.setStyleSheet("color: #155724; font-weight: bold;")
        else:
            if bg_color:
                self.setStyleSheet(f".TaskItemWidget {{ background-color: {bg_color}; border-bottom: 1px solid #eee; }}")
            else:
                # Transparent to let QListWidget alternating color show through? 
                # Actually QListWidgetItem widget covers the item. We need to set background on widget transparent.
                self.setStyleSheet(".TaskItemWidget { background-color: transparent; }")
                
            if "00:0" in countdown_text and "剩余" in countdown_text: # Urgency color?
                 self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            else:
                 self.status_label.setStyleSheet("color: #007bff; font-weight: bold;")

class MiniModeWidget(QWidget):
    """
    Compact 'Music Player' style widget for focused work.
    Shows only Task Name, Timer, Restore, and Close.
    Support dragging since window is frameless.
    """
    restore_clicked = Signal()
    close_clicked = Signal()
    add_task_clicked = Signal(str) # Emits task name

    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Floating effect needs a bit of margin for shadow if we were using graphics effect, 
        # but for simple widget styling we do border and radius.
        # Floating effect with specific selector to avoid leaking style to children
        self.setStyleSheet("""
            QWidget#MiniModeWidget {
                background-color: #222222; 
                border: 1px solid #555555; 
                border-radius: 0px; 
            }
        """)
        self.setObjectName("MiniModeWidget")
        self.setAttribute(Qt.WA_StyledBackground, True) # Ensure background draws
        
        # Ultra-Compact 300x30
        self.setFixedSize(300, 30)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0) 
        layout.setSpacing(5)
        
        # Drag handle logic
        self._drag_pos = None

        # controls layout
        
        # Task Label
        self.task_label = QLabel("无任务")
        self.task_label.setStyleSheet("color: #888; font-size: 10px; border: none; background: transparent;")
        self.task_label.setFixedWidth(70) 
        
        # Time Label
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        
        # Controls
        # Controls
        # Restore Button
        self.btn_restore = QPushButton("❐") # Square icon for restore
        self.btn_restore.setFixedSize(20, 20)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setToolTip("恢复标准模式")
        self.btn_restore.clicked.connect(self.restore_clicked.emit)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                border: none; 
                border-radius: 10px; 
                color: #eee; 
                font-size: 10px;
                padding-bottom: 2px;
            }
            QPushButton:hover { background-color: #666; }
        """)

        # Add Task Button
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(20, 20)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setToolTip("快速添加任务")
        self.btn_add.clicked.connect(self.on_add_clicked)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #007aff; 
                border: none; 
                border-radius: 10px; 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)

        # Close Button
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("隐藏到托盘")
        self.btn_close.clicked.connect(self.close_clicked.emit)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: none; 
                border-radius: 10px; 
                color: #888; 
                font-size: 10px;
                padding-bottom: 2px;
            }
            QPushButton:hover { background-color: #cc0000; color: white; }
        """)

        layout.addWidget(self.task_label)
        layout.addWidget(self.time_label, 1) # Stretch time
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_restore)
        layout.addWidget(self.btn_close)
        
    def on_add_clicked(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        text, ok = QInputDialog.getText(self, "添加任务", "任务名称:", QLineEdit.Normal, "")
        if ok and text.strip():
            self.add_task_clicked.emit(text.strip())
        
    def update_info(self, task_name, time_str, is_break=False):
        # Truncate task name
        metrics = self.task_label.fontMetrics()
        elided = metrics.elidedText(task_name, Qt.ElideRight, self.task_label.width())
        self.task_label.setText(elided)
        self.time_label.setText(time_str)
        
        if is_break:
             # Green digital glow
             self.time_label.setStyleSheet("""
                font-family: Consolas, monospace; 
                font-size: 20px; 
                color: #4cd964; 
                font-weight: bold; 
                border: none; 
                background: transparent;
             """)
        else:
             # Blue digital glow
             self.time_label.setStyleSheet("""
                font-family: Consolas, monospace; 
                font-size: 20px; 
                color: #007aff; 
                font-weight: bold; 
                border: none; 
                background: transparent;
             """)

    # Dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.window().move(event.globalPos() - self._drag_pos)
            event.accept()

class MainWindow(QMainWindow):
    # Custom signals
    request_show = Signal()
    sig_notify = Signal(str, str) # title, message

    def __init__(self, scheduler=None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(400, 600) # User mentioned 400x600 as standard
        self.data_manager = DataManager()
        self.scheduler = scheduler
        self.pomodoro_count = 0 # Track completed Pomodoros
        
        self.is_mini_mode = False
        self.normal_geometry = None
        
        # Setup UI
        # Setup UI - Use StackedWidget for Mode Switching
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # --- Page 1: Normal Mode ---
        self.central_widget_normal = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget_normal)
        main_layout = self.main_layout
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.stack.addWidget(self.central_widget_normal)
        
        # --- Page 2: Mini Mode (Lazy Init or Pre-init) ---
        self.mini_widget = MiniModeWidget(self)
        self.mini_widget.restore_clicked.connect(self.toggle_mini_mode)
        self.mini_widget.close_clicked.connect(self.close)
        self.mini_widget.add_task_clicked.connect(self.quick_add_task)
        self.stack.addWidget(self.mini_widget)
        
        # Tab 1: Dashboard (Tasks & Input)
        self.dashboard_tab = QWidget()
        self.setup_dashboard(self.dashboard_tab)
        self.tabs.addTab(self.dashboard_tab, "仪表盘")
        
        # Tab 2: Records
        self.records_tab = QWidget()
        self.setup_records(self.records_tab)
        self.tabs.addTab(self.records_tab, "坚持记录")

        # Tab 3: Settings
        self.settings_tab = QWidget()
        self.setup_settings(self.settings_tab)
        self.tabs.addTab(self.settings_tab, "设置")

        # Connect signals
        self.request_show.connect(self.show_normal_thread_safe)
        
        # Load initial state
        self.load_settings()

    def setup_dashboard(self, parent):
        layout = QVBoxLayout(parent)
        
        # Header Row with Mini Mode Button
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        self.btn_mini_mode = QPushButton("精简模式")
        self.btn_mini_mode.setToolTip("切换到桌面迷你倒计时")
        self.btn_mini_mode.setStyleSheet("""
            QPushButton {
                color: #666; background: transparent; border: 1px solid #ccc; border-radius: 4px; padding: 2px 8px; font-size: 12px;
            }
            QPushButton:hover { background-color: #f0f0f0; color: #333; }
        """)
        self.btn_mini_mode.clicked.connect(self.toggle_mini_mode)
        header_layout.addWidget(self.btn_mini_mode)
        
        layout.addLayout(header_layout)
        
        # 0. Encouragement Label (Added per user request)
        quote_text = "种一棵树最好的时间是十年前，其次是现在。\n保持专注，当下即是未来。" # Fallback
        
        # Try load random quote
        import json
        import random
        from .config import PROJECT_ROOT
        
        quote_file = PROJECT_ROOT / "resources" / "quotes.json"
        if quote_file.exists():
            try:
                with open(quote_file, 'r', encoding='utf-8') as f:
                    quotes = json.load(f)
                    if quotes:
                        q = random.choice(quotes)
                        quote_text = f"“{q['content']}”\n—— {q['author']}"
            except Exception as e:
                print(f"Error loading quotes: {e}")

        self.encourage_label = QLabel(quote_text)
        self.encourage_label.setAlignment(Qt.AlignCenter)
        self.encourage_label.setWordWrap(True) # Ensure long quotes wrap
        self.encourage_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #555;
                font-style: italic;
                font-family: "Microsoft YaHei", sans-serif;
                padding: 8px;
                background-color: #f0f4f8;
                border-radius: 6px;
                min-height: 45px; 
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(self.encourage_label)

        # 1. Task Input Section (Top)
        input_group = QGroupBox("1. 设定任务")
        input_layout = QVBoxLayout(input_group)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("第一步：在此输入任务名称，然后点击下方时间按钮开始...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
        """)

        # Tag Auto-complete (Select below input)
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.input_field.setCompleter(self.completer)
        
        # Install event filter to show popup on click
        self.input_field.installEventFilter(self)
        self.input_field.returnPressed.connect(self.on_input_return_pressed)
        
        input_layout.addWidget(self.input_field)
        
        # Prominent 25m Pomodoro Button
        self.pomo_btn = QPushButton("开始 25分钟 标准番茄钟 🍅")
        self.pomo_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545; 
                color: white; 
                font-size: 16px; 
                font-weight: bold; 
                padding: 12px;
                border-radius: 6px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.pomo_btn.clicked.connect(lambda: self.start_focus_with_input(25, is_pomodoro=True))
        input_layout.addWidget(self.pomo_btn)
        
        # Return key triggers start
        self.input_field.returnPressed.connect(self.on_input_return_pressed)
        
        layout.addWidget(input_group)
        
        # 2. Timer Section (Collapsible)
        # Toggle Button
        self.toggle_timer_btn = QPushButton("▶ 更多时间选项 (自定义时长)")
        self.toggle_timer_btn.setCheckable(True)
        self.toggle_timer_btn.setChecked(False)
        self.toggle_timer_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                border: none;
                padding: 5px;
                color: #555;
                font-size: 14px;
            }
            QPushButton:hover { color: #007bff; }
        """)
        self.toggle_timer_btn.toggled.connect(self.on_toggle_timer)
        layout.addWidget(self.toggle_timer_btn)

        # Container for advanced timer controls (Hidden by default)
        self.timer_container = QWidget()
        focus_layout = QVBoxLayout(self.timer_container)
        focus_layout.setContentsMargins(5, 0, 5, 0) # Indent slightly
        
        # Slider Info Label
        self.timer_label = QLabel("0 分钟")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #007bff;")
        focus_layout.addWidget(self.timer_label)
        
        # Slider
        self.timer_slider = QSlider(Qt.Horizontal)
        self.timer_slider.setRange(0, 120)
        self.timer_slider.setValue(0)
        self.timer_slider.setTickPosition(QSlider.TicksBelow)
        self.timer_slider.setTickInterval(30)
        self.timer_slider.setSingleStep(5) 
        self.timer_slider.setPageStep(30)
        
        self.timer_slider.valueChanged.connect(self.on_slider_changed)
        self.timer_slider.sliderReleased.connect(self.on_slider_released)
        
        focus_layout.addWidget(self.timer_slider)
        
        # Manual Quick Buttons
        self.btn_layout = QHBoxLayout() # Make class attribute to access later
        
        # Test 10s Button (Hidden by default)
        self.test_btn = QPushButton("测试 (5秒)")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800; 
                color: white; 
                font-weight: bold;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #e68900; }
        """)
        self.test_btn.clicked.connect(lambda: self.start_focus_with_input(5/60)) # 5 seconds
        self.test_btn.setVisible(False)
        self.btn_layout.addWidget(self.test_btn)

        # Removed 25 from here as it's now prominent above
        for mins in [15, 30, 45, 60]:
            btn = QPushButton(f"{mins}分钟")
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 6px;
                    padding: 5px;
                    background-color: #e0e0e0;
                }
                QPushButton:hover { background-color: #d0d0d0; }
            """)
            btn.clicked.connect(lambda checked=False, m=mins: self.start_focus_with_input(m))
            self.btn_layout.addWidget(btn)
        focus_layout.addLayout(self.btn_layout)

        # Start Button for Slider
        self.start_btn = QPushButton("开始专注 (使用滑动条时间)")
        self.start_btn.clicked.connect(lambda: self.start_focus_with_input(self.timer_slider.value()))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        focus_layout.addWidget(self.start_btn)
        
        layout.addWidget(self.timer_container)
        self.timer_container.setVisible(False) # Default Hidden        
        # 3. Active Tasks Section (Bottom)
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView

        self.task_list = QTableWidget()
        self.task_list.setColumnCount(3)
        self.task_list.setHorizontalHeaderLabels(["任务名称", "开始-结束", "倒计时"])
        
        # Grid & Style
        self.task_list.setShowGrid(True)
        self.task_list.setAlternatingRowColors(True)
        self.task_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_list.verticalHeader().setVisible(False)
        self.task_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Column Resizing
        header = self.task_list.horizontalHeader()
        # Evenly distribute columns or give more space to title?
        # User asked for "average out", implying equal or better balance.
        # Let's try Stretch for Title, and Fixed/ResizeToContents with minimums for others?
        # Or just Stretch all? "Start-End" is wide. "Countdown" is medium. "Title" varies.
        # Let's give Start-End and Title more space, Countdown less.
        
        # Strategy: Title (Stretch), Start-End (ResizeToContents usually wide enough), Countdown (ResizeToContents)
        # But user said "too crowded at back".
        # Let's use Stretch for ALL to fill width evenly?
        # Or: Title (Stretch, Factor 2), Time (Stretch, Factor 2), Countdown (Stretch, Factor 1)
        
        header.setSectionResizeMode(0, QHeaderView.Stretch) 
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Time is fixed width roughly
        header.setSectionResizeMode(2, QHeaderView.Stretch) # Give countdown some stretch space too
        
        # Actually, QHeaderView.Stretch on multiple splits them.
        # Let's set 0 and 1 to Stretch, 2 to ResizeToContents?
        # Or simple: All Stretch.
        # header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Let's try: Title (Stretch), Time (ResizeToContents), Countdown (ResizeToContents) was the old way.
        # New way: Title (Stretch), Time (Stretch), Countdown (ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch) 
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) 
        
        # Tooltip is enabled by default for items if setToolTip is called, 
        # or if text is elided and we assume Qt handles it?
        # Qt usually handles elided text tooltips automatically if text doesn't fit?
        # We will manually setToolTip just in case.
        
        # Custom Style for Table
        self.task_list.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
                gridline-color: #e0e0e0;
                border: 1px solid #ccc;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
                font-weight: bold;
                color: #555;
            }
        """)

        self.task_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.task_list)
        
        # UI Refresh Timer (for countdowns)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_task_timers)
        self.ui_timer.start(1000) # Update every second
        
        # Keep track of active tasks locally for UI countdown 
        # {task_id: {end_time, title, finished: bool, popup_shown: bool, type: 'focus'|'break'}}
        self.active_ui_tasks = {}

    def start_focus_with_input(self, minutes, is_pomodoro=False):
        # If starting a break, we might skip input check?
        # But this function is usually called from UI buttons (Focus).
        
        task_text = self.input_field.text().strip()
        if not task_text:
            # Visual feedback
            self.input_field.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                    font-size: 14px;
                    border: 2px solid #ff3333;
                    border-radius: 5px;
                    background-color: #fff0f0;
                }
            """)
            self.input_field.setPlaceholderText("❌ 请务必先输入任务名称！")
            QTimer.singleShot(1000, self.reset_input_style)
            return

        # If 25m button pressed, track as pomodoro type
        t_type = "focus_pomo" if is_pomodoro else "focus_manual"
        
        self.start_focus_timer(minutes, task_text, task_type=t_type)
        # Don't clear input if it's a pomodoro chain? 
        # Actually user might want to keep same task name.
        # But let's clear for now to be safe, or maybe keep it?
        # User request didn't specify. Clearing is standard behavior.
        self.input_field.clear()

    def reset_input_style(self):
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
        """)
        self.input_field.setPlaceholderText("第一步：在此输入任务名称，然后点击下方时间按钮开始...")

    # Replaces old start_focus_timer
    def start_focus_timer(self, minutes, title="专注模式", task_type="focus_manual"):
        if minutes <= 0:
            return
            
        if self.scheduler:
            import uuid
            from datetime import datetime, timedelta
            
            task_id = f"focus_{uuid.uuid4().hex[:8]}"
            now = datetime.now()
            end_time = now + timedelta(minutes=minutes)
            
            # Store for UI display
            self.active_ui_tasks[task_id] = {
                "title": title,
                "start_time": now,
                "end_time": end_time,
                "total_minutes": minutes,
                "finished": False,
                "popup_shown": False,
                "type": task_type
            }
            self.refresh_task_list(full_reload=True)
            
            # We don't remove from UI list in job_function anymore.
            # job_function only handles System Notification (Tray)
            def job_function():
                # Display explicit seconds for very short durations
                duration_str = f"{minutes} 分钟" if minutes >= 1 else f"{int(minutes*60)} 秒"
                # Use signal instead of direct Utils call
                self.sig_notify.emit("任务完成", f"任务 [{title}] 的 {duration_str} 已达成！")
                
            self.scheduler.add_countdown_task(task_id, minutes, job_function)
            
            # Friendly format for start notification too
            duration_str = f"{minutes} 分钟" if minutes >= 1 else f"{int(minutes*60)} 秒"
            self.sig_notify.emit("任务开始", f"[{title}] - {duration_str} 倒计时开始。")
            
            if minutes >= 1:
                self.timer_label.setText(f"设定: {minutes} 分钟")
            else:
                 self.timer_label.setText(f"设定: {int(minutes*60)} 秒")
        else:
            print("Scheduler not initialized!")

    def show_context_menu(self, pos):
        item = self.task_list.itemAt(pos)
        if item:
            # TableWidget items store data individually. We put task_id on column 0 item.
            # We need to find the row, then get item at (row, 0)
            row = self.task_list.row(item)
            id_item = self.task_list.item(row, 0)
            task_id = id_item.data(Qt.UserRole)
            
            info = self.active_ui_tasks.get(task_id)
            
            menu = QMenu(self)
            
            if info and info.get("finished"):
                close_action = QAction("✅ 关闭任务/清除历史", self)
                close_action.triggered.connect(lambda: self.cancel_task(task_id, row, force_close=True))
                menu.addAction(close_action)
            else:
                cancel_action = QAction("🛑 取消任务", self)
                cancel_action.triggered.connect(lambda: self.cancel_task(task_id, row))
                menu.addAction(cancel_action)
                
            menu.exec(self.task_list.mapToGlobal(pos))

    def cancel_task(self, task_id, row, force_close=False):
        if task_id and task_id in self.active_ui_tasks:
            # Remove from scheduler
            if self.scheduler:
                self.scheduler.remove_task(task_id)
            
            # Remove from UI tracking
            del self.active_ui_tasks[task_id]
            
            # Remove from table
            self.task_list.removeRow(row)
            
            if not force_close:
                self.sig_notify.emit("任务取消", "已取消该专注任务。")
    
    def update_task_timers(self):
        # Called every second
        updated = False
        popup_needed_for = None # Store task info if popup is needed
        
        from datetime import datetime
        from PySide6.QtWidgets import QMessageBox
        now = datetime.now()
        
        # Don't auto remove anymore, just mark finished
        
        for t_id, info in self.active_ui_tasks.items():
            if info["finished"]:
                continue
                
            remaining = (info["end_time"] - now).total_seconds()
            
            if remaining <= 0:
                # Task Just Finished
                info["finished"] = True
                info["finished_time"] = now # Record actual finish time
                updated = True
                
                # Check if popup is needed
                if not info["popup_shown"]:
                    popup_needed_for = info
                    info["popup_shown"] = True
            else:
                updated = True
            
        if updated:
            self.refresh_task_list(full_reload=False)
            
            # Force UI update so Green Background appears BEFORE popup blocks execution
            QApplication.processEvents() 

        # Handle Popup AFTER UI refresh
        if popup_needed_for:
            info = popup_needed_for
            t_type = info.get("type", "focus_manual")
            
            if t_type == "focus_pomo":
                self.pomodoro_count += 1
                
                # Record to persistent stats
                # Pass Title as tag
                self.data_manager.record_pomodoro(task_name=info['title'])
                
                # Refresh graph
                if hasattr(self, 'contrib_panel'):
                    self.contrib_panel.update()
                
                breaks_needed = 15 if (self.pomodoro_count % 4 == 0) else 5
                break_name = "长休息" if breaks_needed == 15 else "短休息"
                
                msg = QMessageBox(self)
                msg.setWindowTitle("番茄钟完成!")
                msg.setText(f"恭喜！第 {self.pomodoro_count} 个番茄钟已完成。\n\n接下来建议进行 {breaks_needed} 分钟{break_name}。\n是否立即开始休息？")
                msg.setIcon(QMessageBox.Information)
                yes_btn = msg.addButton("开始休息", QMessageBox.YesRole)
                no_btn = msg.addButton("稍后", QMessageBox.NoRole)
                msg.exec()
                
                if msg.clickedButton() == yes_btn:
                    self.start_focus_timer(breaks_needed, f"{break_name} ({breaks_needed}min)", task_type="break")
                    
            elif t_type == "break":
                msg = QMessageBox(self)
                msg.setWindowTitle("休息结束!")
                msg.setText("休息时间到了，神清气爽！\n是否开始下一个25分钟番茄钟？")
                msg.setIcon(QMessageBox.Question)
                yes_btn = msg.addButton("开始专注", QMessageBox.YesRole)
                no_btn = msg.addButton("停止", QMessageBox.NoRole)
                msg.exec()
                
                if msg.clickedButton() == yes_btn:
                    self.start_focus_timer(25, "下一轮专注", task_type="focus_pomo")
                    
            else:
                # Manual task
                msg = QMessageBox(self)
                msg.setWindowTitle("专注完成!")
                msg.setText(f"恭喜！任务 [{info['title']}] 已完成！\n请休息一下吧。")
                msg.setIcon(QMessageBox.Information)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()

                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()

    def toggle_mini_mode(self):
        """Switch between Normal and Mini Mode."""
        if not self.is_mini_mode:
            # === Switch to Mini Mode ===
            self.is_mini_mode = True
            self.normal_geometry = self.geometry()
            
            # Hide first
            self.hide()
            
            # Change flags: Frameless + StayOnTop
            # Removed Qt.Tool as it can cause restoration issues on some Windows versions
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            
            # Setup Mini Widget if not already in stack (it is now pre-inited, but just in case logic changed)
            if self.stack.indexOf(self.mini_widget) == -1:
                 self.stack.addWidget(self.mini_widget)
            
            # Switch Stack
            self.stack.setCurrentWidget(self.mini_widget)
            
            # FORCE Resize and constraints
            # setFixedSize on MainWindow is the only sure way to stop layout expansion
            self.setFixedSize(300, 30)
            self.show()
            
        else:
            # === Restore to Normal Mode ===
            self.is_mini_mode = False
            
            self.hide()
            
            # 1. Restore Flags
            self.setWindowFlags(Qt.Window)
            
            # 2. Swap Content
            self.stack.setCurrentWidget(self.central_widget_normal)
            
            # 3. Reset Constraints
            self.setMinimumSize(0, 0) 
            self.setMaximumSize(16777215, 16777215) # QWIDGETSIZE_MAX
            
            # 4. Restore Geometry
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            else:
                self.resize(400, 600)
                # Center on screen fallback
                try:
                    screen_geo = self.screen().availableGeometry()
                    if screen_geo.isValid():
                        center_point = screen_geo.center()
                        self.move(center_point.x() - 200, center_point.y() - 300)
                except:
                    pass
            
            # 5. Show and Activate
            # Using showNormal() ensuring it's not minimized
            self.showNormal()
            self.activateWindow()
            self.raise_()
            
        self.refresh_task_list(full_reload=False) # Update timers immediately

    def refresh_task_list(self, full_reload=False):
        # Update Mini Widget if active
        if self.is_mini_mode and hasattr(self, 'mini_widget'):
            # Find most urgent active task
            active_task = None
            min_remaining = float('inf')
            
            from datetime import datetime
            now = datetime.now()
            
            for t_id, info in self.active_ui_tasks.items():
                if not info["finished"]:
                    rem = (info["end_time"] - now).total_seconds()
                    if rem < min_remaining:
                        min_remaining = rem
                        active_task = info
            
            if active_task:
                 title = active_task['title']
                 rem_sec = int(min_remaining) if min_remaining > 0 else 0
                 mins, secs = divmod(rem_sec, 60)
                 if mins >= 60:
                     hrs, mins = divmod(mins, 60)
                     time_str = f"{hrs}:{mins:02d}:{secs:02d}"
                 else:
                     time_str = f"{mins:02d}:{secs:02d}"
                 
                 is_break = active_task.get("type") == "break"
                 self.mini_widget.update_info(title, time_str, is_break)
            else:
                 self.mini_widget.update_info("暂无任务", "00:00")
            
            # We skip table update if in mini mode to save resources? 
            # Or just let it run in background. It's fine to run; table is hidden.
        
        if full_reload:
             self.task_list.setRowCount(0) # Clear table
        
        from datetime import datetime
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTableWidgetItem
        now = datetime.now()
        
        # We need to map active tasks to rows.
        # Since we might not want to re-create rows every second, we search.
        # But for simplicity and stability, with < 50 tasks, re-populating cells is fine.
        # Ideally, we find the row by UserRole.
        
        # 1. Map existing rows
        existing_rows = {} # t_id -> row_index
        for row in range(self.task_list.rowCount()):
            item = self.task_list.item(row, 0)
            if item:
                t_id = item.data(Qt.UserRole)
                existing_rows[t_id] = row
            
        current_ids = set()
        
        for t_id, info in self.active_ui_tasks.items():
            current_ids.add(t_id)
            
            # Format Times
            start_dt = info.get('start_time', now)
            start_str = start_dt.strftime("%H:%M:%S")
            
            if info.get("finished"):
                finish_dt = info.get("finished_time", now)
                end_str = finish_dt.strftime("%H:%M:%S")
                
                time_info = f"{start_str} - {end_str}"
                countdown_text = "完成"
                finished = True
            else:
                remaining_seconds = int((info["end_time"] - now).total_seconds())
                if remaining_seconds < 0: remaining_seconds = 0
                
                mins, secs = divmod(remaining_seconds, 60)
                time_str = f"{mins:02d}:{secs:02d}"
                # Calculate expected end time
                end_dt = info["end_time"]
                end_str = end_dt.strftime("%H:%M:%S")
                
                time_info = f"{start_str} - {end_str}"
                countdown_text = f"⏳ {time_str}"
                finished = False
            
            # Update or Create Row
            if t_id in existing_rows:
                row = existing_rows[t_id]
                # Update items
                self.task_list.item(row, 0).setText(f"✅ {info['title']}" if finished else f"⏳ {info['title']}")
                self.task_list.item(row, 1).setText(time_info)
                self.task_list.item(row, 2).setText(countdown_text)
                
                # Update Style for Finished
                if finished:
                    for col in range(3):
                        self.task_list.item(row, col).setBackground(QColor("#d4edda"))
                        self.task_list.item(row, col).setForeground(QColor("#155724"))
                else:
                     # Restore default colors (alternating handled by table, but we might have overwritten)
                     # Actually setBackground(QBrush()) clears it?
                     for col in range(3):
                        self.task_list.item(row, col).setData(Qt.BackgroundRole, None) # Reset to default
                        self.task_list.item(row, col).setForeground(QColor("black"))
                        if col == 2:
                             # Countdown color
                             if "00:0" in countdown_text and "剩余" in countdown_text:
                                  self.task_list.item(row, col).setForeground(QColor("#d9534f"))
                             else:
                                  self.task_list.item(row, col).setForeground(QColor("#007bff"))

            else:
                # Add new row
                row = self.task_list.rowCount()
                self.task_list.insertRow(row)
                
                # Col 0: Title
                title_text = f"✅ {info['title']}" if finished else f"⏳ {info['title']}"
                item0 = QTableWidgetItem(title_text)
                item0.setData(Qt.UserRole, t_id)
                item0.setToolTip(info['title']) # Force tooltip
                self.task_list.setItem(row, 0, item0)
                
                # Col 1: Time
                item1 = QTableWidgetItem(time_info)
                item1.setTextAlignment(Qt.AlignCenter)
                self.task_list.setItem(row, 1, item1)
                
                # Col 2: Countdown
                item2 = QTableWidgetItem(countdown_text)
                item2.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.task_list.setItem(row, 2, item2)
                
                # Initial Style
                if finished:
                    for col in range(3):
                        self.task_list.item(row, col).setBackground(QColor("#d4edda"))
                        self.task_list.item(row, col).setForeground(QColor("#155724"))
                else:
                    item2.setForeground(QColor("#007bff"))

        # Cleanup zombies
        # Iterate backwards to avoid index shifting issues
        for row in range(self.task_list.rowCount() - 1, -1, -1):
            item = self.task_list.item(row, 0)
            t_id = item.data(Qt.UserRole)
            if t_id not in current_ids:
                self.task_list.removeRow(row)

    def on_slider_changed(self, value):
        self.timer_label.setText(f"{value} 分钟")

    def on_slider_released(self):
        val = self.timer_slider.value()
        snaps = [0, 30, 60, 90, 120]
        closest = min(snaps, key=lambda x: abs(x - val))
        if abs(val - closest) < 5: 
            self.timer_slider.setValue(closest)

    def on_toggle_timer(self, checked):
        self.timer_container.setVisible(checked)
        if checked:
             self.toggle_timer_btn.setText("▼ 更多时间选项 (自定义时长)")
        else:
             self.toggle_timer_btn.setText("▶ 更多时间选项 (自定义时长)")

    # Legacy handle_input removed or integrated
    def handle_input(self):
        # If user presses enter in input box, maybe default to 25 mins?
        # Or just do nothing and wait for button press.
        pass

    def setup_records(self, parent):
        layout = QVBoxLayout(parent)
        
        # Contribution Panel (New)
        self.contrib_panel = ContributionPanel(self.data_manager)
        layout.addWidget(self.contrib_panel)
        layout.addStretch()

    def setup_settings(self, parent):
        layout = QVBoxLayout(parent)
        
        self.check_autostart = QCheckBox("开机自启动")
        self.check_autostart.toggled.connect(self.on_autostart_toggled)
        
        self.check_engineer = QCheckBox("工程师模式 (Python 刷题提醒)")
        self.check_engineer.toggled.connect(self.on_engineer_mode_toggled)
        
        self.check_test_mode = QCheckBox("测试模式 (显示 5秒 快速测试按钮)")
        self.check_test_mode.toggled.connect(self.on_test_mode_toggled)
        
        self.check_deepseek = QCheckBox("启用 DeepSeek API 功能 (开发中)")
        self.check_deepseek.toggled.connect(self.on_deepseek_toggled)
        
        self.btn_clear_tags = QPushButton("⚠️ 清空常用标签统计")
        self.btn_clear_tags.setStyleSheet("color: red; margin-top: 10px;")
        self.btn_clear_tags.clicked.connect(self.on_clear_tags_clicked)
        
        layout.addWidget(self.check_autostart)
        layout.addWidget(self.check_engineer)
        layout.addWidget(self.check_test_mode)
        layout.addWidget(self.check_deepseek)
        layout.addWidget(self.btn_clear_tags)
        layout.addStretch()

    def load_settings(self):
        config = self.data_manager.get_config()
        # Autostart check (from registry, more reliable than config file sync)
        from .utils import check_autostart
        self.check_autostart.setChecked(check_autostart())
        self.check_engineer.setChecked(config.get("engineer_mode", False))
        self.check_test_mode.setChecked(config.get("test_mode", False))
        self.check_deepseek.setChecked(config.get("deepseek_enabled", False))

    def on_autostart_toggled(self, checked):
        if set_autostart(checked):
            self.data_manager.update_config("auto_start", checked)
        else:
            # Revert if failed
            self.check_autostart.blockSignals(True)
            self.check_autostart.setChecked(not checked)
            self.check_autostart.blockSignals(False)

    def on_engineer_mode_toggled(self, checked):
        self.data_manager.update_config("engineer_mode", checked)
        
        if checked:
             self.sig_notify.emit("工程师模式已开启", "您将收到 Python 练习提醒。")
        else:
             self.sig_notify.emit("工程师模式已关闭", "Python 练习提醒已关闭。")

    def on_test_mode_toggled(self, checked):
        self.data_manager.update_config("test_mode", checked)
        self.test_btn.setVisible(checked)
        if checked:
             self.btn_layout.removeWidget(self.test_btn)
             self.btn_layout.insertWidget(0, self.test_btn) # Ensure it's first

    def on_deepseek_toggled(self, checked):
        self.data_manager.update_config("deepseek_enabled", checked)
        if checked:
            self.sig_notify.emit("DeepSeek API", "已启用 DeepSeek 功能接口 (暂无实际功能)")
        else:
            self.sig_notify.emit("DeepSeek API", "已禁用 DeepSeek 功能")

    def on_clear_tags_clicked(self):
        reply = QMessageBox.question(
            self, 
            "确认", 
            "确定要清空所有常用标签统计吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.data_manager.clear_tag_stats()
            # If records tab is active, update it
            if hasattr(self, 'contrib_panel'):
                if hasattr(self.contrib_panel, 'tag_stats'):
                    self.contrib_panel.tag_stats.update_data()
            self.sig_notify.emit("完成", "常用标签统计已清空。")


    def closeEvent(self, event):
        """Minimize to tray instead of closing."""
        event.ignore()
        self.hide()

    @Slot()
    def show_normal_thread_safe(self):
        """Slot to be called from main thread."""
        self.show()
        self.activateWindow()
        self.raise_()

    def quick_add_task(self, task_name):
        """Handle quick add from Mini Mode."""
        # 1. Add to active UI tasks immediately
    def quick_add_task(self, task_name):
        """Handle quick add from Mini Mode."""
        if not task_name: return
        
        self.input_field.setText(task_name) 
        # User expects task to START immediately when using this quick add.
        # Default to 25m Pomodoro
        self.start_focus_with_input(25, is_pomodoro=True)
    
    def add_task(self):
        task_name = self.input_field.text().strip()
        if task_name:
            self.data_manager.add_task(task_name, "manual") 
            # Note: This just adds to Todo list, doesn't start timer.
                
        self.input_field.clear()

    def on_input_return_pressed(self):
        """Handle return key in input field - Start 25m Pomodoro by default."""
        self.start_focus_with_input(25, is_pomodoro=True)

    def eventFilter(self, obj, event):
        if obj == self.input_field:
            if event.type() == QEvent.FocusIn or (event.type() == QEvent.MouseButtonPress):
                # Update completer model
                top_tags = [t[0] for t in self.data_manager.get_tag_stats()]
                if top_tags:
                    model = QStringListModel(top_tags)
                    self.completer.setModel(model)
                    
                    # Force popup show even if text is empty
                    if not self.input_field.text():
                        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
                    else:
                        self.completer.setCompletionMode(QCompleter.PopupCompletion)
                        
                    self.completer.complete()
        
        return super().eventFilter(obj, event)
