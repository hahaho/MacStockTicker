@echo off
chcp 65001
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building executable...
python -m PyInstaller --noconfirm --onedir --windowed --name "WindowsStockTicker" stock_ticker.py

echo.
echo Build complete!
echo Executable is located in the dist\WindowsStockTicker folder.
pause
