@echo off
title ?? C?P NH?T D? �N AI TH?Y L?I
cd /d "E:\abc"

echo.
echo =============================================
echo     ?? AI TH?Y L?I - T? �?NG C?P NH?T CODE
echo =============================================
echo.
set /p msg="?? Nh?p n?i dung thay d?i (commit message): "

echo.
echo ? �ang th�m file thay d?i...
git add .

echo.
echo ?? �ang t?o commit: %msg%
git commit -m "%msg%"

echo.
echo ??  �ang d?y code l�n GitHub...
git push

echo.
echo ? C?p nh?t l�n GitHub th�nh c�ng!
echo ?? Render s? t? d?ng tri?n khai b?n m?i trong v�i ph�t...
echo.
pause
