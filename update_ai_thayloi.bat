@echo off
title ?? C?P NH?T D? ÁN AI TH?Y L?I
cd /d "E:\abc"

echo.
echo =============================================
echo     ?? AI TH?Y L?I - T? Ð?NG C?P NH?T CODE
echo =============================================
echo.
set /p msg="?? Nh?p n?i dung thay d?i (commit message): "

echo.
echo ? Ðang thêm file thay d?i...
git add .

echo.
echo ?? Ðang t?o commit: %msg%
git commit -m "%msg%"

echo.
echo ??  Ðang d?y code lên GitHub...
git push

echo.
echo ? C?p nh?t lên GitHub thành công!
echo ?? Render s? t? d?ng tri?n khai b?n m?i trong vài phút...
echo.
pause
