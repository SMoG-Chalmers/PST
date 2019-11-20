@ECHO OFF

set pstalgo_dir=%~dp0..

IF "%DISTRIBUTION_ROOT%"=="" (
	ECHO ERROR: Environment variable DISTRIBUTION_ROOT has not been set
	EXIT
)

rd %DISTRIBUTION_ROOT%\pstalgo /s /q
xcopy %pstalgo_dir%\bin\*.dll %DISTRIBUTION_ROOT%\pstalgo\bin\ /s /y
xcopy %pstalgo_dir%\include\*.* %DISTRIBUTION_ROOT%\pstalgo\include\ /s /y
xcopy %pstalgo_dir%\bin\*.lib %DISTRIBUTION_ROOT%\pstalgo\lib\ /s /y