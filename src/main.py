import sys
import os
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from .gui import MainWindow
from .tray import SystemTray
from .scheduler import TaskScheduler
from .utils import show_notification

def main():
    # Fix for high DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set App User Model ID for Windows Notifications
    try:
        from ctypes import windll
        myappid = 'TaskPulse.DesktopApp.v1.0'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    # Single Instance Lock
    from PySide6.QtCore import QSharedMemory
    shared_memory = QSharedMemory("TaskPulse_Instance_Lock_v1")
    if not shared_memory.create(1):
        # Segment exists, meaning instance is running.
        # Try to attach to check if it's really alive (optional, but create failing usually handles it on Windows)
        # On Windows, shared memory counts references, so if process dies, it should be released.
        show_notification("TaskPulse", "TaskPulse is already running.")
        sys.exit(0)
    
    # Initialize Scheduler
    scheduler = TaskScheduler()
    
    window = MainWindow(scheduler) # Pass scheduler to GUI
    
    # Define exit callback
    def exit_app():
        scheduler.shutdown()
        app.quit()
    
    # Initialize Tray
    # Note: QSystemTrayIcon must be created in the main thread (which this is).
    tray = SystemTray(window, exit_app, scheduler)
    tray.setup()
    
    # Connect Window Notifications to Tray
    window.sig_notify.connect(lambda title, msg: tray.showMessage(title, msg, QSystemTrayIcon.Information, 3000))
    
    # Welcome Notification
    tray.showMessage("TaskPulse", "TaskPulse 已在后台运行。", QSystemTrayIcon.Information, 3000)
    
    # Show window on start as requested
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
