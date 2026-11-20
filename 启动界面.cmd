@echo off
cd /d "%~dp0"

if exist "code\dist\HotelBooking.exe" (
    start "" /d "code\dist" "code\dist\HotelBooking.exe"
    exit /b
)

if exist "code\launch_gui.pyw" (
    start "" pyw -3 "code\launch_gui.pyw"
    exit /b
)

echo Launcher not found. Please check the code folder.
pause
