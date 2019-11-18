@ECHO OFF

PUSHD %~dp0..

rmdir deploy /s /q
del *.zip
for /f "delims=" %%i in ('dir /a:d /s /b __pycache__') do rd /s /q "%%i"
del *.pyc /s /q

POPD