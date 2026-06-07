@echo off
chcp 65001 >nul
title Dex AI Assistant
setlocal

echo ========================================
echo    Dex AI Assistant v3+
echo    Personalnyj golosovoj AI-assistent
echo ========================================
echo.
echo Vyberite dejstvie:
echo.
echo  [1] Zapustit Dex (Windows prilozhenie)
echo  [2] Zapustit Dex (komandnaya stroka)
echo  [3] Sobrat .exe dlya obychnogo zapuska
echo  [4] Vyhod
echo.

choice /c 1234 /n /m "Vash vybor: "
if errorlevel 4 exit /b
if errorlevel 3 goto build
if errorlevel 2 goto cli
if errorlevel 1 goto gui

:gui
echo.
echo Zapusk Windows prilozheniya...
call launch.bat --dashboard
pause
exit /b

:cli
echo.
echo Zapusk v komandnoj stroke...
call launch.bat
pause
exit /b

:build
echo.
echo Sborka .exe...
echo Eto mozhet zanyat 5-15 minut...
call build_exe.bat
pause
exit /b
