@echo off
setlocal
:: ROOT = 项目根目录 (此 .bat 在 ops/install/, 跳两层)
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

echo ========================================
echo   Aion Chat - Environment Setup
echo ========================================
echo.

:: ----------------------------------------
:: 1. Check Python
:: ----------------------------------------
echo [1/5] Checking Python ...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found!
    echo.
    echo    Please install Python 3.10+ from:
    echo    https://www.python.org/downloads/
    echo    Make sure to check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo    [OK] Python %PYVER%

:: ----------------------------------------
:: 2. Check venv module
:: ----------------------------------------
echo.
echo [2/5] Checking venv module ...
python -c "import venv" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python venv module is not available!
    echo.
    echo    This usually means Python was installed from Microsoft Store.
    echo    Fix: Uninstall the Microsoft Store version, then download from:
    echo    https://www.python.org/downloads/
    echo    Choose "Customize installation" and check all components.
    echo.
    pause
    exit /b 1
)
echo    [OK] venv module ready

:: ----------------------------------------
:: 3. Create virtual environment
:: ----------------------------------------
echo.
echo [3/5] Creating virtual environment (.venv) ...
set "NEED_VENV=1"
if exist "%ROOT%\.venv\Scripts\activate.bat" (
    findstr /i /c:"%CD%" "%ROOT%\.venv\Scripts\activate.bat" >nul 2>&1
    if not errorlevel 1 (
        set "NEED_VENV=0"
        echo    .venv already exists, skipping
    ) else (
        echo    .venv path mismatch, rebuilding ...
        rmdir /s /q .venv >nul 2>&1
    )
)
if "%NEED_VENV%"=="1" (
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment!
        echo    Make sure Python is from python.org (not Microsoft Store).
        pause
        exit /b 1
    )
    echo    Virtual environment created
)

:: ----------------------------------------
:: 4. Install dependencies
:: ----------------------------------------
echo.
echo [4/5] Installing dependencies (may take a few minutes) ...
if exist "vendor" (
    echo    Local vendor packages found; trying offline install first ...
    "%ROOT%\.venv\Scripts\python" -m pip install --no-index --find-links "%ROOT%\vendor" -r "%ROOT%\aion-chat\requirements.txt" -q
    if errorlevel 1 (
        echo.
        echo    Offline install failed, retrying with local packages plus Aliyun mirror ...
        "%ROOT%\.venv\Scripts\python" -m pip install --find-links "%ROOT%\vendor" -r "%ROOT%\aion-chat\requirements.txt" -i https://mirrors.aliyun.com/pypi/simple/ -q
    )
) else (
    echo    Trying Aliyun mirror first for speed ...
    "%ROOT%\.venv\Scripts\python" -m pip install -r "%ROOT%\aion-chat\requirements.txt" -i https://mirrors.aliyun.com/pypi/simple/ -q
    if errorlevel 1 (
        echo.
        echo    Mirror failed, retrying with default PyPI ...
        "%ROOT%\.venv\Scripts\python" -m pip install -r "%ROOT%\aion-chat\requirements.txt" -q
    )
)
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed!
    echo.
    echo    Common fixes:
    echo.
    echo    1. If this package includes a vendor folder, run offline install:
    echo       .venv\Scripts\python -m pip install --no-index --find-links vendor -r aion-chat\requirements.txt
    echo.
    echo    2. If you see "Microsoft Visual C++ 14.0 or greater is required":
    echo       Download and install Microsoft C++ Build Tools:
    echo       https://visualstudio.microsoft.com/zh-hans/visual-cpp-build-tools/
    echo       Check "Desktop development with C++", restart PC, then retry.
    echo.
    pause
    exit /b 1
)
echo    [OK] All dependencies installed

:: ----------------------------------------
:: 5. Verify
:: ----------------------------------------
echo.
echo [5/5] Verifying installation ...
"%ROOT%\.venv\Scripts\python" -c "import fastapi; print('    FastAPI', fastapi.__version__)"
"%ROOT%\.venv\Scripts\python" -c "import cv2; print('    OpenCV ', cv2.__version__)"
"%ROOT%\.venv\Scripts\python" -c "import numpy; print('    NumPy  ', numpy.__version__)"
"%ROOT%\.venv\Scripts\python" -c "import pyncm; print('    PyNCM   OK')"
"%ROOT%\.venv\Scripts\python" -c "import psutil; print('    psutil ', psutil.__version__)"
"%ROOT%\.venv\Scripts\python" -c "import ebooklib; print('    ebooklib OK')"
"%ROOT%\.venv\Scripts\python" -c "import bs4; print('    BeautifulSoup4 OK')"

echo.
echo ========================================
echo   [OK] Setup complete!
echo   You can now run the app.
echo ========================================
echo.
pause
