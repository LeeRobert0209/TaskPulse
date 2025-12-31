from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QLineEdit, QApplication, QSystemTrayIcon, QMenu,
                               QTabWidget, QCheckBox, QPushButton, QListWidget, QHBoxLayout,
                               QSlider, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QTime
from PySide6.QtGui import QIcon, QAction
from .config import APP_NAME, APP_ICON_PATH
from .data_manager import DataManager
from .utils import set_autostart

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

class MainWindow(QMainWindow):
    # Custom signals
    request_show = Signal()
    sig_notify = Signal(str, str) # title, message

    def __init__(self, scheduler=None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(380, 500)
        self.data_manager = DataManager()
        self.scheduler = scheduler
        self.pomodoro_count = 0 # Track completed Pomodoros
        
        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Dashboard (Tasks & Input)
        self.dashboard_tab = QWidget()
        self.setup_dashboard(self.dashboard_tab)
        self.tabs.addTab(self.dashboard_tab, "仪表盘")
        
        # Tab 2: Settings
        self.settings_tab = QWidget()
        self.setup_settings(self.settings_tab)
        self.tabs.addTab(self.settings_tab, "设置")

        # Connect signals
        self.request_show.connect(self.show_normal_thread_safe)
        
        # Load initial state
        self.load_settings()

    def setup_dashboard(self, parent):
        layout = QVBoxLayout(parent)
        
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
        
        layout.addWidget(input_group)
        
        # 2. Timer Section (Middle)
        focus_group = QGroupBox("2. 设定时间并开始")
        focus_layout = QVBoxLayout(focus_group)
        
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
        
        layout.addWidget(focus_group)
        
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

    def refresh_task_list(self, full_reload=False):
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

    # Legacy handle_input removed or integrated
    def handle_input(self):
        # If user presses enter in input box, maybe default to 25 mins?
        # Or just do nothing and wait for button press.
        pass

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
        
        layout.addWidget(self.check_autostart)
        layout.addWidget(self.check_engineer)
        layout.addWidget(self.check_test_mode)
        layout.addWidget(self.check_deepseek)
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

    def handle_input(self):
        text = self.input_field.text().strip()
        if text:
            # Add as task logic (Simplified)
            # In real deep mode, would parse date/time or show dialog
            self.data_manager.add_task(text, "manual")
            self.task_list.addItem(text)
                
        self.input_field.clear()
