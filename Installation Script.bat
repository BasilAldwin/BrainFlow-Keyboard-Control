@echo off
REM ===================================================
REM  BrainFlow Keyboard Control - Installation Script
REM ===================================================

echo.
echo This script will install the required Python libraries for the BrainFlow Keyboard Control project.
echo Please ensure you have Python 3 installed and that it's accessible from your command line.
echo.
echo Press any key to begin the installation...
pause > nul

REM Check if requirements.txt exists in the current directory
if not exist "requirements.txt" (
    echo.
    echo [ERROR] requirements.txt not found!
    echo Please make sure this install.bat script is in the same folder as requirements.txt and muse_server_backend.py.
    echo.
    goto end
)

echo.
echo Found requirements.txt. Attempting to install packages using pip...
echo This may take a few minutes.
echo.

REM Use 'py -m pip' as it's a more reliable way to call pip on modern Windows systems
py -m pip install -r requirements.txt

REM Check the exit code of the previous command to see if it was successful
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The installation failed.
    echo Please review any error messages above. You may need to run this script as an Administrator.
    echo You can also try installing manually by running this command in your terminal:
    echo py -m pip install -r requirements.txt
    echo.
) else (
    echo.
    echo ===================================================
    echo      Installation Successful!
    echo ===================================================
    echo.
    echo You can now run the main application by double-clicking 'muse_server_backend.py'
    echo or by running the following command in this terminal:
    echo py muse_server_backend.py
    echo.
)

:end
echo Press any key to close this window.
pause > nul
