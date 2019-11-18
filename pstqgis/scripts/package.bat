@ECHO OFF

set pstqgis_dir=%~dp0..
set deploy_dir=%pstqgis_dir%\deploy

del %pstqgis_dir%\pstqgis_*.zip
7z a %pstqgis_dir%\pstqgis_%DATE%.zip -tzip -r %deploy_dir%/*.*
%DISTRIBUTION_ROOT%\zipchmod\bin\zipchmod32.exe %pstqgis_dir%\pstqgis_%DATE%.zip command 0100755

pause