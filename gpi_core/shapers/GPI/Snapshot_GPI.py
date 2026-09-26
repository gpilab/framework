# Copyright (c) 2014, Dignity Health
# 
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
# 
#     Under either license, the following additional term applies:
# 
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
# 
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
# 
#         This file is part of the GPI core node library.
# 
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.


# Author: Guru Krishnamoorthy, PhD
# Date: September 2026

import gpi
from gpi.arrayops import copy as _copy, is_torch as _is_torch

# Fixed at module scope (not a widget) since GPI ports can't be added/removed
# after node creation -- bump this and add matching labels below to get more slots.
_SLOT_LABELS = ('A', 'B', 'C', 'D')


class ExternalNode(gpi.NodeAPI):
    """Holds up to 4 independent snapshots of whatever NumPy array or PyTorch
    tensor is on the input port, one per output port -- e.g. capture a recon at
    'Denoising %' = 1 into slot A, change the widget and rerun upstream, then
    capture the new result into slot B, and feed A/B into ImageCompare/Subtract
    without duplicating the recon node or round-tripping through WriteNPY/ReadNPY.

    INPUT: 'in' -- NumPy array or PyTorch tensor

    OUTPUT: 'out A'..'out D' -- the data last captured into that slot (holds its
        value across compute cycles until overwritten or cleared); None/empty
        until first captured

    WIDGETS:
    Capture A/B/C/D: copies the current input into that slot
    Clear All: resets every slot back to empty
    Status: read-only summary of what each slot currently holds
    """

    def initUI(self):
        self._slots = {lbl: None for lbl in _SLOT_LABELS}

        # Widgets
        for lbl in _SLOT_LABELS:
            self.addWidget('PushButton', 'Capture ' + lbl, toggle=False)
        self.addWidget('PushButton', 'Clear All', toggle=False)
        self.addWidget('TextBox', 'Status', val=self._status_text())

        # IO Ports
        self.addInPort('in', 'NPYorTorch', obligation=gpi.OPTIONAL)
        for lbl in _SLOT_LABELS:
            self.addOutPort('out ' + lbl, 'NPYorTorch')

        return 0

    def _status_text(self):
        parts = []
        for lbl in _SLOT_LABELS:
            data = self._slots[lbl]
            if data is None:
                parts.append(f'{lbl}: empty')
            else:
                kind = 'torch' if _is_torch(data) else 'numpy'
                parts.append(f'{lbl}: {kind} {data.dtype} {tuple(data.shape)}')
        return '\n'.join(parts)

    def compute(self):
        indata = self.getData('in')

        if self.getVal('Clear All'):
            self._slots = {lbl: None for lbl in _SLOT_LABELS}
        elif indata is not None:
            for lbl in _SLOT_LABELS:
                if self.getVal('Capture ' + lbl):
                    self._slots[lbl] = _copy(indata)

        for lbl in _SLOT_LABELS:
            self.setData('out ' + lbl, self._slots[lbl])

        self.setAttr('Status', val=self._status_text())

        return 0

    def execType(self):
        # GPI_THREAD: just holds/copies references, same class as Glue/Combine/Switch.
        return gpi.GPI_THREAD
