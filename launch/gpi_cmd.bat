@echo off
setlocal
::    Copyright (C) 2014  Dignity Health
::
::    This program is free software: you can redistribute it and/or modify
::    it under the terms of the GNU Lesser General Public License as published by
::    the Free Software Foundation, either version 3 of the License, or
::    (at your option) any later version.
::
::    This program is distributed in the hope that it will be useful,
::    but WITHOUT ANY WARRANTY; without even the implied warranty of
::    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
::    GNU Lesser General Public License for more details.
::
::    You should have received a copy of the GNU Lesser General Public License
::    along with this program.  If not, see <http://www.gnu.org/licenses/>.
::
::    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
::    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
::    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
::    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
::    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
::    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
::    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
::    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

:: The GPI launcher script for Windows installations.

set ANACONDA=/opt/anaconda1anaconda2anaconda3
set PYTHON=%ANACONDA%\python
set GPI_LAUNCH=%ANACONDA%\Scripts\gpi_launch

:: Add needed folders to the path if launching from outside an active conda
set ANACONDA_WIN=%ANACONDA:/=\%
echo %PATH% | findstr %ANACONDA_WIN% > NUL
if %ERRORLEVEL% NEQ 0 goto :fixpath
goto :endif

:fixpath
  set PATH=%ANACONDA_WIN%\bin;%PATH%
  set PATH=%ANACONDA_WIN%\Scripts;%PATH%
  set PATH=%ANACONDA_WIN%\Library\bin;%PATH%
  set PATH=%ANACONDA_WIN%\Library\usr\bin;%PATH%
  set PATH=%ANACONDA_WIN%\Library\mingw-w64\bin;%PATH%
  set PATH=%ANACONDA_WIN%;%PATH%
:endif

%PYTHON% %GPI_LAUNCH% -style Windows %*

