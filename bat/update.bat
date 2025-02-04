@echo off
setlocal enabledelayedexpansion

set /a SUCCESS=0
set /a SUCCESS_VERSION=1
set /a SUCCESS_RELEASE=2
set /a SUCCESS_MICROUPDATE=4
set /a SUCCESS_MINORUPDATE=8
set /a SUCCESS_MAJORUPDATE=16
set /a FAIL_UNEXPECTED=32
set /a FAIL_NOTUPDATED=33
set /a FAIL_WRITEERROR=34
set /a MAX_COUNT=16

set MODULE=src\python\ccpn\util\Update.py

rem iterate through and resolve the symbolic links if needed
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

set ENTRY_MODULE=%CCPNMR_TOP_DIR%\%MODULE%

set /a lasterr=-1
set /a err=0
for /l %%c in (1,1,!MAX_COUNT!) do (
    "%CONDA%\python.exe" -i -O -W ignore "%ENTRY_MODULE%" %*

    if !errorlevel! equ !SUCCESS! (
        rem updated with code that requires loop to terminate
        rem   could be called with switches that do other actions
        goto _done
    )
    if !errorlevel! geq !FAIL_UNEXPECTED! (
        rem updated with code that requires loop to terminate
        echo there was an error updating: !errorlevel!
        goto _done
    )
    if !errorlevel! equ !lasterr! (
        rem update was apparently successful but the version didn't increment by 1 in any field
        echo there was an issue updating version: !errorlevel!
        goto _done
    )

    rem version changed so may need to update again
    set /a lasterr=!errorlevel!
)

:_done
endlocal

rem return the exit code from the update
exit /b !errorlevel!

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
