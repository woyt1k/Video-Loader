@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || exit /b 1

set "PYTHONUTF8=1"
set "VIDEO_LOADER_PYTHON_HOME=%LOCALAPPDATA%\Programs\VideoLoader\Python313"
rem The running Command Prompt does not pick up PATH changes from WinGet.
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WindowsApps;%LOCALAPPDATA%\Microsoft\WinGet\Links;%ProgramFiles%\WinGet\Links"
set "VIDEO_LOADER_INSTALL_FLAGS=--exact --source winget --silent --disable-interactivity --no-upgrade --accept-package-agreements --accept-source-agreements"

call :find_python
if not defined VIDEO_LOADER_PYTHON (
    call :install_package Python.Python.3.13
    if errorlevel 1 goto :failed
    call :find_python
)
if not defined VIDEO_LOADER_PYTHON (
    echo Could not find Python 3.10 or newer after installation. 1>&2
    goto :failed
)

call :ensure_tool yt-dlp yt-dlp.yt-dlp
if errorlevel 1 goto :failed
call :ensure_tool ffmpeg Gyan.FFmpeg
if errorlevel 1 goto :failed
call :ensure_tool deno DenoLand.Deno
if errorlevel 1 goto :failed
call :ensure_tool gallery-dl mikf.gallery-dl
if errorlevel 1 goto :failed

"%VIDEO_LOADER_PYTHON%" %VIDEO_LOADER_PYTHON_OPTION% "%~dp0video_downloader.py" %*
set "VIDEO_LOADER_EXIT=%ERRORLEVEL%"
goto :finish

:failed
set "VIDEO_LOADER_EXIT=1"

:finish
popd
if not "%VIDEO_LOADER_EXIT%"=="130" pause
exit /b %VIDEO_LOADER_EXIT%

:find_python
set "VIDEO_LOADER_PYTHON="
set "VIDEO_LOADER_PYTHON_OPTION="
set "VIDEO_LOADER_CANDIDATE=%VIDEO_LOADER_PYTHON_HOME%\python.exe"
if exist "%VIDEO_LOADER_CANDIDATE%" call :test_python
for /f "delims=" %%P in ('where.exe python.exe 2^>nul') do (
    if not defined VIDEO_LOADER_PYTHON (
        set "VIDEO_LOADER_CANDIDATE=%%P"
        call :test_python
    )
)
if defined VIDEO_LOADER_PYTHON exit /b 0

set "VIDEO_LOADER_PYTHON_OPTION=-3"
for /f "delims=" %%P in ('where.exe py.exe 2^>nul') do (
    if not defined VIDEO_LOADER_PYTHON (
        set "VIDEO_LOADER_CANDIDATE=%%P"
        call :test_python
    )
)
exit /b 0

:test_python
"%VIDEO_LOADER_CANDIDATE%" %VIDEO_LOADER_PYTHON_OPTION% -c "import sys; sys.exit(sys.version_info[:2] < (3, 10))" >nul 2>&1
if not errorlevel 1 set "VIDEO_LOADER_PYTHON=%VIDEO_LOADER_CANDIDATE%"
exit /b 0

:ensure_tool
where.exe "%~1.exe" >nul 2>&1
if not errorlevel 1 exit /b 0
call :install_package "%~2"
if errorlevel 1 exit /b 1
where.exe "%~1.exe" >nul 2>&1
if not errorlevel 1 exit /b 0
echo Could not find %~1.exe after installation. 1>&2
exit /b 1

:install_package
where.exe winget.exe >nul 2>&1
if errorlevel 1 (
    echo WinGet is required for automatic installation. Install or update App Installer from the Microsoft Store. 1>&2
    exit /b 1
)

echo Installing %~1...
if /i "%~1"=="Python.Python.3.13" (
    winget.exe install --id "%~1" %VIDEO_LOADER_INSTALL_FLAGS% --scope user --location "%VIDEO_LOADER_PYTHON_HOME%"
) else (
    winget.exe install --id "%~1" %VIDEO_LOADER_INSTALL_FLAGS%
)
if not errorlevel 1 exit /b 0
echo Installation failed for %~1. See the WinGet message above, then open this file again. 1>&2
exit /b 1
