@ECHO OFF

if "%1" EQU "" goto usage
if "%2" NEQ "" goto usage

set pstalgo_dir=%~dp0..
set target_dir=%1

xcopy %pstalgo_dir%\bin\*32.dll          %target_dir%\pstalgo\bin\ /y
xcopy %pstalgo_dir%\bin\*64.dll          %target_dir%\pstalgo\bin\ /y
xcopy %pstalgo_dir%\bin\libpstalgo.dylib %target_dir%\pstalgo\bin\ /y
xcopy %pstalgo_dir%\python\*.py          %target_dir%\pstalgo\python\ /s /y

goto:eof

:usage
ECHO Usage: deploy TARGET_FOLDER
exit /B 1