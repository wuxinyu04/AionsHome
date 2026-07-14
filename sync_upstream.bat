@echo off
REM AionsHome - 同步 upstream 脚本
REM 作用: 把本地魔改存成 patch → reset → merge upstream → 回打 patch
REM 用法: 双击运行，或 cmd /c sync_upstream.bat
REM 作者: 你 + Claude

cd /d "%~dp0"

setlocal enabledelayedexpansion

echo ========================================
echo   AionsHome - 同步 upstream
echo ========================================
echo.

REM ---------- 前置检查 ----------
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git 未安装
    pause
    exit /b 1
)

git remote get-url upstream >nul 2>&1
if errorlevel 1 (
    echo [ERROR] upstream remote 未配置
    echo        运行: git remote add upstream https://github.com/death34018-hue/AionsHome.git
    pause
    exit /b 1
)

REM ---------- 第 1 步: 备份当前 main ----------
echo [1/5] 备份当前 main...
REM 用 PowerShell 取 YYYYMMDD 格式日期（兼容性最好）
for /f "delims=" %%D in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd'"') do set "DATETIME=%%D"
if "!DATETIME!"=="" set "DATETIME=manual"
set "BACKUP=backup/before-sync-!DATETIME!"
git branch "!BACKUP!" main 2>nul
if errorlevel 1 (
    echo       (!BACKUP! 已存在, 跳过)
) else (
    echo       OK: !BACKUP!
)
echo.

REM ---------- 第 2 步: 把本地未提交改动存成 patch ----------
echo [2/5] 把本地未提交改动存成 patch...
set "PATCH=%TEMP%\aionshome-local-mods.patch"
git diff --quiet
if errorlevel 1 (
    git diff > "!PATCH!"
    if errorlevel 1 (
        echo       [ERROR] patch 存盘失败
        pause
        exit /b 1
    )
    echo       OK: !PATCH!
    set "HAS_PATCH=1"
) else (
    echo       工作区干净, 无需存 patch
    set "HAS_PATCH=0"
)
echo.

REM ---------- 第 3 步: 清空工作区 ----------
echo [3/5] 清空工作区...
if "!HAS_PATCH!"=="1" (
    git checkout -- .
    if errorlevel 1 (
        echo       [ERROR] git checkout 失败
        pause
        exit /b 1
    )
) else (
    echo       无未提交改动, 跳过
)
echo       OK
echo.

REM ---------- 第 4 步: merge upstream ----------
echo [4/5] 拉 upstream 并 merge...
git fetch upstream
if errorlevel 1 (
    echo       [ERROR] git fetch 失败 (网络?)
    pause
    exit /b 1
)
echo.

git merge upstream/main --no-ff -m "merge: upstream 同步"
if errorlevel 1 (
    echo.
    echo ========================================
    echo   [CONFLICT] merge 有冲突!
    echo.
    echo   请手动解决:
    echo     1. git status           看冲突文件
    echo     2. 编辑冲突文件        解 ^<^<^<^<^<^< 标记
    echo     3. git add ^<file^>      标记已解决
    echo     4. git commit          完成 merge
    echo     5. git apply "!PATCH!"  回打本地魔改
    echo.
    echo   备份分支: !BACKUP!
    echo   Patch: !PATCH!
    echo ========================================
    pause
    exit /b 1
)
echo       OK
echo.

REM ---------- 第 5 步: 回打 patch ----------
echo [5/5] 回打本地魔改...
if "!HAS_PATCH!"=="0" (
    echo       无 patch 可打, 跳过
    goto :done
)
git apply "!PATCH!"
if errorlevel 1 (
    echo.
    echo ========================================
    echo   [WARN] patch 应用失败
    echo.
    echo   请手动处理:
    echo     git apply --reject "!PATCH!"     ^<-- 部分应用, 生成 .rej
    echo     git apply -R "!PATCH!"            ^<-- 完全回滚
    echo.
    echo   备份分支: !BACKUP!
    echo   Patch: !PATCH!
    echo ========================================
    pause
    exit /b 1
)
echo       OK
echo.

:done
echo ========================================
echo   同步完成!
echo.
echo   下一步:
echo     git status           看状态
echo     git diff --cached    看变化
echo     git commit           确认提交
echo.
echo   备份: !BACKUP!
echo   Patch: !PATCH!
echo ========================================
pause
