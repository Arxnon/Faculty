@echo off
chcp 65001 > nul

echo Очистка...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Faculty.spec del /f /q Faculty.spec

echo Сборка...

pyinstaller ^
--noconfirm ^
--windowed ^
--hidden-import=openpyxl ^
--name Faculty ^
--add-data "main.ui;." ^
--add-data "style.qss;." ^
--add-data "employee_system.db;." ^
--add-data "files;files" ^
main.py

echo.
echo Готово!
pause