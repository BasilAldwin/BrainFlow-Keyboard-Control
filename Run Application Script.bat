@echo off
REM ===================================================
REM  BrainFlow Keyboard Control - Run Script
REM ===================================================

echo.
echo Starting the BrainFlow Keyboard Control server...
echo The user interface should open in your default web browser momentarily.
echo.
echo This window must remain open for the application to work.
echo To stop the server, simply close this window or press CTRL+C.
echo.

REM Use 'py' to launch the Python script.
py muse_server_backend.py

echo.
echo Server has been stopped.
echo Press any key to close this window.
pause > nul
