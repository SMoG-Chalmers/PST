@ECHO OFF

PUSHD %~dp0..

for /f "delims=" %%i in ('dir /a:d /s /b build') do rd /s /q "%%i"
for /f "delims=" %%i in ('dir /a:d /s /b __pycache__') do rd /s /q "%%i"
del *.pyc /s /q

POPD