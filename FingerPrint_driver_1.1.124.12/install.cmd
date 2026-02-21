REM Goodix Fingerprint SPI Device Driver Install Demo 1.0 - 2020/11/27
@echo off
setlocal enabledelayedexpansion 
set indexcode=0
set e_code=0
set exitcode=0
set index2=0
cd /d "%~dp0"

rem Disable Fingerprint Driver Log Recording Function For Formal Release
REG ADD HKEY_LOCAL_MACHINE\SOFTWARE\Goodix\FP\LogOutput /v LogLevel /t REG_DWORD /d 00000000 /f /reg:64
REG ADD HKEY_LOCAL_MACHINE\SOFTWARE\Goodix\FP\LogOutput /v LogTarget /t REG_DWORD /d 00000000 /f /reg:64
REG ADD HKEY_LOCAL_MACHINE\SOFTWARE\Goodix\FP\LogOutput /v LogPath /t REG_SZ /d "C:\ProgramData\Goodix" /f /reg:64

devcon.exe rescan
rem Set Fingerprint Driver INF Name
set substring_1=gfspi.inf

rem Get Fingerprint Device HWID
:GetHWID
devcon.exe drivernodes "USB\VID_27C6&PID_51*" > HWID_T1.txt
set /p HWID_T2=<HWID_T1.txt
set HWID="%HWID_T2:~0,21%"

rem Uninstall Fingerprint Drivers
"C:\Windows\System32\dism.exe" /online /get-drivers /format:table > drivers.txt
findstr /n /i /C:"!substring_1!" drivers.txt > INF.txt &&goto removeoem || goto install

:removeoem
devcon.exe remove %HWID%
for /f "tokens=2 delims=: " %%a in (INF.txt) do (devcon.exe -f dp_delete %%a)

rem Install Fingerprint Drivers
:install
devcon.exe rescan
devcon.exe update "%~dp0\Drivers\gfspi.inf" %HWID%
if %ERRORLEVEL% GTR 1 (
set /a e_code=%ERRORLEVEL%
set /a index2=1"<<"16
)

:exit
del drivers.txt
del INF.txt
del HWID_T1.txt
set /a indexcode=%index2%
set /a exitcode=%indexcode%+%e_code%
exit /b %exitcode%