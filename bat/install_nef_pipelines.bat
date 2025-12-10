@echo off
setlocal enabledelayedexpansion

set CCPNMR_TOP_DIR=%~dpnx0
set /a _count=0
:_countLoop
    call :isLink _SYM "%CCPNMR_TOP_DIR%"
    call :fileName _PATH "%CCPNMR_TOP_DIR%"
    set _FOUND=
    set "_CMD=cmd /c dir /AL "%CCPNMR_TOP_DIR%\.." 2^>nul ^| find "%_PATH%""
    for /F "tokens=2 delims=[]" %%G in ('%_CMD%') do set "_FOUND=%%G"
    if defined _SYM if defined _FOUND call :AbsPath CCPNMR_TOP_DIR "%_FOUND%"
    call :AbsPath CCPNMR_TOP_DIR "%CCPNMR_TOP_DIR%\.."

    set /a _count+=1
    if !_count! lss 2 goto _countLoop

call "%CCPNMR_TOP_DIR%\bat\paths"
"%CONDA%\python.exe" -m pip uninstall nef_pipelines
"%CONDA%\python.exe" -m pip cache purge
"%CONDA%\python.exe" -m pip install nef_pipelines
endlocal

PAUSE
exit /b

:AbsPath
    REM return absolute name of input path
    REM :param %1: Name of output variable
    REM :param %2: input path
    REM :return: absolute path
    set %1=%~f2
    exit /b

:fileName
    REM return absolute name of input path
    REM :param %1: Name of output variable
    REM :param %2: input path
    REM :return: filename
    set %1=%~nx2
    exit /b

:isLink
    REM return if path object is a symlink
    REM :param %1: Name of output variable
    REM :param %2: input path
    REM :return: true (variable defined) if symlink
    set %1=
    for %%i in ("%~f2") do set attribute=%%~ai
    set attribute=%attribute:~8,1%
    if "%attribute%"=="l" set %1=true
    exit /b
