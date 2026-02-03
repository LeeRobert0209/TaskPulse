@echo off
setlocal enabledelayedexpansion

:: 切换到脚本所在目录
cd /d "%~dp0"

set "CONFIG_FILE=config.ini"
set "PYTHON_EXEC=pythonw"

:: 读取配置文件
if exist "%CONFIG_FILE%" (
    for /f "tokens=1,* delims==" %%A in ('type "%CONFIG_FILE%" ^| findstr /i "python_path"') do (
        set "KEY=%%A"
        set "VAL=%%B"
        :: 简单的去空格处理
        for /f "tokens=* delims= " %%a in ("!KEY!") do set "KEY=%%a"
        if /i "!KEY!"=="python_path" (
             set "TARGET_PYTHON=%%B"
        )
    )
)

:: 如果配置了 python_path
if defined TARGET_PYTHON (
    :: 去除可能存在的引号和空格
    set "TARGET_PYTHON=!TARGET_PYTHON:"=!"
    for /f "tokens=* delims= " %%a in ("!TARGET_PYTHON!") do set "TARGET_PYTHON=%%a"

    if exist "!TARGET_PYTHON!" (
        :: 尝试使用同目录下的 pythonw.exe 以避免黑框
        for %%I in ("!TARGET_PYTHON!") do set "PYTHON_DIR=%%~dpI"
        set "POTENTIAL_PYTHONW=!PYTHON_DIR!pythonw.exe"
        
        if exist "!POTENTIAL_PYTHONW!" (
            set "PYTHON_EXEC=!POTENTIAL_PYTHONW!"
        ) else (
            set "PYTHON_EXEC=!TARGET_PYTHON!"
        )
    ) else (
        echo [WARN] 配置的 python_path 未找到: "!TARGET_PYTHON!"
        echo 正在回退到系统默认 pythonw...
        timeout /t 3 >nul
    )
)

echo Starting TaskPulse with: !PYTHON_EXEC!
start "" "!PYTHON_EXEC!" -m src.main
exit
