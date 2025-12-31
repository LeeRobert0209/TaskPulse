@echo off
cd /d "%~dp0"
echo Starting TaskPulse...
start "" pythonw -m src.main
exit
