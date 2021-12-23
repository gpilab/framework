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
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.


import gpi
from gpi import QtCore
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


class GPIState(QtCore.QObject):
    """A single FSM state to be used with the GPI_FSM class.  It manages its
    transitions, entry and exit functions.
    """
    entered = gpi.Signal()
    exited = gpi.Signal()

    def __init__(self, name, func, machine=None, efunc=None):
        super(GPIState, self).__init__()
        if not isinstance(name, str):
            msg = "expecting str arg: GPIState.__init__(>str<,func,GPI_FSM)"
            log.critical(msg)
        if machine:
            if not isinstance(machine, GPI_FSM):
                msg = "expecting GPI_FSM arg: GPIState.__init__(str,func,>GPI_FSM<)"
                log.critical(msg)
        self._name = str(name)
        self._transitions = {}
        self._func = func  # on entry
        self._efunc = efunc  # on exit
        if machine:
            machine.addState(self)

    def addTransition(self, sig, state):
        if not isinstance(sig, str):
            msg = "expecting str arg: GPIState.addTransition(>str<,GPIState)"
            log.critical(msg)
        self._transitions[sig] = state

    @property
    def name(self):
        return self._name

    def transitions(self):
        return self._transitions

    def onEntry(self, sig):
        self.entered.emit()
        if self._func:
            self._func(sig)

    def onExit(self, sig):
        self.exited.emit()
        if self._efunc:
            self._efunc(sig)


class GPI_FSM(QtCore.QObject):
    """The GPI Canvase and Nodes operate within different states.  The finite
    state machine allows for fast and easy checking to determine whether the
    user has performed an invalid operation or not.
    """
    switched = gpi.Signal()

    def __init__(self, name=''):
        super(GPI_FSM, self).__init__()
        self._name = name
        self._states = []
        self._cur_state = None

    @property
    def curState(self):
        return self._cur_state

    @property
    def curStateName(self):
        return self._cur_state.name

    @property
    def name(self):
        return self._name

    def next(self, dsig):
        '''Validate input signal as part of _cur_state,
        then switch to indicated state.'''
        if isinstance(dsig, str):
            sig = str(dsig)
            dsig = sig
        elif isinstance(dsig, str):
            sig = str(dsig)
            dsig = sig
        elif isinstance(dsig, dict):
            if 'sig' in dsig:
                if isinstance(dsig['sig'], str) or isinstance(dsig['sig'], str):
                    sig = str(dsig['sig'])
                    dsig['sig'] = sig
                else:
                    msg = "expecting str in dict[\'sig\'] in arg: GPI_FSM(" + self._name + ").next(>str<)"
                    log.critical(msg)
            else:
                msg = "expecting str key \'sig\' in arg: GPI_FSM(" + self._name + ").next(>str<)"
                log.critical(msg)
                return
        else:
            msg = "expecting str (or str in dict[\'sig\']) arg: GPI_FSM(" + \
                    self._name + ").next(>str<) type:" + str(type(dsig))
            log.critical(msg)
            return

        if sig in self._cur_state.transitions():
            self._cur_state.onExit(dsig)
            self._cur_state = self._cur_state.transitions()[sig]
            msg = "GPI_FSM(" + self._name + "):next(): Switched to state(" + \
                self._cur_state.name + ")"
            log.debug(msg)
            self._cur_state.onEntry(dsig)
            self.switched.emit()
        else:
            msg = "GPI_FSM(" + self._name + "):next(): state(" + self._cur_state.name + \
                ") has no transition: \'" + str(
                    sig) + "\'\n" + str(self._cur_state.transitions())
            log.debug(msg)

    def addState(self, state):
        if state in self._states:
            msg = "EMPHATIC WARNING!!!: GPI_FSM(" + self._name + "):addState(): Warning, state(" + state.name \
                + ") already exists, skipping..."
            log.critical(msg)
        else:
            self._states.append(state)

    def start(self, state):
        if state in self._states:
            self._cur_state = state
            msg = "GPI_FSM(" + self._name + \
                "):start(): in state(" + state.name + ")"
            log.debug(msg)
            self._cur_state.onEntry('init')
        else:
            msg = "GPI_FSM(" + self._name + "):start(): ERROR, state(" + state.name \
                + ") state not in list, can't start GPI_FSM!"
            log.critical(msg)
