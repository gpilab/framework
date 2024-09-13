@ECHO OFF
FOR /F "tokens=* USEBACKQ" %%F IN (`python -c "import gpi; import os; print(os.path.dirname(gpi.__file__))"`) DO (
SET gpipath=%%F
)
ECHO %gpipath%
python %gpipath%\..\..\..\scripts\gpi_make --all