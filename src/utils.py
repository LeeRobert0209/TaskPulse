import winreg
import sys
import os
import logging
from .config import APP_NAME
from plyer import notification
from .config import APP_ICON_ICO_PATH

def show_notification(title, message):
    """
    Show a desktop notification.
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name=APP_NAME,
            app_icon=str(APP_ICON_ICO_PATH) if APP_ICON_ICO_PATH.exists() else None,
            timeout=10
        )
    except Exception as e:
        logging.error(f"Notification error: {e}")

def set_autostart(enable: bool = True):
    """
    Toggle auto-start for the application in Windows Registry.
    Uses Start_TaskPulse.bat to ensure correct environment.
    """
    key = winreg.HKEY_CURRENT_USER
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
        if enable:
            # Use the batch file in the project root as it handles environment setup correctly
            from .config import PROJECT_ROOT
            bat_path = PROJECT_ROOT / "Start_TaskPulse.bat"
            
            if bat_path.exists():
                command = f'"{bat_path}"'
                winreg.SetValueEx(registry_key, APP_NAME, 0, winreg.REG_SZ, command)
                logging.info(f"Auto-start enabled: {command}")
            else:
                logging.error(f"Batch file not found at {bat_path}, cannot enable autostart.")
                # Fallback to previous method or fail?
                # Failing is better than broken entry.
                winreg.CloseKey(registry_key)
                return False
        else:
            try:
                winreg.DeleteValue(registry_key, APP_NAME)
                logging.info("Auto-start disabled")
            except FileNotFoundError:
                pass # Already disabled
                
        winreg.CloseKey(registry_key)
        return True
    except Exception as e:
        logging.error(f"Error setting autostart: {e}")
        return False

def check_autostart() -> bool:
    """Check if auto-start is currently enabled."""
    key = winreg.HKEY_CURRENT_USER
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(registry_key, APP_NAME)
        winreg.CloseKey(registry_key)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Error checking autostart: {e}")
        return False
