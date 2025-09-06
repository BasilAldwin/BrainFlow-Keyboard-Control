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

REM The 'cmd /k' command will run the python script and keep this window open,
REM which is useful for seeing any startup errors from Python.
cmd /k py muse_server_backend.py
