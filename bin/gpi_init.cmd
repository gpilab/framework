@ECHO OFF
python "%~dp0gpi_make" --all --force -w
FOR /F "usebackq tokens=* delims=" %%P IN (`python -c "import sys,io; _o=sys.stdout; sys.stdout=io.StringIO(); from gpi.config import Config; sys.stdout=_o; [print(p) for p in Config.GPI_LIBRARY_PATH]" 2^>nul`) DO (
    IF EXIST "%%P" (
        ECHO Building modules in: %%P
        PUSHD "%%P"
        python "%~dp0gpi_make" --all --force -r 10 -w
        POPD
    ) ELSE (
        ECHO Warning: Directory '%%P' does not exist, skipping.
    )
)
