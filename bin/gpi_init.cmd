@ECHO OFF
SETLOCAL EnableExtensions EnableDelayedExpansion

python -m gpi.win_setup
IF ERRORLEVEL 1 (
    ECHO ERROR: Windows MinGW setup failed. Aborting.
    EXIT /B 1
)

FOR /F "usebackq tokens=* delims=" %%P IN (`python -c "import gpi_core, os; print(os.path.dirname(gpi_core.__file__))" 2^>nul`) DO (
    SET "BASEDIR=%%P"
)

IF NOT DEFINED BASEDIR (
    ECHO ERROR: Could not resolve gpi_core base directory.
    EXIT /B 1
)

FOR %%R IN ("!BASEDIR!\..") DO SET "ROOTDIR=%%~fR"

CALL :build_dir "!BASEDIR!" 10
CALL :build_dir "!ROOTDIR!\gpi\include\PyFI" 2
CALL :build_dir "!ROOTDIR!\include\PyFI" 2

FOR /F "usebackq tokens=* delims=" %%P IN (`python -c "import sys,io; _o=sys.stdout; sys.stdout=io.StringIO(); from gpi.config import Config; sys.stdout=_o; [print(p) for p in Config.GPI_NODE_BUILD_DIRS]" 2^>nul`) DO (
    SET "BNAME=%%~nxP"
    IF /I "!BNAME!"=="gpi_core" (
        CALL :build_dir "%%P" 10
    ) ELSE IF /I "!BNAME!"=="PyFI" (
        CALL :build_dir "%%P" 10
    ) ELSE IF /I "!BNAME:~0,4!"=="gpi_" (
        CALL :build_dir "%%P" 10
    ) ELSE (
        ECHO Skipping non-GPI path: %%P
    )
)

python -m gpi.install_shortcut --interactive
EXIT /B 0

:build_dir
SET "TGT=%~1"
SET "DEPTH=%~2"
IF EXIST "%TGT%\" (
    ECHO Building modules in: %TGT%
    PUSHD "%TGT%"
    python "%~dp0gpi_make" --all --force -r %DEPTH% -w
    POPD
)
EXIT /B 0
