@ECHO OFF

set pstqgis_dir=%~dp0..
set deploy_dir=%pstqgis_dir%\deploy

IF "%PSTALGO_PATH%" == "" (
	set pstalgo_dir=%pstqgis_dir%\..\pstalgo
) ELSE (
	set pstalgo_dir=%PSTALGO_PATH%
)

rmdir %deploy_dir% /s /q
mkdir %deploy_dir%
mkdir %deploy_dir%\pst

xcopy %pstqgis_dir%\src\pst\*.py         %deploy_dir%\pst /sy
xcopy %pstqgis_dir%\src\pst\*.png        %deploy_dir%\pst /sy
xcopy %pstqgis_dir%\src\pst\metadata.txt %deploy_dir%\pst /y
copy  %pstqgis_dir%\doc\readme.txt       %deploy_dir%\pst /y

CALL %pstalgo_dir%\scripts\deploy.bat %deploy_dir%\pst

pause