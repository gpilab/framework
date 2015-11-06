#!/bin/bash

#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# The GPI launcher script.  The .command suffix is used by OSX automator.

# get user environment settings
#   -this will pickup the user's visual editor
if [ -f $HOME/.bashrc ]; then
        . $HOME/.bashrc
fi

ANACONDA=/opt/anaconda1anaconda2anaconda3
PYTHON=${ANACONDA}/bin/python
GPI_LAUNCH=${ANACONDA}/bin/gpi_launch
GPI_LINK=/tmp/GPI
TMPFILE="/tmp/gpi__.command"

# OSX
if [ "$(uname)" == "Darwin" ]; then
    ln -f -s $PYTHON $GPI_LINK

    # remove existing temp file
    rm -f $TMPFILE  

    # roll all args into another script for terminal.app
    echo "#!/bin/bash" > $TMPFILE
    echo "$GPI_LINK $GPI_LAUNCH $@" >> $TMPFILE
    chmod a+x $TMPFILE
    /usr/bin/open $TMPFILE
fi

# Linux
if [ "$(uname)" == "Linux" ]; then
    $PYTHON $GPI_LAUNCH -style cleanlooks $@
fi
