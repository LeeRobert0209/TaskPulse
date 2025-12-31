from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from .config import APP_NAME, APP_ICON_PATH

class SystemTray(QSystemTrayIcon):
    def __init__(self, main_window, app_exit_callback, scheduler):
        super().__init__()
        self.main_window = main_window
        self.app_exit_callback = app_exit_callback
        self.scheduler = scheduler
        
        # Load Icon
        if APP_ICON_PATH.exists():
            self.setIcon(QIcon(str(APP_ICON_PATH)))
        else:
            print(f"Icon not found: {APP_ICON_PATH}")

        # Menu
        self.menu = QMenu()
        
        # Actions
        show_action = QAction("显示 TaskPulse", self)
        show_action.triggered.connect(self.on_show_clicked)
        self.menu.addAction(show_action)
        
        # Quick Focus Submenu was removed per user request
        
        # self.menu.addSeparator() # Removed separator
        
        # exit_action added below
        
        self.menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.on_exit_clicked)
        self.menu.addAction(exit_action)
        
        self.setContextMenu(self.menu)
        
        # Click handler
        self.activated.connect(self.on_activated)

    def setup(self):
        self.show()

    def run(self):
        # Native tray doesn't need a separate run loop, it uses the app's loop.
        pass

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # Single click (or Double Click depending on firing order)
            # On some Windows versions, Trigger is single click. 
            # We can handle DoubleClick specifically if needed.
            pass
        elif reason == QSystemTrayIcon.DoubleClick:
            self.on_show_clicked()

    def on_show_clicked(self):
        self.main_window.show_normal_thread_safe()

    def on_quick_timer(self, minutes):
        import uuid
        from .utils import show_notification
        
        task_id = f"quick_{uuid.uuid4().hex[:8]}"
        
        def job_function():
            show_notification("时间到!", f"您的 {minutes} 分钟专注会话已结束。")
            
        self.scheduler.add_countdown_task(task_id, minutes, job_function)
        show_notification("专注开始", f"定时器已设定为 {minutes} 分钟。")

    def on_exit_clicked(self):
        self.hide() # Remove icon immediately
        self.app_exit_callback()
