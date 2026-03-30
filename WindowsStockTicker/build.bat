@echo off
echo 正在安装必要的 Python 依赖...
pip install -r requirements.txt

echo.
echo 正在打包 Windows 可执行文件 (EXE)...
pyinstaller --noconfirm --onedir --windowed --name "WindowsStockTicker" --add-data "config.json;." "stock_ticker.py"

echo.
echo 打包完成！
echo 您的程序已生成在 dist\WindowsStockTicker 文件夹中。
echo 您可以双击 dist\WindowsStockTicker\WindowsStockTicker.exe 运行它。
pause