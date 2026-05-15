@ECHO OFF
FOR /F "tokens=* USEBACKQ" %%F IN (`python -c "import gpi; import os; print(os.path.dirname(gpi.__file__))"`) DO (
SET gpipath=%%F
)
ECHO %gpipath%
python %gpipath%\..\..\..\scripts\gpi_make --all --force -w
IF EXIST "%USERPROFILE%\.gpirc" (
    FOR /F "tokens=3" %%L IN ('findstr /B "LIB_DIRS" "%USERPROFILE%\.gpirc"') DO (
        FOR %%D IN (%%L) DO (
            IF EXIST "%%D" (
                ECHO Building modules in: %%D
                python %gpipath%\..\..\..\scripts\gpi_make --all --force -r 10 -w -d "%%D"
            ) ELSE (
                ECHO Warning: Directory '%%D' does not exist, skipping.
            )
        )
    )
)
